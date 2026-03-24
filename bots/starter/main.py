import random

from cambc import Controller, Direction, EntityType, GameConstants, Environment, Position
from scanning import *
from core import *



# non-centre directions
DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]

class Player:
    def __init__(self):
        self.num_spawned = 0 # number of builder bots spawned so far (core)
        self.heading = random.choice(DIRECTIONS)
    def run(self, ct: Controller) -> None:
        etype = ct.get_entity_type()
        if etype == EntityType.CORE:
            corerrun(self, ct)


            #40x40 grid
            #Core A (11, 25)
            #Core B (28,14)
            #Core B ((40-11)-1, (40-25)-1)
            #Opponent core equals
            #Core ((grid_length - CoreAx)-1 , (grid_height - CoreAy) -1)
        elif etype == EntityType.BUILDER_BOT:
            # Move towards a target
            # direction = ct.get_position().direction_to(ores)
            # if ct.can_move(direction):
            #     ct.move(direction)
            
            ores = scan_ore_vision(ct, GameConstants.BUILDER_BOT_VISION_RADIUS_SQ)

            if(ores):
                for i in ores:
                    print(i)
            move_pos = ct.get_position().add(self.heading)
            if ct.can_build_road(move_pos):
                ct.build_road(move_pos)
                
            # Try to move forward
            if ct.can_move(self.heading):
                ct.move(self.heading)
            
            else:
                self.heading = random.choice(DIRECTIONS)
            # # if we are adjacent to an ore tile, build a harvester on it
            # for d in Direction:
            #     check_pos = ct.get_position().add(d)
            #     if ct.can_build_harvester(check_pos):
            #         ct.build_harvester(check_pos)
            #         break
            
            # # move in a random direction
            # move_dir = random.choice(DIRECTIONS)
            # move_pos = ct.get_position().add(move_dir)
            # # we need to place a conveyor or road to stand on, before we can move onto a tile
            # if ct.can_build_road(move_pos):
            #     ct.build_road(move_pos)
            # if ct.can_move(move_dir):
            #     ct.move(move_dir)

            # # place a marker on an adjacent tile with the current round number
            # marker_pos = ct.get_position().add(random.choice(DIRECTIONS))
            # if ct.can_place_marker(marker_pos):
            #     ct.place_marker(marker_pos, ct.get_current_round())
