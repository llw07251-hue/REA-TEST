"""3D SIMP topology optimisation on the SHELL ENVELOPE (mirror-symmetric).

Design domain : every 2 mm hex element whose centre lies within +-2.6 mm of the
                wave shell / pen sleeve mid-surface (a 3D curved band, not a plane)
Passive solid : free rims / feet, card trough strip, pen-socket floor
Supports      : all envelope nodes touching the desk (z = 0)
Load cases    : LC1 card stack + finger press on trough       4 N  (-z)
                LC2 finger push on sail at card-top height    5 N  (sail normal)
                LC3 pen levered sideways at the socket lip    3 N  (+x)
                LC4 pen levered sideways at the socket lip    3 N  (-x)
Symmetry      : design variables averaged with their mirror (x -> -x) each step
Objective     : min sum w_i c_i  s.t. volume <= 40 % of the envelope
Output        : density field -> drives the graded perforation of the shell
"""
import sys, time, json
import numpy as np
import scipy.sparse as sp
from scipy.spatial import cKDTree
from pypardiso import spsolve
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from geometry_params import *
from surf import sample

OUT = __file__.rsplit('/', 2)[0] + '/data/'
h = TO_H
nx, ny, nz = [int(round((b[1] - b[0]) / h)) for b in TO_BOX]
print(f'grid {nx}x{ny}x{nz}')
xc, yc, zc = [TO_BOX[a, 0] + (np.arange(n) + 0.5) * h for a, n in enumerate((nx, ny, nz))]
X, Y, Z = np.meshgrid(xc, yc, zc, indexing='ij')
C = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])

P, att, _ = sample(0.5)
RIM = att['rim']
tree = cKDTree(P)
dist, idx = tree.query(C, workers=4)
incl = dist < TO_BAND
incl = (incl.reshape(nx, ny, nz) | incl.reshape(nx, ny, nz)[::-1]).ravel()
rs = np.hypot(C[:, 0] - PEN_C[0], C[:, 1] - PEN_C[1])
solid = incl & (dist < 1.6) & (RIM[idx] < 3.0)
solid |= incl & (rs < PEN_RB + 3.0) & (C[:, 2] < PEN_ZB + 4) & (dist < 1.6)       # socket bottom ring
trough = (np.abs(C[:, 1] - TROUGH[0]) < 3.0) & (C[:, 2] < TROUGH[1] + 3.0) & (np.abs(C[:, 0]) < CARD_SUPPORT + 2)
solid |= incl & trough & (dist < 1.6)
solid = (solid.reshape(nx, ny, nz) | solid.reshape(nx, ny, nz)[::-1]).ravel() & incl
active = incl & ~solid
print(f'envelope elements {incl.sum()}, passive solid {solid.sum()}, design {active.sum()}')

