from unittest import result

from prelude import *
import split.vbar
import duct.solid

WALL_STRENGTH = NOZZLE * 10
FLOOR_STRENGTH = 5
HEIGHT = 210
WIDTH = 1144
DUCT_FOAM_DEPTH = 10
FOAM_THICKNESS = 20
DUCT_DEPTH = 20
DEPTH = DUCT_DEPTH + FOAM_THICKNESS * 2 + WALL_STRENGTH * 4
CAVITY_HEIGHT = HEIGHT - FLOOR_STRENGTH * 2


BASE_PLATE_DEPTH = 144
BASE_PLATE_HEIGHT = 10
BASE_PLATE_BEGIN = DEPTH - BASE_PLATE_DEPTH
BASE_PLATE_EXTENSION = 15

SIDES_WIDTH = 30

from front.fanAssembly import FANASSEMBLY_CUTOUT_WIDTH

SECTION1_WALL_STRENGTH = NOZZLE * 3

SECTION15_WIDTH = FANASSEMBLY_CUTOUT_WIDTH + 2 * SECTION1_WALL_STRENGTH

SLOPE_SEAL_WIDTH = 256 - split.vbar.WIDTH - SECTION15_WIDTH

SECTION234_WIDTH = (WIDTH - (SIDES_WIDTH + SECTION15_WIDTH) * 2) / 3

_SECTIONS = [
    (SIDES_WIDTH, SECTION15_WIDTH),
    (SIDES_WIDTH + SECTION15_WIDTH, SECTION234_WIDTH),
    (SIDES_WIDTH + SECTION15_WIDTH + SECTION234_WIDTH, SECTION234_WIDTH),
    (SIDES_WIDTH + SECTION15_WIDTH + SECTION234_WIDTH * 2, SECTION234_WIDTH),
    (SIDES_WIDTH + SECTION15_WIDTH + SECTION234_WIDTH * 3, SECTION15_WIDTH),
]


import front.fanAssembly
import front.filter
import front.basePlate
import shapes


_DUCT_WIDTH = SECTION234_WIDTH * 2 + WALL_STRENGTH

import duct.vane


_FILTER_FAN_ASSEMBLY_GAP = NOZZLE * 12

_FANASSEMBLY_CUTOUT_OFFSETY = WALL_STRENGTH
_FANASSEMBLY_CUTOUT_DEPTH = (
    DEPTH - front.filter.DEPTH - _FILTER_FAN_ASSEMBLY_GAP - _FANASSEMBLY_CUTOUT_OFFSETY
)

fanAssemblySet = front.fanAssembly.set(_FANASSEMBLY_CUTOUT_DEPTH).translate(
    (
        SIDES_WIDTH + SECTION1_WALL_STRENGTH,
        _FANASSEMBLY_CUTOUT_OFFSETY,
        HEIGHT - WALL_STRENGTH,
    )
)

import front.elbow

_ELBOW_WIDTH = SECTION15_WIDTH - WALL_STRENGTH * 2


elbowSet = front.elbow.make_elbow_set(
    _ELBOW_WIDTH, CAVITY_HEIGHT, DUCT_DEPTH, FOAM_THICKNESS, 20
).translate(
    (
        WIDTH - SIDES_WIDTH - WALL_STRENGTH - _ELBOW_WIDTH,
        WALL_STRENGTH * 2,
        FLOOR_STRENGTH,
    )
)

from helmholtz.array import tuned_helmholtz_array


def cavityCutouts():

    result = shapes.box(
        SECTION234_WIDTH - 2 * WALL_STRENGTH, FOAM_THICKNESS, CAVITY_HEIGHT
    ).translate(
        (
            SIDES_WIDTH + SECTION15_WIDTH + WALL_STRENGTH,
            DEPTH - FOAM_THICKNESS - WALL_STRENGTH,
            FLOOR_STRENGTH,
        )
    )

    offset = 150

    offsetHalf = 75

    result = result.union(
        shapes.box(
            SECTION234_WIDTH - WALL_STRENGTH - offset, FOAM_THICKNESS, CAVITY_HEIGHT
        ).translate(
            (
                SIDES_WIDTH + SECTION15_WIDTH + offset,
                WALL_STRENGTH,
                FLOOR_STRENGTH,
            )
        )
    )

    result = result.union(
        shapes.box(
            SECTION234_WIDTH - WALL_STRENGTH - offsetHalf,
            FOAM_THICKNESS / 2,
            CAVITY_HEIGHT,
        ).translate(
            (
                SIDES_WIDTH + SECTION15_WIDTH + offsetHalf,
                WALL_STRENGTH,
                FLOOR_STRENGTH,
            )
        )
    )

    for x, width in _SECTIONS[2:-1]:
        c1 = shapes.box(
            width - 2 * WALL_STRENGTH, FOAM_THICKNESS, CAVITY_HEIGHT
        ).translate((x + WALL_STRENGTH, WALL_STRENGTH, FLOOR_STRENGTH))

        c2 = shapes.box(
            width - 2 * WALL_STRENGTH, FOAM_THICKNESS, CAVITY_HEIGHT
        ).translate(
            (x + WALL_STRENGTH, DEPTH - FOAM_THICKNESS - WALL_STRENGTH, FLOOR_STRENGTH)
        )

        result = result.union(c1).union(c2)

    return result


