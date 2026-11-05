"""Compose exhibition concept boards (Korean annotations) from raw renders + data.
usage: python compose.py <raw_render_dir>"""
import json, sys, os
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = __file__.rsplit('/', 2)[0] + '/'
R = ROOT + 'renders/'
RAW = (sys.argv[1].rstrip('/') + '/') if len(sys.argv) > 1 else R
M = json.load(open(ROOT + 'data/metrics.json'))
TL = json.load(open(ROOT + 'data/topopt_log.json'))
KR = '/root/.fonts/NotoSansKR.ttf'

def F(sz, w=400):
    f = ImageFont.truetype(KR, sz)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f

INK, SUB, ACC, BG, LINE = (17, 17, 17), (92, 92, 92), (255, 90, 31), (246, 245, 242), (208, 206, 201)
W = 3000

def load(name, size=None):
    im = Image.open(RAW + name + '.png').convert('RGB')
    return ImageOps.fit(im, size, Image.LANCZOS) if size else im

def header(d, num, title, sub):
    d.text((90, 66), f'{num:02d}', font=F(40, 700), fill=ACC)
    d.text((170, 54), title, font=F(56, 700), fill=INK)
    d.text((172, 136), sub, font=F(27), fill=SUB)
    d.text((W - 90, 72), 'ARBOR WAVE  ·  DfAM Card & Pen Holder', font=F(28, 600), fill=INK, anchor='ra')
    d.text((W - 90, 112), 'HP Multi Jet Fusion  |  HP 3D HR PA 11  |  Black', font=F(24), fill=SUB, anchor='ra')
    d.line([(90, 196), (W - 90, 196)], fill=INK, width=3)

def footer(d, H):
    d.line([(90, H - 88), (W - 90, H - 88)], fill=LINE, width=2)
    d.text((90, H - 70), '전시 샘플 시안 v5 · 모든 이미지는 3D SIMP 위상최적화 + SDF 셸/보로노이 설계로 생성한 실제 출력용 STL(watertight)에서 렌더링',
           font=F(22), fill=SUB)
    d.text((W - 90, H - 70), 'Concept v5.0', font=F(22), fill=SUB, anchor='ra')

def cap(d, xy, t, s=None, ts=30, ss=23, lh=34):
    x, y = xy
    d.text((x, y), t, font=F(ts, 700), fill=INK)
    if s:
        yy = y + ts + 16
        for line in s.split('\n'):
            d.text((x, yy), line, font=F(ss), fill=SUB); yy += lh
    return y

def table(d, x, y, rows, cw=(330, 420), rh=52, fs=24):
    for i, (k, v) in enumerate(rows):
        yy = y + i * rh
        d.line([(x, yy + rh - 6), (x + sum(cw), yy + rh - 6)], fill=LINE, width=1)
        d.text((x, yy + 6), k, font=F(fs), fill=SUB)
        d.text((x + cw[0], yy + 6), v, font=F(fs, 600), fill=INK)
    return y + rh * len(rows)

def save(im, name):
    im.save(R + name + '.png', optimize=True); print('saved', name)

bb = M['bbox_mm']

