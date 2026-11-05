# ARBOR WAVE: DfAM 명함·볼펜 홀더 (HP MJF / PA 11 / 블랙)

전시회 샘플용 시안입니다. 하나의 대칭 유선형 셸 안에 명함 거치부와 볼펜 1자루용 소켓을 함께 넣었고,
같은 제품끼리 포개어 쌓을 수 있습니다. 모든 이미지는 실제 출력용 메쉬(watertight)에서 렌더링했습니다.

| 항목 | 값 |
|---|---|
| 장비 / 재료 | HP Multi Jet Fusion / HP 3D HR PA 11, 블랙 염색 |
| 외곽 크기 | 114 × 102 × 63 mm (바닥 윤곽: 원형에 가까운 타원) |
| 질량 | **16.2 g** (15.5 cm³). 같은 형상의 2.5 mm 솔리드 셸(51.1 g) 대비 −68% |
| 보로노이 셀 | 751개, 2.3 mm(엣지) ~ 10.3 mm(평면) |
| 최소 리브/벽 두께 | p1 1.12 mm, 중앙값 1.50 mm |
| 밀폐 공동 / 비다양체 에지 | 0 / 0 (watertight) |
| 적층 피치 | 12.0 mm (간극 0.6 mm), 10개 적층 시 171 mm |
| MJF 빌드 포개기 | 피치 26 mm(분말 간극 3 mm) 기준 1 빌드 약 78개 (포개지 않으면 30개) |
| 대칭 | x = 0 기준 완전 대칭 (형상, 위상최적화, 시드 모두) |

## 시안 이미지 (`renders/`)

| 파일 | 내용 |
|---|---|
| `00_hero_dark.png`, `00_in_use.png`, `00_stack.png` | 단독 렌더 (히어로 / 사용 상태 / 5단 적층) |
| `01_hero_concept.png` | 최종 시안과 핵심 수치 |
| `02_orthographic_views.png` | 정면·후면·측면·평면 |
| `03_stackable.png` | 포개어 쌓기: 피치, 적층 높이, 빌드당 수량 |
| `04_topology_optimization.png` | 3D SIMP 경계조건, 반복별 밀도, 수렴 이력 |
| `05_pattern_texture_details.png` | 엣지 조밀 / 평면 확장 보로노이, 플로우 라인 텍스처, 펜 소켓, 명함 골 |
| `06_dfam_verification.png` | 단면, MJF 설계 규칙 체크, 재료 사용량 |

## 설계 방법

1. **형상** (`src/geometry_params.py`): 셸 중립면을 높이장 z = H(x, y)로 정의했습니다.
   단면은 앞 에이프런 → 립 → 명함 골 → 15° 돛 → 크레스트 → 뒤 스커트 순서이고,
   크레스트는 중앙 피크(64 mm)에서 양 끝으로 흘러내립니다. 반경 방향 돔과 스무스 블렌드해서
   타원 바닥 윤곽 전체가 닫힙니다. 중앙 피크에는 구배 10°의 원추형 펜 소켓이 있습니다.
   오버행이 없기 때문에 같은 형상끼리 포개집니다.
2. **위상최적화** (`src/topopt_shell.py`): 셸 외피 ±2.6 mm 곡면 밴드를 3D 설계영역으로 잡았습니다
   (1.25 mm hex8 요소 51,418개, 208,794 자유도). SIMP p=3, 밀도필터 2 mm, OC 갱신을 쓰고,
   매 반복마다 좌우 대칭 평균을 적용했습니다.
   하중 케이스는 명함 골 4 N, 돛 5 N, 펜 소켓 입구 ±3 N 네 가지입니다.
3. **패턴 / 질감** (`src/build_model.py`, `src/surf.py`): 셸 표면에 대칭 보로노이 시드를 심었습니다.
   셀 크기는 엣지 거리와 곡률로 정하고(엣지는 조밀, 평면은 넓게), 리브 폭은 위상최적화 밀도로 정합니다.
   림 비드는 1.4 → 2.5 mm, 플로우 라인 리플은 0.12 mm(피치 1.2 mm)입니다.
   SDF로 만든 뒤 0.25 mm 복셀 마칭큐브로 메쉬화하고, 아래 항목을 검증합니다:
   섬(떨어진 조각) 제거, 밀폐 공동, 최소 두께, 적층 간섭.
4. **렌더** (`src/render/`): headless Chromium + three.js로 렌더링하고, `src/compose.py`로 보드를 구성합니다.

## 모델 파일 (`model/`)

- `arbor_wave_v3_PA11.3mf`: 출력용 메쉬 (139만 삼각형, mm, 압축 3MF)
- `render_lod.glb`, `to_*.glb`: 렌더·시각화용
- 전체 해상도 STL(67 MB)은 용량 때문에 커밋하지 않았습니다. 아래 명령으로 다시 생성합니다.

## 재생성

```bash
pip install numpy scipy scikit-image trimesh pypardiso fast-simplification pillow matplotlib
cd dfam_card_pen_holder/src
python3 topopt_shell.py        # 3D SIMP (~8분)
python3 build_model.py 0.25    # SDF 셸 → STL/GLB + data/metrics.json
python3 to_viz.py              # 위상최적화 시각화
```

## 후처리 권장

1. 비드 블라스팅으로 탈분합니다.
2. 블랙 딥 염색을 합니다(PA 11 원색은 회색).
3. 증기 평활은 선택 사항입니다. 하면 0.12 mm 텍스처가 연해지므로 엣지에만 국부 적용을 권장합니다.
