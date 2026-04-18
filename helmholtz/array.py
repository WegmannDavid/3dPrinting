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
    width = depth - wall_thickness * 2
    n = vNeck(depth, width, height, wall_thickness, extension)
    return n.rotate((0, 0, 0), (0, 1, 0), 45).translate((width, 0, width))


def helmholtz_array(numX, numZ, width, depth, height, lengths):
    offsetX = width / numX
    offsetZ = height / numZ
    startX = 0
    startZ = 0

    necks = []
    for j in range(numZ):
        for i in range(numX):
            l = lengths[j, i]
            necks.append(
                rectVNeck(depth, l, NOZZLE * 2, 10).translate(
                    (startX + i * offsetX, 0, startZ + j * offsetZ)
                )
            )
    return functools.reduce(lambda a, b: a.union(b), necks)


def sample_neck_lengths_2d(l1, l2, nX, nZ, seed=42):
    u = np.linspace(0, 1, nX * nZ)
    L = (1 / np.sqrt(l1) - u * (1 / np.sqrt(l1) - 1 / np.sqrt(l2))) ** (-2)
    rng = np.random.default_rng(seed)
    rng.shuffle(L)
    return L.reshape(nZ, nX)


def tuned_helmholtz_array(numX, numZ, width, depth, height):
    l_min = 5  # 50 mm
    l_max = 20  # 50 mm
    diameters = sample_neck_lengths_2d(l_min, l_max, numX, numZ)
    return helmholtz_array(numX, numZ, width, depth, height, diameters)


import numpy as np


def test():
    a = tuned_helmholtz_array(5 * 4, 4, 1000, 6.4, 200)

    cq.exporters.export(a.val(), "stl/tests/helmholtz_array_test.stl")
