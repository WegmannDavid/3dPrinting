from prelude import *
import external.sunkhead

_freeRad = 1.6
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
