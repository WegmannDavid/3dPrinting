import cadquery as cq
from OCP.gp import gp_Pnt, gp_Vec, gp_Circ, gp_Ax2, gp_Dir, gp_Pln
from OCP.Geom import Geom_BSplineCurve, Geom_BSplineSurface, Geom_Circle
from OCP.GeomConvert import GeomConvert
from OCP.TColgp import TColgp_Array1OfPnt, TColgp_Array2OfPnt
from OCP.TColStd import (
    TColStd_Array1OfReal,
    TColStd_Array1OfInteger,
    TColStd_Array2OfReal,
)
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeWire,
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_Sewing,
)
from OCP.BRep import BRep_Builder
from OCP.TopoDS import TopoDS_Solid, TopoDS, TopoDS_Shell, TopoDS_Face
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SHELL, TopAbs_FACE
from OCP.ShapeFix import ShapeFix_Solid
import math
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Convention:
#
#   All curves must wind COUNTERCLOCKWISE when viewed from outside the solid.
#
#   A BezierEndpoint pairs a boundary curve with a control curve. The
#   control curve gives the positions (not offsets) of the inner Bezier
#   control row at that boundary. The lofted surface interpolates four
#   rows of poles in U:
#       start.curve → start.control → end.control → end.curve
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# BezierEndpoint
# ---------------------------------------------------------------------------


@dataclass
class BezierEndpoint:
    """
    A boundary curve paired with the inner Bezier control row at that
    boundary.

    curve:   the actual boundary — a BSpline curve in 3D space
    control: positions of the inner Bezier control row — a BSpline curve
             of absolute positions (not offsets)

    The lofted surface interpolates four rows of poles in U:
        start.curve → start.control → end.control → end.curve
    """

    curve: Geom_BSplineCurve
    control: Geom_BSplineCurve

    def translate(self, offset: tuple[float, float, float]) -> "BezierEndpoint":
        """Return a copy of this endpoint translated by the given offset."""
        return BezierEndpoint(
            curve=offset_curve(self.curve, offset),
            control=offset_curve(self.control, offset),
        )


# ---------------------------------------------------------------------------
# Curve unification
# ---------------------------------------------------------------------------


def _unify_curves(curves: list[Geom_BSplineCurve]) -> list[Geom_BSplineCurve]:
    """
    Make all BSpline curves compatible: same degree, same knot vector,
    same number of poles. Operates in-place and returns the same list.
    """
    max_deg = max(c.Degree() for c in curves)
    for c in curves:
        if c.Degree() < max_deg:
            c.IncreaseDegree(max_deg)

    all_knots: dict[float, int] = {}
    for c in curves:
        first, last = c.FirstParameter(), c.LastParameter()
        rng = last - first
        for i in range(1, c.NbKnots() + 1):
            norm_k = round((c.Knot(i) - first) / rng, 12)
            m = c.Multiplicity(i)
            if norm_k not in all_knots or all_knots[norm_k] < m:
                all_knots[norm_k] = m

    for c in curves:
        first, last = c.FirstParameter(), c.LastParameter()
        rng = last - first
        for norm_k, target_mult in sorted(all_knots.items()):
            actual_k = first + norm_k * rng
            current_mult = 0
            for i in range(1, c.NbKnots() + 1):
                if abs(c.Knot(i) - actual_k) < 1e-10:
                    current_mult = c.Multiplicity(i)
                    break
            if current_mult < target_mult:
                c.InsertKnot(actual_k, target_mult - current_mult)

    return curves


# ---------------------------------------------------------------------------
# Surface construction
# ---------------------------------------------------------------------------


def _build_surface(curves: list[Geom_BSplineCurve]) -> Geom_BSplineSurface:
    """
    Build a BSpline surface from exactly 4 unified BSpline curves
    used as cubic Bezier control rows in the U direction.
    """
    if len(curves) != 4:
        raise ValueError("Exactly 4 curves required")

    curves = _unify_curves(curves)

    n_v = curves[0].NbPoles()
    v_degree = curves[0].Degree()

    poles = TColgp_Array2OfPnt(1, 4, 1, n_v)
    weights = TColStd_Array2OfReal(1, 4, 1, n_v)

    for i, c in enumerate(curves):
        for j in range(1, n_v + 1):
            poles.SetValue(i + 1, j, c.Pole(j))
            w = c.Weight(j) if c.IsRational() else 1.0
            weights.SetValue(i + 1, j, w)

    u_knots = TColStd_Array1OfReal(1, 2)
    u_knots.SetValue(1, 0.0)
    u_knots.SetValue(2, 1.0)
    u_mults = TColStd_Array1OfInteger(1, 2)
    u_mults.SetValue(1, 4)
    u_mults.SetValue(2, 4)

    v_nk = curves[0].NbKnots()
    v_knots = TColStd_Array1OfReal(1, v_nk)
    v_mults = TColStd_Array1OfInteger(1, v_nk)
    for i in range(1, v_nk + 1):
        v_knots.SetValue(i, curves[0].Knot(i))
        v_mults.SetValue(i, curves[0].Multiplicity(i))

    return Geom_BSplineSurface(
        poles,
        weights,
        u_knots,
        v_knots,
        u_mults,
        v_mults,
        3,
        v_degree,
    )


