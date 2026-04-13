from cambc import Controller, Direction, EntityType, GameConstants, Environment, Position


dir = ["x", "y", "r"]
def mirror(pos: Position, w,h, d):
    x= pos.x
    y= pos.y
    if d=="r": #180 rot
        return Position(w-1-x, h-1-y) 
    elif d=="x": #ref on x
        return Position(x, h-1-y)
    elif d == "y":
        return Position(w-1-x, y)
    else:
        raise ValueError(f"Invalid symmetry: {d}")

locked = None
possible = set(dir)

def movemode(self, ct:Controller, currentpos, destination=None):
    from builder import run_greedy_mode, run_bug_mode, run_roomba_mode
    if self.mode == "BUG":
        if run_bug_mode(self, ct,currentpos, destination):
            return

    if self.mode == "GREEDY":
        if run_greedy_mode(self, ct, currentpos, destination):
            return
    if self.mode == "ROOMBA":
        if run_roomba_mode(self, ct, currentpos):
            return

    return 




def check_symmetry(self, ct: Controller, tiles: list[Position]):
    global possible, locked
    if locked is not None:
        return locked, None

    if tiles is None:
        return locked, None

    width = ct.get_map_width()
    height = ct.get_map_height()
    mirroredpoints= []
    for pos in tiles:
        tile = ct.get_tile_env(pos)
        changedpos= possible.copy()

        for d in possible:  
            mirrored = mirror(pos, width, height, d)

            if not (0 <= mirrored.x < width and 0 <= mirrored.y < height):
                changedpos.discard(d)
                continue
            

            if not ct.is_in_vision(mirrored):
                mirroredpoints.append((pos, mirrored, tile, d))
                continue
            
            else:
                
                mirrored_tile = ct.get_tile_env(mirrored)

                if mirrored_tile != tile:
                    changedpos.discard(d)

                if len(changedpos) == 1:
                    locked = next(iter(changedpos))
                    print("Detected symmetry:", locked)
        
        possible = changedpos

    return locked, mirroredpoints 
#locked will be none if symmetry isnt determined yet
#otherwise it will be the detected symmetry
#mirrored points are the points that are in the vision but their mirror is not


def orient(self, ct: Controller):
    print("in orient")
    global possible, locked
    if self.current_target is None:
        pos, mirrored, tiletype, d = self.mirroredpoints[0]
        self.current_target = mirrored
        print(f"[TARGET LOCK] Locked target {self.current_target}")

    mirrored = self.current_target
    print(f"Checking point {pos} with mirror {mirrored} and tile type {tiletype}")

    if ct.is_in_vision( mirrored):
        if ct.get_tile_env(mirrored) != tiletype:
            possible.discard(d)
        self.mirroredpoints = [
            (pos, mirrored, tile, d)
            for pos, mirrored, tile, d in self.mirroredpoints
            if d in possible
        ]
        print("in mirrored")   
    else:
        currentpos= ct.get_position()
        if self.mode not in ["BUG", "WALL_JUMP"]:
            self.mode = "GREEDY"

        movemode(self, ct, currentpos, mirrored)
        return

    if len(possible)==1:
        locked= next(iter(possible))
        return

    
def find_local_ore(self, ct: Controller):
    if self.localorepos !=None:
        return
    
    tiles = ct.get_nearby_tiles()
    for tile in tiles:
        if ct.get_tile_env(tile)== Environment.ORE_TITANIUM:
            self.localorepos= tile
            return
    

def find_the_enemy(self, ct: Controller):

    if self.enemycoord!= None:
        return
    print("in find")
    find_local_ore(self, ct)
    tiles = ct.get_nearby_tiles()

    editedtiles= set(tiles)
    for tile in tiles:
        if ct.get_tile_env(tile)== Environment.EMPTY:
            editedtiles.discard(tile)
    
    tiles = list(editedtiles) 
    symmetry, farpoints = check_symmetry(self, ct, tiles)
    self.symmetry = symmetry

    if symmetry is not None:
        print ("celebrate")
        self.enemycoord = mirror(self.ourcoord, ct.get_map_width(), ct.get_map_height(), symmetry)
        if self.localorepos!= None:
            self.enemyore= mirror(self.localorepos, ct.get_map_width(), ct.get_map_height(), self.symmetry)
        print(self.enemycoord)
    elif farpoints is not None:
        if self.current_target is None:
            self.mirroredpoints = farpoints
            orient(self, ct)
        else:
            # keep going toward locked target
            movemode(self, ct, ct.get_position(), self.current_target)




