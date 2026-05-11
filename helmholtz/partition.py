import math


EPS = 1e-12
COS_135 = -math.sqrt(2) / 2


def split_at_edge(
    polygon, edge_index, fraction, gravity, min_dock_length, max_dock_length
):
    """Find a 2-segment cut path P -> M -> H that splits a convex CCW polygon
    into:

      - A non-convex CCW "cavity" piece (CCW from P along the polygon to H,
        then back to P via a bend at M; M is a reflex vertex of the cavity).
        Its area equals fraction * total area, and its portion of edge
        `edge_index` (the dock segment from P to polygon[edge_index + 1]) has
        length in [min_dock_length, max_dock_length].
      - A convex CCW "remainder" piece (polygon[edge_index] -> P -> M -> H ->
        polygon[k+1] -> ... -> polygon[edge_index]). The recursion continues
        on this piece, so the bend is placed on the cavity side of chord PH:
        M is reflex for the cavity and convex for the remainder.

    Each of the two cut segments (P -> M, M -> H) makes an angle of at least
    135 degrees with `gravity` (within 45 degrees of straight up-from-gravity).

    Among feasible cut paths, picks the one that maximises the minimum
    isoperimetric ratio of the two pieces -- i.e. both pieces are as round
    as possible.

    Returns (P, M, H, hit_edge_index). Raises ValueError if no feasible cut
    path exists under the combined constraints.
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

    N_P = 20
    N_H = 20

    best = None  # (score, P, M, H, k)

    for k_offset in range(1, n):
        k = (e + k_offset) % n
        edge_k_a = polygon[k]
        edge_k_b = polygon[(k + 1) % n]
        edge_k_vec = (edge_k_b[0] - edge_k_a[0], edge_k_b[1] - edge_k_a[1])

        between_pts = [polygon[(e + 1 + i) % n] for i in range(k_offset)]
        cw_count = (e - k - 1) % n
        after_h_pts = [polygon[(k + 1 + i) % n] for i in range(cw_count)]

        for ip in range(N_P + 1):
            tP = ip / N_P
            L = L_lo + tP * (L_hi - L_lo)
            sP = 1 - L / edge_len
            P = (a_e[0] + sP * edge_vec[0], a_e[1] + sP * edge_vec[1])

            for ih in range(1, N_H):
                tH = ih / N_H
                H = (
                    edge_k_a[0] + tH * edge_k_vec[0],
                    edge_k_a[1] + tH * edge_k_vec[1],
                )

                cavity_straight = [P] + between_pts + [H]
                A_straight = _signed_area(cavity_straight)
                if A_straight <= target + 1e-9:
                    continue

                ux = H[0] - P[0]
                uy = H[1] - P[1]
                u_len = math.hypot(ux, uy)
                if u_len < 1e-6:
                    continue

                # Cavity is the CCW piece, lying to the right of P->H. Right
                # perpendicular = inward normal into cavity.
                nx = uy / u_len
                ny = -ux / u_len
                beta = 2 * (A_straight - target) / u_len

                mid_x = (P[0] + H[0]) / 2
                mid_y = (P[1] + H[1]) / 2
                M = (mid_x + beta * nx, mid_y + beta * ny)

                if not _point_in_polygon(M, polygon):
                    continue

                if not _segment_gravity_ok(P, M, g_hat):
                    continue
                if not _segment_gravity_ok(M, H, g_hat):
                    continue

                # Remainder convexity: automatic at polygon[e] and polygon[k+1]
                # (original convex vertices, unaffected by the cut), at P (any
                # M inside the polygon lies on the interior side of the dock),
                # and at M (beta > 0 forces a left turn for the remainder).
                # Only H needs an explicit check.
                next_after_h = polygon[(k + 1) % n]
                if not _is_left_turn(M, H, next_after_h):
                    continue

                cavity_poly = cavity_straight + [M]
                remainder_poly = [a_e, P, M, H] + after_h_pts

                iso_c = _isoperimetric_ratio(cavity_poly)
                iso_r = _isoperimetric_ratio(remainder_poly)
                score = -min(iso_c, iso_r)

                if best is None or score < best[0]:
                    best = (score, P, M, H, k)

    if best is None:
        raise ValueError(
            f"no feasible 2-segment cut found for fraction {fraction} on "
            f"edge {edge_index}"
        )

    _, P, M, H, k = best
    return P, M, H, k


def partition_along_edge(polygon, edge_index, items, gravity, wall_strength=0.0):
    """Recursively split a convex CCW polygon along a single dock edge into
    sub-polygons using 2-segment cut paths.

    polygon       -- convex CCW polygon as a list of (x, y).
    edge_index    -- index of the dock edge.
    items         -- list of (fraction, min_dock_length) tuples. Fractions are
                     shares of the *original* polygon's area and must sum to 1.
                     min_dock_length is the absolute minimum length each
                     sub-polygon must occupy along the (remaining) dock edge.
    gravity       -- 2D vector indicating "down". Each cut segment satisfies
                     angle-to-gravity >= 135 deg.
    wall_strength -- if > 0, each pair of adjacent cells is separated by a wall
                     slab of this thickness. Cells are inset by wall_strength/2
                     on every cut-edge.

    Each cut produces a non-convex cavity (the cell) and a convex remainder
    (recursed on). Returns: list of n sub-polygons in the same order as
    `items`.
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

    P, M, H, hit_edge_index = split_at_edge(
        polygon, edge_index, relative_V, gravity, L_head, max_dock
    )
    cavity, remainder, new_edge_index = _split_polygon_2seg(
        polygon, edge_index, P, M, H, hit_edge_index
    )
    rest_cells, rest_cuts = _partition_recurse(
        remainder, new_edge_index, items_rest, gravity
    )
    return [cavity] + rest_cells, [(P, M, H)] + rest_cuts


