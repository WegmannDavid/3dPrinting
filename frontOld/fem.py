"""
Acoustic Transmission Loss — single-file Python simulation
===========================================================
Pipeline:
  1. CadQuery   →  export air.step + foam.step + port coordinates
  2. Gmsh       →  import, fragment (conformal mesh), tag boundaries
  3. scikit-fem →  Helmholtz + Delany-Bazley, complex frequency sweep
  4. pyvista    →  3D SPL volume plot + cross-section slice
  5. Matplotlib →  STL curve + CSV export

Requirements:
    pip install cadquery gmsh scikit-fem meshio matplotlib numpy scipy pyvista "pyvista[jupyter]"
"""

# ── Imports ───────────────────────────────────────────────────────────────────
import json
import math
from pathlib import Path

import gmsh
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
import matplotlib.pyplot as plt
import pyvista as pv
import cadquery as cq
import front

from skfem import (
    MeshTet,
    Basis,
    FacetBasis,
    ElementTetP1,
    asm,
    LinearForm,
    BilinearForm,
)
from skfem.helpers import grad, dot

# ── User configuration ────────────────────────────────────────────────────────
FREQ_START = 50  # Hz
FREQ_STOP = 1000  # Hz
FREQ_STEP = 50  # Hz

SIGMA = 12400.0  # Pa·s/m²  — Bassotect flow resistivity
RHO0 = 1.204  # kg/m³    — air density at 20 °C
C0 = 343.0  # m/s      — speed of sound in air
P_REF = 20e-6  # Pa       — acoustic reference pressure

ELEM_PER_WAVE = 6  # elements per wavelength at FREQ_STOP (min 6)

# Frequency at which to generate the 3D pressure plot
PLOT_FREQ = 500  # Hz — change to any frequency in the sweep

CSV_OUT = Path("STL_results.csv")
PNG_OUT = Path("STL_results.png")
VIZ_HTML = Path("pressure_3d.html")
VIZ_PNG = Path("pressure_3d.png")

# Physical group tags — must match Gmsh
TAG_AIR = 1
TAG_FOAM = 2
TAG_PORT1 = 1
TAG_PORT2 = 2
TAG_WALLS = 3


# ═════════════════════════════════════════════════════════════════════════════
# STEP 1 — CadQuery: export geometry
# ═════════════════════════════════════════════════════════════════════════════


def export_geometry():
    """
    Calls front.femAir() and front.femFoam().
    Port 1: face with normal along -X (min X face)  ~12x3 cm
    Port 2: face with normal along -Z (min Z face)  ~20x2 cm
    Exports STEP files and port_info.json with centroid + axis per port.
    """
    _air = front.femAir()
    _foam = front.femFoam()

    port1_face = _air.faces("<X").val()  # normal along X, ~12x3 cm
    port2_face = _air.faces("<Z").val()  # normal along Z, ~20x2 cm

    p1 = port1_face.Center()
    p2 = port2_face.Center()
    bb = _air.val().BoundingBox()

    port_info = {
        # Port 1: X-normal face — tag by X centroid
        "port1_axis": "x",
        "port1_coord": p1.x,
        # Port 2: Z-normal face — tag by Z centroid
        "port2_axis": "z",
        "port2_coord": p2.z,
        "xmin": bb.xmin,
        "xmax": bb.xmax,
        "ymin": bb.ymin,
        "ymax": bb.ymax,
        "zmin": bb.zmin,
        "zmax": bb.zmax,
    }

    print(f"Port 1 centre: ({p1.x:.2f}, {p1.y:.2f}, {p1.z:.2f}) mm  axis=X")
    print(f"Port 2 centre: ({p2.x:.2f}, {p2.y:.2f}, {p2.z:.2f}) mm  axis=Z")

    cq.exporters.export(_air, "air.step")
    cq.exporters.export(_foam, "foam.step")
    with open("port_info.json", "w") as f:
        json.dump(port_info, f, indent=2)
    print("Exported: air.step, foam.step, port_info.json")
    return port_info


