from inkex import dataclass

from prelude import *
from external.fan import fan

import shapes

import duct.solid

_FAN_SIZE = 120
_FOAM_THICKNESS = 1.6
_BOTTOM_FOAM_EXTRA_THICKNESS = 10
_FOAM_WIDTH = 6
_WALL_THICKNESS = NOZZLE * 4
_FAN_OUTLET_ZOFFSET = 61
_FAN_OFFSET = _WALL_THICKNESS + _FOAM_THICKNESS
_FAN_OUTLET_DEPTH_OFFSET = _WALL_THICKNESS + 4
_FAN_OUTLET_DEPTH = 29
_FAN_OUTLET_HEIGHT = 57
# wall foam fan foam fan foam wall
FANASSEMBLY_WIDTH = _FAN_OFFSET + _FAN_SIZE + _FOAM_THICKNESS + _FAN_SIZE + _FAN_OFFSET
# wall foam fan foam foamWidth singlefanOutlet foam wall
FANASSEMBLY_HEIGHT = (
    _FAN_OFFSET
    + _FAN_SIZE
    + _FOAM_THICKNESS
    + _FOAM_WIDTH
    + (_FAN_SIZE - _FAN_OUTLET_ZOFFSET)
    + _FAN_OFFSET
)

_COMBINED_OUTLET_HEIGHT = (
    FANASSEMBLY_HEIGHT - _FAN_OFFSET - _FAN_OUTLET_ZOFFSET - _WALL_THICKNESS
)

FANASSEMBLY_CUTOUT_WIDTH = FANASSEMBLY_WIDTH + 2 * _FOAM_THICKNESS
FANASSEMBLY_CUTOUT_HEIGHT = (
    FANASSEMBLY_HEIGHT + 2 * _FOAM_THICKNESS + _BOTTOM_FOAM_EXTRA_THICKNESS
)

_DUCT_OFFSETX = _FAN_OFFSET + _FAN_SIZE + _FOAM_THICKNESS
_DUCT_OFFSETZ = _FAN_OFFSET + _FAN_SIZE + _FOAM_THICKNESS
_DUCT_LENGTH = FANASSEMBLY_WIDTH - _DUCT_OFFSETX
_DUCT_HEIGHT = FANASSEMBLY_HEIGHT - _DUCT_OFFSETZ


def duct1Cutout(depth):
    deeper = duct.solid.bezierDuctProfile(
        portDim="Z",
        lengthDim="X",
        s1=_FOAM_WIDTH,
        e1=_FOAM_WIDTH + _FAN_OUTLET_HEIGHT,
        s2=_WALL_THICKNESS,
        e2=_DUCT_HEIGHT - _WALL_THICKNESS,
        length=_DUCT_LENGTH - _WALL_THICKNESS,
        depth=depth,
    )
    end = cq.Workplane("XY").box(
        _WALL_THICKNESS,
        _FAN_OUTLET_DEPTH,
        _DUCT_HEIGHT - _WALL_THICKNESS * 2,
        centered=False,
    )
    end = end.translate((_DUCT_LENGTH - _WALL_THICKNESS, 0, _WALL_THICKNESS))
    return deeper.union(end)


def fanAssembly(depth):
    box1 = shapes.openBox(
        FANASSEMBLY_WIDTH, 1, 1, FANASSEMBLY_HEIGHT, 1, 1, depth, 1, 0, _WALL_THICKNESS
    )

    ductBox = cq.Workplane("XY").box(
        _DUCT_LENGTH,
        _FAN_OUTLET_DEPTH_OFFSET + _FAN_OUTLET_DEPTH + _FOAM_WIDTH / 2,
        _DUCT_HEIGHT,
        centered=False,
    )
    ductBox = ductBox.translate((_DUCT_OFFSETX, 0, _DUCT_OFFSETZ))

    box1 = box1.union(ductBox)

    ductCut1 = duct1Cutout(_FAN_OUTLET_DEPTH + _FOAM_WIDTH / 2).translate(
        (_DUCT_OFFSETX, _FAN_OUTLET_DEPTH_OFFSET, _DUCT_OFFSETZ)
    )

    ductCut2 = cq.Workplane("XY").box(
        _WALL_THICKNESS, _FAN_OUTLET_DEPTH, _FAN_OUTLET_HEIGHT, centered=False
    )
    ductCut2 = ductCut2.translate(
        (
            FANASSEMBLY_WIDTH - _WALL_THICKNESS,
            _FAN_OUTLET_DEPTH_OFFSET,
            _FAN_OFFSET + _FAN_OUTLET_ZOFFSET,
        )
    )

    box1 = box1.cut(ductCut1).cut(ductCut2)

    ductBoxCover = cq.Workplane("XY").box(
        _DUCT_LENGTH - _WALL_THICKNESS, _FOAM_WIDTH, _DUCT_HEIGHT, centered=False
    )
    ductBoxCover = ductBoxCover.translate(
        (_DUCT_OFFSETX, _FAN_OUTLET_DEPTH_OFFSET + _FAN_OUTLET_DEPTH, _DUCT_OFFSETZ)
    )
    ductBoxCover = ductBoxCover.cut(box1)

    fan1 = fan.translate(
        (_FAN_OFFSET, _WALL_THICKNESS, FANASSEMBLY_HEIGHT - _FAN_SIZE - _FAN_OFFSET)
    )
    fan2 = fan.translate(
        (_FAN_SIZE + _FOAM_THICKNESS + _FAN_OFFSET, _WALL_THICKNESS, _FAN_OFFSET)
    )

    box1 = box1.cut(fan1).cut(fan2)
    return box1, ductBoxCover


def fanAssemblyCutout(positive_Depth):
    return (
        cq.Workplane("XY")
        .box(
            FANASSEMBLY_CUTOUT_WIDTH,
            positive_Depth,
            FANASSEMBLY_CUTOUT_HEIGHT,
            centered=False,
        )
        .translate(
            (0, 0, _FOAM_THICKNESS + _WALL_THICKNESS - FANASSEMBLY_CUTOUT_HEIGHT)
        )
    )


@dataclass
class FanAssemblySet:
    fanAssembly: cq.Workplane
    port: duct.solid.RectPort
    cover: cq.Workplane
    cutout: cq.Workplane

    def translate(self, d):
        return FanAssemblySet(
            fanAssembly=self.fanAssembly.translate(d),
            port=self.port.translate(d),
            cover=self.cover.translate(d),
            cutout=self.cutout.translate(d),
        )


def set(depth):
    fa_depth = depth - 2 * _FOAM_THICKNESS
    fa, fa_cover = translate_all(
        fanAssembly(fa_depth),
        (
            _FOAM_THICKNESS,
            _FOAM_THICKNESS,
            -FANASSEMBLY_HEIGHT + _WALL_THICKNESS,
        ),
    )
    fac = fanAssemblyCutout(depth)

    port = duct.solid.RectPort(
        width=_FAN_OUTLET_DEPTH,
        height=_COMBINED_OUTLET_HEIGHT,
        x=FANASSEMBLY_CUTOUT_WIDTH,
        y=_FAN_OUTLET_DEPTH_OFFSET + _FOAM_THICKNESS,
        z=-_COMBINED_OUTLET_HEIGHT,
    )

    return FanAssemblySet(fanAssembly=fa, port=port, cover=fa_cover, cutout=fac)
