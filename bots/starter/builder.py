import random
from cambc import Controller, Direction, GameConstants, Position
from scanning import *
from snipe import *
from healer import *

BRIDGE_TILES = [
    (dx, dy)
    for dx in range(-3,4)
    for dy in range(-3,4)
    if 0 < dx**2 + dy**2 <= 9
]

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

def rotate(current_dir, steps_clockwise):
    if current_dir == Direction.CENTRE :
        return random.choice(DIRECTIONS) 
    current_index = CLOCKWISE_DIRS.index(current_dir)
    new_index = (current_index + steps_clockwise) % 8
    return CLOCKWISE_DIRS[new_index]

# ==========================================
# CONVEYOR FUNCTIONS
# ==========================================

def cardinal_toward_base(from_pos: Position, base_pos: Position):
    d = from_pos.direction_to(base_pos)
    if d in STRAIGHT_DIRS:
        return d
    dx = base_pos.x - from_pos.x
    dy = base_pos.y - from_pos.y
    if abs(dx) >= abs(dy):
        return Direction.EAST if dx > 0 else Direction.WEST
    else:
        return Direction.SOUTH if dy > 0 else Direction.NORTH

def try_build_road(ct: Controller, tile_pos: Position):
    if ct.can_build_road(tile_pos):
        ct.build_road(tile_pos)
        print(f"  [try_build_road] Built road at {tile_pos}")

def is_wall_tile(ct: Controller, pos: Position):
    if not (0 <= pos.x < ct.get_map_width()) or not (0 <= pos.y < ct.get_map_height()):
        return True
    env = ct.get_tile_env(pos)
    return env == Environment.WALL


def try_build_conveyor(self, ct: Controller, tile_pos: Position, base_pos: Position):
    if ct.get_action_cooldown() != 0:
        print(f"  [try_build_conveyor] Skipped — action cooldown {ct.get_action_cooldown()}")
        return False
    ti_cost = ct.get_conveyor_cost()[0]
    if ct.get_global_resources()[0] < ti_cost:
        print(f"  [try_build_conveyor] Skipped — not enough Ti ({ct.get_global_resources()[0]}/{ti_cost})")
        return False
    # Destroy any existing road so conveyor can be placed
    if (ct.can_destroy(tile_pos) and ct.get_entity_type(ct.get_tile_building_id(tile_pos)) == EntityType.ROAD):
        ct.destroy(tile_pos)
        print(f"  [try_build_conveyor] Destroyed existing building at {tile_pos}")
    # Check if there is an enemy road to fire at it
    existing_id = ct.get_tile_building_id(tile_pos)
    if existing_id is not None and ct.get_entity_type(existing_id) == EntityType.ROAD and ct.get_team(existing_id) != ct.get_team():
        if ct.can_fire(tile_pos):
            ct.fire(tile_pos)
            print(f"  [try_build_conveyor] Fired at enemy road at {tile_pos}")
            return True
        else:
            print(f"  [try_build_conveyor] Can't fire at enemy road at {tile_pos} — cooldown {ct.get_action_cooldown()}")
            return True
    direction = cardinal_toward_base(tile_pos, base_pos)
    # if ct.get_entity_type(ct.get_tile_building_id(tile_pos.add(direction))) == EntityType.MARKER:
    #     direction = rotate(direction, 2)
    #--------------------------------------------------------------------------------------------------
    # if ct.get_tile_env(tile_pos.add(direction)) == Environment.ORE_TITANIUM:
    #     self.mode = "BACKTRACK"
    #     self.target_greedy = self.ourcoord
    #     return True

    if ct.can_build_conveyor(tile_pos, direction):
        ct.build_conveyor(tile_pos, direction)
        print(f"  [try_build_conveyor] Built at {tile_pos} → {direction}")
        return True
    print(f"  [try_build_conveyor] Failed at {tile_pos} dir {direction}")
    return False

def find_bridge_target(self, ct: Controller, current_pos: Position, goal_pos: Position, conveyor_dir: Direction):
    taken_core_tiles = []
    nearby_buildings = ct.get_nearby_buildings()
    for b_id in nearby_buildings:
        if ct.get_entity_type(b_id) == EntityType.BRIDGE:
            bridge_target = ct.get_bridge_target(b_id)
            if (bridge_target.x - self.ourcoord.x)**2 + (bridge_target.y - self.ourcoord.y)**2 <= 2:
                taken_core_tiles.append(bridge_target)

    best_target = None
    min_tile_distance_to_core = 99999
    for dx, dy in BRIDGE_TILES:
        target_pos = Position(current_pos.x + dx, current_pos.y + dy)
        if not(0 <= target_pos.x < ct.get_map_width()) or not(0 <= target_pos.y < ct.get_map_height()):
            continue
        tile_team_id = ct.get_tile_building_id(target_pos)
        if ct.get_tile_env(target_pos) == Environment.WALL or ct.get_tile_env(target_pos) == Environment.ORE_TITANIUM or ct.get_tile_env(target_pos) == Environment.ORE_AXIONITE or ct.get_entity_type(ct.get_tile_building_id(target_pos)) == EntityType.MARKER or (self.our_team != ct.get_team(ct.get_tile_building_id(current_pos))):
            continue
        if goal_pos == self.splitter_foundry_pos and (target_pos in self.core_tiles or target_pos == self.ourcoord):
            continue

        dist_sq = (target_pos.x - goal_pos.x)**2 + (target_pos.y - goal_pos.y)**2

        if dist_sq <= min_tile_distance_to_core:
            # if (ct.get_entity_type(tile_team_id) == EntityType.ROAD and tile_team != self.our_team)
            min_tile_distance_to_core = dist_sq
            best_target = target_pos

    return best_target