# ═════════════════════════════════════════════════════════════════════════════
# STEP 2 — Gmsh: mesh and tag boundaries
# ═════════════════════════════════════════════════════════════════════════════


def build_mesh(port_info, show_gui=False):
    """
    Import air.step + foam.step, fragment for conformal interface,
    tag boundaries, generate tet mesh, write mesh.msh.
    """
    TOL = 1.0  # mm tolerance for centroid matching

    lambda_min_mm = (C0 / FREQ_STOP) * 1000.0
    h = lambda_min_mm / ELEM_PER_WAVE
    print(f"\nMesh: lambda_min = {lambda_min_mm:.1f} mm  ->  h = {h:.1f} mm")

    gmsh.initialize()
    gmsh.model.add("acoustic_STL")
    gmsh.option.setNumber("General.Terminal", 1)

    air_ents = gmsh.model.occ.importShapes("air.step")
    foam_ents = gmsh.model.occ.importShapes("foam.step")
    gmsh.model.occ.synchronize()

    air_vols = [s[1] for s in air_ents if s[0] == 3]
    foam_vols = [s[1] for s in foam_ents if s[0] == 3]

    all_ents = [(3, v) for v in air_vols + foam_vols]
    out_ents, mapping = gmsh.model.occ.fragment(all_ents, [])
    gmsh.model.occ.synchronize()

    n_air = len(air_vols)

    def remapped(indices):
        tags = set()
        for i in indices:
            if i < len(mapping):
                for e in mapping[i]:
                    if e[0] == 3:
                        tags.add(e[1])
        return list(tags)

    new_air_vols = remapped(range(n_air))
    new_foam_vols = remapped(range(n_air, n_air + len(foam_vols)))

    if not new_air_vols or not new_foam_vols:
        print("Remap fallback — classifying by volume centroid")
        x_mid = (port_info["xmin"] + port_info["xmax"]) / 2.0
        new_air_vols, new_foam_vols = [], []
        for e in out_ents:
            if e[0] == 3:
                cx, _, _ = gmsh.model.occ.getCenterOfMass(3, e[1])
                (new_air_vols if cx < x_mid else new_foam_vols).append(e[1])

    gmsh.model.addPhysicalGroup(3, new_air_vols, tag=TAG_AIR, name="Air")
    gmsh.model.addPhysicalGroup(3, new_foam_vols, tag=TAG_FOAM, name="Foam")

    # Tag port surfaces by centroid along their respective normal axis
    port1_axis = port_info["port1_axis"]  # "x"
    port1_coord = port_info["port1_coord"]  # mm
    port2_axis = port_info["port2_axis"]  # "z"
    port2_coord = port_info["port2_coord"]  # mm
    axis_idx = {"x": 0, "y": 1, "z": 2}

    port1_surfs, port2_surfs, wall_surfs = [], [], []
    for dim, tag in gmsh.model.getEntities(2):
        cx, cy, cz = gmsh.model.occ.getCenterOfMass(dim, tag)
        centroid = [cx, cy, cz]
        c1 = centroid[axis_idx[port1_axis]]
        c2 = centroid[axis_idx[port2_axis]]
        if abs(c1 - port1_coord) < TOL:
            port1_surfs.append(tag)
        elif abs(c2 - port2_coord) < TOL:
            port2_surfs.append(tag)
        else:
            wall_surfs.append(tag)

    assert port1_surfs, f"No Port1 surface at {port1_axis}={port1_coord:.1f} mm"
    assert port2_surfs, f"No Port2 surface at {port2_axis}={port2_coord:.1f} mm"

    gmsh.model.addPhysicalGroup(2, port1_surfs, tag=TAG_PORT1, name="Port1")
    gmsh.model.addPhysicalGroup(2, port2_surfs, tag=TAG_PORT2, name="Port2")
    gmsh.model.addPhysicalGroup(2, wall_surfs, tag=TAG_WALLS, name="Walls")

    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", h)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMin", h / 4)
    gmsh.option.setNumber("Mesh.Algorithm3D", 4)
    gmsh.model.mesh.generate(3)
    gmsh.model.mesh.optimize("Netgen")
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.write("mesh.msh")
    print("Mesh written: mesh.msh")

    if show_gui:
        gmsh.fltk.run()
    gmsh.finalize()


