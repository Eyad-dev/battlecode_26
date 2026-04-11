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
    Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST
]
DIAGONAL_DIRS = [
    Direction.NORTHEAST, Direction.SOUTHEAST, Direction.SOUTHWEST, Direction.NORTHWEST,
]
BRIDGE_TILES = [
    (dx, dy)
    for dx in range(-3,4)
    for dy in range(-3,4)
    if 0 < dx**2 + dy**2 <= 9
]

def rotate(current_dir, steps_clockwise):
    current_index = CLOCKWISE_DIRS.index(current_dir)
    new_index = (current_index + steps_clockwise) % 8
    return CLOCKWISE_DIRS[new_index]

# ==========================================
# CONVEYORS FUNCTIONS
# ==========================================
def cardinal_toward_base(from_pos: Position, base_pos: Position):
    d = from_pos.direction_to(base_pos)
    if d in STRAIGHT_DIRS:
        return d
    
    dx = base_pos.x - from_pos.x
    dy = base_pos.y - from_pos.y

    if abs(dx) >= abs(dy):
        return Direction.EAST if dx>0 else Direction.WEST
    else:
        return Direction.SOUTH if dy>0 else Direction.NORTH
    

def try_build_conveyor(ct: Controller, tile_pos: Position, base_pose: Position):
    if ct.get_action_cooldown() != 0:
        return False
    ti_cost = ct.get_conveyor_cost()[0]
    if ct.get_global_resources()[0] < ti_cost:
        return False
    direction = cardinal_toward_base(tile_pos, base_pose)
    if ct.can_build_conveyor(tile_pos, direction):
        ct.build_conveyor(tile_pos,direction)
        return True
    return False

def is_wall_tile(ct: Controller, pos: Position):
    if not (0 <= pos.x < ct.get_map_width()) or not (0 <= pos.y < ct.get_map_height()):
        return True
    env = ct.get_tile_env(pos)
    return env == Environment.WALL


def find_wall_jump_target(ct: Controller, current_pos: Position, goal_pos: Position):
    current_dist_sq = (current_pos.x - goal_pos.x)**2 + (current_pos.y - goal_pos.y)**2
    best_pos = None
    best_dist_sq = current_dist_sq

    for dx, dy in BRIDGE_TILES:
        landing = Position(current_pos.x + dx, current_pos.y + dy)

        # Out of bounds?
        if not (0 <= landing.x < ct.get_map_width()) or not (0 <= landing.y < ct.get_map_height()):
            continue

        env = ct.get_tile_env(landing)
        if env in (Environment.WALL, Environment.ORE_TITANIUM):
            continue

        # Must be closer to goal
        dist_sq = (landing.x - goal_pos.x)**2 + (landing.y - goal_pos.y)**2
        if dist_sq >= best_dist_sq:
            continue

        steps = max(abs(dx), abs(dy))
        has_wall_between = False
        for step in range(1, steps):
            mid_x = round(current_pos.x + dx * step / steps)
            mid_y = round(current_pos.y + dy * step / steps)
            mid = Position(mid_x, mid_y)
            if is_wall_tile(ct, mid):
                has_wall_between = True
                break
 
        if not has_wall_between:
            continue
 
        best_dist_sq = dist_sq
        best_pos = landing

    return best_pos

