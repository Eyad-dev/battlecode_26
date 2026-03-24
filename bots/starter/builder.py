from scanning import *
import random
from cambc import Controller, Direction, EntityType, GameConstants, Environment, Position

DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]
CLOCKWISE_DIRS = [
    Direction.NORTH,
    Direction.NORTHEAST,
    Direction.EAST,
    Direction.SOUTHEAST,
    Direction.SOUTH,
    Direction.SOUTHWEST,
    Direction.WEST,
    Direction.NORTHWEST
]
STRAIGHT_DIRS = [
    Direction.NORTH, Direction.EAST, 
    Direction.SOUTH, Direction.WEST
]

def rotate(current_dir, steps_clockwise):
    # 1 for 45 degrees right
    # -2 for 90 degrees left
    current_index = CLOCKWISE_DIRS.index(current_dir)
    new_index = (current_index + steps_clockwise) % 8

    return CLOCKWISE_DIRS[new_index]


def builderrun(self, ct: Controller):
    current_pos = ct.get_position()
    
    #Randomly move around till you find some ores
    if self.mode == "ROOMBA":
        ores = scan_ore_vision(ct, GameConstants.BUILDER_BOT_VISION_RADIUS_SQ)
        if ores:
            self.target_ore = ores[0]
            self.mode = "GREEDY"
    
    #Check if we are standing next to an ore
    if self.target_ore:
        distance_to_ore_sq = (current_pos.x - self.target_ore.x)**2 + (current_pos.y - self.target_ore.y)**2

            #If distance equals 1 or 2 then its adjacent
        if distance_to_ore_sq <= 2:
            if ct.can_build_harvester(self.target_ore):
                ct.build_harvester(self.target_ore)
                 #LETSA GO, WE BUILT OUR FIRST HARVERSTER ON OUR FIRST ORE
                self.mode = "ROOMBA"
                self.target_ore = None
            else:
                self.mode = "ROOMBA"
                self.target_ore = None
            return
        #   ===========================================================================================================================    
        #If we aren't adjacent to the ore yet
    if self.mode == "BUG":
        current_dist_sq = (current_pos.x - self.target_ore.x)**2 + (current_pos.y - self.target_ore.y)**2
        print("BUG")
        print(current_dist_sq)
        print(self.hit_distance)
        # The Release Condition: Did we get closer than when we got stuck?
        if current_dist_sq < self.hit_distance:
            self.mode = "GREEDY"
            self.hit_distance = 999999
        else:
            print("We rotating")
            # The Wall Sweep: Look 90 degrees left, then sweep clockwise
            check_ore_direction = current_pos.direction_to(self.target_ore)
            print(check_ore_direction)
            print(self.heading)
            test_dir = rotate(self.wall_follow_direction, -2)
            if (current_pos.x - self.target_ore.x == 0 or current_pos.y - self.target_ore.y == 0) or (current_pos.x - self.target_ore.x == current_pos.y - self.target_ore.y):
            # if (current_pos.x - self.target_ore.x == 0 or current_pos.y - self.target_ore.y == 0):
                temp_dir = rotate(self.wall_follow_direction, 2)
                if (temp_dir == check_ore_direction):
                    test_dir = rotate(self.wall_follow_direction, 2)

            for _ in range(8):
                test_pos = current_pos.add(test_dir)
                if ct.can_move(test_dir) or ct.can_build_road(test_pos):
                    if ct.can_build_road(test_pos):
                        ct.build_road(test_pos)
                    if ct.can_move(test_dir):
                        ct.move(test_dir)
                    # Remember this direction for next turn
                    self.wall_follow_direction = test_dir
                    return 
                test_dir = rotate(test_dir, 1) # Rotate 45 degrees right
            return # This happens when we are completley trapped, 
        #===========================================================================================================================
    if self.mode == "GREEDY":
        print("GREEDY")
        print(self.hit_distance)
        current_dist_sq = (current_pos.x - self.target_ore.x)**2 + (current_pos.y - self.target_ore.y)**2
        possible_moves = []
        
        for d in DIRECTIONS:
            hyp_pos = current_pos.add(d)
            dist_sq = (hyp_pos.x - self.target_ore.x)**2 + (hyp_pos.y - self.target_ore.y)**2
            possible_moves.append((dist_sq, d, hyp_pos))
            
        possible_moves.sort(key=lambda item: item[0])
        
        best_valid_dist = 999999
        best_dir = None
        best_pos = None
        
        # Find the best move we can legally make
        for dist_sq, d, hyp_pos in possible_moves:
            if ct.can_move(d) or ct.can_build_road(hyp_pos):
                best_valid_dist = dist_sq
                best_dir = d
                best_pos = hyp_pos
                break
        
        # TRAP DETECTION
        if best_valid_dist >= current_dist_sq:
            # stuck in the dam wall, bug mode activated
            self.mode = "BUG"
            self.hit_distance = current_dist_sq
            self.wall_follow_direction = best_dir if best_dir else DIRECTIONS[0]
            print(self.hit_distance)
            return 
        else:
            if best_pos and ct.can_build_road(best_pos):
                ct.build_road(best_pos)
            if best_dir and ct.can_move(best_dir):
                ct.move(best_dir)
            return
        #===========================================================================================================================
        #If nun of all that, then that means we still didn't see any ores yet so we will continue the roomba
    if self.mode == "ROOMBA":
        print("ROOMBA")
        print(self.hit_distance)
        move_pos = current_pos.add(self.heading)
        
        if ct.can_build_road(move_pos):
            ct.build_road(move_pos)

        if ct.can_move(self.heading):
            ct.move(self.heading)
        else:
            # BUMP! Look for a new random open path
            valid_directions = list(DIRECTIONS)
            random.shuffle(valid_directions)
            
            for d in valid_directions:
                pos = current_pos.add(d)
                if ct.can_move(d) or ct.can_build_road(pos):
                    self.heading = d
                    if ct.can_build_road(pos):
                        ct.build_road(pos)
                    if ct.can_move(self.heading):
                        ct.move(self.heading)
                    break
                    