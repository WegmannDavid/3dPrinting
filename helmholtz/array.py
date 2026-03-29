from prelude import *
import functools
from helmholtz.random import generate_hole_sizes, HelmholtzPanelParams

import shapes


def neck(depth, diameter):
    n = cq.Workplane("XY").box(diameter, depth, diameter)
    n = n.translate((0, depth / 2, 0))
    n = n.rotate((0, 0, 0), (0, 1, 0), 45)
    return n


def vNeck(depth, width, height, wall_thickness, extension):
    size = depth - wall_thickness * 2
    v = shapes.box(width, size, height).translate((0, wall_thickness, 0))
    a = shapes.box(width, wall_thickness + extension, size).translate(
        (0, -extension, 0)
    )
    b = shapes.box(width, wall_thickness + extension, size).translate(
        (0, depth - wall_thickness, height - size)
    )
    return v.union(a).union(b)


def rectVNeck(depth, height, wall_thickness, extension):
    return vNeck(depth, depth - wall_thickness * 2, height, wall_thickness, extension)


def helmholtz_array(numX, numZ, width, depth, height, lengths):
    offsetX = width / numX
    offsetZ = height / numZ
    startX = offsetZ / 2
    startZ = 0

    necks = []
    for j in range(numZ):
        for i in range(numX):
            l = lengths[i + j * numX]
            necks.append(
                rectVNeck(depth, l, NOZZLE * 2, 10).translate(
                    (startX + i * offsetX, 0, startZ + j * offsetZ)
                )
            )
    return functools.reduce(lambda a, b: a.union(b), necks)


def tuned_helmholtz_array(numX, numZ, width, depth, height):
    l_min = 35  # 50 mm
    l_max = 35  # 50 mm
    beta = 4.0  # increase for more aggressive skew toward small holes
    u = np.random.uniform(0, 1, numX * numZ) ** beta
    diameters = l_min * (l_max / l_min) ** u
    return helmholtz_array(numX, numZ, width, depth, height, diameters)


import numpy as np


def test():
    a = tuned_helmholtz_array(5 * 4, 4, 1000, 6.4, 200)

    cq.exporters.export(a.val(), "stl/tests/helmholtz_array_test.stl")
