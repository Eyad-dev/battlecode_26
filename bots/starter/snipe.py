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
    pos, mirrored, tiletype, d = self.mirroredpoints[0][:]
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
        from builder import run_greedy_mode
        currentpos= ct.get_position()
        run_greedy_mode(self, ct,currentpos, mirrored)

    if len(possible)==1:
        locked= next(iter(possible))

    

def find_the_enemy(self, ct: Controller):
    print("in snipe")
    if self.enemycoord!= None:
        return
    
    tiles = ct.get_nearby_tiles()

    editedtiles= set(tiles)
    for tile in tiles:
        if ct.get_tile_env(tile)== Environment.EMPTY:
            editedtiles.discard(tile)
    
    tiles = list(editedtiles) 
    symmetry, farpoints = check_symmetry(self, ct, tiles)

    if symmetry is not None:
        print ("celebrate")
        self.enemycoord = mirror(self.ourcoord, ct.get_map_width(), ct.get_map_height(), symmetry)
    elif farpoints is not None:
        self.mirroredpoints= farpoints
        orient(self,ct)



def snipe_the_enemy(self, ct):
    if self.enemycoord== None:
        return


