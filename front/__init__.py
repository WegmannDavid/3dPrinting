import math

from prelude import *

import external.fan.Axial60x60x25mm

import loft
import shapes

import front.filter

WALL_STRENGTH = NOZZLE * 3

HEIGHT = 210
EXPANDER_HEIGHT = 120
INNER_EXPANDER_HEIGHT = EXPANDER_HEIGHT - WALL_STRENGTH

HEAD_HEIGHT = 90
INNER_HEIGHT_ABOVE_FILTER = HEAD_HEIGHT - WALL_STRENGTH

FILTER_HEIGHT = HEIGHT - HEAD_HEIGHT

BASEPLATE_HEIGHT = 10

DEPTH = 70
DEPTH_EXTENSION = 10
INNER_EXTENDED_DEPTH = DEPTH + DEPTH_EXTENSION - 2 * WALL_STRENGTH
INNER_DEPTH = DEPTH - 2 * WALL_STRENGTH


OUTLET_DUCT_DEPTH = 5
FOAM_DEPTH = 30
FILTER_DEPTH = 15
FILTER_DUCT_OFFSET = (
    WALL_STRENGTH + OUTLET_DUCT_DEPTH + WALL_STRENGTH + FOAM_DEPTH + WALL_STRENGTH
)
FILTER_DUCT_DEPTH = DEPTH - FILTER_DUCT_OFFSET - FILTER_DEPTH
FILTER_DUCT_RAD = 2
FILTER_OFFSET = DEPTH - FILTER_DEPTH

SQRT2 = math.sqrt(2)

LONG_OFFSET = external.fan.Axial60x60x25mm.CUTOUT_SIZE * (SQRT2 / 2)
SHORT_OFFSET = external.fan.Axial60x60x25mm.CUTOUT_LENGTH * (SQRT2 / 2)

TOP_HEIGHT = SHORT_OFFSET + WALL_STRENGTH


