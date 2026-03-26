from prelude import *
import functools
from helmholtz.random import generate_hole_sizes, HelmholtzPanelParams

def neck(depth, diameter):
    n = cq.Workplane("XY").box(diameter, depth, diameter)
    n = n.translate((0, depth / 2, 0))
    n = n.rotate((0, 0, 0), (0, 1, 0), 45)
    return n

def helmholtz_array(numX, numZ, width, depth, height, diameters):
    offsetX = width  / numX
    offsetZ = height / numZ
    startX  = offsetX / 2
    startZ  = offsetZ / 2

    necks = []
    for j in range(numZ):
        for i in range(numX):
            d = diameters[i + j * numX]
            necks.append(
                neck(depth, d).translate(
                    (startX + i * offsetX, 0, startZ + j * offsetZ)
                )
            )
    return functools.reduce(lambda a, b: a.union(b), necks)

def tuned_helmholtz_array(numX, numZ, width, depth, height):
    a_min=0.6   # 1 mm
    a_max=6   # 1 mm
    beta = 4.0  # increase for more aggressive skew toward small holes
    u = np.random.uniform(0, 1, numX*numZ) ** beta
    diameters = a_min * (a_max / a_min) ** u
    return helmholtz_array(numX, numZ, width, depth, height, diameters)

import numpy as np

def test():
    a = tuned_helmholtz_array(5*4, 4, 1000, 6.4, 200)

    cq.exporters.export(a.val(), "stl/tests/helmholtz_array_test.stl")