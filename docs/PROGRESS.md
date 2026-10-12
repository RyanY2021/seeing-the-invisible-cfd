# Progress log

Newest entries at the top. Each shot: TODO → SIM → RENDERING → DONE (frames in `renders/<id>/`).
Open questions for the user: `docs/QUESTIONS.md`.

## Shot status
| ID | Status | Notes |
|----|--------|-------|
| S01/S02 incense+title | RENDERING | sim: `blender/sim_incense.py` (runs *inside Blender*, writes `cache/incense_vdb/incense_0000..0559.vdb`). Render: `blender/shot_incense.py -- S01 1 552 100 64` → `renders/S01/0001..0552.png` (~20–30 s/frame). Look-dev params baked as defaults (DENS 170, FALL 1.6, LIGHT 1.35). `render_frames` skips existing frames → safe to re-launch to resume. |
| S03 equations | DONE | `src/shot_s03_equations.py bg|render` → `renders/S03/0000..0551.png` (text baked in; 12-frame head handle) |
| S04 mesh | TODO | Blender (Eevee ok); needs SDF car |
| S05 cell | TODO | Blender (Eevee ok) |
| S06 vortex street | DONE | `src/shot_s06_vortex_street.py sim|render` → `renders/S06/0000..0431.png` (432 f). Possible polish: EXPO 0.55→0.45 if too contrasty. Steps per frame in `cache/s06/meta.npz` (for the time-step counter overlay). |
| S07 resolution | DONE | `src/shot_s07_resolution.py` → `renders/S07/0000..0239.png`; labels include real compute times (0.8 s / 2.7 s / 3 min 25 s) |
| S08 Kelvin–Helmholtz | RENDERING | sim done (`cache/s08/c_####.npy`, 3840×2160 f16). Render in 3 CPU procs → `renders/S08/0000..0335.png` |
| S09 models | TODO | derive from S08 dye fields (time-avg = RANS, blur = LES, raw = DNS) |
| S10 wing | RENDERING | `src/sim_wing.py` (vortex-blob roll-up, 3M markers → `cache/wing_tex/####.png`), `src/plane_sdf.py` (aircraft mesh), `blender/shot_wing.py -- S10 1 196 100 64` → `renders/S10/` |
| S11 car | SIM PENDING | car: `src/car_sdf.py mesh` (done), mask `src/sim_car_mask.py` (done). Sim: `blender/sim_car.py -- 200 8000` (inside Blender; writes `cache/car_vdb`). Scene: `blender/shot_car.py` (untested until VDBs exist) |
| S12 offshore | TODO | plan: Blender ocean + monopile turbine (+ fog wakes / tip vortices) |
| S13 weather | TODO | plan: globe + wind streaks (real GFS via NCSS if reachable) |
| S14 blood | TODO | plan: artery bifurcation + RBC instancing via frame handler |
| S15 close | TODO | reuse incense VDBs 300..559 (`shot_incense.py -- S15` / `S15cfd`), wipe in compositor |
| music | TODO | `src/music.py` |
| compose/edit | TODO | `src/compose.py` |

## Key technical notes (learned the hard way)
- **Warp launch order:** last launch dim varies fastest → launch as `(nz, ny, nx)` / `(ny, nx)` with `z, y, x = wp.tid()`. Wrong order was 10× slower.
- `lbm3d.py` sets `max_unroll=64` (19-velocity loops). 3D LBM ≈ 0.64 GLUPS, 2D ≈ 1.3+ GLUPS on the 4070 SUPER.
- Warp + project modules can be imported inside Blender: `sys.path.append(<venv site-packages>)` (Blender's own numpy stays first).
- Blender `openvdb`: `FloatGrid.copyFromArray(arr[x,y,z], tolerance=…)`, `grid.saveFloatAsHalf=True`; mask sparse fields or files balloon.
- Incense VDB: 1 fine voxel = 0.5 mm in scene (object scale 0.0005), VDB index (x, depth, up).
- Blender volume sequence: `frame_offset=-1` maps scene frame 1 → file 0000; `frame_duration` must cover the range.

## Log
### 2026-10-12 — session 1 (user asleep from ~00:40; working autonomously)
- 00:10 requirements + environment survey; project + venv + docs + git.
- 00:30 2D LBM (Warp) validated: clean von Kármán street. S06 simulated & rendered (smoke-wire look).
- 00:45 3D LBM + MacCormack smoke (2× grid) validated on plume tests; perf fix (launch order).
- 00:52 incense sim started inside Blender (192×384×192 LBM, 384×768×384 smoke) → VDB.
- 01:00 S07 sims + render; incense look-dev (scale 0.5 mm/voxel, height-dilution of density, bokeh background).
- 01:08 S01 final render started.
- 01:10–01:27 S03 rendered; SDF car built (glass via vertex colours, alloy rims); wing shot: red smoke curtain + Krasny roll-up looks great; KH cloud shading fixed.
- NEXT: run car sim once incense sim finishes; S12 offshore, S13 earth, S14 artery, S04 mesh, S05 cell, S09, music, compose.
