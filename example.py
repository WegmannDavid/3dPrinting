"""
Quarter-Wave Resonator — Transmission Loss Simulation
======================================================
  CadQuery  – parametric geometry (STEP)
  Gmsh      – tetrahedral mesh
  SciPy/FEM – Helmholtz solver (plane-wave forcing, ABC outlet)
  Matplotlib– TL plot with analytic overlay
  PyVista   – 3-D pressure cross-section at each frequency

Resonator geometry:
  Main duct:  radius 25 mm, length 400 mm (along X)
  Stub:       radius 30 mm, length 85 mm  (along +Y from duct wall)
              λ/4 resonance at c/(4×0.085) ≈ 1009 Hz

Helmholtz BVP:
  ∇²p + k²p = 0   in Ω
  p  = 1           on inlet  (x = 0,   Dirichlet via penalty)
  ∂p/∂n = jk·p    on outlet (x = L,   1st-order absorbing BC, Robin)
  ∂p/∂n = 0       on walls  (rigid,   natural BC)

TL = −20 log₁₀(|⟨p⟩_outlet| / |⟨p⟩_inlet|)
"""

import cadquery as cq
import gmsh, math, os
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
import pyvista as pv
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

# ════════════════════════════════════════════════════
#  PARAMETERS
# ════════════════════════════════════════════════════
DUCT_R = 0.030  # duct radius   [m]
DUCT_L = 0.40  # duct length   [m]
RES_R = 0.030  # stub radius   [m]  (same as duct for strong coupling)
RES_L = 0.085  # stub length   [m]  → f_res ≈ 1009 Hz
RES_POS = 0.20  # stub centre x [m]

C0 = 343.0
FREQS = np.arange(50, 2001, 50)  # 40 frequencies

OUT = "/mnt/user-data/outputs"
os.makedirs(OUT, exist_ok=True)

# ════════════════════════════════════════════════════
#  1. ANALYTIC REFERENCE (1-D, plane wave)
# ════════════════════════════════════════════════════
S_duct = np.pi * DUCT_R**2
S_res = np.pi * RES_R**2
TL_analytic = []
for f in FREQS:
    k = 2 * np.pi * f / C0
    tan_kL = np.tan(k * RES_L)
    T = 2 * S_duct / (2 * S_duct + 1j * S_res * tan_kL)
    TL_analytic.append(-20.0 * np.log10(max(abs(T), 1e-12)))

# ════════════════════════════════════════════════════
#  2. CADQUERY GEOMETRY
# ════════════════════════════════════════════════════
print("▶ CadQuery geometry …")
duct = cq.Workplane("YZ").circle(DUCT_R).extrude(DUCT_L)
stub = cq.Workplane("XZ").center(RES_POS, 0).circle(RES_R).extrude(DUCT_R + RES_L)
solid = duct.union(stub)
step_path = "/home/claude/qwr.step"
cq.exporters.export(solid, step_path)
print(f"  STEP: {step_path}")

# ════════════════════════════════════════════════════
#  3. GMSH — mesh
# ════════════════════════════════════════════════════
print("▶ Gmsh meshing …")
gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 0)
gmsh.model.add("qwr")

d = gmsh.model.occ.addCylinder(0, 0, 0, DUCT_L, 0, 0, DUCT_R)
s = gmsh.model.occ.addCylinder(RES_POS, 0, 0, 0, DUCT_R + RES_L, 0, RES_R)
gmsh.model.occ.fuse([(3, d)], [(3, s)])
gmsh.model.occ.synchronize()

# 8 elements per λ at f_max = 2000 Hz
lc = C0 / FREQS[-1] / 8
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", lc)
gmsh.option.setNumber("Mesh.CharacteristicLengthMin", lc * 0.3)
gmsh.option.setNumber("Mesh.Algorithm3D", 4)
gmsh.model.mesh.generate(3)

# Tag inlet / outlet
inlet_surfs, outlet_surfs = [], []
for dim, tag in gmsh.model.getEntities(dim=2):
    bb = gmsh.model.getBoundingBox(dim, tag)
    if bb[3] < 1e-5:
        inlet_surfs.append(tag)
    if bb[0] > DUCT_L - 1e-5:
        outlet_surfs.append(tag)
assert inlet_surfs and outlet_surfs