def duct(OUTLET_X1, OUTLET_X2, INLET_X1, INLET_X2):

    OUTLET_WIDTH = OUTLET_X2 - OUTLET_X1
    INLET_WIDTH = INLET_X2 - INLET_X1

    INLET_MIDDLE_X = INLET_X1 + INLET_WIDTH / 2
    INLET_REFERENCE_POINT = (INLET_MIDDLE_X, INNER_EXTENDED_DEPTH, 0)

    def rectBeforeBendPoints():
        Z = HEIGHT - HEAD_HEIGHT
        Y1 = FILTER_DUCT_OFFSET
        Y2 = Y1 + FILTER_DUCT_DEPTH - FILTER_DUCT_RAD
        return [
            (INLET_X2, Y1, Z - front.filter.RIM),
            (INLET_X1, Y1, Z - front.filter.RIM),
            (INLET_X1, Y2, Z - front.filter.RIM + FILTER_DUCT_RAD * 2),
            (INLET_X2, Y2, Z - front.filter.RIM + FILTER_DUCT_RAD * 2),
        ]

    def head():
        HEAD_OFFSET = (0, WALL_STRENGTH, HEIGHT - WALL_STRENGTH)

        COMBINED_OFFSET = LONG_OFFSET + SHORT_OFFSET

        OUTLET_MIDDLE_X = OUTLET_X1 + OUTLET_WIDTH / 2

        FAN_MIDDLE_X = (OUTLET_MIDDLE_X + INLET_MIDDLE_X) / 2

        FAN_OFFSET_X = FAN_MIDDLE_X - external.fan.Axial60x60x25mm.CUTOUT_SIZE / 2

        fanSet = (
            external.fan.Axial60x60x25mm.set()
            .rotate(axisStartPoint=(0, 0, 0), axisEndPoint=(1, 0, 0), angleDegrees=-45)
            .translate((FAN_OFFSET_X, 0, -SHORT_OFFSET))
        )

        OUTLET_REFERENCE_POINT = (OUTLET_MIDDLE_X, 0, 0)
        REFERENCE_POINT_FAN = (FAN_MIDDLE_X, 0, 0)

        EXPANDER_Y = -INNER_EXPANDER_HEIGHT

        def rectAfterFan():
            return loft.polygon_endpoint(
                [
                    (OUTLET_X2, 0, EXPANDER_Y),
                    (OUTLET_X1, 0, EXPANDER_Y),
                    (OUTLET_X1, OUTLET_DUCT_DEPTH, EXPANDER_Y),
                    (OUTLET_X2, OUTLET_DUCT_DEPTH, EXPANDER_Y),
                ],
                [
                    (0, 0, EXPANDER_Y / 2),
                    (0, 0, EXPANDER_Y / 2),
                    (0, 0, EXPANDER_Y / 6),
                    (0, 0, EXPANDER_Y / 6),
                ],
                OUTLET_REFERENCE_POINT,
            )

        def rectBeforeFan():
            D = (
                external.fan.Axial60x60x25mm.CUTOUT_SIZE
                - external.fan.Axial60x60x25mm.CUTOUT_DUCT_INSET
            )
            Y = COMBINED_OFFSET
            Z = -D * (SQRT2 / 2)

            return loft.polygon_endpoint(
                [
                    (INLET_X2, Y, Z),
                    (INLET_X1, Y, Z),
                    (INLET_X1, Y, 0),
                    (INLET_X2, Y, 0),
                ],
                [
                    (0, 1, -1),
                    (0, 1, -1),
                    (0, INNER_EXTENDED_DEPTH - Y, 0),
                    (0, INNER_EXTENDED_DEPTH - Y, 0),
                ],
                INLET_REFERENCE_POINT,
            )

        def rectBeforeEllbowPoints():
            Z = -LONG_OFFSET
            Y1 = COMBINED_OFFSET + WALL_STRENGTH
            Y2 = INNER_EXTENDED_DEPTH
            return [
                (INLET_X2, Y1, Z),
                (INLET_X1, Y1, Z),
                (INLET_X1, Y2, Z),
                (INLET_X2, Y2, Z),
            ]

        def rectBeforeEllbow1():
            Z = -LONG_OFFSET
            return loft.polygon_endpoint(
                rectBeforeEllbowPoints(),
                [
                    (0, 0, -1),
                    (0, 0, -1),
                    (0, 0, Z / 2),
                    (0, 0, Z / 2),
                ],
                INLET_REFERENCE_POINT,
            )

        def rectBeforeEllbow2():
            return loft.polygon_endpoint(
                rectBeforeEllbowPoints(),
                [
                    (0, 0, -SHORT_OFFSET / 3),
                    (0, 0, -SHORT_OFFSET / 3),
                    (0, 0, -SHORT_OFFSET / 2),
                    (0, 0, -SHORT_OFFSET / 2),
                ],
                INLET_REFERENCE_POINT,
            )

        def rectBeforeBend():
            return loft.polygon_endpoint(
                translate_points(rectBeforeBendPoints(), negative_point(HEAD_OFFSET)),
                [
                    (0, 0, -SHORT_OFFSET / 2 - front.front.filter.RIM),
                    (0, 0, -SHORT_OFFSET / 2 - front.front.filter.RIM),
                    (0, 0, -SHORT_OFFSET),
                    (0, 0, -SHORT_OFFSET),
                ],
                INLET_REFERENCE_POINT,
            )

        reducer = loft.closed_bezier_loft(
            loft.circular_port_to_endpoint(
                fanSet.bottomPort,
                start_reference=REFERENCE_POINT_FAN,
                tangent_length=external.fan.Axial60x60x25mm.CUTOUT_DUCT_INSET
                * (SQRT2 / 2),
            ),
            rectAfterFan(),
        )

        expander = loft.closed_bezier_loft(
            loft.circular_port_to_endpoint(
                fanSet.topPort,
                start_reference=REFERENCE_POINT_FAN,
                tangent_length=external.fan.Axial60x60x25mm.CUTOUT_DUCT_INSET
                * (SQRT2 / 2)
                / 2,
            ),
            rectBeforeFan(),
        )

        ellbow = loft.closed_bezier_loft(rectBeforeFan(), rectBeforeEllbow1())

        bend = loft.closed_bezier_loft(rectBeforeEllbow2(), rectBeforeBend())

        fanCutout = fanSet.cutout

        return translate_all((bend, ellbow, expander, fanCutout, reducer), HEAD_OFFSET)

    bend, ellbow, expander, fanCutout, reducer = head()

    outletDuct = shapes.box(
        OUTLET_WIDTH, OUTLET_DUCT_DEPTH, BASEPLATE_HEIGHT + HEIGHT - EXPANDER_HEIGHT
    ).translate((OUTLET_X1, WALL_STRENGTH, -BASEPLATE_HEIGHT))

    FILTER_RECT_HEIGHT = FILTER_HEIGHT - front.filter.RIM * 2

    def rectBeforeBend():
        return loft.polygon_endpoint(
            rectBeforeBendPoints(),
            [
                (0, 0, -FILTER_RECT_HEIGHT),
                (0, 0, -FILTER_RECT_HEIGHT),
                (0, 0, -FILTER_DUCT_RAD),
                (0, 0, -FILTER_DUCT_RAD),
            ],
            (0, 0, 0),
        )

    def filterRect():
        Z1 = front.filter.RIM
        Z2 = FILTER_HEIGHT - front.filter.RIM
        return loft.polygon_endpoint(
            [
                (INLET_X2, FILTER_OFFSET, Z1),
                (INLET_X1, FILTER_OFFSET, Z1),
                (INLET_X1, FILTER_OFFSET, Z2),
                (INLET_X2, FILTER_OFFSET, Z2),
            ],
            [
                (0, FILTER_DUCT_DEPTH / 2, 0),
                (0, FILTER_DUCT_DEPTH / 2, 0),
                (0, FILTER_DUCT_RAD / 2, 0),
                (0, FILTER_DUCT_RAD / 2, 0),
            ],
            (0, 0, 0),
        )

    filterDuct = loft.closed_bezier_loft(rectBeforeBend(), filterRect())

    foam = shapes.box(INLET_WIDTH, FOAM_DEPTH, 90).translate(
        (INLET_X1, WALL_STRENGTH * 2 + OUTLET_DUCT_DEPTH, 0)
    )

    return (
        bend.union(ellbow)
        .union(expander)
        .union(fanCutout)
        .union(reducer)
        .union(outletDuct)
        .union(filterDuct)
    )


