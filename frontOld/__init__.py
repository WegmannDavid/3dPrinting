from unittest import result

from prelude import *
import split.vbar
import duct.solid

import external.m3

WALL_STRENGTH = NOZZLE * 12

# M3_FREE_WALL_STRENGTH = external.m3.FREE_OFFSET * 2
# M3_TOP_WALL_STRENGTH = external.m3.TOP_OFFSET * 2
# M3_WALL_STRENGTH = external.m3.OFFSET * 2
FLOOR_STRENGTH = 5
HEIGHT = 210
WIDTH = 1144
DUCT_FOAM_DEPTH = 10
FOAM_THICKNESS = 20
DUCT_DEPTH = 20
DEPTH = DUCT_DEPTH + FOAM_THICKNESS * 2 + WALL_STRENGTH * 4
CAVITY_HEIGHT = HEIGHT - FLOOR_STRENGTH * 2


SIDES_WIDTH = 30

from front.fanAssembly import FANASSEMBLY_CUTOUT_WIDTH

THIN_WALL_ALONG_Y_STRENGTH = NOZZLE * 2
VBAR_WALL_ALONG_Y_STRENGTH = external.m3.TOP_OFFSET + external.m3.OFFSET

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


_DUCT_WIDTH = SECTION234_WIDTH * 2 + VBAR_WALL_ALONG_Y_STRENGTH

import duct.vane

_filterSet = front.filter.set().translate((SIDES_WIDTH, DEPTH - front.filter.DEPTH, 0))

_FILTER_FAN_ASSEMBLY_GAP = front.external.m3.FREE_OFFSET * 2

_FANASSEMBLY_CUTOUT_OFFSETY = 8.4
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


_RIGHT_WALL_STRENGTH = external.m3.OFFSET + external.m3.TOP_OFFSET
_ELBOW_WIDTH = SECTION15_WIDTH - VBAR_WALL_ALONG_Y_STRENGTH - _RIGHT_WALL_STRENGTH


elbowSet = front.elbow.make_elbow_set(
    _ELBOW_WIDTH, CAVITY_HEIGHT, DUCT_DEPTH, FOAM_THICKNESS, 20
).translate(
    (
        WIDTH - SIDES_WIDTH - _RIGHT_WALL_STRENGTH - _ELBOW_WIDTH,
        WALL_STRENGTH * 2,
        FLOOR_STRENGTH,
    )
)

import helmholtz.array


def cavity1(x, width):
    w = width - VBAR_WALL_ALONG_Y_STRENGTH - THIN_WALL_ALONG_Y_STRENGTH
    c1 = shapes.box(
        w,
        FOAM_THICKNESS,
        CAVITY_HEIGHT,
    ).translate((x + VBAR_WALL_ALONG_Y_STRENGTH, WALL_STRENGTH, FLOOR_STRENGTH))

    return c1


def cavity2(x, width):
    w = width - VBAR_WALL_ALONG_Y_STRENGTH - THIN_WALL_ALONG_Y_STRENGTH
    c2 = shapes.box(
        w,
        FOAM_THICKNESS,
        CAVITY_HEIGHT,
    ).translate(
        (
            x + VBAR_WALL_ALONG_Y_STRENGTH,
            DEPTH - FOAM_THICKNESS - WALL_STRENGTH,
            FLOOR_STRENGTH,
        )
    )

    return c2


def cavityCutouts():

    result = cavity2(_SECTIONS[1][0], _SECTIONS[1][1])

    offset = 135

    offsetHalf = VBAR_WALL_ALONG_Y_STRENGTH

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
    w = width - VBAR_WALL_ALONG_Y_STRENGTH - THIN_WALL_ALONG_Y_STRENGTH
    return helmholtz.array.tuned_helmholtz_array(
        numX=4, numZ=4, width=w, depth=WALL_STRENGTH, height=CAVITY_HEIGHT
    ).translate(
        (x + VBAR_WALL_ALONG_Y_STRENGTH, WALL_STRENGTH + FOAM_THICKNESS, FLOOR_STRENGTH)
    )


def necks2(x, width):
    w = width - VBAR_WALL_ALONG_Y_STRENGTH - THIN_WALL_ALONG_Y_STRENGTH
    return helmholtz.array.tuned_helmholtz_array(
        numX=4, numZ=4, width=w, depth=WALL_STRENGTH, height=CAVITY_HEIGHT
    ).translate(
        (
            x + VBAR_WALL_ALONG_Y_STRENGTH,
            DEPTH - FOAM_THICKNESS - WALL_STRENGTH * 2,
            FLOOR_STRENGTH,
        )
    )


