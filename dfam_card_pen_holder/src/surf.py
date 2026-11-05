"""Dense, mirror-symmetric point sampling of the heightfield shell + attributes.

Per point: rim distance (3D distance to any free edge or foot line),
curvature magnitude sqrt(k1^2 + k2^2) of the mid-surface, flow parameter S.
These drive the 'dense at edges / wide on flats' Voronoi grading.
"""
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
import trimesh
from geometry_params import *

def curvature_grid(xs, ys, H, m, g):
    Hf = H.copy()
    # nan-aware fill so derivatives near the outline stay finite
    idx = ndimage.distance_transform_edt(~m, return_distances=False, return_indices=True)
    Hf = Hf[tuple(idx)]
    Hf = ndimage.gaussian_filter(Hf, 1.5)
    Hx, Hy = np.gradient(Hf, g, g)
    Hxx, Hxy = np.gradient(Hx, g, g); _, Hyy = np.gradient(Hy, g, g)
    W = np.sqrt(1 + Hx ** 2 + Hy ** 2)
    E, F, G = 1 + Hx ** 2, Hx * Hy, 1 + Hy ** 2
    L, M, N = Hxx / W, Hxy / W, Hyy / W
    det = E * G - F * F
    # shape operator S = I^-1 II ; trace(S^2) = k1^2 + k2^2
    a = (G * L - F * M) / det; b = (G * M - F * N) / det
    c = (E * M - F * L) / det; d = (E * N - F * M) / det
    K = np.sqrt(np.maximum(a * a + 2 * b * c + d * d, 0))
    return ndimage.gaussian_filter(K, 2.0)

def sample(ds=0.2, g=0.3, seed=3):
    mesh, Sv, (xs, ys, H, m) = surface_mesh(g)
    # boundary (free edges + feet) vertices
    e, cnt = np.unique(mesh.edges_sorted, axis=0, return_counts=True)
    bverts = np.unique(e[cnt == 1].ravel())
    rim_v = cKDTree(mesh.vertices[bverts]).query(mesh.vertices, workers=4)[0]
    K = curvature_grid(xs, ys, H, m, g)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    Kv = K[m]
    n = int(mesh.area / ds ** 2)
    rng = np.random.default_rng(seed)
    pts, fid = trimesh.sample.sample_surface(mesh, n, seed=seed)
    bc = trimesh.triangles.points_to_barycentric(mesh.triangles[fid], pts)
    tri = mesh.faces[fid]
    lerp = lambda a: (a[tri] * bc).sum(1)
    att = dict(rim=lerp(rim_v), K=lerp(Kv), S=lerp(Sv))
    # mirror symmetry: keep x >= 0, reflect
    keep = pts[:, 0] >= 0
    P = pts[keep]; P2 = P * [-1, 1, 1]
    P = np.vstack([P, P2])
    att = {k: np.concatenate([v[keep], v[keep]]) for k, v in att.items()}
    return P, att, mesh
