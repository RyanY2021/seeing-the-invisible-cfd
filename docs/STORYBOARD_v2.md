# Storyboard v2 — "Seeing the Invisible" (with Clawd)

1920×1080 · 24 fps · score at **120 BPM → 1 bar = 2 s = 48 frames, 1 beat = 12 frames, 1/16 = 3 frames**
(everything is cut on the music grid). Target ≈ **4:45** (142 bars).

## What changed from v1 (user review, 2026-10-13)
| v1 problem | v2 answer |
|---|---|
| Story too compressed; few logical steps | A **question → answer spine** (Clawd asks, captions answer); rules taught by *intuition first, equation last*; a "can we trust it?" beat (simulation vs a real satellite photo). |
| Music lacked transients | Tidepool-based score: droplet plinks, kalimba, soft kick/snap, ticks — rhythmic but **no heavy drops**, slower (150 → 120 BPM). |
| Coarse Blender models | **Low-key "car-ad" lighting**: black glossy objects drawn only by strip-light highlights, neon rims, haze. Detail is implied, never inspected. |
| Too serious for outsiders | **Clawd** (the orange pixel critter of Claude Code) as a curious guide; neon / acrylic / prismatic look; bouncy beat-synced motion and type. |

## Logic spine (the "mind guidance")
1. *Air is invisible — what is it doing?* → smoke reveals it.
2. *Why should I care?* → everything that moves through air/water is shaped by it; we want to see it **before building**.
3. *Does air follow rules?* → follow one parcel: pressure, viscosity, momentum, conservation → **Navier–Stokes** as the summary.
4. *Then why not just solve them?* → nonlinear, coupled; unsolved by hand.
5. *How does a computer do it?* → cells → balance in each cell → tiny time steps.
6. *Can we trust it?* → swirls **emerge** on their own — and the same pattern appears in real clouds behind an island.
7. *What's the catch?* → resolution costs; turbulence has too many swirls → model the small ones.
8. *So where is it used?* → wing, car, offshore wind, weather, blood.
9. *Back to the start* → now we can see the invisible.

## Two worlds
- **Studio (the real world):** black glossy floor, neon tubes (magenta / cyan / violet), volumetric haze, rim light.
  Real-looking smoke & water lit like a concert. Product-shot lighting hides coarse geometry.
- **Cell world (inside the computer):** vaporwave grid floor, sunset-gradient sky, edge-lit **acrylic voxel cells**,
  prismatic highlights. Clawd is a native here — it's made of cells too.