# ═════════════════════════════════════════════════════════════════════════════
# STEP 3 — scikit-fem: load mesh
# ═════════════════════════════════════════════════════════════════════════════


def load_mesh_skfem():
    """
    Load mesh.msh into scikit-fem.

    Note: skfem's MSH2 loader has a tag collision — volume physical groups
    share integer tags with surface groups and surface names win. We fix this
    by renaming volume subdomains after loading, then scale mm -> metres.
    """
    mesh = MeshTet.load("mesh.msh")

    # Volume tag 1 = Air, tag 2 = Foam (per PhysicalNames in .msh)
    # but skfem loaded them as 'Port1' / 'Port2' (surface names for same tags)
    mesh.subdomains["Air"] = mesh.subdomains.pop("Port1")
    mesh.subdomains["Foam"] = mesh.subdomains.pop("Port2")

    mesh = mesh.scaled(1e-3)  # mm -> m

    print(f"Mesh: {mesh.nvertices} nodes, {mesh.nelements} tets")
    print(f"  Subdomains: {list(mesh.subdomains.keys())}")
    print(f"  Boundaries: {list(mesh.boundaries.keys())}")
    print(f"  Extent: {mesh.p.min():.3f} – {mesh.p.max():.3f} m")
    return mesh


# ═════════════════════════════════════════════════════════════════════════════
# STEP 4 — scikit-fem: Helmholtz + Delany-Bazley frequency sweep
# ═════════════════════════════════════════════════════════════════════════════


def delany_bazley(f):
    """
    Delany-Bazley equivalent fluid for fibrous absorbers.
    Returns complex (rho_eq, c_eq). Valid for 0.01 < rho0*f/sigma < 1.0.
    """
    X = RHO0 * f / SIGMA
    rho_eq = RHO0 * complex(1 + 0.0982 * X ** (-0.778), -0.1088 * X ** (-0.700))
    c_eq = C0 * complex(1 + 0.0978 * X ** (-0.700), -0.0858 * X ** (-0.700))
    return rho_eq, c_eq


def solve_helmholtz(mesh, f, bases):
    """
    Solve complex Helmholtz at frequency f.
    Returns (p_r, p_i) — real and imaginary parts of nodal pressure.

    Formulation (2N x 2N real block system):
      Air  (real k):     int grad(p).grad(v) dx - k2_air  * int p*v dx = 0
      Foam (complex k):  int grad(p).grad(v) dx - k2_foam * int p*v dx = 0
      Port1 (Neumann):   dp/dn = -i*omega*rho0  (unit velocity, v_n = 1 m/s)
      Port2 (Robin):     dp/dn + (i*omega/c0)*p = 0  (anechoic termination)
      Walls (Neumann 0): dp/dn = 0  (hard wall, default)

    Block structure:
      [A_diag   A_ri ] [p_r]   [    0        ]
      [A_ir    A_diag] [p_i] = [neumann*f_p1 ]

      A_diag = K - k2r*M_air - kfr*M_foam - robin*B_p2
      A_ri   = +kfi*M_foam - robin*B_p2
      A_ir   = -kfi*M_foam + robin*B_p2
    """
    K, M_air, M_foam, B_p2, f_p1 = bases

    omega = 2.0 * math.pi * f
    _, c_foam = delany_bazley(f)

    k2_r = float((omega / C0) ** 2)
    kf = (omega / c_foam) ** 2
    kf_r = float(kf.real)
    kf_i = float(kf.imag)
    robin = omega / C0
    neumann = -omega * RHO0

    A_diag = K - k2_r * M_air - kf_r * M_foam - robin * B_p2
    A_ri = kf_i * M_foam - robin * B_p2
    A_ir = -kf_i * M_foam + robin * B_p2

    A = sp.bmat([[A_diag, A_ri], [A_ir, A_diag]], format="csc")

    N = mesh.nvertices
    rhs = np.zeros(2 * N)
    rhs[N:] = neumann * f_p1

    sol = spla.spsolve(A, rhs)
    return sol[:N], sol[N:]


