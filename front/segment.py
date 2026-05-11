import math

from prelude import *


import loft
import shapes

import front
import external
import helmholtz.geometry

WALL_STRENGTH = NOZZLE * 6

SCREW_PADDING = external.m3.TOP_OFFSET + external.m3.OFFSET


OUTLET_DUCT_HEIGHT_ABOVE_BASEPLATE = 80
EXPANDER_HEIGHT = front.HEIGHT - OUTLET_DUCT_HEIGHT_ABOVE_BASEPLATE

BASEPLATE_HEIGHT = 10


OUTLET_DUCT_DEPTH = 3
OUTLET_DEPTH = 4
FOAM_DEPTH = 20
FOAM_OFFSET_Y = WALL_STRENGTH + OUTLET_DUCT_DEPTH
RESONATOR_WALL_OFFSET_Y = FOAM_OFFSET_Y + FOAM_DEPTH
RESONATOR_OFFSET_Y = RESONATOR_WALL_OFFSET_Y + WALL_STRENGTH
RESONATOR_F1 = 200
RESONATOR_F2 = 800

OUTLETS_PER_FAN = 2
OUTLET_X_GAP_WIDTH = WALL_STRENGTH

SQRT2 = math.sqrt(2)

import external.fan.Axial

FAN = external.fan.Axial.axial80x80x25mm()

LONG_OFFSET = FAN.PARAMETERS.CUTOUT_SIZE * (SQRT2 / 2)
SHORT_OFFSET = FAN.PARAMETERS.CUTOUT_LENGTH * (SQRT2 / 2)

TOP_HEIGHT = SHORT_OFFSET + WALL_STRENGTH
BOTTOM_HEIGHT = front.HEIGHT - TOP_HEIGHT


import duct.solid


def singleFanOutlet(width):
    outletDuct = shapes.box(
        width - OUTLET_X_GAP_WIDTH,
        OUTLET_DUCT_DEPTH,
        OUTLET_DUCT_HEIGHT_ABOVE_BASEPLATE + BASEPLATE_HEIGHT + WALL_STRENGTH,
    ).translate((OUTLET_X_GAP_WIDTH / 2, WALL_STRENGTH, -BASEPLATE_HEIGHT))

    for i in range(1, OUTLETS_PER_FAN):
        v = duct.solid.guidingVaneAlongZ(
            OUTLET_X_GAP_WIDTH,
            NOZZLE * 2,
            OUTLET_DUCT_DEPTH,
            BASEPLATE_HEIGHT + OUTLET_DUCT_HEIGHT_ABOVE_BASEPLATE + WALL_STRENGTH,
        ).translate(((width / OUTLETS_PER_FAN) * i, WALL_STRENGTH, -BASEPLATE_HEIGHT))
        outletDuct = outletDuct.cut(v)

    return outletDuct


def outletDuct(width, numFans):
    result = cq.Workplane("XY")
    for i in range(numFans):
        result = result.union(
            singleFanOutlet(width / numFans).translate(((width / numFans) * i, 0, 0))
        )
    return result


