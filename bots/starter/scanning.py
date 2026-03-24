from cambc import Controller, Direction, EntityType, GameConstants, Environment, Position

def scan_ore_vision(ct, gameconst):
    ores=[]
    rangesquare = gameconst
    ranged= (int)(rangesquare**0.5)
    for x in range(-ranged, ranged + 1):
        for y in range(-ranged, ranged + 1):
            if x**2 + y**2 <= rangesquare:
                newposx = ct.get_position().x +x
                newposy = ct.get_position().y +y
                pos = Position(newposx, newposy)
                if ct.get_tile_env(pos) == Environment.ORE_TITANIUM or ct.get_tile_env(pos) ==Environment.ORE_AXIONITE:
                    ores.append(pos)
    return ores

