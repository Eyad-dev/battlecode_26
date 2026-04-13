
from cambc import Position


def distance_squared(pos1: Position, pos2: Position):
    return (pos1.x - pos2.x)**2 + (pos1.y - pos2.y)**2