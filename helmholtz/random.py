"""
Broadband Helmholtz resonator panel — hole-size generator
==========================================================

Neck geometry (matches the CadQuery implementation)
----------------------------------------------------
Each neck is a cube of side `diameter` and length `depth`, rotated 45°
around the flow axis (Y).  This means:

  * The cross-section perpendicular to flow is a square of area  A = diameter²,
    oriented as a diamond (45°-rotated square) when viewed from the duct.
  * The cross-section is CONSTANT along the full depth — there is no taper or
    chamfer effect in the flow direction.
  * The footprint on the wall face is a square of side  diameter * sqrt(2),
    so grid cells must be at least that wide to avoid overlap.

Helmholtz resonance frequency
------------------------------
    f = (c / 2π) · √(A / (V · L_eff))

where
    A     = diameter²                          (neck cross-section area)
    V     = w · h · d_cavity                   (shared cavity volume)
    L_eff = depth + δ_total                    (effective neck length)
    δ_total = 1.7 · √(A/π) = 1.7/√π · a      (end correction, both ends,
                                                using equivalent-radius method)
"""

import numpy as np
from dataclasses import dataclass
from typing import Literal


@dataclass
class HelmholtzPanelParams:
    """
    Full specification for a broadband Helmholtz resonator panel.

    Panel geometry
    --------------
    w        : float   Panel width  [m]
    h        : float   Panel height [m]
    depth    : float   Neck / wall thickness [m]  (= `depth` in neck())
    d_cavity : float   Basotect cavity depth [m]

    Hole grid
    ---------
    n_holes : int    Total holes  (n_cols × n_rows)
    a_min   : float  Minimum neck side-length (= `diameter`) [m]
    a_max   : float  Maximum neck side-length [m]

    Target absorption band
    ----------------------
    f_low  : float   Lower frequency [Hz]
    f_high : float   Upper frequency [Hz]

    Distribution shape
    ------------------
    distribution : 'flat' | 'log' | 'bell'
        'flat'  — uniform density in Hz          (equal weight per frequency)
        'log'   — log-uniform / equal per octave (recommended for acoustics)
        'bell'  — triangular peak at band centre (emphasise a centre region)

    Physics
    -------
    c : float   Speed of sound [m/s], default 343.
    """
    w: float
    h: float
    depth: float
    d_cavity: float
    n_holes: int
    a_min: float
    a_max: float
    f_low: float
    f_high: float
    distribution: Literal["flat", "log", "bell"] = "log"
    c: float = 343.0

    def __post_init__(self):
        if self.a_max * 2**0.5 > min(self.w, self.h):
            raise ValueError(
                f"a_max={self.a_max*1e3:.1f} mm: diamond footprint "
                f"{self.a_max*2**0.5*1e3:.1f} mm exceeds panel dimensions."
            )


# ---------------------------------------------------------------------------
# Physics
# ---------------------------------------------------------------------------

_INV_SQRT_PI = 1.0 / np.sqrt(np.pi)


def _end_correction(a: np.ndarray) -> np.ndarray:
    """
    Total end correction (both ends) for a square orifice of side a.
    Uses equivalent-radius: r_eq = a / sqrt(π), so δ = 1.7 · a / sqrt(π).
    """
    return 1.7 * _INV_SQRT_PI * a


def hole_frequency(a: np.ndarray, params: HelmholtzPanelParams) -> np.ndarray:
    """
    Resonance frequency of a square neck of side `a`.

        f = (c / 2π) · √( a² / (V · (depth + 1.7/√π · a)) )

    Parameters
    ----------
    a      : neck side-length(s) [m], scalar or array
    params : HelmholtzPanelParams

    Returns
    -------
    f [Hz]
    """
    a = np.asarray(a, dtype=float)
    V = params.w * params.h * params.d_cavity
    L_eff = params.depth + _end_correction(a)
    return (params.c / (2.0 * np.pi)) * np.sqrt(a**2 / (V * L_eff))


