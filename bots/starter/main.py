import random

from cambc import Controller, Direction, EntityType, GameConstants, Environment, Position
from scanning import *
from core import *
from builder import *
from bugnav import *
from sentinel import sentinelrun

# non-centre directions
DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]

class Player:
    def __init__(self):
        #the new nav

        self.bugnav= BugNav()


        #moveman
        self.movemanrotateright=True
        self.movedir=None #direction
        self.forbidden= None #boolean array
        self.lastturnloc=None #position
        self.pushdir=Direction.CENTRE
        self.flyingids= set() 

        #TEAM ID (a or b)
        self.our_team = None
        #CORE MEMROY
        self.num_spawned = 0 # number of builder bots spawned so far (core)
        self.marker_spawned = False
        self.mirroredpoints= None
        self.enemycoord= None
        self.ourcoord= None
        self.localorepos= None
        self.enemyore= None
        self.symmetry= None
        self.sentinelsbuilt= 0
        self.sentinelsconnected=0
        self.nextsentinelpos= None
        self.lastsentineldir= None
        self.attack= None
        self.bridges= None
        self.snipe= []
        self.snipecoord= None
        # BUILDER BOT MEMORY
        self.bot_state = None
        self.mode = "ROOMBA"
        self.heading = random.choice(DIRECTIONS)
        self.target_ore = None
        self.target_greedy = None
        self.target_enemy_bridge = None
        self.hit_distance = 999999
        self.wall_follow_direction = None
        self.splitters_built = 0
        self.bug_start_dir = None
        self.current_target = None
        self.bridges_limit = 0
        self.wall_jump_landing = None
        self.wall_jump_active = False
        self.core_tiles = []
        self.axionite_foundary_states = 0
        self.temp_pos_A_foundary = None
        # SPLITTER & GUNNER MEMORY
        self.splitter_positions = []
        self.gunner_positions = []
        self.core_splitter_built = False
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
            #checking if the bot state is stillo none
            if self.bot_state is None:
                nearby_ids = ct.get_nearby_entities()

                for entity_id in nearby_ids:
                    if ct.get_entity_type(entity_id) == EntityType.CORE:
                        core_pos = ct.get_position(entity_id)
                        self.ourcoord = core_pos
                        self.core_tiles = [core_pos.add(Direction.NORTH), core_pos.add(Direction.SOUTH), core_pos.add(Direction.EAST), core_pos.add(Direction.WEST), core_pos.add(Direction.NORTHEAST), core_pos.add(Direction.NORTHWEST), core_pos.add(Direction.SOUTHEAST), core_pos.add(Direction.SOUTHWEST)]
                    if ct.get_entity_type(entity_id) == EntityType.MARKER:

                        self.our_team = ct.get_team(entity_id)
                        role_id = ct.get_marker_value(entity_id)

                        if role_id == 1:
                            self.bot_state = "HARVEST"
                        elif role_id == 2:
                            self.bot_state = "ATTACK"
                            self.mode = "GREEDY"
                        elif role_id == 3: # HEALER
                            self.bot_state = "HEALER"
                        
                        print(self.bot_state)
                        #break from searching any other entity, we got our role
                
                
            
            if self.bot_state == "HARVEST":
                builderrun(self, ct)
            elif self.bot_state == "ATTACK":
                builderrun(self, ct)
                print("fight sound effects :)")
            # Move towards a target
            # direction = ct.get_position().direction_to(ores)
            # if ct.can_move(direction):
            #     ct.move(direction)
        
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
        elif etype == EntityType.SENTINEL:
            sentinelrun(self,ct)
