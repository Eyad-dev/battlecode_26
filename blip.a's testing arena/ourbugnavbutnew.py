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
            self.bugnav.currentDir = test_dir          # ✅ keep bugnav in sync
            self.bugnav.lastObstacleFound = None        # ✅ moved freely, no obstacle
            print(f"[BUG] Moved {test_dir} to {test_pos}")
            return True
        else:
            self.bugnav.lastObstacleFound = test_pos   # ✅ record what's blocking us
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
                return True
        test_dir = rotate(test_dir, 1)

    print(f"[BUG] Completely trapped — waiting")
    return True