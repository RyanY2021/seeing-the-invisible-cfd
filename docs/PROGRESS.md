# Progress log

# ===== v2 (2026-10-13 →) — see docs/STORYBOARD_v2.md =====
User reviewed v1 and asked for v2 (neon/acrylic/prismatic style, Clawd as guide, Tidepool-based softer score,
more 3D, richer narrative; see CLAUDE.md "v2"). User is asleep — working autonomously; report at the end.

## v2 STATUS (2026-10-13): complete; committed + pushed to `main`, no release yet (user asked for no release)
`output/Seeing_the_Invisible_CFD_v2.mp4` — 4:46, 1920x1080 24 fps H.264 CRF 15 + AAC 48 kHz (-14 LUFS mix), 1.14 GB;
EN/ZH sidecar subtitles `output/Seeing_the_Invisible_CFD_v2.{en,zh}.srt`. Copied to the user's delivery folder.
All 26 shots rendered (7440 frames) and QA'd in the edit; re-renders done for lighting / reflection-artifact fixes
(V05 V06 V10 V12 V19 V25 V26). The video itself is not in git (a future v2.0.0 release would carry it).
Waiting for the user's review.
Re-cut after edits: `cd src && python compose_v2.py` (~20 min; `--still BAR` / `--draft --bars A B` for previews).
Known compromises: Clawd is occasionally occluded by passing cells in V24; V13 counter says 'CELLS · DEMO'
(21 k cells, while the caption says 'millions' in general); the score was checked numerically only, not by ear.

## v2 delivery (user request 2026-10-13)
When the final compose is done, copy `output/Seeing_the_Invisible_CFD_v2.mp4` to the user's OneDrive Attachments
folder (path kept out of the public repo; `tools/finish_v2.sh` takes it from `$V2_DELIVER_DIR`).

## v2 building blocks (done)
- `blender/clawd.py` — Clawd voxel character (18×5 banner sprite, 1:2 pixels) + acting helpers
  (hop/walk/look/blink/surprise/wave/tilt/say) + `export_track()` (screen pos + cues → json for bubbles/SFX).
- `blender/studio.py` — v2 render setup (**scene-linear EXR**, DWAA half), neon tubes (+ backing area lights,
  `neon_switch` flicker-on), lacquer floor, haze, strip softboxes. `blender/props.py` — incense stick + v1 smoke VDB.
- `blender/cellworld.py` — synthwave sky/sun/grid floor, octree cell mesh (`src/octree3d.py` → cache/v2/octree_car.npz),
  edge-lit acrylic cell material.
- `src/grade.py` — EXR → bloom → AgX (punchy) → prism fringe → vignette. `src/paint25d.py` — 2.5D glossy
  acrylic-paint shader for 2D dye fields (banded neon palette, relief normals, soft shadows, strip reflections, thin film).
- `src/score/` — Tidepool engine copied (48 kHz, 120 BPM); `score_v2.py` → `audio/score_v2.wav` (142 bars, −14 LUFS) draft.
- Look-dev stills in `cache/lookdev_v2/` (V01 studio+smoke+Clawd, cell world, car-ad, KH paint).
- Learned: Cycles light linking — receiver collection with **EXCLUDE** entries works (including the volume as the
  only receiver did not). Eevee ≈ 3–4 s/frame for the cell world; Cycles incense shot ≈ 35 s/frame at 64 spp.
- Installed into venv: OpenEXR, soundfile.

## v2 shot status
Two render queues: Cycles `bash tools/gpu_queue_v2.sh` (cache/v2/queue.txt) and Eevee `bash tools/gpu_queue_named.sh e`
(cache/v2/queue_e.txt). Lines are shell commands; finished line numbers in *.done. Renders skip existing frames.
Look-dev stills: `blender/shot_vXX.py -- test <first> <last> [spp]` -> cache/lookdev_v2/VXX_####.exr; `src/grade.py` previews them.

| Shot | Bars | Script | Notes |
|---|---|---|---|
| V01 incense + Clawd climbs tower | 0-6 | blender/shot_v01.py (Cycles) | haze faked in grade (real haze volume was 4x slower) |
| V02 Clawd leaps through smoke | 6-10 | blender/sim_v02.py (src/lbm3d_body.py moving body) -> shot_v02.py (Cycles) | sim done; real swirls behind Clawd |
| V03 neon title sign | 10-14 | shot_v03.py (Cycles) | words flicker on, Clawd turns, waves |
| V04 holographic cards | 14-22 | src/cards_v04.py -> shot_v04.py | potential-flow streamlines with running dashes |
| V05 parcel river + time freeze | 22-26 | shot_v05.py (blender/streaks.py, rules_props.py) | |
| V06 pressure plunger | 26-30 | shot_v06.py | |
| V07 viscosity plates | 30-34 | shot_v07.py | 1D momentum diffusion between plates |
| V08 smoke ring (momentum) | 34-38 | blender/sim_v08_ring.py -> shot_v08.py (Eevee volume) | annulus fill, periodic sides + sponge (all-open bounds blew up) |
| V09 hose (conservation) | 38-42 | shot_v09.py | same droplets/s, double speed after squash |
| V10 equations | 42-48 | src/eq_tex.py -> shot_v10.py | |
| V11 shatter | 48-50 | shot_v11.py | Voronoi shards keep their UV piece of the board |
| V12 into the monitor | 50-54 | shot_v12.py | screen swaps to 'Clawd inside' after the hop |
| V13 octree build + voxel burst | 54-60 | src/octree3d.py -> shot_v13.py | hud.json = cell count |
| V14 one cell + ripple | 60-66 | shot_v14.py | |
| V15 Clawd-obstacle vortex street | 66-74 | src/sim_v15_clawd.py -> src/tex_v15.py -> shot_v15.py | hud.json = time step |
| V16 sim -> NASA clouds | 74-80 | src/shot_v16.py (python 2.5D) | DONE |
| V17 resolution x3 + hot chip | 80-86 | tex_v15.py v17 -> shot_v17.py | |
| V18 KH glossy paint zoom | 86-96 | src/shot_v18.py (python 2.5D) | DONE; 2D pixel Clawd overlay in compose |
| V19 RANS/LES/DNS polaroids | 96-106 | src/tex_v19.py -> shot_v19.py | |
| V20 aircraft (chase cam -> wide) | 106-112 | src/sim_wing.py 336 4.0 wing_tex_v2 -> shot_v20.py (Eevee) | camera cut via timeline marker at frame 97 |
| V21 car-ad wind tunnel | 112-116 | shot_v21.py (Eevee) | light linking keeps the car black |
| V22 offshore synthwave dusk | 116-120 | shot_v22.py (Eevee, from v1 offshore) | |
| V23 neon winds globe | 120-124 | src/shot_s13_wind.py 216 wind_tex_v2 -> shot_v23.py | |
| V24 Clawd surfs a red cell | 124-130 | src/artery.py 312 artery_v2 -> shot_v24.py | |
| V25 CFD-twin scan wipe | 130-136 | shot_v25.py (Cycles) + props.smoke_twin_wipe | wipe in object space (volume Position is object space here) |
| V26 sign off + post-credit peek | 136-142 | shot_v26.py (Cycles) | |
Audio: src/score/score_v2.py -> audio/score_v2.wav; src/sfx_v2.py (cues from clawd_track.json) -> audio/sfx_v2.wav + mix_v2.wav.
Edit: src/timeline_v2.py + src/compose_v2.py (+ textfx_v2.py, grade.py). `python compose_v2.py --draft` previews with placeholders.

