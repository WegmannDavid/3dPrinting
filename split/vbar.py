from front.basePlate import BASE_PLATE_EXTENSION
from prelude import *
import split

WIDTH = NOZZLE * 5  # accessible
_SIDES = NOZZLE * 4  # private
_STRENGTH = NOZZLE * 2  # private
Y_OFFSET = NOZZLE * 8
X_REQUIRED = WIDTH + NOZZLE * 3


def _shape1(height, width, depth):
    return (
        cq.Workplane("XZ")
        .moveTo(0, 0)
        .lineTo(0, height)
        .lineTo(width, height)
        .lineTo(width, width)
        .close()
        .extrude(depth)
    )


def vbar(height, contactArea):
    freeArea = height - WIDTH - _SIDES

    middle = _shape1(height - LAYER * 3, WIDTH, _STRENGTH / 2)
    middle = middle.translate((0, 0, LAYER * 3))

    side = _shape1(height - WIDTH - LAYER * 3, _SIDES, _STRENGTH - EPSILON * 4)
    side = side.rotate((0, 0, 0), (0, 0, _STRENGTH / 2), -90)
    side = side.translate((WIDTH, -_STRENGTH / 2, WIDTH + LAYER * 3))

    contact1 = _shape1(contactArea, NOZZLE, _STRENGTH)
    contact1 = contact1.rotate((0, 0, 0), (0, 0, _STRENGTH / 2), 180)
    contact1 = contact1.translate(
        (WIDTH - _STRENGTH + EPSILON * 4, _SIDES - _STRENGTH / 2, height - contactArea)
    )

    contact2 = _shape1(contactArea, NOZZLE, WIDTH)
    contact2 = contact2.rotate((0, 0, 0), (0, 0, _STRENGTH / 2), 90)
    contact2 = contact2.translate((0, NOZZLE, height - contactArea))
    half = middle.union(side).union(contact1).union(contact2)
    whole = half.union(half.mirror("XZ"))
    return whole


def vbarCutout(height, contactArea):
    freeArea = height - WIDTH - _SIDES

    middle = _shape1(height - LAYER * 2, WIDTH + NOZZLE, _STRENGTH / 2 + EPSILON)
    middle = middle.translate((0, 0, LAYER * 2))

    side = _shape1(height - WIDTH - LAYER * 2, _SIDES + NOZZLE, _STRENGTH + NOZZLE)
    side = side.rotate((0, 0, 0), (0, 0, _STRENGTH / 2), -90)
    side = side.translate((WIDTH + NOZZLE, -_STRENGTH / 2, WIDTH + LAYER * 2))

    side2 = _shape1(height - WIDTH - LAYER * 2, NOZZLE * 2, NOZZLE)
    side2 = side2.rotate((0, 0, 0), (0, 0, _STRENGTH / 2), -90)
    side2 = side2.translate((NOZZLE * 3, -_STRENGTH / 2, WIDTH + LAYER * 2))

    contact1 = _shape1(height - WIDTH - _SIDES - contactArea, NOZZLE, _SIDES + NOZZLE)
    contact1 = contact1.rotate((0, 0, 0), (0, 0, _STRENGTH / 2), 180)
    contact1 = contact1.translate(
        (WIDTH - _STRENGTH, _STRENGTH / 2, WIDTH + _SIDES + contactArea)
    )

    contact2 = _shape1(height - contactArea, NOZZLE + EPSILON, WIDTH + NOZZLE)
    contact2 = contact2.rotate((0, 0, 0), (0, 0, _STRENGTH / 2), 90)
    contact2 = contact2.translate((0, NOZZLE, contactArea))

    half = middle.union(side).union(side2).union(contact1).union(contact2)
    whole = half.union(half.mirror("XZ"))
    return whole


import shapes


def feature(height, contactArea):
    cutout = vbarCutout(height, contactArea).translate((0, 0, 0))
    bar = vbar(height + EPSILON * 2, contactArea).translate((-EPSILON * 2, 0, 0))
    gap = cutout.cut(bar)
    return split.Feature(gap, bar)


def splitYZWithVBars(Y1, Y2, Z1, Z2, vbarPositions, contactArea):
    plane = split.planeYZ(Y1, Y2, Z1, Z2)
    for Y, Z1, Z2 in vbarPositions:
        featureHeight = Z2 - Z1
        plane = split.addFeature(
            plane, feature(featureHeight, contactArea).translate((0, Y, Z1))
        )
    return plane


def spread(Y1, Y2, Z1, Z2, num, contactArea):
    offset = (Y2 - Y1) / num
    height = Z2 - Z1
    result = split.Feature(cq.Workplane("XY"), cq.Workplane("XY"))

    for i in range(0, num):
        result = result.union(
            feature(height, contactArea).translate((0, Y1 + offset * (i + 0.5), Z1))
        )

    return result