# ---------------------------------------------------------------------------
# Solid construction
# ---------------------------------------------------------------------------


def _sew_to_solid(faces: list) -> TopoDS_Solid:
    """Sew faces into a shell, then wrap as a solid with fixed orientation."""
    sewing = BRepBuilderAPI_Sewing(1e-3)
    for f in faces:
        sewing.Add(f)
    sewing.Perform()
    sewn = sewing.SewedShape()

    builder = BRep_Builder()
    solid = TopoDS_Solid()
    builder.MakeSolid(solid)

    explorer = TopExp_Explorer(sewn, TopAbs_SHELL)
    while explorer.More():
        builder.Add(solid, TopoDS.Shell_s(explorer.Current()))
        explorer.Next()

    if not TopExp_Explorer(solid, TopAbs_SHELL).More():
        shell = TopoDS_Shell()
        builder.MakeShell(shell)
        face_exp = TopExp_Explorer(sewn, TopAbs_FACE)
        while face_exp.More():
            builder.Add(shell, face_exp.Current())
            face_exp.Next()
        builder.Add(solid, shell)

    fixer = ShapeFix_Solid()
    fixer.Init(solid)
    fixer.Perform()
    return fixer.Solid()


def _make_cap_face(curve: Geom_BSplineCurve, reverse: bool) -> "TopoDS_Face":
    """Make a planar face bounded by a BSpline curve."""
    c = curve.Reversed() if reverse else curve
    edge = BRepBuilderAPI_MakeEdge(c).Edge()
    wire = BRepBuilderAPI_MakeWire(edge).Wire()
    return BRepBuilderAPI_MakeFace(wire).Face()


# ---------------------------------------------------------------------------
# Public API: loft functions
# ---------------------------------------------------------------------------


def closed_bezier_loft(start, end):
    from OCP.Geom import Geom_RectangularTrimmedSurface

    curves = _unify_curves(
        [start.curve, start.control, end.control, end.curve]
    )
    surface = _build_surface(curves)

    # Split surface into sub-faces at V knots (one per polygon edge)
    v_knots = [surface.VKnot(i) for i in range(1, surface.NbVKnots() + 1)]
    loft_faces = []
    for i in range(len(v_knots) - 1):
        v1, v2 = v_knots[i], v_knots[i + 1]
        if v2 - v1 < 1e-10:
            continue
        trimmed = Geom_RectangularTrimmedSurface(surface, 0.0, 1.0, v1, v2)
        loft_faces.append(BRepBuilderAPI_MakeFace(trimmed, 1e-6).Face())

    cap_start = _make_cap_face(curves[0], reverse=True)
    cap_end = _make_cap_face(curves[3], reverse=False)
    solid = _sew_to_solid(loft_faces + [cap_start, cap_end])
    return cq.Workplane("XY").add(cq.Solid(solid))


# ---------------------------------------------------------------------------
# Curve builders
# ---------------------------------------------------------------------------


