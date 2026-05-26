from attr import dataclass

from prelude import *
import port


@dataclass
class FilterSet:
    cutout: cq.Workplane
    male: cq.Workplane
    female: cq.Workplane
    medium: cq.Workplane
    port: port.PolygonPort

    def translate(self, d):
        return FilterSet(
            cutout=self.cutout.translate(d),
            male=self.male.translate(d),
            female=self.female.translate(d),
            medium=self.medium.translate(d),
            port=self.port.translate(d),
        )

    def rotate(self, axisPoint, axisDirection, angle):
        return FilterSet(
            cutout=self.cutout.rotate(axisPoint, axisDirection, angle),
            male=self.male.rotate(axisPoint, axisDirection, angle),
            female=self.female.rotate(axisPoint, axisDirection, angle),
            medium=self.medium.rotate(axisPoint, axisDirection, angle),
            port=self.port.rotate(axisPoint, axisDirection, angle),
        )

    def mirror(self, plane):
        return FilterSet(
            cutout=self.cutout.mirror(plane),
            male=self.male.mirror(plane),
            female=self.female.mirror(plane),
            medium=self.medium.mirror(plane),
            port=self.port.mirror(plane),
        )


CLAMP_STRENGTH = NOZZLE * 4
GAP = NOZZLE
NARROWING_DEPTH = NOZZLE
NARROWING_HEIGHT = NOZZLE * 2
RIM = 15
FRAME_STRENGTH = NOZZLE * 4


