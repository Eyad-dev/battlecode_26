from cambc import Controller, Direction, EntityType, GameConstants, Environment, Position

def scan_ore_vision(ct:Controller, gameconst):
    tiles= ct.get_nearby_tiles() 
    entities = ct.get_nearby_entities()
    ores=[]
    for tile in tiles:
        if ct.get_tile_env(tile) == Environment.ORE_TITANIUM:
                    if ct.get_tile_building_id(tile) is None:
                        ores.append(tile)
    return ores

