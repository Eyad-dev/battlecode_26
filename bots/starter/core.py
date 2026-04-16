from scanning import *
import random
from cambc import Controller, Direction, EntityType, GameConstants, Environment, Position
from healer import *

builderstate= ["ATTACK", "HARVEST", "HEALER"]

DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]
DIAGONAL_DIRS = [
    Direction.NORTHEAST, Direction.SOUTHEAST, Direction.SOUTHWEST, Direction.NORTHWEST,
]

def corerrun(self, ct: Controller):
    self.turn_counter += 1
    spawn_pos = ct.get_position().add(random.choice(DIRECTIONS))
    # for d in DIAGONAL_DIRS:
    #     if (self.axioniter_spawned == False and self.turn_counter >= 1500):
    #         role_id=67 #axioniter 
    #         writemarker(self,ct,role_id)
    #         test_pos2 = ct.get_position().add(d)
    #         if (ct.can_spawn(test_pos2)):
    #             ct.spawn_builder(test_pos2)
    #             self.axioniter_spawned = True
    #             self.num_spawned += 1
    #             break
   
    if self.num_spawned < 4:
            if self.num_spawned <=1 :
                 role_id = 4 # AXIONITER
            elif self.num_spawned <= 0:
                 role_id = 1 # HARVESTER               
            else:
                 role_id = 2 # ATTACKER
            
            if ct.can_spawn(spawn_pos):
                ct.spawn_builder(spawn_pos)
                self.num_spawned += 1
    
            writemarker(self,ct,role_id)
    elif self.num_spawned == 2:
         role_id = 1
         writemarker(self,ct,role_id)
    
    if (ct.get_hp() < ct.get_max_hp() and self.healers_spawned < 5):
        role_id = 3 # HEALER
        for d in DIRECTIONS:
            test_pos = ct.get_position().add(d)
            if ct.can_spawn(test_pos):
                ct.spawn_builder(test_pos)
                self.healers_spawned += 1
                writemarker(self,ct,role_id)
                break
            
            


    

def writemarker(self,ct,role_id):
    # Place marker on a diagonal to avoid splitter positions
    for d in DIAGONAL_DIRS:
        test_pos = ct.get_position().add(d).add(d)
        if ct.can_place_marker(test_pos):
            ct.place_marker(test_pos, role_id)
            break