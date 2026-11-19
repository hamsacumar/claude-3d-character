# Implementation Plan v1 (revision 2): Photo → FLAME 2023 Open head → Blender → print-colour texture

Status: **waiting for approval**. Nothing has been installed or downloaded for this plan.

## 0. Decisions applied in this revision
1. **The expression and gaze in the photo are preserved.** No automatic neutralization and no jaw closing.
   This matches `blender-print-texture` §2 ("Preserve … expression, gaze direction").
2. **Hair must be printable:** a scalp colour texture plus a separate **hair shell mesh**. No hair curves in
   deliverables.
3. **SDXL and any texture enhancement are deferred.** They are not part of the proof of concept or v1a.
4. **A FLAME reconstruction proof of concept (PoC) comes first.** It has measurable acceptance criteria (§3).
5. The texture stage now **follows the restored skill exactly**: registered orthographic painting views,
   one 4096 × 4096 colour image per figure, emission bake, no reliance on extra maps (§5).
6. Licences are verified from primary sources before any download request (§7 and
   `docs/licenses/FLAME_licence_record_2026-11-19.md`).

## 1. Phases

| Phase | Content | Downloads | Needs approval |
|---|---|---|---|
| **P0: FLAME proof of concept** | Fit FLAME 2023 Open to one photo; Blender 4.5.14 scene; front, 3/4 and side renders; front comparison; landmark error report; correspondence validation | ~0.5 GB + FLAME zip | **Yes, this request** |
| v1a: Character geometry | Mouth interior/teeth decision, hair shell, eyes, printable assembly, base texture from registered photo projection | small (see §6) | After P0 review |
| v1b: `blender-print-texture` | The skill's §1–§14 on a copy of the v1a figure, with an approved local image-editing model | ~7.3 GB (SDXL), decided later | After v1a review |

## 2. How P0 works

All of this is **built by us**. No existing FLAME fitting code is used. Every part is tested as described in §4,
not assumed to work.

