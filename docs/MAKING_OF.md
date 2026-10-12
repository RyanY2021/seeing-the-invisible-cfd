# Making of "Seeing the Invisible" — what is simulated, what is modelled

Everything was produced by code in this folder (Python + NVIDIA Warp on the RTX 4070 SUPER, Blender 5.2 Cycles/Eevee,
ffmpeg). No stock footage. Third-party inputs: Poly Haven CC0 HDRIs, NASA Earth imagery, NOAA GFS wind data.

| Shot | What you see | How it was made | "Real CFD"? |
|------|--------------|-----------------|-------------|
| S01/S02 incense | Smoke ribbon → turbulent curls, title | 3D lattice-Boltzmann (D3Q19, regularised BGK + Smagorinsky, Guo buoyancy) 192×384×192 cells; smoke on a 2× refined grid (384×768×384) with MacCormack advection; 560 OpenVDB frames → Cycles volume render (85 mm, f/2.8 look) | **Yes** — own GPU solver |
| S03 equations | Navier–Stokes term by term | matplotlib mathtext; background = small 2D LBM decaying-turbulence dye field | background yes |
| S04 mesh | Octree mesh growing around a clay car | Quadtree refinement driven by the car's signed-distance field (cells refine where |sdf| < 1.6 h) on two slice planes; Eevee | real meshing algorithm |
| S05 cell | One finite-volume cell, fluxes in/out | Illustrative animation (Eevee) | illustration |
| S06 vortex street | Wind-tunnel smoke-wire photo look, flow starts from rest | 2D LBM (D2Q9) 2800×1200, Re = 150, 74 k time steps; 20 M smoke particles advected as streaklines; photographic shading | **Yes** |
| S07 resolution | Same flow on 9 k / 92 k / 1.5 M cells | Three separate 2D LBM runs; labels show measured compute times | **Yes** |
| S08 Kelvin–Helmholtz | Sunset wave clouds rolling up | 2D LBM 3840×2160 shear layer (Smagorinsky LES) + MacCormack dye; 2D light-marching cloud shading | **Yes** |
| S09 RANS/LES/DNS | One cloud layer, three model levels | Same S08 fields: time/x-average (RANS-like), Gaussian filter (LES-like), raw (DNS) | derived from real sim |
| S10 wing | Plane punches through red smoke; tip vortices spiral | Krasny vortex-blob method (600 blobs, elliptic loading) carrying 3 M smoke markers in the Trefftz plane → texture sequence → Cycles volume slab; procedural aircraft (SDF) | **Yes** (vortex method) |
| S11 car | Smoke streaklines over a clay car in a wind tunnel | 3D LBM 460×128×192 around the voxelised SDF car (Smagorinsky LES), 3 M smoke particles from a nozzle rake → VDB → Cycles | **Yes** |
| S12 offshore | Wind farm on monopiles at sunset | Blender ocean (FFT spectrum) + procedural turbines; a helical tip-vortex wake was modelled but left out (looked unconvincing) | ocean spectrum only |
| S13 weather | Real surface winds over the North Atlantic | NOAA GFS 10 m winds, 12–13 Oct 2026 (itself a CFD weather model), 260 k particles on the GPU; NASA Blue/Black Marble | real CFD *data* |
| S14 blood | Carotid bifurcation, streamlines + red cells, 72 bpm pulse | Geometry from SDF tubes; pulsatile Poiseuille-like kinematic model (not a solved flow) | illustration |
| S15 close | Incense smoke wiped into its "simulation view" | Same S01 sim (later frames); vorticity grid exported from the solver colours the CFD view | **Yes** |

Music: additive/FM synthesis + convolution reverb in numpy (`src/music.py`), 72 BPM; edit is bar-aligned (`src/timeline.py`).