def circle_curve(
    center: tuple[float, float, float],
    normal: tuple[float, float, float],
    radius: float,
    start_reference: tuple[float, float, float] | None = None,
) -> Geom_BSplineCurve:
    """
    BSpline circle in 3D space, defined by a center, a normal, and a radius.
    Winds CCW when viewed from the direction the normal points toward
    (right-hand rule around the normal).

    Parameters
    ----------
    center : (x, y, z)
        Center of the circle.
    normal : (x, y, z)
        Normal of the circle's plane. Need not be unit length —
        normalized internally.
    radius : float
        Circle radius.
    start_reference : (x, y, z) or None, optional
        If provided, the curve is reparameterized so t=0 corresponds to
        the point on the circle nearest to this reference. The reference
        is projected onto the circle's plane and the direction from the
        center to that projected point determines the start angle.
        If the reference projects onto the center (ambiguous), the
        start direction is chosen arbitrarily.

    Returns
    -------
    Geom_BSplineCurve
    """
    # Normalize the normal
    nx, ny, nz = normal
    n_mag = math.sqrt(nx * nx + ny * ny + nz * nz)
    if n_mag < 1e-12:
        raise ValueError("Normal vector cannot be zero")
    nx, ny, nz = nx / n_mag, ny / n_mag, nz / n_mag

    cx, cy, cz = center

    # Determine the X direction of the circle's local frame
    if start_reference is None:
        # Pick an arbitrary direction perpendicular to the normal.
        # Use whichever world axis is least aligned with the normal
        # as a seed, then orthogonalize.
        if abs(nx) < abs(ny) and abs(nx) < abs(nz):
            seed = (1.0, 0.0, 0.0)
        elif abs(ny) < abs(nz):
            seed = (0.0, 1.0, 0.0)
        else:
            seed = (0.0, 0.0, 1.0)
        # x_dir = seed - (seed . n) * n, then normalize
        dot = seed[0] * nx + seed[1] * ny + seed[2] * nz
        xx = seed[0] - dot * nx
        xy = seed[1] - dot * ny
        xz = seed[2] - dot * nz
    else:
        # Project (reference - center) onto the circle's plane
        rx = start_reference[0] - cx
        ry = start_reference[1] - cy
        rz = start_reference[2] - cz
        dot = rx * nx + ry * ny + rz * nz
        xx = rx - dot * nx
        xy = ry - dot * ny
        xz = rz - dot * nz

    x_mag = math.sqrt(xx * xx + xy * xy + xz * xz)
    if x_mag < 1e-12:
        # Ambiguous (reference on the normal axis through center);
        # fall back to an arbitrary perpendicular direction
        if abs(nx) < abs(ny) and abs(nx) < abs(nz):
            seed = (1.0, 0.0, 0.0)
        elif abs(ny) < abs(nz):
            seed = (0.0, 1.0, 0.0)
        else:
            seed = (0.0, 0.0, 1.0)
        dot = seed[0] * nx + seed[1] * ny + seed[2] * nz
        xx = seed[0] - dot * nx
        xy = seed[1] - dot * ny
        xz = seed[2] - dot * nz
        x_mag = math.sqrt(xx * xx + xy * xy + xz * xz)

    xx, xy, xz = xx / x_mag, xy / x_mag, xz / x_mag

    axis = gp_Ax2(gp_Pnt(cx, cy, cz), gp_Dir(nx, ny, nz), gp_Dir(xx, xy, xz))
    circle = Geom_Circle(axis, radius)
    bs = GeomConvert.CurveToBSplineCurve_s(circle)
    bs.Segment(0, 2 * math.pi)
    return bs


def _build_closed_piecewise_linear(
    points: list[tuple[float, float, float]],
) -> Geom_BSplineCurve:
    """
    Build a closed degree-1 BSpline from a list of points.
    n points produce n segments. The last point connects back to the first.
    Each segment occupies an equal share (1/n) of the parameter range,
    regardless of physical segment length. This means longer segments
    are traversed "faster" in world space per unit of parameter, but
    parameter progress is uniform across segments.

    Parameters
    ----------
    points : list of (x, y, z) tuples, length >= 3

    Returns
    -------
    Geom_BSplineCurve
        Closed, degree-1 BSpline parameterized uniformly over segments.
    """
    n = len(points)
    if n < 3:
        raise ValueError(f"Need at least 3 points, got {n}")

    # n+1 poles: the n points plus a repeat of the first to close
    gp_pts = [gp_Pnt(*p) for p in points]
    gp_pts.append(gp_Pnt(*points[0]))

    poles_arr = TColgp_Array1OfPnt(1, n + 1)
    for i, p in enumerate(gp_pts):
        poles_arr.SetValue(i + 1, p)

    # Uniform knot spacing: each segment gets 1/n of the [0, 1] range
    n_knots = n + 1
    knots = TColStd_Array1OfReal(1, n_knots)
    mults = TColStd_Array1OfInteger(1, n_knots)
    for i in range(n_knots):
        knots.SetValue(i + 1, i / n)
    # Clamped: first and last mult = degree + 1 = 2
    mults.SetValue(1, 2)
    for i in range(2, n_knots):
        mults.SetValue(i, 1)
    mults.SetValue(n_knots, 2)

    return Geom_BSplineCurve(poles_arr, knots, mults, 1, False)


