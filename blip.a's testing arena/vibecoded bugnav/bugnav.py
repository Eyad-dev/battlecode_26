import random
from cambc import Controller, Direction, GameConstants, Position, Environment
from helper import *

class BugNav:
    LEAVE_THRESHOLD          = 1     # Lowered for better responsiveness
    MAX_TURNS_ON_WALL        = 20    # Increased to handle larger obstacles
    TARGET_MOVED_FAR_THRESH  = 15    # Prevent resetting on small target shifts

    def __init__(self):
        self.prevtarget:         Position | None = None
        self.lastObstacleFound:  Position | None = None
        self.mindisttotarget:    float           = float("inf")
        self.minloctotarget:     Position | None = None
        self.rotateright:        bool | None     = None
        self.turnsmovingtoobstacle: int          = 0
        self.states:             set             = set()
        self.mode:               str             = "ROOMBA"

    def _hard_reset(self, ct: Controller):
        self.turnsmovingtoobstacle = 0
        self.lastObstacleFound     = None
        self.mindisttotarget       = float("inf")
        self.minloctotarget        = None
        self.rotateright = random.choice([True, False])
        self.mode                  = "GREEDY"
        self.states.clear()

    def _soft_reset(self, ct: Controller):
        if self.minloctotarget is not None and self.prevtarget is not None:
            dist_here = distance_squared(ct.get_position(), self.prevtarget)
            self.mindisttotarget = dist_here
            self.minloctotarget  = ct.get_position()
        self.lastObstacleFound      = None
        self.turnsmovingtoobstacle  = 0
        self.mode                   = "GREEDY"
        self.states.clear()

    def _is_tile_blocked(self, ct: Controller, pos: Position) -> bool:
        """Custom check to treat Ores as walls for navigation."""
        if not ct.is_tile_passable(pos):
            return True
        env = ct.get_tile_env(pos)













        #MIGHT COMMENT LATERRRRR
        if env in [Environment.ORE_TITANIUM, Environment.ORE_AXIONITE]:
            return True
        return False

    def _try_build_road(self, ct: Controller, pos: Position) -> bool:
        """Returns True if it performed a build action."""
        if ct.get_action_cooldown() == 0:
            if ct.can_build_road(pos):
                ct.build_road(pos)
                return True
        return False
    
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

    def move_towards(self, ct: Controller, target: Position):
        if target is None: return
        currentpos = ct.get_position()
        dist_sq = distance_squared(currentpos, target)

        state = (
            currentpos.x,
            currentpos.y,
            self.mode,
            self.rotateright,
            self.lastObstacleFound.x if self.lastObstacleFound else -1,
            self.lastObstacleFound.y if self.lastObstacleFound else -1,
        )

        if state in self.states:
            print("[BUGNAV] Loop detected — flipping direction")
            self.rotateright = not self.rotateright
            self._soft_reset(ct)
            return

        self.states.add(state)

        # 1. Target Tracking
        if self.prevtarget is None or distance_squared(self.prevtarget, target) > self.TARGET_MOVED_FAR_THRESH:
            self._hard_reset(ct)
        self.prevtarget = target

        # 2. Leave Condition

        dir_to_target = currentpos.direction_to(target)
        next_tile = currentpos.add(dir_to_target)
        if (
            dist_sq < self.mindisttotarget - self.LEAVE_THRESHOLD
            and not self._is_tile_blocked(ct, next_tile)
            and ct.can_move(dir_to_target)
        ):
            self.mindisttotarget = dist_sq
            self.lastObstacleFound = None
            self.mode = "GREEDY"

        # 3. Greedy Navigation
        if self.mode == "GREEDY":
            dir_to_target = currentpos.direction_to(target)
            next_tile = currentpos.add(dir_to_target)

            if not self._is_tile_blocked(ct, next_tile) and ct.can_move(dir_to_target):
                # Opportunistic build
                if self._try_build_road(ct, next_tile): return
                ct.move(dir_to_target)
                return
            
            # Switch to Wall Follow
            self.mode = "WALL"
            is_blocked = self._is_tile_blocked(ct, next_tile)
            if is_blocked:
                self.lastObstacleFound = next_tile
            if self.rotateright is None:
                left = dir_to_target.rotate_left()
                right = dir_to_target.rotate_right()

                if ct.can_move(left):
                    self.rotateright = False
                elif ct.can_move(right):
                    self.rotateright = True
                else:
                    self.rotateright = True

        # 4. Wall Following
        if self.mode == "WALL":
            self.turnsmovingtoobstacle += 1
            print(f"[BUGNAV WALL] Starting wall follow - turnsmovingtoobstacle={self.turnsmovingtoobstacle}, lastObstacleFound={self.lastObstacleFound}, rotateright={self.rotateright}")
            sweep_dir = currentpos.direction_to(self.lastObstacleFound)
            print(f"[BUGNAV WALL] Initial sweep_dir towards obstacle: {sweep_dir}")
            
            # Start sweep by looking slightly 'away' from the wall
            sweep_dir = sweep_dir.rotate_left() if self.rotateright else sweep_dir.rotate_right()
            print(f"[BUGNAV WALL] After initial rotation (away from wall): sweep_dir={sweep_dir}")

            for step in range(8):
                next_tile = currentpos.add(sweep_dir)
                is_blocked = self._is_tile_blocked(ct, next_tile)
                can_move_wall = ct.can_move(sweep_dir)
                friendly_blocking = self._is_friendly_bot_blocking(ct, next_tile)
                print(f"[BUGNAV WALL] Step {step}: sweep_dir={sweep_dir}, next_tile={next_tile}, is_blocked={is_blocked}, can_move={can_move_wall}, friendly_blocking={friendly_blocking}")
                
                # Check for friendly bot deadlock
                if friendly_blocking:
                    print(f"[BUGNAV WALL] Friendly bot detected at {next_tile}, attempting nudges")
                    # Try a small nudge to avoid standing still
                    nudge_options = [sweep_dir.rotate_left(), sweep_dir.rotate_right()]
                    print(f"[BUGNAV WALL] Nudge options: {nudge_options}")
                    for nudge in nudge_options:
                        can_nudge = ct.can_move(nudge)
                        print(f"[BUGNAV WALL] Trying nudge {nudge}: can_move={can_nudge}")
                        if can_nudge:
                            print(f"[BUGNAV WALL] Executing nudge move: {nudge}")
                            ct.move(nudge)
                            return
                    print(f"[BUGNAV WALL] No valid nudges found, staying in place")
                    # fallback: break out of wall mode
                    self._soft_reset(ct)
                    return

                move_condition = not is_blocked and can_move_wall
                print(f"[BUGNAV WALL] Move condition check: not_blocked_and_can_move = {move_condition}")
                if move_condition:
                    road_built = self._try_build_road(ct, next_tile)
                    if road_built: 
                        print(f"[BUGNAV WALL] Built road at {next_tile} during wall follow")
                        return
                    print(f"[BUGNAV WALL] Moving along wall to {next_tile} in direction {sweep_dir}")
                    ct.move(sweep_dir)
                    return

                # Update wall reference
                print(f"[BUGNAV WALL] Cannot move to {next_tile}, updating wall reference from {self.lastObstacleFound} to {next_tile}")
                self.lastObstacleFound = next_tile
                old_sweep_dir = sweep_dir
                sweep_dir = sweep_dir.rotate_right() if self.rotateright else sweep_dir.rotate_left()
                print(f"[BUGNAV WALL] Rotating sweep_dir from {old_sweep_dir} to {sweep_dir} (rotateright={self.rotateright})")

            print(f"[BUGNAV WALL] No move found — forcing escape")

            # FORCE a move (critical fix)
            for d in Direction:
                if d != Direction.CENTRE and ct.can_move(d):
                    print(f"[BUGNAV] Emergency move: {d}")
                    ct.move(d)
                    self._soft_reset(ct)
                    return

            # If literally no moves possible
            print("[BUGNAV] Completely stuck — hard reset")
            self._hard_reset(ct)
            return

        max_turns_exceeded = self.turnsmovingtoobstacle > self.MAX_TURNS_ON_WALL
        print(f"[BUGNAV WALL] Turn count check: turnsmovingtoobstacle={self.turnsmovingtoobstacle} > MAX_TURNS_ON_WALL={self.MAX_TURNS_ON_WALL} = {max_turns_exceeded}")
        if max_turns_exceeded:
            print(f"[BUGNAV WALL] Exceeded max turns on wall, performing hard reset")
            self._hard_reset(ct)