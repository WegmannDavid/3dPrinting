from prelude import *
import math


def bellmouthAlongY(throatInnerRadius, throatRadius, depth):
    """
    Create the flow volume of a bellmouth inlet with a streamlined
    center-body cone, revolved about the Y axis.

    The returned solid is the region the air occupies — intended to be
    subtracted from a surrounding block to leave a bellmouth-shaped cavity
    with a streamlined cone on the centerline.

    Flow direction is (0, -1, 0): air enters at the wide upstream lip
    (y = +depth/2) and exits through the narrow throat (y = -depth/2).

    Geometry:
      * Throat (downstream end, y = -depth/2): annular flow region from
        r = throatInnerRadius (cone) to r = throatRadius (bellmouth wall).
        This is the only constrained cross-section.
      * Lip (upstream end, y = +depth/2): annular flow region from
        r = NOSE_FLARE_RATIO * throatInnerRadius (cone nose) to
        r = LIP_FLARE_RATIO * throatRadius (bellmouth lip). Both flares are
        sized for low loss using standard bellmouth proportions.
      * Bellmouth wall: cubic Bezier approximation of a quarter-ellipse,
        tangent radial at the lip and tangent axial at the throat.
      * Cone surface: cubic Bezier approximation of a quarter-ellipse,
        tangent radial at the nose (rounded, low-drag) and tangent axial
        at the throat (clean axial handoff to the impeller eye).

    Parameters
    ----------
    throatInnerRadius : float
        Cone radius at the throat plane. The hole in the middle of the
        annular throat — typically matched to the impeller hub.
    throatRadius : float
        Bellmouth radius at the throat plane (outer radius of the annular
        throat). Must be > throatInnerRadius.
    depth : float
        Axial length of the bellmouth along Y.

    Returns
    -------
    cq.Workplane
        A solid filling the annular flow region between the bellmouth wall
        and the center cone, centered on the origin so it spans
        y in [-depth/2, +depth/2].
    """
    assert (
        throatInnerRadius < throatRadius
    ), "throatInnerRadius must be less than throatRadius"

    # Cubic-Bezier quarter-ellipse handle factor: max radial error ≈ 0.027%.
    k = 0.5522847498307933

    # Derived radii at the lip plane.
    lipRadius = throatRadius + depth
    noseRadius = throatInnerRadius - depth

    # --- bellmouth wall curve (throat -> lip) in the (r, y) plane ---
    b_p0 = (throatRadius, -depth / 2.0)  # throat
    b_p3 = (lipRadius, depth / 2.0)  # lip
    b_a = depth  # axial semi-axis
    b_b = lipRadius - throatRadius  # radial semi-axis
    b_p1 = (throatRadius, -depth / 2.0 + k * b_a)  # tangent axial at throat
    b_p2 = (lipRadius - k * b_b, depth / 2.0)  # tangent radial at lip

    # --- cone surface curve (lip -> throat) in the (r, y) plane ---
    # Upstream (lip): rounded nose, tangent radial.
    # Downstream (throat): tangent axial, smooth handoff.
    c_p0 = (noseRadius, depth / 2.0)  # nose at lip plane
    c_p3 = (throatInnerRadius, -depth / 2.0)  # cone base at throat
    c_a = depth  # axial semi-axis
    c_b = noseRadius - throatInnerRadius  # radial semi-axis
    c_p1 = (noseRadius - k * c_b, depth / 2.0)  # tangent radial at nose
    c_p2 = (throatInnerRadius, -depth / 2.0 + k * c_a)  # tangent axial at throat

    # --- closed 2D profile in the XY plane (X = radial, Y = axial) ---
    # Counter-clockwise walk:
    #   throat outer (throatRadius, -d/2)
    #   --bellmouth Bezier-->  lip outer (lipRadius, +d/2)
    #   --lip face line-->     cone nose (noseRadius, +d/2)
    #   --cone Bezier-->       cone base (throatInnerRadius, -d/2)
    #   --throat face line-->  back to start
    profile = (
        cq.Workplane("XY")
        .moveTo(*b_p0)
        .bezier([b_p0, b_p1, b_p2, b_p3], includeCurrent=True)
        .lineTo(*c_p0)
        .bezier([c_p0, c_p1, c_p2, c_p3], includeCurrent=True)
        .close()
    )

    return profile.revolve(360, (0, 0, 0), (0, 1, 0))


def struts(r, depth, strength):
    import shapes

    s = shapes.box(r * 4, depth / 2, strength, centered=True).translate(
        (0, -depth / 4 + EPSILON, 0)
    )
    s1 = s.rotate((0, 0, 0), (0, 1, 0), 0)
    s2 = s.rotate((0, 0, 0), (0, 1, 0), 45)
    s3 = s.rotate((0, 0, 0), (0, 1, 0), 90)
    s4 = s.rotate((0, 0, 0), (0, 1, 0), 135)

    return s1.union(s2).union(s3).union(s4)


def bellmouthWithStruts(r1, r2, depth):
    c = bellmouthAlongY(r1, r2, depth)
    # s = struts(r2, depth, NOZZLE * 3)
    return c  # .cut(s)


def bellmouthWithStrutsByArea(r1, a, depth):
    r2 = math.sqrt(r1**2 + a / math.pi)
    return bellmouthWithStruts(r1, r2, depth)
