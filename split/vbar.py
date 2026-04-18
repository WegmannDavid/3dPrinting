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

    side = _shape1(height - WIDTH - LAYER * 3, _SIDES, _STRENGTH)
    side = side.rotate((0, 0, 0), (0, 0, _STRENGTH / 2), -90)
    side = side.translate((WIDTH, -_STRENGTH / 2, WIDTH + LAYER * 3))

    contact = _shape1(contactArea, NOZZLE, _STRENGTH)
    contact = contact.rotate((0, 0, 0), (0, 0, _STRENGTH / 2), 180)
    contact = contact.translate(
        (WIDTH - _STRENGTH, _SIDES - _STRENGTH / 2, height - contactArea)
    )

    half = middle.union(side).union(contact)
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

    contact = _shape1(height - WIDTH - _SIDES - contactArea, NOZZLE, _SIDES + NOZZLE)
    contact = contact.rotate((0, 0, 0), (0, 0, _STRENGTH / 2), 180)
    contact = contact.translate(
        (WIDTH - _STRENGTH, _STRENGTH / 2, WIDTH + _SIDES + contactArea)
    )

    half = middle.union(side).union(side2).union(contact)
    whole = half.union(half.mirror("XZ"))
    return whole


def vbarFeature(height, contactArea):
    cutout = vbarCutout(height, contactArea).translate((-EPSILON, 0, 0))
    bar = vbar(height, contactArea).translate((EPSILON, 0, 0))
    gap = cutout.cut(bar)
    return gap


def vbarDoubleFeature(height, z, contactArea):
    vbar1 = vbarFeature(z, contactArea)
    vbar2 = vbarFeature(height - z, contactArea).mirror("XY").translate((0, 0, height))
    return vbar1.union(vbar2)
