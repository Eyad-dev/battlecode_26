import random
from cambc import Controller, Direction, GameConstants, Position
from helper import *


class BugNav:
    """
    BugNav2 — merged Bug0/Bug1 navigator.

    Modes
    -----
    GREEDY      : move straight toward target; switch to WALL on obstacle
    WALL        : hug the wall until we beat our personal best distance record

    Reset hierarchy
    ---------------
    hard reset  : new target far away   → wipe everything, choose new rotation side
    soft reset  : target nudged slightly → recalibrate mindist, keep rotation side
    """

    # ── tunables ────────────────────────────────────────────────────────────────
    LEAVE_THRESHOLD          = 1    # dist² improvement needed to leave wall mode
    MAX_TURNS_ON_WALL        = 15    # flip rotation if stuck this many turns
    TARGET_MOVED_FAR_THRESH  = 20    # dist² threshold: hard-reset vs soft-reset
    # ────────────────────────────────────────────────────────────────────────────

    def __init__(self):
        self.prevtarget:         Position | None = None
        self.lastObstacleFound:  Position | None = None   # wall reference tile
        self.mindisttotarget:    float           = float("inf")
        self.minloctotarget:     Position | None = None
        self.rotateright:        bool    | None  = None   # None = undecided
        self.turnsmovingtoobstacle: int          = 0
        self.states:             set             = set()  # loop-detection codes
        self.mode:               str             = "GREEDY"   # "GREEDY" | "WALL"

    # ── resets ──────────────────────────────────────────────────────────────────

    def _hard_reset(self, ct: Controller):
        """Full reset — forget rotation side too."""
        self.turnsmovingtoobstacle  = 0
        self.lastObstacleFound      = None
        self.mindisttotarget        = float("inf")
        self.minloctotarget         = None
        self.rotateright            = None
        self.mode                   = "GREEDY"
        self.states.clear()
        print("[BUGNAV] hard reset")

    def _soft_reset(self, ct: Controller):
        """Keep rotation side; recalibrate mindist from current position."""
        if self.minloctotarget is not None and self.prevtarget is not None:
            dist_from_best  = distance_squared(self.minloctotarget, self.prevtarget)
            dist_from_here  = distance_squared(ct.get_position(),   self.prevtarget)
            if dist_from_best < dist_from_here:
                self.mindisttotarget = dist_from_best
            else:
                self.mindisttotarget = dist_from_here
                self.minloctotarget  = ct.get_position()
        else:
            self._hard_reset(ct)
            return
        self.lastObstacleFound    = None
        self.turnsmovingtoobstacle = 0
        self.mode                  = "GREEDY"
        self.states.clear()
        print("[BUGNAV] soft reset")

    # ── helpers ─────────────────────────────────────────────────────────────────

    def _choose_rotation_side(self, ct: Controller):
        """
        Decide once which side to hug by checking which first free tile
        is closer to the target.
        """
        if self.rotateright is not None:
            return

        currentpos = ct.get_position()
        direction  = currentpos.direction_to(self.prevtarget)

        dir_left   = direction
        dir_right  = direction
        loc_left   = currentpos
        loc_right  = currentpos

        for _ in range(8):
            dir_left = dir_left.rotate_left()
            loc_left = loc_left.add(dir_left)
            if ct.can_move(dir_left):
                break

        for _ in range(8):
            dir_right = dir_right.rotate_right()
            loc_right = loc_right.add(dir_right)
            if ct.can_move(dir_right):
                break

        if distance_squared(loc_left, self.prevtarget) < distance_squared(loc_right, self.prevtarget):
            self.rotateright = False
        else:
            self.rotateright = True

        print(f"[BUGNAV] rotation side chosen: {'right' if self.rotateright else 'left'}")

    def _check_loop(self, ct: Controller):
        """
        Encode (position × obstacle-direction × rotation-side) into an int and
        detect if we've visited this state before → stuck in a loop → hard reset.
        """
        if self.lastObstacleFound is None:
            return

        dir_map = {
            Direction.NORTH: 0, Direction.NORTHEAST: 1, Direction.EAST: 2,
            Direction.SOUTHEAST: 3, Direction.SOUTH: 4, Direction.SOUTHWEST: 5,
            Direction.WEST: 6, Direction.NORTHWEST: 7, Direction.CENTRE: 8,
        }

        currentpos         = ct.get_position()
        dir_to_obstacle    = currentpos.direction_to(self.lastObstacleFound)
        rot_bit            = 0 if (self.rotateright is True or self.rotateright is None) else 1

        code = (
            (currentpos.x           << 6)
            | (currentpos.y)
            | (rot_bit              << 15)
            | (dir_map[dir_to_obstacle] << 12)
        )

        if code in self.states:
            print("[BUGNAV] loop detected — resetting rotation side")
            self._hard_reset(ct)
        else:
            self.states.add(code)

    def _is_friendly_bot_blocking(self, ct: Controller, pos: Position) -> bool:
        """Return True if a friendly bot is standing on *pos*."""
        try:
            nearby = ct.get_nearby_entities()
            for eid in nearby:
                if ct.get_position(eid) == pos:
                    etype = ct.get_entity_type(eid)
                    # adjust EntityType names to match your game API
                    if hasattr(etype, "name") and etype.name in ("BUILDER_BOT", "SENTINEL"):
                        return True
        except Exception:
            pass
        return False

    # Inside BugNav class
    def _try_build_road(self, ct: Controller, pos: Position) -> bool:
        """Returns True if a road was actually built."""
        try:
            if ct.can_build_road(pos):
                ct.build_road(pos)
                return True
        except Exception:
            pass
        return False



    def _orthogonal_alignment_check(
        self, current_pos: Position, goal_pos: Position, current_dist_sq: int
    ) -> bool:
        """
        True when robot is axis- or diagonally-aligned with the goal and close —
        a configuration that can trap certain wall-follow directions.
        """
        dx = current_pos.x - goal_pos.x
        dy = current_pos.y - goal_pos.y
        aligned = (dx == 0 or dy == 0 or dx == dy)
        return aligned and current_dist_sq <= 20

    # ── main entry point ────────────────────────────────────────────────────────

    def move_towards(self, ct: Controller, target: Position):
        if target is None:
            return

        currentpos   = ct.get_position()
        dist_sq      = distance_squared(currentpos, target)

        if dist_sq == 0:
            return

        # ── 1. target-change detection ──────────────────────────────────────────
        if self.prevtarget is None or distance_squared(self.prevtarget, target) > self.TARGET_MOVED_FAR_THRESH:
            self._hard_reset(ct)
        elif distance_squared(self.prevtarget, target) > 0:
            self._soft_reset(ct)

        self.prevtarget = target

        # ── 2. loop detection ───────────────────────────────────────────────────
        self._check_loop(ct)

        # ── 3. overtime / stuck detection ──────────────────────────────────────
        if self.lastObstacleFound is not None:
            self.turnsmovingtoobstacle += 1
            if self.turnsmovingtoobstacle > self.MAX_TURNS_ON_WALL:
                print("[BUGNAV] stuck too long — flipping rotation side")
                self.rotateright             = not self.rotateright if self.rotateright is not None else True
                self.turnsmovingtoobstacle   = 0
                self.states.clear()

        # ── 4. leave condition — beat personal-best distance ───────────────────
        if dist_sq < self.mindisttotarget - self.LEAVE_THRESHOLD:
            self.mindisttotarget = dist_sq
            self.minloctotarget  = currentpos
            if self.lastObstacleFound is not None:
                print("[BUGNAV] new record distance — leaving wall mode")
                self.lastObstacleFound    = None
                self.turnsmovingtoobstacle = 0
                self.mode                  = "GREEDY"
                # keep rotation side; don't full-reset

        # ── 5. greedy mode ──────────────────────────────────────────────────────
        if self.lastObstacleFound is None:
            dir_to_target = currentpos.direction_to(target)
            next_tile     = currentpos.add(dir_to_target)

            if ct.can_move(dir_to_target) and ct.is_tile_passable(next_tile):
                ct.move(dir_to_target)
                return

            # hit something → enter wall-follow
            self.lastObstacleFound = next_tile
            self.mode              = "WALL"
            self._choose_rotation_side(ct)
            # fall through to wall-follow block immediately

        # ── 6. wall-follow mode ─────────────────────────────────────────────────
        if self.lastObstacleFound is not None:
            # ── 6a. optional orthogonal-alignment correction ────────────────────
            # When perfectly aligned and close, the naive sweep can loop;
            # a 90° counter-rotation fixes it.
            if self._orthogonal_alignment_check(currentpos, target, dist_sq):
                candidate = self.lastObstacleFound.direction_to(currentpos)
                if self.rotateright:
                    candidate = candidate.rotate_right().rotate_right()
                else:
                    candidate = candidate.rotate_left().rotate_left()
                print(f"[BUGNAV] alignment correction: candidate dir = {candidate}")
                # we just update the starting direction hint, not hard-override

            # ── 6b. compute sweep start direction ──────────────────────────────
            sweep_dir = currentpos.direction_to(self.lastObstacleFound)

            # Rotate AWAY from wall first (so we immediately check the "open" side)
            if self.rotateright:
                sweep_dir = sweep_dir.rotate_left()
            else:
                sweep_dir = sweep_dir.rotate_right()

            # ── 6c. sweep up to 8 directions ───────────────────────────────────
            found_path = False
            for i in range(8):
                next_tile = currentpos.add(sweep_dir)

                                # In move_towards sweep logic:
                if self._try_build_road(ct, next_tile):
                    return # End turn here! Don't try to move until next turn.

                if ct.can_move(sweep_dir) and ct.is_tile_passable(next_tile):
                    ct.move(sweep_dir)
                    return


                print(
                    f"[WALLFOLLOW] dir={sweep_dir} tile={next_tile} "
                    f"passable={ct.is_tile_passable(next_tile)} "
                    f"can_move={ct.can_move(sweep_dir)}"
                )

                # try to build road opportunistically
                self._try_build_road(ct, next_tile)

                if ct.can_move(sweep_dir) and ct.is_tile_passable(next_tile):
                    ct.move(sweep_dir)
                    found_path = True
                    break

                # check for friendly-bot blockage (don't update wall ref in this case)
                if self._is_friendly_bot_blocking(ct, next_tile):
                    for nudge in [sweep_dir.rotate_left(), sweep_dir.rotate_right()]:
                        if ct.can_move(nudge):
                            ct.move(nudge)
                            return 
                    print(f"[BUGNAV] friendly bot at {next_tile} — waiting one turn")
                    return


                # update wall reference to this newly confirmed obstacle
                self.lastObstacleFound = next_tile

                # continue rotating around the wall
                if self.rotateright:
                    sweep_dir = sweep_dir.rotate_right()
                else:
                    sweep_dir = sweep_dir.rotate_left()

            if not found_path:
                print("[BUGNAV] completely trapped — hard reset")
                self._hard_reset(ct)