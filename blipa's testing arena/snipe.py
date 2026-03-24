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
            

            if mirrored not in tiles:
                mirroredpoints.append(mirrored)
                continue
            
            else:
                
                mirrored_tile = ct.get_tile_env(mirrored)

                if mirrored_tile != tile:
                    changedpos.discard(d)

                if len(changedpos) == 1:
                    locked = next(iter(changedpos))
                    print("Detected symmetry:", locked)
        
        possible = changedpos

    if locked is not None: 
        mirroredpoints= None

    return locked, mirroredpoints


def orient(self, ct: Controller):

    tiles = ct.get_nearby_tiles()

    global possible, locked

    if locked is not None:
        return locked

    editedtiles= tiles.copy()
    for tile in tiles:
        if ct.get_tile_env(tile)== Environment.EMPTY:
            editedtiles.discard(tile)
    
    tiles = editedtiles 
    symmetry, farpoints = check_symmetry(self, ct, tiles)

    if symmetry is not None:
        print ("celebrate")
    



   





def far_orient_builder(self, ct: Controller):  
    #bep
    x = 0