# ------------------------------------------------------------- reduced FE model
def ke_h8(nu=0.3):
    Cm = 1 / ((1 + nu) * (1 - 2 * nu)) * np.array([
        [1 - nu, nu, nu, 0, 0, 0], [nu, 1 - nu, nu, 0, 0, 0], [nu, nu, 1 - nu, 0, 0, 0],
        [0, 0, 0, (1 - 2 * nu) / 2, 0, 0], [0, 0, 0, 0, (1 - 2 * nu) / 2, 0], [0, 0, 0, 0, 0, (1 - 2 * nu) / 2]])
    nodes = np.array([[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
                      [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]], float)
    g = 1 / np.sqrt(3); K = np.zeros((24, 24))
    for a in (-g, g):
        for b in (-g, g):
            for c in (-g, g):
                dN = np.zeros((3, 8))
                for i, (xi, yi, zi) in enumerate(nodes):
                    dN[0, i] = xi * (1 + yi * b) * (1 + zi * c) / 8
                    dN[1, i] = yi * (1 + xi * a) * (1 + zi * c) / 8
                    dN[2, i] = zi * (1 + xi * a) * (1 + yi * b) / 8
                dN *= 2.0
                B = np.zeros((6, 24))
                for i in range(8):
                    B[0, 3 * i] = dN[0, i]; B[1, 3 * i + 1] = dN[1, i]; B[2, 3 * i + 2] = dN[2, i]
                    B[3, 3 * i] = dN[1, i]; B[3, 3 * i + 1] = dN[0, i]
                    B[4, 3 * i + 1] = dN[2, i]; B[4, 3 * i + 2] = dN[1, i]
                    B[5, 3 * i] = dN[2, i]; B[5, 3 * i + 2] = dN[0, i]
                K += B.T @ Cm @ B * 0.125
    return K, nodes
KE, ln = ke_h8()
eids = np.flatnonzero(incl); ne = len(eids)
I, J, K_ = np.unravel_index(eids, (nx, ny, nz))
nnx, nny = nx + 1, ny + 1
gn = np.stack([(I + (n[0] > 0)) + nnx * ((J + (n[1] > 0)) + nny * (K_ + (n[2] > 0))) for n in ln], 1)
uniq, conn = np.unique(gn, return_inverse=True); conn = conn.reshape(ne, 8)
nn = len(uniq); ndof = 3 * nn
edof = np.repeat(conn * 3, 3, axis=1) + np.tile([0, 1, 2], 8)
iK = np.repeat(edof, 24, axis=1).ravel(); jK = np.tile(edof, 24).ravel()
NI = uniq % nnx; NJ = (uniq // nnx) % nny; NK = uniq // (nnx * nny)
NX, NY, NZ = NI * h, NJ * h, NK * h
print('reduced dofs', ndof)

fixn = np.flatnonzero(NK == 0)
fixed = np.concatenate([3 * fixn, 3 * fixn + 1, 3 * fixn + 2])
free = np.setdiff1d(np.arange(ndof), fixed)
NX = NX + TO_BOX[0, 0]; NY = NY + TO_BOX[1, 0]; NZ = NZ + TO_BOX[2, 0]
F = np.zeros((ndof, 4))
def add(mask, vec, col):
    ids = np.flatnonzero(mask); assert ids.size, col
    for d in range(3): F[3 * ids + d, col] += vec[d] / ids.size
inx = np.abs(NX) < CARD_SUPPORT
add(inx & (np.abs(NY - TROUGH[0]) < 2.5) & (np.abs(NZ - TROUGH[1]) < 2.5), (0, 0, -4.0), 0)
zc_top = TROUGH[1] + CARD_H * np.cos(CARD_TILT) - 8
ysail = 21.0 + (zc_top - 13.0) * np.tan(CARD_TILT)
add(inx & (np.abs(NZ - zc_top) < 2.1) & (np.abs(NY - ysail) < 2.5),
    np.array([0, np.cos(CARD_TILT), -np.sin(CARD_TILT)]) * 5.0, 1)
nr = np.hypot(NX - PEN_C[0], NY - PEN_C[1])
lip = (NZ > 50) & (NZ < 60) & (nr < PEN_RB + (55 - PEN_ZB) * np.tan(PEN_DRAFT) + 3)
add(lip, (3.0, 0, 0), 2); add(lip, (-3.0, 0, 0), 3)
print('load nodes', [int((F[:, c] != 0).sum() // 3) for c in range(4)])

# ------------------------------------------------------------- filter (on envelope elements)
rmin = 1.6
ctr = np.column_stack([I, J, K_]).astype(float)
et = cKDTree(ctr)
pairs = et.sparse_distance_matrix(et, rmin, output_type='coo_matrix')
w = rmin - pairs.data
Hf = sp.csr_matrix((np.concatenate([w, np.full(ne, rmin)]),
                    (np.concatenate([pairs.row, np.arange(ne)]), np.concatenate([pairs.col, np.arange(ne)]))), (ne, ne))
Hs = np.asarray(Hf.sum(1)).ravel()

sol = solid[eids]; act = active[eids]
lut = -np.ones(nx * ny * nz, int); lut[eids] = np.arange(ne)
mir = lut[np.ravel_multi_index((nx - 1 - I, J, K_), (nx, ny, nz))]
assert (mir >= 0).all(), 'envelope not symmetric'
volfrac = 0.40
x = np.where(sol, 1.0, volfrac)
penal, Emin = 3.0, 1e-6
wts = np.array([1.0, 1.5, 1.0, 1.0])
hist, snaps = [], {}
snap_iters = {1, 4, 10, 20}
t0 = time.time()
for it in range(1, 61):
    xp = (Hf @ x) / Hs; xp[sol] = 1.0
    E = Emin + xp ** penal * (1 - Emin)
    Kg = sp.coo_matrix(((KE.ravel()[None] * E[:, None]).ravel(), (iK, jK)), shape=(ndof, ndof)).tocsr()
    U = np.zeros((ndof, 4)); U[free] = spsolve(Kg[free][:, free], F[free])
    c = 0.0; dc = np.zeros(ne)
    for lc in range(4):
        ue = U[edof, lc]; ce = np.einsum('ij,jk,ik->i', ue, KE, ue)
        c += wts[lc] * (E * ce).sum(); dc += wts[lc] * (-penal * xp ** (penal - 1) * (1 - Emin) * ce)
    dc = Hf @ (dc / Hs); dv = Hf @ (np.ones(ne) / Hs)
    l1, l2, mv = 1e-12, 1e12, 0.15
    xa = x[act]; dca = np.minimum(dc[act], -1e-15); dva = dv[act]; tgt = volfrac * act.sum()
    while (l2 - l1) / (l1 + l2) > 1e-4:
        lm = 0.5 * (l1 + l2)
        xn = np.clip(xa * np.sqrt(-dca / dva / lm), np.maximum(0, xa - mv), np.minimum(1, xa + mv))
        l1, l2 = (lm, l2) if xn.sum() > tgt else (l1, lm)
    x_old = x.copy(); x[act] = xn; x = 0.5 * (x + x[mir]); ch = np.abs(x - x_old).max()
    hist.append(dict(it=it, c=float(c), change=float(ch)))
    print(f'it {it:3d} c={c:9.3f} ch={ch:.3f} t={time.time()-t0:5.0f}s', flush=True)
    full = np.zeros(nx * ny * nz, np.float32); full[eids] = xp
    if it in snap_iters: snaps[f'it{it}'] = full.reshape(nx, ny, nz)
    if ch < 0.01 and it > 25: break
xp = (Hf @ x) / Hs; xp[sol] = 1.0
full = np.zeros(nx * ny * nz, np.float32); full[eids] = xp
snaps['final'] = full.reshape(nx, ny, nz)
np.savez_compressed(OUT + 'topopt_result.npz', rho=snaps['final'], incl=incl.reshape(nx, ny, nz),
                    solid=solid.reshape(nx, ny, nz), h=h, **snaps)
json.dump(dict(grid=[nx, ny, nz], h=h, envelope_elements=int(ne), design_elements=int(act.sum()),
               volfrac=volfrac, penal=penal, rmin_mm=rmin * h, dofs=int(ndof), history=hist,
               load_nodes=[int((F[:, c] != 0).sum() // 3) for c in range(4)]),
          open(OUT + 'topopt_log.json', 'w'), indent=1)
print('done', time.time() - t0)
