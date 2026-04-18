from prelude import *
import split

Y_EXTENSION = NOZZLE * 2  # accessible
HEIGHT = NOZZLE * 5  # private
Y_OFFSET = NOZZLE * 4 + Y_EXTENSION


def hbar(width):
    return (
        cq.Workplane("YZ")
        .moveTo(0, 0)
        .lineTo(Y_EXTENSION, 0)
        .lineTo(Y_EXTENSION, -(HEIGHT - NOZZLE) / 2)
        .lineTo(Y_EXTENSION - NOZZLE, -HEIGHT + NOZZLE)
        .lineTo(0, -HEIGHT + NOZZLE)
        .close()
        .extrude(width - NOZZLE * 2)
        .translate((NOZZLE, 0, 0))
        .mirror("XZ", None, True)
    )


def hbarCutout(width):
    return (
        cq.Workplane("YZ")
        .moveTo(0, 0)
        .lineTo(Y_EXTENSION + EPSILON, 0)
        .lineTo(Y_EXTENSION + EPSILON, -HEIGHT)
        .lineTo(0, -HEIGHT)
        .close()
        .extrude(width)
        .mirror("XZ", None, True)
    )


def hbarFeature(width):
    cutout = hbarCutout(width).translate((0, 0, EPSILON))
    bar = hbar(width).translate((0, 0, -EPSILON))
    gap = cutout.cut(bar)
    return gap
