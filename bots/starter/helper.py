
from cambc import Position


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