from prelude import *
import shapes

WALL_THICKNESS = NOZZLE * 4

DEPTH = 28
SIZE = 130

SCREW_DISTANCE = 49

import external.sunkhead


def screwCutouts():
    cornerOffset = SCREW_DISTANCE * math.sqrt(3) / 3

    s1 = (
        external.sunkhead.sunkhead(4.1, 0.4, 2.1, 8, 2, 10)
        .rotate((0, 0, 0), (1, 0, 0), 90)
        .translate((0, 0, -cornerOffset))
    )

    s2 = s1.rotate((0, 0, 0), (0, 1, 0), 120)
    s3 = s1.rotate((0, 0, 0), (0, 1, 0), 240)

    return s1.union(s2).union(s3)


HUB_WALL_STRENGTH = 2
HUB_RADIUS = 38
HUB_DEPTH = 4


def hubCutout():
    return shapes.cylinderAlongY(HUB_RADIUS, HUB_DEPTH)


IMPELLER_RADIUS = 51
IMPELLER_DEPTH = 20

IMPELLER_Y_OFFSET = HUB_WALL_STRENGTH + HUB_DEPTH


def impellerCutout():
    return shapes.cylinderAlongY(IMPELLER_RADIUS, IMPELLER_DEPTH).translate(
        (0, IMPELLER_Y_OFFSET, 0)
    )


REDUCER_IN_DEPTH = 12
REDUCER_OUT_Y1 = 10
REDUCER_OUT_Y2 = 18

import duct.solid


def uPath(
    plane: str,
    leg_length: float,
    bend_radius: float,
) -> cq.Wire:
    """
    Creates a U-shaped path wire: straight leg, 180° semicircular arc, straight leg.

    The U lies in the given plane, opens in the +Y direction of that plane,
    and is symmetric about the local Y axis. The two legs are spaced
    2 * bend_radius apart (center-to-center), so the arc is a true semicircle.

        start                end
          |                   |
          |  leg          leg |
          |                   |
          \\______ arc _______/
              (bend_radius)

    Args:
        plane:        Workplane name, e.g. "XY", "XZ", "YZ"
        leg_length:   Length of each straight segment
        bend_radius:  Radius of the 180° bend

    Returns:
        A cq.Wire representing the U-shaped path.
    """
    # Points (in plane-local 2D coords)
    p_start = (-bend_radius, 0)
    p_leg1_bottom = (-bend_radius, -leg_length)
    p_arc_mid = (0, -leg_length - bend_radius)
    p_leg2_bottom = (bend_radius, -leg_length)
    p_end = (bend_radius, 0)

    wire = (
        cq.Workplane(plane)
        .moveTo(*p_start)
        .lineTo(*p_leg1_bottom)
        .threePointArc(p_arc_mid, p_leg2_bottom)
        .lineTo(*p_end)
        .wire()
        .val()
    )

    return wire


def reducerCutout():
    path = uPath("XZ", SIZE / 2 - WALL_THICKNESS, IMPELLER_RADIUS)
    Y1 = IMPELLER_Y_OFFSET + IMPELLER_DEPTH / 2 - REDUCER_IN_DEPTH / 2
    Y2 = Y1 + REDUCER_IN_DEPTH
    profile = duct.solid.bezierDuctProfile(
        "Y",
        "X",
        Y1,
        Y2,
        REDUCER_OUT_Y1,
        REDUCER_OUT_Y2,
        IMPELLER_RADIUS,
        SIZE / 2 - WALL_THICKNESS,
        extendStraight1=IMPELLER_RADIUS / 2,
        extendStraight2=SIZE,
    )
    b = shapes.box(
        IMPELLER_RADIUS * 2, REDUCER_IN_DEPTH, SIZE / 2 - WALL_THICKNESS
    ).translate((-IMPELLER_RADIUS, Y1, 0))
    return (
        profile.sweep(path, isFrenet=True)
        .translate((0, 0, SIZE / 2 - WALL_THICKNESS))
        .union(b)
    )


INTAKE_RADIUS = 37
INTAKE_DEPTH = DEPTH - HUB_WALL_STRENGTH - HUB_DEPTH - IMPELLER_DEPTH


def intakeCutout():
    return shapes.cylinderAlongY(INTAKE_RADIUS, INTAKE_DEPTH)