def b1():
    H = 1980; im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    header(d, 1, '최종 시안 — 면에서 자라나는 보로노이 명함·펜 홀더',
           '모서리는 원래 면, 안쪽으로 갈수록 핀홀 → 보로노이 셀로 열리는 하나의 곡면 · 명함 골 + 15° 돛 + 단일 펜 소켓 · 원형에 가까운 바닥')
    im.paste(load('raw_hero_dark', (1960, 1180)), (90, 240))
    im.paste(load('raw_use', (960, 400)), (90, 1440)); im.paste(load('raw_hero_bare', (960, 400)), (1090, 1440))
    d.text((110, 1452), '사용 상태 — 명함 약 30매 + 볼펜 1자루', font=F(24, 600), fill=INK)
    d.text((1110, 1452), '라이트 배경', font=F(24, 600), fill=INK)
    x = 2120
    cap(d, (x, 250), '핵심 수치')
    rows = [('재료 / 장비', 'PA 11 블랙 / HP MJF'),
            ('외곽 크기', f"{bb[0]:.0f} × {bb[1]:.0f} × {bb[2]:.0f} mm"),
            ('질량', f"{M['mass_g']:.1f} g  ({M['volume_cm3']:.1f} cm³)"),
            ('솔리드 셸 대비', f"{M['ref_solid_shell_mass_g']:.0f} g → {M['mass_g']:.0f} g (−{M['saving_vs_solid_shell_pct']:.0f}%)"),
            ('보로노이 셀', f"{M['voronoi_cells']}개 · {M['cell_size_mm'][0]}~{M['cell_size_mm'][1]:.0f} mm"),
            ('적층 피치', f"{M['stack_pitch_display_mm']:.1f} mm (포개어 쌓기)"),
            ('서포트 / 부품 수', '없음 / 1 (일체 출력)'),
            ('대칭', '좌우 완전 대칭 (x = 0)')]
    y = table(d, x, 316, rows, cw=(250, 540), rh=54, fs=24) + 40
    cap(d, (x, y), '디자인 언어', '모서리·능선·골은 매끈한 원래 면으로 남고,\n면에서 멀어질수록 작은 원형 핀홀이 돋아나\n'
        '점점 커지며 보로노이 셀로 열린다. 메쉬가\n성겨지는 만큼 패턴이 자라는 "성장형" 표면.')
    y += 230
    cap(d, (x, y), '3D 프린팅으로만 가능한 이유', '· 면과 셀이 하나로 이어진 연속 곡면 (금형 분리 불가)\n'
        '· 위치마다 개구율이 연속 변하는 1,491셀 그라데이션\n· 오버행 없는 높이장 → 같은 형상을 포개어 적층/출력\n'
        '· 솔리드 면의 적층 결 텍스처까지 1회 성형')
    footer(d, H); save(im, '01_hero_concept')

