from cambc import Controller, Direction, EntityType, GameConstants, Environment, Position

def wrath(self, ct, pos: Position):
    if ct.can_fire(pos):
        ct.fire(pos)
    return


def sentinelrun(self, ct:Controller):
    if self.enemycoord != None:
        print(f"[SENTINEL] Firing at enemy core at {self.enemycoord}")
        wrath(self, ct, self.enemycoord)
        return
    if self.snipecoord == None and self.snipe:
        self.snipecoord== self.snipe.pop()

    if self.snipecoord != None:
        self.snipecoord= None
        wrath(self, ct, self.snipecoord)
        return

    
    tiles= ct.get_nearby_tiles()
    attackable = ct.get_attackable_tiles()
    for tile in tiles:
        id = ct.get_tile_building_id(tile)
        checker = ct.get_entity_type(id)
        if checker == EntityType.CORE and tile in attackable:
            self.enemycoord= tile
            wrath(self, ct, self.enemycoord)
            return
        else:
            self.our_team!= ct.get_team(ct.get_tile_building_id(tile))
            self.snipe.append(tile)