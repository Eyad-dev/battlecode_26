# import random
# from cambc import Controller, Direction, GameConstants, Position
# from helper import *

# def updatelastturnloc(self, ct:Controller):
#     self.lastturnloc=ct.get_position()

# def update(self,ct:Controller):
#     self.forbidden= [False] * 9
#     currentpos= ct.get_position()
#     if self.lastturnloc is not None:
#         self.pushdir= self.lastturnloc.direction_to(currentpos)

# def try_build_road(ct: Controller, tile_pos: Position):
#     if ct.can_build_road(tile_pos):
#         ct.build_road(tile_pos)
#         print(f"  [try_build_road] Built road at {tile_pos}")

# def canmove(self, ct: Controller, direction: Direction):

# def moveforwardwrap(self, ct:Controller):
#     canturn= True
