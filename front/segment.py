import math

from prelude import *

import shapes

import front

# Every segment is the same width; it used to be threaded through every
# function as a parameter, but it was always front.SEGMENT_WIDTH.
WIDTH = front.SEGMENT_WIDTH

WALL_STRENGTH = NOZZLE * 8

OUTLET_DEPTH = 2

NUM_OUTLETS = 5
OUTLET_X_GAP_WIDTH = WALL_STRENGTH

FOAM_DEPTH = 10
INNER_DUCT_DEPTH = 8
FOAM_BOX_DEPTH = (
    WALL_STRENGTH + FOAM_DEPTH * 2 + INNER_DUCT_DEPTH + FOAM_DEPTH * 2 + WALL_STRENGTH
)
FILTER_DEPTH = 12


import duct.solid

OUTLET_DUCT_HEIGHT_ABOVE_BASE_PLATE = 20
OUTLET_STRUT_STRENGTH = NOZZLE * 6


import external.fan.Centrifugal

FAN_OFFSET = WALL_STRENGTH + 10 + external.fan.Centrifugal.SIZE
FAN_CENTER_OFFSET = FAN_OFFSET - external.fan.Centrifugal.SIZE / 2


def _build_fanSet():
    fan = external.fan.Centrifugal.centrifugalFanSet(10)
    fan = fan.translate(
        (
            WIDTH - FAN_OFFSET,
            WALL_STRENGTH + 10,
            front.HEIGHT - external.fan.Centrifugal.SIZE - WALL_STRENGTH - 10,
        )
    )
    return fan


SCREW_PADDING = external.m3.TOP_OFFSET * 2


def _build_foam():
    f1 = shapes.boxFromBounds(
        WALL_STRENGTH,
        WIDTH - WALL_STRENGTH,
        WALL_STRENGTH,
        WALL_STRENGTH + FOAM_DEPTH * 2,
        0,
        front.HEIGHT - WALL_STRENGTH,
    )
    f2 = f1.translate((0, INNER_DUCT_DEPTH + FOAM_DEPTH * 2, 0))
    f3 = shapes.boxFromBounds(
        WALL_STRENGTH,
        WIDTH - WALL_STRENGTH,
        WALL_STRENGTH,
        FOAM_BOX_DEPTH - WALL_STRENGTH,
        front.HEIGHT - WALL_STRENGTH - FOAM_DEPTH,
        front.HEIGHT - WALL_STRENGTH,
    )
    outletWall = shapes.boxFromBounds(
        WALL_STRENGTH,
        WIDTH - WALL_STRENGTH,
        WALL_STRENGTH + FOAM_DEPTH * 2 - NOZZLE * 2,
        WALL_STRENGTH + FOAM_DEPTH * 2 + INNER_DUCT_DEPTH + NOZZLE * 2,
        0,
        OUTLET_DUCT_HEIGHT_ABOVE_BASE_PLATE,
    )
    screwCutoutl = shapes.box(SCREW_PADDING, INNER_DUCT_DEPTH, FOAM_DEPTH).translate(
        (
            0,
            WALL_STRENGTH + FOAM_DEPTH * 2,
            front.HEIGHT - WALL_STRENGTH - FOAM_DEPTH,
        )
    )
    screwCutoutr = screwCutoutl.translate((WIDTH - SCREW_PADDING, 0, 0))
    return (
        f1.union(f2)
        .union(f3)
        .cut(outletWall)
        .cut(fanSet.cutout)
        .cut(screwCutoutl)
        .cut(screwCutoutr)
    )


