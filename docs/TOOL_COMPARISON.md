# Single-Image to 3D Face: Practical Tool Comparison (Nov 2026)

Constraints: Ubuntu 22.04, Blender 4.5, **RTX 3050 Laptop GPU with 4 GB VRAM**, no paid APIs and
no large model downloads without approval, and eventual commercial use in the AI 3D Studio.

| Tool | Resemblance | Geometry | Texture | Blender | Local GPU | Commercial license | Verdict |
|---|---|---|---|---|---|---|---|
| **MediaPipe Face Landmarker** (478 3D landmarks) + canonical mesh | Good from the front (the texture is the real photo); medium in profile | Face only, 468 vertices, smooth after subdivision; depth is learned but coarse | Photo projection: exact where visible | Easy (mesh + UVs via `bpy`) | **CPU only, 3.7 MB model** | **Apache-2.0** | **Selected for v0.** It runs today, needs no approval, and the license is clean |
| DECA / EMOCA / SMIRK (FLAME) | Good expression; medium identity | **Full FLAME head** (5k vertices, ears, neck, fixed UVs) | Low-res albedo model; photo projection possible | Good (FLAME add-on / OBJ) | ~2–3 GB, **fits 4 GB** | FLAME + code: **non-commercial**; needs FLAME registration | Best upgrade path for v1 (with your approval) |
| MICA (+ FLAME) | **Best identity shape** among open FLAME regressors | Full FLAME head, neutral | None (pair with DECA/projection) | Good | ~2 GB | Non-commercial (FLAME + InsightFace ArcFace) | Pair with SMIRK in v1 |
| flame-head-tracker / Pixel3DMM (FLAME fitting) | Very good (optimization-based) | Full FLAME head | Photo-projected texture | Good | 4 GB is tight; slow | Non-commercial | v1/v2 refinement |
| 3DDFA_V2 / 3DDFA-V3 (BFM) | Good from the front | Face only (~38k vertices, denser than MediaPipe) | Photo projection | OBJ export | CPU (ONNX) / small GPU | Code MIT, **BFM non-commercial** | Alternative to v0; no full head |
| HRN / Deep3DFaceRecon (BFM) | Good, with detail maps | Face only, plus displacement | Good | OBJ | ~4 GB | BFM non-commercial; manual registration | Detail maps later |
| Hunyuan3D-2 / 2mini (generic image-to-3D) | **Weak**: faces drift and look generic | Full object incl. hair, but messy topology | Texture stage needs 8–16 GB | GLB | Shape ~5–6 GB; 4 GB only with offloading forks | Tencent community license (regional and scale limits) | Hair and accessories later, not the face |
| TRELLIS / TripoSR / SF3D | Weak on identity | Generic meshes | Medium | GLB | 6–16 GB | MIT (TRELLIS, TripoSR); SF3D under Stability community license | Not suitable for 4 GB / identity |
| FaceLift, PanoHead, 3D Gaussian heads | Very good full 360° heads | Gaussians / NeRF, **not clean meshes** | Very good | Poor (needs meshing) | 12–24 GB | Mostly research-only | Not practical here |
| KeenTools FaceBuilder (Blender add-on) | Very good with several photos | Clean head topology | Projected | **Native Blender** | CPU | Paid licence | Commercial benchmark; semi-manual |
| Paid APIs (Hyper3D Rodin, Tripo, Meshy, Avaturn) | Good to very good | Full head + hair | Good | GLB/FBX | Cloud | Paid; check output terms | Needs your approval (cost + photo leaves the machine) |

Sources used for this review include the [FLAME-Universe list](https://github.com/TimoBolkart/FLAME-Universe),
[flame-head-tracker](https://github.com/PeizhiYan/flame-head-tracker),
[3DDFA_V2](https://github.com/cleardusk/3DDFA_V2), [Hunyuan3D-2](https://github.com/Tencent/Hunyuan3D-2),
[MeshLAM (2026)](https://arxiv.org/pdf/2604.22865) and the
[FaceLift paper](https://openaccess.thecvf.com/content/ICCV2025/papers/Lyu_FaceLift_Learning_Generalizable_Single_Image_3D_Face_Reconstruction_from_Synthetic_ICCV_2025_paper.pdf).
VRAM figures are approximate and should be confirmed on the RTX 3050.

## Decision

**v0 (implemented):** MediaPipe dense 3D landmarks → the person's own face surface in a
frontal metric frame → visibility-aware photo texture → back of head, scalp and neck completed
from face proportions → Blender skin shader (subsurface scattering + bump) → `.blend` file.
It runs on CPU in seconds, needs no approval, and is Apache-2.0.

**v1 (needs your approval, ~1 GB of downloads + FLAME registration):** MICA (identity) +
SMIRK (expression/pose) → full FLAME head with ears and real skull shape. Then reuse the v0
texture projection, now in FLAME's UV space. This fits in 4 GB VRAM. It is the largest expected
jump in profile resemblance. The licence is non-commercial, so it suits research; for commercial use, license
FLAME (Meshcapade) or swap the model behind the same interface.

## Honest limits of v0
- Depth (nose projection, face depth) is MediaPipe's learned estimate, so profiles are approximate.
- The back of the head, scalp and neck are **inferred** and colour-filled, not reconstructed. There are
  no ears, eyeballs, hair geometry or teeth yet.
- The facial expression in the photo is kept (no neutralization in v0).
- Lighting from the photo stays baked into the texture.
