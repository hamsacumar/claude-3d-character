# Implementation Plan v1: Photo → FLAME 2023 Open head → Blender → 4K texture

Status: **waiting for approval**. Nothing has been installed or downloaded.

## Scope of v1
One photo → fitted **FLAME 2023 Open** head (skull, ears, eyeballs, neck) → Blender 4.5 project →
improved 4096² colour texture → **separate** `.blend` + PNG. Body and teeth are out of scope.
Hair is a simple first version only.

## 1. Pipeline and who implements each part

| Step | What | Implementation | Runs on |
|---|---|---|---|
| 1 Analyze | 478 face landmarks, head pose, hair/face-skin/body/clothes segmentation | MediaPipe Face Landmarker + Multiclass Selfie Segmenter (existing libraries) | CPU |
| 2 FLAME layer | Shape/expression blendshapes, pose correctives, linear blend skinning (5 joints) | **We write this ourselves** (~200 lines of PyTorch), plus a loader that reads the FLAME `.pkl` **without `chumpy`**, an unmaintained library that breaks on NumPy ≥1.24 | CPU/GPU |
| 3 Landmark correspondence | MediaPipe 468 points → points on the FLAME surface | **We build this ourselves**: a one-time registration of the MediaPipe canonical mesh to the FLAME template (anchor pairs + non-rigid ICP), stored as an asset. We don't use MICA's MediaPipe embedding, which is non-commercial | CPU, once |
| 4 Fitting | Optimize shape β, expression ψ, jaw/neck/eye pose, camera, SH lighting | **We build this ourselves** in plain PyTorch. Losses: landmarks (inner face points), silhouette (distance transform of the face+hair mask sampled at the projected contour), photometric (photo sampled at visible projected vertices vs albedo × SH shading), plus regularizers (β/ψ priors, Laplacian smoothness). **No PyTorch3D or nvdiffrast needed** | CPU (~1–3 min) or GPU (<1 GB) |
| 5 Neutralize | Set ψ = 0 and jaw closed → neutral, rig-ready head | Our code | CPU |
| 6 Blender build | Import mesh + UVs, subdivision, skin/eye materials, camera matched to the photo, lights, four-view cameras | `bpy` script, Blender 4.5.14 headless | CPU/GPU |
| 7 Hair v1 | Hair cap texture + Geometry-Nodes hair curves on the scalp. Length, volume and colour come from the photo's hair mask | `bpy` + our code | CPU |
| 8 Texture: registered projection | For each texel of the 4096² UV atlas: 3D point → project into the photo → depth test (our numpy/PyTorch z-buffer) → weight by visibility and viewing angle | Our code | CPU/GPU |
| 9 Texture: de-light + fill | Divide by the fitted SH shading; mirror fill via FLAME's left/right vertex symmetry; skin-tone fill for areas never seen | Our code | CPU |
| 10 Texture: AI enhancement | (a) Real-ESRGAN ×4 upscale of the face crop. (b) SDXL inpainting at **low strength** on the registered face for skin detail. (c) Render side/back/top views in Blender, inpaint only the unseen masked regions, project back from the known cameras | diffusers + SDXL-inpainting-0.1 + fp16-fix VAE; spandrel to load Real-ESRGAN | GPU (offload) |
| 11 Bake + package | Merge into a 4096² colour atlas (+ roughness), save PNG, copy the project to `*_print_texture.blend`, pack the image. **The original `.blend` and PNG are never written** | `bpy` (Cycles bake / image save) | GPU/CPU |
| 12 Verify | Front, 3/4, side and back renders + a contact sheet with the photo; landmark reprojection error | `bpy` + our code | GPU/CPU |

The texture stage (steps 8–11) is where `blender-print-texture` applies. Its **original
instructions are still needed** (see `.claude/skills/blender-print-texture/SKILL.md`). Steps 8–11
will be adjusted to follow them exactly once they are pasted in.

## 2. Expected output quality (realistic)
- **Front view:** strong likeness. The visible face texture is the person's own photo, on a fitted head.
- **Three-quarter view:** good. **Profile:** plausible, but nose projection, chin depth and skull length come from
  landmarks + the FLAME prior. Expect noticeable differences from the real profile.
- **Back view:** a coherent generic skull with hair-coloured scalp/curves; not the person's real back of head.
- **Geometry:** FLAME resolution (5,023 vertices, ~80k after subdivision). Clean, symmetric topology with ears and
  eyeballs; no wrinkles or pores in the geometry (detail comes from the texture/bump only).
- **Hair:** v1 hair is a simple stand-in (scalp texture + curves). Short or simple hairstyles look acceptable;
  long, curly or styled hair will not match. Beards are texture only.
- **Texture:** 4096² atlas. True detail is limited by the photo: a 600-px-tall face supplies ~600 px of
  real information, and the rest is upscaling or AI detail. The AI steps add plausible skin texture but
  **can drift identity**, so they run at low strength and only fill masked, unseen areas on the sides and back.
- **Not included in v1:** teeth/mouth interior, eyelashes as geometry, body, clothing, re-lighting
  quality comparable to a scan.

## 3. Estimated downloads (all need your approval; sizes approximate)

