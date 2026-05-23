from attr import dataclass

from prelude import *
import port


@dataclass
class FilterSet:
    cutout: cq.Workplane
    male: cq.Workplane
    female: cq.Workplane
    port: port.PolygonPort

    def translate(self, d):
        return FilterSet(
            cutout=self.cutout.translate(d),
            male=self.male.translate(d),
            female=self.female.translate(d),
            port=self.port.translate(d),
        )

    def rotate(self, axisPoint, axisDirection, angle):
        return FilterSet(
            cutout=self.cutout.rotate(axisPoint, axisDirection, angle),
            male=self.male.rotate(axisPoint, axisDirection, angle),
            female=self.female.rotate(axisPoint, axisDirection, angle),
            port=self.port.rotate(axisPoint, axisDirection, angle),
        )


CLAMP_STRENGTH = NOZZLE * 4
GAP = NOZZLE
NARROWING = NOZZLE
RIM = 15


def set(DEPTH, HEIGHT, WIDTH, DOWNWARD_EXTENSION):
    SLOT_DEPTH = DEPTH - 2 * CLAMP_STRENGTH
    SLOT_HEIGHT = HEIGHT - 2 * CLAMP_STRENGTH
    SLOT_WIDTH = WIDTH - 2 * CLAMP_STRENGTH

    _slotCutout = (
        (
            cq.Workplane("YZ")
            .moveTo(0, -DOWNWARD_EXTENSION)
            .bezier(
                [
                    (0, -DOWNWARD_EXTENSION),
                    (0, -DOWNWARD_EXTENSION / 2),  # control point
                    (
                        CLAMP_STRENGTH + NARROWING,
                        -DOWNWARD_EXTENSION / 2,
                    ),  # control point
                    (CLAMP_STRENGTH + NARROWING, CLAMP_STRENGTH / 2),  # end point
                ]
            )
            .bezier(
                [
                    (CLAMP_STRENGTH + NARROWING, CLAMP_STRENGTH / 2),
                    (
                        CLAMP_STRENGTH + NARROWING,
                        -DOWNWARD_EXTENSION / 2,
                    ),  # control point
                    (CLAMP_STRENGTH + NARROWING, CLAMP_STRENGTH / 2),  # end point
                ]
            )
            .bezier(
                [
                    (CLAMP_STRENGTH + NARROWING, CLAMP_STRENGTH / 2),
                    (
                        CLAMP_STRENGTH + NARROWING,
                        CLAMP_STRENGTH * (3 / 4),
                    ),  # control point
                    (CLAMP_STRENGTH, CLAMP_STRENGTH * (3 / 4)),  # control point
                    (CLAMP_STRENGTH, CLAMP_STRENGTH),  # end point
                ]
            )
            .lineTo(CLAMP_STRENGTH, HEIGHT - CLAMP_STRENGTH)
            .lineTo(DEPTH - CLAMP_STRENGTH, HEIGHT - CLAMP_STRENGTH)
            .lineTo(DEPTH - CLAMP_STRENGTH, -DOWNWARD_EXTENSION)
            .close()
        )
        .extrude(WIDTH - 2 * CLAMP_STRENGTH, combine=False)
        .translate((CLAMP_STRENGTH, 0, 0))
    )

    _areaCutout = (
        (
            cq.Workplane("YZ")
            .moveTo(CLAMP_STRENGTH, RIM - CLAMP_STRENGTH)
            .lineTo(NOZZLE * 2, RIM)
            .lineTo(0, RIM)
            .lineTo(0, HEIGHT - RIM)
            .lineTo(NOZZLE * 2, HEIGHT - RIM)
            .lineTo(CLAMP_STRENGTH, HEIGHT - RIM + CLAMP_STRENGTH)
            .close()
        )
        .extrude(WIDTH - 2 * RIM, combine=False)
        .translate((RIM, 0, 0))
    )

    _cutout = _slotCutout.union(_areaCutout.mirror("XZ", (0, DEPTH / 2, 0), True))

    import shapes

    FRAME_STRENGTH = NOZZLE * 4

    FRAME_WIDTH = WIDTH - 2 * (CLAMP_STRENGTH + GAP)
    FRAME_HEIGHT = HEIGHT - 2 * CLAMP_STRENGTH

    def framePart(rim, outerWallOffset, depth, pincherDepth):
        base = shapes.box(FRAME_WIDTH, FRAME_STRENGTH, FRAME_HEIGHT)
        innerWidth = FRAME_WIDTH - 2 * rim
        innerHeight = FRAME_HEIGHT - 2 * rim
        cutouts = shapes.rectPatterXZ(
            innerWidth, FRAME_STRENGTH, innerHeight, 5, 4, FRAME_STRENGTH
        ).translate((rim, 0, rim))
        outerWall = shapes.rectTubeAlongY(
            FRAME_WIDTH - 2 * outerWallOffset,
            depth,
            FRAME_HEIGHT - 2 * outerWallOffset,
            FRAME_STRENGTH,
        ).translate((outerWallOffset, 0, outerWallOffset))
        pincher = shapes.rectTubeAlongY(
            innerWidth + 2 * FRAME_STRENGTH,
            pincherDepth,
            innerHeight + 2 * FRAME_STRENGTH,
            FRAME_STRENGTH,
        ).translate((rim - FRAME_STRENGTH, 0, rim - FRAME_STRENGTH))
        return base.cut(cutouts).union(outerWall).union(pincher)

    def handle(downwardExtension, slope):
        profile = (
            cq.Workplane("YZ")
            .moveTo(slope, 0)
            .lineTo(-CLAMP_STRENGTH + GAP, -downwardExtension + FRAME_STRENGTH)
            .lineTo(-CLAMP_STRENGTH + GAP, -downwardExtension)
            .lineTo(SLOT_DEPTH, -downwardExtension)
            .lineTo(SLOT_DEPTH, 0)
            .close()
            .extrude(SLOT_WIDTH)
        )
        return profile

    def filterParts():
        pincherGap = 4

        pincherDepth = SLOT_DEPTH - FRAME_STRENGTH - pincherGap

        male = framePart(
            RIM,
            FRAME_STRENGTH + GAP,
            pincherDepth,
            pincherDepth - FRAME_STRENGTH,
        )
        female = (
            framePart(RIM, 0, SLOT_DEPTH - FRAME_STRENGTH * 2, FRAME_STRENGTH * 2)
            .mirror(
                "XZ",
            )
            .translate((0, SLOT_DEPTH, 0))
        )
        _handle = handle(DOWNWARD_EXTENSION + CLAMP_STRENGTH, FRAME_STRENGTH * 2)
        return male, female.union(_handle)

    male, female = filterParts()

    male = male.translate((CLAMP_STRENGTH + GAP, CLAMP_STRENGTH, CLAMP_STRENGTH))
    female = female.translate((CLAMP_STRENGTH + GAP, CLAMP_STRENGTH, CLAMP_STRENGTH))

    p = port.PolygonPort(
        [
            (RIM, 0, RIM),
            (RIM, 0, HEIGHT - RIM),
            (WIDTH - RIM, 0, HEIGHT - RIM),
            (WIDTH - RIM, 0, RIM),
        ],
    )

    return FilterSet(
        cutout=_cutout,
        male=male,
        female=female,
        port=p,
    )
