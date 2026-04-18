from unittest import result

from prelude import *
from dataclasses import dataclass

import duct.vane
import shapes

import front

SUPPORT_THICKNESS = NOZZLE * 2

GAP_FOAM_THICKNESS = 1.5


@dataclass
class ElbowSet:
    vanes: cq.Workplane
    cutout: cq.Workplane
    foam: cq.Workplane
    port: duct.solid.RectPort

    def translate(self, vec):
        return ElbowSet(
            vanes=self.vanes.translate(vec),
            cutout=self.cutout.translate(vec),
            foam=self.foam.translate(vec),
            port=self.port.translate(vec),
        )


def supportHexagon(size, innerSize, depth):
    support = (
        cq.Workplane("XZ")
        .moveTo(-innerSize, -innerSize)
        .lineTo(-innerSize, innerSize)
        .lineTo(size - innerSize * 2, size)
        .lineTo(size, size)
        .lineTo(size, size - innerSize * 2)
        .lineTo(innerSize, -innerSize)
        .close()
        .extrude(depth)
    )
    return support


def make_elbow_set(width, size, duct_depth, foam_depth, num_vanes):

    vane_size = duct.vane.vaneSize(size, num_vanes)

    def vanes():
        v = duct.vane.vanes(
            size, duct_depth + SUPPORT_THICKNESS * 2, num_vanes
        ).translate((0, -SUPPORT_THICKNESS, 0))
        support = supportHexagon(size, vane_size, SUPPORT_THICKNESS)
        supportCutout = supportHexagon(
            size, vane_size - SUPPORT_THICKNESS * 2, SUPPORT_THICKNESS
        )
        support = support.cut(supportCutout)
        result = v.union(support)
        return result

    def cutout():
        return shapes.box(
            width,
            duct_depth + 2 * foam_depth,
            size + 2 * GAP_FOAM_THICKNESS + vane_size,
        ).translate((0, 0, -GAP_FOAM_THICKNESS - vane_size))

    def foam():
        c = cutout()
        ductIn = shapes.box(width, duct_depth, size + 2 * GAP_FOAM_THICKNESS).translate(
            (0, foam_depth, 0)
        )
        ductOut = shapes.box(
            size + vane_size, duct_depth, vane_size + GAP_FOAM_THICKNESS
        ).translate(
            (
                width - size - vane_size,
                foam_depth,
                -GAP_FOAM_THICKNESS - vane_size,
            )
        )
        return c.cut(ductIn).cut(ductOut)

    def port():
        return duct.solid.RectPort(
            width=duct_depth,
            height=size,
            x=0,
            y=foam_depth,
            z=0,
        )

    outletCutout = shapes.box(size, duct_depth, size).translate(
        (
            width - size - GAP_FOAM_THICKNESS,
            foam_depth,
            -size - GAP_FOAM_THICKNESS,
        )
    )

    v = vanes().translate((width - size - GAP_FOAM_THICKNESS, foam_depth, 0))
    c = cutout().union(outletCutout)
    f = foam()
    p = port()

    return ElbowSet(v, c, f, p)