def find_splitter_pos(self, ct: Controller):
    foundry_pos = self.temp_pos_A_foundary
    core_pos = self.ourcoord

    dir_foundry_to_core = cardinal_toward_base(foundry_pos, core_pos)
    # The splitter sits adjacent to the foundry, on the core side
    for d in STRAIGHT_DIRS:
        splitter_pos = foundry_pos.add(dir_foundry_to_core)
        self.splitter_foundry_pos = splitter_pos
        if splitter_pos not in self.core_tiles:
            break
        else:
            dir_foundry_to_core = rotate(dir_foundry_to_core, 2)  # Rotate 90 degrees and check the next side
    

    # The splitter's input comes from the titanium ore side (away from foundry)
    # which is the direction from splitter back toward the ore/conveyor chain
    dir_splitter_to_foundry = cardinal_toward_base(splitter_pos, foundry_pos)
    # Input direction = where the conveyor chain is coming FROM
    # i.e. opposite of toward-foundry, which is toward the ore
    for d in STRAIGHT_DIRS:
        if (splitter_pos.add(dir_splitter_to_foundry) in self.core_tiles) or (splitter_pos.add(dir_splitter_to_foundry) == self.temp_pos_A_foundary):
            input_dir = rotate(dir_splitter_to_foundry, 2)
        else:  # 4 steps = 180 degrees
            break

    return splitter_pos, input_dir
# ==========================================
# MODULARIZED STATE FUNCTIONS
# ==========================================

