from prelude import *


import shapes

WIDTH = 1148
SIDE_WALL_WIDTH = 0

DEPTH = 70
DEPTH_EXTENSION = 10
EXTENDED_DEPTH = DEPTH + DEPTH_EXTENSION
DEPTH_EXTENSIONZ = 15

HEIGHT = 210


SEGMENT_WIDTH = 250
NUM_SEGMENTS = 4
ALL_SEGMENTS_WIDTH = SEGMENT_WIDTH * NUM_SEGMENTS
PADDING_WIDTH = (WIDTH - ALL_SEGMENTS_WIDTH - 2 * SIDE_WALL_WIDTH) / 2

SEGMENT_POSITIONS = [
    PADDING_WIDTH + SIDE_WALL_WIDTH + i * SEGMENT_WIDTH for i in range(NUM_SEGMENTS)
]

SEGMENT_SCREW_X_OFFSET = 10

import front.basePlate
import front.segment


def base():
    top = (
        cq.Workplane("YZ")
        .moveTo(0, 0)
        .lineTo(0, HEIGHT)
        .lineTo(DEPTH + DEPTH_EXTENSION, HEIGHT)
        .lineTo(DEPTH, 0)
        .close()
        .extrude(WIDTH - 2 * front.basePlate.FOAM_RIM_INSET)
    ).translate((front.basePlate.FOAM_RIM_INSET, 0, 0))

    base = top.union(front.basePlate.basePlate(WIDTH))
    return base


SLOPE_SEAL_WIDTH = 2


def leftCutout():
    mainCutout = shapes.box(
        PADDING_WIDTH
        - front.basePlate.FOAM_RIM_INSET
        - SLOPE_SEAL_WIDTH
        - front.basePlate.WALL_STRENGTH,
        DEPTH - front.basePlate.WALL_STRENGTH - 10,
        HEIGHT,
    )

    backCutout = shapes.box(
        PADDING_WIDTH
        - front.basePlate.FOAM_RIM_INSET
        - SLOPE_SEAL_WIDTH
        - front.basePlate.WALL_STRENGTH * 2,
        front.basePlate.BASE_PLATE_EXTENSION,
        HEIGHT,
    ).translate((front.basePlate.WALL_STRENGTH, front.DEPTH, 0))

    cableCutout = shapes.box(PADDING_WIDTH, front.segment.WALL_STRENGTH + 10, HEIGHT)

    import external.m3

    mountingHole = (
        external.m3.m3(EXTENDED_DEPTH * 2, 10)
        .rotate((0, 0, 0), (1, 0, 0), 90)
        .translate((0, 0, front.HEIGHT * 1 / 3))
    )

    m1 = mountingHole.translate((PADDING_WIDTH * 1 / 4, 0, 0))
    m2 = mountingHole.translate((PADDING_WIDTH * 2 / 4, 0, 0))
    m3 = mountingHole.translate((PADDING_WIDTH * 3 / 4, 0, 0))

    m4 = mountingHole.translate((PADDING_WIDTH * 1 / 4, 0, front.HEIGHT * 1 / 3))
    m5 = mountingHole.translate((PADDING_WIDTH * 2 / 4, 0, front.HEIGHT * 1 / 3))
    m6 = mountingHole.translate((PADDING_WIDTH * 3 / 4, 0, front.HEIGHT * 1 / 3))

    m = m1.union(m2).union(m3).union(m4).union(m5).union(m6)

    result = mainCutout.union(backCutout).union(cableCutout).union(m)
    return result


def full():
    _base = base()

    _lc = leftCutout()

    _base = _base.cut(_lc)

    for X1 in SEGMENT_POSITIONS:
        segment = front.segment.segmentCutout.translate((X1, 0, 0))
        _base = _base.cut(segment)

    _base = _base.cut(_lc.mirror("YZ", (WIDTH / 2, 0, 0)))

    cableCutout = shapes.box(
        front.basePlate.FOAM_RIM_INSET, 15, front.basePlate.BASE_PLATE_HEIGHT
    ).translate(
        (
            0,
            front.DEPTH - 15 - front.basePlate.WALL_STRENGTH,
            -front.basePlate.BASE_PLATE_HEIGHT,
        )
    )
    _base = _base.cut(cableCutout)

    return _base


