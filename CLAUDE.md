# CFD Intro — "Seeing the Invisible"

A ~2.5-minute (target 150 s, hard limit ~155 s) cinematic short introducing **Computational Fluid Dynamics**
to a **general audience**. Goal: show the *beauty* of CFD and let viewers grasp the main idea/principle easily.
The user will review the final cut. Ask the user when genuinely unsure (they welcome questions).

**Always read `docs/PROGRESS.md` first** — it is the running log of what is done / in progress / next.
Shot-by-shot plan, timings and caption text live in `docs/STORYBOARD.md`.
Update `docs/PROGRESS.md` after every milestone (a session may be aborted at any time).

## User decisions (fixed — do not re-ask)
- Art style: **realistic / cinematic** (photoreal renders, real-looking smoke & dye), but free to show skill.
- **No voiceover.** On-screen text + music only → captions must carry the explanation: short, elegant, readable.
- Audience: **general public** — intuition first; show Navier–Stokes but explain each term visually; mesh → cells → time-stepping explained simply; one beat on turbulence modelling.
- Applications montage must include **all**: aircraft wing (tip vortices), car in wind tunnel, offshore/ocean structure
  (offshore wind turbine on a monopile), weather (global winds), blood flow (artery).
- Music: **original score composed procedurally in code** (no licensed tracks).
- Everything for this project stays inside `D:\Creative\CFD Intro` (user wants their workspace clean).
  Do not install into the global/base Python; use the project venv.

## Output spec
- 1920×1080, **24 fps**, H.264 (yuv420p, high quality) + AAC stereo 48 kHz → `output/`.
- Frames are rendered per shot into `renders/<shot_id>/####.png` (16-bit PNG where banding matters), then
  `src/compose.py` assembles the edit (crossfades, captions, grade, grain) and pipes to ffmpeg.

## Environment (verified 2026-10-12)
- GPU: RTX 4070 SUPER 12 GB (OptiX OK), Ryzen 7 9700X, 31 GB RAM. ~118 GB free on D:.
- Project Python venv: `.venv\Scripts\python.exe` (Python 3.13) with numpy, scipy, pillow, matplotlib,
  **warp-lang 1.18** (GPU kernels), numba, opencv-python, imageio, imageio-ffmpeg.
- ffmpeg 7.1 (has libx264, libx265, nvenc, loudnorm, afir): `.venv\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe`
  (resolved in code via `imageio_ffmpeg.get_ffmpeg_exe()`; see `src/common.py`).
- Blender **5.2.2 LTS**: `D:\Tools\Blender\blender.exe` — Cycles + OptiX, Mantaflow, bundled `openvdb` python module.
  Run headless: `blender.exe -b --factory-startup --python blender\<script>.py -- <args>`.
- After Effects 2026 exists at `D:\Tools\Adobe\AE` but is **not** used (pipeline is fully code-driven/reproducible).
- Warp kernel cache must point into the project: set `wp.config.kernel_cache_dir = <project>/cache/warp` *before* `wp.init()`
  (done in `src/common.py`). (A stray `C:\Users\Administrator\AppData\Local\NVIDIA\warp` folder was created on day 1 before this was set; harmless, user may delete it.)
- Fonts (Windows): titles `GillSansLightNova.ttf` (tracked caps), captions `GeorgiaPro-Light.ttf` / `GeorgiaPro-LightItalic.ttf`,
  equations via matplotlib mathtext (stix). All in `C:\Windows\Fonts`.
- Shell note: the project path contains a space — always quote it.

## Layout
```
CLAUDE.md            this file (auto-loaded)
docs/STORYBOARD.md   shots, timings, captions, look notes
docs/PROGRESS.md     running log + next steps  ← keep current
src/                 python: solvers (warp), 2D shading, music, compositor
blender/             blender scene/render scripts (+ .blend files saved by them)
cache/               simulation outputs (npy/npz/vdb) — regenerable, git-ignored
renders/<shot>/      rendered frames per shot — git-ignored
audio/               music + sfx stems, final mix
assets/              downloaded third-party assets (with LICENSE notes)
output/              final video(s)
tools/               small probes/utilities
```
Large/regenerable data (`.venv`, `cache`, `renders`, `output`, `audio/*.wav`, `audio/stems/`) is git-ignored; scripts and docs are committed.

## Git / GitHub
- **Public** repo: https://github.com/RyanY2021/seeing-the-invisible-cfd, branch `main` (code MIT, media CC BY 4.0; see README).
  Commit identity comes from the global git config (EdtRhyn <qirui.you.2021@gmail.com>). Pushing uses the stored Git Credential Manager login.
- Local branch `master` = original pre-publication history (contains the music stems and an old email) — **never push it**;
  the user may delete it once they're happy with `main`.
- Public repo → keep personal details about the user out of committed files.