## Clawd
- Shape from the Claude Code welcome banner (block characters ` ▐▛███▜▌ / ▝▜█████▛▘ /   ▘▘ ▝▝ `):
  an 18×5 sprite of 1:2 pixels → built as **glossy orange voxels** (#D97757 family), black eye gaps, 2 arms, 4 legs.
- Acting is pure pixel-art: hops with squash/stretch on the beat, eyes slide one pixel to look, blink (eye gaps fill),
  arm waves, legs patter. Speaks only in short **pixel speech bubbles** + soft 8-bit chirps (questions, "!", "?").
- Captions (the narrator) answer; Clawd asks and reacts. Clawd never blocks the science.
- Fan use of Anthropic's mascot: README will note the character is Anthropic's and outside the CC BY licence.

## Shot list
Bars are edit positions (0-based). Captions in quotes; **[bubble]** = Clawd's speech bubble.

| Shot | Bars | Time | Picture | Text | Production |
|---|---|---|---|---|---|
| **PROLOGUE — the invisible** ||||||
| V01 | 0–6 | 0:00 | Black. A magenta neon tube flickers on → black glossy table, incense stick, smoke rising smooth then curling. Clawd hops in from the left, lands (squash), looks up at the smoke. | "Air is invisible…" · "…but it is never still." | incense VDB (v1 sim) + Cycles volume, neon rig; Clawd |
| V02 | 6–10 | 0:12 | Close: Clawd swipes an arm through the plume; smoke curls around the arm and spins off an eddy. | **[!?]** · "Smoke lets us see it — for a moment." | new 3D smoke sim with moving obstacle (Warp) |
| V03 | 10–14 | 0:20 | Neon sign **SEEING THE INVISIBLE** buzzes on letter by letter through the drifting smoke; Clawd sits on the sign. | *an introduction to Computational Fluid Dynamics* | Blender neon-tube text + smoke |
| **I — why see it?** ||||||
| V04 | 14–22 | 0:28 | Clawd **[why care?]** — five holographic acrylic cards pop out around it on the beat: wing, car, turbine, globe, heart, each with animated flow lines. | "Wings, cars, turbines, storms, our own blood —" · "all shaped by flows we cannot see." · "To design them, we must see the flow before it is built." | Eevee; line-art textures drawn in Python |
| **II — the rules** ||||||
| V05 | 22–26 | 0:44 | **[does air follow rules?]** A glowing cyan acrylic cube — a fluid parcel — drifts in a stream of neon streaks; camera follows. | "It does. Follow one tiny parcel of fluid —" · "and ask what pushes it." | Eevee; analytic flow |
| V06 | 26–30 | 0:52 | Pressure: magenta HIGH haze behind, blue LOW ahead; Clawd shoves a plunger, the parcel squeezes and shoots toward low. | "① Pressure — pushed from high to low." | Eevee |
| V07 | 30–34 | 1:00 | Viscosity: a stack of acrylic plates; Clawd drags the top one, the layers below follow less and less (shear). Honey vs water side by side. | "② Viscosity — neighbours drag each other along." · *honey: a lot · air: very little* | Eevee |
| V08 | 34–38 | 1:08 | Momentum: Clawd surfs the parcel round a bend; it overshoots, the flow bends itself. | "③ Momentum — once moving, it keeps going," · "carried by the flow itself." | Eevee + streamlines |
| V09 | 38–42 | 1:16 | Conservation: neon hose; Clawd covers the nozzle with its arm → the jet speeds up and flies further. | "④ Nothing appears or disappears:" · "narrow the path, and it speeds up." | particle jet (analytic) |
| V10 | 42–48 | 1:24 | The four ideas fly together into glowing glass equations (momentum + continuity); each term lights in its vignette colour. | "Together: the Navier–Stokes equations (1822–1845)." · "Newton's force = mass × acceleration — for every drop of fluid." | mathtext → extruded acrylic, Eevee |
| V11 | 48–50 | 1:36 | Equations shatter into prismatic shards. | "Easy to write. Almost impossible to solve." · *(proving they always behave is a $1M open problem)* | Eevee/Cycles shards |
| **III — the computer's trick** ||||||
| V12 | 50–54 | 1:40 | **[can a computer?]** Clawd hops through a glowing screen into the cell world (grid floor, sunset sky). | "A computer can't solve it everywhere at once —" · "so it works piece by piece." | Eevee cell world |
| V13 | 54–60 | 1:48 | Around an obstacle, space dices itself into edge-lit acrylic cells, finer near the surface; a cell counter climbs. Clawd looks at its own pixels. | "Step 1 — chop space into millions of tiny cells." · **[I'm made of cells too!]** | octree (v1 `mesh_s04.py`) in new look |
| V14 | 60–66 | 2:00 | Into one cell: particles stream in and out through its faces; in/out tallies; a light ripple shows each cell talks only to its neighbours. Clawd sits on top keeping score. | "Step 2 — in every cell, balance the books:" · "in − out = change." · "Each cell only talks to its neighbours." | Eevee |
| V15 | 66–74 | 2:12 | Glass tank in the cell world: flow past a **Clawd-shaped obstacle** starts from rest; the wake grows and starts shedding swirls. Step counter races. | "Step 3 — take a tiny step forward in time." · "Then another. Millions of them." | new 2D LBM (Clawd obstacle) → glossy dye shader on a 3D slab |
| V16 | 74–80 | 2:28 | "Nobody told the computer to make swirls." Match-cut to a real satellite photo: von Kármán vortices in clouds behind an island. | "Nobody told it to make these swirls — they emerge from the rules." · "Nature agrees: clouds behind an island, ~100 km long." | NASA image (public domain) 2.5D push-in |
| V17 | 80–86 | 2:40 | The same flow at three resolutions — chunky 8-bit pixels (Clawd-sized) → fine. A cost meter climbs; Clawd fans a glowing hot chip. | "More cells, sharper flow —" · "halve the cell size in 3D: 16× the work." | 2D LBM ×3 (reuse v1 S07 idea) |
| **IV — turbulence** ||||||
| V18 | 86–96 | 2:52 | **[why is it hard?]** Two layers slide past each other and roll into billows — glossy neon acrylic-pour paint with real light & shadow; slow zoom into eddies within eddies. | "The real challenge: turbulence." · "Big swirls feed smaller swirls — down to fractions of a millimetre." · "Far too many to compute them all." | v1 KH data → new 2.5D paint shader |
| V19 | 96–106 | 3:12 | Clawd with a pixel camera snaps three acrylic polaroids of one flow: long exposure / soft focus / every detail. | "So we model the smallest swirls instead:" · RANS *the average* · LES *big swirls sharp, small ones estimated* · DNS *every swirl — tiny problems only* | v1 S09 filters → polaroid slabs |
| **V — everywhere** ||||||
| V20 | 106–112 | 3:32 | Black glossy wing drawn by strip-light highlights; a magenta smoke curtain rolls into the tip vortex; Clawd clings to the wingtip. | AIRCRAFT · "the swirl behind every wingtip" | v1 roll-up sim, new lighting |
| V21 | 112–116 | 3:44 | Car-ad look: a black car revealed only by sliding highlights; neon smoke streaks flow over it; Clawd holds the smoke wand. | CARS · "less drag, less fuel" | v1 car sim, new lighting |
| V22 | 116–120 | 3:52 | Synthwave dusk sea; offshore turbine on a monopile, rim-lit; waves and wake around the pile; Clawd waves from the platform. | OFFSHORE WIND · "turbines standing in the waves" | v1 scene, new sky/light |
| V23 | 120–124 | 4:00 | Night globe with neon wind streaks (real GFS winds); Clawd drifts past like a satellite. | WEATHER · "tomorrow's winds, today" | v1 wind textures, new shading |
| V24 | 124–130 | 4:08 | Acrylic-glass artery; glowing streamlines pulse; Clawd surfs a red blood cell. | MEDICINE · "blood through an artery" | v1 artery, new look |
| **VI — close** ||||||
| V25 | 130–136 | 4:20 | Back in the studio: Clawd looks at the smoke; a lens wipes across revealing its simulated twin in neon colours. | "Computational Fluid Dynamics:" · "seeing the invisible — before it is built." | incense VDB + false-colour pass |
| V26 | 136–142 | 4:32 | The neon sign flickers; Clawd waves and hops off; sign switches off; credits. Post-credit: Clawd peeks back, *blip*. | credits | Blender |

## Look & feel
- **Palette:** ink-violet night (#0B0820) · neon magenta (#FF4FD8) · cyan (#3BE8FF) · electric violet (#8A5CFF) ·
  sunset peach/orange (Clawd #D97757, #FF9E6B) · a little acid lime (#C6FF4F) for highlights. Smoke and dye are
  lit, not painted: colour comes from the lights.
- **Materials:** glossy black lacquer; clear/frosted **acrylic** with glowing edges; **thin-film iridescence** and
  prismatic (RGB-split) glints; neon glass tubes; Clawd = glossy orange plastic voxels.
- **Light & shadow:** every shot has a key strip light + coloured rims + haze; 2D flows are shaded as glossy
  relief (height → normals → specular from neon strips, soft shadows), not flat colour maps.
- **Motion:** "jumping" — elements pop in on beats with spring overshoot; camera drifts and orbits (more 3D).
- **Type:** rounded sans captions with soft neon glow on a frosted-acrylic pill, words popping in on the beat;
  pixel font for Clawd's bubbles; neon-tube lettering for titles.

## Music (`src/score/`, from the Tidepool engine in `D:\Creative\Colorbass Test`)
120 BPM, E major, liquid colorbass softened: no impacts / heavy drops, gentler drive, filtered stabs;
keeps droplet plinks, kalimba, bubbling brook, gliding chords, droplet hi-hats, soft kick & snap.
| Bars | Section | Music |
|---|---|---|
| 0–14 | Prologue | underwater: muffled pad, brook, distant "oo" voice; filter opens slightly for the title |
| 14–22 | I | surfacing: kalimba arps, droplet ticks, soft kick |
| 22–50 | II | groove 1: droplet hook, soft liquid chords; a gentle accent per rule; gliss for the equations |
| 50–86 | III | ticking 16th droplet arp = time steps; builds into a legato "flow" when the swirls emerge |
| 86–106 | IV | "The Deep": C#m9–Amaj9–E/G#–B–Cmaj9, kalimba, siren voices, heartbeat |
| 106–130 | V | riser into the fullest section: hook + vocal chops + flow + waterfall cascades — a soft splash on every shot change (108/112/116/120/124), still no heavy drop |
| 130–142 | VI | sinking back, resolve to E, long tail; Clawd's 8-bit goodbye blip |
SFX: Clawd chirps (8-bit), neon buzz, soft whooshes on transitions.
