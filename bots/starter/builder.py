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


def try_build_conveyor(ct: Controller, tile_pos: Position, base_pos: Position):
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
    if ct.get_entity_type(ct.get_tile_building_id(tile_pos.add(direction))) == EntityType.MARKER:
        direction = rotate(direction, 2)
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
# MODULARIZED STATE FUNCTIONS
# ==========================================

def handle_vision_and_harvesting(self, ct: Controller, current_pos: Position) -> bool:
    print(f"[VISION] Mode={self.mode} | Pos={current_pos} | target_ore={self.target_ore} | target_greedy={self.target_greedy} | target_enemy_bridge={self.target_enemy_bridge}")

    if self.mode == "ROOMBA":
        ores = scan_ore_vision(ct, GameConstants.BUILDER_BOT_VISION_RADIUS_SQ)
        for ore_pos in ores:
            if (ct.get_tile_env(ore_pos) == Environment.ORE_AXIONITE and self.axionite_foundary_states == 0):
                print(f"[VISION] Axionite ore spotted at {ore_pos} — prioritizing for harvest")
                self.target_ore = ore_pos
                self.mode = "GREEDY"
                self.axionite_foundary_states = 1
                return True
        if ores:
            self.target_ore = ores[0]
            existing = ct.get_tile_building_id(self.target_ore)
            if existing is not None and ct.get_entity_type(existing) == EntityType.HARVESTER:
                print(f"[VISION] Ore at {self.target_ore} already has a harvester, skipping to next")
                ores.pop(0)
                self.target_ore = ores[0]
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
                            # Switch to BACKTRACK mode to handle conveyor building with destroyed road
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
            #bool is_enemy_road = b_id is not None and ct.get_entity_type(b_id) == EntityType.ROAD and ct.get_team(b_id) != self.our_team
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
        self.hit_distance = 999999
        return False

    self.bugnav.move_towards(ct, goal_pos)
    return True


