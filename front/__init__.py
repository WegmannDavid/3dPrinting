from prelude import *


import shapes

WIDTH = 1144
SIDE_WALL_WIDTH = 10

DEPTH = 100
DEPTH_EXTENSION = 10
EXTENDED_DEPTH = DEPTH + DEPTH_EXTENSION
DEPTH_EXTENSIONZ = 15

HEIGHT = 210

import front.basePlate
import front.segment

SEGMENT_WIDTH = 200
NUM_SEGMENTS = 5
ALL_SEGMENTS_WIDTH = SEGMENT_WIDTH * NUM_SEGMENTS
PADDING_WIDTH = (WIDTH - ALL_SEGMENTS_WIDTH - 2 * SIDE_WALL_WIDTH) / 2

FANS_PER_SEGMENT = 2

SEGMENT_POSITIONS = [
    PADDING_WIDTH + SIDE_WALL_WIDTH + i * SEGMENT_WIDTH for i in range(NUM_SEGMENTS)
]

SEGMENT_SCREW_X_OFFSET = 10


def base():
    top = (
        cq.Workplane("YZ")
        .moveTo(0, 0)
        .lineTo(0, HEIGHT)
        .lineTo(DEPTH + DEPTH_EXTENSION, HEIGHT)
        .lineTo(DEPTH + DEPTH_EXTENSION, DEPTH_EXTENSIONZ)
        .lineTo(DEPTH, DEPTH_EXTENSIONZ - DEPTH_EXTENSION)
        .lineTo(DEPTH, 0)
        .close()
        .extrude(WIDTH - 2 * PADDING_WIDTH)
    ).translate((PADDING_WIDTH, 0, 0))

    base = top.union(front.basePlate.basePlate(WIDTH))
    return base


FOAM_Y = front.segment.WALL_STRENGTH * 3 + front.segment.OUTLET_DUCT_DEPTH
FOAM_Z = front.HEIGHT - front.segment.EXPANDER_HEIGHT + front.segment.WALL_STRENGTH * 2
FOAM_DEPTH = 50


def full():
    _base = base()

    for X1 in SEGMENT_POSITIONS:
        segment = front.segment.segmentCutout(
            SEGMENT_WIDTH, FANS_PER_SEGMENT
        ).translate((X1, 0, 0))
        _base = _base.cut(segment)

    cableChannel = shapes.extrudePolygon(
        front.segment.cableChannelPolygon(), "YZ", WIDTH
    )
    _base = _base.cut(cableChannel)

    # Cut out foam space

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


import split.vbar


def splitX(X):
    Y1 = front.basePlate.BASE_PLATE_BEGIN
    Y2 = EXTENDED_DEPTH
    return split.vbar.splitXYWithVBars(
        Y1,
        Y2,
        -front.basePlate.BASE_PLATE_HEIGHT,
        front.HEIGHT,
        front.basePlate.vBars() + front.segment.vBars(),
        2,
    ).translate((X, 0, 0))


def splitter():
    result = cq.Workplane("XY")
    for X1 in SEGMENT_POSITIONS:
        segment = front.segment.splitSegment(SEGMENT_WIDTH, FANS_PER_SEGMENT).translate(
            (X1, 0, 0)
        )
        result = result.union(segment)

    result.add(splitXSides(-1).translate((PADDING_WIDTH, 0, 0)))

    for X1 in SEGMENT_POSITIONS[1:]:
        splitSegments = splitX(X1)
        result = result.union(splitSegments)

    result.add(splitXSides(1).translate((WIDTH - PADDING_WIDTH, 0, 0)))

    basePlateScrewXPositions = [PADDING_WIDTH / 2, PADDING_WIDTH * 1.5]

    for X1 in SEGMENT_POSITIONS[1:]:
        basePlateScrewXPositions.append(X1 + SEGMENT_SCREW_X_OFFSET)

    basePlateScrewXPositions.append(WIDTH - PADDING_WIDTH / 2)
    basePlateScrewXPositions.append(WIDTH - PADDING_WIDTH * 1.5)

    result.add(front.basePlate.bottomDrillings(basePlateScrewXPositions))

    return result


def air():

    volume = shapes.box(
        ALL_SEGMENTS_WIDTH,
        DEPTH + DEPTH_EXTENSION,
        HEIGHT + front.basePlate.BASE_PLATE_HEIGHT,
    ).translate((0, 0, -front.basePlate.BASE_PLATE_HEIGHT))

    return volume.translate((PADDING_WIDTH + SIDE_WALL_WIDTH, 0, 0))


def foam():
    result = cq.Workplane("XY")
    for X1 in SEGMENT_POSITIONS:
        segmentFoam = front.segment.foam(SEGMENT_WIDTH).translate((X1, 0, 0))
        result = result.union(segmentFoam)
    return result


import export


def exportForFem():
    _full = full()
    _foam = foam()
    _air = air().cut(_full.union(_foam))

    airCutout = (
        shapes.box(ALL_SEGMENTS_WIDTH, front.segment.FOAM_OFFSET_Y + 1, 1)
        .translate(
            (
                0,
                0,
                front.segment.OUTLET_DUCT_HEIGHT_ABOVE_BASEPLATE
                + front.segment.WALL_STRENGTH
                + 1,
            )
        )
        .translate((PADDING_WIDTH + SIDE_WALL_WIDTH, 0, 0))
    )
    _air = _air.cut(airCutout)

    outletAir = shapes.box(
        ALL_SEGMENTS_WIDTH - front.segment.OUTLET_X_GAP_WIDTH,
        front.segment.OUTLET_DUCT_DEPTH,
        1,
    ).translate(
        (
            PADDING_WIDTH + SIDE_WALL_WIDTH + front.segment.OUTLET_X_GAP_WIDTH / 2,
            front.segment.WALL_STRENGTH,
            -front.basePlate.BASE_PLATE_HEIGHT - 1,
        )
    )
    inletAir = shapes.box(
        ALL_SEGMENTS_WIDTH - front.segment.OUTLET_X_GAP_WIDTH,
        front.segment.OUTLET_DUCT_DEPTH,
        1,
    ).translate(
        (
            PADDING_WIDTH + SIDE_WALL_WIDTH + front.segment.OUTLET_X_GAP_WIDTH / 2,
            front.segment.WALL_STRENGTH,
            front.segment.OUTLET_DUCT_HEIGHT_ABOVE_BASEPLATE,
        )
    )

    actualInletAir = shapes.box(
        ALL_SEGMENTS_WIDTH,
        front.segment.OUTLET_DUCT_DEPTH,
        1,
    ).translate(
        (
            PADDING_WIDTH + SIDE_WALL_WIDTH + front.segment.OUTLET_X_GAP_WIDTH / 2,
            EXTENDED_DEPTH + 20,
            -front.basePlate.BASE_PLATE_HEIGHT - 1,
        )
    )

    export.combined_nastran(
        [_air.union(actualInletAir).union(outletAir), _foam],
        "build/System.nas",
        max_element_size=10,
    )
