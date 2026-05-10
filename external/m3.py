import front
from prelude import *
import external.sunkhead

_freeRad = 1.75
_HeadRad = 3.1
_HeadHeight = 0.4
_rad = 1.2


def m3(height, freeHeight):
    return external.sunkhead.sunkhead(
        _HeadRad, _HeadHeight, _freeRad, freeHeight, _rad, height
    )


FREE_OFFSET = _freeRad + NOZZLE * 2
TOP_OFFSET = _HeadRad + NOZZLE * 2
OFFSET = _rad + NOZZLE * 2


def cornerCutouts(height, freeHeight, width, depth):
    screwCutout = external.m3.m3(height, freeHeight)

    s1 = screwCutout.translate((external.m3.TOP_OFFSET, external.m3.TOP_OFFSET, 0))
    s2 = screwCutout.translate(
        (width - external.m3.TOP_OFFSET, external.m3.TOP_OFFSET, 0)
    )
    s3 = screwCutout.translate(
        (external.m3.TOP_OFFSET, depth - external.m3.TOP_OFFSET, 0)
    )
    s4 = screwCutout.translate(
        (
            width - external.m3.TOP_OFFSET,
            depth - external.m3.TOP_OFFSET,
            0,
        )
    )
    return s1.union(s2).union(s3).union(s4)