def run_wall_jump_mode(self, ct: Controller, current_pos: Position, goal_pos:Position):
    landing = find_wall_jump_target(ct, current_pos, goal_pos)
    if landing is None:
        print("WALL_JUMP: No valid landing found, falling back to BUG")
        self.mode = "BUG"
        self.hit_distance = (current_pos.x - goal_pos.x)**2 + (current_pos.y - goal_pos.y)**2
        direction_to_goal = current_pos.direction_to(goal_pos)
        self.wall_follow_direction = direction_to_goal
        return True
    
    bridge_cost = ct.get_bridge_cost()[0]
    current_ti = ct.get_global_resources()[0]
 
    if ct.get_action_cooldown() != 0 or current_ti < bridge_cost:
        print(f"WALL_JUMP: Waiting for resources/cooldown ({current_ti}/{bridge_cost})")
        return True  # Wait here
    
    if ct.can_build_bridge(current_pos, landing):
        ct.build_bridge(current_pos, landing)
        print(f"WALL_JUMP: Bridge built to {landing}. Resuming conveyors on the other side.")
    
        self.wall_jump_landing = landing
        self.mode = "GREEDY"
        self.wall_jump_active = True
    else:
        print("WALL_JUMP: can_build_bridge returned False — switching to BUG")
        self.mode = "BUG"
        self.hit_distance = (current_pos.x - goal_pos.x)**2 + (current_pos.y - goal_pos.y)**2
        self.wall_follow_direction = current_pos.direction_to(goal_pos)
 
    return True
# ==========================================
# MODULARIZED STATE FUNCTIONS
# ==========================================
    
    
def handle_vision_and_harvesting(self, ct: Controller, current_pos: Position) -> bool:
    if self.mode == "ROOMBA":
        ores = scan_ore_vision(ct, GameConstants.BUILDER_BOT_VISION_RADIUS_SQ)
        if ores:
            self.target_ore = ores[0]
            env = ct.get_tile_env( self.target_ore)
            existing = ct.get_tile_building_id( self.target_ore)
            if existing is not None and ct.get_entity_type(existing) == EntityType.HARVESTER:
                ores.pop(0)
                self.target_ore = ores[0]
            self.mode = "GREEDY"

        else:
            # --- THE HIGHWAY ROBBER RADAR ---
            # No ore? Look for enemy bridges to steal!
            nearby_buildings = ct.get_nearby_buildings()
            for b_id in nearby_buildings:
                if ct.get_entity_type(b_id) == EntityType.BRIDGE and ct.get_team(b_id) != self.our_team:
                    self.target_enemy_bridge = ct.get_position(b_id)
                    self.mode = "GREEDY"
                    break
            
    # Scenario A hunting an ORE
    if self.target_ore:
        if ct.is_in_vision(self.target_ore):
            distance_to_ore_sq = (current_pos.x - self.target_ore.x)**2 + (current_pos.y - self.target_ore.y)**2
            env = ct.get_tile_env(self.target_ore)
            
            # Scenario A: We are hunting an Ore
            if env == Environment.ORE_TITANIUM:
                if distance_to_ore_sq == 1 :
                    road_id = ct.get_entity_type(ct.get_tile_building_id(self.target_ore))
                    if ct.get_entity_type(ct.get_tile_building_id(self.target_ore)) == EntityType.HARVESTER:
                        self.mode = "BACKTRACK"
                        self.target_ore = None
                        return True
                    
                    elif ct.can_build_harvester(self.target_ore):
                        if road_id == EntityType.ROAD:
                            if ct.get_team(ct.get_tile_building_id(self.target_ore)) == self.our_team:
                                if ct.can_destroy(self.target_ore):
                                    ct.destroy(self.target_ore)
                            else:
                                self.target_ore = None
                                return True
                    if ct.can_build_harvester(self.target_ore):
                        if ct.get_action_cooldown() == 0: 
                            ct.build_harvester(self.target_ore)
                            self.mode = "BACKTRACK" 
                            self.target_ore = None
                    print("-------")
                    print("TARGETS")
                    print(self.target_ore)
                    print(self.target_bridge)
                    return True # Turn consumed (waiting for money or just built)
                    
    # Scenario B: We are walking to aa Bridge target
    if self.target_bridge:
        distance_to_bridge_sq = (current_pos.x - self.target_bridge.x)**2 + (current_pos.y - self.target_bridge.y)**2
        
        if distance_to_bridge_sq == 0:
            self.mode = "BACKTRACK"
            self.target_bridge = None
            return True # Arrived! Next turn we build.
    # SCENARIO C
    if self.target_enemy_bridge:
        if ct.is_in_vision(self.target_enemy_bridge):
            
            # Verify the enemy bridge is still there (someone else might have destroyed it!)
            b_id = ct.get_tile_building_id(self.target_enemy_bridge)
            if b_id is None or ct.get_team(b_id) == self.our_team or ct.get_entity_type(b_id) != EntityType.BRIDGE:
                self.target_enemy_bridge = None
                self.mode = "ROOMBA" # It's gone, go back to wandering
                return True
            if current_pos.x == self.target_enemy_bridge.x and current_pos.y == self.target_enemy_bridge.y:
                # If we are close enough to smash it (Distance 1 or 2)
                if ct.get_action_cooldown() == 0 and ct.get_global_resources()[0] >= 2:
                    if ct.can_fire(current_pos):
                        ct.fire(current_pos)
                        print("labombalakaka")
                        check_broken = ct.get_tile_building_id(current_pos)
                        if check_broken is None or ct.get_entity_type(check_broken) != EntityType.BRIDGE:
                            print("SMASHED ENEMY HIGHWAY! Hijacking territory...")                        
                            # Instantly start building our own highway from this spot!
                            self.mode = "BACKTRACK"
                            self.target_enemy_bridge = None
                return True
    
    return False

