# ARBOR WAVE: DfAM 명함·볼펜 홀더 (HP MJF / PA 11 / 블랙)

전시회 샘플용 시안입니다. 좌우 대칭인 하나의 곡면 안에 명함 골과 볼펜 1자루용 소켓이 들어 있습니다.
모서리·능선·골은 **원래 면**으로 남고, 면에서 멀어질수록 **원형 핀홀**이 생겨 점점 커지다가
**보로노이 셀**로 열립니다. 바닥은 원형에 가까운 타원이고, 같은 제품끼리 포개어 쌓을 수 있습니다.
모든 이미지는 실제 출력용 메쉬(watertight)에서 렌더링했습니다.

| 항목 | 값 |
|---|---|
| 장비 / 재료 | HP Multi Jet Fusion / HP 3D HR PA 11, 블랙 염색 |
| 외곽 크기 | 113 × 100 × 64 mm |
| 질량 | **25.3 g** (24.1 cm³). 같은 형상의 2.5 mm 솔리드 셸(51.1 g) 대비 −50% |
| 보로노이 셀 | 1,491개, 1.7 mm(엣지) ~ 6.3 mm(평면) |
| 리브 | 폭 1.7~2.2 mm, 두께 2.0 mm, 반원(불노즈) 단면 |
| 최소 벽 두께 | p1 1.58 mm, 중앙값 1.80 mm |
| 밀폐 공동 / 비다양체 에지 | 0 / 0 (watertight, 164만 삼각형) |
| 적층 피치 | 13.0 mm, 10개 적층 시 181 mm |
| MJF 빌드 포개기 | 피치 27.5 mm(분말 간극 3 mm) 기준 1 빌드 약 72개 (포개지 않으면 30개) |
| 대칭 | x = 0 기준 완전 대칭 (형상, 위상최적화, 시드 모두) |

## 시안 이미지 (`renders/`)

| 파일 | 내용 |
|---|---|
| `00_hero_dark.png`, `00_in_use.png`, `00_stack.png` | 단독 렌더 (히어로 / 사용 상태 / 5단 적층) |
| `01_hero_concept.png` | 최종 시안과 핵심 수치 |
| `02_orthographic_views.png` | 정면·후면·측면·평면 |
| `03_stackable.png` | 포개어 쌓기: 피치, 적층 높이, 빌드당 수량 |
| `04_topology_optimization.png` | 3D SIMP 경계조건, 반복별 밀도, 수렴 이력 |
| `05_pattern_texture_details.png` | 면 → 핀홀 → 셀 전이, 펜 소켓, 명함 골, 적층 결 텍스처 |
| `06_dfam_verification.png` | 단면, MJF 설계 규칙 체크, 재료 사용량 |

## 설계 방법

1. **형상** (`src/geometry_params.py`): 곡면을 높이장 z = H(x, y)로 정의했습니다.
   단면은 앞 에이프런 → 립 → 명함 골 → 15° 돛 → 크레스트 → 뒤 스커트 순서입니다.
   타원 반경 방향 돔과 블렌드해서 둘레 전체가 닫히고, 중앙 피크에 구배 10°의 원추형 펜 소켓을 두었습니다.
   오버행이 없어서 같은 형상끼리 포개집니다.
2. **위상최적화** (`src/topopt_shell.py`): 곡면 ±2.6 mm 밴드를 3D 설계영역으로 잡았습니다
   (1.25 mm hex8 요소 51,418개, 208,794 자유도). SIMP p=3을 쓰고 좌우 대칭을 구속했습니다.
   하중 케이스는 명함 골 4 N, 돛 5 N, 펜 소켓 입구 ±3 N 네 가지입니다.
3. **성장형 보로노이** (`src/build_model.py`, `src/surf.py`):
   - 셀 크기는 엣지 거리와 곡률로 정합니다. 메쉬가 성길수록 셀이 커지는 방식입니다.
   - 셀마다 개구율 0→1을 매깁니다. 0이면 원래 면, 작으면 시드 중심의 원형 핀홀, 1이면 보로노이 다각형입니다.
   - 리브 폭은 위상최적화 밀도로 정합니다.
   - 솔리드 면에는 1.2 mm 피치 수평 결을 넣어 프린팅 표현을 줍니다.
   - `cell_pattern()`은 앞으로 보로노이 면에 패턴을 입힐 때 쓸 자리입니다(현재 비활성).
4. **검증**: SDF를 0.25 mm 복셀 마칭큐브로 메쉬화한 뒤 섬 제거, 밀폐 공동, 최소 두께, 적층 간섭을 검사합니다.
5. **렌더** (`src/render/`): headless Chromium + three.js로 렌더링하고, `src/compose.py`로 보드를 구성합니다.

## 모델 파일 (`model/`)

- `arbor_wave_v5_PA11.3mf`: 출력용 메쉬 (mm, 압축 3MF)
- `render_lod.glb`, `to_*.glb`: 렌더·시각화용
- 전체 해상도 STL은 용량 때문에 커밋하지 않았습니다. `build_model.py`로 다시 생성합니다.

## 재생성

```bash
pip install numpy scipy scikit-image trimesh pypardiso fast-simplification pillow matplotlib
cd dfam_card_pen_holder/src
python3 topopt_shell.py        # 3D SIMP (~8분)
python3 build_model.py 0.25    # SDF → STL/GLB + data/metrics.json (~3분)
python3 to_viz.py              # 위상최적화 시각화
```

## 후처리 권장

1. 비드 블라스팅으로 탈분합니다.
2. 블랙 딥 염색을 합니다(PA 11 원색은 회색).
3. 증기 평활은 적층 결 텍스처를 연하게 만들므로 생략을 권장합니다.