def _build_outletCutout():
    bottomNarrowing = duct.solid.bezierDuctProfile(
        portDim="Y",
        lengthDim="Z",
        s1=0,
        e1=INNER_DUCT_DEPTH,
        s2=3,
        e2=5,
        l1=OUTLET_DUCT_HEIGHT_ABOVE_BASE_PLATE,
        l2=-front.basePlate.BASE_PLATE_HEIGHT,
    ).extrude(WIDTH)
    segments = duct.solid.arrayAlongXOfDuctsAlongZ(
        num=5,
        topX1=WALL_STRENGTH,
        topX2=WIDTH - WALL_STRENGTH,
        botX1=OUTLET_STRUT_STRENGTH / 2,
        botX2=WIDTH - OUTLET_STRUT_STRENGTH / 2,
        depth=-INNER_DUCT_DEPTH,
        topSep=NOZZLE * 2,
        botSep=OUTLET_STRUT_STRENGTH,
        Y1=-front.basePlate.BASE_PLATE_HEIGHT,
        Y2=OUTLET_DUCT_HEIGHT_ABOVE_BASE_PLATE,
    )
    result = bottomNarrowing.intersect(segments)
    return result


def _build_innerDuctCutout():
    w1 = 90
    result = (
        cq.Workplane("XZ")
        .moveTo(WALL_STRENGTH, OUTLET_DUCT_HEIGHT_ABOVE_BASE_PLATE)
        .bezier(
            [
                (WALL_STRENGTH, OUTLET_DUCT_HEIGHT_ABOVE_BASE_PLATE),
                (WALL_STRENGTH, front.HEIGHT - FOAM_DEPTH - WALL_STRENGTH - w1),
                (WALL_STRENGTH + w1, front.HEIGHT - FOAM_DEPTH - WALL_STRENGTH),
            ]
        )
        .lineTo(WIDTH - SCREW_PADDING, front.HEIGHT - FOAM_DEPTH - WALL_STRENGTH)
        .lineTo(WIDTH - WALL_STRENGTH, OUTLET_DUCT_HEIGHT_ABOVE_BASE_PLATE)
        .close()
    ).extrude(-INNER_DUCT_DEPTH)

    return result


def _build_ductCutout():
    i = innerDuctCutout
    o = outletCutout
    return i.union(o).translate((0, WALL_STRENGTH + FOAM_DEPTH * 2, 0))


FILTER_ANGLE = -math.degrees(
    cq.Vector(0, 0, 1).getAngle(cq.Vector(0, front.DEPTH_EXTENSION, front.HEIGHT))
)


def _build_filterSet():
    import front.filter

    return (
        front.filter.set(
            DEPTH=FILTER_DEPTH,
            HEIGHT=front.HEIGHT,
            WIDTH=WIDTH - WALL_STRENGTH * 2,
            DOWNWARD_EXTENSION=front.basePlate.BASE_PLATE_HEIGHT,
        )
        .translate((WALL_STRENGTH, front.DEPTH - FILTER_DEPTH, 0))
        .rotate(
            (0, front.DEPTH - FILTER_DEPTH, 0),
            (1, front.DEPTH - FILTER_DEPTH, 0),
            FILTER_ANGLE,
        )
    )


import loft


def _build_collectorCutout():
    fs = filterSet

    fan = fanSet
    return loft.closed_bezier_loft(
        loft.polygon_endpoint(
            fs.port.vertices,
            [(0, -WALL_STRENGTH * 2, 0)] * 4,
        ),
        loft.circular_port_to_endpoint(
            fan.inlet, start_reference=(0, 0, 0), tangent_length=-WALL_STRENGTH * 3
        ),
    )


import external.fan


def _build_segmentCutout():
    f = foam

    duct = ductCutout

    filter = filterSet

    fan = fanSet

    collector = collectorCutout

    return f.union(duct).union(filter.cutout).union(collector).union(fan.cutout)


SPLIT_Z = front.HEIGHT - WALL_STRENGTH - FOAM_DEPTH - 40