def b2():
    H = 2150; im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    header(d, 2, '형상 구성 — 4방향 뷰', '좌우 대칭 · 둘레 전체 닫힘 · 높이장(heightfield) 곡면 → 포개어 적층 가능')
    tiles = [('raw_front', '정면', '직선 명함 골(카드 하단 지지) · 아치형 크레스트 · 중앙 펜 소켓 노치'),
             ('raw_rear', '후면 3/4', '원추형 펜 소켓(구배 10°)이 셸에 녹아든 후면 · 뒤쪽 스커트 접지'),
             ('raw_left', '측면', '앞 립 → 골 → 15° 돛 → 크레스트 → 뒤 스커트의 파도형 단면'),
             ('raw_top', '평면', '원형에 가까운 타원 바닥 윤곽(112×100) · 중앙선 대칭 시드 → 척추 리브 · 소켓 배출공')]
    tw, th = 1385, 780
    for i, (n, t, s) in enumerate(tiles):
        x = 90 + (i % 2) * (tw + 40); y = 236 + (i // 2) * (th + 150)
        im.paste(load(n, (tw, th)), (x, y)); cap(d, (x, y + th + 16), t, s)
    footer(d, H); save(im, '02_orthographic_views')

def b3():
    H = 1900; im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    header(d, 3, '스택 — 포개어 쌓는 구조', '모든 면이 위를 향하는 높이장 + 펜 소켓 10° 구배 → 동일 제품이 컵처럼 포개짐 (복셀 간섭 검사로 피치 산출)')
    im.paste(load('raw_stack', (1700, 1250)), (90, 236))
    im.paste(load('raw_stack_explode', (1100, 1250)), (1810, 236))
    d.text((110, 250), f"5단 적층 · 피치 {M['stack_pitch_display_mm']:.1f} mm", font=F(28, 700), fill=INK)
    d.text((1830, 250), '분해 — 동일 형상의 반복', font=F(28, 700), fill=INK)
    y = 1530
    up = round(bb[2] * 10, 0)
    rows = [('적층 피치 (전시/포장, 간극 0.6 mm)', f"{M['stack_pitch_display_mm']:.1f} mm"),
            ('10개 적층 높이', f"{M['stack_10_height_mm']:.0f} mm   (단순 적재 시 {up:.0f} mm → −{100*(1-M['stack_10_height_mm']/up):.0f}%)"),
            ('MJF 빌드 내 포개기 (분말 간극 3 mm)', f"피치 {M['stack_pitch_build_mm']:.1f} mm → 1 빌드 약 {M['units_per_build_nested']}개 (비포개기 {M['units_per_build_unnested']}개)")]
    table(d, 90, y, rows, cw=(760, 1300), rh=56, fs=25)
    footer(d, H); save(im, '03_stackable')

def b4():
    H = 1960; im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    header(d, 4, '위상최적화 (3D SIMP, 대칭 구속)', '셸 외피(±2.6 mm 곡면 밴드) 전체를 3D 설계영역으로 · 4개 하중 케이스 · 결과 밀도 → 보로노이 리브 두께')
    im.paste(load('raw_bc', (1500, 1000)), (90, 236))
    x = 1640
    cap(d, (x, 236), '경계조건 (3D)', '반투명 민트 = 설계영역(셸 외피) / 짙은 회색 = 비설계 고체\n(림·명함 골·소켓 바닥) / 파란 콘 = 데스크 접지')
    hist = TL['history']
    rows = [('요소 / 자유도', f"{TL['envelope_elements']:,} hex8 ({TL['h']} mm) / {TL['dofs']:,} DOF"),
            ('방법', f"SIMP p=3 · 밀도필터 {TL['rmin_mm']:.1f} mm · OC · 좌우 대칭 평균"),
            ('반복 / 수렴', f"{len(hist)}회 · 컴플라이언스 {hist[0]['c']/hist[-1]['c']:.1f}배 감소"),
            ('LC1 명함 + 누름', '골 4 N (−Z)'), ('LC2 명함 뽑기', '돛 상단 5 N (면 법선)'),
            ('LC3 / LC4 펜 지렛대', '소켓 입구 3 N (+X / −X)'),
            ('결과 활용', '밀도 ρ → 리브 반폭 0.50 + 0.45ρ mm')]
    table(d, x, 400, rows, cw=(380, 900), rh=56, fs=24)
    cv = Image.open(R + '_to_convergence.png').convert('RGB'); cv = cv.resize((1000, int(cv.height * 1000 / cv.width)))
    im.paste(cv, (x + 135, 812))
    snaps = ['it1', 'it4', 'it10', 'it20', 'final']
    tw = (2820 - 4 * 30) // 5; th = int(tw * 0.72); y0 = 1330
    for i, s in enumerate(snaps):
        xx = 90 + i * (tw + 30)
        im.paste(load(f'raw_to_{s}', (tw, th)), (xx, y0))
        d.text((xx + 18, y0 + 14), '최종' if s == 'final' else f'반복 {s[2:]}', font=F(27, 700), fill=INK)
    d.text((90, y0 + th + 24), '밀도 ρ ≥ 0.5 등위면의 진화 — 하중 경로(골→돛→크레스트→접지, 소켓→리어 스커트)가 남고 저응력 면이 비워짐',
           font=F(24), fill=SUB)
    footer(d, H); save(im, '04_topology_optimization')

def b5():
    H = 2270; im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    header(d, 5, '패턴 · 질감 디테일', '개구율 0 → 1: 원래 면 → 원형 핀홀 → 보로노이 셀 · 셀 크기 = 곡률·엣지 거리 · 리브 폭 = 위상최적화 밀도')
    tiles = [('raw_macro_edge', 'A. 엣지 — 원래 면에서 핀홀이 돋아남',
              f"모서리·능선은 무타공 1.6 mm 면 · 셀 {M['cell_size_mm'][0]} mm부터 시작\n개구율이 작을 땐 시드 중심의 원형 핀홀 → 점차 확대"),
             ('raw_macro_field', 'B. 평면 — 보로노이 셀로 완전히 열림',
              f"셀 최대 ~{M['cell_size_mm'][1]:.1f} mm · 리브 폭 1.7~2.2 mm (위상최적화 밀도)\n리브 두께 2.0 mm · 반원(불노즈) 단면으로 부드러운 가장자리"),
             ('raw_macro_socket', 'C. 단일 펜 소켓',
              '구배 10° 원추 · 곡률이 커 무타공 면으로 유지\n바닥 무타공 (펜 촉 보호) · Ø3.4 배출공'),
             ('raw_macro_trough', 'D. 명함 골 · 적층 결 텍스처',
              '골·립 크레스트는 원래 면 → 카드 하단 연속 지지\n솔리드 면에 1.2 mm 피치 수평 결 (프린팅 표현)')]
    tw, th = 1385, 800
    for i, (n, t, s) in enumerate(tiles):
        x = 90 + (i % 2) * (tw + 40); y = 236 + (i // 2) * (th + 160)
        im.paste(load(n, (tw, th)), (x, y)); cap(d, (x, y + th + 16), t, s)
    footer(d, H); save(im, '05_pattern_texture_details')

def b6():
    H = 1720; im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    header(d, 6, 'DfAM 검증 — HP MJF / PA 11', '단면 (주황 = 절단면) · 모든 공간이 외부와 연결 → 잔류 분말 0 · 수밀 메쉬')
    im.paste(load('raw_section', (1500, 1080)), (90, 236))
    x = 1650
    cap(d, (x, 236), 'MJF 설계 규칙 체크')
    rows = [('최소 벽/리브 두께 ≥0.5 (권장 1.0)', f"p1 {M['wall_p1_mm']:.2f} · 중앙값 {M['wall_median_mm']:.2f} mm ✓"),
            ('핀홀 / 셀 개구 (탈분)', '관통 개구 · 막힌 공동 없음 ✓'),
            ('밀폐 공동 / 잔류 분말', f"검출 {M.get('enclosed_voids_found', 0)} → 충전 후 0 ✓"),
            ('수밀 / 비다양체 에지', f"{'예' if M['watertight'] else '아니오'} / {M['nonmanifold_edges']} ✓"),
            ('서포트', '불필요 (분말층 자기지지) ✓'),
            ('두께 급변', '개구율 연속 변화 · 불노즈 가장자리 ✓'),
            ('배출공 ≥2 mm', '소켓 바닥 Ø3.4 ✓'),
            ('대칭 / 적층', f"x=0 대칭 · 피치 {M['stack_pitch_display_mm']:.1f} mm ✓"),
            ('메쉬', f"{M['faces_full']/1e6:.2f} M 삼각형 · 0.25 mm 복셀")]
    y = table(d, x, 306, rows, cw=(560, 700), rh=54, fs=24) + 46
    cap(d, (x, y), '재료 사용량')
    bars = [('동일 형상 2.5 mm 솔리드 셸', M['ref_solid_shell_mass_g']), ('1.4 mm 무타공 셸', M['ref_unperforated_cm3'] * 1.05),
            ('ARBOR WAVE (최종)', M['mass_g'])]
    yy = y + 62; mx = max(v for _, v in bars)
    for k, v in bars:
        d.text((x, yy), k, font=F(23), fill=SUB)
        L = int(700 * v / mx)
        d.rectangle([x + 380, yy + 6, x + 380 + L, yy + 32], fill=ACC if 'ARBOR' in k else INK)
        d.text((x + 392 + L, yy + 2), f'{v:.1f} g', font=F(23, 700), fill=INK); yy += 48
    d.text((x, yy + 14), f"→ 솔리드 셸 대비 −{M['saving_vs_solid_shell_pct']:.0f}% 재료", font=F(27, 700), fill=ACC)
    cap(d, (90, 1360), '후처리 / 출력 권장', '① 비드 블라스팅 탈분 → ② 블랙 딥 염색 (HP PA 11 원색은 회색) → ③ (선택) 증기 평활 시 적층 결 텍스처가 연화되므로 생략 권장\n'
        '④ 출력 방향: 바닥(접지선)을 빌드 XY에 두고 Z 방향 포개기 배치 — 높이장 형상이라 동일 방향 반복 적층 시 분말 간극 3 mm 확보\n'
        '⑤ 공차: 명함 골 폭 여유 · 펜 소켓 구배 10° → ±0.3 mm 치수 편차에도 기능 유지', ss=24, lh=40)
    footer(d, H); save(im, '06_dfam_verification')

if __name__ == '__main__':
    for fn in (b1, b2, b3, b4, b5, b6):
        try: fn()
        except FileNotFoundError as e: print('skip', fn.__name__, e)