def handle_vision_and_harvesting(self, ct: Controller, current_pos: Position) -> bool:
    print(f"[VISION] Mode={self.mode} | Pos={current_pos} | target_ore={self.target_ore} | target_greedy={self.target_greedy} | target_enemy_bridge={self.target_enemy_bridge}")

    if self.mode == "ROOMBA":
        ores = scan_ore_vision(ct, GameConstants.BUILDER_BOT_VISION_RADIUS_SQ)
        for ore_pos in ores:
            if (ct.get_tile_env(ore_pos) == Environment.ORE_AXIONITE and self.axionite_foundary_states == 0):
                print("I AXIONITE BABYYYYY")
                print(f"[VISION] Axionite ore spotted at {ore_pos} — prioritizing for harvest")
                self.target_ore = ore_pos
                self.mode = "GREEDY"
                self.axionite_foundary_states = 1
                return True
            
        eligible_ores = [
        o for o in ores
        if not (ct.get_tile_env(o) == Environment.ORE_AXIONITE and self.axionite_foundary_states != 0)
        ]
        if eligible_ores:
            self.target_ore = eligible_ores[0]
            existing = ct.get_tile_building_id(self.target_ore)
            if existing is not None and ct.get_entity_type(existing) == EntityType.HARVESTER:
                print(f"[VISION] Ore at {self.target_ore} already has a harvester, skipping to next")
                eligible_ores.pop(0)
                self.target_ore = eligible_ores[0]
            print(f"[VISION] Ore spotted at {self.target_ore} — switching to GREEDY")
            self.mode = "GREEDY"
        else:
            nearby_buildings = ct.get_nearby_buildings()
            for b_id in nearby_buildings:
                if ct.get_entity_type(b_id) == EntityType.BRIDGE and ct.get_team(b_id) != self.our_team:
                    self.target_enemy_bridge = ct.get_position(b_id)
                    print(f"[VISION] Enemy bridge spotted at {self.target_enemy_bridge} — switching to GREEDY")
                    self.mode = "GREEDY"
                    break

    # Scenario A: Hunting an ORE
    if self.target_ore:
        if ct.is_in_vision(self.target_ore):
            distance_to_ore_sq = (current_pos.x - self.target_ore.x)**2 + (current_pos.y - self.target_ore.y)**2
            env = ct.get_tile_env(self.target_ore)
            print(f"[VISION | ORE HUNT] Ore at {self.target_ore} | dist²={distance_to_ore_sq} | env={env}")

            if (env == Environment.ORE_TITANIUM or env == Environment.ORE_AXIONITE):
                if distance_to_ore_sq == 1:
                    ore_bid = ct.get_tile_building_id(self.target_ore)
                    ore_type = ct.get_entity_type(ore_bid) if ore_bid is not None else None

                    if ore_type == EntityType.HARVESTER:
                        print(f"[VISION | ORE HUNT] Ore already harvested — heading back to base")
                        self.mode = "GREEDY"
                        self.target_ore = None
                        self.target_greedy = self.ourcoord
                        return True

                    elif ct.can_build_harvester(self.target_ore):
                        if ore_type == EntityType.ROAD:
                            if ct.get_team(ore_bid) == self.our_team:
                                if ct.can_destroy(self.target_ore):
                                    print(f"[VISION | ORE HUNT] Destroying our own road on ore tile to make room")
                                    ct.destroy(self.target_ore)
                            else:
                                print(f"[VISION | ORE HUNT] Enemy road on ore tile — abandoning target")
                                self.target_ore = None
                                return True

                    if ct.can_build_harvester(self.target_ore):
                        if ct.get_action_cooldown() == 0:
                            ct.build_harvester(self.target_ore)
                            print(f"[VISION | ORE HUNT] Harvester built — heading back to base")
                            self.mode = "BACKTRACK"
                            self.target_ore = None
                            self.target_greedy = self.ourcoord
                            return True
                    print(f"[VISION | ORE HUNT] Waiting — cooldown or resources not ready")
                    return True

    # Scenario B: Walking to a greedy target
    if self.target_greedy:
        distance_to_target_sq = (current_pos.x - self.target_greedy.x)**2 + (current_pos.y - self.target_greedy.y)**2
        print(f"[VISION | GREEDY WALK] Target at {self.target_greedy} | dist²={distance_to_target_sq}")
        if distance_to_target_sq == 0:
            print(f"[VISION | GREEDY WALK] Arrived at target — switching to BACKTRACK")
            self.mode = "BACKTRACK"
            self.target_greedy = None
            return True

    # Scenario C: Enemy bridge/Road raiding
    if self.target_enemy_bridge:
        if ct.is_in_vision(self.target_enemy_bridge):
            b_id = ct.get_tile_building_id(self.target_enemy_bridge)
            if b_id is None or ct.get_team(b_id) == self.our_team or ct.get_entity_type(b_id) != EntityType.BRIDGE:
                print(f"[VISION | ENEMY RAID] Enemy bridge at {self.target_enemy_bridge} is gone — back to ROOMBA")
                self.target_enemy_bridge = None
                self.mode = "ROOMBA"
                return True
            if current_pos.x == self.target_enemy_bridge.x and current_pos.y == self.target_enemy_bridge.y:
                print(f"[VISION | ENEMY RAID] On enemy bridge tile — attempting to fire")
                if ct.get_action_cooldown() == 0 and ct.get_global_resources()[0] >= 2:
                    if ct.can_fire(current_pos):
                        ct.fire(current_pos)
                        print("[VISION | ENEMY RAID] Fired!")
                        check_broken = ct.get_tile_building_id(current_pos)
                        if check_broken is None or ct.get_entity_type(check_broken) != EntityType.BRIDGE:
                            print("[VISION | ENEMY RAID] Bridge destroyed — heading back to base")
                            self.mode = "BACKTRACK"
                            self.target_enemy_bridge = None
                            if(self.splitter_foundry_pos is not None and ct.is_in_vision(self.splitter_foundry_pos)):
                                self.target_greedy = self.splitter_foundry_pos
                            else:
                                self.target_greedy = self.ourcoord
                else:
                    print(f"[VISION | ENEMY RAID] Can't fire — cooldown {ct.get_action_cooldown()} | Ti {ct.get_global_resources()[0]}")
                return True

    return False


def run_bug_mode(self, ct: Controller, current_pos: Position, goal_pos: Position) -> bool:
    current_dist_sq = (current_pos.x - goal_pos.x)**2 + (current_pos.y - goal_pos.y)**2
    print(f"[BUG] At {current_pos} | Goal {goal_pos} | dist²={current_dist_sq} | hit_dist={self.hit_distance}")

    if current_dist_sq < self.hit_distance:
        print(f"[BUG] Closer than hit distance — switching to GREEDY")
        self.mode = "GREEDY"
        self.target_greedy = goal_pos
        self.hit_distance = 999999
        return False
    
    self.hook_offset = -2
    self.sweep_dir = 1
    test_dir = self.wall_follow_direction

    hit_dir = self.wall_follow_direction

    # print(f"[BUG] Still wall-following | wall_dir={self.wall_follow_direction}")
    # check_ore_direction = current_pos.direction_to(goal_pos)
    # test_dir = rotate(self.wall_follow_direction, -2)
    

    # Bug nav can get stuck in straight corridors if the goal is directly ahead or behind — add special check to rotate direction if aligned and close to goal
    # but this thing buggy
    # if ((current_pos.x - goal_pos.x == 0 or current_pos.y - goal_pos.y == 0) or
    #         (current_pos.x - goal_pos.x == current_pos.y - goal_pos.y)) and (current_dist_sq <= 20):
    #     print(f"[BUG] Orthogonal/diagonal alignment check triggered")
    #     temp_dir = rotate(self.wall_follow_direction, 2)
    #     if temp_dir == check_ore_direction:
    #         print(f"[BUG] Direction correction applied")
    #         test_dir = rotate(self.wall_follow_direction, 2)
    for _ in range(8):
        print(f"[BUG] Testing direction {test_dir}")
        test_pos = current_pos.add(test_dir)
        print(f"[BUG] Trying dir={test_dir} | pos={test_pos} | can_build_road={ct.can_build_road(test_pos)}")
        if ct.can_build_road(test_pos):
            try_build_road(ct, test_pos)
            self.wall_follow_direction = test_dir
            print()
        if ct.can_move(test_dir):
            ct.move(test_dir)
            print(f"[BUG] Moved {test_dir} to {test_pos}")
            new_dir = test_dir

            if hit_dir != new_dir:
                right_side_directions = [rotate(new_dir,1), rotate(new_dir,2), rotate(new_dir,3)]
                left_side_directions = [rotate(new_dir,-1), rotate(new_dir,-2), rotate(new_dir,-3)]

                if hit_dir in right_side_directions:
                    self.hook_offset = 2
                    self.sweep_dir = -1
                    print(f"[BUG] Hit was on the right side — setting hook_offset={self.hook_offset} and sweep_dir={self.sweep_dir}")
                elif hit_dir in left_side_directions:
                    self.hook_offset = -2
                    self.sweep_dir = 1
                    print(f"[BUG] Hit was on the left side — setting hook_offset={self.hook_offset} and sweep_dir={self.sweep_dir}")
                print(f"[BUG] Found open tile — rotating wall follow direction to {self.wall_follow_direction}")

            self.wall_follow_direction = rotate(new_dir, self.hook_offset)
            print(f"[BUG] Updated wall follow direction to {self.wall_follow_direction} for next turn")
            return True
        test_dir = rotate(test_dir, 1)
    print(f"[BUG] Completely trapped — waiting")
    return True

