import random
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



    turnsmovingtoobstacle: int = 0
    rotateright: bool = True
    lastObstacleFound: Position | None = None
    mindisttotarget: int = float("inf")
    prevtarget: Position | None = None
    minloctotarget: Position | None = None
    states= set()

    def __init__(self):

        BugNav.ct= None
        print("[BugNav] initialized")

    @staticmethod
    def moveto(ct: Controller, target: Position):
        BugNav.ct= ct
        print(f"[BugNav] moveto called: current_pos={ct.get_position()}, target={target}")
        if target is None or distance_squared(ct.get_position(), target)==0:
            print("[BugNav] moveto: target is None or already at target")
            return
        
        distbetweentargets= 0

        if BugNav.prevtarget is None:
            BugNav.resetPathFinding(True)
        else:
            distbetweentargets= distance_squared(BugNav.prevtarget, target)

        BugNav.prevtarget= target
        if distbetweentargets>2:
            BugNav.resetPathFinding(True)
        elif distbetweentargets>0:
            BugNav.softResetPathfinding()

        if BugNav.lastObstacleFound is not None:
            BugNav.checkstates()

        d = distance_squared(ct.get_position(), target)
        print(f"[BugNav] moveto: distance to target={d}, mindisttotarget={BugNav.mindisttotarget}")
        if d<BugNav.mindisttotarget:
            BugNav.resetPathFinding(False)
            BugNav.mindisttotarget=d
            BugNav.minloctotarget= ct.get_position()
            BugNav.states.clear()
            print("min dist achieved", BugNav.mindisttotarget)

        dir = ct.get_position().direction_to(target)
        if BugNav.lastObstacleFound is not None:
            dir= ct.get_position().direction_to(BugNav.lastObstacleFound)
        print(f"[BugNav] moveto: chosen dir={dir}, lastObstacleFound={BugNav.lastObstacleFound}")

        try_build_road(ct, ct.get_position().add(dir))
        
        if BugNav.ct.can_move(dir)  and ct.get_tile_env(ct.get_position().add(dir)) != Environment.ORE_TITANIUM and ct.get_tile_env(ct.get_position().add(dir)) != Environment.ORE_AXIONITE:
            BugNav.ct.move(dir)
            print(f"[BugNav] moveto: moved in dir={dir}")
            if BugNav.lastObstacleFound is not None:
                BugNav.turnsmovingtoobstacle+=1
                newloc= ct.get_position().add(dir)
                BugNav.lastObstacleFound= newloc
                if BugNav.turnsmovingtoobstacle>= BugNav.MAXTURNSMOVINGTOOBSTACLE or not onmap(BugNav.ct, BugNav.lastObstacleFound):
                    BugNav.resetPathFinding(False)
            return
        else:
            BugNav.turnsmovingtoobstacle=0
            print("[BugNav] moveto: cannot move in dir, starting rotation")

        BugNav.updateRot()

        for x in range(16):
            print(f"[BugNav] moveto: trying rotation {x}, dir={dir}")
            try_build_road(ct, ct.get_position().add(dir))
            if BugNav.ct.can_move(dir)  and ct.get_tile_env(ct.get_position().add(dir)) != Environment.ORE_TITANIUM and ct.get_tile_env(ct.get_position().add(dir)) != Environment.ORE_AXIONITE:
                BugNav.ct.move(dir)
                print(f"[BugNav] moveto: moved after rotation in dir={dir}")
                return
            newloc= ct.get_position().add(dir)
            if onmap(BugNav.ct, newloc.add(dir)):
                BugNav.lastObstacleFound= ct.get_position().add(dir)

            if BugNav.rotateright is True:
                dir = dir.rotate_right()
            elif BugNav.rotateright is False:
                dir = dir.rotate_left()

        print(f"[BugNav] moveto: after loop, final try dir={dir}")
        try_build_road(ct, ct.get_position().add(dir))
        if BugNav.ct.can_move(dir)  and ct.get_tile_env(ct.get_position().add(dir)) != Environment.ORE_TITANIUM and ct.get_tile_env(ct.get_position().add(dir)) != Environment.ORE_AXIONITE:
            BugNav.ct.move(dir)
            print(f"[BugNav] moveto: final move in dir={dir}")

    @staticmethod
    def resetPathFinding(resetrot: bool):
        BugNav.turnsmovingtoobstacle=0
        BugNav.lastObstacleFound=None 
        BugNav.mindisttotarget= BugNav.infinity 
        if resetrot:
            BugNav.rotateright=None
        BugNav.states.clear()
        if resetrot:
            print("[BugNav] resetting bugnav", resetrot)


    @staticmethod
    def softResetPathfinding():
        if BugNav.minloctotarget is not None:
            dist = distance_squared(BugNav.minloctotarget, BugNav.prevtarget)
            currentdist= distance_squared(BugNav.prevtarget, BugNav.ct.get_position())
            if(dist<currentdist):
                BugNav.mindisttotarget= dist
            else:
                BugNav.mindisttotarget= currentdist
                BugNav.minloctotarget= BugNav.ct.get_position()
        else:
            BugNav.resetPathFinding(False)
        print("[BugNav] soft reset bugnav")

    @staticmethod
    def checkstates():
        if BugNav.lastObstacleFound is None:
            return

        currentpos = BugNav.ct.get_position()
        directiontoobstacle = currentpos.direction_to(BugNav.lastObstacleFound)

        # Encode cleanly as tuple (simple + safe)
        state = (
            currentpos.x,
            currentpos.y,
            BugNav.directions[directiontoobstacle],
            BugNav.rotateright
        )

        if state in BugNav.states:
            print("[BugNav] LOOP DETECTED → resetting")
            BugNav.resetPathFinding(True)
        else:
            BugNav.states.add(state)

    @staticmethod
    def updateRot():
        if BugNav.rotateright==None:
            currentpos=BugNav.ct.get_position()
            direction= currentpos.direction_to(BugNav.prevtarget)
            directionleft= direction
            directionright= direction
            locationleft= currentpos
            locationright= currentpos
            for x in range(8):
                directionleft= directionleft.rotate_left()
                locationleft= locationleft.add(directionleft)
                if BugNav.ct.can_move(directionleft):
                    print(f"[BugNav] updateRot found left move {directionleft} at step {x}")
                    break
            for x in range(8):
                directionright= directionright.rotate_right()
                locationright= locationright.add(directionright)
                if BugNav.ct.can_move(directionright):
                    print(f"[BugNav] updateRot found right move {directionright} at step {x}")
                    break
            leftdist= distance_squared(locationleft, BugNav.prevtarget)
            rightdist= distance_squared(locationright, BugNav.prevtarget)
            print(f"[BugNav] updateRot leftdist={leftdist} rightdist={rightdist}")
            if leftdist < rightdist:
                BugNav.rotateright=False
                print("[BugNav] updateRot choosing rotate left")
                return
            BugNav.rotateright=True
            print("[BugNav] updateRot choosing rotate right")
            return