def run_bug_mode(self, ct: Controller, current_pos: Position, goal_pos: Position ) -> bool:
    current_dist_sq = (current_pos.x - goal_pos.x)**2 + (current_pos.y - goal_pos.y)**2
    print(f"BUG Mode | Dist: {current_dist_sq} | Hit: {self.hit_distance}")
    print(goal_pos)

    if current_dist_sq < self.hit_distance:
        self.mode = "GREEDY"
        self.hit_distance = 999999
        return False # Returning False lets it run GREEDY mode on this exact same turn!
    else:
        print("We rotating")
        check_ore_direction = current_pos.direction_to(goal_pos)


        # if self.wall_follow_direction in DIAGONAL_DIRS:
        #     test_dir = rotate(self.wall_follow_direction, -1)
        # else:
        test_dir = rotate(self.wall_follow_direction, -2)
        
        # Custom Orthogonal/Diagonal rotation logic
        if ((current_pos.x - goal_pos.x == 0 or current_pos.y - goal_pos.y == 0) or (current_pos.x - goal_pos.x == current_pos.y - goal_pos.y)) and (current_dist_sq <= 20):
            print("-----------------")
            print("CHECKS")
            print("first check")
            temp_dir = rotate(self.wall_follow_direction, 2)
            if (temp_dir == check_ore_direction):
                print("second check")
                test_dir = rotate(self.wall_follow_direction, 2)

        for _ in range(8):
            test_pos = current_pos.add(test_dir)
            print("----------------")
            print("CHECKS TWO")
            print(test_pos)
            print(test_dir)
            can_conv = ct.can_build_conveyor(test_pos, cardinal_toward_base(test_pos, self.ourcoord))
            if (ct.can_move(test_dir) or can_conv) and ct.get_tile_env(test_pos) != Environment.ORE_TITANIUM:
                try_build_conveyor(ct, test_pos, self.ourcoord)
                if ct.can_move(test_dir):
                    ct.move(test_dir)
                self.wall_follow_direction = test_dir
                return True # Step taken, end turn
            test_dir = rotate(test_dir, 1) 
            
        return True # Completely trapped, end turn and wait