def splitXSides(slopeDirection):
    profile = (
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
            HEIGHT,
        )
        .close()
    )
    result = profile.extrude(
        -front.basePlate.BASE_PLATE_DEPTH - front.basePlate.BASE_PLATE_EXTENSION
    ).translate((0, front.basePlate.BASE_PLATE_BEGIN, 0))
    return result


def splitter():
    result = cq.Workplane("XY")

    result.add(splitXSides(-1).translate((PADDING_WIDTH, 0, 0)))

    for X1 in SEGMENT_POSITIONS:
        segment = front.segment.segmentSplitTop.translate((X1, 0, 0))
        result = result.union(segment)

    for X1 in SEGMENT_POSITIONS[1:]:
        segment = front.segment.splitSegmentX.translate((X1, 0, 0))
        result = result.union(segment)

    result.add(splitXSides(1).translate((WIDTH - PADDING_WIDTH, 0, 0)))

    basePlateScrewXPositions = [PADDING_WIDTH / 2]

    for X1 in SEGMENT_POSITIONS:
        basePlateScrewXPositions.append(X1 + SEGMENT_WIDTH / 2)

    basePlateScrewXPositions.append(WIDTH - PADDING_WIDTH / 2)

    result.add(front.basePlate.bottomDrillings(basePlateScrewXPositions))

    return result


def air():

    volume = shapes.boxFromBounds(
        0,
        ALL_SEGMENTS_WIDTH,
        -10,
        DEPTH + DEPTH_EXTENSION + front.segment.OUTLET_DEPTH,
        0,
        HEIGHT + front.basePlate.BASE_PLATE_HEIGHT,
    ).translate((0, 0, -front.basePlate.BASE_PLATE_HEIGHT))

    outletVolumeExtension = shapes.box(
        ALL_SEGMENTS_WIDTH,
        2,
        1,
    ).translate(
        (
            0,
            front.segment.WALL_STRENGTH + front.segment.FOAM_DEPTH * 2,
            -front.basePlate.BASE_PLATE_HEIGHT - 1,
        )
    )

    return volume.union(outletVolumeExtension).translate(
        (PADDING_WIDTH + SIDE_WALL_WIDTH, 0, 0)
    )


def foam():
    result = cq.Workplane("XY")
    for X1 in SEGMENT_POSITIONS:
        segmentFoam = front.segment.foam.translate((X1, 0, 0))
        result = result.union(segmentFoam)
    return result


def filterSolids():
    result = cq.Workplane("XY")
    for X1 in SEGMENT_POSITIONS:
        segmentFilterSolid = front.segment.filterSet.male.union(
            front.segment.filterSet.female
        ).translate((X1, 0, 0))
        result = result.union(segmentFilterSolid)
    return result


def fanSolids():
    result = cq.Workplane("XY")
    for X1 in SEGMENT_POSITIONS:
        segmentFan = front.segment.fanSet.housing.translate((X1, 0, 0))
        result = result.union(segmentFan)
    return result


def filterMedia():
    result = cq.Workplane("XY")
    for X1 in SEGMENT_POSITIONS:
        segmentFilterMedia = front.segment.filterSet.medium.translate((X1, 0, 0))
        result = result.union(segmentFilterMedia)
    return result


import export


def exportForFem():

    _full = full()
    _foam = foam()
    _filterSolids = filterSolids()
    _fanSolids = fanSolids()
    _filterMedia = filterMedia()
    _air = air().cut(
        _full.union(_foam).union(_filterSolids).union(_filterMedia).union(_fanSolids)
    )

    export.combined_nastran(
        [_air, _foam, _filterMedia],
        "build/System.nas",
        max_element_size=10,
    )
