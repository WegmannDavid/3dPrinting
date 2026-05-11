import math

from scipy.optimize import brentq, minimize_scalar


EPS = 1e-12
COS_135 = -math.sqrt(2) / 2


def split_at_edge(
    polygon, edge_index, fraction, gravity, min_dock_length, max_dock_length
):
    """Find a dock point on edge `edge_index` and a cut angle that split a
    convex CCW polygon into two pieces:

      - The piece bounded by polygon edges going CCW from the dock point has
        area = fraction * total area.
      - That piece's portion of edge `edge_index` (the segment from the dock
        point to polygon[edge_index + 1]) has length in
        [min_dock_length, max_dock_length].
      - The cut direction makes an angle of at least 135 degrees with `gravity`
        (within 45 degrees of straight up-from-gravity).

    Returns (dock_point, angle):
      dock_point -- (x, y) tuple on edge `edge_index`.
      angle      -- cut direction in radians (atan2 convention).

    Raises ValueError if no feasible (dock_point, angle) exists under the
    combined area, gravity, and dock-length constraints.
    """
    if not (0 < fraction < 1):
        raise ValueError(f"fraction must be in (0, 1), got {fraction}")
    if min_dock_length < 0 or max_dock_length < 0:
        raise ValueError("dock lengths must be non-negative")
    if min_dock_length > max_dock_length:
        raise ValueError(
            f"min_dock_length ({min_dock_length}) > max_dock_length ({max_dock_length})"
        )

    g_mag = math.hypot(gravity[0], gravity[1])
    if g_mag == 0:
        raise ValueError("gravity must be non-zero")
    g_hat = (gravity[0] / g_mag, gravity[1] / g_mag)

    n = len(polygon)
    A_total = _signed_area(polygon)
    if A_total <= 0:
        raise ValueError("polygon must be CCW with positive area")
    target = fraction * A_total

    e = edge_index
    a_e = polygon[e]
    b_e = polygon[(e + 1) % n]
    edge_vec = (b_e[0] - a_e[0], b_e[1] - a_e[1])
    edge_len = math.hypot(edge_vec[0], edge_vec[1])

    L_lo = max(EPS, min_dock_length)
    L_hi = min(edge_len - EPS, max_dock_length)
    if L_lo > L_hi:
        raise ValueError(
            f"dock length range [{min_dock_length}, {max_dock_length}] "
            f"does not fit edge of length {edge_len:.4f}"
        )

    # Interior cone at any interior point of edge e is the 180-deg half-plane
    # on the polygon-interior side of the edge.
    theta0 = math.atan2(edge_vec[1], edge_vec[0])
    sweep = math.pi

    def gravity_constraint(t):
        theta = theta0 + t * sweep
        return math.cos(theta) * g_hat[0] + math.sin(theta) * g_hat[1] - COS_135

    t_g_lo, t_g_hi = _valid_t_range(gravity_constraint)
    if t_g_lo is None:
        raise ValueError(
            "no cut direction from this edge satisfies the 135-deg gravity constraint"
        )
    theta_g_lo = theta0 + t_g_lo * sweep
    theta_g_hi = theta0 + t_g_hi * sweep

    def area_at(L, theta):
        s = 1.0 - L / edge_len
        return _ccw_piece_area_from_edge(polygon, e, s, theta)

    # For fixed theta, the CCW-piece area is monotone increasing in L (moving
    # the dock toward polygon[e] enlarges the piece). So the achievable area
    # range at dock-length L is [area_at(L, theta_g_lo), area_at(L, theta_g_hi)],
    # itself sliding upward as L grows. The L sub-range where target is
    # bracketable is therefore an interval, found by two scalar root-finds.
    A_lo_at_Llo = area_at(L_lo, theta_g_lo)
    A_hi_at_Llo = area_at(L_lo, theta_g_hi)
    A_lo_at_Lhi = area_at(L_hi, theta_g_lo)
    A_hi_at_Lhi = area_at(L_hi, theta_g_hi)

    if target < A_lo_at_Llo - 1e-9 or target > A_hi_at_Lhi + 1e-9:
        f_min = A_lo_at_Llo / A_total
        f_max = A_hi_at_Lhi / A_total
        raise ValueError(
            f"fraction {fraction} unreachable on edge {e} with dock length in "
            f"[{min_dock_length}, {max_dock_length}] and gravity constraint; "
            f"feasible fraction range = [{f_min:.4f}, {f_max:.4f}]"
        )

    if A_hi_at_Llo >= target:
        L_feas_lo = L_lo
    else:
        L_feas_lo = brentq(lambda L: area_at(L, theta_g_hi) - target, L_lo, L_hi)

    if A_lo_at_Lhi <= target:
        L_feas_hi = L_hi
    else:
        L_feas_hi = brentq(lambda L: area_at(L, theta_g_lo) - target, L_lo, L_hi)

    # Within the feasible L interval, area = target gives a 1-parameter family
    # of (L, theta) solutions. Pick the one that minimises the cut length.
    def cut_length_at(L_try):
        try:
            theta_try = brentq(
                lambda th: area_at(L_try, th) - target,
                theta_g_lo,
                theta_g_hi,
                xtol=1e-10,
            )
        except ValueError:
            return float("inf")
        s_try = 1.0 - L_try / edge_len
        P_try = (a_e[0] + s_try * edge_vec[0], a_e[1] + s_try * edge_vec[1])
        d = (math.cos(theta_try), math.sin(theta_try))
        for offset in range(1, n):
            idx = (e + offset) % n
            a_seg = polygon[idx]
            b_seg = polygon[(idx + 1) % n]
            hit_pt = _ray_segment_intersect(P_try, d, a_seg, b_seg)
            if hit_pt is not None:
                return math.hypot(hit_pt[0] - P_try[0], hit_pt[1] - P_try[1])
        return float("inf")

    span = L_feas_hi - L_feas_lo
    if span <= 1e-9:
        L = (L_feas_lo + L_feas_hi) / 2
    else:
        # Margin avoids the degenerate endpoints where brentq is at the boundary.
        margin = max(1e-9, span * 1e-6)
        res = minimize_scalar(
            cut_length_at,
            bounds=(L_feas_lo + margin, L_feas_hi - margin),
            method="bounded",
            options={"xatol": max(1e-9, span * 1e-6)},
        )
        L = res.x

    theta = brentq(
        lambda th: area_at(L, th) - target, theta_g_lo, theta_g_hi, xtol=1e-12
    )
    s = 1.0 - L / edge_len
    P = (a_e[0] + s * edge_vec[0], a_e[1] + s * edge_vec[1])
    return P, math.atan2(math.sin(theta), math.cos(theta))