| Item | Size | Needed for |
|---|---|---|
| FLAME 2023 Open (you register and download it yourself) | ~50–150 MB (check on the download page) | Geometry |
| `uv` + Python 3.11 venv (Ubuntu 22.04's Python 3.10 reached end of life in Oct 2026; recent PyTorch may not ship wheels for it) | ~40 MB | Everything |
| PyTorch (CUDA wheel incl. NVIDIA libraries) | ~2.5–3.5 GB (CPU-only build: ~200 MB, enough for the fitting alone) | Fitting, SDXL, ESRGAN |
| diffusers, transformers, accelerate, safetensors, opencv, scipy, mediapipe | ~0.3 GB | — |
| SDXL inpainting 0.1 (fp16 weights only) | ~6.9 GB | AI texture |
| sdxl-vae-fp16-fix | ~0.3 GB | AI texture (prevents fp16 NaNs) |
| Real-ESRGAN x4plus weights | 64 MB | Upscale |
| MediaPipe Multiclass Selfie Segmenter | ~16 MB | Hair/skin masks |
| **Total** | **~10–11 GB disk** | |

Option to stage approvals: **v1a** = steps 1–9 + 11–12 (no SDXL: ~3.5 GB, or ~0.6 GB with CPU-only torch),
then **v1b** adds SDXL.

## 4. GPU memory (RTX 3050 Laptop, 4 GB)

| Step | VRAM | Time (estimate) |
|---|---|---|
| Fitting | <1 GB (or CPU) | 1–3 min |
| Real-ESRGAN, tiled | <1 GB | <1 min |
| SDXL inpainting fp16, **sequential CPU offload**, 1024² | ~2–3 GB peak | **~2–6 min per image**; ~6–8 images per character → **~20–45 min** |
| Blender Cycles 4096² bake / renders | ~1–2 GB | a few minutes |

SDXL with offload also needs **≥16 GB system RAM**. This is still to be confirmed with `scripts/check_env.sh`.

## 5. PyTorch3D compatibility (item 4)
**v1 does not use PyTorch3D.** The fitter only needs to project vertices and sample images, which plain
PyTorch can do. That avoids building PyTorch3D from source against a matching CUDA toolkit and compiler.
PyTorch3D's latest builds (0.7.9) are published on conda-forge, not as pip wheels for current PyTorch. If
a later version needs a full differentiable rasterizer, compatibility will be checked against the exact
output of `scripts/check_env.sh` (driver, CUDA, gcc, Python) before anything is installed.

PyTorch itself: the RTX 3050 (Ampere, compute capability 8.6) is supported by all current CUDA 12.x/13.x
wheels. The wheel's CUDA version must be ≤ the version your **driver** supports (`nvidia-smi` shows it).
CUDA 13 wheels need a 580-series or newer driver. We'll pick the wheel from your report.
**Unverified until you run `scripts/check_env.sh`.**

## 6. Licence register (each item individually)

| Component | Licence | Commercial use | Notes |
|---|---|---|---|
| FLAME 2023 **Open** model | CC-BY-4.0 + no pornographic use (MPI) | ✅ with attribution | Older FLAME versions are non-commercial. **To verify:** whether the UV layout, masks and landmark files in the Open download are under the same licence (flame.is.tue.mpg.de is blocked from this session) |
| Our FLAME layer, loader, fitter, correspondence, texture code | Ours | ✅ | Written from the published FLAME paper's equations; no MPI/MICA/DECA code copied |
| MediaPipe library | Apache-2.0 | ✅ | |
| Face Landmarker model | Apache-2.0 (model card) | ✅ | |
| Multiclass Selfie Segmenter model | Apache-2.0 (model card) | ✅ | |
| MediaPipe canonical face mesh | Apache-2.0 | ✅ | Used to build the correspondence |
| PyTorch | BSD-3-Clause | ✅ | CUDA wheels bundle NVIDIA runtime libraries under NVIDIA's redistributable EULA (fine for use) |
| NumPy, SciPy | BSD | ✅ | |
| OpenCV (4.5+) | Apache-2.0 | ✅ | |
| diffusers, transformers, accelerate, safetensors | Apache-2.0 | ✅ | |
| SDXL inpainting 0.1 (diffusers) | CreativeML Open RAIL++-M | ✅ with use restrictions | Outputs are yours; the licence's use restrictions (no harmful/illegal use, etc.) must be passed on to Studio users |
| SDXL text encoders / VAE (inside the checkpoint) | Same RAIL++-M | ✅ | |
| sdxl-vae-fp16-fix | MIT | ✅ | |
| Real-ESRGAN code + x4plus weights | BSD-3-Clause | ✅ | |
| spandrel (model loader) | MIT | ✅ | Avoids `basicsr`, which is heavy and breaks with newer torchvision |
| Blender 4.5 | GPL-3 | ✅ | Files you create with Blender are not covered by the GPL |
| PyTorch3D | BSD-3-Clause | ✅ | Not used in v1 |
| **Excluded (non-commercial):** MICA, SMIRK, DECA, EMOCA, earlier FLAME versions, nvdiffrast, InsightFace/ArcFace, BiSeNet / CelebAMask-HQ face parsing, GFPGAN's facexlib parsing, CodeFormer, FLUX.1-dev/Kontext-dev, FFHQ-UV | | ❌ | |

Also needed for commercial use: **consent** from the person in the photo (face images are biometric data).

## 7. Main risks
1. The FLAME 2023 Open package may not include UVs under the open licence. *Fallback:* our own UV unwrap in Blender.
2. The correspondence quality (step 3) limits fit accuracy. *Mitigation:* inner-face landmarks only, and the contour comes from silhouettes.
3. SDXL may alter identity or be too slow on 4 GB. *Mitigation:* masks, low strength, staged v1a/v1b.
4. Hair v1 is basic.

## 8. Approvals requested
1. Paste the original `blender-print-texture` instructions into the skill file.
2. Run `scripts/check_env.sh` on Ubuntu and share the output.
3. Register for and download FLAME 2023 Open (and confirm its licence page covers the UV files).
4. Approve v1a (≈3.5 GB, or ≈0.6 GB CPU-only), then v1b (+≈7.3 GB SDXL).
