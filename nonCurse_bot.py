
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
# MODULARIZED STATE FUNCTIONS
# ==========================================
def cardinal_toward_base(from_pos: Position, base_pos: Position):
    dx = base_pos.x - from_pos.x
    dy = base_pos.y - from_pos.y
    
    if abs(dx) > abs(dy):
        return Direction.EAST if dx > 0 else Direction.WEST
    else:
        return Direction.SOUTH if dy > 0 else Direction.NORTH
    
    
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
            if (ct.can_move(test_dir) or ct.can_build_road(test_pos)) and ct.get_tile_env(test_pos) != Environment.ORE_TITANIUM:
                if ct.can_build_road(test_pos):
                    ct.build_road(test_pos)
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
        if (ct.can_move(d) or ct.can_build_road(hyp_pos)) and (ct.get_entity_type(ct.get_tile_building_id(hyp_pos)) != EntityType.MARKER and (ct.get_tile_env(hyp_pos) != Environment.ORE_TITANIUM) and (ct.get_tile_env(hyp_pos) != Environment.ORE_AXIONITE)):
            best_valid_dist = dist_sq
            best_dir = d
            best_pos = hyp_pos
            break
    
    # TRAP DETECTION
    if best_valid_dist > current_dist_sq and best_valid_dist: 
        blocker_id = ct.get_tile_building_id(best_pos) if best_pos else None
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
        if best_pos and ct.can_build_road(best_pos):
            ct.build_road(best_pos)
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

    if self.bot_state== "HARVEST":
        # 1. Vision and Harvester check
        print("If I am stuck")
        if handle_vision_and_harvesting(self, ct, current_pos):
            print("I will show it here")
            return 

        active_goal = self.target_bridge or self.target_enemy_bridge or self.target_ore        # 2. State Machine execution
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

                bridge_pos = run_backtrack_mode(self, ct, current_pos, self.ourcoord, taken_core_tiles)
                
                if bridge_pos is None:
                    print("Core is fully occupied")
                    return
                
                bridge_ti_cost = ct.get_bridge_cost()[0]
                current_ti = ct.get_global_resources()[0]

                if ct.get_action_cooldown() == 0 and current_ti >= bridge_ti_cost:

                    # Rip up the road under our feet (if there is one)
                    if ct.can_destroy(current_pos):
                        ct.destroy(current_pos)
                    
                    is_highway = False
                    bridges_team_id = ct.get_tile_building_id(bridge_pos)
                    if bridges_team_id is not None:
                        check_highway = ct.get_entity_type(bridges_team_id)
                        bridges_team = ct.get_team(bridges_team_id)
                        if check_highway == EntityType.BRIDGE and bridges_team == self.our_team:
                            is_highway = True

                    # NOW we can ask permission and build the bridge!

                    print(ct.can_build_bridge(current_pos, bridge_pos))
                    
                    if ct.can_build_bridge(current_pos, bridge_pos):
                        ct.build_bridge(current_pos, bridge_pos)

                        dist_to_base_sq = (bridge_pos.x - self.ourcoord.x)**2 + (bridge_pos.y - self.ourcoord.y)**2


                        if dist_to_base_sq <= 2 or is_highway:
                            print("Supply line touching the Core! Back to work.")
                            self.mode = "ROOMBA"
                            self.target_bridge = None
                            self.heading = self.ourcoord.direction_to(current_pos)
                            # self.bridges_limit += 1
                        else:
                            # Supply line isn't finished. Walk to the end of the bridge!
                            self.target_bridge = bridge_pos
                            self.mode = "GREEDY"
                    return
        return # Ensure we end the turn if we are in BACKTRACK mode!
    elif self.bot_state== "ATTACK":
        find_the_enemy(self, ct)
        snipe_the_enemy(self, ct)