def necks():
    result = necks2(_SECTIONS[1][0], _SECTIONS[1][1])

    for x, width in _SECTIONS[2:-1]:
        n1 = necks1(x, width)
        n2 = necks2(x, width)
        result = result.union(n1).union(n2)

    return result


def _cutouts():

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
        expanderCutout.union(_filterSet.cutout)
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


def femAir():
    damperPart = shapes.box(
        WIDTH - 2 * SIDES_WIDTH - SECTION15_WIDTH,
        DEPTH,
        front.basePlate.BASE_PLATE_HEIGHT + HEIGHT,
    ).translate((SIDES_WIDTH + SECTION15_WIDTH, 0, -front.basePlate.BASE_PLATE_HEIGHT))
    return damperPart.cut(full().union(elbowSet.vanes)).cut(femFoam())


def vBarTest():
    return full().intersect(
        shapes.box(40, 400, 400).translate(
            (SIDES_WIDTH + SECTION15_WIDTH - 20, -100, -100)
        )
    )


import split
import split.vbar
import split.hbar


def drillings():
    def topDrillings():

        positions = []

        positions += [
            (
                SIDES_WIDTH + external.m3.TOP_OFFSET,
                external.m3.TOP_OFFSET,
            ),
            (
                SIDES_WIDTH + external.m3.TOP_OFFSET,
                DEPTH
                - front.filter.DEPTH
                - _FILTER_FAN_ASSEMBLY_GAP / 2
                + front.filter.CLAMP_STRENGTH / 2,
            ),
        ]

        positions += [
            (
                SIDES_WIDTH + SECTION15_WIDTH - external.m3.TOP_OFFSET,
                external.m3.TOP_OFFSET,
            ),
            (
                SIDES_WIDTH + SECTION15_WIDTH - external.m3.TOP_OFFSET,
                DEPTH
                - front.filter.DEPTH
                - _FILTER_FAN_ASSEMBLY_GAP / 2
                + front.filter.CLAMP_STRENGTH / 2,
            ),
        ]

        for x, _ in _SECTIONS[1:]:
            y1 = DEPTH - WALL_STRENGTH * 2
            y2 = WALL_STRENGTH * 2
            dOffset = WALL_STRENGTH + FOAM_THICKNESS * 1 / 3
            positions += [
                (x + external.m3.TOP_OFFSET, y1),
                (x + external.m3.TOP_OFFSET, y2),
            ]

        for x, _ in _SECTIONS[2:]:
            y1 = DEPTH - WALL_STRENGTH * 1.5 - FOAM_THICKNESS
            y2 = WALL_STRENGTH * 1.5 + FOAM_THICKNESS
            dOffset = WALL_STRENGTH + FOAM_THICKNESS * 1 / 3
            positions += [
                (x - external.m3.TOP_OFFSET * 3, y1),
                (x - external.m3.TOP_OFFSET * 3, y2),
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

    def bottomDrillings():
        positions = [SIDES_WIDTH / 2]

        for x, _ in _SECTIONS:
            positions += [x + SIDES_WIDTH / 2]

        positions += [WIDTH - SIDES_WIDTH * 1.5, WIDTH - SIDES_WIDTH / 2]

        out = front.basePlate.bottomDrillings(positions)
        return out

    return topDrillings().union(bottomDrillings())


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
            -front.basePlate.BASE_PLATE_HEIGHT,
        )  # ---------------------------------------------
        .lineTo(
            (SLOPE_SEAL_WIDTH + EPSILON) * slopeDirection,
            -front.basePlate.BASE_PLATE_HEIGHT,
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
        .extrude(
            -front.basePlate.BASE_PLATE_DEPTH - front.basePlate.BASE_PLATE_EXTENSION
        )
    ).translate((0, front.basePlate.BASE_PLATE_BEGIN, 0))

    return splitPlaneAndCutout


import external.m3


def vbarFeature(x, y):
    contactArea = 1.2
    m = HEIGHT + front.basePlate.BASE_PLATE_HEIGHT - FLOOR_STRENGTH
    v = split.vbar.vbarFeature(
        front.basePlate.BASE_PLATE_HEIGHT + HEIGHT - FLOOR_STRENGTH, contactArea
    ).translate((x, y, -front.basePlate.BASE_PLATE_HEIGHT))
    return v