def partition_along_edge(polygon, edge_index, items, gravity, wall_strength=0.0):
    """Recursively split a convex CCW polygon along a single dock edge into
    sub-polygons.

    polygon       -- convex CCW polygon as a list of (x, y).
    edge_index    -- index of the dock edge.
    items         -- list of (fraction, min_dock_length) tuples. Fractions are
                     shares of the *original* polygon's area and must sum to 1.
                     min_dock_length is the absolute minimum length each
                     sub-polygon must occupy along the (remaining) dock edge.
    gravity       -- 2D vector indicating "down". Each cut direction satisfies
                     angle-to-gravity >= 135 deg.
    wall_strength -- if > 0, each pair of adjacent cells is separated by a wall
                     slab of this thickness. Cells are inset by wall_strength/2
                     on every cut-edge (original polygon edges are unchanged).
                     Cell areas are reduced by their adjacent half-wall slabs;
                     they are no longer exactly V_i * A_total but the cells no
                     longer touch.

    Returns: list of n sub-polygons in the same order as `items`. Each is a
    list of (x, y) vertices.

    Raises ValueError if the sum of min dock lengths exceeds the dock edge,
    or if any individual cut is infeasible under the gravity / dock / area
    constraints.
    """
    if not items:
        return []
    fractions = [v for v, _ in items]
    if abs(sum(fractions) - 1.0) > 1e-9:
        raise ValueError(f"fractions must sum to 1, got {sum(fractions)}")
    if any(v <= 0 for v in fractions):
        raise ValueError("fractions must be positive")
    if any(L < 0 for _, L in items):
        raise ValueError("min dock lengths must be non-negative")
    if wall_strength < 0:
        raise ValueError("wall_strength must be non-negative")

    # Compensate min_dock_length for wall-inset shrinkage of the dock segment.
    # Each adjacent cut shortens its cell's dock end by ~wall_strength/2 (more
    # at oblique cut angles; this is the perpendicular-cut estimate). End cells
    # have one cut-adjacent dock endpoint, middle cells have two.
    if wall_strength > 0 and len(items) > 1:
        last = len(items) - 1
        items = [
            (V, L + (1 if i in (0, last) else 2) * wall_strength)
            for i, (V, L) in enumerate(items)
        ]

    n = len(polygon)
    a_e = polygon[edge_index]
    b_e = polygon[(edge_index + 1) % n]
    edge_len = math.hypot(b_e[0] - a_e[0], b_e[1] - a_e[1])
    total_min_dock = sum(L for _, L in items)
    if total_min_dock > edge_len + 1e-9:
        raise ValueError(
            f"sum of min dock lengths ({total_min_dock}) exceeds dock edge "
            f"length ({edge_len:.4f})"
        )

    cells, cuts = _partition_recurse(polygon, edge_index, items, gravity)

    if wall_strength > 0:
        cells = [_inset_cut_edges(cell, cuts, wall_strength / 2) for cell in cells]

    return cells