def set(DEPTH, HEIGHT, WIDTH, HANDLE_HEIGHT, HANDLE_DEPTH):
    SLOT_DEPTH = DEPTH - 2 * CLAMP_STRENGTH
    SLOT_WIDTH = WIDTH - 2 * CLAMP_STRENGTH

    _slotCutoutProfile = (
        cq.Workplane("YZ")
        .moveTo(HANDLE_DEPTH, -HANDLE_HEIGHT)
        .bezier(
            [
                (HANDLE_DEPTH, -HANDLE_HEIGHT),
                (HANDLE_DEPTH, -HANDLE_HEIGHT / 2),  # control point
                (
                    DEPTH - CLAMP_STRENGTH - NARROWING_DEPTH,
                    -HANDLE_HEIGHT / 2,
                ),  # control point
                (
                    DEPTH - CLAMP_STRENGTH - NARROWING_DEPTH,
                    CLAMP_STRENGTH - NARROWING_HEIGHT,
                ),  # end point
            ]
        )
        .bezier(
            [
                (
                    DEPTH - CLAMP_STRENGTH - NARROWING_DEPTH,
                    CLAMP_STRENGTH - NARROWING_HEIGHT,
                ),  # start point
                (
                    DEPTH - CLAMP_STRENGTH - NARROWING_DEPTH,
                    CLAMP_STRENGTH - NARROWING_HEIGHT / 2,
                ),  # control point
                (
                    DEPTH - CLAMP_STRENGTH,
                    CLAMP_STRENGTH - NARROWING_HEIGHT / 2,
                ),  # control point
                (DEPTH - CLAMP_STRENGTH, CLAMP_STRENGTH),  # end point
            ]
        )
        .lineTo(DEPTH - CLAMP_STRENGTH, HEIGHT - CLAMP_STRENGTH)
        .lineTo(CLAMP_STRENGTH, HEIGHT - CLAMP_STRENGTH)
        .lineTo(CLAMP_STRENGTH, -HANDLE_HEIGHT)
        .close()
    )
    _slotCutout = _slotCutoutProfile.extrude(SLOT_WIDTH, combine=False).translate(
        (CLAMP_STRENGTH, 0, 0)
    )

    _areaCutout = (
        (
            cq.Workplane("YZ")
            .moveTo(CLAMP_STRENGTH, RIM - CLAMP_STRENGTH + FRAME_STRENGTH)
            .lineTo(NOZZLE * 2, RIM + FRAME_STRENGTH)
            .lineTo(0, RIM + FRAME_STRENGTH)
            .lineTo(0, HEIGHT - RIM - FRAME_STRENGTH)
            .lineTo(NOZZLE * 2, HEIGHT - RIM - FRAME_STRENGTH)
            .lineTo(CLAMP_STRENGTH, HEIGHT - RIM + CLAMP_STRENGTH - FRAME_STRENGTH)
            .close()
        )
        .extrude(WIDTH - 2 * RIM - 2 * GAP - 2 * CLAMP_STRENGTH, combine=False)
        .translate((RIM + GAP + CLAMP_STRENGTH, 0, 0))
    )

    _cutout = _slotCutout.union(_areaCutout.mirror("XZ", (0, DEPTH / 2, 0), True))

    import shapes

    FRAME_WIDTH = WIDTH - 2 * (CLAMP_STRENGTH + GAP)
    FRAME_HEIGHT = HEIGHT - 2 * CLAMP_STRENGTH

    def framePart(outerWallOffset, depth, pincherDepth):
        base = shapes.box(FRAME_WIDTH, FRAME_STRENGTH, FRAME_HEIGHT)
        innerWidth = FRAME_WIDTH - 2 * RIM
        innerHeight = FRAME_HEIGHT - 2 * RIM
        cutouts = shapes.rectPatterXZ(
            innerWidth, FRAME_STRENGTH, innerHeight, 5, 4, FRAME_STRENGTH
        ).translate((RIM, 0, RIM))
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
        ).translate((RIM - FRAME_STRENGTH, 0, RIM - FRAME_STRENGTH))
        return base.cut(cutouts).union(outerWall).union(pincher)

    def handle(handleHeight, narrowDepth):
        profile = (
            cq.Workplane("YZ")
            .moveTo(narrowDepth, 0)
            .lineTo(HANDLE_DEPTH - CLAMP_STRENGTH - GAP, -handleHeight + FRAME_STRENGTH)
            .lineTo(HANDLE_DEPTH - CLAMP_STRENGTH - GAP, -handleHeight)
            .lineTo(0, -handleHeight)
            .lineTo(0, 0)
            .close()
        )
        return profile.extrude(FRAME_WIDTH)

    def filterParts():
        pincherGap = 4

        pincherDepth = SLOT_DEPTH - FRAME_STRENGTH - pincherGap

        male = (
            framePart(
                FRAME_STRENGTH + GAP,
                pincherDepth,
                pincherDepth - FRAME_STRENGTH,
            )
            .mirror("XZ")
            .translate((0, SLOT_DEPTH, 0))
        )
        female = framePart(0, SLOT_DEPTH - FRAME_STRENGTH * 2, FRAME_STRENGTH * 2)
        _handle = handle(
            HANDLE_HEIGHT + CLAMP_STRENGTH,
            DEPTH - FRAME_STRENGTH * 2 - CLAMP_STRENGTH * 2,
        )
        return male, female.union(_handle)

    male, female = filterParts()

    male = male.translate((CLAMP_STRENGTH + GAP, CLAMP_STRENGTH, CLAMP_STRENGTH))
    female = female.translate((CLAMP_STRENGTH + GAP, CLAMP_STRENGTH, CLAMP_STRENGTH))

    p = port.PolygonPort(
        [
            (WIDTH - RIM - FRAME_STRENGTH - GAP, DEPTH, RIM + FRAME_STRENGTH),
            (WIDTH - RIM - FRAME_STRENGTH - GAP, DEPTH, HEIGHT - RIM - FRAME_STRENGTH),
            (RIM + FRAME_STRENGTH + GAP, DEPTH, HEIGHT - RIM - FRAME_STRENGTH),
            (RIM + FRAME_STRENGTH + GAP, DEPTH, RIM + FRAME_STRENGTH),
        ],
    )
    medium = (
        shapes.box(FRAME_WIDTH, SLOT_DEPTH, FRAME_HEIGHT)
        .translate((CLAMP_STRENGTH + GAP, CLAMP_STRENGTH, CLAMP_STRENGTH))
        .cut(male.union(female))
    )

    return FilterSet(
        cutout=_cutout,
        male=male,
        female=female,
        medium=medium,
        port=p,
    )
