import shapes
import external.m3
import export


def generate():

    bottom = shapes.box(10, 10, 10)

    bottom = bottom.union(
        shapes.openBox(10, 1, 1, 10, 1, 1, 10, 1, 0, 1).translate((0, 0, 10))
    )

    cap = shapes.box(10, 10, 3).translate((0, 0, 20))

    screw = external.m3.m3(23, 3).translate((5, 5, 23))

    bottom = bottom.cut(screw)
    cap = cap.cut(screw)

    export.stl(bottom, "bottom.stl")
    export.stl(cap, "cap.stl")

    return 0
