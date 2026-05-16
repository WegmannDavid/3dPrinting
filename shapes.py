import cadquery as cq

from prelude import *


def box(width, depth, height, centered=False):
    return cq.Workplane("XY").box(width, depth, height, centered=centered)


def boxFromBounds(x1, x2, y1, y2, z1, z2):
    return box(x2 - x1, y2 - y1, z2 - z1).translate((x1, y1, z1))


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


def rectTubeAlongY(width, depth, height, strength):
    return box(width, depth, height).cut(
        box(width - 2 * strength, depth, height - 2 * strength).translate(
            (strength, 0, strength)
        )
    )


def rectPatterXZ(width, depth, height, nX, nZ, gap):
    cellWidth = (width - gap * (nX - 1)) / nX
    cellHeight = (height - gap * (nZ - 1)) / nZ

    cellOffsetX = cellWidth + gap
    cellOffsetZ = cellHeight + gap

    result = cq.Workplane("XY")

    for i in range(nX):
        for j in range(nZ):
            result = result.union(
                box(cellWidth, depth, cellHeight).translate(
                    (i * cellOffsetX, 0, j * cellOffsetZ)
                )
            )

    return result


def rectPatterXY(width, depth, height, nX, nY, gap):
    patterXZ = rectPatterXZ(width, depth, height, nX, nY, gap)
    result = patterXZ.rotate((0, 0, 0), (1, 0, 0), 90)
    return result


def cylinderAlongZ(radius, height):
    return cq.Workplane("XY").circle(radius).extrude(height)


def cylinderAlongY(radius, depth):
    return cq.Workplane("XZ").circle(radius).extrude(-depth)


def extrudePolygon(polygon, workplane="XY", length=1.0):
    """Extrude a 2D polygon (list of (x, y) tuples) along the workplane normal."""
    return cq.Workplane(workplane).polyline(list(polygon)).close().extrude(length)
