from scanning import *
import random
from cambc import Controller, Direction, EntityType, GameConstants, Environment, Position

builderstate= ["ATTACK", "HARVEST", "DEFENSE"]

DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]
def corerrun(self, ct: Controller):
    ores= scan_ore_vision(ct, GameConstants.CORE_VISION_RADIUS_SQ)
    if self.num_spawned < 6:
            if self.num_spawned <= 2:
                 role_id = 1 # HARVESTER
            else:
                 role_id = 2 # ATTACKER
            
            spawn_pos = ct.get_position().add(random.choice(DIRECTIONS))
            marker_pos = ct.get_position().add(Direction.WEST)
            if self.marker_spawned == False:
                if ct.can_place_marker(marker_pos.add(Direction.WEST)):
                        ct.place_marker(marker_pos.add(Direction.WEST), role_id)
                        self.marker_spawned = True
            else:
                if ct.can_spawn(spawn_pos):
                    ct.spawn_builder(spawn_pos)
                    self.num_spawned += 1
                    self.marker_spawned = False

