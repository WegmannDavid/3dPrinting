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
FILTER_DEPTH = 16


import duct.solid

OUTLET_DUCT_HEIGHT_ABOVE_BASE_PLATE = 30
OUTLET_STRUT_STRENGTH = NOZZLE * 6


import external.fan.Centrifugal

FAN_OFFSET = WALL_STRENGTH + FOAM_DEPTH + external.fan.Centrifugal.SIZE
FAN_CENTER_OFFSET = FAN_OFFSET - external.fan.Centrifugal.SIZE / 2


def _build_fanSet():
    fan = external.fan.Centrifugal.centrifugalFanSet(FOAM_DEPTH)
    fan = fan.translate(
        (
            WIDTH - FAN_OFFSET,
            WALL_STRENGTH + FOAM_DEPTH,
            front.HEIGHT - external.fan.Centrifugal.SIZE - WALL_STRENGTH - FOAM_DEPTH,
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
    ic = fanSet.inletCutout
    return (
        f1.union(f2)
        .union(f3)
        .cut(outletWall)
        .cut(fanSet.cutout)
        .cut(screwCutoutl)
        .cut(screwCutoutr)
        .cut(ic)
    )


def _build_outletCutout():
    MIDDLE_Z = 20
    reducer = duct.solid.bezierDuctProfile(
        portDim="Y",
        lengthDim="Z",
        s1=0,
        e1=INNER_DUCT_DEPTH,
        s2=3,
        e2=5,
        l1=OUTLET_DUCT_HEIGHT_ABOVE_BASE_PLATE,
        l2=MIDDLE_Z,
    ).extrude(WIDTH)
    expander = duct.solid.bezierDuctProfile(
        portDim="Y",
        lengthDim="Z",
        s1=0,
        e1=INNER_DUCT_DEPTH,
        s2=3,
        e2=5,
        l1=-front.basePlate.BASE_PLATE_HEIGHT,
        l2=MIDDLE_Z,
    ).extrude(WIDTH)
    outletSegments = duct.solid.arrayAlongXOfDuctsAlongZ(
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
    result = reducer.union(expander).intersect(outletSegments)
    return result


def _build_innerDuctCutout():
    w1 = 90 + WALL_STRENGTH
    result = (
        cq.Workplane("XZ")
        .moveTo(WALL_STRENGTH, OUTLET_DUCT_HEIGHT_ABOVE_BASE_PLATE)
        .bezier(
            [
                (WALL_STRENGTH, OUTLET_DUCT_HEIGHT_ABOVE_BASE_PLATE),
                (WALL_STRENGTH, front.HEIGHT - FOAM_DEPTH - WALL_STRENGTH - w1),
                (w1, front.HEIGHT - FOAM_DEPTH - WALL_STRENGTH),
            ]
        )
        .lineTo(WIDTH - SCREW_PADDING, front.HEIGHT - FOAM_DEPTH - WALL_STRENGTH)
        .lineTo(WIDTH - WALL_STRENGTH, OUTLET_DUCT_HEIGHT_ABOVE_BASE_PLATE)
        .close()
    ).extrude(-INNER_DUCT_DEPTH)

    supportCutout = shapes.supportsAlongYForZ(
        w1 - SCREW_PADDING,
        INNER_DUCT_DEPTH,
        front.HEIGHT
        - FOAM_DEPTH
        - WALL_STRENGTH * 1.5
        - OUTLET_DUCT_HEIGHT_ABOVE_BASE_PLATE,
        WALL_STRENGTH / 2,
        4,
        1,
    ).translate((SCREW_PADDING, 0, OUTLET_DUCT_HEIGHT_ABOVE_BASE_PLATE))
    supportCutout = supportCutout.cut(
        result.translate((-WALL_STRENGTH, 0, WALL_STRENGTH))
    )
    return result.union(supportCutout)


def _build_ductCutout():
    i = innerDuctCutout
    o = outletCutout
    return i.union(o).translate((0, WALL_STRENGTH + FOAM_DEPTH * 2, 0))


FILTER_ANGLE = -math.degrees(
    cq.Vector(0, 0, 1).getAngle(cq.Vector(0, front.DEPTH_EXTENSION, front.HEIGHT))
)

HANDLE_HEIGHT = 30
HANDLE_DEPTH = 18


def _build_filterSet():
    import front.filter

    FILTER_Z = HANDLE_HEIGHT - front.basePlate.BASE_PLATE_HEIGHT

    untrimmed = (
        front.filter.set(
            DEPTH=FILTER_DEPTH,
            HEIGHT=front.HEIGHT - FILTER_Z,
            WIDTH=WIDTH - WALL_STRENGTH * 2,
            HANDLE_HEIGHT=FILTER_Z + front.basePlate.BASE_PLATE_HEIGHT,
            HANDLE_DEPTH=HANDLE_DEPTH,
        )
        .mirror("XZ")
        .translate(
            (
                WALL_STRENGTH,
                front.DEPTH,
                FILTER_Z,
            )
        )
        .rotate(
            (0, front.DEPTH - HANDLE_DEPTH, 0),
            (1, front.DEPTH - HANDLE_DEPTH, 0),
            FILTER_ANGLE,
        )
    )
    ufemale = untrimmed.female
    untrimmed.female = untrimmed.female.cut(
        shapes.boxFromBounds(
            0,
            WIDTH,
            0,
            front.DEPTH,
            -2 * front.basePlate.BASE_PLATE_HEIGHT,
            -front.basePlate.BASE_PLATE_HEIGHT,
        )
    )
    female = untrimmed.female
    male = untrimmed.male
    return untrimmed


import loft


def _build_collectorCutout():
    fs = filterSet

    fan = fanSet
    return loft.closed_bezier_loft(
        loft.polygon_endpoint(
            fs.port.vertices,
            [(0, -WALL_STRENGTH * 1.5, 0)] * 4,
        ),
        loft.circular_port_to_endpoint(
            fan.inlet, start_reference=(0, 0, 0), tangent_length=-WALL_STRENGTH * 2
        ),
    )


def _build_segmentCutout():
    f = foam

    duct = ductCutout

    filter = filterSet.cutout

    fan = fanSet.cutout

    collector = collectorCutout

    cable = cableCutout

    intakeCutout = fanSet.inletCutout

    return (
        f.union(duct)
        .union(filter)
        .union(collector)
        .union(fan)
        .union(cable)
        .union(intakeCutout)
    )


SPLIT_Z1 = front.HEIGHT - FAN_CENTER_OFFSET
SPLIT_Z2 = front.HEIGHT - WALL_STRENGTH - FOAM_DEPTH


def _build_segmentSplitTop():
    topBox = shapes.box(
        WIDTH, front.EXTENDED_DEPTH, WALL_STRENGTH + FOAM_DEPTH
    ).translate((0, 0, SPLIT_Z2))
    PADDING_X = (
        WALL_STRENGTH
        + front.filter.RIM
        + front.filter.CLAMP_STRENGTH
        + front.filter.GAP
    )
    topFilterExtensions = shapes.boxFromBounds(
        PADDING_X,
        WIDTH - PADDING_X,
        FOAM_BOX_DEPTH - WALL_STRENGTH,
        front.EXTENDED_DEPTH,
        SPLIT_Z1,
        front.HEIGHT,
    )
    top = topBox.union(topFilterExtensions)

    import split

    topShell = split.shell(top)

    s = external.m3.m3(40, front.HEIGHT - SPLIT_Z2).translate(
        (
            external.m3.TOP_OFFSET,
            0,
            front.HEIGHT,
        )
    )

    s1 = s.translate((0, WALL_STRENGTH + FOAM_DEPTH * 2 + INNER_DUCT_DEPTH / 2, 0))
    s2 = s.translate((WALL_STRENGTH, FOAM_BOX_DEPTH + external.m3.TOP_OFFSET, 0))
    s12 = s1.union(s2)
    s34 = s12.mirror("YZ").translate((WIDTH, 0, 0))

    import split.hbar

    CLIP_RAD = external.fan.Centrifugal.INTAKE_RADIUS + 15

    h1 = split.hbar.feature(WIDTH - WALL_STRENGTH * 2).translate(
        (WALL_STRENGTH, WALL_STRENGTH / 2, SPLIT_Z2)
    )

    h2 = split.hbar.feature(WIDTH - PADDING_X - FAN_CENTER_OFFSET - CLIP_RAD).translate(
        (
            PADDING_X,
            FOAM_BOX_DEPTH - WALL_STRENGTH / 2,
            SPLIT_Z1,
        )
    )
    h3 = split.hbar.feature(FAN_CENTER_OFFSET - PADDING_X - CLIP_RAD).translate(
        (
            WIDTH - FAN_CENTER_OFFSET + CLIP_RAD,
            FOAM_BOX_DEPTH - WALL_STRENGTH / 2,
            SPLIT_Z1,
        )
    )
    result = topShell.union(s12).union(s34)
    result = split.addFeature(result, h1.union(h2).union(h3))

    return result


def _build_cableCutout():
    return shapes.box(WIDTH, 10, 3).translate((0, WALL_STRENGTH, SPLIT_Z2))


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
        SPLIT_Z2,
        2,
        contact,
    )
    v2 = split.vbar.spread(
        WALL_STRENGTH + FOAM_DEPTH * 2 + INNER_DUCT_DEPTH,
        front.DEPTH,
        -front.basePlate.BASE_PLATE_HEIGHT,
        SPLIT_Z2,
        3,
        contact,
    )
    return split.addFeature(p, v1.union(v2).union(front.basePlate.vBars()))


# ---------------------------------------------------------------------------
# A segment is identical across the unit, so every piece is built exactly
# once here (at import) and reused. Callers translate copies; CadQuery's
# translate/cut/union return new objects, so the shared originals are safe.
# Assigned in dependency order: each builder reads the globals defined above.
# ---------------------------------------------------------------------------
cableCutout = _build_cableCutout()
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


def pins(NUMX, NUMZ, WIDTH, HEIGHT, PADDING):
    pin = shapes.box(NOZZLE * 2, NOZZLE * 8, NOZZLE * 2).translate(
        (-NOZZLE, -NOZZLE * 4, -NOZZLE)
    )

    result = cq.Workplane("XY")
    for i in range(NUMX):
        for j in range(NUMZ):
            x = PADDING + i * (WIDTH - PADDING * 2) / (NUMX - 1)
            z = PADDING + j * (HEIGHT - PADDING * 2) / (NUMZ - 1)
            result = result.add(pin.translate((x, 0, z)))

    return result.combine(glue=True)


def cutBoxTemplate(WIDTH, DEPTH, HEIGHT, BOTTOM_EXTENSION):
    return (
        shapes.box(
            WIDTH + WALL_STRENGTH * 2,
            DEPTH + WALL_STRENGTH * 2,
            BOTTOM_EXTENSION + HEIGHT + WALL_STRENGTH,
        )
        .translate((-WALL_STRENGTH, -WALL_STRENGTH, -WALL_STRENGTH - BOTTOM_EXTENSION))
        .cut(
            shapes.box(
                WIDTH,
                DEPTH,
                HEIGHT,
            )
        )
    )


def exportTemplates():
    f1 = shapes.boxFromBounds(
        WALL_STRENGTH,
        WIDTH - WALL_STRENGTH,
        0,
        WALL_STRENGTH,
        0,
        front.HEIGHT - WALL_STRENGTH - FOAM_DEPTH,
    )
    pins1 = pins(
        20,
        16,
        WIDTH - WALL_STRENGTH * 2,
        front.HEIGHT - WALL_STRENGTH * 2 - FOAM_DEPTH,
        1,
    ).translate((WALL_STRENGTH, 0, WALL_STRENGTH))
    t1 = f1.union(pins1).cut(fanSet.cutout.translate((0, -FOAM_DEPTH * 2, 0)))

    pins2 = pins(
        12,
        12,
        external.fan.Centrifugal.SIZE,
        external.fan.Centrifugal.SIZE,
        10,
    ).translate(
        (
            WIDTH - FOAM_DEPTH - external.fan.Centrifugal.SIZE - WALL_STRENGTH,
            0,
            front.HEIGHT - WALL_STRENGTH - FOAM_DEPTH - external.fan.Centrifugal.SIZE,
        )
    )

    t2 = f1.union(pins2).intersect(fanSet.cutout.translate((0, -FOAM_DEPTH * 2, 0)))

    ic = fanSet.inletCutout.translate((0, -FOAM_BOX_DEPTH + FOAM_DEPTH, 0))

    t2 = t2.cut(ic)

    import export

    export.step(t1, "foamTemplate1.step")
    export.step(t2, "foamTemplate2.step")