def run_frequency_sweep(mesh):
    """Assemble matrices once, sweep frequencies, return STL results."""
    frequencies = np.arange(FREQ_START, FREQ_STOP + FREQ_STEP, FREQ_STEP, dtype=float)
    stl_db = np.zeros(len(frequencies))
    p1_abs = np.zeros(len(frequencies))
    p2_abs = np.zeros(len(frequencies))

    # Store pressure field at PLOT_FREQ for 3D visualisation
    plot_result = {"p_r": None, "p_i": None, "freq": PLOT_FREQ}

    # Assemble frequency-independent matrices
    basis_air = Basis(mesh, ElementTetP1(), elements=mesh.subdomains["Air"])
    basis_foam = Basis(mesh, ElementTetP1(), elements=mesh.subdomains["Foam"])
    basis_p1 = FacetBasis(mesh, ElementTetP1(), facets=mesh.boundaries["Port1"])
    basis_p2 = FacetBasis(mesh, ElementTetP1(), facets=mesh.boundaries["Port2"])

    @BilinearForm
    def stiffness(u, v, w):
        return dot(grad(u), grad(v))

    @BilinearForm
    def mass(u, v, w):
        return u * v

    @BilinearForm
    def boundary_mass(u, v, w):
        return u * v

    @LinearForm
    def port1_load(v, w):
        return v

    K = asm(stiffness, basis_air) + asm(stiffness, basis_foam)
    M_air = asm(mass, basis_air)
    M_foam = asm(mass, basis_foam)
    B_p2 = asm(boundary_mass, basis_p2)
    f_p1 = asm(port1_load, basis_p1)

    bases = (K, M_air, M_foam, B_p2, f_p1)
    print(
        f"\nFrequency sweep: {FREQ_START}–{FREQ_STOP} Hz ({len(frequencies)} steps)\n"
    )

    for idx, f in enumerate(frequencies):
        p_r, p_i = solve_helmholtz(mesh, f, bases)

        def mean_p_mag(b):
            vals = b.interpolate(p_r) + 1j * b.interpolate(p_i)
            w = b.dx
            return np.sum(np.abs(vals) * w) / np.sum(w)

        mag1 = mean_p_mag(basis_p1)
        mag2 = mean_p_mag(basis_p2)

        p1_abs[idx] = mag1
        p2_abs[idx] = mag2
        ratio = (mag1 / mag2) ** 2 if mag2 > 1e-20 else 1e20
        stl = 10.0 * math.log10(max(ratio, 1e-20))
        stl_db[idx] = stl

        print(f"  f={f:6.0f} Hz  |p1|={mag1:.4f}  |p2|={mag2:.6f}  STL={stl:.2f} dB")

        # Store field at chosen visualisation frequency
        if abs(f - PLOT_FREQ) < 1e-6:
            plot_result["p_r"] = p_r.copy()
            plot_result["p_i"] = p_i.copy()

    return frequencies, stl_db, p1_abs, p2_abs, plot_result


# ═════════════════════════════════════════════════════════════════════════════
# STEP 5 — pyvista: 3D pressure visualisation
# ═════════════════════════════════════════════════════════════════════════════


