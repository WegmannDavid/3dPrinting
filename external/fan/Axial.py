from prelude import *
import shapes


import port


class AxialParameters:
    CASING_SIZE: float
    CASING_LENGTH: float
    CASING_DUCT_INSET: float
    FOAM_THICKNESS: float

    def __init__(
        self, CASING_SIZE, CASING_LENGTH, CASING_DUCT_INSET, FOAM_THICKNESS=3.5
    ):
        self.CASING_SIZE = CASING_SIZE
        self.CASING_LENGTH = CASING_LENGTH
        self.CASING_DUCT_INSET = CASING_DUCT_INSET
        self.FOAM_THICKNESS = FOAM_THICKNESS

        self.CUTOUT_SIZE = self.CASING_SIZE + 2 * self.FOAM_THICKNESS
        self.CUTOUT_LENGTH = self.CASING_LENGTH + 2 * self.FOAM_THICKNESS
        self.CUTOUT_DUCT_INSET = self.CASING_DUCT_INSET + self.FOAM_THICKNESS


class AxialSet:
    PARAMETERS: AxialParameters
    cutout: cq.Workplane
    duct: cq.Workplane
    bottomPort: port.CircularPort
    topPort: port.CircularPort

    def translate(self, offset: tuple[float, float, float]) -> "AxialSet":
        """Return a copy of this set transformed by the given offset."""
        new_set = AxialSet()
        new_set.PARAMETERS = self.PARAMETERS
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
    ) -> "AxialSet":
        """Return a copy of this set rotated around the given axis by the given angle."""
        new_set = AxialSet()
        new_set.PARAMETERS = self.PARAMETERS
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


def fromParameters(parameters: AxialParameters) -> AxialSet:

    def cutoutWithFoam():
        cutout = shapes.box(
            parameters.CUTOUT_SIZE, parameters.CUTOUT_SIZE, parameters.CUTOUT_LENGTH
        )
        cableCutout = (
            shapes.box(
                parameters.CUTOUT_LENGTH / 2,
                parameters.CUTOUT_LENGTH,
                parameters.CUTOUT_LENGTH / 2,
            )
            .translate((parameters.FOAM_THICKNESS + 2, -parameters.CUTOUT_LENGTH, 0))
            .rotate((0, 0, 0), (1, 0, 0), -45)
        )
        return cutout.union(cableCutout)

    result = AxialSet()
    result.PARAMETERS = parameters
    result.cutout = cutoutWithFoam()
    result.duct = shapes.cylinderAlongZ(
        parameters.CASING_SIZE / 2 - parameters.CASING_DUCT_INSET,
        parameters.CUTOUT_LENGTH,
    ).translate((parameters.CUTOUT_SIZE / 2, parameters.CUTOUT_SIZE / 2, 0))
    result.bottomPort = port.CircularPort(
        center=(parameters.CUTOUT_SIZE / 2, parameters.CUTOUT_SIZE / 2, 0),
        normal=(0, 0, -1),
        radius=parameters.CASING_SIZE / 2 - parameters.CASING_DUCT_INSET,
    )
    result.topPort = port.CircularPort(
        center=(
            parameters.CUTOUT_SIZE / 2,
            parameters.CUTOUT_SIZE / 2,
            parameters.CUTOUT_LENGTH,
        ),
        normal=(0, 0, 1),
        radius=parameters.CASING_SIZE / 2 - parameters.CASING_DUCT_INSET,
    )
    return result


def axial60x60x25mm() -> AxialSet:
    return fromParameters(
        AxialParameters(
            CASING_SIZE=60,
            CASING_LENGTH=25,
            CASING_DUCT_INSET=1,
            FOAM_THICKNESS=3.5,
        )
    )


def axial80x80x25mm() -> AxialSet:
    return fromParameters(
        AxialParameters(
            CASING_SIZE=80,
            CASING_LENGTH=25,
            CASING_DUCT_INSET=1,
            FOAM_THICKNESS=3.5,
        )
    )
