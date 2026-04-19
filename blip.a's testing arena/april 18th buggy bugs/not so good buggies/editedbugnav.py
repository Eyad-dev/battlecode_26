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
        self.currentDir = None
        self.turnsmovingtoobstacle = 0
        self.states = set()
        self.MAXTURNS = 3  # equivalent of MAX_TURNS_MOVING_TO_OBSTACLE

    

    def resetPathFinding(self, ct:Controller, resetrot: bool):
        self.turnsmovingtoobstacle=0
        self.lastObstacleFound=None #(Position)
        self.mindisttotarget= float('inf') #int
        self.minloctotarget = None
        if resetrot:
            self.rotateright=None
            print(f"[BugNav] resetPathFinding(resetrot=True) prevtarget={self.prevtarget} lastObstacleFound={self.lastObstacleFound}")
        else:
            print(f"[BugNav] resetPathFinding(resetrot=False) prevtarget={self.prevtarget} lastObstacleFound={self.lastObstacleFound}")
        self.states.clear()

    def softResetPathfinding(self, ct: Controller):
        print(f"[BugNav] softResetPathfinding prevtarget={self.prevtarget} minloctotarget={self.minloctotarget} mindisttotarget={self.mindisttotarget}")
        if self.minloctotarget is not None:
            dist = distance_squared(self.minloctotarget, self.prevtarget)
            currentdist= distance_squared(self.prevtarget, ct.get_position())
            print(f"[BugNav] softReset computed dist={dist} currentdist={currentdist}")
            if(dist<currentdist):
                self.mindisttotarget= dist
                print(f"[BugNav] softReset keeps mindisttotarget={self.mindisttotarget}")
            else:
                self.mindisttotarget= currentdist
                self.minloctotarget=ct.get_position()
                print(f"[BugNav] softReset updated mindisttotarget={self.mindisttotarget} minloctotarget={self.minloctotarget}")
        else:
            BugNav.resetPathFinding(self,ct, False)
        print("[BugNav] soft reset bugnav")

    def checkstate(self, ct: Controller):
        if self.lastObstacleFound==None:
            print("[BugNav] checkstate skipped: no lastObstacleFound")
            return 
        boolenc=0
        if self.rotateright is not None:
            if self.rotateright is True:
                boolenc= 0
            else:
                boolenc= 1

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

        currentpos= ct.get_position()
        directiontoobstacle= currentpos.direction_to(self.lastObstacleFound)
        code = (currentpos.x << 6) \
        | currentpos.y \
        | (boolenc << 15) \
        | (dir_map[directiontoobstacle] << 12)
        print(f"[BugNav] checkstate currentpos={currentpos} lastObstacleFound={self.lastObstacleFound} directiontoobstacle={directiontoobstacle} rotateright={self.rotateright} code={code} states_size={len(self.states)}")
        if code in self.states :
            print(f"[BugNav] checkstate found repeat state code={code} - resetting pathfinding")
            BugNav.resetPathFinding(self,ct, False)
        else:
            self.states.add(code)
            print(f"[BugNav] checkstate added state code={code}")

    def updateRot(self, ct:Controller):
        if self.rotateright==None:
            currentpos=ct.get_position()
            direction= currentpos.direction_to(self.prevtarget)
            directionleft= direction
            directionright=direction
            locationleft= currentpos
            locationright= currentpos
            print(f"[BugNav] updateRot computing rotation from currentpos={currentpos} prevtarget={self.prevtarget} direction={direction}")
            for x in range(8):
                directionleft= directionleft.rotate_left()
                locationleft= locationleft.add(directionleft)
                if ct.can_move(directionleft):
                    print(f"[BugNav] updateRot found left move {directionleft} at step {x}")
                    break
            for x in range(8):
                directionright= directionright.rotate_right()
                locationright= locationright.add(directionright)
                if ct.can_move(directionright):
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

        
    def move(self, ct: Controller, dir: Direction):
        print(f"[BugNav] move called dir={dir} can_move={ct.can_move(dir)}")
        if ct.can_move(dir):
            ct.move(dir)


    def move_towards(self,ct: Controller,target: Position):
        if target==None:
            print("[BugNav] move_towards skipped: target=None")
            return
        currentpos=ct.get_position()
        dist_sq = distance_squared(currentpos, target)
        if dist_sq==0:
            print(f"[BugNav] move_towards skipped: already at target {target}")
            return
        
        distbetweentargets=0
        if self.prevtarget ==None:
            print(f"[BugNav] move_towards initial target assignment target={target}")
            BugNav.resetPathFinding(self, ct, True)
        else:
            distbetweentargets= distance_squared(self.prevtarget, target)
            print(f"[BugNav] move_towards prevtarget={self.prevtarget} target={target} distbetweentargets={distbetweentargets}")
        
        self.prevtarget= target
        if distbetweentargets>2:
            print(f"[BugNav] move_towards target jumped far: resetting navigation")
            BugNav.resetPathFinding(self, ct, True)
        elif  distbetweentargets>0:
            BugNav.softResetPathfinding(self,ct)

        BugNav.checkstate(self,ct)

        dist_sq = distance_squared(currentpos, target)
        print(f"[BugNav] move_towards currentpos={currentpos} target={target} dist_sq={dist_sq} mindisttotarget={self.mindisttotarget} lastObstacleFound={self.lastObstacleFound} rotateright={self.rotateright} turnsmovingtoobstacle={self.turnsmovingtoobstacle}")
        if dist_sq < self.mindisttotarget:
            self.mindisttotarget = dist_sq
            self.minloctotarget = currentpos
            # only reset if not currently wall-following
            if self.lastObstacleFound is None:
                BugNav.resetPathFinding(self, ct, False)
        dir= currentpos.direction_to(target)
        # in the circumnavigation loop, use currentDir if available
        dir = self.currentDir if self.currentDir is not None else currentpos.direction_to(target)
        # if self.lastObstacleFound is not None:
        #     dir = currentpos.direction_to(self.lastObstacleFound)
        #     print(f"[BugNav] move_towards using obstacle direction {dir} towards lastObstacleFound={self.lastObstacleFound}")
        # else:
        #     print(f"[BugNav] move_towards using direct direction {dir} towards target")

        nextpos = currentpos.add(dir)
        can_move = ct.can_move(dir)
        passable = ct.is_tile_passable(nextpos)
        print(f"[BugNav] move_towards candidate dir={dir} nextpos={nextpos} can_move={can_move} passable={passable}")
        if (can_move and passable):
            BugNav.move(self,ct,dir)
            if self.lastObstacleFound is not None:
                self.turnsmovingtoobstacle+=1
                width = ct.get_map_width()
                height = ct.get_map_height()
                print(f"[BugNav] move_towards moving along obstacle, turnsmovingtoobstacle={self.turnsmovingtoobstacle} lastObstacleFound={self.lastObstacleFound}")
                if self.turnsmovingtoobstacle>= self.MAXTURNS or not (0 <= self.lastObstacleFound.x < width and 0 <= self.lastObstacleFound.y < height) :
                    print("[BugNav] move_towards obstacle tracking expired, resetting pathfinding")
                    BugNav.resetPathFinding(self,ct,False)
            return
        else:
            self.turnsmovingtoobstacle=0
            print(f"[BugNav] move_towards cannot move directly; resetting turnsmovingtoobstacle to 0")

        BugNav.updateRot(self,ct)

        width = ct.get_map_width()
        height = ct.get_map_height()
        print(f"[BugNav] move_towards starting obstacle circumnavigation loop rotateright={self.rotateright}")
        for x in range(8):
            nextpos= currentpos.add(dir)
            can_move = ct.can_move(dir)
            passable = ct.is_tile_passable(nextpos)
            print(f"[BugNav] circumnavigate step={x} dir={dir} nextpos={nextpos} can_move={can_move} passable={passable}")
            if can_move and passable:
                self.currentDir = dir
                BugNav.move(self,ct, dir)
                return
            newpos= currentpos.add(dir)
            if not (0 <= newpos.x < width and 0 <= newpos.y < height):
                self.rotateright= not self.rotateright
                print(f"[BugNav] circumnavigate hit border, flip rotateright to {self.rotateright}")
            else:
                self.lastObstacleFound= newpos
                print(f"[BugNav] circumnavigate obstacle found at {newpos}")
            if self.rotateright:
                dir= dir.rotate_right()
            else:
                dir= dir.rotate_left()

        final_nextpos = currentpos.add(dir)
        print(f"[BugNav] circumnavigate finished loop final dir={dir} final_nextpos={final_nextpos} can_move={ct.can_move(dir)} passable={ct.is_tile_passable(final_nextpos)}")
        if ct.can_move(dir) and ct.is_tile_passable(final_nextpos):
            BugNav.move(self,ct, dir)
    
            
        
        
        
