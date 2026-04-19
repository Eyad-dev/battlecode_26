import random
from cambc import *
from helper import *

class BugNav:

    infinity = float('inf')
    MAXTURNSMOVINGTOOBSTACLE = 3

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
        self.rotateright: bool = True
        self.lastObstacleFound: Position | None = None
        self.mindisttotarget: int = float("inf")
        self.prevtarget: Position | None = None
        self.minloctotarget: Position | None = None
        self.states = set()
        self.ct = None

    def moveto(self, ct: Controller, target: Position):
        self.ct = ct
        if target is None or distance_squared(ct.get_position(), target) == 0:
            return

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

        if self.lastObstacleFound is not None:
            self.checkstates()

        d = distance_squared(ct.get_position(), target)
        if d < self.mindisttotarget:
            self.resetPathFinding(False)
            self.mindisttotarget = d
            self.minloctotarget = ct.get_position()
            self.states.clear()

        dir = ct.get_position().direction_to(target)
        if self.lastObstacleFound is not None:
            dir = ct.get_position().direction_to(self.lastObstacleFound)

        try_build_road(ct, ct.get_position().add(dir))

        if self.ct.can_move(dir):
            self.ct.move(dir)
            # BUG 1 FIX: don't overwrite lastObstacleFound with our own position.
            # Just count turns; reset if we've moved far enough past the obstacle.
            if self.lastObstacleFound is not None:
                self.turnsmovingtoobstacle += 1
                if (self.turnsmovingtoobstacle >= self.MAXTURNSMOVINGTOOBSTACLE
                        or not onmap(self.ct, self.lastObstacleFound)):
                    self.resetPathFinding(False)
            return
        else:
            self.turnsmovingtoobstacle = 0

        self.updateRot()

        for x in range(16):
            try_build_road(ct, ct.get_position().add(dir))
            if self.ct.can_move(dir):
                self.ct.move(dir)
                # BUG 3 FIX: after hugging moves, record the blocked face we just
                # rotated away from as the new obstacle anchor.
                blocked = ct.get_position().add(
                    dir.rotate_left() if self.rotateright else dir.rotate_right()
                )
                if onmap(self.ct, blocked):
                    self.lastObstacleFound = blocked
                return

            newloc = ct.get_position().add(dir)
            # BUG 2 FIX: check newloc itself, not newloc.add(dir).
            if onmap(self.ct, newloc):
                self.lastObstacleFound = newloc

            if self.rotateright:
                dir = dir.rotate_right()
            else:
                dir = dir.rotate_left()

        try_build_road(ct, ct.get_position().add(dir))
        if self.ct.can_move(dir):
            self.ct.move(dir)

    def resetPathFinding(self, resetrot: bool):
        self.turnsmovingtoobstacle = 0
        self.lastObstacleFound = None
        self.mindisttotarget = self.infinity
        # BUG 5 FIX: always clear minloctotarget so soft reset can't use stale data.
        self.minloctotarget = None
        if resetrot:
            self.rotateright = None
        self.states.clear()

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

    def checkstates(self):
        if self.lastObstacleFound is None:
            return
        currentpos = self.ct.get_position()
        directiontoobstacle = currentpos.direction_to(self.lastObstacleFound)
        state = (
            currentpos.x,
            currentpos.y,
            self.directions[directiontoobstacle],
            self.rotateright
        )
        if state in self.states:
            self.resetPathFinding(True)
        else:
            self.states.add(state)

    def updateRot(self):
        if self.rotateright is not None:
            return
        currentpos = self.ct.get_position()
        direction = currentpos.direction_to(self.prevtarget)

        # BUG 4 FIX: probe candidate directions from currentpos each step,
        # don't accumulate locationleft/right across iterations.
        dirleft = direction
        diright = direction
        locationleft = currentpos
        locationright = currentpos

        for x in range(8):
            dirleft = dirleft.rotate_left()
            if self.ct.can_move(dirleft):
                locationleft = currentpos.add(dirleft)
                break

        for x in range(8):
            diright = diright.rotate_right()
            if self.ct.can_move(diright):
                locationright = currentpos.add(diright)
                break

        leftdist = distance_squared(locationleft, self.prevtarget)
        rightdist = distance_squared(locationright, self.prevtarget)

        self.rotateright = leftdist >= rightdist