def _partition_recurse(polygon, edge_index, items, gravity):
    if len(items) == 1:
        return [polygon], []

    V_head, L_head = items[0]
    items_rest = items[1:]

    n = len(polygon)
    a_e = polygon[edge_index]
    b_e = polygon[(edge_index + 1) % n]
    edge_len = math.hypot(b_e[0] - a_e[0], b_e[1] - a_e[1])

    future_min_dock = sum(L for _, L in items_rest)
    max_dock = edge_len - future_min_dock

    remaining_V = sum(v for v, _ in items)
    relative_V = V_head / remaining_V

    P, theta = split_at_edge(
        polygon, edge_index, relative_V, gravity, L_head, max_dock
    )
    ccw_piece, cw_piece, new_edge_index = _split_polygon_with_dock(
        polygon, edge_index, P, theta
    )
    rest_cells, rest_cuts = _partition_recurse(
        cw_piece, new_edge_index, items_rest, gravity
    )
    return [ccw_piece] + rest_cells, [(P, theta)] + rest_cuts


def _inset_cut_edges(cell, cuts, offset):
    """Inset every cell-edge that lies on a cut centerline by `offset` toward
    the cell interior; original polygon edges are left untouched. Returns the
    new vertex list."""
    n = len(cell)
    edge_offsets = [0.0] * n
    edge_dirs = [(1.0, 0.0)] * n
    for i in range(n):
        a = cell[i]
        b = cell[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L < 1e-12:
            continue
        edge_dirs[i] = (dx / L, dy / L)
        for P_cut, theta_cut in cuts:
            cn = (-math.sin(theta_cut), math.cos(theta_cut))
            d_a = (a[0] - P_cut[0]) * cn[0] + (a[1] - P_cut[1]) * cn[1]
            d_b = (b[0] - P_cut[0]) * cn[0] + (b[1] - P_cut[1]) * cn[1]
            if abs(d_a) < 1e-6 and abs(d_b) < 1e-6:
                edge_offsets[i] = offset
                break

    new_verts = []
    for i in range(n):
        prev_i = (i - 1) % n
        v1 = edge_dirs[prev_i]
        v2 = edge_dirs[i]
        n1 = (-v1[1], v1[0])  # CCW polygon: left normal points inward
        n2 = (-v2[1], v2[0])
        a1 = (
            cell[i][0] + edge_offsets[prev_i] * n1[0],
            cell[i][1] + edge_offsets[prev_i] * n1[1],
        )
        a2 = (
            cell[i][0] + edge_offsets[i] * n2[0],
            cell[i][1] + edge_offsets[i] * n2[1],
        )
        det = -v1[0] * v2[1] + v1[1] * v2[0]
        if abs(det) < 1e-12:
            new_verts.append(a1)
        else:
            rhs_x = a2[0] - a1[0]
            rhs_y = a2[1] - a1[1]
            s = (rhs_y * v2[0] - rhs_x * v2[1]) / det
            new_verts.append((a1[0] + s * v1[0], a1[1] + s * v1[1]))
    return new_verts


def _split_polygon_with_dock(polygon, edge_index, P, theta):
    """Split a convex polygon by the cut from P at angle theta into
    (ccw_piece, cw_piece). Return the edge index in cw_piece of the original
    dock-edge remnant (the segment from polygon[edge_index] to P)."""
    n = len(polygon)
    e = edge_index
    d = (math.cos(theta), math.sin(theta))
    hit = None
    k = None
    for offset in range(1, n):
        idx = (e + offset) % n
        a = polygon[idx]
        b = polygon[(idx + 1) % n]
        h = _ray_segment_intersect(P, d, a, b)
        if h is not None:
            hit = h
            k = idx
            break
    if hit is None:
        raise RuntimeError(f"ray missed polygon at theta={theta}")

    ccw_count = (k - e) % n
    cw_count = (e - k) % n
    ccw = [P] + [polygon[(e + 1 + i) % n] for i in range(ccw_count)] + [hit]
    cw = [hit] + [polygon[(k + 1 + i) % n] for i in range(cw_count)] + [P]
    # In cw, polygon[e] sits at index cw_count, P at index cw_count + 1, so
    # the dock-edge remnant is the edge between them.
    return ccw, cw, cw_count


def _valid_t_range(constraint, samples=2001):
    ts = [i / (samples - 1) for i in range(samples)]
    valid = [constraint(t) <= EPS for t in ts]
    if not any(valid):
        return None, None
    first = next(i for i, ok in enumerate(valid) if ok)
    last = samples - 1 - next(i for i, ok in enumerate(reversed(valid)) if ok)
    t_lo = (
        _refine_boundary(constraint, ts[first - 1], ts[first]) if first > 0 else 0.0
    )
    t_hi = (
        _refine_boundary(constraint, ts[last + 1], ts[last])
        if last < samples - 1
        else 1.0
    )
    return t_lo, t_hi


def _refine_boundary(constraint, t_invalid, t_valid, iters=60):
    for _ in range(iters):
        mid = (t_invalid + t_valid) / 2
        if constraint(mid) > 0:
            t_invalid = mid
        else:
            t_valid = mid
    return t_valid


def _signed_area(polygon):
    n = len(polygon)
    s = 0.0
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def _ccw_piece_area_from_edge(polygon, e, s, theta):
    n = len(polygon)
    a_e = polygon[e]
    b_e = polygon[(e + 1) % n]
    P = (a_e[0] + s * (b_e[0] - a_e[0]), a_e[1] + s * (b_e[1] - a_e[1]))
    d = (math.cos(theta), math.sin(theta))
    for offset in range(1, n):
        idx = (e + offset) % n
        a = polygon[idx]
        b = polygon[(idx + 1) % n]
        hit = _ray_segment_intersect(P, d, a, b)
        if hit is None:
            continue
        verts = [P] + [polygon[(e + 1 + i) % n] for i in range(offset)] + [hit]
        return _signed_area(verts)
    raise RuntimeError(f"no ray-edge intersection for theta={theta}")


def _ray_segment_intersect(origin, direction, a, b):
    """Intersect ray origin + t*direction (t >= 0) with segment a + s*(b-a),
    s in [0, 1]. Returns hit point or None."""
    ox, oy = origin
    dx, dy = direction
    ex, ey = b[0] - a[0], b[1] - a[1]
    det = -dx * ey + ex * dy
    if abs(det) < 1e-15:
        return None
    rx, ry = a[0] - ox, a[1] - oy
    t = (-rx * ey + ex * ry) / det
    s = (dx * ry - rx * dy) / det
    if t < -1e-12 or s < -1e-12 or s > 1 + 1e-12:
        return None
    return (ox + t * dx, oy + t * dy)