def fanEllbow(OUTLET_X1, OUTLET_X2, INLET_X1, INLET_X2):

    OUTLET_WIDTH = OUTLET_X2 - OUTLET_X1
    INLET_WIDTH = INLET_X2 - INLET_X1

    INLET_MIDDLE_X = INLET_X1 + INLET_WIDTH / 2

    OUTLET_MIDDLE_X = OUTLET_X1 + OUTLET_WIDTH / 2

    FAN_MIDDLE_X = INLET_MIDDLE_X

    FAN_OFFSET_X = FAN_MIDDLE_X - FAN.PARAMETERS.CUTOUT_SIZE / 2

    fanSet = FAN.rotate(
        axisStartPoint=(0, 0, 0), axisEndPoint=(1, 0, 0), angleDegrees=-45
    ).translate(
        (FAN_OFFSET_X, WALL_STRENGTH, front.HEIGHT - SHORT_OFFSET - WALL_STRENGTH)
    )

    REFERENCE_POINT_OUTLET = (OUTLET_MIDDLE_X, 0, front.HEIGHT)
    REFERENCE_POINT_INLET = (
        FAN_MIDDLE_X,
        front.DEPTH + front.DEPTH_EXTENSION,
        front.HEIGHT,
    )

    EXPANDER_Y = OUTLET_DUCT_HEIGHT_ABOVE_BASEPLATE + WALL_STRENGTH

    def rectAfterFan():
        return loft.polygon_endpoint(
            [
                (OUTLET_X2, WALL_STRENGTH, EXPANDER_Y),
                (OUTLET_X1, WALL_STRENGTH, EXPANDER_Y),
                (OUTLET_X1, WALL_STRENGTH + OUTLET_DUCT_DEPTH, EXPANDER_Y),
                (OUTLET_X2, WALL_STRENGTH + OUTLET_DUCT_DEPTH, EXPANDER_Y),
            ],
            [
                (0, 0, -EXPANDER_HEIGHT / 2),
                (0, 0, -EXPANDER_HEIGHT / 2),
                (0, 0, -EXPANDER_HEIGHT / 6),
                (0, 0, -EXPANDER_HEIGHT / 6),
            ],
            REFERENCE_POINT_OUTLET,
        )

    def inletRect():
        D = FAN.PARAMETERS.CUTOUT_SIZE + FAN.PARAMETERS.CUTOUT_DUCT_INSET
        Y = front.DEPTH + front.DEPTH_EXTENSION
        Z1 = front.HEIGHT - D * (SQRT2 / 2)
        Z2 = front.HEIGHT - WALL_STRENGTH
        return loft.polygon_endpoint(
            [
                (INLET_X2, Y, Z1),
                (INLET_X1, Y, Z1),
                (INLET_X1, Y, Z2),
                (INLET_X2, Y, Z2),
            ],
            [
                (0, 0, -10),
                (0, 0, -10),
                (0, (Y - SHORT_OFFSET) / 2, 0),
                (0, (Y - SHORT_OFFSET) / 2, 0),
            ],
            REFERENCE_POINT_INLET,
        )

    reducer = loft.closed_bezier_loft(
        loft.circular_port_to_endpoint(
            fanSet.bottomPort,
            start_reference=REFERENCE_POINT_OUTLET,
            tangent_length=fanSet.PARAMETERS.CUTOUT_DUCT_INSET * (SQRT2 / 2),
        ),
        rectAfterFan(),
    )

    expander = loft.closed_bezier_loft(
        loft.circular_port_to_endpoint(
            fanSet.topPort,
            start_reference=REFERENCE_POINT_OUTLET,
            tangent_length=fanSet.PARAMETERS.CUTOUT_DUCT_INSET * (SQRT2 / 2) / 2,
        ),
        inletRect(),
    )

    fanCutout = fanSet.cutout

    return expander.union(fanCutout).union(reducer)


import external.m3
import split


def interval(start, end, num, gap):
    width = end - start
    step = width / num
    return [
        (start + gap / 2 + i * step, start + i * step + step - gap / 2)
        for i in range(num)
    ]


def safe_line_to(wp, x, y, tol=1e-6):
    cx, cy = wp.val().Center().x, wp.val().Center().y  # not always reliable
    # Better: track points yourself, see option 3
    if abs(cx - x) < tol and abs(cy - y) < tol:
        return wp
    return wp.lineTo(x, y)


def singleResonatorCutout(width):
    ReferenceY = WALL_STRENGTH + SHORT_OFFSET + LONG_OFFSET + WALL_STRENGTH * SQRT2
    ReferenceZ = front.HEIGHT - LONG_OFFSET - WALL_STRENGTH

    Y1 = RESONATOR_OFFSET_Y
    Z1 = ReferenceZ - (ReferenceY - Y1)

    Y2 = front.EXTENDED_DEPTH - WALL_STRENGTH
    Z2 = ReferenceZ + (ReferenceY - Y2)

    # CCW polygon (the original was CW when read as YZ tuples).
    # Edge indices (CCW): 0 V0->V1, 1 V1->V2, 2 V2->V3, 3 V3->V4, 4 V4->V5, 5 V5->V0.
    # V4 -> V5 is the vertical left side from (Y1, Z1) down to (Y1, 0): the dock.
    polygon = [
        (
            front.DEPTH - WALL_STRENGTH,
            front.DEPTH_EXTENSIONZ - front.DEPTH_EXTENSION + WALL_STRENGTH * SQRT2 / 2,
        ),
        (
            front.EXTENDED_DEPTH - WALL_STRENGTH,
            front.DEPTH_EXTENSIONZ + WALL_STRENGTH * SQRT2 / 2,
        ),
        (Y2, Z2),
        (ReferenceY, ReferenceZ),
        (Y1, Z1),
        (Y1, OUTLET_DUCT_HEIGHT_ABOVE_BASEPLATE),
        (Y1, 0),
    ]

    return helmholtz.geometry.cavity_array(
        polygon=polygon,
        extrusion_depth=width,
        gravity=(0, -1),
        f1=RESONATOR_F1,
        f2=RESONATOR_F2,
        n_cavities=3,
        neck_length=WALL_STRENGTH,
        dock_edge_index=5,
        wall_strength=WALL_STRENGTH,
        workplane="YZ",
    )


import split.vbar


def resonatorsCutout(width, numFans):
    OUTLETS_PER_SEGMENT = OUTLETS_PER_FAN * numFans
    PADDING = split.vbar.X_REQUIRED
    result = cq.Workplane("XY")

    for X1, X2 in interval(
        PADDING, width - PADDING, OUTLETS_PER_SEGMENT, OUTLET_X_GAP_WIDTH
    ):
        R1 = singleResonatorCutout(X2 - X1).translate((X1, 0, 0))
        result = result.union(R1)

    return result


