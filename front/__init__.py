from unittest import result

from prelude import *
import split.vbar
import duct.solid

import external.m3

WALL_STRENGTH = NOZZLE * 10
M3_WALL_STRENGTH = external.m3.OFFSET * 2
FLOOR_STRENGTH = 6.4
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
BASE_PLATE_EXTENSION = 12

SIDES_WIDTH = 30

from front.fanAssembly import FANASSEMBLY_CUTOUT_WIDTH

THIN_WALL_ALONG_Y_STRENGTH = NOZZLE * 2

SECTION15_WIDTH = FANASSEMBLY_CUTOUT_WIDTH + 2 * THIN_WALL_ALONG_Y_STRENGTH

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


_FILTER_FAN_ASSEMBLY_GAP = M3_WALL_STRENGTH

_FANASSEMBLY_CUTOUT_OFFSETY = 8
_FANASSEMBLY_CUTOUT_DEPTH = (
    DEPTH - front.filter.DEPTH - _FILTER_FAN_ASSEMBLY_GAP - _FANASSEMBLY_CUTOUT_OFFSETY
)

fanAssemblySet = front.fanAssembly.set(
    _FANASSEMBLY_CUTOUT_DEPTH, _FANASSEMBLY_CUTOUT_OFFSETY
).translate(
    (
        SIDES_WIDTH + THIN_WALL_ALONG_Y_STRENGTH,
        _FANASSEMBLY_CUTOUT_OFFSETY,
        HEIGHT - FLOOR_STRENGTH,
    )
)

import front.elbow

_ELBOW_WIDTH = SECTION15_WIDTH - WALL_STRENGTH * 2 - M3_WALL_STRENGTH


elbowSet = front.elbow.make_elbow_set(
    _ELBOW_WIDTH, CAVITY_HEIGHT, DUCT_DEPTH, FOAM_THICKNESS, 20
).translate(
    (
        WIDTH - SIDES_WIDTH - WALL_STRENGTH * 2 - _ELBOW_WIDTH,
        WALL_STRENGTH * 2,
        FLOOR_STRENGTH,
    )
)

import helmholtz.array


def cavity1(x, width):
    c1 = shapes.box(
        width - WALL_STRENGTH - THIN_WALL_ALONG_Y_STRENGTH,
        FOAM_THICKNESS,
        CAVITY_HEIGHT,
    ).translate((x + WALL_STRENGTH, WALL_STRENGTH, FLOOR_STRENGTH))

    return c1


def cavity2(x, width):
    c2 = shapes.box(
        width - M3_WALL_STRENGTH - THIN_WALL_ALONG_Y_STRENGTH,
        FOAM_THICKNESS,
        CAVITY_HEIGHT,
    ).translate(
        (
            x + M3_WALL_STRENGTH,
            DEPTH - FOAM_THICKNESS - WALL_STRENGTH,
            FLOOR_STRENGTH,
        )
    )

    return c2