def _side_for_frequency(f: np.ndarray, params: HelmholtzPanelParams) -> np.ndarray:
    """
    Invert the Helmholtz equation analytically.

    From  f² · (2π/c)² · V · (depth + α·a) = a²,  with α = 1.7/√π:

        a² − α·K·a − K·depth = 0,   K = (2πf/c)² · V

    Positive root:  a = (α·K + √(α²·K² + 4·K·depth)) / 2
    """
    f = np.asarray(f, dtype=float)
    alpha = 1.7 * _INV_SQRT_PI
    V = params.w * params.h * params.d_cavity
    K = (2.0 * np.pi * f / params.c) ** 2 * V

    disc = (alpha * K) ** 2 + 4.0 * K * params.depth
    return (alpha * K + np.sqrt(np.maximum(disc, 0.0))) / 2.0


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------

def _quantile_to_frequency(u: np.ndarray, params: HelmholtzPanelParams) -> np.ndarray:
    """Map uniform quantiles u ∈ [0, 1] to target frequencies."""
    fl, fh = params.f_low, params.f_high
    if params.distribution == "flat":
        return fl + u * (fh - fl)
    elif params.distribution == "log":
        return fl * (fh / fl) ** u
    elif params.distribution == "bell":
        fmid = 0.5 * (fl + fh)
        return np.where(
            u < 0.5,
            fl  + (fmid - fl) * np.sqrt(2.0 * u),
            fh  - (fh - fmid) * np.sqrt(2.0 * (1.0 - u)),
        )
    else:
        raise ValueError(
            f"Unknown distribution '{params.distribution}'. "
            "Choose 'flat', 'log', or 'bell'."
        )


def generate_hole_sizes(
    params: HelmholtzPanelParams,
    seed: int | None = None,
    strategy: Literal["stratified", "random"] = "stratified",
) -> np.ndarray:
    """
    Generate neck side-lengths for a broadband Helmholtz resonator panel.

    Uses the inverse-CDF method:
      1. Draw quantiles according to `strategy`.
      2. Map u → target frequency via the chosen distribution.
      3. Invert the Helmholtz equation analytically to get the side-length.
      4. Clamp to [a_min, a_max].

    Parameters
    ----------
    params   : HelmholtzPanelParams
    seed     : int or None — RNG seed (used for strategy='random' and shuffle)
    strategy : 'stratified' — evenly spaced quantiles, deterministic,
                              maximum uniformity (recommended for manufacturing)
               'random'     — Monte-Carlo draws

    Returns
    -------
    sizes : np.ndarray, shape (n_holes,)
        Neck side-lengths in metres (= `diameter` in the CadQuery neck()).
    """
    N = params.n_holes
    if strategy == "stratified":
        u = (np.arange(N) + 0.5) / N
    elif strategy == "random":
        u = np.random.default_rng(seed).uniform(0.0, 1.0, size=N)
    else:
        raise ValueError(f"Unknown strategy '{strategy}'.")

    sizes = _side_for_frequency(_quantile_to_frequency(u, params), params)
    return np.clip(sizes, params.a_min, params.a_max)


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

def panel_summary(params: HelmholtzPanelParams, sizes: np.ndarray) -> dict:
    """
    Diagnostic summary for a generated panel.

    Returns a dict with keys:
      resonance_frequencies_hz  : per-hole resonance frequencies [Hz]
      fraction_in_band          : fraction of holes with f in [f_low, f_high]
      perforation_ratio         : total open area / panel face area
      footprint_ok              : True if largest neck fits within its grid cell
      max_footprint_mm          : diamond footprint of the largest neck [mm]
      approx_cell_size_mm       : estimated square-root grid cell size [mm]
      cavity_volume_liters      : shared cavity volume [L]
      a_min_used, a_max_used    : actual min/max side-lengths after clamping [m]
    """
    freqs = hole_frequency(sizes, params)
    in_band = np.sum((freqs >= params.f_low) & (freqs <= params.f_high))
    panel_area = params.w * params.h
    cell_size = (panel_area / params.n_holes) ** 0.5
    max_footprint = float(sizes.max() * 2**0.5)

    return {
        "resonance_frequencies_hz": freqs,
        "fraction_in_band": float(in_band / len(sizes)),
        "perforation_ratio": float((sizes**2).sum()) / panel_area,
        "footprint_ok": max_footprint <= cell_size,
        "max_footprint_mm": max_footprint * 1e3,
        "approx_cell_size_mm": cell_size * 1e3,
        "cavity_volume_liters": panel_area * params.d_cavity * 1e3,
        "a_min_used": float(sizes.min()),
        "a_max_used": float(sizes.max()),
    }


