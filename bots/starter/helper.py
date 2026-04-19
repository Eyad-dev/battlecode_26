
from cambc import *


def distance_squared(pos1: Position, pos2: Position):
    return (pos1.x - pos2.x)**2 + (pos1.y - pos2.y)**2

def loopyloops(path, min_len=2, max_len=102):
    
    for seq_len in range(min_len, max_len + 1):
        if len(path) < seq_len * 2:
            continue
        
        current_cycle = path[-seq_len:]
        previous_cycle = path[-seq_len * 2 : -seq_len]
        
        if current_cycle == previous_cycle:
            return True, current_cycle
        
def onmap(ct: Controller, pos: Position ):
    width = ct.get_map_width()
    height = ct.get_map_height()
    return (0 <= pos.x < width and 0 <= pos.y < height)

def try_build_road(ct: Controller, tile_pos: Position):
    if ct.can_build_road(tile_pos) and ct.get_tile_env(tile_pos) != Environment.ORE_TITANIUM and ct.get_tile_env(tile_pos) != Environment.ORE_AXIONITE:
        ct.build_road(tile_pos)
        print(f"  [try_build_road] Built road at {tile_pos}")