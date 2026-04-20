from cambc import Controller, Direction, EntityType, GameConstants, Environment, Position, ResourceType
from helper import *
from bugnav import *
from builder import run_bug_mode,run_greedy_mode,run_roomba_mode, run_wall_jump_mode


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
    if destination == None:
        run_roomba_mode(self, ct, currentpos)
        return

    else:
        self.nav.moveto(ct, destination)
        return

def unlockedenemy(self, ct:Controller):
    self.unlockedenemycoord= mirror(self.ourcoord, ct.get_map_width(), ct.get_map_height(), "r")


def reachunlockedenemycoord(self, ct: Controller):
    currentpos = ct.get_position()
    if not ct.is_in_vision(self.unlockedenemycoord):
        print("moving to enemy core")
        self.prevpos = currentpos
        self.turnstaken = 0
        movemode(self, ct, currentpos, self.unlockedenemycoord)
        return
    elif ct.is_in_vision(self.unlockedenemycoord):
        if ct.get_entity_type(ct.get_tile_building_id(self.unlockedenemycoord))== EntityType.CORE:
            self.enemycoord = self.unlockedenemycoord  
        else:
            if "x" in possible:
                self.unlockedenemycoord = mirror(self.ourcoord, ct.get_map_width(), ct.get_map_height(), "x")
            elif "y" in possible:
                self.unlockedenemycoord = mirror(self.ourcoord, ct.get_map_width(), ct.get_map_height(), "y")
    return


def check_symmetry(self, ct: Controller):
    global possible, locked
    if locked is not None:
        return locked, None
    

    tiles = ct.get_nearby_tiles()
    editedtiles= set(tiles)
    for tile in tiles:
        if ct.get_tile_env(tile)== Environment.EMPTY:
            editedtiles.discard(tile)

    tiles= set(editedtiles)
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
    tiles = ct.get_nearby_tiles()
    for tile in tiles:
        if tile in self.mirroredpoints:
            for entry in self.mirroredpoints:
                if mirrored == tile:
                    pos, mirrored, tiletype, d = entry    
            print(f"Checking point {pos} with mirror {mirrored} and tile type {tiletype}")
            if ct.get_tile_env(mirrored) != tiletype:
                possible.discard(d)
                self.mirroredpoints = [
                    (pos, mirrored, tile, d)
                    for pos, mirrored, tile, d in self.mirroredpoints
                    if d in possible
                ]
                if d == "r":
                    print("panik")
                    self.unlockedenemycoord= (self.ourcoord, ct.get_map_width(), ct.get_map_height(), "x")
                elif d == "x" and "r" not in possible:
                    self.unlockedenemycoord= (self.ourcoord, ct.get_map_width(), ct.get_map_height(), "y")



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
    
