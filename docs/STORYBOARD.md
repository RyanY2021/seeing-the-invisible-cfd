# Storyboard v1 — "Seeing the Invisible"

24 fps · 1920×1080 · target ≈ 150 s. Times are edit positions (approximate; tune in `src/compose.py`).
Each shot is rendered with ~1 s extra handles for crossfades.
No voice: captions carry the story. Caption style: Georgia Pro Light, sentence case, soft fade + slight blur-in,
lower third or centred. Titles: Gill Sans Nova Light, uppercase, wide tracking.

| ID | Edit time | Dur | Picture | Captions (on screen) | Production |
|----|-----------|-----|---------|----------------------|------------|
| **ACT I — WONDER** |||||
| S01 incense | 0:00–0:14 | 14 s | Black → glowing ember of an incense stick; a thin smoke ribbon rises laminar, wavers, breaks into turbulent curls. Dark room, cool rim light from side, warm ember. Slow push-in. | 0:02 "A ribbon of smoke." · 0:06 "Smooth at first…" · 0:10 "…then, suddenly, chaos." | 3D GPU smoke solver (`src/sim3d_smoke.py`, Warp) → VDB → Cycles volume (`blender/shot_incense.py`) |
| S02 title | 0:14–0:22 | 8 s | Smoke keeps drifting, darker; title resolves out of the smoke. | **SEEING THE INVISIBLE** / *an introduction to Computational Fluid Dynamics* | Same render (continuation) + compositor title |
| **ACT II — THE RULES** |||||
| S03 equations | 0:22–0:44 | 22 s | Dark, faint drifting flow behind. Navier–Stokes momentum + continuity appear. Each term highlights in turn with a one-line meaning. | "Air, water, blood — every fluid obeys the same rules." → equations, label "Navier–Stokes equations · 1822–1845" → term labels: *how the flow changes* · *the flow carries itself* · *pressure pushes* · *viscosity smooths* · *outside forces* · *mass is never lost* → "Beautiful — but almost impossible to solve by hand." small: "Even proving they always have a smooth solution is an open $1,000,000 Millennium Prize problem." | matplotlib mathtext → compositor (`src/shot_equations.py`) |
| **ACT III — THE IDEA** |||||
| S04 mesh | 0:44–0:58 | 14 s | Clay car model in a dark studio. A computational mesh grows around it: octree cells, finer near the body, slice plane glowing. Cell counter climbs. | "So we let a computer do it — piece by piece." · "① Divide space into millions of tiny cells." | Blender (`blender/shot_mesh.py`) |
| S05 cell | 0:58–1:08 | 10 s | Push into one cell: glassy cube, flow arrows on faces, particles passing through. | "② In every cell, keep the balance:" · "what flows in − what flows out = what changes" | Blender (`blender/shot_cell.py`) |
| S06 vortex street | 1:08–1:24 | 16 s | Wind-tunnel smoke-wire look: flow past a cylinder starts from rest, wake grows, then the von Kármán vortex street sheds. Time-step counter. | "③ Step forward in time — thousands of times." · "From simple local rules, the whole flow emerges." | 2D GPU lattice-Boltzmann (`src/sim2d_lbm.py`) → realistic smoke shading (`src/render2d.py`) |
| S07 resolution | 1:24–1:32 | 8 s | Same flow at 3 mesh resolutions side by side (grid lines visible on coarse). | "Finer cells reveal more — at a higher cost." labels: 40 × 20 · 160 × 80 · 1280 × 640 | 2D LBM ×3 |
| **ACT IV — TURBULENCE** |||||
| S08 Kelvin–Helmholtz | 1:32–1:44 | 12 s | Two layers sliding past each other roll up into billows — rendered like sunset-lit KH clouds / dye; slow zoom into eddies within eddies. | "The hardest part: turbulence." · "Swirls within swirls — from kilometres down to millimetres." | 2D LBM high-res + shading |
| S09 models | 1:44–1:52 | 8 s | Triptych of one turbulent flow: averaged / large eddies / every eddy. | "Too many to compute them all — so the smallest are modelled." labels: RANS · *the average* / LES · *the big eddies* / DNS · *every eddy* | Filters of S08 data |
| **ACT V — EVERYWHERE** |||||
| S10 wing | 1:52–1:58 | 6–7 s | Wing in a smoke layer; wing-tip vortex rolls the smoke into a spiral. | "Wings that lift us" | Vortex-sheet roll-up (Krasny) → smoke → Blender |
| S11 car | 1:58–2:04 | 6–7 s | Clay car in wind tunnel; smoke streaklines over body, separation & wake. | "Cars that slip through the air" | 3D LBM (`src/sim3d_lbm.py`) + streaklines → Blender curves |
| S12 offshore | 2:04–2:10 | 6–7 s | Offshore wind turbine on a monopile, ocean waves, wake/foam around the pile, helical tip vortices. | "Turbines standing in the sea" | Blender ocean + 2D LBM foam wake |
| S13 weather | 2:10–2:16 | 6–7 s | Night/day Earth with animated wind streaks (real GFS winds if obtainable, else simulated). | "Tomorrow's weather" | Globe render + particle advection |
| S14 blood | 2:16–2:22 | 6–7 s | Translucent artery (bifurcation/aneurysm), red cells & speed-coloured streamlines, pulsatile. | "The blood in our veins" | Blender |
| **ACT VI — CLOSE** |||||
| S15 close | 2:22–2:32 | 10 s | Smoke again; a wipe reveals its CFD twin (vorticity colour) and back; fade to title. | "Computational Fluid Dynamics" · "Seeing the invisible — before it is built." | Reuse S01 sim + false-colour render |

## Look & feel
- Realism: physically based renders (Cycles), real-looking smoke/dye, filmic tone mapping, subtle film grain,
  vignette, gentle bloom on bright smoke, slow camera moves. Dark, elegant backgrounds; restrained colour
  (warm ember / cool rim, sunset gold for KH, ocean blues), CFD false-colour only where "the simulation view" is meant.
- Text: little and large; never more than ~8 words on screen at once (except the Millennium note).

## Music (procedural, `src/music.py`)
Act I: low drone + airy pad, sparse bell-piano notes (wonder). Act II: pad opens, gentle pulse.
Act III: arpeggio motif builds with time-stepping. Act IV: tension (minor, filtered noise swells).
Act V: full warm chord progression, soft low percussion, rising. Act VI: resolve to tonic, long reverb tail.
Sound design: soft air whoosh on transitions, faint ember crackle in S01.
