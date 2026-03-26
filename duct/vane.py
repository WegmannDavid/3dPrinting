from prelude import *
import cadquery as cq
import shapes

_strength = NOZZLE * 2


def startVane(size, depth):
    return (
        cq.Workplane("XZ")
        .moveTo(0, size)
        .lineTo(0, 0)
        .lineTo(size, 0)
        .radiusArc((0, size), -size)
        .close()
    ).extrude(-depth)


def vane(size, depth):
    return (
        cq.Workplane("XZ")
        .moveTo(-size, size)
        .lineTo(-size, size - _strength)
        .radiusArc((size - _strength, -size), size * 2 - _strength)
        .lineTo(size, -size)
        .lineTo(size, 0)
        .radiusArc((0, size), -size)
        .close()
    ).extrude(-depth)


def endVane(size, depth):
    return (
        cq.Workplane("XZ")
        .moveTo(-size, size)
        .lineTo(-size, size - _strength)
        .radiusArc((size - _strength, -size), size * 2 - _strength)
        .lineTo(size, -size)
        .lineTo(size, size)
        .close()
    ).extrude(-depth)


def vaneSize(size, num):
    return size / num


def vanes(size, depth, num):
    vaneSize = size / num
    result = startVane(vaneSize, depth).translate((-vaneSize, 0, -vaneSize))
    for i in range(0, num - 1):
        result = result.union(
            vane(vaneSize, depth).translate((i * vaneSize, 0, i * vaneSize))
        )
    result = result.union(
        endVane(vaneSize, depth).translate(
            ((num - 1) * vaneSize, 0, (num - 1) * vaneSize)
        )
    )
    return result


def vaneElbowCutout(size, numVanes, depth):
    _vaneSize = vaneSize(size, numVanes)
    volume = shapes.box(size + _vaneSize, depth, size + _vaneSize)
    volume = volume.translate((-_vaneSize, 0, -_vaneSize))
    v = vanes(size, depth, numVanes)
    return volume.cut(v)