def find_exploration_target(self, ct: Controller):
    width = ct.get_map_width()
    height = ct.get_map_height()

    candidates = [
        Position(0, 0),
        Position(width - 1, 0),
        Position(0, height - 1),
        Position(width - 1, height - 1),
        Position(width // 2, height // 2),
    ]
    
    for pos in candidates:
        if not ct.is_in_vision(pos):
            return pos
    
    step = ct.get_vision_range() if hasattr(ct, 'get_vision_range') else 4
    for x in range(0, width, step):
        for y in range(0, height, step):
            pos = Position(x, y)
            if not ct.is_in_vision(pos):
                return pos
    
    return None

def find_the_enemy(self, ct: Controller):
    if self.enemycoord is not None:
        return

    if self.unlockedenemycoord is None:
        unlockedenemy(self, ct)

    print("in find")
    find_local_ore(self, ct)
    reachunlockedenemycoord(self, ct)

    symmetry, farpoints = check_symmetry(self, ct)
    self.symmetry = symmetry

    if symmetry is not None:
        print("celebrate")
        candidate = mirror(self.ourcoord, ct.get_map_width(), ct.get_map_height(), symmetry)
        # Only confirm enemycoord if we can see the tile and a building is there
        if ct.is_in_vision(candidate):
            if ct.get_entity_type(ct.get_tile_building_id(candidate)):
                self.enemycoord = candidate
                if self.localorepos is not None:
                    self.enemyore = mirror(self.localorepos, ct.get_map_width(), ct.get_map_height(), symmetry)
                    print(self.enemycoord)
            # else: tile is visible but no core — symmetry may be wrong, don't assign
        else:
            # Can't see it yet; reachunlockedenemycoord will confirm once we get there
            self.unlockedenemycoord = candidate

    elif farpoints and self.current_target is None:
        self.mirroredpoints = farpoints
        orient(self, ct)



def reach_enemy_core(self, ct: Controller):
    if self.enemycoord is None:
        return
    currentpos = ct.get_position()
    if not ct.is_in_vision(self.enemycoord):
        print("moving to enemy core")
        self.prevpos = currentpos
        self.turnstaken= 0
        movemode(self, ct, currentpos, self.enemycoord)
        return
    # elif distance_squared(currentpos, self.enemycoord) > 5:
    #     print("moving closer to enemy core")
    #     movemode(self, ct, currentpos, self.enemycoord)
    #     return
    else:
        self.attack = "FIND"
        self.chockerstate= "STARTER"
        print("reached enemy core, switching to find mode")
        return

def scan_field_for_bridges(self, ct:Controller):
    if self.bridges != None :
        return
    tiles = ct.get_nearby_tiles()
    bridges= set()
    for tile in tiles:
        if ct.get_entity_type(ct.get_tile_building_id(tile)) == EntityType.BRIDGE and self.our_team!= ct.get_team(ct.get_tile_building_id(tile)):
            bridges.add(tile)
    if len(bridges)>0:
        self.bridges= sorted(bridges, key=lambda p: (p.x - self.enemycoord.x)**2 + (p.y - self.enemycoord.y)**2)
        self.attack= "GO"

def scan_field_for_conveyer_with_titanium(self, ct:Controller):

    if self.titaniumconveyor != None :
        return
    
    tiles = ct.get_nearby_tiles()
    conveyors= set()
    for tile in tiles:
        if ct.get_entity_type(ct.get_tile_building_id(tile)) == EntityType.CONVEYOR:
            ct.get_stored_resource(ct.get_tile_building_id(tile)) == ResourceType.TITANIUM
            conveyors.add(tile)
            break

    if len(conveyors)>0:
        self.titaniumconveyor= sorted(conveyors, key=lambda p: (p.x - self.enemycoord.x)**2 + (p.y - self.enemycoord.y)**2)
        self.attack= "GO"
    return


def move_to_enemy_bridge(self, ct:Controller, bridge:Position):

    if self.nextsentinelpos in ct.get_nearby_tiles() and ct.get_tile_builder_bot_id(self.nextsentinelpos) is not None and ct.get_team(ct.get_tile_builder_bot_id(self.nextsentinelpos))== self.our_team and ct.get_id()!= ct.get_tile_builder_bot_id(self.nextsentinelpos):
        print("friendly bot is blocking sentinel position, finding new position MOVE TO ENEMY BRIDGE")
        print("bridges:", self.bridges)
        print("convs:", self.titaniumconveyor)
        if self.bridges is not None and self.nextsentinelpos in self.bridges:
            print("new bridge")
            self.bridges.discard(self.nextsentinelpos)
            self.attack = "FIND"
            return
        if self.titaniumconveyor is not None and self.nextsentinelpos in self.titaniumconveyor:
            print("new conveyor")
            self.attack = "FIND"
            self.titaniumconveyor.discard(self.nextsentinelpos)
            return
        else:
            movemode(self,ct, ct.get_position())
            self.attack= "FIND"
    if ct.get_position()!= bridge:
        movemode(self, ct, ct.get_position(), bridge )
        return
    else:
        self.attack= "DAMAGE"


def destroy_the_damn_bridge(self, ct:Controller):

    id = ct.get_tile_building_id(ct.get_position())
    if ct.get_entity_type(id) == EntityType.BRIDGE or ct.get_entity_type(id) == EntityType.CONVEYOR or ct.get_entity_type(id) == EntityType.ROAD:
        if ct.can_fire(ct.get_position()):
            ct.fire(ct.get_position())
        return
    else:
        self.attack= "SENTINEL"
    


def place_sentinels(self, ct: Controller):
    if self.enemycoord is None :
        return
    
    if ct.get_position() == self.nextsentinelpos:
        print("at sentinel position, will scoot", self.nextsentinelpos)

        id = ct.get_tile_building_id(ct.get_position())
        if ct.get_entity_type(id) == EntityType.ROAD:
            print("there is a tile to break, switching to damage mode")
            self.attack = "DAMAGE"
            return
        


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

        if ct.get_tile_builder_bot_id(self.nextsentinelpos) is not None and ct.get_team(ct.get_tile_builder_bot_id(self.nextsentinelpos))== self.our_team:
            print("friendly bot is blocking sentinel position, finding new position PLACE SENTINEL")
            if self.bridges is not None and self.nextsentinelpos in self.bridges:
                self.bridges.discard(self.nextsentinelpos)
            if self.titaniumconveyor is not None and self.nextsentinelpos in self.titaniumconveyor:
                self.titaniumconveyor.discard(self.nextsentinelpos)
                self.attack = "FIND"
            return


        dir = self.nextsentinelpos.direction_to(self.enemycoord)
        if ct.can_build_sentinel(self.nextsentinelpos, dir):
            print("scooted, placing sentinel now", self.nextsentinelpos)
            print(f"placing sentinel at {self.nextsentinelpos} facing {dir}")
            self.sentinelsbuilt += 1

            ct.build_sentinel(self.nextsentinelpos, dir)
            self.attack = "FIND"
            return
        else:
            id = ct.get_tile_building_id(self.nextsentinelpos)
            if ct.get_entity_type(id) == EntityType.ROAD:
                print("there is a tile to break, switching to damage mode")
                self.attack = "DAMAGE"
                movemode(self,ct,self.nextsentinelpos)
                return
            sentinelcost = ct.get_sentinel_cost()
            titaniumnow= ct.get_global_resources()
            print(f"cannot build sentinel yet, have {titaniumnow} titanium, need {sentinelcost}")


    return



def snipe_the_enemy(self, ct):
    if self.enemycoord== None or self.chocked== False:
        return
    print("in snipe")
    if self.attack == None:
        print("reach core")
        reach_enemy_core(self, ct)
        return
    if self.attack == "FIND":
        print("in scanning")
        scan_field_for_bridges(self, ct)
        print("scanned bridges")
        scan_field_for_conveyer_with_titanium(self, ct)
        print("scanned titanium conveyor")
        if self.bridges is not None and len(self.bridges) > 0:
            bridge = self.bridges.pop()       
            self.nextsentinelpos= bridge
            print("in go mode yeaaaa(bridge) with target:", bridge)
            self.attack = "GO"
        elif self.titaniumconveyor is not None and len(self.titaniumconveyor)>0:
            conveyor = self.titaniumconveyor.pop()
            self.nextsentinelpos= conveyor
            print("in go mode yeaaaa(conveyor) with target:", conveyor)
            self.attack = "GO"
        else:           print("no targets found, going to roomba")
    elif self.attack == "GO":
        print("moving to next sentinel pos", self.nextsentinelpos)
        self.mode = "GREEDY"
        move_to_enemy_bridge(self, ct, self.nextsentinelpos)
    elif self.attack == "DAMAGE":
        print("destroying nowww")
        destroy_the_damn_bridge(self, ct)
    elif self.attack == "SENTINEL":
        print("placing sentinels")
        place_sentinels(self,ct)


def side(loc, ex, ey):
    dx = loc.x - ex
    dy = loc.y - ey
    if dy == -2:   
        return (0, loc.x)
    elif dx == 2:
        return (1, loc.y)
    elif dy == 2:  
        return (2, -loc.x)  
    else:      
        return (3, -loc.y)

def calculatebarrierlocs(self, ct: Controller):
    if self.barrierlocs :
        return
    barriers= []
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            if abs(dx) == 2 or abs(dy) == 2:
                loc = Position(self.enemycoord.x + dx, self.enemycoord.y + dy)
                width = ct.get_map_width()
                height = ct.get_map_height()

                if 0 <= loc.x < width and 0 <= loc.y < height:
                    barriers.append(loc)
    self.barrierlocs = sorted(barriers, key=lambda loc: side(loc, self.enemycoord.x, self.enemycoord.y))
    print ("calculated barrier locs:", self.barrierlocs)
    self.nextchoke=self.barrierlocs.pop()            
    self.chockerstate= "MOVE"
    
def movetotarget(self,ct: Controller):
    if self.nextchoke in ct.get_nearby_tiles() and ct.get_tile_builder_bot_id(self.nextchoke) is not None and ct.get_team(ct.get_tile_builder_bot_id(self.nextchoke))== self.our_team and ct.get_id()!= ct.get_tile_builder_bot_id(self.nextchoke):
        print("friendly bot is blocking barrier position, finding new loc")
        if self.barrierlocs is not None and self.nextchoke in self.barrierlocs:
            print("new loc")
            if self.nextchoke in self.barrierlocs:
                self.barrierlocs.remove(self.nextchoke)
            if self.barrierlocs:
                self.nextchoke= self.barrierlocs.pop()
                self.attack = "MOVE"
            else: 
                self.chocked= True
                return
            return
        else:

            return
    elif self.nextchoke in ct.get_nearby_tiles() and (ct.get_entity_type(ct.get_tile_building_id(self.nextchoke)) == EntityType.BARRIER or ct.get_tile_env(self.nextchoke) == Environment.WALL or ct.is_tile_passable(self.nextchoke)== False) :
        if self.nextchoke in self.barrierlocs:
            self.barrierlocs.remove(self.nextchoke)
            if self.barrierlocs:
                self.nextchoke= self.barrierlocs.pop()
            else: 
                self.chocked= True
                return
    elif self.nextchoke in ct.get_nearby_tiles() and (ct.get_entity_type(ct.get_tile_building_id(self.nextchoke)) == EntityType.MARKER or ct.get_entity_type(ct.get_tile_building_id(self.nextchoke)) == EntityType.HARVESTER or ct.get_entity_type(ct.get_tile_building_id(self.nextchoke)) == EntityType.FOUNDRY) :
        if self.nextchoke in self.barrierlocs:
            self.barrierlocs.remove(self.nextchoke)
        if self.barrierlocs:
            self.nextchoke= self.barrierlocs.pop()
        else: 
            self.chocked= True
            return

    if ct.get_position()!=self.nextchoke:
        movemode(self, ct, ct.get_position(), self.nextchoke )
        return
    else:
        self.chockerstate= "BREAK"

def breaktheirlegs(self,ct:Controller):
    id = ct.get_tile_building_id(ct.get_position())
    if ct.get_entity_type(id) == EntityType.BRIDGE or ct.get_entity_type(id) == EntityType.CONVEYOR or ct.get_entity_type(id) == EntityType.SPLITTER or(ct.get_entity_type(id) == EntityType.ROAD and ct.get_team(ct.get_tile_building_id(ct.get_position()))!= self.our_team):
        if ct.can_fire(ct.get_position()):
            print("banging at", ct.get_position())
            ct.fire(ct.get_position())
        return
    elif (ct.get_entity_type(id) == EntityType.ROAD and ct.get_team(ct.get_tile_building_id(ct.get_position()))== self.our_team):
        if ct.can_destroy(ct.get_position()):
            print("destroying road at", ct.get_position())
            ct.destroy(ct.get_position())
    else:
        print("tile broken, scooting into position to choke")
        self.chockerstate= "SCOOT"

def scoot(self,ct:Controller):

    # if ct.get_tile_builder_bot_id(self.nextchoke) is not None and ct.get_team(ct.get_tile_builder_bot_id(self.nextchoke))== self.our_team:
    #         print("friendly bot is blocking barrier position, finding new position choke")
    #         if self.barrierlocs is not None and self.nextchoke in self.barrierlocs:
    #             self.barrierlocs.discard(self.nextchoke)
    #             self.nextchoke= self.barrierlocs.pop()
    #             self.attack == "MOVE"
    #         return

    if ct.get_position() == self.nextchoke:
        print("at choke pos, will scoot")

        id = ct.get_tile_building_id(ct.get_position())
        if ct.get_entity_type(id) == EntityType.ROAD:
            print("there is a tile to break, switching to damage mode")
            self.chockerstate= "BREAK"
            return
        
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
                self.chockerstate = "CHOKE"
                ct.move(direction)
                return
    else:
        self.chockerstate= "MOVE"
        return

def barrierboba(self, ct:Controller):
    id = ct.get_tile_building_id(self.nextchoke)
    if (ct.get_entity_type(id) == EntityType.ROAD and ct.get_team(ct.get_tile_building_id(self.nextchoke))== self.our_team):
        print("destroying friendly road")
        if ct.can_destroy(self.nextchoke):
            print("destroying road at", self.nextchoke)
            ct.destroy(self.nextchoke)
            return
    if ct.can_build_barrier(self.nextchoke):
        ct.build_barrier(self.nextchoke)
        if self.nextchoke in self.barrierlocs:
            self.barrierlocs.remove(self.nextchoke)
        if self.barrierlocs:
            self.nextchoke= self.barrierlocs.pop()
            self.chockerstate= "MOVE"
        else:
            print("choking done :)")
            self.bot_state = "ATTACK"
            self.chocked= True
    elif (ct.get_entity_type(id) == EntityType.ROAD) or (ct.get_entity_type(id) ==EntityType.CONVEYOR) or (ct.get_entity_type(id) ==EntityType.SPLITTER):
        self.chockerstate= "BREAK"
        movetotarget(self,ct)
    elif ct.get_entity_type(id) == EntityType.BARRIER or ct.get_entity_type(id) == EntityType.FOUNDRY:
        print("barrier or foundry exists, next barrier incoming")
        if self.nextchoke in self.barrierlocs:
            self.barrierlocs.remove(self.nextchoke)
        if self.barrierlocs:
            self.nextchoke= self.barrierlocs.pop()
            self.chockerstate= "MOVE"




def choke_the_enemy(self, ct:Controller):
    if self.chocked is True or self.enemycoord== None :
        return
    if self.chockerstate == None:
        tiles = ct.get_nearby_tiles()
        barriertile=False
        barrierenemy=False
        for tile in tiles:
            if ct.get_entity_type(ct.get_tile_building_id(tile)) == EntityType.BARRIER:
                barriertile= True
            if ct.get_entity_type(ct.get_tile_building_id(tile)) == EntityType.CORE and self.our_team!= ct.get_team(ct.get_tile_building_id(tile)):
                barrierenemy= True
        if barrierenemy and barriertile:
            self.chockerstate= "STARTER"
        print("reach core in choke")
        reach_enemy_core(self, ct)
        return
    if self.chockerstate== "STARTER":  
        print("calculating barrier locs")
        calculatebarrierlocs(self,ct)
        return
    if self.chockerstate== "MOVE":
        nearby = ct.get_nearby_tiles()
        if self.nextchoke in nearby:
            if ct.get_entity_type(ct.get_tile_building_id(self.nextchoke)) == EntityType.BARRIER:
                print("barrier exists")
                if self.nextchoke in self.barrierlocs:
                    self.barrierlocs.remove(self.nextchoke)
                if self.barrierlocs:
                    self.nextchoke= self.barrierlocs.pop()
        if  not self.barrierlocs:
            print("choking done :)")
            self.chocked= True
            return
        print("move to barrier loc", self.nextchoke)
        movetotarget(self,ct)
        return
    if self.chockerstate== "BREAK":
        print("break the floor im on")
        breaktheirlegs(self,ct)
        return
    if self.chockerstate== "SCOOT":
        print("scooooooting")
        scoot(self,ct)
        return
    if self.chockerstate== "CHOKE":
        print("choking the core with barrier rn")
        barrierboba(self, ct)
        return
    


