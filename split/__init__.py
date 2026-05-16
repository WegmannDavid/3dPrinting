from prelude import *

# def bulge(splitter, feature):
#    inter = splitter.intersect(feature)
#    return splitter.union(feature).cut(inter)


class Feature:
    feature: cq.Workplane
    join: cq.Workplane

    def __init__(self, feature, join):
        self.feature = feature
        self.join = join

    def translate(self, t):
        return Feature(self.feature.translate(t), self.join.translate(t))

    def rotate(self, axisStart, axisEnd, angle):
        return Feature(
            self.feature.rotate(axisStart, axisEnd, angle),
            self.join.rotate(axisStart, axisEnd, angle),
        )

    def mirror(self, plane):
        return Feature(self.feature.mirror(plane), self.join.mirror(plane))


def addFeature(splitter, feature: Feature):
    u = splitter.union(feature.feature)
    return u.cut(feature.join)


def planeYZ(Y1, Y2, Z1, Z2, THICKNESS=2 * EPSILON):
    depth = Y2 - Y1
    height = Z2 - Z1
    return (
        cq.Workplane("YZ")
        .rect(depth, height, centered=False)
        .extrude(THICKNESS)
        .translate((-THICKNESS / 2, Y1, Z1))
    )


def planeXY(X1, X2, Y1, Y2):
    width = X2 - X1
    depth = Y2 - Y1
    return shapes.box(width, depth, 2 * EPSILON).translate((X1, Y1, -EPSILON))


def shell(solid: cq.Workplane) -> cq.Workplane:
    """
    Thin shell hugging the original surface, with sharp corners preserved.
    """
    outward = solid.shell(EPSILON / 2, kind="intersection")
    inward = solid.shell(-EPSILON / 2, kind="intersection")
    return outward.union(inward)
