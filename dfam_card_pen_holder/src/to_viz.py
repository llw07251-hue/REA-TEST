"""3D topology-optimisation visuals: envelope / passive / iteration iso-surfaces (GLB),
render job list for the BC scene, convergence plot."""
import sys, json
import numpy as np
from scipy import ndimage
from skimage import measure
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from geometry_params import *

ROOT = __file__.rsplit('/', 2)[0] + '/'
fm.fontManager.addfont('/root/.fonts/NotoSansKR.ttf')
plt.rcParams['font.family'] = 'Noto Sans KR'; plt.rcParams['axes.unicode_minus'] = False
d = np.load(ROOT + 'data/topopt_result.npz'); h = float(d['h'])

def iso(field, level, name, up=2, sig=0.5):
    f = np.pad(field.astype(np.float64), 2)
    f = ndimage.zoom(ndimage.gaussian_filter(f, sig), up, order=1)
    v, fc, _, _ = measure.marching_cubes(f, level, spacing=(h / up,) * 3)
    v += TO_BOX[:, 0] - 1.5 * h       # padded element-centre grid -> mm (box origin)
    m = trimesh.Trimesh(v, fc)
    if m.volume < 0: m.invert()
    m.export(ROOT + f'model/{name}.glb'); print(name, len(m.faces))

iso(d['incl'], 0.5, 'to_envelope', sig=0.7)
iso(d['solid'], 0.5, 'to_passive', sig=0.6)
for k in ('it1', 'it4', 'it10', 'it20', 'final'):
    iso(d[k], 0.5, f'to_{k}', sig=0.6)

log = json.load(open(ROOT + 'data/topopt_log.json'))
it = [x['it'] for x in log['history']]; c = [x['c'] for x in log['history']]
fig, ax = plt.subplots(figsize=(6.4, 3.0), dpi=220)
ax.semilogy(it, c, color='#111', lw=2.2)
for s in (1, 4, 10, 20): ax.plot(s, c[s - 1], 'o', color='#ff5a1f', ms=6)
ax.set_xlabel('반복 횟수 (iteration)'); ax.set_ylabel('가중 컴플라이언스 (Σ w·c)')
ax.grid(alpha=.3)
for s in ('top', 'right'): ax.spines[s].set_visible(False)
fig.tight_layout(); fig.savefig(ROOT + 'renders/_to_convergence.png', facecolor='white')

# BC scene: loads (arrows end at the application point) + desk supports
zc_top = TROUGH[1] + CARD_H * np.cos(CARD_TILT) - 8
ysail = 21.0 + (zc_top - 13.0) * np.tan(CARD_TILT)
nrm = [0, float(np.cos(CARD_TILT)), float(-np.sin(CARD_TILT))]
rl = PEN_RB + (55 - PEN_ZB) * np.tan(PEN_DRAFT)
arrows = [[[x, TROUGH[0], TROUGH[1] + 1], [0, 0, -1], 20, '#d62828'] for x in (-30, 0, 30)] + \
         [[[x, ysail, zc_top], nrm, 22, '#e36414'] for x in (-25, 25)] + \
         [[[-rl, PEN_C[1], 55], [1, 0, 0], 20, '#6a4c93'], [[rl, PEN_C[1], 55], [-1, 0, 0], 20, '#6a4c93']]
sup = [[float(ELL_A * np.cos(t) * 0.97), float(ELL_YC + ELL_B * np.sin(t) * 0.97)] for t in np.linspace(0, 2 * np.pi, 19)[:-1]]
json.dump(dict(arrows=arrows, supports=[[float(a), float(b)] for a, b in sup]),
          open(ROOT + 'data/bc_scene.json', 'w'))
print('ok')
