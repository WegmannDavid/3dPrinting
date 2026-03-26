from prelude import *

_freeRad = 1.75
_HeadRad = 3.2
_HeadFlatHeight = 0.8
_rad = 1.2


def m3(height, freeHeight):
    headEndHeight = _HeadRad - _freeRad + _HeadFlatHeight
    profile = (
        cq.Workplane("YZ")
        .moveTo(0, 0)
        .lineTo(_HeadRad, 0)
        .lineTo(_HeadRad, -_HeadFlatHeight)
        .lineTo(_freeRad, -headEndHeight)
        .lineTo(_freeRad, -freeHeight)
        .lineTo(_rad, -freeHeight)
        .lineTo(_rad, -height)
        .lineTo(0, -height)
        .close()
    )
    return profile.revolve(360, (0, 0, 0), (0, 1, 0))


OFFSET = 3.2 + NOZZLE * 2
