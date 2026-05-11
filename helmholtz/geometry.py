import math

import cadquery as cq

import shapes
import helmholtz.array
import helmholtz.partition


WIDTH = 50
RESONATOR_DEPTH = 50
DUCT_DEPTH = 5


def neck(A, L):
    """Neck with cross-sectional area A [mm^2] and length L [mm].
    Occupies y in [0, L], centred on x=0, z=0.
    """
    side = math.sqrt(A)
    return (
        shapes.box(side, L, side, centered=True).translate((0, L / 2, 0))
        # .rotate((0, 0, 0), (0, 1, 0), 45)
    )


def resonator_height(V):
    return V / (WIDTH * RESONATOR_DEPTH)


def resonator(N, A_n, L, V):
    """Helmholtz resonator: N parallel necks of area A_n, length L, into a slab cavity.
    Necks are evenly spaced along the duct width at x = WIDTH * (k + 0.5) / N.
    """
    height = resonator_height(V)
    cavity = shapes.box(WIDTH, RESONATOR_DEPTH, height).translate((0, L, 0))
    result = cavity
    for k in range(N):
        x_k = WIDTH * (k + 0.5) / N
        result = result.union(neck(A_n, L).translate((x_k, 0, height / 2)))
    return result


def ductWithResonators(Rs):
    DUCT_HEIGHT = sum(resonator_height(V) + 1.0 for _, _, _, V in Rs)

    result = shapes.box(WIDTH, DUCT_DEPTH, DUCT_HEIGHT).translate((0, -DUCT_DEPTH, 0))

    offset = 0
    for N, A_n, L, V in Rs:
        x = offset
        # Shift neck down slightly so it clearly intersects the duct wall
        result = result.union(resonator(N, A_n, L, V).translate((0, 0, x)))
        offset += resonator_height(V) + 1.0

    return result


def cavity_array(
    polygon,
    extrusion_depth,
    gravity,
    f1,
    f2,
    n_cavities,
    neck_length,
    dock_edge_index,
    wall_strength=0.0,
    min_dock_length=0.0,
    A_min_mm2=3.0,
    workplane="XY",
):
    """Build the 3D Helmholtz cavity array (cavities + necks) from a 2D
    footprint polygon.

    polygon          -- 2D CCW polygon (list of (x, y) [mm]).
    extrusion_depth  -- depth (mm) to extrude the cavities along the workplane
                        normal.
    gravity          -- 2D gravity vector in the polygon's plane. Cuts run
                        within 45 deg of -gravity, and each neck is placed at
                        the gravity-low end of its cavity's dock face.
    f1, f2           -- frequency band [Hz]; cavity frequencies are linearly
                        spaced from f1 to f2.
    n_cavities       -- number of cavities.
    neck_length      -- nominal neck length L [mm].
    dock_edge_index  -- index of the polygon edge along which cavities dock.
    wall_strength    -- thickness (mm) of walls separating adjacent cavities.
    min_dock_length  -- minimum length each cavity occupies along the dock.
    A_min_mm2        -- minimum neck cross-section.
    workplane        -- cadquery workplane string ("XY" / "YZ" / "XZ") that
                        the polygon lies on. Necks are extruded in the
                        workplane and centred along its normal axis.

    Returns a cadquery Workplane containing one (cavity union neck) solid per
    cavity. Necks are axis-aligned squares (side = sqrt(A_n)), centred along
    the extrusion axis, pointed outward through the dock edge.
    """
    poly = list(polygon)
    polygon_area = abs(_signed_area(poly))
    V_total = polygon_area * extrusion_depth

    Rs = helmholtz.array.resonator_array_linear(
        f1=f1,
        f2=f2,
        n=n_cavities,
        A_min_mm2=A_min_mm2,
        L_min_mm=neck_length,
        V_total_mm3=V_total,
    )
    items = [
        (V / V_total, max(min_dock_length, math.sqrt(A_n)))
        for _, A_n, _, V in Rs
    ]

    cells = helmholtz.partition.partition_along_edge(
        poly, dock_edge_index, items, gravity, wall_strength
    )

    n_poly = len(poly)
    a_e = poly[dock_edge_index]
    b_e = poly[(dock_edge_index + 1) % n_poly]
    edge_vec = (b_e[0] - a_e[0], b_e[1] - a_e[1])
    edge_len = math.hypot(edge_vec[0], edge_vec[1])
    n_out = (edge_vec[1] / edge_len, -edge_vec[0] / edge_len)

    g_mag = math.hypot(gravity[0], gravity[1])
    g_hat = (gravity[0] / g_mag, gravity[1] / g_mag)

    result = cq.Workplane()
    for cell, (_, A_n, L_n, _) in zip(cells, Rs):
        cell_clean = _dedup_vertices(cell)
        if len(cell_clean) < 3:
            continue
        cavity = shapes.extrudePolygon(cell_clean, workplane, extrusion_depth)

        neck_solid = _make_neck(
            cell_clean, a_e, b_e, n_out, g_hat, A_n, L_n,
            extrusion_depth, workplane,
        )
        if neck_solid is not None:
            cavity = cavity.union(neck_solid)

        result = result.add(cavity)
    return result