| Step | What | Implementation |
|---|---|---|
| P0.1 | Inspect `FLAME2023Open.zip`: file list, model keys, vertex/face counts, number of shape and expression components, whether UVs are present | `unzip -l` + a loader that reads the `.pkl` **without `chumpy`**: a restricted unpickler that maps chumpy arrays to NumPy |
| P0.2 | FLAME layer: template + shape/expression blendshapes + pose correctives + linear blend skinning (global, neck, jaw, 2 eyes) | Our PyTorch code, written from the FLAME paper (SIGGRAPH Asia 2017, §3). **Tested** against FLAME's own template, plus analytic checks (§4 T1) |
| P0.3 | MediaPipe → FLAME correspondence (468 points → triangle + barycentric coordinates on the FLAME surface) | Our one-time registration: hand-picked anatomical anchors → similarity alignment → non-rigid ICP on the face region → closest-surface projection. **Validated as in §4 T2–T5** |
| P0.4 | Photo analysis | MediaPipe Face Landmarker (478 points, blendshape scores) + Multiclass Selfie Segmenter (hair, face skin, body skin, clothes) |
| P0.5 | Fitting | Plain PyTorch, Adam then L-BFGS, staged: (1) camera + head rotation from stable landmarks; (2) + shape β, expression ψ, jaw and eye pose; (3) + outline term (jaw/cheek contour against the face mask's distance transform) and shading term (photo vs albedo × spherical-harmonic lighting at visible vertices). Regularizers: β and ψ priors, pose limits, eyelid–eyeball non-penetration. **The expression is kept.** CPU only |
| P0.6 | Blender 4.5.14 scene | Headless `bpy` script: FLAME mesh (topology unchanged), eyeballs, a camera that reproduces the photo's view, neutral lighting, cameras for front, 3/4 and side (plus back, informational only) |
| P0.7 | Renders and comparison | Clay renders (geometry only) and **evaluation-only** photo-projected renders. The projection is used only to judge likeness and is **not** the texture deliverable. Front render overlaid on the photo, with side-by-side views |
| P0.8 | Report | `poc_report.md` + JSON: landmark errors per region, outline error, parameter ranges, penetration checks, timings, and a description of where the reconstruction is inaccurate |

P0 runs on **CPU** (PyTorch CPU build); no CUDA install is needed. Blender renders with Cycles or EEVEE on your
GPU. Hair, teeth and texture enhancement are **not** part of P0.

## 3. P0 acceptance criteria

The errors are 2D distances in the photo, expressed as a percentage of **inter-ocular distance (IOD)**: the
distance between the outer eye corners.

The criteria are set relative to MediaPipe's own accuracy. Its model card reports ~2.76 % IOD mean
absolute error, so a fit cannot honestly be expected to beat that.

| # | Criterion | Threshold |
|---|---|---|
| A1 | Runs end to end on your Ubuntu machine with Blender 4.5.14, with no downloads beyond the approved list | Pass/fail |
| A2 | Output mesh is unchanged FLAME 2023 Open topology (vertex and face counts equal the template's); the expression/jaw/eye pose from the photo is preserved, not neutralized | Pass/fail |
| A3 | Mean landmark error, all fitted landmarks | **≤ 4.0 % IOD** |
| A4 | Mean error per region: eyes, brows, nose, lips, outline | each **≤ 6.0 % IOD**, all reported |
| A5 | Eye corners, mouth corners, nose base (key anatomical points) | each **≤ 3.5 % IOD** |
| A6 | Jaw/cheek outline: mean distance from the projected FLAME contour to the face-mask boundary | **≤ 4.0 % IOD** |
| A7 | Plausibility: all shape coefficients within ±3 SD; no eyelid/eyeball or upper/lower-lip interpenetration beyond 0.5 mm | Pass/fail, reported |
| A8 | Front visual comparison: the overlay and side-by-side show no visibly misplaced eyes, nose, mouth or face outline | **Your sign-off** |
| A9 | 3/4 and side clay renders are produced and the limitations section names the specific inaccuracies (see below) | Pass/fail |
| A10 | Correspondence validation T1–T4 pass (§4); T5 is reported if extra photos exist | Pass/fail |
| A11 | Reproducible: two runs with the same seed give identical parameters | Pass/fail |
| A12 | Only verified-licence components were used; the FLAME zip contents were checked against the licence record before use | Pass/fail |

**Optional profile check (recommended):** if you also supply a **side photo of the same person**, it is not used for
fitting. It is used only to measure profile error: nose-tip, chin and forehead offsets as a % of face height. A
single frontal photo cannot measure the profile, so without it the profile accuracy is **unknown**, not "good".

**Where P0 is expected to be inaccurate (to be confirmed by the report):**
- **Profile:** nose projection, chin and forehead depth, and skull length come mostly from FLAME's statistical prior.
- **Ears:** close to FLAME's average shape.
- **Eyelids:** fine eyelid shape is limited by FLAME's resolution.
- **Mouth:** an open mouth shows **no teeth** (FLAME has none). This is a v1a decision.
- **Hair:** the head is bald.

## 4. Validating the custom FLAME layer and the MediaPipe → FLAME correspondence

Nothing is assumed correct. Each test produces numbers or images that go into the PoC report.

| Test | What it proves | Pass condition |
|---|---|---|
| **T1 FLAME layer correctness** | Our PyTorch FLAME reproduces the model: zero parameters give the template exactly; single shape/expression components match `template + basis × value` directly from the `.pkl`; jaw and eye rotations move only the expected vertices (checked against skinning weights); left/right symmetry of the mean head | Max vertex deviation **< 1e-5 m** for the linear checks. Joint checks are exact up to float tolerance |
| **T2 Registration residuals** | The MediaPipe canonical mesh was actually deformed onto the FLAME template | After non-rigid ICP: median point-to-surface distance **< 1.0 mm**, max **< 3.0 mm** in the face region. Anchor residuals reported individually |
| **T3 Semantic overlay** | Points land on the right **features**, not just near the surface: eyelid points on the lid margin (not the eyeball), lip points on the vermilion border and inner lip line, brow points on the brow ridge, nose points on the alae and tip | Front and side Blender renders of the FLAME template with MediaPipe contours drawn on it. **Reviewed visually by me and by you**; failures fixed by adjusting anchors or region weights |
| **T4 Synthetic recovery** | The fitter and correspondence together can recover a known head: sample random FLAME heads (β, ψ, jaw, eye pose, camera), generate their landmarks through the correspondence, add noise at MediaPipe's level, fit, compare | 2D reprojection **< 1 % IOD** without noise. 3D vertex error reported **per region and per axis**: this measures how much depth a single view really constrains |
| **T5 Systematic-bias check on real photos** | Detects correspondence points that are consistently off on real faces (e.g. a lid point that always sits 2 px too high) | Needs **≥ 10 photos** with permission for commercial R&D use. Per-landmark mean residual vector across photos: any landmark with a consistent bias **> 2 % IOD** is flagged and its embedding re-optimized. With one photo this test is not meaningful and is reported as "not run" |

What these tests **cannot** prove: true 3D accuracy of a real person's profile. Only the optional profile photo,
or a 3D scan, can measure that.

## 5. Texture stage: aligned with the restored `blender-print-texture` skill

Two separate things:
- **Base appearance (v1a, Stage 1 output, not the skill):** the photo is projected onto the fitted mesh through
  the fitted camera, with a depth test and viewing-angle weights. Lighting is removed using the fitted SH
  lighting. The parts the photo cannot see (back of head, under the chin, behind the ears) get a smooth,
  uniform skin or hair colour taken from nearby visible areas. They are **labelled as inferred** and have no
  invented markings. The result is the figure's starting colour texture.
- **Enhancement (v1b) = the skill, run as written** on a **copy** of the v1a figure:
  - §1 inspect; §2 protected backup + working copy; §3 original UV layers kept, a separate print-atlas UV layer
    only if needed, with the reason stated.
  - §4 compare with this figure's reference only; **where the reference does not show an area, keep the
    existing appearance** (no AI invention of the back or sides).
  - §5 **flat albedo previews from known orthographic cameras**, with each camera's transform, framing and
    bounds recorded; these previews are the edit targets.
  - §6 AI paint guide on those previews (model target and appearance reference clearly separated; surface colour
    only; features locked; drifting guides rejected; prompts saved).
  - §7 face, eye and hair colour goals, including **no noisy pore detail**; §8 clothing protection.
  - §9 project only registered, inspected guides with masks, visibility, angle falloff and bounds.
  - §10 **one 4096 × 4096 colour image per figure**, baked through an **emission/unlit pass**, colour management
    handled deliberately, polygon material indices cached and restored, margins checked, no 8K deliverable.
  - §11 AO only if requested; **no reliance on roughness, normal, bump or displacement maps**.
  - §12 simple final material; PNG saved and packed into the copied `.blend`.
  - §13 full verification list; §14 save, open, report.
- **Gaps that remain:** (1) the §5 "painting-and-baking guidance" document has not been supplied; (2) §6's
  "imagegen skill / built-in image generation tool" doesn't exist in Claude Code and will be replaced by an
  approved local model (decided at v1b).

Conflicts from revision 1, now resolved:

| Revision 1 | Conflict | Revision 2 |
|---|---|---|
| Step 5 "Neutralize" | §2 preserve expression/gaze | Removed; the expression is kept |
| Step 10c SDXL invents side/back | §4 don't invent unseen areas | Removed; unseen areas keep the inferred base colour |
| Step 10b SDXL skin detail | §7 no noisy pore detail | Removed |
| Step 11 "+ roughness" | §10–§12 single colour image | Single colour image only |
| Steps 8–10 edit the photo directly | §5 registered orthographic albedo previews | The skill's §5 workflow is used |
| Step 7 hair curves | printable output | Scalp texture + hair shell mesh |
| "AI fills the back" in quality notes | §4 | Inferred areas are labelled, not invented |

## 6. Downloads and resources

**P0 (this approval):**

| Item | Size | Licence (verified) |
|---|---|---|
| `uv` + Python 3.12 virtual environment | ~45 MB | uv: MIT/Apache-2.0; CPython: PSF |
| PyTorch 2.15 **CPU-only** build | ~0.2 GB | BSD-3-style (PyPI: Apache-2.0 AND BSD-3-Clause AND others, all permissive) |
| numpy, scipy, opencv-python, mediapipe | ~0.15 GB | BSD-3 / BSD / Apache-2.0 / Apache-2.0 |
| Face Landmarker bundle (detector + mesh + blendshapes) | 3.7 MB (already used in v0) | Apache-2.0 (each of the 3 model cards checked) |
| Multiclass Selfie Segmenter | ~16 MB | Apache-2.0 (model card checked) |
| `FLAME2023Open.zip` (you sign in and download) | unknown until signed in | CC-BY-4.0-based Open Model License (verified, see §7) |
| **Total** | **≈ 0.4–0.5 GB + FLAME zip** | |

Why Python 3.12: PyTorch 2.15 requires Python ≥ 3.11 and current NumPy requires ≥ 3.12. Ubuntu 22.04 ships 3.10, so
`uv` installs 3.12 in the project folder only and leaves the system Python untouched. All wheels are
`manylinux_2_28`, which needs glibc ≥ 2.28; Ubuntu 22.04 has 2.35.

**GPU and memory:** P0 needs **no CUDA**: fitting on CPU takes roughly 1–5 minutes, with about 2 GB of RAM.
Blender uses your RTX 3050 for renders. The CUDA PyTorch choice is deferred to v1b; your driver version from
`scripts/check_env.sh` decides it (CUDA 12.8 wheels need driver ≥ 570, CUDA 13 wheels need driver ≥ 580).

**Not used: PyTorch3D or nvdiffrast.** PyTorch3D isn't needed (BSD, conda-forge builds only). nvdiffrast is
excluded because its NVIDIA licence is non-commercial.

## 7. Licence register

| Component | Licence | Source checked | Commercial |
|---|---|---|---|
| FLAME 2023 **Open** model and software | Open Model License: CC Attribution; credit + link to licence + note changes; **no pornographic use; no fake, libelous, misleading or defamatory content** | flame.is.tue.mpg.de/modellicense.html, read 2026-11-19; homepage news: "CC-BY-4.0" | ✅ with attribution |
| FLAME 2017/2019/2020/2023 (non-Open), FLAME Blender add-on | Academic licence, non-commercial | same page | ❌ not used |
| FLAME texture space | CC BY-NC-SA 4.0 | texturelicense.html | ❌ not used |
| Registered D3DFACS data | Non-commercial research | datalicense.html | ❌ not used |
| FLAME vertex masks, landmark embeddings, other separate downloads | Not covered by the Open Model License unless stated | — | ❌ not used |
| Contents of `FLAME2023Open.zip` | **Unverified until you sign in** and list it | — | Checked at P0.1 |
| MediaPipe library 1.2.3 | Apache-2.0 | PyPI metadata | ✅ |
| Face detector (BlazeFace short range), Face Mesh V2, Blendshape V2 models | Apache-2.0 | Google model cards (storage.googleapis.com/mediapipe-assets) | ✅ |
| Multiclass Selfie Segmenter | Apache-2.0 | Google model card | ✅ |
| MediaPipe canonical face mesh (for the correspondence) | Apache-2.0 | mediapipe repository | ✅ |
| PyTorch 2.15 | Apache-2.0 AND BSD-2/BSD-3 AND MIT AND others (all permissive) | PyPI metadata | ✅ |
| NumPy | BSD-3-Clause and permissive components | PyPI | ✅ |
| SciPy | BSD | PyPI | ✅ |
| opencv-python | Apache-2.0 | PyPI | ✅ |
| Blender 4.5.14 | GPL-3 (program); your output files are not covered | blender.org | ✅ |
| Our code (FLAME layer, loader, correspondence, fitter, Blender scripts) | Ours | — | ✅ |
| v1a/v1b candidates (SDXL inpainting, sdxl-vae-fp16-fix, Real-ESRGAN, spandrel, CC0 MPFB teeth/eye assets) | To be re-verified individually at their approval step | — | — |

**Using real people's faces:** the Open Model License forbids "fake, libelous, misleading or defamatory content".
Use photos only with the person's **consent**, and never present a character as genuine footage of them.

## 8. What I need for P0
1. Approval of the P0 downloads in §6.
2. FLAME: sign in, download `FLAME2023Open.zip`, run the command below and send me the output (it lists the
   file names only; nothing is extracted):
   ```
   unzip -l FLAME2023Open.zip
   ```
3. Where development happens:
   - **(a) recommended:** commit the zip to this private repository (CC-BY allows sharing with attribution,
     which I'll add) so I can build and test the correspondence and fitter here;
   - **(b)** run each step locally and send me the outputs.
4. One reference photo (with consent), plus an optional side photo of the same person for the profile check, and
   optionally ≥ 10 consented photos for T5.
5. The output of `scripts/check_env.sh`.
