from unittest import result

from prelude import *
from dataclasses import dataclass

import duct.vane
import shapes

import front

SIZE = front.CAVITY_HEIGHT
DEPTH = front.DUCT_DEPTH
NUMVANES = 20

SUPPORT_THICKNESS = NOZZLE * 2
VANE_SIZE = duct.vane.vaneSize(SIZE, NUMVANES)

GAP_FOAM_THICKNESS = 1.5
FOAMDEPTH = 10


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


def make_elbow_set(width):
    def vanes():
        v = duct.vane.vanes(SIZE, DEPTH, NUMVANES)
        support = (
            cq.Workplane("XZ")
            .moveTo(-VANE_SIZE, -VANE_SIZE)
            .lineTo(-VANE_SIZE, VANE_SIZE)
            .lineTo(SIZE - VANE_SIZE * 2, SIZE)
            .lineTo(SIZE, SIZE)
            .lineTo(SIZE, SIZE - VANE_SIZE * 2)
            .lineTo(VANE_SIZE, -VANE_SIZE)
            .close()
            .extrude(SUPPORT_THICKNESS)
        )
        result = v.union(support)
        return result

    def cutout():
        return shapes.box(
            width,
            front.DUCT_DEPTH + 2 * FOAMDEPTH,
            SIZE + 2 * GAP_FOAM_THICKNESS + VANE_SIZE,
        ).translate((0, 0, -GAP_FOAM_THICKNESS - VANE_SIZE))

    def foam():
        c = cutout()
        ductIn = shapes.box(
            width - FOAMDEPTH, front.DUCT_DEPTH, SIZE + 2 * GAP_FOAM_THICKNESS
        ).translate((0, FOAMDEPTH, 0))
        ductOut = shapes.box(
            SIZE + VANE_SIZE, front.DUCT_DEPTH, VANE_SIZE + GAP_FOAM_THICKNESS
        ).translate(
            (
                width - SIZE - FOAMDEPTH - VANE_SIZE,
                FOAMDEPTH,
                -GAP_FOAM_THICKNESS - VANE_SIZE,
            )
        )
        return c.cut(ductIn).cut(ductOut)

    def port():
        return duct.solid.RectPort(
            width=front.DUCT_DEPTH,
            height=SIZE,
            x=0,
            y=FOAMDEPTH,
            z=0,
        )

    outletCutout = shapes.box(SIZE, front.DUCT_DEPTH, SIZE).translate(
        (
            width - FOAMDEPTH - SIZE,
            FOAMDEPTH,
            -SIZE,
        )
    )

    v = vanes().translate((width - FOAMDEPTH - SIZE, FOAMDEPTH, 0))
    c = cutout().union(outletCutout)
    f = foam()
    p = port()

    return ElbowSet(v, c, f, p)
