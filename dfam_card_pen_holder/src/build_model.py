"""Build the final printable part (SDF -> marching cubes -> watertight STL).

ONE mirror-symmetric heightfield mid-surface (card cradle wave + single-pen socket)
carrying an ORGANIC 3D Voronoi strut network (no plate, no fillets):
  * every Voronoi edge = elliptical tube, radius field swells toward nodes,
    centre-lines woven +-0.7 mm out of the mid-surface
  * round rim tube along every free edge, two card rails, solid socket floor
  * edge-graded Voronoi: cell size from GEOMETRY - dense (2.3 mm) along every
    edge, rim, foot, crease (lip crest, trough, crest ridge, socket lip),
    opening up to ~11 mm on flat panels; rib width from the 3D SIMP density
  * mirror-symmetric seeds (pattern is symmetric; centre-line spine rib)
  * stack check: minimal nesting pitch for display stacks & nested build packing
Usage: python build_model.py [voxel_mm]
"""
import sys, json, time, os
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage import measure
import trimesh, fast_simplification
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from geometry_params import *
from surf import sample

ROOT = os.environ.get('OUT_ROOT', __file__.rsplit('/', 2)[0] + '/')
TO_NPZ = os.environ.get('TO_NPZ', __file__.rsplit('/', 2)[0] + '/data/topopt_result.npz')
HF = float(sys.argv[1]) if len(sys.argv) > 1 else 0.25
SUB = 4
HC = HF * SUB
rng = np.random.default_rng(11)
t0 = time.time()

def smin(a, b, k):
    hh = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - hh) + a * hh - k * hh * (1 - hh)

# ------------------------------------------------------------------ surface + TO density on it
P, att, _ = sample(0.2)
RIM, KK, Q = att['rim'], att['K'], att['S']
to = np.load(TO_NPZ)
SIG = 2.0 / float(to['h'])
rho = ndimage.gaussian_filter(to['rho'].astype(np.float64), SIG)
occ = ndimage.gaussian_filter(to['incl'].astype(np.float64), SIG)
rho_n = np.where(occ > 1e-3, rho / np.maximum(occ, 1e-3), 0)
th = float(to['h'])
def rho_at(X):
    c = ((X - TO_BOX[:, 0]) / th - 0.5).T
    return np.clip(ndimage.map_coordinates(rho_n, c, order=1, mode='nearest'), 0, 1)
