from prelude import *

def _pin():
    a = cq.Workplane("XY").box(7,20,3)
    b = cq.Workplane("XY").box(3,20,2).translate((0,0,-2.5))
    return a.union(b)

pin = _pin()

def _fan():
    wallThickness = 2
    outletDepth = 29
    outletHeight = 57
    base = cq.Workplane("XY").box(120, 2, 120, centered=False).translate((0, 2, 0))
    outlet = cq.Workplane("XY").box(20, outletDepth+2*wallThickness, outletHeight+wallThickness*2, centered=False)
    outlet = outlet.translate((100,2,120-outletHeight-wallThickness*2))
    outletCutout = cq.Workplane("XY").box(20, outletDepth, outletHeight, centered=False)
    outletCutout = outletCutout.translate((100,2+wallThickness,120-outletHeight-wallThickness))
    fan = base.union(outlet).cut(outletCutout)
    pin1 = pin.translate((7.5, 0, 7.5))
    pin2 = pin.translate((7.5, 0, 112.5))
    pin3 = pin.translate((112.5, 0, 7.5))
    return fan.union(pin1).union(pin2).union(pin3)

fan = _fan()