import external.m3
import split
import export


def test():
    d = duct(5, 75, 5, 75)
    volume = (
        cq.Workplane("YZ")
        .moveTo(0, 0)
        .lineTo(0, HEIGHT)
        .lineTo(DEPTH + DEPTH_EXTENSION, HEIGHT)
        .lineTo(DEPTH + DEPTH_EXTENSION, FILTER_HEIGHT + FILTER_DEPTH + DEPTH_EXTENSION)
        .lineTo(DEPTH - FILTER_DEPTH, FILTER_HEIGHT - front.filter.RIM)
        .lineTo(DEPTH - FILTER_DEPTH, 0)
        .close()
        .extrude(80)
    )

    screwCutout = external.m3.m3(50, TOP_HEIGHT).translate((0, 0, HEIGHT))

    s1 = screwCutout.translate((external.m3.TOP_OFFSET, external.m3.TOP_OFFSET, 0))
    s2 = screwCutout.translate((80 - external.m3.TOP_OFFSET, external.m3.TOP_OFFSET, 0))
    s3 = screwCutout.translate(
        (external.m3.TOP_OFFSET, (DEPTH + DEPTH_EXTENSION) * 3 / 4, 0)
    )
    s4 = screwCutout.translate(
        (
            80 - external.m3.TOP_OFFSET,
            (DEPTH + DEPTH_EXTENSION) * 3 / 4,
            0,
        )
    )

    splitPlane = split.planeXY(80).translate((0, 0, HEIGHT - TOP_HEIGHT))

    splitter = splitPlane.union(s1).union(s2).union(s3).union(s4)

    splitted = volume.cut(d).cut(splitter)

    parts = splitted.solids().vals()
    parts = sorted(parts, key=lambda s: (s.Center().x, s.Center().y, s.Center().z))

    export.stl(parts[0], "tests/part1.stl")
    export.stl(parts[1], "tests/part2.stl")

    return parts
