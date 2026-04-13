import random
from cambc import Controller, Direction, GameConstants, Position
from scanning import *
from snipe import *

def healerrun(self, ct: Controller):
    nearby_entities = ct.get_nearby_entities()
    for entity in nearby_entities:
        if ct.get_type(entity) == EntityType.BUILDER_BOT and ct.get_team(entity) == self.our_team:
            if ct.get_hp(entity) < ct.get_max_hp(entity):
                if ct.can_heal(ct.get_position(entity)):
                    ct.heal(ct.get_position(entity))
        if ct.get_type(entity) == EntityType.CORE and ct.get_team(entity) == self.our_team:
            if ct.get_hp(entity) < ct.get_max_hp(entity):
                if ct.can_heal(ct.get_position(entity)):
                    ct.heal(ct.get_position(entity))
    