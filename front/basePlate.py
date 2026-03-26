from prelude import *
from front import *

def basePlate(width):
    plate = cq.Workplane("XY").box(width, BASE_PLATE_DEPTH+BASE_PLATE_EXTENSION, BASE_PLATE_HEIGHT, centered=False)
    plate = plate.translate((0, BASE_PLATE_BEGIN, -BASE_PLATE_HEIGHT))
    return plate