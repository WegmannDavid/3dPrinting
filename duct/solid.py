import cadquery as cq
from dataclasses import dataclass


@dataclass
class RectPort:
    width: float
    height: float
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def translate(self, d):
        dx, dy, dz = d
        return RectPort(
            width=self.width,
            height=self.height,
            x=self.x + dx,
            y=self.y + dy,
            z=self.z + dz,
        )


def bezierDuctProfile(
    portDim: str,
    lengthDim: str,
    s1: float,
    e1: float,
    s2: float,
    e2: float,
    length: float,
    depth: float,
) -> cq.Workplane:
    """
    Creates a solid 2D duct profile extruded to depth.

    The profile is drawn in the plane defined by portDim and lengthDim,
    then extruded along the remaining third dimension by depth.

    The two side walls are Bezier curves with tangents parallel to lengthDim
    at both ends, giving smooth transitions at the ports.

    Args:
        portDim:   Dimension of the port spans, e.g. "X"
        lengthDim: Dimension the duct extends along, e.g. "Z"
        s1, e1:    Start and end of port 1 along portDim (at lengthDim=0)
        s2, e2:    Start and end of port 2 along portDim (at lengthDim=length)
        length:    Extent of the duct along lengthDim
        depth:     Extrusion depth along the remaining dimension
    """

    def make_point(port_val: float, length_val: float):
        coords = {"X": 0.0, "Y": 0.0, "Z": 0.0}
        coords[portDim] = port_val
        coords[lengthDim] = length_val
        return (coords["X"], coords["Y"], coords["Z"])

    all_dims = {"X", "Y", "Z"}
    extrude_dim = (all_dims - {portDim, lengthDim}).pop()
    plane_name = "".join(sorted([portDim, lengthDim]))
    handle = length / 3.0

    start_curve = [
        cq.Vector(make_point(s1, 0)),
        cq.Vector(make_point(s1, handle)),
        cq.Vector(make_point(s2, length - handle)),
        cq.Vector(make_point(s2, length)),
    ]
    end_curve = [
        cq.Vector(make_point(e2, length)),
        cq.Vector(make_point(e2, length - handle)),
        cq.Vector(make_point(e1, handle)),
        cq.Vector(make_point(e1, 0)),
    ]

    start_edge = cq.Edge.makeBezier(start_curve)
    end_edge = cq.Edge.makeBezier(end_curve)
    port1_edge = cq.Edge.makeLine(
        cq.Vector(make_point(s1, 0)),
        cq.Vector(make_point(e1, 0)),
    )
    port2_edge = cq.Edge.makeLine(
        cq.Vector(make_point(s2, length)),
        cq.Vector(make_point(e2, length)),
    )

    wire = cq.Wire.assembleEdges([port1_edge, end_edge, port2_edge, start_edge])

    return cq.Workplane(plane_name).add(wire).toPending().extrude(-depth)


def rectDuctYZAlongX(port1: RectPort, port2: RectPort) -> cq.Workplane:
    length = port2.x - port1.x
    # Full extents covering both ports
    max_y = max(abs(port1.y + port1.width), abs(port2.y + port2.width))
    max_z = max(abs(port1.z + port1.height), abs(port2.z + port2.height))

    depth = max(max_y, max_z)

    profile_a = bezierDuctProfile(
        portDim="Y",
        lengthDim="X",
        s1=port1.y,
        e1=port1.y + port1.width,
        s2=port2.y,
        e2=port2.y + port2.width,
        length=length,
        depth=-depth * 2,
    )

    profile_b = bezierDuctProfile(
        portDim="Z",
        lengthDim="X",
        s1=port1.z,
        e1=port1.z + port1.height,
        s2=port2.z,
        e2=port2.z + port2.height,
        length=length,
        depth=depth * 2,
    )

    # profile_a = profile_a.union(profile_a.mirror("YZ"))
    # profile_b = profile_b.union(profile_b.mirror("XZ"))

    result = profile_a.intersect(profile_b).translate((port1.x, 0, 0))

    return result


def guidingVaneAlongZ(Width1, Width2, Depth, Height):
    result = bezierDuctProfile(
        portDim="X",
        lengthDim="Z",
        s1=-Width1 / 2,
        e1=Width1 / 2,
        s2=-Width2 / 2,
        e2=Width2 / 2,
        length=Height,
        depth=Depth,
    )
    return result
