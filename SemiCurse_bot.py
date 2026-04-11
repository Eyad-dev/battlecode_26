import random
from cambc import Controller, Direction, GameConstants, Position
from scanning import *
from snipe import *

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
            return False
        else:
            print(f"  [try_build_conveyor] Can't fire at enemy road at {tile_pos} — cooldown {ct.get_action_cooldown()}")
            return False
    direction = cardinal_toward_base(tile_pos, base_pos)
    if ct.can_build_conveyor(tile_pos, direction):
        ct.build_conveyor(tile_pos, direction)
        print(f"  [try_build_conveyor] Built at {tile_pos} → {direction}")
        return True
    print(f"  [try_build_conveyor] Failed at {tile_pos} dir {direction}")
    return False

def find_bridge_target(self, ct: Controller, current_pos: Position, goal_pos: Position, conveyor_dir: Direction):
    # Find a suitable bridge target, preferring positions beyond walls in the conveyor direction
    # First, try to find a position directly beyond the wall in conveyor_dir
    pos = current_pos
    wall_found = False
    for _ in range(5):  # Check up to 5 tiles ahead for wall
        pos = pos.add(conveyor_dir)
        if not (0 <= pos.x < ct.get_map_width()) or not (0 <= pos.y < ct.get_map_height()):
            break
        if is_wall_tile(ct, pos):
            wall_found = True
            break
    
    if wall_found:
        # Look for empty tiles beyond the wall
        for i in range(1, 4):  # Up to 3 tiles beyond wall
            target_pos = pos
            for _ in range(i):
                target_pos = target_pos.add(conveyor_dir)
            if not (0 <= target_pos.x < ct.get_map_width()) or not (0 <= target_pos.y < ct.get_map_height()):
                continue
            if not is_wall_tile(ct, target_pos) and ct.get_tile_building_id(target_pos) is None:
                dist_to_goal = (target_pos.x - goal_pos.x)**2 + (target_pos.y - goal_pos.y)**2
                if dist_to_goal > 2:  # Not on core
                    print(f"  [find_bridge_target] Found beyond wall: {target_pos}")
                    return target_pos
    
    # Fallback: original logic
    best_target = None
    min_dist = 99999
    for dx, dy in BRIDGE_TILES:
        target_pos = Position(current_pos.x + dx, current_pos.y + dy)
        if not (0 <= target_pos.x < ct.get_map_width()) or not (0 <= target_pos.y < ct.get_map_height()):
            continue
        if ct.get_tile_env(target_pos) == Environment.WALL:
            continue
        if ct.get_tile_building_id(target_pos) is not None:
            continue
        print(f"  [find_bridge_target] Checking {target_pos}")
        print(f"    Env: {ct.get_tile_env(target_pos)} | Building: {ct.get_tile_building_id(target_pos)}")
        dist_to_goal = (target_pos.x - goal_pos.x)**2 + (target_pos.y - goal_pos.y)**2
        if dist_to_goal < min_dist and dist_to_goal > 2:
            min_dist = dist_to_goal
            best_target = target_pos
    print(f"  [find_bridge_target] Selected fallback: {best_target}")
    return best_target

def is_wall_tile(ct: Controller, pos: Position):
    if not (0 <= pos.x < ct.get_map_width()) or not (0 <= pos.y < ct.get_map_height()):
        return True
    env = ct.get_tile_env(pos)
    return env == Environment.WALL


# ==========================================
# MODULARIZED STATE FUNCTIONS
# ==========================================