def _nearest_point_on_segment(
    p: tuple[float, float, float],
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float]:
    """
    Find the nearest point on segment a->b to the reference point p.

    Returns (f, dist_sq) where f is the parameter along the segment
    in [0, 1] and dist_sq is the squared distance from p to that point.
    """
    ax, ay, az = a
    bx, by, bz = b
    px, py, pz = p

    # Direction along segment
    dx = bx - ax
    dy = by - ay
    dz = bz - az

    seg_len_sq = dx * dx + dy * dy + dz * dz
    if seg_len_sq < 1e-24:
        # Degenerate segment; nearest point is the start
        ddx = px - ax
        ddy = py - ay
        ddz = pz - az
        return 0.0, ddx * ddx + ddy * ddy + ddz * ddz

    # Project (p - a) onto (b - a)
    t = ((px - ax) * dx + (py - ay) * dy + (pz - az) * dz) / seg_len_sq
    # Clamp to segment
    t = max(0.0, min(1.0, t))

    # Nearest point
    nx = ax + t * dx
    ny = ay + t * dy
    nz = az + t * dz

    ddx = px - nx
    ddy = py - ny
    ddz = pz - nz

    return t, ddx * ddx + ddy * ddy + ddz * ddz


def _reorder_polygon(
    points: list[tuple[float, float, float]],
    tangents: list[tuple[float, float, float]],
    start_reference: tuple[float, float, float],
) -> tuple[list[tuple[float, float, float]], list[tuple[float, float, float]]]:
    """
    Reorder (and possibly split) a closed polygon so the curve starts at
    the point on the polygon boundary nearest to a reference point.

    The start location is fully geometric — it does not depend on the
    cyclic ordering of the input vertex list. Any rotation of the input
    points will produce the same final curve.

    Parameters
    ----------
    points : list of (x, y, z)
    tangents : list of (x, y, z)
    start_reference : (x, y, z)
        Reference point. The nearest point on the polygon boundary
        becomes the new start of the curve.

    Returns
    -------
    (new_points, new_tangents)
    """
    n = len(points)

    # Find the segment and parameter that minimize distance to start_reference
    best_edge = 0
    best_f = 0.0
    best_dist_sq = float("inf")

    for k in range(n):
        a = points[k]
        b = points[(k + 1) % n]
        f, dist_sq = _nearest_point_on_segment(start_reference, a, b)
        if dist_sq < best_dist_sq:
            best_dist_sq = dist_sq
            best_edge = k
            best_f = f

    # If the nearest point is (nearly) on a vertex, just rotate to that vertex
    if best_f < 1e-10:
        idx = best_edge
        return points[idx:] + points[:idx], tangents[idx:] + tangents[:idx]
    if best_f > 1.0 - 1e-10:
        idx = (best_edge + 1) % n
        return points[idx:] + points[:idx], tangents[idx:] + tangents[:idx]

    # Insert a new vertex on the edge
    k = best_edge
    k2 = (k + 1) % n
    f = best_f

    mid_pt = (
        points[k][0] + f * (points[k2][0] - points[k][0]),
        points[k][1] + f * (points[k2][1] - points[k][1]),
        points[k][2] + f * (points[k2][2] - points[k][2]),
    )
    mid_tan = (
        tangents[k][0] + f * (tangents[k2][0] - tangents[k][0]),
        tangents[k][1] + f * (tangents[k2][1] - tangents[k][1]),
        tangents[k][2] + f * (tangents[k2][2] - tangents[k][2]),
    )

    # Build new list: start at the new midpoint, then go through
    # remaining vertices starting from k2 and wrapping around
    new_pts = [mid_pt]
    new_tans = [mid_tan]
    idx = k2
    for _ in range(n):
        new_pts.append(points[idx])
        new_tans.append(tangents[idx])
        idx = (idx + 1) % n
    # The final segment closes back to mid_pt (handled by
    # _build_closed_piecewise_linear)
    return new_pts, new_tans


