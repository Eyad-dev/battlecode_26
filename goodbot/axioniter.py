from cambc import *
from builder import*


def axioniterrun(self,ct):
    current_pos = ct.get_position()
     # -------------------------------------------------------
    # FOUNDRY BUILD CHECK — runs every turn, no matter mode!
    # -------------------------------------------------------
    #I want when the bot finds now a titanium ore after finishing the ROOMBA in axionite_foundary_states == 3, in 4 I want to now go back to the foundary position (building conveyors to there) (found at self.temp_pos_A_foundary) and set this as my target_greedy, I need to connect that titanium ore that I found back to the foundary with conveyors and then when I arrive at the foundary position I want to go back to roomba

    if self.axionite_foundary_states == 5:
        conveyor_dir = cardinal_toward_base(current_pos, self.splitter_foundry_pos)
        next_pos = current_pos.add(conveyor_dir)

        if next_pos == self.splitter_foundry_pos:
            if ct.get_action_cooldown() == 0:
                existing = ct.get_tile_building_id(current_pos)
                if existing is not None and ct.can_destroy(current_pos):
                    ct.destroy(current_pos)
                    print(f"[BRIDGE] Destroyed conveyor at {current_pos}")
                if ct.can_fire(current_pos):
                    ct.fire(current_pos)
                    print(f"[BRIDGE] Fired at building on current tile {current_pos} to clear way for bridge")
                if ct.can_build_bridge(current_pos, self.splitter_foundry_pos):
                    ct.build_bridge(current_pos, self.splitter_foundry_pos)
                    print(f"[BRIDGE] Built bridge to splitter at {self.splitter_foundry_pos}")
                    self.axionite_foundary_states = -1
                    self.mode = "ROOMBA"
                    self.target_greedy = None
                else:
                    print(f"[BRIDGE] Can't build bridge yet")
            else:
                print(f"[BRIDGE] Waiting — cooldown {ct.get_action_cooldown()}")
            return

        if ct.get_action_cooldown() == 0:
            built_conveyor = try_build_conveyor(self, ct, next_pos, self.splitter_foundry_pos)
            if built_conveyor and ct.can_move(conveyor_dir):
                ct.move(conveyor_dir)
                print(f"[STATE5] Moving {conveyor_dir} toward splitter")
            else:
                if ct.get_entity_type(ct.get_tile_building_id(next_pos)) == EntityType.CONVEYOR and ct.get_team(ct.get_tile_building_id(next_pos)) == self.our_team:
                    if ct.can_destroy(current_pos) and ct.get_entity_type(ct.get_tile_building_id(current_pos)) == EntityType.CONVEYOR:
                        ct.destroy(current_pos)
                        print(f"[BRIDGE] Destroyed conveyor at {current_pos} for bridge placement")
                    if ct.can_build_bridge(current_pos, self.splitter_foundry_pos):
                        ct.build_bridge(current_pos, self.splitter_foundry_pos)
                        print(f"[BRIDGE] Built bridge to splitter at {self.splitter_foundry_pos}")
                        self.axionite_foundary_states = -1
                        self.mode = "ROOMBA"
                        self.target_greedy = None
                    print(f"[STATE5] Riding existing conveyor {conveyor_dir} toward splitter")
                print(f"[STATE5] Can't move {conveyor_dir} — blocked")
        return

    if self.axionite_foundary_states == 4:
        # Just roaming — the normal HARVEST flow below handles ore detection.
        # Once a harvester is built, handle_vision_and_harvesting sets mode=BACKTRACK
        # and target_greedy=ourcoord. We intercept that here.
        if self.mode == "BACKTRACK" or (self.mode == "GREEDY" and self.target_greedy == self.ourcoord):
            print(f"[STATE4] Harvester built — redirecting backtrack to splitter")
            self.axionite_foundary_states = 5
            self.target_greedy = None
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
    if self.axionite_foundary_states == 2 and ct.get_action_cooldown() == 0:
        if ct.can_build_foundry(self.temp_pos_A_foundary):
            ct.build_foundry(self.temp_pos_A_foundary)
            print(f"[FOUNDRY] Built Axionite Foundry at {self.temp_pos_A_foundary}")
            self.axionite_foundary_states = 3
            return
        else:
            print(f"[FOUNDRY] Waiting — can't build foundry at {self.temp_pos_A_foundary} yet")

    inaxioniter


def inaxioniter(self,ct : Controller):
    current_pos = ct.get_position()
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
                goal = self.splitter_foundry_pos if self.axionite_foundary_states == 5 and self.bot_state == "AXIONITER" else self.ourcoord
                try_build_conveyor(self, ct, current_pos, goal)
                print(f"[BACKTRACK] Done — switching to GREEDY toward {goal}")
                self.mode = "GREEDY"
                self.target_greedy = goal
            else:
                print(f"[BACKTRACK] Waiting — action cooldown {ct.get_action_cooldown()}")
            return
    