def volume():
    return shapes.box(SIZE, DEPTH, SIZE).translate((-SIZE / 2, 0, -SIZE / 2))


def strutArray(numX, numZ, Width, Height, Strength, Depth):
    s = shapes.box(Strength, Depth, Strength)

    def axis_positions(num, total, strut):
        # N struts + N gaps fill `total`. Step between strut origins is strut + gap.
        step = (total - Strength) / num
        return [i * step for i in range(0, num + 1)]

    xs = axis_positions(numX, Width, Strength)
    zs = axis_positions(numZ, Height, Strength)

    result = cq.Workplane("XY")
    for x in xs:
        for z in zs:
            result = result.union(s.translate((x, 0, z)))
    return result


def struts():
    s1 = strutArray(
        3, 1, SIZE, SIZE, WALL_THICKNESS, REDUCER_OUT_Y2 - REDUCER_OUT_Y1
    ).translate((-SIZE / 2, REDUCER_OUT_Y1, -SIZE / 2))

    s2 = strutArray(
        1, 3, SIZE, SIZE, WALL_THICKNESS, REDUCER_OUT_Y2 - REDUCER_OUT_Y1
    ).translate((-SIZE / 2, REDUCER_OUT_Y1, -SIZE / 2))

    return s1.union(s2)


import math


def teardrop(l: float, h: float, radius: float, depth: float) -> cq.Workplane:
    """
    Creates an extruded teardrop/balloon shape: a circle with two straight
    tangent lines rising to a flat top chord of length `l` at height `h`.

    The cross-section lies in the XZ plane:
      - Circle centered at (0, 0) with the given radius
      - Flat top chord of length `l`, centered on X=0, at Z=h
      - Two straight lines connecting the chord endpoints tangentially
        to the circle

    The shape is extruded along Y by `depth`.

    Args:
        l:       Length of the flat top chord (along X)
        h:       Height of the chord above the circle center (along Z)
        radius:  Radius of the circle (at the bottom)
        depth:   Extrusion depth along Y

    Returns:
        A cq.Workplane containing the extruded solid.
    """
    # Top chord endpoints
    top_left = (l / 2.0, h)
    top_right = (-l / 2.0, h)

    # For each top point P, find the tangent point T on the circle such that
    # the line from P to T is tangent to the circle (P-T perpendicular to O-T).
    # |OP|^2 = |OT|^2 + |PT|^2  =>  |PT| = sqrt(|OP|^2 - r^2)
    # The tangent point is found by rotating OP toward the circle by angle
    # alpha = atan2(|PT|, r) ... but it's simpler to compute directly.
    def tangent_point(px: float, pz: float, sign: int) -> tuple[float, float]:
        """
        Tangent point on the circle for an external point (px, pz).
        `sign` picks which of the two tangent points (left vs right).
        """
        d2 = px * px + pz * pz
        if d2 <= radius * radius:
            raise ValueError(
                f"Top point ({px}, {pz}) is inside or on the circle of radius {radius}"
            )
        # Angle from origin to P
        phi = math.atan2(pz, px)
        # Angle between OP and OT (where T is the tangent point)
        theta = math.acos(radius / math.sqrt(d2))
        # Two candidate angles for T:
        t_angle = phi + sign * theta
        return (radius * math.cos(t_angle), radius * math.sin(t_angle))

    # Left top -> tangent point on the upper-left of the circle
    # Right top -> tangent point on the upper-right of the circle
    # `sign` chosen so we get the upper tangent points (the ones facing the chord)
    tan_left = tangent_point(top_left[0], top_left[1], sign=-1)
    tan_right = tangent_point(top_right[0], top_right[1], sign=+1)

    # Build the profile: chord -> right tangent line -> arc around the bottom
    # of the circle -> left tangent line -> back to start
    profile = (
        cq.Workplane("XZ")
        .moveTo(*top_left)
        .lineTo(*top_right)
        .lineTo(*tan_right)
        # Arc from right tangent point, around the bottom of the circle,
        # back up to the left tangent point. The "via" point is the bottom
        # of the circle (0, -radius), which guarantees we go the long way around.
        .threePointArc((0, -radius), tan_left)
        .lineTo(*top_left)
        .close()
    )

    return profile.extrude(-depth)


CABLE_CUTOUT_DEPTH = 7