def skfem_to_pyvista(mesh, p_r, p_i):
    """Build a pyvista UnstructuredGrid with pressure fields as point data."""
    pts = mesh.p.T
    tets = mesh.t.T
    cells = np.hstack([np.full((tets.shape[0], 1), 4, dtype=np.int64), tets]).ravel()
    ctypes = np.full(tets.shape[0], 10, dtype=np.uint8)  # VTK_TETRA = 10
    grid = pv.UnstructuredGrid(cells, ctypes, pts)

    p_mag = np.abs(p_r + 1j * p_i)
    SPL = 20.0 * np.log10(np.maximum(p_mag, P_REF * 1e-3) / P_REF)

    grid.point_data["SPL (dB)"] = SPL
    grid.point_data["|p| (Pa)"] = p_mag
    grid.point_data["Re(p) (Pa)"] = p_r
    grid.point_data["Im(p) (Pa)"] = p_i

    # Domain flag per cell: 0 = Air, 1 = Foam
    domain = np.zeros(mesh.nelements, dtype=np.int8)
    domain[mesh.subdomains["Foam"]] = 1
    grid.cell_data["Domain"] = domain

    return grid


def plot_3d(mesh, p_r, p_i, freq, show=True):
    """
    3D pyvista visualisation of the pressure field.

    Produces:
      pressure_3d.html       — interactive 3D volume (open in browser)
      pressure_3d.png        — screenshot of 3D view
      pressure_3d_slice.html — interactive cross-section slice
      pressure_3d_slice.png  — screenshot of slice
    """
    grid = skfem_to_pyvista(mesh, p_r, p_i)

    air_grid = grid.extract_cells(mesh.subdomains["Air"])
    foam_grid = grid.extract_cells(mesh.subdomains["Foam"])

    spl_min = grid.point_data["SPL (dB)"].min()
    spl_max = grid.point_data["SPL (dB)"].max()
    clim = [spl_min, spl_max]

    scalar_bar_args = {
        "title": "SPL (dB)",
        "title_font_size": 14,
        "label_font_size": 12,
        "n_labels": 6,
        "fmt": "%.0f",
        "color": "black",
    }

    pv.OFF_SCREEN = not show

    # ── 3D volume plot ───────────────────────────────────────────────────────
    pl = pv.Plotter(off_screen=not show, window_size=(1400, 700))
    pl.set_background("white")

    pl.add_mesh(
        air_grid,
        scalars="SPL (dB)",
        cmap="jet",
        clim=clim,
        scalar_bar_args=scalar_bar_args,
    )
    pl.add_mesh(
        foam_grid,
        scalars="SPL (dB)",
        cmap="jet",
        clim=clim,
        opacity=0.55,
        show_scalar_bar=False,
    )
    pl.add_mesh(
        foam_grid.extract_surface(),
        color="dimgray",
        style="wireframe",
        line_width=0.8,
        opacity=0.25,
        label="Bassotect (foam)",
    )

    pl.add_title(f"Sound Pressure Level — {freq:.0f} Hz", font_size=14, color="black")
    pl.add_axes(color="black")
    pl.add_legend(face=None, bcolor="white")

    pl.screenshot(str(VIZ_PNG))
    print(f"Saved: {VIZ_PNG}")
    pl.export_html(str(VIZ_HTML))
    print(f"Saved: {VIZ_HTML}  (open in browser for interactive view)")

    if show:
        pl.show()
    pl.close()

    # ── Cross-section slice (Y midplane) ────────────────────────────────────
    y_mid = (mesh.p[1].min() + mesh.p[1].max()) / 2.0
    slice_ = grid.slice(normal="y", origin=(0, y_mid, 0))

    pl2 = pv.Plotter(off_screen=not show, window_size=(1400, 500))
    pl2.set_background("white")
    pl2.add_mesh(
        slice_,
        scalars="SPL (dB)",
        cmap="jet",
        clim=clim,
        scalar_bar_args={**scalar_bar_args, "title": "SPL (dB)"},
    )
    pl2.add_title(
        f"SPL cross-section (Y = {y_mid*1000:.1f} mm) — {freq:.0f} Hz",
        font_size=13,
        color="black",
    )
    pl2.view_xz()
    pl2.add_axes(color="black")

    slice_png = Path(str(VIZ_PNG).replace(".png", "_slice.png"))
    slice_html = Path(str(VIZ_HTML).replace(".html", "_slice.html"))

    pl2.screenshot(str(slice_png))
    print(f"Saved: {slice_png}")
    pl2.export_html(str(slice_html))
    print(f"Saved: {slice_html}")

    if show:
        pl2.show()
    pl2.close()


