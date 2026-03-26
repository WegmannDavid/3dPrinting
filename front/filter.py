from prelude import *
import front

DEPTH = 20

CLAMP_STRENGTH = NOZZLE*4
RIM = 10
NARROWING = NOZZLE/2

_slotCutout = (
    cq.Workplane("YZ")
    .moveTo(0, -front.BASE_PLATE_HEIGHT)
    .bezier([
        (0,                        -front.BASE_PLATE_HEIGHT),
        (0,                        -front.BASE_PLATE_HEIGHT/2),   # control point
        (CLAMP_STRENGTH+NARROWING, -front.BASE_PLATE_HEIGHT/2),   # control point
        (CLAMP_STRENGTH+NARROWING, CLAMP_STRENGTH/2),             # end point
    ])
    .bezier([
        (CLAMP_STRENGTH+NARROWING, CLAMP_STRENGTH/2), 
        (CLAMP_STRENGTH+NARROWING, CLAMP_STRENGTH*(3/4)),         # control point
        (CLAMP_STRENGTH,           CLAMP_STRENGTH*(3/4)),         # control point
        (CLAMP_STRENGTH,           CLAMP_STRENGTH),               # end point
    ])
    .lineTo(CLAMP_STRENGTH        , front.HEIGHT-CLAMP_STRENGTH)
    .lineTo(DEPTH - CLAMP_STRENGTH,  front.HEIGHT-CLAMP_STRENGTH)
    .lineTo(DEPTH - CLAMP_STRENGTH, -front.BASE_PLATE_HEIGHT)
    .close()
).extrude(front.SECTION15_WIDTH-2*CLAMP_STRENGTH, combine=False).translate((CLAMP_STRENGTH, 0, 0))

_areaCutout = (
    cq.Workplane("YZ")
    .moveTo(CLAMP_STRENGTH, RIM-CLAMP_STRENGTH)
    .lineTo(NOZZLE*2, RIM)
    .lineTo(0, RIM)

    .lineTo(-front.WALL_STRENGTH, RIM)
    .lineTo(-front.WALL_STRENGTH, front.HEIGHT-RIM)

    .lineTo(0, front.HEIGHT-RIM)
    .lineTo(NOZZLE*2, front.HEIGHT-RIM)
    .lineTo(CLAMP_STRENGTH, front.HEIGHT-RIM+CLAMP_STRENGTH)
    .close()
    ).extrude(front.SECTION15_WIDTH-2*RIM, combine=False).translate((RIM, 0, 0))

cutout = _slotCutout.union(_areaCutout.mirror("XZ", (0, DEPTH/2,0), True)).translate((0, front.DEPTH-DEPTH, 0))
