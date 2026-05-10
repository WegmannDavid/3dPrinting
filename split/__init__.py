from prelude import *


def bulge(splitter, feature):
    inter = splitter.intersect(feature)
    return splitter.union(feature).cut(inter)


def planeYZ(Y1, Y2, Z1, Z2):
    depth = Y2 - Y1
    height = Z2 - Z1
    return (
        cq.Workplane("YZ")
        .rect(depth, height, centered=False)
        .extrude(2 * EPSILON)
        .translate((-EPSILON, Y1, Z1))
    )


def planeXY(X1, X2, Y1, Y2):
    width = X2 - X1
    depth = Y2 - Y1
    return shapes.box(width, depth, 2 * EPSILON).translate((X1, Y1, -EPSILON))


import shapes


def sink(width, depth, height):
    s = shapes.openBox(width, 1, 1, depth, 1, 1, height, 1, 1, EPSILON * 2)
    return s.translate((0, 0, -height + EPSILON))
