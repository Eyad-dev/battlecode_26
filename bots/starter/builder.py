import random
from cambc import Controller, Direction, GameConstants, Position
from scanning import *
from snipe import *

DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]
CLOCKWISE_DIRS = [
    Direction.NORTH, Direction.NORTHEAST, Direction.EAST, 
    Direction.SOUTHEAST, Direction.SOUTH, Direction.SOUTHWEST, 
    Direction.WEST, Direction.NORTHWEST
]
STRAIGHT_DIRS = [
    Direction.NORTH, Direction.EAST, 
    Direction.SOUTH, Direction.WEST
]

def rotate(current_dir, steps_clockwise):
    current_index = CLOCKWISE_DIRS.index(current_dir)
    new_index = (current_index + steps_clockwise) % 8
    return CLOCKWISE_DIRS[new_index]


# ==========================================
# MODULARIZED STATE FUNCTIONS
# ==========================================

def handle_vision_and_harvesting(self, ct: Controller, current_pos: Position) -> bool:
    if self.mode == "ROOMBA":
        ores = scan_ore_vision(ct, GameConstants.BUILDER_BOT_VISION_RADIUS_SQ)
        if ores:
            self.target_ore = ores[0]
            self.mode = "GREEDY"
            
    if self.target_ore:
        distance_to_ore_sq = (current_pos.x - self.target_ore.x)**2 + (current_pos.y - self.target_ore.y)**2
        if distance_to_ore_sq <= 2:
            if ct.can_build_harvester(self.target_ore):
                ct.build_harvester(self.target_ore)
                self.mode = "ROOMBA"
                self.target_ore = None
            else:
                self.mode = "ROOMBA"
                self.target_ore = None
            return True # Turn consumed
    return False


def run_bug_mode(self, ct: Controller, current_pos: Position) -> bool:
    current_dist_sq = (current_pos.x - self.target_ore.x)**2 + (current_pos.y - self.target_ore.y)**2
    print(f"BUG Mode | Dist: {current_dist_sq} | Hit: {self.hit_distance}")

    if current_dist_sq < self.hit_distance:
        self.mode = "GREEDY"
        self.hit_distance = 999999
        return False # Returning False lets it run GREEDY mode on this exact same turn!
    else:
        print("We rotating")
        check_ore_direction = current_pos.direction_to(self.target_ore)
        test_dir = rotate(self.wall_follow_direction, -2)
        
        # Custom Orthogonal/Diagonal rotation logic
        if (current_pos.x - self.target_ore.x == 0 or current_pos.y - self.target_ore.y == 0) or (current_pos.x - self.target_ore.x == current_pos.y - self.target_ore.y):
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
                self.wall_follow_direction = test_dir
                return True # Step taken, end turn
            test_dir = rotate(test_dir, 1) 
            
        return True # Completely trapped, end turn and wait


def run_greedy_mode(self, ct: Controller, current_pos: Position) -> bool:
    print(f"GREEDY Mode | Hit Dist: {self.hit_distance}")
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
    
    for dist_sq, d, hyp_pos in possible_moves:
        if ct.can_move(d) or ct.can_build_road(hyp_pos):
            best_valid_dist = dist_sq
            best_dir = d
            best_pos = hyp_pos
            break
    
    # TRAP DETECTION
    if best_valid_dist >= current_dist_sq:
        self.mode = "BUG"
        self.hit_distance = current_dist_sq
        self.wall_follow_direction = best_dir if best_dir else DIRECTIONS[0]
        return True # State changed, wait for next turn to execute BUG
    else:
        if best_pos and ct.can_build_road(best_pos):
            ct.build_road(best_pos)
        if best_dir and ct.can_move(best_dir):
            ct.move(best_dir)
        return True


def run_roomba_mode(self, ct: Controller, current_pos: Position):
    print(f"ROOMBA Mode | Hit Dist: {self.hit_distance}")
    move_pos = current_pos.add(self.heading)
    
    if ct.can_build_road(move_pos):
        ct.build_road(move_pos)

    if ct.can_move(self.heading):
        ct.move(self.heading)
    else:
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


# ==========================================
# MAIN ORCHESTRATOR
# ==========================================


def builderrun(self, ct: Controller):
    """
    This is the main function called by main.py.
    It passes the 'self' instance to the modular helper functions.
    """
    current_pos = ct.get_position()
    print(self.bot_state)

    if self.bot_state== "HARVEST":
        # 1. Vision and Harvester check
        if handle_vision_and_harvesting(self, ct, current_pos):
            return 
            
        # 2. State Machine execution
        if self.mode == "BUG":
            if run_bug_mode(self, ct, current_pos):
                return

        if self.mode == "GREEDY":
            if run_greedy_mode(self, ct, current_pos):
                return

        if self.mode == "ROOMBA":
            run_roomba_mode(self, ct, current_pos)
    
    elif self.bot_state== "ATTACK":
        snipe_the_enemy(self, ct)
