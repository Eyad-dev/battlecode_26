import random
from cambc import Controller, Direction, GameConstants, Position
from helper import *


class BugNav:
    def __init__(self):
        self.prevtarget = None
        self.lastObstacleFound = None
        self.mindisttotarget = float('inf')
        self.minloctotarget = None
        self.rotateright = None
        self.turnsmovingtoobstacle = 0
        self.states = set()
        self.currentDir = None
        self.MAXTURNS = 3

    def check_loop(self, ct: Controller):
        if self.lastObstacleFound is None:
            return False

        currentpos = ct.get_position()

        dir_map = {
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

        direction = currentpos.direction_to(self.lastObstacleFound)

        rot = 0 if self.rotateright else 1 if self.rotateright is not None else 2

        code = (currentpos.x << 16) | (currentpos.y << 8) | (rot << 4) | dir_map[direction]

        if code in self.states:
            print("[LOOP DETECTED] resetting bugnav")
            self.resetPathFinding(ct, True)
            return True

        self.states.add(code)
        return False

    def resetPathFinding(self, ct: Controller, resetrot: bool):
        self.turnsmovingtoobstacle = 0
        self.lastObstacleFound = None
        self.mindisttotarget = float('inf')
        self.currentDir = None
        if resetrot:
            self.rotateright = None
            print("[RESET] full reset")
        self.states.clear()

    def move(self, ct: Controller, dir: Direction):
        if ct.can_move(dir):
            print(f"[MOVE] moving {dir}")
            ct.move(dir)

    def updateRot(self, ct: Controller):
        if self.rotateright is None:
            currentpos = ct.get_position()
            direction = currentpos.direction_to(self.prevtarget)

            left = direction
            right = direction
            locL = currentpos
            locR = currentpos

            for _ in range(8):
                left = left.rotate_left()
                locL = locL.add(left)
                if ct.can_move(left):
                    break

            for _ in range(8):
                right = right.rotate_right()
                locR = locR.add(right)
                if ct.can_move(right):
                    break

            if distance_squared(locL, self.prevtarget) < distance_squared(locR, self.prevtarget):
                self.rotateright = False
            else:
                self.rotateright = True

            print(f"[ROT] choosing {'RIGHT' if self.rotateright else 'LEFT'}")

    def move_towards(self, ct: Controller, target: Position):
        if target is None:
            return

        currentpos = ct.get_position()

        if self.prevtarget is None:
            self.resetPathFinding(ct, True)

        self.prevtarget = target

        print(f"\n[TURN] pos={currentpos} target={target}")
        print(f"[STATE] currentDir={self.currentDir} rotR={self.rotateright} obstacle={self.lastObstacleFound}")

        if self.check_loop(ct):
            return

        # === TRY DIRECT MOVE FIRST ===
        direct_dir = currentpos.direction_to(target)
        if ct.can_move(direct_dir) and ct.is_tile_passable(currentpos.add(direct_dir)):
            print("[DIRECT] moving toward target")
            self.currentDir = direct_dir
            self.lastObstacleFound = None
            self.turnsmovingtoobstacle = 0
            self.move(ct, direct_dir)
            return

        print("[BLOCKED] can't go directly")

        # === START WALL FOLLOWING ===
        self.updateRot(ct)

        if self.currentDir is None:
            self.currentDir = direct_dir

        dir = self.currentDir

        width = ct.get_map_width()
        height = ct.get_map_height()

        for i in range(8):
            print(f"[LOOP {i}] trying dir={dir}")

            # Try exit again (important!)
            direct_dir = currentpos.direction_to(target)
            if ct.can_move(direct_dir) and ct.is_tile_passable(currentpos.add(direct_dir)):
                print("[EXIT] found path to target")
                self.currentDir = direct_dir
                self.lastObstacleFound = None
                self.turnsmovingtoobstacle = 0
                self.move(ct, direct_dir)
                return

            # 🔥 TRY CURRENT WALL DIRECTION
            if ct.can_move(dir) and ct.is_tile_passable(currentpos.add(dir)):
                print(f"[WALL] moving along wall via {dir}")
                self.currentDir = dir
                self.move(ct, dir)
                return

            # otherwise rotate
            newpos = currentpos.add(dir)

            if 0 <= newpos.x < width and 0 <= newpos.y < height:
                if self.lastObstacleFound is None:
                    self.lastObstacleFound = newpos
            else:
                print("[EDGE] hit map boundary, stopping rotation")
                break

            if self.rotateright:
                dir = dir.rotate_right()
            else:
                dir = dir.rotate_left()

            self.currentDir = dir

        # fallback (rare)
        if ct.can_move(dir) and ct.is_tile_passable(currentpos.add(dir)):
            print("[FALLBACK] moving last dir")
            self.move(ct, dir)
        else:
            print("[STUCK] no valid moves found")