def reach_enemy_ores(self, ct: Controller):
    if self.enemyore is None:
        return
    currentpos = ct.get_position()
    if not ct.is_in_vision(self.enemyore):
        print("moving to enemy ore")
        self.mode = "GREEDY"
        movemode(self, ct, currentpos, self.enemyore)
        return

    id = ct.get_tile_building_id(self.enemyore)
    harvester_checker = ct.get_entity_type(id)

    if harvester_checker == EntityType.HARVESTER:
        print("harvester exists")
        self.attack = "FIND"
        return
    distance_to_ore_sq = (currentpos.x - self.enemyore.x)**2 + (currentpos.y - self.enemyore.y)**2
    if distance_to_ore_sq <= 2:
        if ct.can_build_harvester(self.enemyore) and ct.get_action_cooldown() == 0:
            ct.build_harvester(self.enemyore)
            self.attack = "FIND"
            return
        elif ct.get_action_cooldown() > 0:
            return 
    self.mode = "GREEDY"
    movemode(self, ct, currentpos, self.enemyore)



def scan_field_for_bridges(self, ct:Controller):
    if self.bridges != None:
        return
    tiles = ct.get_nearby_tiles()
    bridges= set()
    for tile in tiles:
        if ct.get_entity_type(ct.get_tile_building_id(tile)) == EntityType.BRIDGE and self.our_team!= ct.get_team(ct.get_tile_building_id(tile)):
            bridges.add(tile)
    if len(bridges)>0:
        self.bridges= bridges 
        self.mode="GREEDY"
        self.attack= "GO"
    else:
        self.mode="ROOMBA"
        movemode(self, ct, ct.get_position())
        return


def move_to_enemy_bridge(self, ct:Controller, bridge:Position):
    if ct.get_position()!= bridge:
        movemode(self, ct, ct.get_position(), bridge )
        return
    else:
        self.attack= "DAMAGE"


def destroy_the_damn_bridge(self, ct:Controller):

    id = ct.get_tile_building_id(ct.get_position())
    if ct.get_entity_type(id) == EntityType.BRIDGE:
        if ct.can_fire(ct.get_position()):
            ct.fire(ct.get_position())
        return
    else:
        self.attack= "SENTINEL"
    


def place_sentinels(self, ct: Controller):
    if self.enemycoord is None or self.enemyore is None:
        return
    
    if ct.get_position() == self.nextsentinelpos:


        currentpos = ct.get_position()

        directions = [
            Direction.NORTH,
            Direction.SOUTH,
            Direction.EAST,
            Direction.WEST,
            Direction.NORTHEAST,
            Direction.NORTHWEST,
            Direction.SOUTHEAST,
            Direction.SOUTHWEST,
        ]

        for direction in directions:
            if ct.can_move(direction):
                ct.move(direction)

    else:
        dir = self.nextsentinelpos.direction_to(self.enemycoord)

        if ct.can_build_sentinel(self.nextsentinelpos, dir):
            print(f"placing sentinel at {self.nextsentinelpos} facing {dir}")
            self.sentinelsbuilt += 1

            ct.build_sentinel(self.nextsentinelpos, dir)
            return

        self.attack = "FIND"
        return






def snipe_the_enemy(self, ct):
    if self.enemycoord== None:
        return
    print("in snipe")
    if self.attack == None:
        print("reach ore")
        reach_enemy_ores(self, ct)
        return
    if self.attack == "FIND":
        print("in find")
        scan_field_for_bridges(self, ct)
        if self.bridges is not None and len(self.bridges) > 0:
            bridge = self.bridges.pop()       
            self.nextsentinelpos= bridge
            self.attack = "GO"

    elif self.attack == "GO":
        move_to_enemy_bridge(self, ct, self.nextsentinelpos)
    elif self.attack == "DAMAGE":
        destroy_the_damn_bridge(self, ct)
    elif self.attack == "SENTINEL":
        place_sentinels(self,ct)



    








#ARCHIVED SENTINEL LOGIV

# def reach_enemy_ores(self, ct: Controller):
#     if self.enemyore is None:
#         return

#     currentpos = ct.get_position()

#     if not ct.is_in_vision(self.enemyore):
#         print("moving to enemy ore")
#         movemode(self, ct, currentpos, self.enemyore)
#         return

#     id = ct.get_tile_building_id(self.enemyore)
#     harvester_checker = ct.get_entity_type(id)

#     if harvester_checker == EntityType.HARVESTER:
#         print("harvester exists")
#         self.attack = "SENTINEL"
#         return
#     distance_to_ore_sq = (currentpos.x - self.enemyore.x)**2 + (currentpos.y - self.enemyore.y)**2
#     if distance_to_ore_sq <= 2:
#         if ct.can_build_harvester(self.enemyore):
#             self.attack = "SENTINEL"
#             ct.build_harvester(self.enemyore)
#             return 

#     movemode(self, ct, currentpos, self.enemyore)







# def supply_ammo(self, ct: Controller):

#     if self.sentinelsbuilt == self.sentinelsconnected:
#         return

   


# def snipe_the_enemy(self, ct):
#     if self.enemycoord== None:
#         return
    
#     if self.attack != "SENTINEL":
#         reach_enemy_ores(self, ct)
#         return

#     print("i am alive")
#     place_sentinels(self, ct)
#     supply_ammo(self, ct)
    
    


