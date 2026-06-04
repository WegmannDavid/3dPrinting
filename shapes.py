import cadquery as cq


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


import math

SQRT2 = math.sqrt(2)


def fractalPatternB(SIZE, DEPTH, GAP, recursion_depth):
    if recursion_depth > 0:
        newSize = SIZE / 2 - GAP / 2
        r11 = fractalPatternB(newSize, DEPTH, GAP, recursion_depth - 1).translate(
            (0, 0, 0)
        )
        r21 = fractalPatternB(newSize, DEPTH, GAP, recursion_depth - 1).translate(
            (newSize + GAP, 0, 0)
        )
        r12 = fractalPatternB(newSize, DEPTH, GAP, recursion_depth - 1).translate(
            (0, 0, newSize + GAP)
        )
        r22 = fractalPatternB(newSize, DEPTH, GAP, recursion_depth - 1).translate(
            (newSize + GAP, 0, newSize + GAP)
        )
        return r11.union(r21).union(r12).union(r22)
    else:
        return box(SIZE, DEPTH, SIZE)


def fractalPatternA(SIZE, DEPTH, GAP, recursion_depthA, recursion_depthB):
    b = fractalPatternB(SIZE, DEPTH, GAP, recursion_depthB)
    if recursion_depthA > 0:
        newSize = SIZE / 2 - GAP / 2
        l = fractalPatternA(
            newSize, DEPTH, GAP, recursion_depthA - 1, recursion_depthB - 1
        ).translate((SIZE + GAP, 0, 0))
        r = fractalPatternA(
            newSize, DEPTH, GAP, recursion_depthA - 1, recursion_depthB - 1
        ).translate((0, 0, SIZE + GAP))
        return b.union(l).union(r)
    else:
        return b


def supportsAlongYForZInner(
    SIZE, DEPTH, GAP, inner_recursion_depth, outer_recursion_depth
):
    section = box(SIZE * outer_recursion_depth, DEPTH, SIZE * outer_recursion_depth)
    section = section.translate(
        (-SIZE * outer_recursion_depth + SIZE, 0, -SIZE * outer_recursion_depth + SIZE)
    )
    fp = fractalPatternB(SIZE, DEPTH, GAP, inner_recursion_depth)

    for i in range(outer_recursion_depth):
        for j in range(outer_recursion_depth):
            fp = fp.union(
                fractalPatternB(SIZE, DEPTH, GAP, inner_recursion_depth).translate(
                    ((SIZE + GAP) * -i, 0, (SIZE + GAP) * -j)
                )
            )
    return fp


def supportsAlongYForZ(WIDTH, DEPTH, HEIGHT, GAP, recursion_depthA, recursion_depthB):
    section = box(WIDTH, DEPTH, HEIGHT)
    fp = fractalPatternA(
        WIDTH * SQRT2 / 2, DEPTH, GAP, recursion_depthA, recursion_depthB
    )
    fp = fp.rotate((0, 0, 0), (0, 1, 0), -45).translate((WIDTH / 2, 0, HEIGHT - WIDTH))
    fp = fp.intersect(section)

    supports = supportsAlongYForZInner(
        WIDTH * SQRT2 / 2, DEPTH, GAP, recursion_depthB, math.ceil(HEIGHT / WIDTH) + 1
    )
    supports = supports.rotate((0, 0, 0), (0, 1, 0), -45).translate(
        (WIDTH / 2, 0, HEIGHT - WIDTH)
    )
    return fp.union(supports).intersect(section)