def run_greedy_mode(self, ct: Controller, current_pos: Position, goal_pos: Position) -> bool:
    current_dist_sq = (current_pos.x - goal_pos.x)**2 + (current_pos.y - goal_pos.y)**2
    # ---- BACKTRACK TO BASE: build conveyors on the way back ----
    if goal_pos == self.ourcoord or goal_pos == self.splitter_foundry_pos:
        conveyor_dir = cardinal_toward_base(current_pos, goal_pos)
        next_pos = current_pos.add(conveyor_dir)
        print(f"[GREEDY | BACKTRACK] At {current_pos} | conveyor dir={conveyor_dir}")
        built_conveyor = False

        # Destroying the last conveyor for the Foundry
        if (next_pos in self.core_tiles and self.axionite_foundary_states == 1):
            self.axionite_foundary_states = 2
            splitter_pos = current_pos
            for d in DIRECTIONS:
                if ct.can_move(d):
                    self.temp_pos_A_foundary = current_pos
                    ct.move(d)
                    break
            if ct.can_destroy(splitter_pos):
                ct.destroy(splitter_pos)
                print(f"[GREEDY | BACKTRACK] Destroyed conveyor at {splitter_pos} to free up core tile for splitter")
            return True

        if ct.get_action_cooldown() == 0:
            if(ct.get_team(ct.get_tile_building_id(current_pos)) != self.our_team):
                if ct.can_fire(current_pos):
                    ct.fire(current_pos)
                    print(f"[GREEDY | BACKTRACK] Fired at enemy building on current tile {current_pos} to clear way for conveyor")
                    if (ct.get_tile_building_id(current_pos) is None):
                        print(f"[GREEDY | BACKTRACK] Building destroyed — trying to build conveyor")
                        self.mode = "BACKTRACK"
                    return True
                else:
                    print(f"[GREEDY | BACKTRACK] Can't fire at enemy building on current tile {current_pos} — cooldown {ct.get_action_cooldown()}")
            elif (goal_pos != self.ourcoord and goal_pos != self.splitter_foundry_pos):
                try_build_road(ct, cardinal_toward_base(current_pos, goal_pos))
            else:
                print("[GREEDY | BACKTRACK] At goal — no need to build roads")
                built_conveyor = try_build_conveyor(self, ct, next_pos, goal_pos)

        if built_conveyor and ct.can_move(conveyor_dir):
            ct.move(conveyor_dir)
            print(f"[GREEDY | BACKTRACK] Moved {conveyor_dir} onto conveyor")
        else:
            print(f"[DEBUG] team_check={ct.get_team(ct.get_tile_building_id(current_pos.add(conveyor_dir)))} | our_team={self.our_team} | entity={ct.get_entity_type(ct.get_tile_building_id(current_pos.add(conveyor_dir)))} | axionite_state={self.axionite_foundary_states}")
            if(ct.get_team(ct.get_tile_building_id(current_pos.add(conveyor_dir))) != self.our_team):
                if (ct.can_move(conveyor_dir)):
                    ct.move(conveyor_dir)
            elif (self.axionite_foundary_states == 6 or self.axionite_foundary_states == 0) and (((ct.get_entity_type(ct.get_tile_building_id(current_pos.add(conveyor_dir))) == EntityType.CONVEYOR or ct.get_entity_type(ct.get_tile_building_id(current_pos.add(conveyor_dir))) == EntityType.BRIDGE) and (ct.get_team(ct.get_tile_building_id(current_pos.add(conveyor_dir))) == self.our_team)) or next_pos in self.core_tiles):
                self.target_greedy = None
                self.mode = "ROOMBA"
                return True
            elif self.axionite_foundary_states < 6 and (ct.get_entity_type(ct.get_tile_building_id(current_pos.add(conveyor_dir))) == EntityType.CONVEYOR and ct.get_team(ct.get_tile_building_id(current_pos.add(conveyor_dir))) == self.our_team):
                if ct.can_move(conveyor_dir):
                    ct.move(conveyor_dir)
                    return True
            elif (goal_pos == self.ourcoord and next_pos == self.ourcoord or self.axionite_foundary_states == 0):
                if (next_pos in self.core_tiles):
                    self.target_greedy = None
                    self.mode = "ROOMBA"
                    return True
            elif (goal_pos == self.splitter_foundry_pos and next_pos == self.splitter_foundry_pos or next_pos == self.temp_pos_A_foundary):
                    self.target_greedy = None
                    self.mode = "ROOMBA"
                    self.axionite_foundary_states = 6
                    return True
            else:
                print(f"[GREEDY | BACKTRACK] Can't move {conveyor_dir} — blocked or conveyor not built")
                if (is_wall_tile(ct, next_pos) or ct.get_tile_env(next_pos) == Environment.ORE_TITANIUM or ct.get_tile_env(next_pos) == Environment.ORE_AXIONITE or ct.get_entity_type(ct.get_tile_building_id(next_pos)) == EntityType.HARVESTER or ct.get_entity_type(ct.get_tile_building_id(next_pos)) == EntityType.SPLITTER or (goal_pos == self.splitter_foundry_pos and next_pos in self.core_tiles)):
                    landing = find_bridge_target(self, ct, current_pos, goal_pos, conveyor_dir)
                    print(f"[GREEDY | BACKTRACK] Detected wall at {next_pos} — trying wall jump to {landing}")
                    if landing and ct.get_action_cooldown() == 0:
                        bridge_cost = ct.get_bridge_cost()[0]
                        print("WE RE ABLE TO FIND A LANDING SPOT FOR THE BRIDGE")
                        if ct.get_global_resources()[0] >= bridge_cost:
                            print("WE DID REACH HERE")
                            if ct.can_destroy(current_pos) and ct.get_entity_type(ct.get_tile_building_id(current_pos)) == EntityType.CONVEYOR:
                                ct.destroy(current_pos)
                                print(f"WALL_JUMP: Destroyed road at {current_pos} for bridge placement")
                            if ct.can_build_bridge(current_pos, landing):
                                ct.build_bridge(current_pos, landing)
                                if (goal_pos == self.ourcoord):
                                    if ((landing in self.core_tiles or landing == self.ourcoord or ct.get_entity_type(ct.get_tile_building_id(landing)) == EntityType.CONVEYOR) and self.axionite_foundary_states == 2):
                                        print(f"WALL_JUMP: Bridge landing {landing} is a core tile — switching to ROOMBA")
                                        self.target_greedy = None
                                        self.mode = "ROOMBA"
                                        return True
                                    if (landing in self.core_tiles or landing == self.ourcoord or (ct.get_entity_type(ct.get_tile_building_id(landing)) == EntityType.CONVEYOR and ct.get_team(ct.get_tile_building_id(landing)) == self.our_team) or (ct.get_entity_type(ct.get_tile_building_id(landing)) == EntityType.BRIDGE and ct.get_team(ct.get_tile_building_id(landing)) == self.our_team)):
                                        print(f"WALL_JUMP: Bridge landing {landing} is a core tile — switching to ROOMBA")
                                        self.target_greedy = None
                                        self.mode = "ROOMBA"
                                        return True
                                elif (goal_pos == self.splitter_foundry_pos):
                                    if(landing == self.splitter_foundry_pos or landing == self.temp_pos_A_foundary):
                                        print(f"WALL_JUMP: Bridge landing {landing} is the splitter foundry — switching to ROOMBA")
                                        self.target_greedy = None
                                        self.axionite_foundary_states = 6
                                        self.mode = "ROOMBA"
                                        return True
                                print(f"WALL_JUMP: Built bridge from {current_pos} to {landing}")
                                self.wall_jump_landing = landing
                                landing_dist_sq = (current_pos.x - landing.x)**2 + (current_pos.y - landing.y)**2
                                self.hit_distance = landing_dist_sq
                                self.wall_follow_direction = cardinal_toward_base(landing, goal_pos)
                                self.mode = "WALL_JUMP"
                                return True
        return True

    # ---- NORMAL GREEDY: build roads on the way to ore ----
    print(f"[GREEDY] At {current_pos} | Goal {goal_pos} | dist²={current_dist_sq} | target_ore={self.target_ore} | target_greedy={self.target_greedy}")

    possible_moves = []
    for d in DIRECTIONS:
        hyp_pos = current_pos.add(d)
        dist_sq = (hyp_pos.x - goal_pos.x)**2 + (hyp_pos.y - goal_pos.y)**2
        possible_moves.append((dist_sq, d, hyp_pos))

    possible_moves.sort(key=lambda item: item[0])

    best_valid_dist = 999999
    best_dir = None
    best_pos = None

    for dist_sq, d, hyp_pos in possible_moves:
        bid = ct.get_tile_building_id(hyp_pos)
        is_marker = bid is not None and ct.get_entity_type(bid) == EntityType.MARKER
        env = ct.get_tile_env(hyp_pos)
        if (ct.can_move(d) or ct.can_build_road(hyp_pos)) \
                and not is_marker \
                and env != Environment.ORE_TITANIUM \
                and env != Environment.ORE_AXIONITE \
                and not (self.axionite_foundary_states > 0 and ct.get_entity_type(ct.get_tile_building_id(hyp_pos)) in [EntityType.CONVEYOR, EntityType.BRIDGE] and ct.get_team(ct.get_tile_building_id(hyp_pos)) == self.our_team):
            best_valid_dist = dist_sq
            best_dir = d
            best_pos = hyp_pos
            break

    print(f"[GREEDY] Best move: dir={best_dir} | pos={best_pos} | dist²={best_valid_dist}")

    # TRAP DETECTION
    if best_valid_dist > current_dist_sq and best_valid_dist:

        print(f"[GREEDY] Trapped — best dist² {best_valid_dist} > current {current_dist_sq} — switching to BUG")
        self.mode = "BUG"
        self.hit_distance = current_dist_sq
        self.wall_follow_direction = current_pos.direction_to(goal_pos)
        return True
    else:
        if best_pos:
            try_build_road(ct, best_pos)
        print(f"[GREEDY] Moving {best_dir} to {best_pos}")
        if best_dir and ct.can_move(best_dir):
            ct.move(best_dir)
        return True