# ---------------------------------------------------------------------------
# CadQuery bridge
# ---------------------------------------------------------------------------

def sizes_to_grid(
    sizes: np.ndarray,
    n_cols: int,
    n_rows: int,
    shuffle: bool = True,
    seed: int | None = None,
) -> list[list[float]]:
    """
    Arrange hole sizes into an (n_rows × n_cols) grid for helmholtzArray.

    Parameters
    ----------
    sizes  : output of generate_hole_sizes()
    n_cols : number of columns  (= numX in helmholtzArray)
    n_rows : number of rows     (= numZ in helmholtzArray)
    shuffle: randomise spatial arrangement to avoid clustering similar sizes
    seed   : RNG seed for shuffle

    Returns
    -------
    grid : list of lists, grid[row][col] = diameter [m]
    """
    assert len(sizes) == n_cols * n_rows
    s = sizes.copy()
    if shuffle:
        np.random.default_rng(seed).shuffle(s)
    return s.reshape(n_rows, n_cols).tolist()


def helmholtz_array_variable(numX, numZ, width, depth, height, diameters):
    """
    Drop-in replacement for helmholtzArray() that accepts a 2-D array of
    per-hole diameters instead of a single fixed diameter.

    Parameters
    ----------
    numX, numZ   : grid dimensions  (columns, rows)
    width, depth : panel width and neck depth [same units as diameters]
    height       : panel height
    diameters    : 2-D sequence, shape (numZ, numX), e.g. from sizes_to_grid()

    Returns
    -------
    CadQuery solid (union of all necks)
    """
    import cadquery as cq
    import functools

    def neck(d, diameter):
        n = cq.Workplane("XY").box(diameter, d, diameter)
        n = n.translate((0, d / 2, 0))
        n = n.rotate((0, 0, 0), (0, 1, 0), 45)
        return n

    offsetX = width  / numX
    offsetZ = height / numZ
    startX  = offsetX / 2
    startZ  = offsetZ / 2

    necks = []
    for j in range(numZ):
        for i in range(numX):
            d = diameters[j][i]
            necks.append(
                neck(depth, d).translate(
                    (startX + i * offsetX, 0, startZ + j * offsetZ)
                )
            )
    return functools.reduce(lambda a, b: a.union(b), necks)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    p = HelmholtzPanelParams(
        w=0.10,          # 100 mm
        h=0.10,          # 100 mm
        depth=0.010,     # 10 mm wall  (= `depth` in neck())
        d_cavity=0.005,  # 5 mm cavity
        n_holes=48,      # 8 cols × 6 rows
        a_min=0.001,     # 1 mm
        a_max=0.010,     # 10 mm
        f_low=100.0,
        f_high=550.0,
        distribution="log",
    )

    sizes = generate_hole_sizes(p, seed=42, strategy="stratified")
    info  = panel_summary(p, sizes)

    print(f"Generated {len(sizes)} neck side-lengths")
    print(f"  Side-lengths [mm]: min={info['a_min_used']*1e3:.2f}  "
          f"max={info['a_max_used']*1e3:.2f}")
    print(f"  Fraction in target band : {info['fraction_in_band']:.1%}")
    print(f"  Perforation ratio       : {info['perforation_ratio']:.2%}")
    print(f"  Cavity volume           : {info['cavity_volume_liters']:.3f} L")
    print(f"  Footprint fits in cell  : {info['footprint_ok']}  "
          f"(max footprint {info['max_footprint_mm']:.1f} mm "
          f"vs cell ≈{info['approx_cell_size_mm']:.1f} mm)")
    print()
    print("Resonance frequencies (Hz), sorted:")
    print(np.sort(info["resonance_frequencies_hz"]).round(1))

    grid = sizes_to_grid(sizes, n_cols=8, n_rows=6, shuffle=True, seed=42)
    print("\nGrid of diameters (mm), ready for helmholtz_array_variable():")
    for row in grid:
        print("  ", [f"{v*1e3:.2f}" for v in row])