def splitX():
    plane = split.planeYZ(DEPTH + front.basePlate.BASE_PLATE_DEPTH)
    v1 = vbarFeature(0, split.vbar.Y_OFFSET)
    v2 = vbarFeature(0, WALL_STRENGTH * 2 + FOAM_THICKNESS - split.vbar.Y_OFFSET)
    v3 = vbarFeature(
        0, DEPTH - FOAM_THICKNESS - WALL_STRENGTH * 2 + split.vbar.Y_OFFSET
    )
    v4 = vbarFeature(0, DEPTH - split.vbar.Y_OFFSET)

    vBase = front.basePlate.vBars(3)

    features = v1.union(v2).union(v3).union(v4).union(vBase)

    splitter = split.bulge(plane, features)

    return splitter


def reducedHrail(x, y, width):
    height = HEIGHT - FLOOR_STRENGTH
    reduced_width = width - WALL_STRENGTH * 6
    return split.hbar.hbarFeature(reduced_width).translate(
        (x + WALL_STRENGTH * 3, y, height)
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
        SECTION15_WIDTH - 2 * front.filter.RIM,
        front.filter.DEPTH + _FILTER_FAN_ASSEMBLY_GAP,
        front.filter.RIM,
    ).translate(
        (
            SIDES_WIDTH + front.filter.RIM,
            DEPTH - front.filter.DEPTH - _FILTER_FAN_ASSEMBLY_GAP,
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


import export


def outletCover(rim, outerWallOffset, depth, pincherDepth):
    OUTLETCOVER_FRAME_SIZE = 20

    OUTLETCOVER_STRENGTH = NOZZLE * 4

    base = shapes.box(
        front.CAVITY_HEIGHT + OUTLETCOVER_FRAME_SIZE * 2,
        front.DUCT_DEPTH + OUTLETCOVER_FRAME_SIZE * 2,
        OUTLETCOVER_STRENGTH,
    )
    cutouts = shapes.rectPatterXY(
        front.CAVITY_HEIGHT,
        front.DUCT_DEPTH,
        OUTLETCOVER_STRENGTH,
        1,
        10,
        OUTLETCOVER_STRENGTH,
    )

    return base.cut(cutouts)


def exportAll():
    _male = front._filterSet.male
    _female = front._filterSet.female

    _fanAssembly = front.fanAssemblySet.fanAssembly
    _fanAssemblyCover = front.fanAssemblySet.cover

    _vanes = front.elbowSet.vanes

    _outletCover = front.outletCover.mk()

    _full = front.full()
    _splitall = front.splitAll()

    _solids = _full.cut(_splitall).solids().vals()
    _solids = sorted(_solids, key=lambda s: (s.Center().x, s.Center().y, s.Center().z))

    assert len(_solids) == 12, f"Expected 12 solids, got {len(_solids)}"

    export.stl(_male, "front/male.stl")
    export.stl(_female, "front/female.stl")

    export.stl(_fanAssembly, "front/fanAssembly.stl")
    export.stl(_fanAssemblyCover, "front/fanAssemblyCover.stl")

    export.stl(_vanes, "front/vanes.stl")
    export.stl(_outletCover, "front/vanes.stl")

    export.stl(_solids[0], "front/left.stl")

    export.stl(_solids[1], "front/sec1.stl")
    export.stl(_solids[2], "front/sec1top.stl")
    export.stl(_solids[3], "front/sec2.stl")
    export.stl(_solids[4], "front/sec2top.stl")
    export.stl(_solids[5], "front/sec3.stl")
    export.stl(_solids[6], "front/sec3top.stl")
    export.stl(_solids[7], "front/sec4.stl")
    export.stl(_solids[8], "front/sec4top.stl")
    export.stl(_solids[9], "front/sec5.stl")
    export.stl(_solids[10], "front/sec5top.stl")

    export.stl(_solids[11], "front/right.stl")

    _vbarTest = front.vBarTest().cut(_splitall)

    _testSolids = _vbarTest.solids().vals()

    assert len(_testSolids) == 4, f"Expected 4 solids, got {len(_testSolids)}"

    export.stl(_testSolids[0], "front/test1.stl")
    export.stl(_testSolids[1], "front/test2.stl")
    export.stl(_testSolids[2], "front/test3.stl")
    export.stl(_testSolids[3], "front/test4.stl")
