import shapes

_depth = 2


def potentiometerCutout():
    cylinderCutout = shapes.cylinderAlongY(3.6, _depth)

    lockingPinCutout = shapes.box(1, _depth, 3).translate((-9.6, 0, 0))

    return cylinderCutout.union(lockingPinCutout)


def buttonCutout():
    return shapes.cylinderAlongY(6.1, _depth)
