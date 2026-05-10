import cadquery as cq

from prelude import *


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


def cathedralAlongY(width, depth, height):
    return (
        cq.Workplane("XZ")
        .moveTo(0, 0)
        .lineTo(0, height - width / 2)
        .lineTo(width / 2, height)
        .lineTo(width, height - width / 2)
        .lineTo(width, 0)
        .close()
        .extrude(-depth)
    )


def cathedralAlongX(width, depth, height):
    return (
        cq.Workplane("YZ")
        .moveTo(0, 0)
        .lineTo(0, height - depth / 2)
        .lineTo(depth / 2, height)
        .lineTo(depth, height - depth / 2)
        .lineTo(depth, 0)
        .close()
        .extrude(width)
    )


def shell_union(solid: cq.Workplane) -> cq.Workplane:
    """
    Return a thin shell of thickness 2*epsilon hugging the original surface
    of `solid`, made by unioning an outward shell (+epsilon) and an inward
    shell (-epsilon).

    The result is a hollow skin straddling the boundary of the input solid.
    """
    outward = solid.shell(EPSILON)
    inward = solid.shell(-EPSILON)
    return outward.union(inward)


def extrudePolygon(polygon, workplane="XY", length=1.0):
    """Extrude a 2D polygon (list of (x, y) tuples) along the workplane normal."""
    return cq.Workplane(workplane).polyline(list(polygon)).close().extrude(length)