def _split_polygon_2seg(polygon, edge_index, P, M, H, hit_edge_index):
    """Split a convex polygon by the 2-segment cut P -> M -> H. Returns
    (cavity, remainder, new_edge_index_in_remainder). Cavity is non-convex
    (reflex at M); remainder is convex. The remainder's dock-edge remnant
    (polygon[edge_index] -> P) is always at edge index 0.
    """
    n = len(polygon)
    e = edge_index
    k = hit_edge_index

    ccw_count = (k - e) % n
    cavity = (
        [P] + [polygon[(e + 1 + i) % n] for i in range(ccw_count)] + [H, M]
    )

    cw_count = (e - k - 1) % n
    remainder = (
        [polygon[e], P, M, H]
        + [polygon[(k + 1 + i) % n] for i in range(cw_count)]
    )
    return cavity, remainder, 0


def _inset_cut_edges(cell, cuts, offset):
    """Inset every cell-edge that lies on a cut segment by `offset` toward
    the cell interior; original polygon edges are left untouched. Each cut
    is (P, M, H) with two segments P->M and M->H.
    """
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
        for P_cut, M_cut, H_cut in cuts:
            for seg_start, seg_end in ((P_cut, M_cut), (M_cut, H_cut)):
                sx = seg_end[0] - seg_start[0]
                sy = seg_end[1] - seg_start[1]
                sl = math.hypot(sx, sy)
                if sl < 1e-12:
                    continue
                cn = (-sy / sl, sx / sl)
                d_a = (a[0] - seg_start[0]) * cn[0] + (a[1] - seg_start[1]) * cn[1]
                d_b = (b[0] - seg_start[0]) * cn[0] + (b[1] - seg_start[1]) * cn[1]
                if abs(d_a) < 1e-6 and abs(d_b) < 1e-6:
                    edge_offsets[i] = offset
                    break
            if edge_offsets[i] != 0.0:
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


def _signed_area(polygon):
    n = len(polygon)
    s = 0.0
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def _polygon_perimeter(polygon):
    n = len(polygon)
    p = 0.0
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        p += math.hypot(x2 - x1, y2 - y1)
    return p


def _isoperimetric_ratio(polygon):
    A = abs(_signed_area(polygon))
    P = _polygon_perimeter(polygon)
    if P < EPS:
        return 0.0
    return 4 * math.pi * A / (P * P)


def _point_in_polygon(point, polygon):
    x, y = point
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if (yi > y) != (yj > y):
            x_intersect = xi + (y - yi) * (xj - xi) / (yj - yi)
            if x < x_intersect:
                inside = not inside
        j = i
    return inside


def _segment_gravity_ok(A, B, g_hat):
    dx = B[0] - A[0]
    dy = B[1] - A[1]
    seg_len = math.hypot(dx, dy)
    if seg_len < EPS:
        return False
    dot = (dx * g_hat[0] + dy * g_hat[1]) / seg_len
    return dot <= COS_135 + 1e-9


def _is_left_turn(a, b, c, tol=1e-9):
    return (
        (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
    ) >= -tol
