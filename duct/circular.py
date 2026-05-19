import math

from prelude import *

import loft


def inner(r, depth):
    c1 = loft.circle_curve((0, 0, 0), (0, 1, 0), r)
    t1 = loft.circle_curve((0, depth / 2, 0), (0, 1, 0), r)
    c2 = loft.circle_curve((0, depth, 0), (0, 1, 0), r - depth)
    t2 = loft.circle_curve((0, depth, 0), (0, 1, 0), r - depth / 2)

    e1 = loft.BezierEndpoint(c1, t1)
    e2 = loft.BezierEndpoint(c2, t2)
    return loft.closed_bezier_loft(e1, e2)


def outer(r, depth):
    c1 = loft.circle_curve((0, 0, 0), (0, 1, 0), r)
    t1 = loft.circle_curve((0, depth / 2, 0), (0, 1, 0), r)
    c2 = loft.circle_curve((0, depth, 0), (0, 1, 0), r + depth)
    t2 = loft.circle_curve((0, depth, 0), (0, 1, 0), r + depth / 2)

    e1 = loft.BezierEndpoint(c1, t1)
    e2 = loft.BezierEndpoint(c2, t2)
    return loft.closed_bezier_loft(e1, e2)


def circularDuct(r1, r2, depth):
    o = outer(r2, depth)
    i = inner(r1, depth)
    duct = o.cut(i)
    return duct


def struts(r, depth, strength):
    import shapes

    s = shapes.box(r * 4, depth / 2, strength, centered=True).translate(
        (0, depth / 4, 0)
    )
    s1 = s.rotate((0, 0, 0), (0, 1, 0), 0)
    s2 = s.rotate((0, 0, 0), (0, 1, 0), 45)
    s3 = s.rotate((0, 0, 0), (0, 1, 0), 90)
    s4 = s.rotate((0, 0, 0), (0, 1, 0), 135)

    return s1.union(s2).union(s3).union(s4)


def bellmouthWithStruts(r1, r2, depth):
    c = bellmouthAlongY(r1, r2, depth)
    s = struts(r2, depth, NOZZLE * 3)
    return c.cut(s)


def bellmouthWithStrutsByArea(r2, a, depth):
    r1 = math.sqrt(r2**2 - a / math.pi)
    return bellmouthWithStruts(r1, r2, depth)


def test(r2, a, depth, offset):
    import shapes

    b = shapes.box(
        r2 * 2 + depth * 3, offset + depth, r2 * 2 + depth * 3, centered=True
    ).translate((0, -(offset + depth) / 2 + depth, 0))

    c = circularDuctWithStrutsByArea(r2, a, depth)

    c = c.union(shapes.cylinderAlongY(r2, offset).translate((0, -offset / 2, 0)))

    result = b.cut(c)

    import export

    export.step(result, "circularDuctTest.step")
