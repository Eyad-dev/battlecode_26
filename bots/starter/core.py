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
    healers_spawned = 0
    spawn_pos = ct.get_position().add(random.choice(DIRECTIONS))
    ores= scan_ore_vision(ct, GameConstants.CORE_VISION_RADIUS_SQ)
    if self.num_spawned < 1:
            if self.num_spawned <= 1:
                 role_id = 1 # HARVESTER
            else:
                 role_id = 2 # ATTACKER
                 
            
            
            if self.marker_spawned == False:
                # Place marker on a diagonal to avoid splitter positions
                for d in DIAGONAL_DIRS:
                    test_pos = ct.get_position().add(d).add(d)

                    if ct.can_place_marker(test_pos):
                         ct.place_marker(test_pos, role_id)
                         self.marker_spawned = True
                         break
            else:
                if ct.can_spawn(spawn_pos):
                    ct.spawn_builder(spawn_pos)
                    self.num_spawned += 1
                    self.marker_spawned = False
    if (ct.get_hp() < ct.get_max_hp() and healers_spawned < 10):
         role_id = 3 # HEALER
         if ct.can_spawn(spawn_pos):
              ct.spawn_builder(spawn_pos)
              healers_spawned += 1
              healerrun(self, ct)
        
         

