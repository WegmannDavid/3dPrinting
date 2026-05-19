import math

from prelude import *

import shapes

import front

WALL_STRENGTH = NOZZLE * 8

OUTLET_DUCT_DEPTH = 2

NUM_OUTLETS = 5
OUTLET_X_GAP_WIDTH = WALL_STRENGTH

FOAM_BOX_DEPTH = 48
FILTER_DEPTH = 12


def foamBoxCutout(WIDTH):
    return shapes.boxFromBounds(
        WALL_STRENGTH,
        WIDTH - WALL_STRENGTH,
        WALL_STRENGTH,
        WALL_STRENGTH + FOAM_BOX_DEPTH,
        0,
        front.HEIGHT - WALL_STRENGTH,
    )


def filterSet(WIDTH):
    import front.filter

    up = cq.Vector(0, 0, 1)
    v = cq.Vector(0, front.DEPTH_EXTENSION, front.HEIGHT)
    angle = -math.degrees(up.getAngle(v))

    return (
        front.filter.set(
            DEPTH=FILTER_DEPTH,
            HEIGHT=front.HEIGHT,
            WIDTH=WIDTH - WALL_STRENGTH * 2,
            DOWNWARD_EXTENSION=front.basePlate.BASE_PLATE_HEIGHT,
        )
        .translate((WALL_STRENGTH, front.DEPTH - FILTER_DEPTH, 0))
        .rotate((0, 0, 0), (1, 0, 0), angle)
    )


import loft


def collectorCutout(filterPort, fanInletPort):

    return loft.closed_bezier_loft(filterPort, fanInletPort)


import external.fan


def fanSet(WIDTH):
    fan = external.fan.Centrifugal.centrifugalFanSet(10)
    fan = fan.translate(
        (
            WALL_STRENGTH + 20,
            WALL_STRENGTH + 10,
            front.HEIGHT - external.fan.Centrifugal.SIZE - WALL_STRENGTH - 10,
        )
    )
    return fan


def foam(WIDTH):
    v = foamBoxCutout(WIDTH)
    c1 = fanSet(WIDTH).cutout

    c2 = shapes.boxFromBounds(
        WALL_STRENGTH,
        WIDTH - WALL_STRENGTH,
        WALL_STRENGTH + 20,
        WALL_STRENGTH + FOAM_BOX_DEPTH - 20,
        0,
        front.HEIGHT - WALL_STRENGTH,
    )

    return v.cut(c1).cut(c2)


def segmentCutout(WIDTH):
    foamBox = foamBoxCutout(WIDTH)

    filter = filterSet(WIDTH)

    fan = fanSet(WIDTH)

    reference = (0, 0, 0)

    collector = collectorCutout(
        loft.polygon_endpoint(filter.port.vertices, [(0, -8, 0)] * 4),
        loft.circular_port_to_endpoint(
            fan.inlet, start_reference=reference, tangent_length=-6
        ),
    )

    return foamBox.union(filter.cutout).union(collector)


def segmentFoam(WIDTH):
    foamBox = foamBoxCutout(WIDTH)
    filter = filterSet(WIDTH)
    return foamBox.union(filter.foam)


def splitSegmentX():
    import split.vbar

    p = split.planeYZ(
        front.basePlate.BASE_PLATE_BEGIN,
        front.EXTENDED_DEPTH,
        -front.basePlate.BASE_PLATE_HEIGHT,
        front.HEIGHT,
    )
    s = split.vbar.spread(0, front.DEPTH, 0, front.HEIGHT, 4, 2)
    return split.addFeature(p, s)
