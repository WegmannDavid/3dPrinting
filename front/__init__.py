from prelude import *


import shapes

WIDTH = 1144
SIDE_WALL_WIDTH = 0

DEPTH = 70
DEPTH_EXTENSION = 10
EXTENDED_DEPTH = DEPTH + DEPTH_EXTENSION
DEPTH_EXTENSIONZ = 15

HEIGHT = 210


SEGMENT_WIDTH = 250
NUM_SEGMENTS = 1
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
        .extrude(WIDTH - 2 * PADDING_WIDTH)
    ).translate((PADDING_WIDTH, 0, 0))

    base = top.union(front.basePlate.basePlate(WIDTH))
    return base


def full():
    _base = base()

    for X1 in SEGMENT_POSITIONS:
        segment = front.segment.segmentCutout.translate((X1, 0, 0))
        _base = _base.cut(segment)

    return _base


SLOPE_SEAL_WIDTH = 2


def splitXSides(slopeDirection):
    return (
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

    basePlateScrewXPositions = [PADDING_WIDTH / 2, PADDING_WIDTH * 1.5]

    for X1 in SEGMENT_POSITIONS[1:]:
        basePlateScrewXPositions.append(X1 + SEGMENT_SCREW_X_OFFSET)

    basePlateScrewXPositions.append(WIDTH - PADDING_WIDTH / 2)
    basePlateScrewXPositions.append(WIDTH - PADDING_WIDTH * 1.5)

    result.add(front.basePlate.bottomDrillings(basePlateScrewXPositions))

    return result


def air():

    volume = shapes.boxFromBounds(
        0,
        ALL_SEGMENTS_WIDTH,
        -10,
        DEPTH + DEPTH_EXTENSION + front.segment.INNER_DUCT_DEPTH,
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