gmsh.model.addPhysicalGroup(2, inlet_surfs, tag=1, name="inlet")
gmsh.model.addPhysicalGroup(2, outlet_surfs, tag=2, name="outlet")
vols = [t for _, t in gmsh.model.getEntities(dim=3)]
gmsh.model.addPhysicalGroup(3, vols, tag=10, name="fluid")

# Extract mesh
node_tags_raw, node_xyz, _ = gmsh.model.mesh.getNodes()
N = len(node_tags_raw)
coords = node_xyz.reshape(-1, 3)
tag2idx = {int(t): i for i, t in enumerate(node_tags_raw)}

etypes, _, enode_lists = gmsh.model.mesh.getElements(dim=3)
tets = None
for et, en in zip(etypes, enode_lists):
    if et == 4:
        arr = en.astype(np.int64).reshape(-1, 4)
        tets = np.array([[tag2idx[int(x)] for x in row] for row in arr])
        break
assert tets is not None


def get_tris(phys_tag):
    tris = []
    for dim2, stag in gmsh.model.getEntities(dim=2):
        if phys_tag in gmsh.model.getPhysicalGroupsForEntity(dim2, stag):
            et2, _, en2 = gmsh.model.mesh.getElements(dim=2, tag=stag)
            for et, en in zip(et2, en2):
                if et == 2:
                    arr = en.astype(np.int64).reshape(-1, 3)
                    for row in arr:
                        tris.append([tag2idx[int(x)] for x in row])
    return np.array(tris, dtype=np.int64) if tris else np.zeros((0, 3), dtype=np.int64)


def get_node_set(phys_tag):
    ns = set()
    for dim2, stag in gmsh.model.getEntities(dim=2):
        if phys_tag in gmsh.model.getPhysicalGroupsForEntity(dim2, stag):
            nt, _, _ = gmsh.model.mesh.getNodes(dim2, stag, returnParametricCoord=False)
            ns.update(tag2idx[int(t)] for t in nt)
    return sorted(ns)


outlet_tris = get_tris(2)
inlet_nodes = get_node_set(1)
outlet_nodes = get_node_set(2)
gmsh.finalize()

print(
    f"  N={N} nodes  |  {len(tets)} tets  |  "
    f"inlet {len(inlet_nodes)} nodes  |  outlet {len(outlet_nodes)} nodes  |  "
    f"{len(outlet_tris)} outlet tris"
)

# ════════════════════════════════════════════════════
#  4. FEM ASSEMBLY
# ════════════════════════════════════════════════════
print("▶ Assembling FEM matrices …")

rK = []
cK = []
vK = []
rM = []
cM = []
vM = []

for tet in tets:
    v = coords[tet]
    A_m = np.array([v[1] - v[0], v[2] - v[0], v[3] - v[0]]).T
    vol = abs(np.linalg.det(A_m)) / 6.0
    if vol < 1e-30:
        continue
    B = np.linalg.inv(A_m).T
    G = np.zeros((3, 4))
    G[:, 1:] = B
    G[:, 0] = -B.sum(axis=1)
    Ke = vol * (G.T @ G)
    Me = vol / 20.0 * (np.ones((4, 4)) + np.eye(4))
    for i in range(4):
        for j in range(4):
            rK.append(tet[i])
            cK.append(tet[j])
            vK.append(Ke[i, j])
            rM.append(tet[i])
            cM.append(tet[j])
            vM.append(Me[i, j])

K_g = sp.csr_matrix((vK, (rK, cK)), shape=(N, N))
M_g = sp.csr_matrix((vM, (rM, cM)), shape=(N, N))

rR = []
cR = []
vR = []
for tri in outlet_tris:
    v = coords[tri]
    area = 0.5 * np.linalg.norm(np.cross(v[1] - v[0], v[2] - v[0]))
    Sm = area / 12.0 * (np.ones((3, 3)) + np.eye(3))
    for i in range(3):
        for j in range(3):
            rR.append(tri[i])
            cR.append(tri[j])
            vR.append(Sm[i, j])

R_g = sp.csr_matrix((vR, (rR, cR)), shape=(N, N)) if rR else sp.csr_matrix((N, N))
print("  Assembled.")