def cavityCutouts():

    result = cavity2(_SECTIONS[1][0], _SECTIONS[1][1])

    offset = 135

    offsetHalf = M3_WALL_STRENGTH

    result = result.union(
        shapes.box(
            SECTION234_WIDTH - THIN_WALL_ALONG_Y_STRENGTH - offset,
            FOAM_THICKNESS,
            CAVITY_HEIGHT,
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
            SECTION234_WIDTH - THIN_WALL_ALONG_Y_STRENGTH - offsetHalf,
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
        result = result.union(cavity1(x, width)).union(cavity2(x, width))

    return result


def necks1(x, width):
    return helmholtz.array.tuned_helmholtz_array(
        numX=5, numZ=5, width=width, depth=WALL_STRENGTH, height=CAVITY_HEIGHT
    ).translate((x, WALL_STRENGTH + FOAM_THICKNESS, FLOOR_STRENGTH))


def necks2(x, width):
    return helmholtz.array.tuned_helmholtz_array(
        numX=5, numZ=5, width=width, depth=WALL_STRENGTH, height=CAVITY_HEIGHT
    ).translate((x, DEPTH - FOAM_THICKNESS - WALL_STRENGTH * 2, FLOOR_STRENGTH))


def necks():
    result = necks2(_SECTIONS[1][0], _SECTIONS[1][1])

    for x, width in _SECTIONS[2:-1]:
        n1 = necks1(x, width)
        n2 = necks2(x, width)
        result = result.union(n1).union(n2)

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
    _neckCutouts = necks()

    return (
        expanderCutout.union(filterCutout)
        .union(fanAssemblySet.cutout)
        .union(expanderCutout)
        .union(_cavityCutouts)
        .union(_neckCutouts)
        .union(ductCutout)
        .union(elbowSet.cutout)
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
            (SIDES_WIDTH + external.m3.TOP_OFFSET, external.m3.TOP_OFFSET),
            (
                SIDES_WIDTH + external.m3.TOP_OFFSET,
                DEPTH - front.filter.DEPTH - _FILTER_FAN_ASSEMBLY_GAP / 2,
            ),
        ]

        for x, _ in _SECTIONS[1:]:
            dOffset = WALL_STRENGTH + FOAM_THICKNESS * 1 / 3
            positions += [
                (x + external.m3.OFFSET, dOffset),
                (
                    x + external.m3.OFFSET,
                    DEPTH - dOffset,
                ),
            ]

        positions += [
            (WIDTH - SIDES_WIDTH - external.m3.TOP_OFFSET, DEPTH * 1 / 4),
            (
                WIDTH - SIDES_WIDTH - external.m3.TOP_OFFSET,
                DEPTH * 3 / 4,
            ),
        ]

        result = cq.Workplane("XY")

        for x, y in positions:
            s = external.m3.m3(50, FLOOR_STRENGTH)
            result = result.union(s.translate((x, y, HEIGHT)))

        return result

    def basePlateDrillings():
        return 0

    return topDrillings()


def splitXSides(slopeDirection):
    splitPlaneAndCutout = (
        cq.Workplane("XZ")
        .moveTo(-EPSILON * slopeDirection, HEIGHT)
        .lineTo(-EPSILON * slopeDirection, 0)
        .lineTo(
            (SLOPE_SEAL_WIDTH - EPSILON) * slopeDirection,
            -front.basePlate.FOAM_RIM_HEIGHT,
        )
        .lineTo(
            (SLOPE_SEAL_WIDTH - EPSILON) * slopeDirection,
            -BASE_PLATE_HEIGHT,
        )  # ---------------------------------------------
        .lineTo(
            (SLOPE_SEAL_WIDTH + EPSILON) * slopeDirection,
            -BASE_PLATE_HEIGHT,
        )
        .lineTo(
            (SLOPE_SEAL_WIDTH + EPSILON) * slopeDirection,
            -front.basePlate.FOAM_RIM_HEIGHT,
        )
        .lineTo(
            (SLOPE_SEAL_WIDTH + front.basePlate.FOAM_RIM_INSET) * slopeDirection,
            -front.basePlate.FOAM_RIM_HEIGHT,
        )
        .lineTo(
            (SLOPE_SEAL_WIDTH + front.basePlate.FOAM_RIM_INSET) * slopeDirection,
            0,
        )
        .lineTo(
            EPSILON * slopeDirection,
            0,
        )
        .lineTo(
            EPSILON * slopeDirection,
            HEIGHT,
        )
        .close()
        .extrude(-BASE_PLATE_DEPTH - BASE_PLATE_EXTENSION)
    ).translate((0, BASE_PLATE_BEGIN, 0))

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

    return splitPlaneAndCutout.union(s1).union(s2)


import external.m3


def vbarFeature(x, y):
    contactArea = 1.2
    m = HEIGHT + BASE_PLATE_HEIGHT - FLOOR_STRENGTH
    v = split.vbar.vbarDoubleFeature(
        HEIGHT + BASE_PLATE_HEIGHT, m, contactArea
    ).translate((x, y, -BASE_PLATE_HEIGHT))
    return v


def splitX():
    plane = split.planeYZ(DEPTH + BASE_PLATE_DEPTH)
    v1 = vbarFeature(0, split.vbar.Y_OFFSET)
    v2 = vbarFeature(0, WALL_STRENGTH * 2 + FOAM_THICKNESS - split.vbar.Y_OFFSET)
    v3 = vbarFeature(
        0, DEPTH - FOAM_THICKNESS - WALL_STRENGTH * 2 + split.vbar.Y_OFFSET
    )
    v4 = vbarFeature(0, DEPTH - split.vbar.Y_OFFSET)

    features = v1.union(v2).union(v3).union(v4)

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


def reducedHrail(x, y, width):
    height = HEIGHT - FLOOR_STRENGTH
    reduced_width = width - WALL_STRENGTH * 4
    return split.hbar.hbarFeature(reduced_width).translate(
        (x + WALL_STRENGTH * 2, y, height)
    )


def hrails(width):
    h1 = reducedHrail(0, split.hbar.Y_OFFSET, width)
    h2 = reducedHrail(
        0, WALL_STRENGTH * 2 + FOAM_THICKNESS - split.hbar.Y_OFFSET, width
    )
    h3 = reducedHrail(
        0, DEPTH - WALL_STRENGTH * 2 - FOAM_THICKNESS + split.hbar.Y_OFFSET, width
    )
    h4 = reducedHrail(0, DEPTH - split.hbar.Y_OFFSET, width)
    return h1.union(h2).union(h3).union(h4)


def splitZ():
    result = split.planeXY(WIDTH).translate((0, 0, HEIGHT - FLOOR_STRENGTH))

    s = split.sink(
        SECTION15_WIDTH - 2 * front.filter.RIM, front.filter.DEPTH, front.filter.RIM
    ).translate(
        (
            SIDES_WIDTH + front.filter.RIM,
            DEPTH - front.filter.DEPTH,
            HEIGHT - FLOOR_STRENGTH,
        )
    )

    h1 = reducedHrail(
        SIDES_WIDTH + SECTION15_WIDTH * 1 / 16,
        split.hbar.Y_OFFSET,
        SECTION15_WIDTH * 6 / 16,
    )
    h2 = reducedHrail(
        SIDES_WIDTH + SECTION15_WIDTH * 9 / 16,
        split.hbar.Y_OFFSET,
        SECTION15_WIDTH * 6 / 16,
    )

    result = split.bulge(result, h1.union(h2).union(s))

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
    _splitall = splitAll()
    _full = full()
    result = _full.cut(_splitall)
    return result
