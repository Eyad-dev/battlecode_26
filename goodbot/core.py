from scanning import *
import random
from cambc import Controller, Direction, EntityType, GameConstants, Environment, Position
from healer import *

builderstate = ["ATTACK", "HARVEST", "HEALER"]

DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]
DIAGONAL_DIRS = [
    Direction.NORTHEAST, Direction.SOUTHEAST, Direction.SOUTHWEST, Direction.NORTHWEST,
]
HEALER_DIRS = [Direction.NORTH, Direction.SOUTH, Direction.WEST]
def corerrun(self, ct: Controller):
    core_pos = ct.get_position()
    self.turn_counter += 1
    print(self.turn_counter)

    if self.turn_counter == 1:
         spawnbot(ct, core_pos.add(Direction.SOUTHEAST))
         print("ATTACKER")
    elif self.turn_counter == 2:
         spawnbot(ct, core_pos.add(Direction.NORTHWEST))
         print("HARVESTER")
    elif self.turn_counter == 50:
         spawnbot(ct, core_pos.add(Direction.NORTHWEST))
         print("HARVESTER")
    if self.turn_counter == 1000:
         spawnbot(ct, core_pos.add(Direction.NORTHEAST))
         print("AXIONITER")
    elif self.turn_counter == 100:
         spawnbot(ct, core_pos.add(Direction.SOUTHEAST))
         print("ATTACKER")
    elif self.turn_counter == 200:
         spawnbot(ct, core_pos.add(Direction.SOUTHEAST))
         print("ATTACKER")
    elif self.turn_counter == 202:
        spawnbot(ct, core_pos.add(Direction.SOUTHWEST))
        print("SNIPER")
    elif self.turn_counter == 3:
        spawnbot(ct, core_pos.add(Direction.EAST))
        print("PATROLHEALER")
    elif self.turn_counter == 14:
        spawnbot(ct, core_pos.add(Direction.EAST))
        print("PATROLHEALER")

    if (ct.get_hp() < ct.get_max_hp()):  # HEALER
        for d in HEALER_DIRS:
            test_pos = ct.get_position().add(d)
            if ct.can_spawn(test_pos):
                ct.spawn_builder(test_pos)
                break


def spawnbot(ct, pos):
    if ct.can_spawn(pos):
        ct.spawn_builder(pos)