def _cutouts():
    filterCutout = filter.cutout.translate((SIDES_WIDTH, 0, 0))

    ductInPort = duct.solid.RectPort(
        width=DUCT_DEPTH,
        height=CAVITY_HEIGHT,
        x=SIDES_WIDTH + SECTION15_WIDTH + SECTION234_WIDTH,
        y=WALL_STRENGTH * 2 + FOAM_THICKNESS,
        z=FLOOR_STRENGTH,
    )

    expanderCutout = duct.solid.rectDuctYZAlongX(fanAssemblySet.port, ductInPort)

    ductCutout = shapes.box(_DUCT_WIDTH, DUCT_DEPTH, CAVITY_HEIGHT).translate(
        (
            SIDES_WIDTH + SECTION15_WIDTH + SECTION234_WIDTH,
            WALL_STRENGTH * 2 + FOAM_THICKNESS,
            FLOOR_STRENGTH,
        )
    )

    _cavityCutouts = cavityCutouts()

    return (
        expanderCutout.union(filterCutout)
        .union(fanAssemblySet.cutout)
        .union(expanderCutout)
        .union(_cavityCutouts)
        .union(ductCutout)
        .union(elbowSet.cutout)
        # .union(helmholtzCutouts())
    )


def full():
    base = (
        shapes.box(WIDTH - 2 * SIDES_WIDTH, DEPTH, HEIGHT)
        .translate((SIDES_WIDTH, 0, 0))
        .union(front.basePlate.basePlate(WIDTH))
    )
    cutouts = _cutouts()
    _full = base.cut(cutouts)

    _fanAssembly = fanAssemblySet.fanAssembly
    _fanAssemblyCover = fanAssemblySet.cover

    return _full  # .union(_fanAssembly)


def femFoam():
    return elbowSet.foam.union(cavityCutouts())


def fem():
    damperPart = shapes.box(
        WIDTH - 2 * SIDES_WIDTH - SECTION15_WIDTH, DEPTH, BASE_PLATE_HEIGHT + HEIGHT
    ).translate((SIDES_WIDTH + SECTION15_WIDTH, 0, -BASE_PLATE_HEIGHT))
    return damperPart.cut(full().union(elbowSet.vanes)).cut(femFoam())


import split
import split.vbar
import split.hbar


def drillings():
    def topDrillings():

        positions = []

        positions += [
            (SIDES_WIDTH + external.m3.OFFSET, external.m3.OFFSET),
            (
                SIDES_WIDTH + external.m3.OFFSET,
                DEPTH - front.filter.DEPTH - _FILTER_FAN_ASSEMBLY_GAP / 2,
            ),
        ]

        for x, _ in _SECTIONS[1:-1]:
            positions += [
                (x + external.m3.OFFSET * 1.5, external.m3.OFFSET),
                (
                    x + external.m3.OFFSET * 1.5,
                    DEPTH - external.m3.OFFSET,
                ),
            ]

        positions += [
            (
                WIDTH - SIDES_WIDTH - SECTION15_WIDTH + external.m3.OFFSET,
                WALL_STRENGTH + external.m3.OFFSET / 2,
            ),
            (
                WIDTH - SIDES_WIDTH - SECTION15_WIDTH + external.m3.OFFSET * 1.5,
                DEPTH - external.m3.OFFSET,
            ),
        ]

        positions += [
            (WIDTH - SIDES_WIDTH - external.m3.OFFSET, external.m3.OFFSET),
            (
                WIDTH - SIDES_WIDTH - external.m3.OFFSET,
                DEPTH - external.m3.OFFSET,
            ),
        ]

        result = cq.Workplane("XY")

        for x, y in positions:
            s = external.m3.m3(50, WALL_STRENGTH)
            result = result.union(s.translate((x, y, HEIGHT)))

        return result

    def basePlateDrillings():
        return 0

    return topDrillings()


