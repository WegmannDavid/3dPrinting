from prelude import *


def bulge(splitter, feature):
    inter = splitter.intersect(feature)
    return splitter.union(feature).cut(inter)


def planeYZ(w):
    return (
        cq.Workplane("YZ")
        .rect(w * 3, w * 3)
        .extrude(2 * EPSILON)
        .translate((-EPSILON, 0, 0))
    )


def planeXY(w):
    return (
        cq.Workplane("XY")
        .rect(w * 3, w * 3)
        .extrude(2 * EPSILON)
        .translate((0, 0, -EPSILON))
    )