# ════════════════════════════════════════════════════
#  5. FREQUENCY LOOP
# ════════════════════════════════════════════════════
print(f"▶ Solving {len(FREQS)} frequencies …")

PENALTY = 1e14
TL_fem = []
p_store = {}
KEY = {50, 250, 500, 750, 1000, 1050, 1250, 1500, 1750, 2000}

for fi, freq in enumerate(FREQS):
    k = 2 * np.pi * freq / C0
    A = (K_g - k**2 * M_g + 1j * k * R_g).tolil().astype(complex)
    b = np.zeros(N, dtype=complex)
    for nd in inlet_nodes:
        A[nd, :] = 0.0
        A[nd, nd] = PENALTY
        b[nd] = PENALTY
    p = spla.spsolve(A.tocsr(), b)

    p_in = float(np.mean(np.abs(p[inlet_nodes])))
    p_out = float(np.mean(np.abs(p[outlet_nodes]))) if outlet_nodes else 1e-12
    tl = -20.0 * np.log10(max(p_out / max(p_in, 1e-12), 1e-12))
    TL_fem.append(tl)

    if fi % 4 == 0 or int(freq) in KEY:
        p_store[int(freq)] = p.copy()

    if (fi + 1) % 8 == 0 or fi == 0:
        print(
            f"  {freq:5.0f} Hz  FEM={tl:6.2f} dB  "
            f"analytic={TL_analytic[fi]:6.2f} dB"
        )

print("  Done.")

# ════════════════════════════════════════════════════
#  6. MATPLOTLIB — TL plot
# ════════════════════════════════════════════════════
print("▶ Saving TL plot …")

fig, ax = plt.subplots(figsize=(13, 5))
ax.plot(FREQS, TL_fem, "b-o", ms=4, lw=1.8, label="FEM 3-D")
ax.plot(FREQS, TL_analytic, "r--", lw=1.5, label="1-D analytic")
ax.set_xlabel("Frequency  [Hz]", fontsize=12)
ax.set_ylabel("Transmission Loss  [dB]", fontsize=12)
ax.set_title(
    f"Quarter-Wave Resonator  —  duct R={DUCT_R*1000:.0f} mm  "
    f"| stub R={RES_R*1000:.0f} mm  L={RES_L*1000:.0f} mm",
    fontsize=12,
)
ax.set_xlim(FREQS[0], FREQS[-1])
ax.grid(True, alpha=0.3)
cols = ["darkgreen", "purple", "orange", "brown"]
for n in range(1, 5):
    ft = (2 * n - 1) * C0 / (4 * RES_L)
    if ft <= FREQS[-1]:
        ax.axvline(
            ft,
            color=cols[n - 1],
            ls=":",
            lw=1.5,
            alpha=0.7,
            label=f"λ/4 n={n}: {ft:.0f} Hz",
        )
ax.legend(fontsize=9)
plt.tight_layout()
tl_path = os.path.join(OUT, "TL_quarter_wave_resonator.png")
plt.savefig(tl_path, dpi=150)
plt.close()
print(f"  {tl_path}")

# ════════════════════════════════════════════════════
#  7. PYVISTA — 3-D pressure cross-sections
# ════════════════════════════════════════════════════
print("▶ Rendering 3-D pressure fields …")
pv.start_xvfb()

n_t = len(tets)
cell_arr = np.hstack([np.full((n_t, 1), 4, dtype=np.int64), tets]).ravel()
ctype_arr = np.full(n_t, pv.CellType.TETRA)
grid = pv.UnstructuredGrid(cell_arr, ctype_arr, coords.copy())

for freq, p in p_store.items():
    grid.point_data[f"{freq}Hz_mag"] = np.abs(p).astype(np.float32)
    grid.point_data[f"{freq}Hz_real"] = np.real(p).astype(np.float32)

cam = [(0.65, -0.20, 0.18), (0.20, 0.07, 0.00), (0, 0, 1)]
scr_dir = "/home/claude/screens"
os.makedirs(scr_dir, exist_ok=True)
freq_keys = sorted(p_store.keys())
screen_paths = []

