from cambc import Controller, Direction, EntityType, GameConstants, Environment, Position

def wrath(self, ct, pos: Position):
    if ct.can_fire(pos):
        ct.fire(pos)
    return

def gunnerrun(self, ct:Controller):
    wrath(self, ct, ct.get_gunner_target())
