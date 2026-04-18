from prelude import *


def sunkhead(headRad, headHeight, freeRad, freeHeight, gripRad, height):
    headEndHeight = headRad - freeRad + headHeight
    profile = (
        cq.Workplane("YZ")
        .moveTo(0, 0)
        .lineTo(headRad, 0)
        .lineTo(headRad, -headHeight)
        .lineTo(freeRad, -headEndHeight)
        .lineTo(freeRad, -freeHeight)
        .lineTo(gripRad, -freeHeight)
        .lineTo(gripRad, -height)
        .lineTo(0, -height)
        .close()
    )
    return profile.revolve(360, (0, 0, 0), (0, 1, 0))
