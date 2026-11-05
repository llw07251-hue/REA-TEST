"""ARBOR WAVE v3 - symmetric, stackable card + single-pen holder.

The whole part is ONE perforated shell whose mid-surface is a HEIGHTFIELD
z = H(x, y) (no overhang anywhere) -> identical parts nest into each other
when stacked (exhibition stacks, shipping, and nested MJF build packing).

  x : left-right, mirror-symmetric about x = 0
  y : front -> back,  z : up, desk plane z = 0      (mm)

Cross-section (per x): front foot -> lip crest -> card trough -> 15 deg sail
-> crest -> rear skirt -> rear foot.  Crest peaks at the centre where a
conical single-pen socket (10 deg draft, nests) drops into the shell.
"""
import os
import numpy as np

CARD_W, CARD_H, CARD_T = 90.0, 50.0, 0.35
CARD_TILT = np.deg2rad(15.0)
CARD_X0, CARD_X1 = -45.0, 45.0
TROUGH = np.array([18.0, 7.6])

ELL_A, ELL_B, ELL_YC = 56.0, 50.0, 34.0   # near-circular footprint (ellipse, ratio 1.12)
PEN_C = np.array([0.0, 45.0])       # pen socket axis (x, y)
PEN_ZB = 11.0                       # socket floor height
PEN_RB = 4.6                        # floor radius (pen tip cone sits here)
PEN_DRAFT = np.deg2rad(10.0)        # wall draft from vertical -> nestable
SHELL_T = 1.4
RHO_PA11 = 1.05e-3

def crest_h(x):
    a = np.clip(np.abs(x) / 62.0, 0, 1)
    return 40.0 + 24.0 * (1 - a ** 2) ** 1.6          # 64 mm peak at the centre

def profile_pts(x):
    """section at station x (feet at the ellipse extremes; the radial dome
    trims it to the near-circular footprint)"""
    a = np.clip(np.abs(x) / 62.0, 0, 1)
    H = crest_h(x)
    ys = 21.0 + (H - 8 - 13.0) * np.tan(CARD_TILT)
    lean = 6.0 * a ** 2
    yf, yr = ELL_YC - ELL_B, ELL_YC + ELL_B
    return np.array([
        [yf, 0.0], [yf + 11.0, 4.2], [3.5, 8.6], [9.0, 12.6], [13.2, 10.4], [TROUGH[0], TROUGH[1]],
        [21.0, 13.0], [ys, H - 8.0], [ys + 5.5 + lean, H], [ys + 15.0 + lean, H - 9.5],
        [62.0, 0.55 * H - 8.0], [73.0, 0.22 * H - 2.0], [yr, 0.0]])

def catmull(P, n=1600):
    P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        t = np.linspace(0, 1, n // (len(P) - 3), endpoint=False)[:, None]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2][None])
    return np.vstack(out)

def ell_rho(x, y):
    return np.sqrt((x / ELL_A) ** 2 + ((y - ELL_YC) / ELL_B) ** 2)

def end_dome(x, y):
    """radial closure: the shell rises from the desk all round the near-circular
    footprint (finite slope at the desk keeps the part nestable)"""
    r = np.clip(ell_rho(x, y), 0, 1)
    return 72.0 * (1 - r ** 3)

def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)

def heightfield(g=0.3):
    """xs, ys, H (nan outside), S (arc-length flow parameter), mask.
    x grid is exactly symmetric about 0."""
    n = int(np.ceil((ELL_A + 1) / g))
    xs = np.arange(-n, n + 1) * g
    ys = np.arange(ELL_YC - ELL_B - 0.5, ELL_YC + ELL_B + 0.5 + 1e-9, g)
    H = np.full((len(xs), len(ys)), np.nan); S = np.zeros_like(H); SN = np.zeros_like(H)
    for i, x in enumerate(xs[n:]):
        C = catmull(profile_pts(x))
        seg = np.linalg.norm(np.diff(C, axis=0), axis=1); s = np.concatenate([[0], np.cumsum(seg)])
        ok = (ys >= C[0, 0]) & (ys <= C[-1, 0])
        for ii in {n + i, n - i}:
            H[ii, ok] = np.interp(ys[ok], C[:, 0], C[:, 1])
            S[ii, ok] = np.interp(ys[ok], C[:, 0], s)
            SN[ii, ok] = S[ii, ok] / s[-1]
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    inside = np.isfinite(H) & (ell_rho(X, Y) <= 1.0)
    r = np.hypot(X - PEN_C[0], Y - PEN_C[1])
    zw = PEN_ZB + np.maximum(r - PEN_RB, 0) / np.tan(PEN_DRAFT)
    Hs = smin(np.nan_to_num(H, nan=0.0), end_dome(X, Y), 6.0)     # closed, flowing ends
    Hs = np.maximum(smin(Hs, zw, 3.0), 0.0)
    inside &= ~(r < 1.7)                              # drain / depowder hole in the socket floor
    Hs[~inside] = np.nan
    return xs, ys, Hs, S, inside

def surface_mesh(g=0.3):
    """triangulated heightfield + per-vertex attributes"""
    import trimesh
    xs, ys, H, S, m = heightfield(g)
    nx_, ny_ = H.shape
    vid = -np.ones(H.shape, int); vid[m] = np.arange(m.sum())
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    V = np.column_stack([X[m], Y[m], H[m]])
    a, b, c, d = vid[:-1, :-1], vid[1:, :-1], vid[1:, 1:], vid[:-1, 1:]
    f1 = np.stack([a, b, c], -1).reshape(-1, 3); f2 = np.stack([a, c, d], -1).reshape(-1, 3)
    F = np.vstack([f1[(f1 >= 0).all(1)], f2[(f2 >= 0).all(1)]])
    mesh = trimesh.Trimesh(V, F, process=False)
    return mesh, S[m], (xs, ys, H, m)

TO_H = float(os.environ.get('TO_H', 1.25))
TO_BOX = np.array([[-58.75, 58.75], [-17.5, 85.0], [0.0, 67.5]])
TO_BAND = 2.6