def cableCutout():
    return teardrop(30, SIZE / 2, HUB_RADIUS, CABLE_CUTOUT_DEPTH).translate(
        (0, HUB_WALL_STRENGTH, 0)
    )


def housing():
    v = volume()
    sc = screwCutouts()
    hc = hubCutout().translate((0, HUB_WALL_STRENGTH, 0))
    impc = impellerCutout()
    rc = reducerCutout()
    inc = intakeCutout().translate((0, DEPTH - INTAKE_DEPTH, 0))
    cc = cableCutout()
    str = struts()
    result = v.cut(sc).cut(impc).cut(rc).cut(inc).cut(cc).union(str).cut(hc)
    return result.translate((SIZE / 2, 0, SIZE / 2))


import split
import split.vbar


def splitter():
    reference = housing()
    ch = WALL_THICKNESS * 3
    h = SIZE / 2 - ch
    w = IMPELLER_RADIUS * 2 + WALL_THICKNESS * 2
    x1 = SIZE / 2 - w / 2
    x2 = SIZE / 2 + w / 2
    cover = shapes.box(SIZE * 2, DEPTH * 2, ch).translate(
        (-SIZE / 2, -DEPTH / 2, SIZE - ch)
    )
    box = shapes.box(w, DEPTH * 2, h).translate(
        (x1, -DEPTH / 2, SIZE / 2 + EPSILON * 2)
    )
    splitter = split.shell(box.union(cover))

    lb1 = (
        split.vbar.feature(h, 1.6)
        .mirror("YZ")
        .translate((x1, DEPTH - split.vbar.Y_OFFSET, SIZE / 2))
    )
    lb2 = (
        split.vbar.feature(h, 1.6)
        .mirror("YZ")
        .translate((x1, split.vbar.Y_OFFSET, SIZE / 2))
    )
    rb1 = split.vbar.feature(h, 1.6).translate(
        (x2, DEPTH - split.vbar.Y_OFFSET, SIZE / 2)
    )
    rb2 = split.vbar.feature(h, 1.6).translate((x2, split.vbar.Y_OFFSET, SIZE / 2))
    splitter = split.addFeature(splitter, lb1)
    splitter = split.addFeature(splitter, lb2)
    splitter = split.addFeature(splitter, rb1)
    splitter = split.addFeature(splitter, rb2)

    cutoutDepth = 8

    lc1 = shapes.boxFromBounds(
        0,
        x1 / 2,
        NOZZLE * 2,
        cutoutDepth,
        SIZE - ch - WALL_THICKNESS * 2,
        SIZE - ch,
    )

    lc2 = shapes.boxFromBounds(
        0,
        x1 / 2,
        DEPTH - cutoutDepth,
        DEPTH - NOZZLE * 2,
        SIZE - ch - WALL_THICKNESS * 2,
        SIZE - ch,
    )

    lc = lc1.union(lc2)
    rc = lc.mirror("YZ").translate((SIZE, 0, 0))

    return splitter.union(lc).union(rc)


def export():
    c = external.fan.Centrifugal.housing()
    s = external.fan.Centrifugal.splitter()

    segments = c.cut(s).solids()
    segments = sorted(
        segments, key=lambda s: (s.Center().x, s.Center().y, s.Center().z)
    )

    import export

    export.step(c, "c.step")
    export.step(segments[0], "cBottom.step")
    export.step(segments[1], "cTop.step")


import port


class CentrifugalFanSet:
    housing: cq.Workplane
    cutout: cq.Workplane
    inlet: port.CircularPort

    def __init__(self, housing, cutout, inlet):
        self.housing = housing
        self.cutout = cutout
        self.inlet = inlet

    def translate(self, d):
        return CentrifugalFanSet(
            housing=self.housing.translate(d),
            cutout=self.cutout.translate(d),
            inlet=self.inlet.translate(d),
        )


def centrifugalFanSet(intakeCutoutExtension):
    h = housing()
    c = volume().translate((SIZE / 2, 0, SIZE / 2))
    i = port.CircularPort(
        center=(SIZE / 2, DEPTH + intakeCutoutExtension, SIZE / 2),
        normal=(0, 1, 0),
        radius=INTAKE_RADIUS,
    )
    return CentrifugalFanSet(housing=h, cutout=c, inlet=i)
