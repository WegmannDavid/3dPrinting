import cadquery as cq


def box(width, depth, height, centered=False):
    return cq.Workplane("XY").box(width, depth, height, centered=centered)


def openBox(
    width, wOpen1, wOpen2, depth, dOpen1, dOpen2, height, hOpen1, hOpen2, wallStrength
):
    volume = box(width, depth, height)
    cutout = box(
        width - wOpen1 * wallStrength - wOpen2 * wallStrength,
        depth - dOpen1 * wallStrength - dOpen2 * wallStrength,
        height - hOpen1 * wallStrength - hOpen2 * wallStrength,
    )
    cutout = cutout.translate(
        (wallStrength * wOpen1, wallStrength * hOpen1, wallStrength * dOpen1)
    )
    return volume.cut(cutout)


def grid_plate(holes_x, holes_y, hole_diameter, width, height, depth):
    return 0