import split.hbar


def hbarFeatures(width, num):
    result = cq.Workplane("XY")
    for i in range(num):
        result = result.union(
            split.hbar.hbarFeature(width / num - OUTLET_X_GAP_WIDTH).translate(
                (i * width / num + OUTLET_X_GAP_WIDTH / 2, 0, 0)
            )
        )
    return result


def middlePartSplitter(width, numFans):
    OUTLETS_PER_SEGMENT = OUTLETS_PER_FAN * numFans

    boxPart = shapes.box(
        width,
        RESONATOR_WALL_OFFSET_Y,
        front.HEIGHT - OUTLET_DUCT_HEIGHT_ABOVE_BASEPLATE - TOP_HEIGHT,
    ).translate((0, 0, OUTLET_DUCT_HEIGHT_ABOVE_BASEPLATE))

    bottomHrail1 = (
        hbarFeatures(width, OUTLETS_PER_SEGMENT)
        .mirror("XY")
        .translate((0, WALL_STRENGTH / 2, OUTLET_DUCT_HEIGHT_ABOVE_BASEPLATE))
    )

    result = shapes.shell_union(boxPart)
    return split.bulge(result, bottomHrail1)


def foam(WIDTH):
    return shapes.box(
        WIDTH - OUTLET_X_GAP_WIDTH, FOAM_DEPTH, OUTLET_DUCT_HEIGHT_ABOVE_BASEPLATE
    ).translate((OUTLET_X_GAP_WIDTH / 2, FOAM_OFFSET_Y, 0))


def segmentCutout(WIDTH, numFans):

    ducts = cq.Workplane("XY")

    for (X1In, X2In), (X1Out, X2Out) in zip(
        interval(0, WIDTH, numFans, OUTLET_X_GAP_WIDTH),
        interval(SCREW_PADDING, WIDTH - SCREW_PADDING, numFans, OUTLET_X_GAP_WIDTH),
    ):
        ducts = ducts.union(fanEllbow(X1In, X2In, X1Out, X2Out))

    _outletDuct = outletDuct(WIDTH, numFans)

    _foam = foam(WIDTH)

    resonator = resonatorsCutout(WIDTH, numFans)

    return ducts.union(_outletDuct).union(_foam).union(resonator)


import split.vbar

SCREW_OFFSET_X = split.vbar.X_REQUIRED + external.m3.OFFSET


def splitSegment(WIDTH, numFans):
    visualReference = segmentCutout(WIDTH, numFans)
    m3 = external.m3.m3(60, TOP_HEIGHT).translate((0, 0, front.HEIGHT))
    s1 = m3.translate((SCREW_OFFSET_X, RESONATOR_OFFSET_Y + external.m3.OFFSET, 0))
    s2 = m3.translate(
        (WIDTH - SCREW_OFFSET_X, RESONATOR_OFFSET_Y + external.m3.OFFSET, 0)
    )
    s3 = m3.translate(
        (external.m3.TOP_OFFSET, front.EXTENDED_DEPTH - external.m3.TOP_OFFSET, 0)
    )
    s4 = m3.translate(
        (
            WIDTH - external.m3.TOP_OFFSET,
            front.EXTENDED_DEPTH - external.m3.TOP_OFFSET,
            0,
        )
    )
    m3Cutouts = s1.union(s2.union(s3.union(s4)))

    splitPlane = split.planeXY(0, WIDTH, 0, front.EXTENDED_DEPTH).translate(
        (0, 0, front.HEIGHT - TOP_HEIGHT)
    )
    splitMiddlePart = middlePartSplitter(WIDTH, numFans)

    topLeft = split.planeYZ(0, front.EXTENDED_DEPTH, BOTTOM_HEIGHT, front.HEIGHT)
    topRight = topLeft.translate((WIDTH, 0, 0))

    combined = (
        m3Cutouts.union(splitPlane)
        .union(splitMiddlePart)
        .union(topLeft)
        .union(topRight)
    )

    OUTLETS_PER_SEGMENT = OUTLETS_PER_FAN * numFans
    topHrail1 = hbarFeatures(WIDTH, OUTLETS_PER_SEGMENT).translate(
        (0, WALL_STRENGTH / 2, BOTTOM_HEIGHT)
    )

    result = split.bulge(combined, topHrail1)
    return result


def vBars():
    num = 5

    result = list()

    for Y in split.vbar.spread(RESONATOR_WALL_OFFSET_Y, front.DEPTH, num):
        result.append((Y, -front.basePlate.BASE_PLATE_HEIGHT, BOTTOM_HEIGHT))
    return result