def polygon_endpoint(
    points: list[tuple[float, float, float]],
    tangents: list[tuple[float, float, float]],
    start_reference: tuple[float, float, float] | None = None,
) -> BezierEndpoint:
    """
    Create a BezierEndpoint from a closed polygon with per-vertex tangent
    offsets.

    The boundary curve is a closed piecewise-linear BSpline through the
    given points. The control curve is a matching piecewise-linear BSpline
    whose poles are `point + tangent` per vertex (absolute positions of
    the inner Bezier control row at that boundary).

    Both curves share the same knot structure, so control(t) corresponds
    to the control point paired with curve(t).

    n points produce n line segments (the last connects back to the first).

    Parameters
    ----------
    points : list of (x, y, z) tuples, length >= 3
        Vertices of the polygon. Must wind CCW when viewed from outside
        the solid.
    tangents : list of (x, y, z) tuples, same length as points
        Offset from each vertex to its inner control point.
    start_reference : (x, y, z) or None, optional
        A reference point in 3D space. The curve will be reparameterized
        to start at the point on the polygon boundary nearest to this
        reference. If the nearest point falls on an edge (not a vertex),
        a new vertex with an interpolated tangent is inserted there.

        This is fully geometric — rotating the input vertex list does
        not change the resulting curve. Defaults to None (start at the
        first vertex).

    Returns
    -------
    BezierEndpoint
    """
    n = len(points)
    if n < 3:
        raise ValueError(f"Need at least 3 points, got {n}")
    if len(tangents) != n:
        raise ValueError(
            f"points and tangents must have same length, got {n} and {len(tangents)}"
        )

    if start_reference is not None:
        points, tangents = _reorder_polygon(points, tangents, start_reference)

    curve = _build_closed_piecewise_linear(points)

    # Control curve: same knot structure, poles at point + tangent
    n_out = len(points)
    ctrl_pts = [
        gp_Pnt(p[0] + t[0], p[1] + t[1], p[2] + t[2])
        for p, t in zip(points, tangents)
    ]
    ctrl_pts.append(
        gp_Pnt(
            points[0][0] + tangents[0][0],
            points[0][1] + tangents[0][1],
            points[0][2] + tangents[0][2],
        )
    )

    ctrl_poles = TColgp_Array1OfPnt(1, n_out + 1)
    for i, p in enumerate(ctrl_pts):
        ctrl_poles.SetValue(i + 1, p)

    n_knots = curve.NbKnots()
    ctrl_knots = TColStd_Array1OfReal(1, n_knots)
    ctrl_mults = TColStd_Array1OfInteger(1, n_knots)
    for i in range(1, n_knots + 1):
        ctrl_knots.SetValue(i, curve.Knot(i))
        ctrl_mults.SetValue(i, curve.Multiplicity(i))

    control_curve = Geom_BSplineCurve(
        ctrl_poles, ctrl_knots, ctrl_mults, 1, False
    )

    return BezierEndpoint(curve=curve, control=control_curve)


# ---------------------------------------------------------------------------
# Curve manipulation helpers
# ---------------------------------------------------------------------------


def offset_curve(
    curve: Geom_BSplineCurve,
    offset: tuple[float, float, float],
) -> Geom_BSplineCurve:
    """
    Copy a curve with all poles shifted by an offset vector.
    """
    result = curve.Copy()
    dx, dy, dz = offset
    for i in range(1, result.NbPoles() + 1):
        p = result.Pole(i)
        result.SetPole(i, gp_Pnt(p.X() + dx, p.Y() + dy, p.Z() + dz))
    return result


def scaled_curve(
    curve: Geom_BSplineCurve,
    sx: float = 1.0,
    sy: float = 1.0,
    sz: float = 1.0,
    center: tuple[float, float, float] = (0, 0, 0),
) -> Geom_BSplineCurve:
    """
    Copy a curve with poles scaled relative to a center point.
    """
    result = curve.Copy()
    cx, cy, cz = center
    for i in range(1, result.NbPoles() + 1):
        p = result.Pole(i)
        result.SetPole(
            i,
            gp_Pnt(
                cx + (p.X() - cx) * sx,
                cy + (p.Y() - cy) * sy,
                cz + (p.Z() - cz) * sz,
            ),
        )
    return result


import port


def circular_port_to_endpoint(
    port: port.CircularPort, start_reference, tangent_length: float = 1.0
) -> BezierEndpoint:
    """
    Build a BezierEndpoint for a circular port.

    The control curve is a circle parallel to the boundary, offset along
    the port's normal axis. The control sits at `curve - port.normal *
    tangent_length`, so a negative `tangent_length` offsets the control
    in the +normal direction (matching the prior end-side convention).
    """
    curve = circle_curve(port.center, port.normal, port.radius, start_reference)
    nx, ny, nz = port.normal
    offset = (
        -nx * tangent_length,
        -ny * tangent_length,
        -nz * tangent_length,
    )
    return BezierEndpoint(curve=curve, control=offset_curve(curve, offset))