for freq in freq_keys:
    fname = f"{freq}Hz_mag"
    # XZ mid-plane slice (z=0) to see duct + stub cross-section
    sliced = grid.slice(normal="z", origin=(0, 0, 0))
    # Also a YZ cross-section to show standing wave in stub
    sliced2 = grid.slice(normal="x", origin=(RES_POS, 0, 0))

    pl = pv.Plotter(off_screen=True, window_size=(900, 520), shape=(1, 2))

    # Left: XZ plane (duct horizontal)
    pl.subplot(0, 0)
    pl.set_background("#1a1a2e")
    pl.add_mesh(grid, style="wireframe", color="#4a4a6a", opacity=0.07, line_width=0.4)
    pl.add_mesh(
        sliced,
        scalars=fname,
        cmap="plasma",
        clim=[0, 2.0],
        show_scalar_bar=True,
        scalar_bar_args={
            "title": "|p|",
            "vertical": True,
            "position_x": 0.87,
            "position_y": 0.1,
            "title_font_size": 10,
            "label_font_size": 9,
        },
    )
    pl.add_title(f"XZ slice — |p|  f={freq} Hz", font_size=8, color="white")
    pl.camera_position = cam

    # Right: YZ cross-section at stub position
    pl.subplot(0, 1)
    pl.set_background("#1a1a2e")
    pl.add_mesh(grid, style="wireframe", color="#4a4a6a", opacity=0.07, line_width=0.4)
    pl.add_mesh(
        sliced2, scalars=fname, cmap="plasma", clim=[0, 2.0], show_scalar_bar=False
    )
    pl.add_title(f"YZ at stub x={RES_POS:.2f} m", font_size=8, color="white")
    pl.camera_position = [
        (RES_POS - 0.5, -0.02, 0.02),
        (RES_POS, 0.07, 0.00),
        (0, 0, 1),
    ]

    pl.show(auto_close=False)
    sp = f"{scr_dir}/{freq:04d}.png"
    pl.screenshot(sp)
    pl.close()
    print(f"   {freq} Hz")
    screen_paths.append(sp)

# Mosaic
ncols = 4
nrows = math.ceil(len(screen_paths) / ncols)
imgs = [Image.open(p) for p in screen_paths]
w, h = imgs[0].size
mosaic = Image.new("RGB", (ncols * w, nrows * h), (20, 20, 40))
for idx, img in enumerate(imgs):
    r, c = divmod(idx, ncols)
    mosaic.paste(img, (c * w, r * h))
mosaic_path = os.path.join(OUT, "3D_pressure_mosaic.png")
mosaic.save(mosaic_path)
print(f"  Mosaic: {mosaic_path}")

# Interactive HTML at resonance
f_res = C0 / (4 * RES_L)
ref = freq_keys[np.argmin([abs(f - f_res) for f in freq_keys])]
print(f"▶ Interactive HTML at {ref} Hz …")
sliced_ref = grid.slice(normal="z", origin=(0, 0, 0))
pl2 = pv.Plotter(window_size=(1100, 650))
pl2.set_background("#0d0d1a")
pl2.add_mesh(grid, style="wireframe", color="#404060", opacity=0.12, line_width=0.6)
pl2.add_mesh(
    sliced_ref,
    scalars=f"{ref}Hz_mag",
    cmap="plasma",
    clim=[0, 2.0],
    show_scalar_bar=True,
    scalar_bar_args={"title": f"|p|  at {ref} Hz"},
)
pl2.add_title(
    f"Quarter-Wave Resonator — |p| at {ref} Hz  (resonance ≈ {f_res:.0f} Hz)",
    font_size=11,
)
pl2.camera_position = cam
html_path = os.path.join(OUT, "3D_pressure_interactive.html")
pl2.export_html(html_path)
pl2.close()
print(f"  HTML: {html_path}")

# CSV
np.savetxt(
    os.path.join(OUT, "TL_data.csv"),
    np.column_stack([FREQS, TL_fem, TL_analytic]),
    delimiter=",",
    header="freq_Hz,TL_FEM_dB,TL_analytic_dB",
    comments="",
)

print("\n✓  Outputs:")
print("   TL_quarter_wave_resonator.png  — TL vs frequency (FEM + analytic)")
print("   3D_pressure_mosaic.png         — pressure cross-sections at each freq")
print("   3D_pressure_interactive.html   — interactive 3-D viewer (open in browser)")
print("   TL_data.csv                    — raw numbers")