def run_greedy_mode(self, ct: Controller, current_pos: Position, goal_pos: Position) -> bool:
    current_dist_sq = (current_pos.x - goal_pos.x)**2 + (current_pos.y - goal_pos.y)**2
    # ---- BACKTRACK TO BASE: build conveyors on the way back ----
    if goal_pos == self.ourcoord:
        conveyor_dir = cardinal_toward_base(current_pos, self.ourcoord)
        print(f"[GREEDY | BACKTRACK] At {current_pos} | conveyor dir={conveyor_dir}")
        
        # Build conveyor on the NEXT tile toward base (so we can walk onto it)
        next_pos = current_pos.add(conveyor_dir)
        built_conveyor = False
        if ct.get_action_cooldown() == 0:
            if(ct.get_team(ct.get_tile_building_id(current_pos)) != self.our_team):
                if ct.can_fire(current_pos):
                    ct.fire(current_pos)
                    print(f"[GREEDY | BACKTRACK] Fired at enemy building on current tile {current_pos} to clear way for conveyor")
                else:
                    print(f"[GREEDY | BACKTRACK] Can't fire at enemy building on current tile {current_pos} — cooldown {ct.get_action_cooldown()}")
            else:  
                built_conveyor = try_build_conveyor(ct, next_pos, self.ourcoord)

        # Move toward base onto the conveyor we just built
        if built_conveyor and ct.can_move(conveyor_dir):
            ct.move(conveyor_dir)
            print(f"[GREEDY | BACKTRACK] Moved {conveyor_dir} onto conveyor")
        else:
            # Could be facing another bridge already built, first confirm if its on our side, if its not, we move to that tile first, then on the next turn we fire at it (since we will be standing on it, we can only fire if we are standing on it), if its ours, we know have (PROBABLY) made a joint highway connection back to our core so good
            if(ct.get_team(ct.get_tile_building_id(current_pos.add(conveyor_dir))) != self.our_team):
                if (ct.can_move(conveyor_dir)):
                    ct.move(conveyor_dir)
            #If its on our side, then we made a joint and we can just roomba from here, we don't need to backtrack anymore, we are already getting our source, so switch to roomba to find more ores and not get stuck on the joint
            elif(ct.get_entity_type(ct.get_tile_building_id(current_pos.add(conveyor_dir))) == EntityType.CONVEYOR and ct.get_team(ct.get_tile_building_id(current_pos.add(conveyor_dir))) == self.our_team):
                self.target_greedy = None
                self.mode = "ROOMBA"
                return True
            #Now we want to get a source of titanium and connect it to the foundary we just build when axionite_foundary_state was equal to 2, so we will roomba until we find a titanium ore or a harvester then connect it to the foundary, so we need to set our target after getting the titanium ore to the foundary 
            #Copilot for gods sake, what do you think is the problem
            #cmon tell me
            #You forgot to set the target_greedy to the foundary after finding the titanium ore, so it keeps trying to backtrack to the core instead of going to the foundary to get the source for the foundary, you dummy
            if (self.axionite_foundary_states == 3):
                ores = scan_ore_vision(ct, GameConstants.BUILDER_BOT_VISION_RADIUS_SQ)
                found_target = False
                for ore in ores:
                    if ct.get_tile_env(ore) == Environment.ORE_TITANIUM:
                        self.target_greedy = ore
                        found_target = True
                        print(f"[GREEDY | BACKTRACK] Found titanium ore at {ore} — setting as new target")
                        break
                if not found_target:
                    # Check for harvesters if no titanium visible
                    nearby_buildings = ct.get_nearby_buildings()
                    for b_id in nearby_buildings:
                        if ct.get_entity_type(b_id) == EntityType.HARVESTER and ct.get_team(b_id) == self.our_team:
                            harvester_pos = ct.get_position(b_id)
                            if ct.get_tile_env(harvester_pos) == Environment.ORE_TITANIUM:
                                self.target_greedy = harvester_pos
                                found_target = True
                                print(f"[GREEDY | BACKTRACK] Found friendly harvester on titanium at {harvester_pos} — setting as new target")
                                break
                if not found_target:
                    print(f"[GREEDY | BACKTRACK] No titanium ore or friendly harvesters in sight — continuing to roam")

            if (self.axionite_foundary_states == 2):
                if ct.can_build_foundry(self.temp_pos_A_foundary):
                    ct.build_foundry(self.temp_pos_A_foundary)
                    print(f"[GREEDY | BACKTRACK] Built Axionite Foundry at {self.temp_pos_A_foundary}")
                    self.axionite_foundary_states = 3   
            #destorying the last conveyor for the Foundary
            if (next_pos in self.core_tiles and self.axionite_foundary_states == 1):
                self.axionite_foundary_states = 2
                splitter_pos = current_pos
                for d in DIRECTIONS:
                    if ct.can_move(d) :
                        self.temp_pos_A_foundary = current_pos.add(d)
                        ct.move(d)
                        break
                if ct.can_destroy(splitter_pos):
                    ct.destroy(splitter_pos)
                    print(f"[GREEDY | BACKTRACK] Destroyed conveyor at {splitter_pos} to free up core tile for splitter")
                return True
            
                

             
            
            if (next_pos in self.core_tiles):
                self.target_greedy = None
                self.mode = "ROOMBA"
                return True
            else:
                print(f"[GREEDY | BACKTRACK] Can't move {conveyor_dir} — blocked or conveyor not built")
                # Check if blocked by wall, initiate wall-jump
                if (is_wall_tile(ct, next_pos) or ct.get_tile_env(next_pos) == Environment.ORE_TITANIUM or ct.get_tile_env(next_pos) == Environment.ORE_AXIONITE or ct.get_entity_type(ct.get_tile_building_id(next_pos)) == EntityType.HARVESTER):
                    landing = find_bridge_target(self, ct, current_pos, self.ourcoord, conveyor_dir)
                    print(f"[GREEDY | BACKTRACK] Detected wall at {next_pos} — trying wall jump to {landing}")
                    if landing and ct.get_action_cooldown() == 0:
                        bridge_cost = ct.get_bridge_cost()[0]
                        print("WE RE ABLE TO FIND A LANDING SPOT FOR THE BRIDGE")
                        if ct.get_global_resources()[0] >= bridge_cost:
                            #check if there is a road beneath us to destroy for bridge placement
                            print("WE DID REACH HERE")
                            
                            if ct.can_destroy(current_pos) and ct.get_entity_type(ct.get_tile_building_id(current_pos)) == EntityType.CONVEYOR:
                                ct.destroy(current_pos)
                                print(f"WALL_JUMP: Destroyed road at {current_pos} for bridge placement")

                            if ct.can_build_bridge(current_pos, landing):
                                ct.build_bridge(current_pos, landing)
                                #Check if the bridge landing was on one of the core tiles and if so, We won't continue and bug nav back to base, its already getting its source now, so roomba
                                if (landing in self.core_tiles or ct.get_entity_type(ct.get_tile_building_id(landing)) == EntityType.CONVEYOR):
                                    print(f"WALL_JUMP: Bridge landing {landing} is a core tile — switching to ROOMBA")
                                    self.target_greedy = None
                                    self.mode = "ROOMBA"
                                    return True
                                print(f"WALL_JUMP: Built bridge from {current_pos} to {landing}")
                                self.wall_jump_landing = landing
                                landing_dist_sq = (current_pos.x - landing.x)**2 + (current_pos.y - landing.y)**2
                                self.hit_distance = landing_dist_sq
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
                and env != Environment.ORE_AXIONITE:
            best_valid_dist = dist_sq
            best_dir = d
            best_pos = hyp_pos
            break

    print(f"[GREEDY] Best move: dir={best_dir} | pos={best_pos} | dist²={best_valid_dist}")

    # TRAP DETECTION
    if best_valid_dist > current_dist_sq and best_valid_dist:
        # Check if blocked by a friendly bot
        nearby_entities = ct.get_nearby_entities()
        blocked_by_bot = False
        for entity_id in nearby_entities:
            if ct.get_position(entity_id) == best_pos:
                entity_type = ct.get_entity_type(entity_id)
                if entity_type in [EntityType.BUILDER_BOT, EntityType.SENTINEL]:
                    blocked_by_bot = True
                    break
        
        if blocked_by_bot:
            print(f"[GREEDY] Blocked by friendly bot at {best_pos} — Waiting")
            return True

        print(f"[GREEDY] Trapped — best dist² {best_valid_dist} > current {current_dist_sq} — switching to BUG")
        self.mode = "BUG"
        self.hit_distance = current_dist_sq
        self.wall_follow_direction = best_dir if best_dir else current_pos.direction_to(goal_pos)
        return True
    else:
        # Build road on next tile so we can walk on it
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
    
    # Bug nav to the landing spot
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

    if self.bot_state == "HARVEST":

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
            # Lay conveyor on current tile then switch to GREEDY toward base
            if ct.get_action_cooldown() == 0:
                try_build_conveyor(ct, current_pos, self.ourcoord)
                print(f"[BACKTRACK] Done — switching to GREEDY toward base")
                self.mode = "GREEDY"
                self.target_greedy = self.ourcoord
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