# ═════════════════════════════════════════════════════════════════════════════
# STEP 6 — Post-processing: STL curve + CSV
# ═════════════════════════════════════════════════════════════════════════════


def save_and_plot(frequencies, stl_db, p1_abs, p2_abs):
    data = np.column_stack([frequencies, p1_abs, p2_abs, stl_db])
    np.savetxt(
        CSV_OUT,
        data,
        delimiter=",",
        header="Frequency_Hz,|p1|_Pa,|p2|_Pa,STL_dB",
        comments="",
    )
    print(f"Saved: {CSV_OUT}")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(
        frequencies,
        stl_db,
        "o-",
        color="#2a6496",
        linewidth=2,
        markersize=5,
        label=f"Bassotect (Delany-Bazley, sigma={SIGMA:.0f} Pa.s/m2)",
    )
    ax.fill_between(frequencies, stl_db, alpha=0.08, color="#2a6496")
    ax.set_xlabel("Frequency (Hz)", fontsize=12)
    ax.set_ylabel("Transmission Loss (dB)", fontsize=12)
    ax.set_title(
        "Sound Transmission Loss — Air + Bassotect", fontsize=13, fontweight="bold"
    )
    ax.set_xlim(FREQ_START - FREQ_STEP, FREQ_STOP + FREQ_STEP)
    ax.set_xticks(frequencies)
    ax.tick_params(axis="x", rotation=60)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(fontsize=10)
    ax.axvline(x=100, color="orange", linestyle=":", linewidth=1.2, alpha=0.7)
    ax.text(105, min(stl_db) + 1, "D-B valid ->", color="orange", fontsize=8)
    fig.tight_layout()
    fig.savefig(PNG_OUT, dpi=150)
    print(f"Saved: {PNG_OUT}")
    plt.show()

    print(
        f"\n{'Freq (Hz)':>10}  {'|p1| (Pa)':>12}  {'|p2| (Pa)':>12}  {'STL (dB)':>10}"
    )
    print("-" * 52)
    for f, a1, a2, stl in zip(frequencies, p1_abs, p2_abs, stl_db):
        print(f"{f:>10.0f}  {a1:>12.4f}  {a2:>12.6f}  {stl:>10.2f}")


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════


def run(show_mesh_gui=False, show_3d=True):
    """
    Full pipeline.

    Args:
        show_mesh_gui: Open Gmsh GUI to inspect mesh before solving
        show_3d:       Open interactive pyvista window during 3D plotting
                       (set False for headless/server environments)
    """
    print("=" * 60)
    print("  Acoustic STL — CadQuery -> Gmsh -> scikit-fem -> pyvista")
    print("=" * 60)

    print("\n-- Step 1: Exporting geometry --")
    port_info = export_geometry()

    print("\n-- Step 2: Building mesh --")
    build_mesh(port_info, show_gui=show_mesh_gui)

    print("\n-- Step 3: Loading mesh --")
    mesh = load_mesh_skfem()

    print("\n-- Step 4: Frequency sweep --")
    frequencies, stl_db, p1_abs, p2_abs, plot_result = run_frequency_sweep(mesh)

    print(f"\n-- Step 5: 3D pressure plot at {PLOT_FREQ} Hz --")
    if plot_result["p_r"] is not None:
        plot_3d(
            mesh,
            plot_result["p_r"],
            plot_result["p_i"],
            plot_result["freq"],
            show=show_3d,
        )
    else:
        print(f"  WARNING: PLOT_FREQ={PLOT_FREQ} Hz not in sweep, skipping 3D plot.")

    print("\n-- Step 6: STL results --")
    save_and_plot(frequencies, stl_db, p1_abs, p2_abs)

    print("\nDone.")
    return frequencies, stl_db


if __name__ == "__main__":
    # Set show_3d=False if running headless (no display)
    run(show_mesh_gui=True, show_3d=True)
