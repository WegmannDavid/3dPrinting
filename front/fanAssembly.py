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

_CABLE_DIAMETER = 1.2
_NUM_CABLES = 8
_CABLE_CUTOUT_HEIGHT = 1.6
_CABLE_CUTOUT_DEPTH_PADDING = _FOAM_WIDTH
_CABLE_CUTOUT_WIDTH = _CABLE_DIAMETER * 8 * 3 + 2


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


def cableCutout():
    depth = _FOAM_WIDTH * 2 + _CABLE_DIAMETER
    result = shapes.box(_CABLE_DIAMETER, depth, depth, centered=True)
    return result


def cableCutouts():
    result = cq.Workplane("XY")
    offset = _CABLE_DIAMETER * 3
    for i in range(8):
        result = result.union(
            cableCutout().translate(
                (
                    i * offset,
                    0,
                    0,
                )
            )
        )
    return result


def fanAssembly(depth):
    _cableCutout = cableCutouts().translate(
        (
            _DUCT_OFFSETX - _CABLE_CUTOUT_WIDTH,
            depth,
            FANASSEMBLY_HEIGHT - _WALL_THICKNESS,
        )
    )

    box1 = shapes.openBox(
        FANASSEMBLY_WIDTH, 1, 1, depth, 1, 0, FANASSEMBLY_HEIGHT, 1, 1, _WALL_THICKNESS
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

    box1 = box1.cut(ductCut1).cut(ductCut2).cut(_cableCutout)

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


def pinCutout(x, negative_depth, h1, h2):
    width = 10
    height = h2 + width / 2
    depth = negative_depth - NOZZLE * 2
    shaft = shapes.box(width, depth, height).translate((0, NOZZLE * 2, -height))
    pin1 = shapes.box(width, negative_depth, width).translate((0, 0, -h1 - width / 2))
    pin2 = shapes.box(width, negative_depth, width).translate((0, 0, -h2 - width / 2))
    return shaft.union(pin1).union(pin2).translate((x - width / 2, -negative_depth, 0))


def fanAssemblyCutout(positive_Depth, negative_Depth):

    main = shapes.box(
        FANASSEMBLY_CUTOUT_WIDTH,
        positive_Depth,
        FANASSEMBLY_CUTOUT_HEIGHT,
    ).translate((0, 0, _FOAM_THICKNESS + _WALL_THICKNESS - FANASSEMBLY_CUTOUT_HEIGHT))

    pinholeOffsetX = _FOAM_THICKNESS + _FAN_OFFSET + 7.5

    p1_y = _FOAM_THICKNESS + 7.5
    p2_y = _FOAM_THICKNESS + _FAN_SIZE - 7.5
    p3_y = FANASSEMBLY_HEIGHT - _WALL_THICKNESS - _FAN_OFFSET - _FAN_SIZE + 7.5
    p4_y = FANASSEMBLY_HEIGHT - _WALL_THICKNESS - _FAN_OFFSET - 7.5

    p1 = pinCutout(pinholeOffsetX, negative_Depth, p1_y, p2_y)
    p2 = pinCutout(pinholeOffsetX + 105, negative_Depth, p2_y, p2_y)
    p3 = pinCutout(
        FANASSEMBLY_CUTOUT_WIDTH - pinholeOffsetX - 105, negative_Depth, p3_y, p4_y
    )
    p4 = pinCutout(
        FANASSEMBLY_CUTOUT_WIDTH - pinholeOffsetX, negative_Depth, p4_y, p4_y
    )

    cableCutout1 = shapes.box(
        _CABLE_CUTOUT_WIDTH,
        positive_Depth - _FOAM_WIDTH * 2,
        _CABLE_CUTOUT_HEIGHT + _FOAM_THICKNESS + _WALL_THICKNESS,
    ).translate(
        (
            _DUCT_OFFSETX - _CABLE_CUTOUT_WIDTH - _CABLE_DIAMETER,
            _FOAM_WIDTH,
            0,
        )
    )
    cableCutout2 = shapes.box(
        20,
        10,
        30,
        centered=True,
    ).translate(
        (
            _DUCT_OFFSETX - _CABLE_CUTOUT_WIDTH / 2 - _CABLE_DIAMETER,
            _FOAM_WIDTH + (positive_Depth - _FOAM_WIDTH * 2) / 2,
            0,
        )
    )
    return (
        main.union(p1)
        .union(p2)
        .union(p3)
        .union(p4)
        .union(cableCutout1)
        .union(cableCutout2)
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


def set(positive_depth, negative_depth):
    fa_depth = positive_depth - 2 * _FOAM_THICKNESS
    fa, fa_cover = translate_all(
        fanAssembly(fa_depth),
        (
            _FOAM_THICKNESS,
            _FOAM_THICKNESS,
            -FANASSEMBLY_HEIGHT + _WALL_THICKNESS,
        ),
    )
    fac = fanAssemblyCutout(positive_depth, negative_depth)

    port = duct.solid.RectPort(
        width=_FAN_OUTLET_DEPTH,
        height=_COMBINED_OUTLET_HEIGHT,
        x=FANASSEMBLY_CUTOUT_WIDTH,
        y=_FAN_OUTLET_DEPTH_OFFSET + _FOAM_THICKNESS,
        z=-_COMBINED_OUTLET_HEIGHT,
    )

    return FanAssemblySet(fanAssembly=fa, port=port, cover=fa_cover, cutout=fac)
