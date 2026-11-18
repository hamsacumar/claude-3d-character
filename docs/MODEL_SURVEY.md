# Candidate Models

Each entry is something to evaluate in a phase-1 spike, not a final decision. **Licenses
matter for the AI 3D Studio product**: several key academic assets are
non-commercial. Check every license before shipping.

## Head representation
| Model | Notes | License |
|---|---|---|
| **FLAME 2020/2023** (selected) | 5k vertices, UV layout, expression blendshapes, part of SMPL-X | Non-commercial research; a commercial license is available from MPI/Meshcapade |
| Basel Face Model (BFM) | Used by Deep3DFaceRecon and HRN; face only, no full head | Non-commercial |
| Own topology + PCA | Fallback if licensing blocks FLAME | Ours |

## Identity and shape regressors
| Model | Strength | GPU | Notes |
|---|---|---|---|
| **MICA** | Best-known identity-accurate FLAME shape from one image | ~2 GB | Uses ArcFace (InsightFace weights: non-commercial) |
| **SMIRK** | Strong expression and pose with FLAME | ~2 GB | Pairs with MICA's shape |
| EMOCA / DECA | Shape, expression and detail displacement; mature | ~2–3 GB | Shape identity weaker than MICA |
| Deep3DFaceRecon / HRN | BFM; HRN adds good detail maps | ~3–4 GB | Different topology; would need conversion |
| Pixel3DMM, TEASER and newer FLAME trackers | Recent; check for a precision gain | varies | Evaluate in the spike |

## Landmarks, parsing and identity metric
- **MediaPipe Face Landmarker**: 478 points, Apache-2.0, runs on CPU. Primary landmark source.
- **face-alignment (FAN)**: 68 points, fallback.
- **BiSeNet face parsing**: skin, hair and glasses masks.
- **ArcFace / AdaFace**: identity loss and metric. Commercial use needs a cleared model.

## Rendering and optimization
- **nvdiffrast** (fast, CUDA) or **PyTorch3D** (portable). Hidden behind a `Renderer` interface.

## Texture
- Photo projection + SH de-lighting (our own code).
- **FFHQ-UV**: a dataset and model for complete facial UV albedo; a candidate prior for filling unseen areas.
- **Diffusion inpainting** (SDXL or Flux-class inpaint, run in UV space): ~8–12 GB VRAM, optional stage.
- Later: learned de-lighting and albedo, and a super-resolution step (Real-ESRGAN/GFPGAN-type, with licenses checked).

## Later phases (full character)
- **SMPL-X**: body with the same FLAME head, so the head attaches cleanly.
- Hair: strand or card generation, or generic image-to-3D (TRELLIS / Hunyuan3D 2.x) for hair and accessories only.
- Full-head generative models (PanoHead, FaceLift-type Gaussian heads): a reference for completing the back of the head.

## GPU budget (target)
| Tier | VRAM | Pipeline |
|---|---|---|
| Minimum | 6–8 GB | Regressors + refinement + projection texture (no diffusion) |
| Recommended | 12–16 GB | + diffusion UV inpainting, high-res bake |
| CPU-only | — | Preprocess + regressors at low speed; refinement capped at a few iterations |

Target latency on a 12 GB GPU: under 60 s per head without diffusion and under 2 min with it.