def run_greedy_mode(self, ct: Controller, current_pos: Position, goal_pos: Position) -> bool:
    print(f"GREEDY Mode | Hit Dist: {self.hit_distance}")
    current_dist_sq = (current_pos.x - goal_pos.x)**2 + (current_pos.y - goal_pos.y)**2
    possible_moves = []
    print("---------------")
    print("TARGETS_GREEDY")
    print(self.target_ore)
    print(self.target_bridge)
    print("---------------")
    for d in DIRECTIONS:
        hyp_pos = current_pos.add(d)
        dist_sq = (hyp_pos.x - goal_pos.x)**2 + (hyp_pos.y - goal_pos.y)**2
        possible_moves.append((dist_sq, d, hyp_pos))
        
    possible_moves.sort(key=lambda item: item[0])
    
    best_valid_dist = 999999
    best_dir = None
    best_pos = None
    
    for dist_sq, d, hyp_pos in possible_moves:
        can_conv = ct.can_build_conveyor(hyp_pos, cardinal_toward_base(hyp_pos, self.ourcoord))
        if (ct.can_move(d) or can_conv) and (ct.get_entity_type(ct.get_tile_building_id(hyp_pos)) != EntityType.MARKER and (ct.get_tile_env(hyp_pos) != Environment.ORE_TITANIUM) and (ct.get_tile_env(hyp_pos) != Environment.ORE_AXIONITE)):
            best_valid_dist = dist_sq
            best_dir = d
            best_pos = hyp_pos
            break
    
    # TRAP DETECTION
    if best_valid_dist > current_dist_sq and best_valid_dist: 
        blocker_id = ct.get_tile_building_id(best_pos)
        if is_wall_tile(ct, best_pos):
            print("GREEDY: Wall detected -> WALL_JUMP")
            self.mode = "WALL_JUMP"
            return True
        
        if blocker_id is not None and ct.get_entity_type(blocker_id) == EntityType.BUILDER_BOT:
            self.mode = "ROOMBA"
            return True
        
        print("BUGGGY")
        print(best_valid_dist)
        print(current_dist_sq)
        print(best_pos)
        print("---------------")
        
        self.mode = "BUG"
        self.hit_distance = current_dist_sq
        self.wall_follow_direction = best_dir if best_dir else current_pos.direction_to(goal_pos)
        return True # State changed, wait for next turn to execute BUG
    else:
        if best_pos:
            try_build_conveyor(ct, best_pos, self.ourcoord)
        if best_dir and ct.can_move(best_dir):
            ct.move(best_dir)
        return True


def run_roomba_mode(self, ct: Controller, current_pos: Position):
    print(f"ROOMBA Mode | Hit Dist: {self.hit_distance}")
    move_pos = current_pos.add(self.heading)


    is_safe = True
    if not(0 <= move_pos.x < ct.get_map_width()) or not(0 <= move_pos.y < ct.get_map_height()):
        is_safe = False
    else:
        check_for_marker = ct.get_tile_building_id(move_pos)
        if check_for_marker is not None and ct.get_entity_type(check_for_marker) == EntityType.MARKER:
            is_safe = False
            
    print(is_safe)
    if is_safe and ct.can_build_road(move_pos):
            ct.build_road(move_pos)

    if is_safe and ct.can_move(self.heading):
        ct.move(self.heading)
    else:
        valid_directions = list(DIRECTIONS)
        random.shuffle(valid_directions)
        
        for d in valid_directions:
            pos = current_pos.add(d)
            if not(0 <= pos.x < ct.get_map_width()) or not(0 <= pos.y < ct.get_map_height()):
                continue
            if ct.get_entity_type(ct.get_tile_building_id(pos)) == EntityType.MARKER:
                continue
            if ct.can_move(d) or ct.can_build_road(pos):
                self.heading = d
                if ct.can_build_road(pos):
                    ct.build_road(pos)
                if ct.can_move(self.heading):
                    ct.move(self.heading)
                break