r = rho_at(P)
rs = np.hypot(P[:, 0] - PEN_C[0], P[:, 1] - PEN_C[1])
# ---- edge-graded cell size: dense on edges & creases, wide on flats
flat = np.clip((RIM - 1.5) / 14.0, 0, 1) ** 1.3 * np.exp(-KK / 0.06)
sp_ = (1.8 + 4.7 * flat) * (1 - 0.08 * r)          # 1.8 mm at edges -> ~6.5 mm on flats
STRETCH = np.array([0.85, 1.0, 1.0])
Ps = P * STRETCH
half = np.flatnonzero(P[:, 0] >= 0)
order = rng.permutation(half)[: len(half) // 3]
cell = 2.0; grid = {}; seeds = []
def free_at(p, rr):
    key = (p // cell).astype(int); n = int(np.ceil(rr / cell))
    for dx in range(-n, n + 1):
        for dy in range(-n, n + 1):
            for dz in range(-n, n + 1):
                for q in grid.get((key[0] + dx, key[1] + dy, key[2] + dz), ()):
                    if (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2 < rr * rr:
                        return False
    return True
def put(p):
    grid.setdefault(tuple((p // cell).astype(int)), []).append(p)
for i in order:
    p = Ps[i].copy(); rr = sp_[i]
    if p[0] < 0.45 * rr: p[0] = 0.0                 # snap onto the symmetry plane
    m = p * [-1, 1, 1]
    if free_at(p, rr) and (p[0] == 0 or free_at(m, rr)):
        put(p); seeds.append(p)
        if p[0] > 0: put(m); seeds.append(m)
seeds = np.array(seeds)
# ---- graded-aperture attributes
# aperture 0 = original solid surface (edges, creases, socket), small = pin-holes,
# 1 = fully open Voronoi cell.  Cell size follows the same field ("triangles grow").
APER = np.clip((flat - 0.02) / 0.7, 0, 1) ** 1.3 * (1 - 0.2 * r)
SH = dict(P=P, N=att['n'], tree=cKDTree(P), seeds=seeds, stree=cKDTree(seeds), rho=r, RIM=RIM, sp=sp_,
          ap=APER, Q=Q)
print(f'{len(P)} surface pts, {len(seeds)} Voronoi cells (symmetric), open area share {np.mean(APER > 0.5):.2f}, t={time.time()-t0:.0f}s')

P_SE = 3.5                                    # superellipse exponent of the rib cross-section
def cell_pattern(e, cell_id, X):
    """hook for a future surface pattern on the Voronoi faces (returns 0 now)"""
    return 0.0

def organic_sdf(X):
    """One continuous surface whose Voronoi cells open gradually:
    solid skin at edges -> pin-holes -> open cells on flat areas.
    Rib cross-section is a superellipse in (edge distance, normal offset),
    so skin, pores and ribs are one field (no fillet operation)."""
    S = SH
    d, i = S['tree'].query(X, workers=4, distance_upper_bound=6.0)
    far = ~np.isfinite(d); i[far] = 0; d[far] = 6.0
    v = X - S['P'][i]
    w = (v * S['N'][i]).sum(1)                                   # signed normal offset
    u = np.sqrt(np.maximum(d ** 2 - w ** 2, 0))                  # lateral offset beyond the outline
    dd, ii = S['stree'].query(X * STRETCH, k=4, workers=4)
    s1 = S['seeds'][ii[:, 0]]
    es = np.stack([(dd[:, k] ** 2 - dd[:, 0] ** 2) / (2 * np.linalg.norm(S['seeds'][ii[:, k]] - s1, axis=1) + 1e-9)
                   for k in range(1, 4)], 1)
    e = -0.3 * np.log(np.exp(-es / 0.3).sum(1))                  # distance to the cell border
    ap, spi, rho_i, rim = S['ap'][i], S['sp'][i], S['rho'][i], S['RIM'][i]
    t = 1.6 + 0.4 * ap + 0.6 * np.exp(-rim / 1.5)                # skin 1.6 mm, deeper ribs where open
    # hole: round pin-hole around the seed while the aperture is small,
    # morphing into the (rounded) Voronoi polygon as the aperture opens
    hw_open = 0.85 + 0.25 * rho_i                                 # rib half width of a fully open cell
    circle = dd[:, 0] - ap * 0.62 * spi
    poly = hw_open - e
    hole = (1 - ap) * circle + ap * poly                          # < 0 inside the hole
    g = hole                                                      # distance into material from the hole edge (>0)
    rib = np.where(g < t / 2, np.hypot(t / 2 - g, w) - t / 2, np.abs(w) - t / 2)   # half-round (bull-nose) hole edge
    # outline: the skin ends in a half-round edge of its own thickness
    rsg = rim - u                                                # signed in-surface distance to the outline
    cap = np.where(rsg < t / 2, np.hypot(t / 2 - rsg, w) - t / 2, -1e3)
    rib = np.maximum(rib, cap)
    # printed-strata texture on the skin (design intent, 1.2 mm pitch)
    rib += 0.08 * np.sin(2 * np.pi * X[:, 2] / 1.2) * (1 - ap) * np.clip(rim / 2.0, 0, 1)
    rib += cell_pattern(e, ii[:, 0], X)
    rr = np.hypot(X[:, 0] - PEN_C[0], X[:, 1] - PEN_C[1])
    floor = np.maximum(np.maximum(rr - (PEN_RB + 0.3), np.abs(X[:, 2] - PEN_ZB) - 0.8), 1.7 - rr)
    return np.minimum(rib, floor)

def full_sdf(X):
    d = organic_sdf(X)
    return np.maximum(d, -X[:, 2])

# ------------------------------------------------------------------ narrow-band evaluation
bx = np.array([[-58.0, 58.0], [-18.0, 86.0], [-0.6, 68.0]])
nc = np.ceil((bx[:, 1] - bx[:, 0]) / HC).astype(int)
off = np.array([0.5 * HF - (62.0 % HF), 0.291 * HF, 0.413 * HF])   # x grid symmetric about 0
xc = [bx[a, 0] + off[a] + (SUB * np.arange(nc[a]) + 1.5) * HF for a in range(3)]
xc[0] = (SUB * np.arange(nc[0]) + 1.5 - (nc[0] * SUB - 1) / 2) * HF        # exactly symmetric x grid
Gc = np.stack(np.meshgrid(*xc, indexing='ij'), -1).reshape(-1, 3)
dc = SH['tree'].query(Gc, workers=4, distance_upper_bound=9)[0]
band_c = (dc < 3.2 + HC).reshape(nc) & (Gc[:, 2].reshape(nc) > -HC)
print('coarse band cells', band_c.sum(), f't={time.time()-t0:.0f}s')
nf = nc * SUB
xf = [bx[a, 0] + off[a] + np.arange(nf[a]) * HF for a in range(3)]
xf[0] = (np.arange(nf[0]) - (nf[0] - 1) / 2) * HF
D = np.full(tuple(nf), 1.0, np.float32)
SL = 16
for k0 in range(0, nf[2], SL):
    ks = np.arange(k0, min(k0 + SL, nf[2]))
    m = band_c[:, :, ks // SUB]
    m = np.repeat(np.repeat(m, SUB, 0), SUB, 1)[: nf[0], : nf[1]]
    ii, jj, kk = np.nonzero(m)
    if not len(ii): continue
    X = np.column_stack([xf[0][ii], xf[1][jj], xf[2][ks[kk]]])
    D[ii, jj, ks[kk]] = full_sdf(X)
    if k0 % (SL * 8) == 0: print(f'  z={xf[2][k0]:5.1f}  pts={len(X)}  t={time.time()-t0:.0f}s', flush=True)

# ------------------------------------------------------------------ checks + mesh
sv = D < 0
lab, n = ndimage.label(sv)
sizes = ndimage.sum(sv, lab, range(1, n + 1))
keep = 1 + int(np.argmax(sizes))
D[(lab != keep) & sv] = 0.05
print(f'solid components {n}, removed islands {n-1} ({(sizes.sum()-sizes.max())*HF**3:.2f} mm3)')
air = D >= 0
alab, an = ndimage.label(air)
border = set(np.unique(np.concatenate([alab[0].ravel(), alab[-1].ravel(), alab[:, 0].ravel(), alab[:, -1].ravel(),
                                       alab[:, :, 0].ravel(), alab[:, :, -1].ravel()])).tolist())
enclosed = [i for i in range(1, an + 1) if i not in border]
for i in enclosed:
    w_ = np.argwhere(alab == i)
    print(f'   pocket {i}: {len(w_)*HF**3:.2f} mm3 at', np.round(w_.mean(0) * HF + [xf[0][0], xf[1][0], xf[2][0]], 1))
    D[alab == i] = -0.5 * HF                 # fill: no trapped powder allowed
print('enclosed air pockets:', len(enclosed))
# minimum wall thickness check (voxel EDT inside solid, on the medial ridge)
edt = ndimage.distance_transform_edt(D < 0) * HF
ridge = (edt == ndimage.maximum_filter(edt, size=5)) & (edt > 1.5 * HF)
wall = 2 * edt[ridge]
print(f'wall thickness on medial ridge: p1={np.percentile(wall,1):.2f}  p5={np.percentile(wall,5):.2f}  median={np.median(wall):.2f} mm')

D = ndimage.gaussian_filter(D, 0.6)          # removes voxel-scale MC ambiguities / jaggies
v, f, _, _ = measure.marching_cubes(D, 0.0, spacing=(HF, HF, HF))
v += np.array([xf[0][0], xf[1][0], xf[2][0]])
mesh = trimesh.Trimesh(v, f, process=True)
mesh.update_faces(mesh.nondegenerate_faces()); mesh.remove_unreferenced_vertices()
_, cnt = np.unique(mesh.edges_sorted, axis=0, return_counts=True)
nonman = int((cnt != 2).sum())
print('non-manifold edges', nonman)
if mesh.volume < 0: mesh.invert()
print('mesh', len(mesh.faces), 'watertight', mesh.is_watertight, f't={time.time()-t0:.0f}s')
vol = mesh.volume; mass = vol * RHO_PA11; bb = mesh.bounds
os.makedirs(ROOT + 'model', exist_ok=True)
mesh.export(ROOT + 'model/arbor_wave_v4_PA11.stl')
v2, f2 = fast_simplification.simplify(mesh.vertices.astype(np.float32), mesh.faces.astype(np.int32),
                                      max(0.0, 1 - 2.2e6 / len(mesh.faces)))
trimesh.Trimesh(v2, f2).export(ROOT + 'model/render.glb')
v3, f3 = fast_simplification.simplify(mesh.vertices.astype(np.float32), mesh.faces.astype(np.int32),
                                      1 - 1.5e5 / len(mesh.faces))
trimesh.Trimesh(v3, f3).export(ROOT + 'model/render_lod.glb')

# ------------------------------------------------------------------ metrics
# ---- stack (nesting) check on the voxel model
solid = D < 0
def min_pitch(sol, hv, clear):
    dil = ndimage.distance_transform_edt(~sol) * hv <= clear
    prev = None
    for k in range(1, sol.shape[2]):
        hit = sol[:, :, k:] & dil[:, :, :-k]
        if not hit.any():
            w_ = np.argwhere(prev) if prev is not None else None
            if w_ is not None and len(w_):
                print(f'   limiting contact (clear {clear} mm) near', np.round(w_.mean(0) * hv + [xf[0][0], xf[1][0], xf[2][0]], 1))
            return k * hv
        prev = hit
s2 = solid[::2, ::2, ::2]
pitch_display = min_pitch(s2, 2 * HF, 0.6)
pitch_build = min_pitch(s2, 2 * HF, 3.0)
print(f'nesting pitch: display (0.6 mm gap) {pitch_display:.1f} mm, MJF build (3 mm gap) {pitch_build:.1f} mm')
area_mid = len(P) * 0.2 * 0.2
ref_shell = area_mid * 2.5
ref_unperf = area_mid * SHELL_T
bbx = bb[1] - bb[0]
per_build = int(np.floor(380 / (bbx[0] + 3)) * np.floor(284 / (bbx[1] + 3)) * (1 + np.floor((380 - bbx[2]) / pitch_build))) if pitch_build else 0
per_build_flat = int(np.floor(380 / (bbx[0] + 3)) * np.floor(284 / (bbx[1] + 3)) * np.floor(380 / (bbx[2] + 3)))
metrics = dict(volume_cm3=round(vol / 1000, 2), mass_g=round(mass, 1),
               bbox_mm=[round(float(x), 1) for x in bbx],
               ref_solid_shell_2p5_cm3=round(ref_shell / 1000, 1), ref_solid_shell_mass_g=round(ref_shell / 1000 * 1.05, 1),
               ref_unperforated_cm3=round(ref_unperf / 1000, 1),
               saving_vs_solid_shell_pct=round(100 * (1 - vol / ref_shell), 1),
               porosity_pct=round(100 * (1 - vol / ref_unperf), 1),
               mid_surface_area_cm2=round(area_mid / 100, 1), surface_area_cm2=round(mesh.area / 100, 1),
               faces_full=int(len(mesh.faces)), watertight=bool(mesh.is_watertight),
               enclosed_voids_found=int(sum(1 for i in enclosed if (alab == i).sum() * HF ** 3 > 1.0)), enclosed_voids=0,
               voxel_pockets_filled=len(enclosed), nonmanifold_edges=nonman, islands_removed=int(n - 1),
               wall_p1_mm=round(float(np.percentile(wall, 1)), 2), wall_p5_mm=round(float(np.percentile(wall, 5)), 2),
               wall_median_mm=round(float(np.median(wall)), 2),
               voronoi_cells=int(len(seeds)), cell_size_mm=[round(float(sp_.min()), 1), round(float(sp_.max()), 1)],
               stack_pitch_display_mm=pitch_display, stack_pitch_build_mm=pitch_build,
               stack_10_height_mm=round(float(bbx[2] + 9 * pitch_display), 1),
               units_per_build_nested=per_build, units_per_build_unnested=per_build_flat,
               symmetric=True, voxel_mm=HF)
json.dump(metrics, open(ROOT + 'data/metrics.json', 'w'), indent=1)
print(json.dumps(metrics, indent=1)); print('total', round(time.time() - t0))
