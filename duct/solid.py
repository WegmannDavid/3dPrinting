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
    l1: float,
    l2: float,
    extendStraight1: float = 0.0,
    extendStraight2: float = 0.0,
) -> cq.Workplane:
    """
    Creates a solid 2D duct profile extruded to depth.

    The profile is drawn in the plane defined by portDim and lengthDim,
    then extruded along the remaining third dimension by depth.

    The two side walls are Bezier curves with tangents parallel to lengthDim
    at both ends, giving smooth transitions at the ports. Optional straight
    sections of constant cross-section can be added before port 1 and after
    port 2.

    Args:
        portDim:          Dimension of the port spans, e.g. "X"
        lengthDim:        Dimension the duct extends along, e.g. "Z"
        s1, e1:           Start and end of port 1 along portDim (at lengthDim=l1)
        s2, e2:           Start and end of port 2 along portDim (at lengthDim=l2)
        l1, l2:           Start and end of the Bezier section along lengthDim
        extendStraight1:  Length of straight section before port 1
        extendStraight2:  Length of straight section after port 2
    """

    def make_point(port_val: float, length_val: float):
        coords = {"X": 0.0, "Y": 0.0, "Z": 0.0}
        coords[portDim] = port_val
        coords[lengthDim] = length_val
        return (coords["X"], coords["Y"], coords["Z"])

    all_dims = {"X", "Y", "Z"}
    extrude_dim = (all_dims - {portDim, lengthDim}).pop()
    plane_name = "".join(sorted([portDim, lengthDim]))
    handle = (l2 - l1) / 3.0

    l1_outer = l1 - extendStraight1
    l2_outer = l2 + extendStraight2

    start_curve = [
        cq.Vector(make_point(s1, l1)),
        cq.Vector(make_point(s1, l1 + handle)),
        cq.Vector(make_point(s2, l2 - handle)),
        cq.Vector(make_point(s2, l2)),
    ]
    end_curve = [
        cq.Vector(make_point(e2, l2)),
        cq.Vector(make_point(e2, l2 - handle)),
        cq.Vector(make_point(e1, l1 + handle)),
        cq.Vector(make_point(e1, l1)),
    ]

    start_bezier = cq.Edge.makeBezier(start_curve)
    end_bezier = cq.Edge.makeBezier(end_curve)

    edges = []

    # Port 1
    edges.append(
        cq.Edge.makeLine(
            cq.Vector(make_point(s1, l1_outer)),
            cq.Vector(make_point(e1, l1_outer)),
        )
    )

    # Straight extension 1, side e1
    if extendStraight1 > 0.0:
        edges.append(
            cq.Edge.makeLine(
                cq.Vector(make_point(e1, l1_outer)),
                cq.Vector(make_point(e1, l1)),
            )
        )

    # Bezier side (e1 <-> e2)
    edges.append(end_bezier)

    # Straight extension 2, side e2
    if extendStraight2 > 0.0:
        edges.append(
            cq.Edge.makeLine(
                cq.Vector(make_point(e2, l2)),
                cq.Vector(make_point(e2, l2_outer)),
            )
        )

    # Port 2
    edges.append(
        cq.Edge.makeLine(
            cq.Vector(make_point(e2, l2_outer)),
            cq.Vector(make_point(s2, l2_outer)),
        )
    )

    # Straight extension 2, side s2
    if extendStraight2 > 0.0:
        edges.append(
            cq.Edge.makeLine(
                cq.Vector(make_point(s2, l2_outer)),
                cq.Vector(make_point(s2, l2)),
            )
        )

    # Bezier side (s1 <-> s2)
    edges.append(start_bezier)

    # Straight extension 1, side s1
    if extendStraight1 > 0.0:
        edges.append(
            cq.Edge.makeLine(
                cq.Vector(make_point(s1, l1)),
                cq.Vector(make_point(s1, l1_outer)),
            )
        )

    wire = cq.Wire.assembleEdges(edges)

    return cq.Workplane(plane_name).add(wire).toPending()


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


def arrayAlongXOfDuctsAlongZ(
    num, topX1, topX2, botX1, botX2, depth, Y1, Y2, topSep, botSep
):
    topWidth = topX2 - topX1
    topSegmentWidth = (topWidth - (num - 1) * topSep) / num
    botWidth = botX2 - botX1
    botSegmentWidth = (botWidth - (num - 1) * botSep) / num
    result = cq.Workplane("XY")
    for i in range(num):
        result = result.union(
            bezierDuctProfile(
                portDim="X",
                lengthDim="Z",
                s1=botX1 + i * (botSegmentWidth + botSep),
                e1=botX1 + i * (botSegmentWidth + botSep) + botSegmentWidth,
                s2=topX1 + i * (topSegmentWidth + topSep),
                e2=topX1 + i * (topSegmentWidth + topSep) + topSegmentWidth,
                l1=Y1,
                l2=Y2,
            ).extrude(depth)
        )
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