def run_backtrack_mode(self, ct: Controller, current_pos: Position, goal_pos:Position, taken_core_tiles: list):
    best_target = None
    min_tile_distance_to_core = 99999
    current_dist_sq = (current_pos.x - goal_pos.x)**2 + (current_pos.y - goal_pos.y)**2
    for dx, dy in BRIDGE_TILES:
        target_pos = Position(current_pos.x + dx, current_pos.y + dy)
        if not(0 <= target_pos.x < ct.get_map_width()) or not(0 <= target_pos.y < ct.get_map_height()):
            continue
        tile_team_id = ct.get_tile_building_id(target_pos)
        tile_team = ct.get_team(tile_team_id)
        if ct.get_tile_env(target_pos) == Environment.WALL or ct.get_tile_env(target_pos) == Environment.ORE_TITANIUM or ct.get_tile_env(target_pos) == Environment.ORE_AXIONITE or ct.get_entity_type(ct.get_tile_building_id(target_pos)) == EntityType.MARKER or (tile_team != self.our_team) or (self.our_team != ct.get_team(ct.get_tile_building_id(current_pos))):
            continue

        dist_sq = (target_pos.x - goal_pos.x)**2 + (target_pos.y - goal_pos.y)**2
        # if ct.get_tile_building_id(target_pos) is not None and ct.get_entity_type(ct.get_tile_building_id(target_pos)) == EntityType.BRIDGE:
        #     if dist_sq < current_dist_sq:
        #       best_target = target_pos
        #       return target_pos
            
        if dist_sq <= 2:
            is_taken=False
            for taken_pos in taken_core_tiles:
                if target_pos.x == taken_pos.x and target_pos.y == taken_pos.y:
                    is_taken = True
                    break
            if is_taken:
                continue


        if dist_sq <= min_tile_distance_to_core:
            min_tile_distance_to_core = dist_sq
            best_target = target_pos

    return best_target
    

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

    if not hasattr(self, 'wall_jump_landing'):
        self.wall_jump_landing = None
    if not hasattr(self, 'wall_jump_active'):
        self.wall_jump_active = False

    if self.bot_state== "HARVEST":
        
        if self.wall_jump_active and self.wall_jump_landing:
            if current_pos.x == self.wall_jump_landing.x and current_pos.y == self.wall_jump_landing.y:
                print("WALL_JUMP: Arrived at landing tile, resuming conveyors.")
                self.wall_jump_active = False
                self.wall_jump_landing = None
        # 1. Vision and Harvester check
        print("If I am stuck")
        if handle_vision_and_harvesting(self, ct, current_pos):
            print("I will show it here")
            return 
        
        if self.wall_jump_active and self.wall_jump_landing:
            active_goal = self.wall_jump_landing
        else:
            active_goal = self.target_bridge or self.target_enemy_bridge or self.target_ore  # 2. State Machine execution
        if self.mode == "WALL_JUMP":
            if run_wall_jump_mode(self, ct, current_pos, active_goal):
                return
        if self.mode == "BUG":
            if run_bug_mode(self, ct, current_pos, active_goal):
                return

        if self.mode == "GREEDY":
            if run_greedy_mode(self, ct, current_pos, active_goal):
                return

        if self.mode == "ROOMBA":
            run_roomba_mode(self, ct, current_pos)

        if self.mode == "BACKTRACK":            
                taken_core_tiles = []
                nearby_buildings = ct.get_nearby_buildings()
                for b_id in nearby_buildings:
                    if ct.get_entity_type(b_id) == EntityType.BRIDGE:
                        bridge_target = ct.get_bridge_target(b_id)
                        if (bridge_target.x - self.ourcoord.x)**2 + (bridge_target.y - self.ourcoord.y)**2 <= 2:
                            taken_core_tiles.append(bridge_target)

                anchor_pos = run_backtrack_mode(self, ct, current_pos, self.ourcoord, taken_core_tiles)
                
                if anchor_pos is None:
                    print("Core is fully occupied")
                    return

                if ct.get_action_cooldown() == 0:

                    # Rip up the road under our feet (if there is one)
                    if ct.can_destroy(current_pos):
                        ct.destroy(current_pos)
                    conveyor_dir = cardinal_toward_base(current_pos, self.ourcoord)
                    if ct.can_build_conveyor(current_pos, conveyor_dir):
                        ct.build_conveyor(current_pos, conveyor_dir)
                        print(f"BACKTRACK: Conveyor laid at {current_pos} → {conveyor_dir}")
                    self.mode = "ROOMBA"
                    self.target_bridge = None
                    self.heading = self.ourcoord.direction_to(current_pos)
                    return
        return # Ensure we end the turn if we are in BACKTRACK mode!
    elif self.bot_state== "ATTACK":
        find_the_enemy(self, ct)
        snipe_the_enemy(self, ct)