def run_wall_jump_mode(self, ct: Controller, current_pos: Position, goal_pos: Position) -> bool:
    if self.wall_jump_landing and current_pos == self.wall_jump_landing:
        print("WALL_JUMP: Arrived at landing tile, resuming conveyors.")
        self.wall_jump_landing = None
        self.mode = "GREEDY"
        return True
    
    return run_bug_mode(self, ct, current_pos, self.wall_jump_landing)


def run_roomba_mode(self, ct: Controller, current_pos: Position):
    print(f"[ROOMBA] At {current_pos} | Heading {self.heading}")
    move_pos = current_pos.add(self.heading)

    is_safe = True
    if not (0 <= move_pos.x < ct.get_map_width()) or not (0 <= move_pos.y < ct.get_map_height()):
        print(f"[ROOMBA] Heading {self.heading} goes out of bounds — picking new direction")
        is_safe = False
    else:
        check_for_marker = ct.get_tile_building_id(move_pos)
        if check_for_marker is not None and ct.get_entity_type(check_for_marker) == EntityType.MARKER:
            print(f"[ROOMBA] Marker at {move_pos} — picking new direction")
            is_safe = False
        
        if ct.get_tile_env(move_pos) == Environment.ORE_TITANIUM or ct.get_tile_env(move_pos) == Environment.ORE_AXIONITE:
            is_safe = False 

    if is_safe and ct.can_build_road(move_pos):
        ct.build_road(move_pos)

    if is_safe and ct.can_move(self.heading):
        print(f"[ROOMBA] Moving {self.heading} to {move_pos}")
        ct.move(self.heading)
    else:
        valid_directions = list(DIRECTIONS)
        random.shuffle(valid_directions)

        found = False
        for d in valid_directions:
            pos = current_pos.add(d)
            if not (0 <= pos.x < ct.get_map_width()) or not (0 <= pos.y < ct.get_map_height()):
                continue
            bid = ct.get_tile_building_id(pos)
            if bid is not None and ct.get_entity_type(bid) == EntityType.MARKER:
                continue
            if ct.can_move(d) or ct.can_build_road(pos):
                self.heading = d
                if ct.can_build_road(pos):
                    ct.build_road(pos)
                if ct.can_move(self.heading):
                    ct.move(self.heading)
                print(f"[ROOMBA] New heading {self.heading} — moving to {pos}")
                found = True
                break
        if not found:
            print(f"[ROOMBA] Completely stuck — no valid direction found")