def handle_vision_and_harvesting(self, ct: Controller, current_pos: Position) -> bool:
    print(f"[VISION] Mode={self.mode} | Pos={current_pos} | target_ore={self.target_ore} | target_greedy={self.target_greedy} | target_enemy_bridge={self.target_enemy_bridge}")

    if self.mode == "ROOMBA":
        ores = scan_ore_vision(ct, GameConstants.BUILDER_BOT_VISION_RADIUS_SQ)
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

            if env == Environment.ORE_TITANIUM:
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

    # Scenario C: Enemy bridge raiding
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
                            self.mode = "GREEDY"
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

    print(f"[BUG] Still wall-following | wall_dir={self.wall_follow_direction}")
    check_ore_direction = current_pos.direction_to(goal_pos)
    test_dir = rotate(self.wall_follow_direction, -2)

    if ((current_pos.x - goal_pos.x == 0 or current_pos.y - goal_pos.y == 0) or
            (current_pos.x - goal_pos.x == current_pos.y - goal_pos.y)) and (current_dist_sq <= 20):
        print(f"[BUG] Orthogonal/diagonal alignment check triggered")
        temp_dir = rotate(self.wall_follow_direction, 2)
        if temp_dir == check_ore_direction:
            print(f"[BUG] Direction correction applied")
            test_dir = rotate(self.wall_follow_direction, 2)

    for _ in range(8):
        test_pos = current_pos.add(test_dir)
        print(f"[BUG] Trying dir={test_dir} | pos={test_pos} | can_build_road={ct.can_build_road(test_pos)}")
        if ct.can_build_road(test_pos):
            try_build_road(ct, test_pos)
            self.wall_follow_direction = test_dir
        if ct.can_move(test_dir):
            ct.move(test_dir)
            print(f"[BUG] Moved {test_dir} to {test_pos}")
            return True
        else:
            # Check if blocked by a friendly bot
            nearby_entities = ct.get_nearby_entities()
            blocked_by_bot = False
            for entity_id in nearby_entities:
                if ct.get_position(entity_id) == test_pos:
                    entity_type = ct.get_entity_type(entity_id)
                    if entity_type in [EntityType.BUILDER_BOT, EntityType.SENTINEL]:
                        blocked_by_bot = True
                        break
            if blocked_by_bot:
                print(f"[BUG] Blocked by friendly bot at {test_pos} — switching to ROOMBA")
                self.mode = "ROOMBA"
                return True
        test_dir = rotate(test_dir, 1)

    print(f"[BUG] Completely trapped — waiting")
    return True


def run_greedy_mode(self, ct: Controller, current_pos: Position, goal_pos: Position) -> bool:

    # ---- BACKTRACK TO BASE: build conveyors on the way back ----
    if goal_pos == self.ourcoord:
        conveyor_dir = cardinal_toward_base(current_pos, self.ourcoord)
        print(f"[GREEDY | BACKTRACK] At {current_pos} | conveyor dir={conveyor_dir}")
        
        # Build conveyor on the NEXT tile toward base (so we can walk onto it)
        next_pos = current_pos.add(conveyor_dir)
        built_conveyor = False
        if ct.get_action_cooldown() == 0:
            built_conveyor = try_build_conveyor(ct, next_pos, self.ourcoord)

        # Move toward base onto the conveyor we just built
        if built_conveyor and ct.can_move(conveyor_dir):
            ct.move(conveyor_dir)
            print(f"[GREEDY | BACKTRACK] Moved {conveyor_dir} onto conveyor")
        else:
            print(f"[GREEDY | BACKTRACK] Can't move {conveyor_dir} — blocked or conveyor not built")
            # Check if blocked by wall, initiate wall-jump
            if is_wall_tile(ct, next_pos):
                landing = find_bridge_target(self, ct, current_pos, self.ourcoord, conveyor_dir)
                if landing and ct.get_action_cooldown() == 0:
                    bridge_cost = ct.get_bridge_cost()[0]
                    if ct.get_global_resources()[0] >= bridge_cost:
                        if ct.can_build_bridge(current_pos, landing):
                            ct.build_bridge(current_pos, landing)
                            print(f"WALL_JUMP: Built bridge from {current_pos} to {landing}")
                            self.wall_jump_active = True
                            self.wall_jump_landing = landing
                            self.mode = "WALL_JUMP"
                            return True
                        if ct.can_build_bridge(current_pos, landing):
                            ct.build_bridge(current_pos, landing)
                            print(f"WALL_JUMP: Built bridge from {current_pos} to {landing}")
                            self.wall_jump_active = True
                            self.wall_jump_landing = landing
                            self.mode = "WALL_JUMP"
                            return True

        return True

    # ---- NORMAL GREEDY: build roads on the way to ore ----
    current_dist_sq = (current_pos.x - goal_pos.x)**2 + (current_pos.y - goal_pos.y)**2
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
            print(f"[GREEDY] Blocked by friendly bot at {best_pos} — switching to ROOMBA")
            self.mode = "ROOMBA"
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
        self.wall_jump_active = False
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