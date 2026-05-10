from prelude import *


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


def _vpin(height, width, depth):
    return _shape1(height, width, depth)


def _vpinCutout(height, width, depth):
    return _shape1(
        height + EPSILON * 3, width + 3 * EPSILON, depth + EPSILON * 2
    ).translate((0, EPSILON, -EPSILON * 3))


def vpinFeature(width, depth, height):
    cutout = _vpinCutout(height, width, depth).translate((-EPSILON, 0, 0))
    bar = _vpin(height, width, depth).translate((EPSILON, 0, 0))
    gap = cutout.cut(bar)
    return gap.translate((-EPSILON, 0, 0))
