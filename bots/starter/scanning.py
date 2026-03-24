from cambc import Controller, Direction, EntityType, GameConstants, Environment, Position

def scan_ore_vision(ct, gameconst):
    tiles= ct.get_nearby_tiles() 
    ores=[]
    for tile in tiles:
        if ct.get_tile_env(tile) == Environment.ORE_TITANIUM or ct.get_tile_env(tile) ==Environment.ORE_AXIONITE:
                    ores.append(tile)
    return ores

