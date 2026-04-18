from prelude import *
import shapes

FOAM_THICKNESS = 3.5
CASING_SIZE = 60
CASING_LENGTH = 25
CASING_DUCT_INSET = 1

CUTOUT_SIZE = CASING_SIZE + 2 * FOAM_THICKNESS
CUTOUT_LENGTH = CASING_LENGTH + 2 * FOAM_THICKNESS

CUTOUT_DUCT_INSET = CASING_DUCT_INSET + FOAM_THICKNESS


def cutoutWithFoam():
    cutout = shapes.box(CUTOUT_SIZE, CUTOUT_SIZE, CUTOUT_LENGTH)
    cableCutout = (
        shapes.box(CUTOUT_LENGTH / 2, CUTOUT_LENGTH, CUTOUT_LENGTH / 2)
        .translate((0, -CUTOUT_LENGTH / 2, 0))
        .rotate((0, 0, 0), (1, 0, 0), 45)
    )
    return cutout.union(cableCutout)


import port


class Axial60x60x25mmSet:
    cutout: cq.Workplane
    duct: cq.Workplane
    bottomPort: port.CircularPort
    topPort: port.CircularPort

    def __init__(self):
        self.cutout = cutoutWithFoam()
        self.duct = shapes.cylinder(
            CASING_SIZE / 2 - CASING_DUCT_INSET, CUTOUT_LENGTH
        ).translate((CUTOUT_SIZE / 2, CUTOUT_SIZE / 2, 0))
        self.bottomPort = port.CircularPort(
            center=(CUTOUT_SIZE / 2, CUTOUT_SIZE / 2, 0),
            normal=(0, 0, -1),
            radius=CASING_SIZE / 2 - CASING_DUCT_INSET,
        )
        self.topPort = port.CircularPort(
            center=(CUTOUT_SIZE / 2, CUTOUT_SIZE / 2, CUTOUT_LENGTH),
            normal=(0, 0, 1),
            radius=CASING_SIZE / 2 - CASING_DUCT_INSET,
        )

    def translate(self, offset: tuple[float, float, float]) -> "Axial60x60x25mmSet":
        """Return a copy of this set transformed by the given offset."""
        new_set = Axial60x60x25mmSet()
        new_set.cutout = self.cutout.translate(offset)
        new_set.duct = self.duct.translate(offset)
        new_set.bottomPort = self.bottomPort.transform(offset)
        new_set.topPort = self.topPort.transform(offset)
        return new_set

    def rotate(
        self,
        axisStartPoint: tuple[float, float, float],
        axisEndPoint: tuple[float, float, float],
        angleDegrees: float,
    ) -> "Axial60x60x25mmSet":
        """Return a copy of this set rotated around the given axis by the given angle."""
        new_set = Axial60x60x25mmSet()
        new_set.cutout = self.cutout.rotate(
            axisStartPoint=axisStartPoint,
            axisEndPoint=axisEndPoint,
            angleDegrees=angleDegrees,
        )
        new_set.duct = self.duct.rotate(
            axisStartPoint=axisStartPoint,
            axisEndPoint=axisEndPoint,
            angleDegrees=angleDegrees,
        )
        new_set.bottomPort = self.bottomPort.rotate(
            axisStartPoint=axisStartPoint,
            axisEndPoint=axisEndPoint,
            angleDegrees=angleDegrees,
        )
        new_set.topPort = self.topPort.rotate(
            axisStartPoint=axisStartPoint,
            axisEndPoint=axisEndPoint,
            angleDegrees=angleDegrees,
        )
        return new_set


def set():
    return Axial60x60x25mmSet()
