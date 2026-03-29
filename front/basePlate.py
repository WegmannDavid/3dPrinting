from prelude import *
from front import *

FOAM_RIM_INSET = 2
FOAM_RIM_HEIGHT = 7

_SLOPE_DEPTH = 2
_SLOPE_HEIGHT = 1

import shapes


def basePlate(width):
    plate = (
        cq.Workplane("YZ")
        .moveTo(DEPTH + BASE_PLATE_EXTENSION, -BASE_PLATE_HEIGHT)
        .lineTo(DEPTH + BASE_PLATE_EXTENSION, -_SLOPE_HEIGHT)
        .lineTo(DEPTH + BASE_PLATE_EXTENSION - _SLOPE_DEPTH, 0)
        .lineTo(BASE_PLATE_BEGIN + BASE_PLATE_EXTENSION, 0)
        .lineTo(BASE_PLATE_BEGIN + BASE_PLATE_EXTENSION, -FOAM_RIM_HEIGHT)
        .lineTo(BASE_PLATE_BEGIN, -FOAM_RIM_HEIGHT)
        .lineTo(BASE_PLATE_BEGIN, -BASE_PLATE_HEIGHT)
        .close()
        .extrude(width)
    )

    insetl = shapes.box(
        FOAM_RIM_INSET, BASE_PLATE_DEPTH + BASE_PLATE_EXTENSION, FOAM_RIM_HEIGHT
    ).translate((0, BASE_PLATE_BEGIN, -FOAM_RIM_HEIGHT))

    insetr = insetl.translate((WIDTH - FOAM_RIM_INSET, 0, 0))

    return plate.cut(insetl).cut(insetr)