def splitXSides(slope):
    plane = split.planeYZ(DEPTH + BASE_PLATE_DEPTH)

    s1 = (
        external.m3.m3(50, WALL_STRENGTH)
        .mirror("XY")
        .translate(
            (
                -SIDES_WIDTH / 2,
                BASE_PLATE_BEGIN + external.m3.OFFSET * 1.5,
                -BASE_PLATE_HEIGHT,
            )
        )
    )

    s2 = (
        external.m3.m3(50, WALL_STRENGTH)
        .mirror("XY")
        .translate(
            (
                SIDES_WIDTH / 2,
                BASE_PLATE_BEGIN + external.m3.OFFSET * 1.5,
                -BASE_PLATE_HEIGHT,
            )
        )
    )

    return plane.union(s1).union(s2)


import external.m3


def splitX():
    contactArea = 2
    plane = split.planeYZ(DEPTH + BASE_PLATE_DEPTH)
    m = HEIGHT + BASE_PLATE_HEIGHT - WALL_STRENGTH
    v1 = split.vbar.vbarDoubleFeature(
        HEIGHT + BASE_PLATE_HEIGHT, m, contactArea
    ).translate((0, WALL_STRENGTH / 2, 0))
    v2 = split.vbar.vbarDoubleFeature(
        HEIGHT + BASE_PLATE_HEIGHT, m, contactArea
    ).translate((0, FOAM_THICKNESS + WALL_STRENGTH * 1.5, 0))
    v3 = split.vbar.vbarDoubleFeature(
        HEIGHT + BASE_PLATE_HEIGHT, m, contactArea
    ).translate((0, DEPTH - FOAM_THICKNESS - WALL_STRENGTH * 1.5, 0))
    v4 = split.vbar.vbarDoubleFeature(
        HEIGHT + BASE_PLATE_HEIGHT, m, contactArea
    ).translate((0, DEPTH - WALL_STRENGTH / 2, 0))

    features = v1.union(v2).union(v3).union(v4).translate((0, 0, -BASE_PLATE_HEIGHT))

    splitter = split.bulge(plane, features)

    s3 = (
        external.m3.m3(50, WALL_STRENGTH)
        .mirror("XY")
        .translate(
            (
                external.m3.OFFSET * 1.5,
                BASE_PLATE_BEGIN + external.m3.OFFSET * 1.5,
                -BASE_PLATE_HEIGHT,
            )
        )
    )

    return splitter.union(s3)


def hrails(width):
    height = HEIGHT - WALL_STRENGTH
    reduced_width = width - WALL_STRENGTH * 3
    h1 = split.hbar.hbarFeature(reduced_width).translate((0, split.hbar.Y_OFFSET, 0))
    h2 = split.hbar.hbarFeature(reduced_width).translate(
        (0, WALL_STRENGTH + FOAM_THICKNESS + split.hbar.Y_OFFSET, 0)
    )
    h3 = split.hbar.hbarFeature(reduced_width).translate(
        (0, DEPTH - FOAM_THICKNESS - WALL_STRENGTH - split.hbar.Y_OFFSET, 0)
    )
    h4 = split.hbar.hbarFeature(reduced_width).translate(
        (0, DEPTH - FOAM_THICKNESS - split.hbar.Y_OFFSET, 0)
    )
    return h1.union(h2).union(h3).union(h4).translate((WALL_STRENGTH * 1.5, 0, height))


def splitZ():
    result = split.planeXY(WIDTH).translate((0, 0, HEIGHT - WALL_STRENGTH))

    result = split.bulge(
        result,
        split.hbar.hbarFeature(SECTION15_WIDTH - WALL_STRENGTH * 3).translate(
            (
                SIDES_WIDTH + WALL_STRENGTH * 1.5,
                split.hbar.Y_OFFSET,
                HEIGHT - WALL_STRENGTH,
            )
        ),
    )

    for x, width in _SECTIONS[1:]:
        rails = hrails(width).translate((x, 0, 0))
        result = split.bulge(result, rails)

    return result


def splitAll():
    result = splitZ()

    sideplane = splitXSides(-1).translate((SIDES_WIDTH, 0, 0))

    result = result.union(sideplane)

    for x, width in _SECTIONS[1:]:
        result = result.union(splitX().translate((x, 0, 0)))

    result = result.union(splitXSides(1).translate((WIDTH - SIDES_WIDTH, 0, 0)))

    return result.union(drillings())


def fullSplit():
    result = full().cut(splitAll())
    return result
