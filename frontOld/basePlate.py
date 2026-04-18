from prelude import *
import front
import external.m3

FOAM_RIM_INSET = 1.5
FOAM_RIM_HEIGHT = 7

_SLOPE_DEPTH = 2
_SLOPE_HEIGHT = 1

import shapes

BASE_PLATE_DEPTH = 144
BASE_PLATE_HEIGHT = 10
BASE_PLATE_BEGIN = front.DEPTH - BASE_PLATE_DEPTH
BASE_PLATE_EXTENSION = 12


def basePlate(width):
    plate = (
        cq.Workplane("YZ")
        .moveTo(front.DEPTH + BASE_PLATE_EXTENSION, -BASE_PLATE_HEIGHT)
        .lineTo(front.DEPTH + BASE_PLATE_EXTENSION, -_SLOPE_HEIGHT)
        .lineTo(front.DEPTH + BASE_PLATE_EXTENSION - _SLOPE_DEPTH, 0)
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

    insetr = insetl.translate((front.WIDTH - FOAM_RIM_INSET, 0, 0))

    cableCutout = shapes.box(3, 15, BASE_PLATE_HEIGHT).translate(
        (0, front.DEPTH - 15, -BASE_PLATE_HEIGHT)
    )

    bottomHoles = bottomDrillings(
        [
            BASE_PLATE_BEGIN + BASE_PLATE_EXTENSION + external.m3.FREE_OFFSET,
            BASE_PLATE_BEGIN + BASE_PLATE_EXTENSION + external.m3.TOP_OFFSET,
        ]
    )

    return plate.cut(insetl).cut(insetr).cut(cableCutout)


def bottomDrillings(Xpositions):
    result = cq.Workplane("YZ")

    for x in Xpositions:
        result = result.union(
            external.m3.m3(BASE_PLATE_HEIGHT * 2, BASE_PLATE_HEIGHT)
            .mirror("XY")
            .translate((x, BASE_PLATE_BEGIN + 10, -BASE_PLATE_HEIGHT))
        )
    return result


import split.vbar


def vBars(num):

    offset = (-BASE_PLATE_BEGIN - BASE_PLATE_EXTENSION) / num

    result = cq.Workplane("YZ")

    for i in range(0, num):
        result = result.union(
            split.vbar.vbarFeature(BASE_PLATE_HEIGHT, 1).translate(
                (
                    0,
                    BASE_PLATE_BEGIN
                    + BASE_PLATE_EXTENSION
                    + split.vbar.Y_OFFSET
                    + offset * i,
                    -BASE_PLATE_HEIGHT,
                )
            )
        )
    return result
