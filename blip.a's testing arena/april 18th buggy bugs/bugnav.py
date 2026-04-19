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
        self.states= set()
        self.ct= None


    def moveto(self, ct: Controller, target: Position):
        self.ct= ct
        currentpos= self.ct.get_position()
        if target is None or distance_squared(currentpos, target)==0:
            return
        
        distbetweentargets= 0

        if self.prevtarget is None:
            self.resetPathFinding(True)
        else:
            distbetweentargets= distance_squared(self.prevtarget, target)

        self.prevtarget= target
        if distbetweentargets>2:
            self.resetPathFinding(True)
        elif distbetweentargets>0:
            self.softResetPathfinding()

        self.checkstates()

        d = distance_squared(currentpos, target)
        if d<self.mindisttotarget:
            self.resetPathFinding(False)
            self.mindisttotarget=d
            self.minloctotarget= currentpos
            self.states.clear()
            print("min dist achieved", self.mindisttotarget)

        dir = currentpos.direction_to(target)
        if self.lastObstacleFound is not None:
            dir= currentpos.direction_to(self.lastObstacleFound)

        if self.ct.can_move(dir):
            self.ct.move(dir)
            if self.lastObstacleFound is not None:
                self.turnsmovingtoobstacle+=1
                self.lastObstacleFound= currentpos.add(dir)
                if self.turnsmovingtoobstacle>= self.MAXTURNSMOVINGTOOBSTACLE or onmap(self.ct, self.lastObstacleFound):
                    self.resetPathFinding(False)
            return
        else:
            self.turnsmovingtoobstacle=0

        self.updateRot()

        for x in range(16):
            if self.ct.can_move(dir):
                self.ct.move(dir)
                return
            newloc= currentpos.add(dir)
            if onmap(self.ct, newloc.add(dir)):
                self.lastObstacleFound= currentpos.add(dir)

            if self.rotateright:
                dir= dir.rotate_right()
            else:
                dir= dir.rotate_left()

        if self.ct.can_move(dir):
            self.ct.move(dir)

    def resetPathFinding(self, resetrot: bool):
        self.turnsmovingtoobstacle=0
        self.lastObstacleFound=None 
        self.mindisttotarget= self.infinity 
        if resetrot:
            self.rotateright=None
        self.states.clear()
        if resetrot:
            print("[BugNav] resetting bugnav", resetrot)



    def softResetPathfinding(self):
        if self.minloctotarget is not None:
            dist = distance_squared(self.minloctotarget, self.prevtarget)
            currentdist= distance_squared(self.prevtarget, self.ct.get_position())
            if(dist<currentdist):
                self.mindisttotarget= dist
            else:
                self.mindisttotarget= currentdist
                self.minloctotarget= self.ct.get_position()
        else:
            self.resetPathFinding(False)
        print("[BugNav] soft reset bugnav")


    def checkstates(self):
        if self.lastObstacleFound==None:
            return 
        boolenc=0
        if self.rotateright is not None:
            if self.rotateright is True:
                boolenc= 0
            else:
                boolenc= 1

        currentpos= self.ct.get_position()
        directiontoobstacle= currentpos.direction_to(self.lastObstacleFound)
        code = (currentpos.x << 6) | currentpos.y | (boolenc << 15) | (self.directions[directiontoobstacle] << 12)
        if code in self.states :
            print(f"[BugNav] checkstate found repeat state code={code} - resetting pathfinding")
            self.resetPathFinding(False)
        else:
            self.states.add(code)
            print(f"[BugNav] checkstate added state code={code}")

    def updateRot(self):
        if self.rotateright==None:
            currentpos=self.ct.get_position()
            direction= currentpos.direction_to(self.prevtarget)
            directionleft= direction
            directionright= direction
            locationleft= currentpos
            locationright= currentpos
            for x in range(8):
                directionleft= directionleft.rotate_left()
                locationleft= locationleft.add(directionleft)
                if self.ct.can_move(directionleft):
                    print(f"[BugNav] updateRot found left move {directionleft} at step {x}")
                    break
            for x in range(8):
                directionright= directionright.rotate_right()
                locationright= locationright.add(directionright)
                if self.ct.can_move(directionright):
                    print(f"[BugNav] updateRot found right move {directionright} at step {x}")
                    break
            leftdist= distance_squared(locationleft, self.prevtarget)
            rightdist= distance_squared(locationright, self.prevtarget)
            print(f"[BugNav] updateRot leftdist={leftdist} rightdist={rightdist}")
            if leftdist < rightdist:
                self.rotateright=False
                print("[BugNav] updateRot choosing rotate left")
                return
            self.rotateright=True
            print("[BugNav] updateRot choosing rotate right")
            return