_NORMAL_AXIS = {"XY": (0, 0, 1), "YZ": (1, 0, 0), "XZ": (0, 1, 0)}


def _make_neck(cell, a_e, b_e, n_out, g_hat, A_n, L_n, extrusion_depth, workplane):
    """Build the neck box for one cavity. Returns a Workplane or None if no
    valid placement exists (no dock-edge segment, neck too large to fit, etc.)."""
    dock_seg = _find_dock_segment(cell, a_e, b_e)
    if dock_seg is None:
        return None
    p1, p2 = dock_seg
    proj1 = p1[0] * g_hat[0] + p1[1] * g_hat[1]
    proj2 = p2[0] * g_hat[0] + p2[1] * g_hat[1]
    lowest_pt, highest_pt = (p1, p2) if proj1 >= proj2 else (p2, p1)
    ddx = highest_pt[0] - lowest_pt[0]
    ddy = highest_pt[1] - lowest_pt[1]
    dd_len = math.hypot(ddx, ddy)
    if dd_len < 1e-9:
        return None
    dock_dir = (ddx / dd_len, ddy / dd_len)

    s_neck = math.sqrt(A_n)
    if s_neck > dd_len + 1e-9 or s_neck > extrusion_depth + 1e-9:
        return None

    neck_poly = [
        lowest_pt,
        (lowest_pt[0] + s_neck * dock_dir[0], lowest_pt[1] + s_neck * dock_dir[1]),
        (
            lowest_pt[0] + s_neck * dock_dir[0] + L_n * n_out[0],
            lowest_pt[1] + s_neck * dock_dir[1] + L_n * n_out[1],
        ),
        (lowest_pt[0] + L_n * n_out[0], lowest_pt[1] + L_n * n_out[1]),
    ]
    if _signed_area(neck_poly) < 0:
        neck_poly = list(reversed(neck_poly))

    z_off = (extrusion_depth - s_neck) / 2
    nx, ny, nz = _NORMAL_AXIS[workplane]
    return shapes.extrudePolygon(neck_poly, workplane, s_neck).translate(
        (z_off * nx, z_off * ny, z_off * nz)
    )


def _find_dock_segment(cell, a_e, b_e):
    n = len(cell)
    for i in range(n):
        p1 = cell[i]
        p2 = cell[(i + 1) % n]
        if _on_segment(p1, a_e, b_e) and _on_segment(p2, a_e, b_e):
            return (p1, p2)
    return None


def _on_segment(p, a, b, tol=1e-6):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy)
    if L < 1e-12:
        return math.hypot(px - ax, py - ay) < tol
    t = ((px - ax) * dx + (py - ay) * dy) / (L * L)
    if t < -tol / L or t > 1 + tol / L:
        return False
    proj_x = ax + t * dx
    proj_y = ay + t * dy
    return math.hypot(px - proj_x, py - proj_y) < tol


def _signed_area(polygon):
    n = len(polygon)
    s = 0.0
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def _dedup_vertices(pts, tol=1e-9):
    out = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > tol:
            out.append(p)
    if (
        len(out) > 1
        and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= tol
    ):
        out.pop()
    return out


