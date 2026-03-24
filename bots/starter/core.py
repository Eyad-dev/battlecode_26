from scanning import *
import random
from cambc import Controller, Direction, EntityType, GameConstants, Environment, Position

builderstate= ["ATTACK", "HARVEST", "DEFENSE"]

DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]
def corerrun(self, ct):
    ores= scan_ore_vision(ct, GameConstants.CORE_VISION_RADIUS_SQ)
    if self.num_spawned <1 and ores :
        spawn_pos = ct.get_position().add(random.choice(DIRECTIONS))
        if ct.can_spawn(spawn_pos):
            ct.spawn_builder(spawn_pos)
            self.num_spawned += 1
            self.bot_state=builderstate[1]
            ores= scan_ore_vision(ct, GameConstants.CORE_VISION_RADIUS_SQ)
            print(ores)
    
    if self.attack_bots<3:
        spawn_pos = ct.get_position().add(random.choice(DIRECTIONS))
        if ct.can_spawn(spawn_pos):
            ct.spawn_builder(spawn_pos)
            self.attack_bots += 1
            self.bot_state=builderstate[0]
