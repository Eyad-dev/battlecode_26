from cambc import *
from helper import *


class BugNav:

    infinity = float('inf')
    MAXTURNSMOVINGTOOBSTACLE = 100

    directions = {
        Direction.NORTH: 0,
        Direction.NORTHEAST: 1,
        Direction.EAST: 2,
        Direction.SOUTHEAST: 3,
        Direction.SOUTH: 4,
        Direction.SOUTHWEST: 5,
        Direction.WEST: 6,
        Direction.NORTHWEST: 7,
        Direction.CENTRE: 8
    }

    def __init__(self):
        self.turnsmovingtoobstacle: int = 0
        self.rotateright: bool = None
        self.lastObstacleFound: Position | None = None
        self.mindisttotarget: int = float("inf")
        self.prevtarget: Position | None = None
        self.minloctotarget: Position | None = None
        self.states = set()
        self.ct = None
        print("[BugNav] initialized")

    def _passable(self, dir) -> bool:
        """True if the bot can actually step in this direction."""
        ct = self.ct
        tile = ct.get_position().add(dir)
        return (
            ct.can_move(dir)
            and ct.get_tile_env(tile) != Environment.ORE_TITANIUM
            and ct.get_tile_env(tile) != Environment.ORE_AXIONITE
        )

    def moveto(self, ct: Controller, target: Position):
        self.ct = ct
        pos = ct.get_position()
        print(f"[BugNav] moveto called: current_pos={pos}, target={target}")

        if target is None or distance_squared(pos, target) == 0:
            print("[BugNav] moveto: target is None or already at target")
            return

        # ── target-change bookkeeping ──────────────────────────────────────
        distbetweentargets = 0
        if self.prevtarget is None:
            self.resetPathFinding(True)
        else:
            distbetweentargets = distance_squared(self.prevtarget, target)

        self.prevtarget = target
        if distbetweentargets > 2:
            self.resetPathFinding(True)
        elif distbetweentargets > 0:
            self.softResetPathfinding()

        # ── update closest-distance record ────────────────────────────────
        d = distance_squared(pos, target)
        print(f"[BugNav] moveto: d={d}, mindist={self.mindisttotarget}, obstacle={self.lastObstacleFound}")
        if d < self.mindisttotarget:
            # Genuine progress: clear obstacle state and record new best
            self.resetPathFinding(False)
            self.mindisttotarget = d
            self.minloctotarget = pos
            self.states.clear()
            print(f"[BugNav] new mindist={d}")

        # ── loop detection (only while hugging an obstacle) ───────────────
        if self.lastObstacleFound is not None:
            self.checkstates()
            # checkstates may have cleared lastObstacleFound via reset; re-read
            if self.lastObstacleFound is None:
                print("[BugNav] loop-reset cleared obstacle, retrying straight line")

        # ── choose starting direction ──────────────────────────────────────
        # Always aim at the TARGET first, then rotate around the obstacle.
        # We must NEVER steer toward lastObstacleFound — that causes oscillation
        # (bot navigates into the wall tile and bounces back each turn).
        desired_dir = pos.direction_to(target)

        # ── fast path: direct move toward target ───────────────────────────
        if self.lastObstacleFound is None:
            try_build_road(ct, pos.add(desired_dir))
            if self._passable(desired_dir):
                ct.move(desired_dir)
                print(f"[BugNav] direct move {desired_dir}")
                return
            # Hit a new obstacle — record it and decide rotation direction
            self.lastObstacleFound = pos.add(desired_dir)
            print(f"[BugNav] new obstacle at {self.lastObstacleFound}")
            self.updateRot()

        # ── obstacle-hugging: rotate desired_dir until a passable cell ─────
        # Start from the direction toward the target and sweep according to
        # the chosen rotation sense.  This keeps the bot circling the wall
        # while still trying to make forward progress each turn.
        dir = desired_dir
        for attempt in range(16):
            print(f"[BugNav] hug attempt {attempt}, dir={dir}")
            next_tile = pos.add(dir)
            try_build_road(ct, next_tile)

            if self._passable(dir):
                ct.move(dir)
                print(f"[BugNav] hugging move {dir}")
                self.turnsmovingtoobstacle += 1
                if self.turnsmovingtoobstacle >= self.MAXTURNSMOVINGTOOBSTACLE:
                    print("[BugNav] MAXTURNSMOVINGTOOBSTACLE hit, resetting")
                    self.resetPathFinding(False)
                return

            # Record the impassable tile as the current obstacle face
            if onmap(ct, next_tile):
                self.lastObstacleFound = next_tile

            if self.rotateright:
                dir = dir.rotate_right()
            else:
                dir = dir.rotate_left()

        # Completely boxed in — give up and reset for next turn
        print("[BugNav] completely blocked, resetting")
        self.resetPathFinding(True)

    def resetPathFinding(self, resetrot: bool):
        self.turnsmovingtoobstacle = 0
        self.lastObstacleFound = None
        self.mindisttotarget = self.infinity
        if resetrot:
            self.rotateright = None
        self.states.clear()
        if resetrot:
            print("[BugNav] full reset (rot cleared)")

    def softResetPathfinding(self):
        if self.minloctotarget is not None:
            dist = distance_squared(self.minloctotarget, self.prevtarget)
            currentdist = distance_squared(self.prevtarget, self.ct.get_position())
            if dist < currentdist:
                self.mindisttotarget = dist
            else:
                self.mindisttotarget = currentdist
                self.minloctotarget = self.ct.get_position()
        else:
            self.resetPathFinding(False)
        print("[BugNav] soft reset")

    def checkstates(self):
        if self.lastObstacleFound is None:
            return
        pos = self.ct.get_position()
        dir_to_obs = pos.direction_to(self.lastObstacleFound)
        state = (
            pos.x,
            pos.y,
            BugNav.directions[dir_to_obs],
            self.rotateright
        )
        if state in self.states:
            print("[BugNav] LOOP DETECTED → full reset")
            self.resetPathFinding(True)
        else:
            self.states.add(state)

    def updateRot(self):
        """Pick the rotation direction that leads closer to the target."""
        if self.rotateright is not None:
            return  # Already decided for this obstacle

        pos = self.ct.get_position()
        base_dir = pos.direction_to(self.prevtarget)

        dir_left = base_dir
        dir_right = base_dir
        loc_left = pos
        loc_right = pos

        for _ in range(8):
            dir_left = dir_left.rotate_left()
            loc_left = loc_left.add(dir_left)
            if self.ct.can_move(dir_left):
                break

        for _ in range(8):
            dir_right = dir_right.rotate_right()
            loc_right = loc_right.add(dir_right)
            if self.ct.can_move(dir_right):
                break

        left_dist = distance_squared(loc_left, self.prevtarget)
        right_dist = distance_squared(loc_right, self.prevtarget)
        print(f"[BugNav] updateRot: left_dist={left_dist} right_dist={right_dist}")

        self.rotateright = (right_dist <= left_dist)
        print(f"[BugNav] updateRot: rotateright={self.rotateright}")