def _build_segmentSplitTop():
    topBox = shapes.box(WIDTH, front.EXTENDED_DEPTH, WALL_STRENGTH).translate(
        (0, 0, front.HEIGHT - WALL_STRENGTH)
    )
    topExtensionBox = shapes.boxFromBounds(
        SCREW_PADDING,
        WIDTH - SCREW_PADDING,
        FOAM_BOX_DEPTH - WALL_STRENGTH,
        front.EXTENDED_DEPTH,
        SPLIT_Z,
        front.HEIGHT,
    )
    topFilterBox = shapes.boxFromBounds(
        0,
        WIDTH,
        FOAM_BOX_DEPTH + SCREW_PADDING,
        front.EXTENDED_DEPTH,
        SPLIT_Z,
        front.HEIGHT,
    )
    top = topBox.union(topExtensionBox).union(topFilterBox)

    import split

    topShell = split.shell(top)

    s = external.m3.m3(40, WALL_STRENGTH).translate(
        (
            external.m3.TOP_OFFSET,
            0,
            front.HEIGHT,
        )
    )

    s1 = s.translate((0, WALL_STRENGTH + FOAM_DEPTH * 2 + INNER_DUCT_DEPTH / 2, 0))
    s2 = s.translate((0, FOAM_BOX_DEPTH + external.m3.TOP_OFFSET, 0))
    s12 = s1.union(s2)
    s34 = s12.mirror("YZ").translate((WIDTH, 0, 0))

    import split.hbar

    CLIP_RAD = external.fan.Centrifugal.INTAKE_RADIUS

    h1 = split.hbar.feature(WIDTH - WALL_STRENGTH * 2).translate(
        (WALL_STRENGTH, WALL_STRENGTH / 2, front.HEIGHT - WALL_STRENGTH)
    )

    h2 = split.hbar.feature(
        WIDTH - SCREW_PADDING - FAN_CENTER_OFFSET - CLIP_RAD
    ).translate(
        (
            SCREW_PADDING,
            FOAM_BOX_DEPTH - WALL_STRENGTH / 2,
            SPLIT_Z,
        )
    )
    h3 = split.hbar.feature(FAN_CENTER_OFFSET - SCREW_PADDING - CLIP_RAD).translate(
        (
            WIDTH - (FAN_CENTER_OFFSET - CLIP_RAD),
            FOAM_BOX_DEPTH - WALL_STRENGTH / 2,
            SPLIT_Z,
        )
    )
    result = topShell.union(s12).union(s34)
    result = split.addFeature(result, h1.union(h2).union(h3))

    return result


def _build_splitSegmentX():
    import split.vbar

    contact = 3

    p = split.planeYZ(
        front.basePlate.BASE_PLATE_BEGIN,
        front.EXTENDED_DEPTH,
        -front.basePlate.BASE_PLATE_HEIGHT,
        front.HEIGHT,
    )
    v1 = split.vbar.spread(
        0,
        WALL_STRENGTH + FOAM_DEPTH * 2,
        -front.basePlate.BASE_PLATE_HEIGHT,
        front.HEIGHT - WALL_STRENGTH,
        2,
        contact,
    )
    v2 = split.vbar.spread(
        WALL_STRENGTH + FOAM_DEPTH * 2 + INNER_DUCT_DEPTH,
        FOAM_BOX_DEPTH + external.m3.TOP_OFFSET * 2,
        -front.basePlate.BASE_PLATE_HEIGHT,
        front.HEIGHT - WALL_STRENGTH,
        2,
        contact,
    )
    v3 = split.vbar.spread(
        FOAM_BOX_DEPTH + external.m3.TOP_OFFSET * 2,
        front.DEPTH,
        -front.basePlate.BASE_PLATE_HEIGHT,
        SPLIT_Z,
        1,
        contact,
    )
    return split.addFeature(p, v1.union(v2).union(v3).union(front.basePlate.vBars()))


# ---------------------------------------------------------------------------
# A segment is identical across the unit, so every piece is built exactly
# once here (at import) and reused. Callers translate copies; CadQuery's
# translate/cut/union return new objects, so the shared originals are safe.
# Assigned in dependency order: each builder reads the globals defined above.
# ---------------------------------------------------------------------------
fanSet = _build_fanSet()
foam = _build_foam()
outletCutout = _build_outletCutout()
innerDuctCutout = _build_innerDuctCutout()
ductCutout = _build_ductCutout()
filterSet = _build_filterSet()
collectorCutout = _build_collectorCutout()
segmentCutout = _build_segmentCutout()
segmentSplitTop = _build_segmentSplitTop()
splitSegmentX = _build_splitSegmentX()