Newest entries at the top. Each shot: TODO → SIM → RENDERING → DONE (frames in `renders/<id>/`).
Open questions for the user: `docs/QUESTIONS.md`.

## Shot status
GPU work runs through a **sequential queue**: `bash tools/gpu_queue.sh` (jobs = lines of `cache/gpu_queue.txt`,
finished line numbers in `cache/gpu_queue.done`, log `cache/gpu_queue.log`). Never run >2 Cycles jobs at once
(12 GB VRAM overflows → WDDM paging → everything crawls). Blender renders skip existing frames → safe to restart.

| ID | Status | Notes |
|----|--------|-------|
| S01 incense+title | DONE (512 f) | `blender/shot_incense.py -- S01 1 512 100 40`; VDBs `cache/incense_vdb/` (560) |
| S03 equations | DONE (588 f) | `src/shot_s03_equations.py all` |
| S04 mesh | DONE (340 f) | `blender/shot_mesh.py` Eevee; quadtree cells `src/mesh_s04.py` |
| S05 cell | DONE (262 f) | `blender/shot_cell.py` Eevee |
| S06 vortex street | DONE (432 f) | `src/shot_s06_vortex_street.py` |
| S07 resolution | DONE (240 f) | `src/shot_s07_resolution.py` |
| S08 KH clouds | DONE (336 f) | `src/shot_s08_kh.py` |
| S09 models | DONE (180 f) | `src/shot_s09_models.py` |
| S10 wing | DONE (178 f) | `blender/shot_wing.py -- S10 1 178 100 48` |
| S11 car | DONE (172 f) | sim `blender/sim_car.py` (v4: centre rake, nu=1.5e-3, smoothed particle velocity, GPU blur); scene `blender/shot_car.py` |
| S12 offshore | DONE (174 f) | helical wake disabled (`WAKE_D=0`) |
| S13 weather | DONE (174 f) | real GFS winds → `src/shot_s13_wind.py` → `blender/shot_earth.py` Eevee |
| S14 blood | DONE (188 f) | `src/artery.py` → `blender/shot_artery.py` Eevee |
| S15 close | DONE (336 f) | `shot_incense.py -- S15 1 336 100 40` (CFD-twin wipe inside Blender) |
| music | DONE (v1) | `src/music.py` → `audio/score.wav` (161 s). Not checked by ear. |
| compose | DONE | `src/compose.py` → `output/Seeing_the_Invisible_CFD.mp4` (2:35, 1080p24, CRF 15, AAC 48 kHz). `--draft` / `--still T` for previews. |

`tools/check_renders.py` reports a few clamped tail frames (S03 −4, S08 −9, S15 −1) inside crossfades — invisible, accepted.

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
- 04:58 half-res draft QA (20 sampled times) → two-line title, 48 kHz audio fix.
- 06:40 all renders finished; final compose written. QA of 23 sampled frames: end title crossed the bright plume →
  added dilated dark halo (`shadowed(..., spread=)`) under end title/tagline/credits; re-composed.
- **STATUS: first cut complete** — `output/Seeing_the_Invisible_CFD.mp4`. Waiting for the user's review
  (see `docs/QUESTIONS.md`). Next session: apply review notes; re-run `compose.py` (~11 min) after any change.
- 07:00 user asked to publish on GitHub (public, account RyanY2021). Made a cleaned `main` branch (music stems dropped,
  author email → qirui.you.2021@gmail.com, personal notes redacted); `master` kept locally as the untouched original.
  Added LICENSE (MIT code; CC BY 4.0 media in README), README.md with stills, requirements.txt, BLENDER_EXE env override.
- 07:35 released **v1.0.0** on GitHub (tag `v1.0.0`): `output/Seeing_the_Invisible_CFD_v1.0.0.mp4` (same encode, remuxed with
  version metadata + faststart), EN/ZH .srt, poster. Next version → bump tag (v1.1.0 …) and attach the new mp4 to a new release.
