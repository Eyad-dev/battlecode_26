import random
from cambc import Controller, Direction, GameConstants, Position
from scanning import *
from snipe import *

def healerrun(self, ct: Controller):
    if ct.can_heal(self.ourcoord):
        ct.heal(self.ourcoord)

    ct.get_nearby_entities()