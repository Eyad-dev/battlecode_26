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
        self.MAXTURNS = 3  # equivalent of MAX_TURNS_MOVING_TO_OBSTACLE

    

    def resetPathFinding(self, ct:Controller, resetrot: bool):
        self.turnsmovingtoobstacle=0
        self.lastObstacleFound=None #(Position)
        self.mindisttotarget= float('inf') #int
        if resetrot:
            self.rotateright=None
            print("resetting bugnav")
        self.states.clear()

    def softResetPathfinding(self, ct: Controller):
        if self.minloctotarget is not None:
            dist = distance_squared(self.minloctotarget, self.prevtarget)
            currentdist= distance_squared(self.prevtarget, ct.get_position())
            if(dist<currentdist):
                self.mindisttotarget= dist
            else:
                self.mindisttotarget= currentdist
                self.minloctotarget=ct.get_position()
        else:
            BugNav.resetPathFinding(self,ct, False)
        print("soft reset bugnav")

    def checkstate(self, ct: Controller):
        if self.lastObstacleFound==None:
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
        if code in self.states :
            BugNav.resetPathFinding(self,ct, False)
        else:
            self.states.add(code)

    def updateRot(self, ct:Controller):
        if self.rotateright==None:
            currentpos=ct.get_position()
            direction= currentpos.direction_to(self.prevtarget)
            directionleft= direction
            directionright=direction
            locationleft= currentpos
            locationright= currentpos
            for x in range(8):
                directionleft= directionleft.rotate_left()
                locationleft= locationleft.add(directionleft)
                if ct.can_move(directionleft):
                    break
            for x in range(8):
                directionright= directionright.rotate_right()
                locationright= locationright.add(directionright)
                if ct.can_move(directionright):
                    break
            if distance_squared(locationleft, self.prevtarget)< distance_squared(locationright, self.prevtarget):
                self.rotateright=False
                return
            self.rotateright=True
            return

        
    def move(self, ct: Controller, dir: Direction):
        if ct.can_move(dir):
            ct.move(dir)


    def move_towards(self,ct: Controller,target: Position):
        if target==None:
            return
        currentpos=ct.get_position()
        dist_sq = distance_squared(currentpos, target)
        if dist_sq==0:
            return
        
        distbetweentargets=0
        if self.prevtarget ==None:
            BugNav.resetPathFinding(self, ct, True)
        else:
            distbetweentargets= distance_squared(self.prevtarget, target)
        
        self.prevtarget= target
        if distbetweentargets>2:
            BugNav.resetPathFinding(self, ct, True)
        elif  distbetweentargets>0:
            BugNav.softResetPathfinding(self,ct)

        BugNav.checkstate(self,ct)

        dist_sq = distance_squared(currentpos, target)
        if dist_sq< self.mindisttotarget:
            BugNav.resetPathFinding(self,ct,False)
            self.mindisttotarget=dist_sq
            self.minloctotarget= currentpos

        dir= currentpos.direction_to(target)
        if self.lastObstacleFound is not None:
            dir = currentpos.direction_to(self.lastObstacleFound)

        if (ct.can_move(dir) and ct.is_tile_passable(ct.get_position().add(dir))):
            BugNav.move(self,ct,dir)
            if self.lastObstacleFound is not None:
                self.turnsmovingtoobstacle+=1
                self.lastObstacleFound=currentpos.add(dir)
                width = ct.get_map_width()
                height = ct.get_map_height()
                if self.turnsmovingtoobstacle>= self.MAXTURNS or not (0 <= self.lastObstacleFound.x < width and 0 <= self.lastObstacleFound.y < height) :
                    BugNav.resetPathFinding(self,ct,False)
            return
        else:
            self.turnsmovingtoobstacle=0

        BugNav.updateRot(self,ct)

        width = ct.get_map_width()
        height = ct.get_map_height()
        for x in range(8):
            if ct.can_move(dir) and ct.is_tile_passable(ct.get_position().add(dir)):
                BugNav.move(self,ct, dir)
                return
            newpos= currentpos.add(dir)
            if not (0 <= newpos.x < width and 0 <= newpos.y < height):
                self.rotateright= not self.rotateright
            else:
                self.lastObstacleFound= newpos
            if self.rotateright:
                dir= dir.rotate_right()
            else:
                dir= dir.rotate_left()

        if ct.can_move(dir) and ct.is_tile_passable(ct.get_position().add(dir)):
            BugNav.move(self,ct, dir)
    
            
        
        
        
