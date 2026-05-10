import math

C_SOUND_MM = 343_000.0  # mm/s


def helmholtz_volume_mm(f_hz, A_mm2, L_mm):
    """Volume [mm^3] for target frequency f [Hz] given neck area [mm^2] and length [mm]."""
    r_mm = math.sqrt(A_mm2 / math.pi)
    L_eff = L_mm + 1.7 * r_mm  # end correction
    omega = 2 * math.pi * f_hz
    return (C_SOUND_MM**2) * A_mm2 / (omega**2 * L_eff)


def _neck_for_volume(f_hz, V_mm3, A_min_mm2, L_min_mm):
    """Pick (A, L) so the resonator hits f_hz with cavity V_mm3, respecting minima.

    Try L = L_min and solve for A. If that drives A below A_min, pin A = A_min
    and solve for L instead.
    """
    omega = 2 * math.pi * f_hz
    # Solve c^2 * s^2 - B * s - omega^2 * V * L_min = 0, with s = sqrt(A),
    # which encodes the end correction L_eff = L + 1.7 * sqrt(A/pi).
    B = 1.7 * omega**2 * V_mm3 / math.sqrt(math.pi)
    disc = B**2 + 4 * C_SOUND_MM**2 * omega**2 * V_mm3 * L_min_mm
    s = (B + math.sqrt(disc)) / (2 * C_SOUND_MM**2)
    A = s**2
    if A >= A_min_mm2:
        return A, L_min_mm
    A = A_min_mm2
    r = math.sqrt(A / math.pi)
    L = C_SOUND_MM**2 * A / (omega**2 * V_mm3) - 1.7 * r
    return A, L


def resonator_array_linear(f1, f2, n, A_min_mm2, L_min_mm, V_total_mm3):
    """Linearly-spaced resonator frequencies over [f1, f2] with a fixed total cavity volume.

    V_total is allocated across the n resonators in proportion to each
    resonator's natural volume at (A_min, L_min) -- so low-f cavities get the
    larger share. Per-resonator A and L are then chosen to hit f_i (preferring
    L = L_min, raising A; if that would push A below A_min, A is pinned and L
    grows instead).

    Uniform density in Hz -> flat dB envelope in the large-n limit
    (with Lorentzian tails at the band edges).
    """
    if n == 1:
        fs = [(f1 + f2) / 2]
    else:
        fs = [f1 + (f2 - f1) * i / (n - 1) for i in range(n)]
    V_natural = [helmholtz_volume_mm(f, A_min_mm2, L_min_mm) for f in fs]
    scale = V_total_mm3 / sum(V_natural)
    Vs = [v * scale for v in V_natural]
    Rs = []
    for f_i, V_i in zip(fs, Vs):
        A_i, L_i = _neck_for_volume(f_i, V_i, A_min_mm2, L_min_mm)
        Rs.append((1, A_i, L_i, V_i))
    return Rs
