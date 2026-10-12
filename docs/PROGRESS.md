# Progress log

Newest entries at the top. Each shot: TODO → SIM → RENDERING → DONE (frames in `renders/<id>/`).
Open questions for the user: `docs/QUESTIONS.md`.

## Shot status
GPU work runs through a **sequential queue**: `bash tools/gpu_queue.sh` (jobs = lines of `cache/gpu_queue.txt`,
finished line numbers in `cache/gpu_queue.done`, log `cache/gpu_queue.log`). Never run >2 Cycles jobs at once
(12 GB VRAM overflows → WDDM paging → everything crawls). Blender renders skip existing frames → safe to restart.
S01 render runs separately: `blender/shot_incense.py -- S01 1 484 100 64`.

| ID | Status | Notes |
|----|--------|-------|
| S01 incense+title | RENDERING | 1..484 needed (edit uses 20 s). VDBs `cache/incense_vdb/` (560, done) |
| S03 equations | DONE (re-render 612 f queued on CPU) | `src/shot_s03_equations.py all` |
| S04 mesh | DONE | `blender/shot_mesh.py` Eevee; quadtree cells `src/mesh_s04.py` |
| S05 cell | DONE (+handles 253-262 queued) | `blender/shot_cell.py` Eevee |
| S06 vortex street | DONE | |
| S07 resolution | DONE | |
| S08 KH clouds | DONE | 336 f |
| S09 models | DONE (CPU) | `src/shot_s09_models.py` → 180 f |
| S10 wing | DONE (178 f) | `blender/shot_wing.py -- S10 1 170 100 48` |
| S11 car | RENDERING (queue line 9) | final sim v4: centre rake 14 lines, nu=1.5e-3, 7-point smoothed particle velocity (removed grid-scale wiggle), GPU 3D blur σ=0.7 | sim `blender/sim_car.py` (fixed diffusion/solid kill); scene `blender/shot_car.py` (DENS default 25) — **check test frame, then queue `-- S11 1 164 100 48`** |
| S12 offshore | DONE (174 f) | look approved; visible helical wake disabled (`WAKE_D=0`, looked unconvincing); fixed ocean placement + nacelle transform_apply bug |
| S13 weather | DONE (174 f) | real GFS winds → `src/shot_s13_wind.py` (done) → `blender/shot_earth.py` Eevee |
| S14 blood | DONE (188 f) | `src/artery.py` (done) → `blender/shot_artery.py` Eevee |
| S15 close | QUEUED (40 samples) | `shot_incense.py -- S15 1 336 100 48` (CFD-twin wipe inside Blender) |
| music | DONE (v1) | `src/music.py` → `audio/score.wav` (161 s). Drone maybe a bit heavy. |
| compose | WORKING | `src/compose.py [--draft] [--still T]`; timeline/captions in `src/timeline.py` (bars @72 BPM) |

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
- 01:30–02:10 wing (red smoke + Krasny roll-up) done; offshore scene + helical wake VDBs; GFS winds + Earth (Eevee);
  carotid artery (Eevee); cell shot; S15 CFD-twin wipe; KH→S09 RANS/LES/DNS; procedural score; compositor with captions.
- GPU overload incident 01:40 (3 Cycles + sim) → introduced the sequential GPU queue.
- NEXT: check car + offshore tests when the queue reaches them, queue their finals; draft cut (`compose.py --draft`);
  final compose when all renders exist; review against storyboard; then report to user.
- 03:00–04:05 car sim iterated 3× (fog → grainy → wiggly → clean); S01/S15 dropped to 40 samples (denoised); final compose appended as last queue job (auto-runs when S01 has 510 frames).
- 02:20 extras: `src/make_srt.py` → output/*.en.srt / *.zh.srt (sidecar subtitles); docs/MAKING_OF.md; tools/check_renders.py (frames needed vs rendered).
