from cambc import *
from helper import *
import math

# Map tile type -> max HP using GameConstants
TILE_MAX_HP = {
    "CORE":               GameConstants.CORE_MAX_HP,
    "BUILDER_BOT":        GameConstants.BUILDER_BOT_MAX_HP,
    "CONVEYOR":           GameConstants.CONVEYOR_MAX_HP,
    "SPLITTER":           GameConstants.SPLITTER_MAX_HP,
    "BRIDGE":             GameConstants.BRIDGE_MAX_HP,
    "ARMOURED_CONVEYOR":  GameConstants.ARMOURED_CONVEYOR_MAX_HP,
    "HARVESTER":          GameConstants.HARVESTER_MAX_HP,
    "ROAD":               GameConstants.ROAD_MAX_HP,
    "BARRIER":            GameConstants.BARRIER_MAX_HP,
    "FOUNDRY":            GameConstants.FOUNDRY_MAX_HP,
    "MARKER":             GameConstants.MARKER_MAX_HP,
    "GUNNER":             GameConstants.GUNNER_MAX_HP,
    "SENTINEL":           GameConstants.SENTINEL_MAX_HP,
    "BREACH":             GameConstants.BREACH_MAX_HP,
    "LAUNCHER":           GameConstants.LAUNCHER_MAX_HP,
}

class OrbitBot:

    ORBIT_RADIUS_SQ = 32
    orbit_points: list[Position] = []
    current_target_idx: int = 0

    def __init__(self):
        self.core: Position | None = None
        print("[OrbitBot] initialized")

    def set_core(self, core: Position):
        self.core = core
        OrbitBot.orbit_points = self.compute_orbit_points()
        print(f"[OrbitBot] core set to {core}, {len(OrbitBot.orbit_points)} orbit points computed")


    def compute_orbit_points(self) -> list[Position]:
        r = int(math.sqrt(self.ORBIT_RADIUS_SQ)) + 1
        cx, cy = self.core.x, self.core.y
        candidates = []
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                dsq = dx * dx + dy * dy
                if abs(dsq - self.ORBIT_RADIUS_SQ) <= 6:
                    candidates.append((dx, dy))
        candidates.sort(key=lambda p: math.atan2(p[1], p[0]))
        return [Position(cx + dx, cy + dy) for dx, dy in candidates]


    def find_damaged_tile(self, ct: Controller) -> tuple[Position, str] | None:

        nearby= ct.get_nearby_tiles()
        tiletype=[]
        for tile in nearby:
            id = ct.get_tile_building_id(tile)
            if ct.get_entity_type(id) == EntityType.BRIDGE or ct.get_entity_type(id) == EntityType.CONVEYOR or ct.get_entity_type(id) == EntityType.ROAD:
                type= ct.get_entity_type(id)
                tiletype.append((tile, type))


        for pos, tile_type in tiletype:
            max_hp = TILE_MAX_HP.get(tile_type.name)
            if max_hp is None:
                continue
            tile_id = ct.get_tile_builder_bot_id(pos)
            if tile_id is None:
                tiletype.remove((pos, tile_type))
                continue
            hp = ct.get_hp(tile_id)
            if hp < max_hp:
                print(f"[OrbitBot] damaged tile found: {tile_type} at {pos}, hp={hp}/{max_hp}")
                return (pos, tile_type)
        return None


    def move_adjacent_to(self, ct: Controller, target: Position):
        if distance_squared(ct.get_position(), target) <= 2:
            return  # already adjacent
        dir = ct.get_position().direction_to(target)
        try_build_road(ct, ct.get_position().add(dir))
        if ct.can_move(dir):
            ct.move(dir)
            print(f"[OrbitBot] moving toward damaged tile at {target}")
        else:
            # Try rotating once each way to get unstuck
            for candidate in [dir.rotate_left(), dir.rotate_right()]:
                if ct.can_move(candidate):
                    ct.move(candidate)
                    print(f"[OrbitBot] unstuck move {candidate} toward {target}")
                    break

    def try_heal(self, ct: Controller, pos: Position) -> bool:
        if ct.can_heal(pos):
            ct.heal(pos)
            print(f"[OrbitBot] healed tile at {pos}")
            return True
        return False

    def orbit_step(self, ct: Controller):
        if not OrbitBot.orbit_points:
            return

        target = OrbitBot.orbit_points[OrbitBot.current_target_idx]

        if distance_squared(ct.get_position(), target) <= 2:
            OrbitBot.current_target_idx = (OrbitBot.current_target_idx + 1) % len(OrbitBot.orbit_points)
            target = OrbitBot.orbit_points[OrbitBot.current_target_idx]

        if not onmap(ct, target):
            OrbitBot.current_target_idx = (OrbitBot.current_target_idx + 1) % len(OrbitBot.orbit_points)
            return

        dir = ct.get_position().direction_to(target)
        try_build_road(ct, ct.get_position().add(dir))
        if ct.can_move(dir):
            ct.move(dir)
        else:
            OrbitBot.current_target_idx = (OrbitBot.current_target_idx + 1) % len(OrbitBot.orbit_points)


    def thelastdance(self, ct: Controller):
        if self.core is None:
            print("[OrbitBot] no core set, skipping")
            return

        damaged = self.find_damaged_tile(ct)

        if damaged is not None:
            pos, tile_type = damaged
            self.move_adjacent_to(ct, pos)
            self.try_heal(ct, pos)
        else:
            self.orbit_step(ct)