# ==========================================
# MAIN ORCHESTRATOR
# ==========================================

def builderrun(self, ct: Controller):
    current_pos = ct.get_position()
    
    print(f"========== [BUILDER RUN] Pos={current_pos} | Mode={self.mode} | State={self.bot_state} ==========")
    print(f"self.axiitonite_foundary_states: {self.axionite_foundary_states}")
    #Checking for axioniter state with the marker

    # -------------------------------------------------------
    # FOUNDRY BUILD CHECK — runs every turn, no matter mode!
    # -------------------------------------------------------
    #I want when the bot finds now a titanium ore after finishing the ROOMBA in axionite_foundary_states == 3, in 4 I want to now go back to the foundary position (building conveyors to there) (found at self.temp_pos_A_foundary) and set this as my target_greedy, I need to connect that titanium ore that I found back to the foundary with conveyors and then when I arrive at the foundary position I want to go back to roomba

    if self.axionite_foundary_states == 5 and self.mode != "WALL_JUMP" and self.mode != "GREEDY" and self.mode!= "BACKTRACK":
        conveyor_dir = cardinal_toward_base(current_pos, self.splitter_foundry_pos)
        next_pos = current_pos.add(conveyor_dir)

        # if next_pos == self.splitter_foundry_pos:
        #     if ct.get_action_cooldown() == 0:
        #         existing = ct.get_tile_building_id(current_pos)
        #         if existing is not None and ct.can_destroy(current_pos):
        #             ct.destroy(current_pos)
        #             print(f"[BRIDGE] Destroyed conveyor at {current_pos}")
        #         if ct.can_fire(current_pos):
        #             ct.fire(current_pos)
        #             print(f"[BRIDGE] Fired at building on current tile {current_pos} to clear way for bridge")
        #         if ct.can_build_bridge(current_pos, self.splitter_foundry_pos):
        #             ct.build_bridge(current_pos, self.splitter_foundry_pos)
        #             print(f"[BRIDGE] Built bridge to splitter at {self.splitter_foundry_pos}")
        #             self.axionite_foundary_states = 6
        #             self.mode = "ROOMBA"
        #             self.target_greedy = None
        #         else:
        #             print(f"[BRIDGE] Can't build bridge yet")
        #     else:
        #         print(f"[BRIDGE] Waiting — cooldown {ct.get_action_cooldown()}")
        #     return

        if ct.get_action_cooldown() == 0:
            built_conveyor = try_build_conveyor(self, ct, next_pos, self.splitter_foundry_pos)
            if built_conveyor and ct.can_move(conveyor_dir):
                ct.move(conveyor_dir)
                print(f"[STATE5] Moving {conveyor_dir} toward splitter")
            else:
                print(f"[STATE5] Can't move {conveyor_dir} — blocked")
                if (is_wall_tile(ct, next_pos) or ct.get_tile_env(next_pos) == Environment.ORE_TITANIUM or ct.get_tile_env(next_pos) == Environment.ORE_AXIONITE or ct.get_entity_type(ct.get_tile_building_id(next_pos)) == EntityType.HARVESTER or ct.get_entity_type(ct.get_tile_building_id(next_pos)) == EntityType.SPLITTER or ct.get_position().add(conveyor_dir) in self.core_tiles or ct.get_entity_type(ct.get_tile_building_id(next_pos)) == EntityType.FOUNDRY):
                    landing = find_bridge_target(self, ct, current_pos, self.splitter_foundry_pos, conveyor_dir)
                    print(f"[GREEDY | BACKTRACK] Detected wall at {next_pos} — trying wall jump to {landing}")
                    if landing and ct.get_action_cooldown() == 0:
                        bridge_cost = ct.get_bridge_cost()[0]
                        print("WE RE ABLE TO FIND A LANDING SPOT FOR THE BRIDGE")
                        if ct.get_global_resources()[0] >= bridge_cost:
                            print("WE DID REACH HERE")
                            if ct.can_destroy(current_pos) and ct.get_entity_type(ct.get_tile_building_id(current_pos)) == EntityType.CONVEYOR:
                                ct.destroy(current_pos)
                                print(f"WALL_JUMP: Destroyed road at {current_pos} for bridge placement")
                            print("axionite_foundary_states == 5 ends here")
                            if ct.can_build_bridge(current_pos, landing):
                                ct.build_bridge(current_pos, landing)
                                if (landing == self.splitter_foundry_pos):
                                    print(f"WALL_JUMP: Bridge landing {landing} is a core tile — switching to ROOMBA")
                                    self.target_greedy = None
                                    self.mode = "ROOMBA"
                                    self.axionite_foundary_states = 6
                                    return True
                                print(f"WALL_JUMP: Built bridge from {current_pos} to {landing}")
                                self.wall_jump_landing = landing
                                landing_dist_sq = (current_pos.x - landing.x)**2 + (current_pos.y - landing.y)**2
                                self.hit_distance = landing_dist_sq
                                self.wall_follow_direction = cardinal_toward_base(landing, self.splitter_foundry_pos)
                                self.mode = "WALL_JUMP"
                                self.target_greedy = self.splitter_foundry_pos
                                return True
        return

    if self.axionite_foundary_states == 4:
        # Just roaming — the normal HARVEST flow below handles ore detection.
        # Once a harvester is built, handle_vision_and_harvesting sets mode=BACKTRACK
        # and target_greedy=ourcoord. We intercept that here.
        if self.mode == "BACKTRACK" or (self.mode == "GREEDY" and self.target_greedy == self.ourcoord):
            print(f"[STATE4] Harvester built — redirecting backtrack to splitter")
            self.axionite_foundary_states = 5
            self.target_greedy = self.splitter_foundry_pos
            # Don't return — fall through to normal HARVEST flow this turn
        # else: fall through to normal HARVEST flow so ROOMBA/GREEDY work normally

    if self.axionite_foundary_states == 3:
        conveyor_dir = cardinal_toward_base(current_pos, self.temp_pos_A_foundary)
        next_pos = current_pos.add(conveyor_dir)
        if next_pos == self.temp_pos_A_foundary:
            splitter_pos, input_dir = find_splitter_pos(self, ct)
            if ct.get_action_cooldown() == 0:
                existing = ct.get_tile_building_id(splitter_pos)
                if existing is not None and ct.can_destroy(splitter_pos):
                    ct.destroy(splitter_pos)
                print(f"lolamami: {splitter_pos}")
                if ct.can_build_splitter(splitter_pos, input_dir):
                    ct.build_splitter(splitter_pos, input_dir)
                    print(f"[SPLITTER] Built at {splitter_pos} with input from {input_dir}")
                    self.splitter_foundry_pos = splitter_pos
                    self.axionite_foundary_states = 4
                    self.mode = "ROOMBA"
                    self.target_greedy = None
                else:
                    print(f"[SPLITTER] Can't build yet — retrying")
            return
        self.target_greedy = self.temp_pos_A_foundary
        self.mode = "GREEDY"
        # fall through to HARVEST
        conveyor_dir = cardinal_toward_base(current_pos, self.temp_pos_A_foundary)
        next_pos = current_pos.add(conveyor_dir)
        if next_pos == self.temp_pos_A_foundary:
            # Build splitter once on arrival, never again
            splitter_pos, input_dir = find_splitter_pos(self, ct)
            if ct.get_action_cooldown() == 0:
                # Destroy any road/conveyor on that tile first
                existing = ct.get_tile_building_id(splitter_pos)
                if existing is not None and ct.can_destroy(splitter_pos):
                    ct.destroy(splitter_pos)
                if ct.can_build_splitter(splitter_pos, input_dir):
                    ct.build_splitter(splitter_pos, input_dir)
                    print(f"[SPLITTER] Built at {splitter_pos} with input from {input_dir}")
                    self.splitter_foundry_pos = splitter_pos
                    self.target_greedy = splitter_pos
                    self.axionite_foundary_states = 4
                    self.mode = "ROOMBA" 
                    self.target_greedy = None
                    return True
                else:
                    print(f"[SPLITTER] Can't build at {splitter_pos} — may retry next turn")
                    return  # Don't advance state yet, retry next turn
            else:
                return  # Wait for cooldown
        return
        # ores = scan_ore_vision(ct, GameConstants.BUILDER_BOT_VISION_RADIUS_SQ)
        # found_target = False
        # for ore in ores:
        #     if ct.get_tile_env(ore) == Environment.ORE_TITANIUM:
        #         self.target_greedy = ore
        #         found_target = True
        #         print(f"[GREEDY | BACKTRACK] Found titanium ore at {ore} — setting as new target")
        #         break
        # if not found_target:
        #     nearby_buildings = ct.get_nearby_buildings()
        #     for b_id in nearby_buildings:
        #         if ct.get_entity_type(b_id) == EntityType.HARVESTER and ct.get_team(b_id) == self.our_team:
        #             harvester_pos = ct.get_position(b_id)
        #             if ct.get_tile_env(harvester_pos) == Environment.ORE_TITANIUM:
        #                 self.target_greedy = harvester_pos
        #                 found_target = True
        #                 print(f"[GREEDY | BACKTRACK] Found friendly harvester on titanium at {harvester_pos} — setting as new target")
        #                 break
        # if not found_target:
        #     print(f"[GREEDY | BACKTRACK] No titanium ore or friendly harvesters in sight — continuing to roam")
        #     self.mode = "ROOMBA"
        #     self.target_greedy = None
        
        # self.axionite_foundary_states = 4
        # if found_target:
        #     self.target_greedy = self.temp_pos_A_foundary
    if self.axionite_foundary_states == 2 and ct.get_action_cooldown() == 0:
        if ct.can_build_foundry(self.temp_pos_A_foundary):
            ct.build_foundry(self.temp_pos_A_foundary)
            print(f"[FOUNDRY] Built Axionite Foundry at {self.temp_pos_A_foundary}")
            self.axionite_foundary_states = 3
            return
        else:
            print(f"[FOUNDRY] Waiting — can't build foundry at {self.temp_pos_A_foundary} yet")
    # -------------------------------------------------------

    if self.bot_state == "HARVEST" or self.bot_state == "AXIONITER":

        if handle_vision_and_harvesting(self, ct, current_pos):
            print(f"[BUILDER RUN] Vision/harvesting consumed the turn")
            return

        active_goal = self.target_greedy or self.target_enemy_bridge or self.target_ore
        print(f"[BUILDER RUN] Active goal = {active_goal}")

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
            if ct.get_action_cooldown() == 0:
                goal = self.splitter_foundry_pos if self.axionite_foundary_states == 5 else self.ourcoord
                if ct.can_destroy(current_pos):
                    ct.destroy(current_pos)
                try_build_conveyor(self, ct, current_pos, goal)
                print(f"[BACKTRACK] Done — switching to GREEDY toward {goal}")
                self.mode = "GREEDY"
                self.target_greedy = goal
            else:
                print(f"[BACKTRACK] Waiting — action cooldown {ct.get_action_cooldown()}")
            return

        return

    elif self.bot_state == "ATTACK":
        print(f"[BUILDER RUN] ATTACK mode")
        find_the_enemy(self, ct)
        snipe_the_enemy(self, ct)

    elif self.bot_state == "HEALER":
        print(f"[BUILDER RUN] HEALER mode")
        healerrun(ct)