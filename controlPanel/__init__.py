import external.controls
from prelude import *
import shapes

HEIGHT = 60
DEPTH = 20
WIDTH = 120

WALL_STRENGTH = 2


def base():
    volume = shapes.box(WIDTH, DEPTH, HEIGHT)
    cutout = shapes.box(
        WIDTH - 2 * WALL_STRENGTH, DEPTH - WALL_STRENGTH, HEIGHT - 2 * WALL_STRENGTH
    ).translate((WALL_STRENGTH, WALL_STRENGTH, WALL_STRENGTH))
    return volume.cut(cutout)


POTENTIOMETER_OFFSET = 20

POTENTIOMETER1_POS = (POTENTIOMETER_OFFSET, 0, HEIGHT - POTENTIOMETER_OFFSET)
POTENTIOMETER2_POS = (WIDTH - POTENTIOMETER_OFFSET, 0, HEIGHT - POTENTIOMETER_OFFSET)

BUTTON_OFFSET = 15

BUTTON1_POS = (BUTTON_OFFSET, 0, BUTTON_OFFSET)
BUTTON2_POS = (WIDTH - BUTTON_OFFSET, 0, BUTTON_OFFSET)


def pcbMounting():
    BOARD_WIDTH = 64
    BOARD_DEPTH = 5
    BOARD_HEIGHT = 40
    boardReference = shapes.box(BOARD_WIDTH, BOARD_DEPTH, BOARD_HEIGHT)
    HOLE_OFFSETX = 4
    HOLE_OFFSETZ = 4

    import external.m3

    m = external.m3.m3Mounting(DEPTH - BOARD_DEPTH, WALL_STRENGTH)
    m1 = m.translate((HOLE_OFFSETX, 0, HOLE_OFFSETZ))
    m2 = m.translate((BOARD_WIDTH - HOLE_OFFSETX, 0, HOLE_OFFSETZ))
    m3 = m.translate((HOLE_OFFSETX, 0, BOARD_HEIGHT - HOLE_OFFSETZ))
    m4 = m.translate((BOARD_WIDTH - HOLE_OFFSETX, 0, BOARD_HEIGHT - HOLE_OFFSETZ))
    result = m1.union(m2).union(m3).union(m4)
    return result.translate(((WIDTH - BOARD_WIDTH) / 2, 0, (HEIGHT - BOARD_HEIGHT) / 2))


def full():
    b = base()
    potCutout = external.controls.potentiometerCutout()
    butCutout = external.controls.buttonCutout()
    b = b.cut(potCutout.translate(POTENTIOMETER1_POS))
    b = b.cut(potCutout.translate(POTENTIOMETER2_POS))
    b = b.cut(butCutout.translate(BUTTON1_POS))
    b = b.cut(butCutout.translate(BUTTON2_POS))
    m = pcbMounting()
    return b.union(m)


def export():
    import export

    f = full()
    export.step(f, "controlPanel.step")
