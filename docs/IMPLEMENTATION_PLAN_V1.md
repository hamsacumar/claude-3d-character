# Implementation Plan v1 (revision 3, final for approval)

Status: **waiting for explicit approval of this plan and the download list in §8.**
Until then: no FLAME download, no dependency installation, no implementation.

## 0. Decisions in force
1. **Preserve the person:** expression, eye direction and facial proportions from the photo are kept as closely as
   possible. No neutralization and no jaw closing (§4).
2. **Printable hair** (scalp colour + separate hair shell mesh) comes in v1a, not the proof of concept.
3. **CPU-only first experiment** in a **project-local** Python environment. No CUDA, no SDXL, no texture enhancement.
4. **FLAME 2023 Open is kept separate** from every other FLAME asset, governed by
   `docs/licenses/LICENCE_MANIFEST.md`. Any asset with an unclear licence is excluded.
5. **Accuracy claims are kept honest:** 2D landmark accuracy, real 3D shape accuracy and synthetic tests are
   reported separately, and **synthetic FLAME recovery is never presented as proof of real-world likeness** (§5).
6. Later texture work follows the restored `blender-print-texture` skill exactly (§7).

## 1. Phases

| Phase | Content | Approval |
|---|---|---|
| **P0: FLAME reconstruction proof of concept** | One photo → FLAME 2023 Open fit → Blender 4.5.14 → renders, overlay, error report, reconstructed-vs-inferred list | **Requested now** |
| v1a: printable character geometry + base texture | Hair shell, mouth interior/teeth decision, eyes, base colour from registered photo projection | After P0 review |
| v1b: `blender-print-texture` (§1–§14) | On a copy of the v1a figure, with an approved local image-editing model | After v1a review |

## 2. FLAME asset handling (before any FLAME file is used)
1. **You** sign in and download `FLAME2023Open.zip` (only after approving this plan). Nothing else from the FLAME site.
2. Run `unzip -l FLAME2023Open.zip` and `sha256sum FLAME2023Open.zip`, and send me the output. Nothing is
   extracted yet.
3. I add **every file** to Section A of `docs/licenses/LICENCE_MANIFEST.md` with its source, licence, commercial-use
   and redistribution status. A file counts as verified only if it is clearly part of "the FLAME 2023 Open model,
   and software" under the Open Model License. **Unclear means excluded**, and excluded files are deleted from the
   working copy.
4. Only verified files are extracted to `third_party/flame2023_open/`. That folder is git-ignored and holds
   nothing but FLAME 2023 Open. The loader refuses any file whose SHA-256 is not in the manifest.
5. **The ZIP or its files are committed to GitHub only after every manifest row is verified**, together with an
   `ATTRIBUTION.md` (credit, licence link, list of changes) as the licence requires. Until then, development
   happens on your machine (you run each step and send me outputs) or with files you share privately once verified.

## 3. P0 pipeline (all code written by us; no existing FLAME fitting code is used)

| Step | What |
|---|---|
| P0.1 | Inspect the verified FLAME files: model keys, vertex and face counts, number of shape and expression components, joint layout, presence of UVs. The loader reads the `.pkl` without `chumpy` (a restricted unpickler) |
| P0.2 | FLAME layer in PyTorch, written from the FLAME paper: template + shape and expression blendshapes + pose correctives + linear blend skinning (global, neck, jaw, two eyes) |
| P0.3 | MediaPipe → FLAME correspondence: hand-picked anatomical anchors → similarity alignment → non-rigid ICP on the face region → closest-surface embedding (triangle + barycentric coordinates) |
| P0.4 | Photo analysis: MediaPipe Face Landmarker (478 points incl. irises, blendshape scores) + Multiclass Selfie Segmenter (hair, face skin, body skin, clothes, background) |
| P0.5 | Fitting on CPU in stages: camera and head pose → shape, expression, jaw and eye rotations → outline (face-mask distance transform) and shading (photo vs albedo × SH lighting) terms. Priors keep the shape plausible; weights are tuned so proportions, expression and gaze are preserved (§4) |
| P0.6 | Blender 4.5.14 headless scene: FLAME mesh (topology unchanged), FLAME eyeballs, a camera reproducing the photo view, neutral studio light, front, three-quarter and side cameras (back view informational) |
| P0.7 | Renders and overlays: clay (geometry only) and evaluation-only photo-projected versions. The projection is used **only** to judge likeness and is not a texture deliverable |
| P0.8 | Report: metrics JSON + `poc_report.md` |

## 4. Preserving expression, eye direction and proportions
Measured on the photo and on the fitted model's projection, then reported side by side:

| Property | Metric | Target |
|---|---|---|
| Facial proportions | Ratios to inter-ocular distance (IOD): eye widths, nose width, mouth width, face width, brow-to-chin height, eye-to-mouth height | each within **±3 %** of the photo's ratio |
| Expression | Lip gap (mouth opening), mouth-corner positions, eyelid aperture (each eye), brow height | gap and apertures within **±10 %** of the photo; corners in the A5 limit |
| Eye direction | Iris-centre landmark error; fitted eye rotation compared with the iris position inside the eye contour | iris centres **≤ 2.5 % IOD** |
| Head pose | Yaw, pitch and roll of the fit vs MediaPipe's pose estimate | reported |

When priors and data disagree (e.g. an unusual nose width), the fit favours the photo within plausible FLAME
shape limits (±3 SD), and the report says where a limit was hit.

## 5. What is measured, and what a single frontal photo cannot tell us

**Three kinds of evidence, reported separately:**

| Kind | What it tells us | What it does **not** tell us |
|---|---|---|
| **2D landmark accuracy** (the fitting photo) | How well the fitted head, seen from the photo's camera, lines up with the detected features | Anything about depth. A head with the wrong nose projection can still score perfectly in 2D |
| **3D shape accuracy** (held-out real photos of the same person) | Whether the fitted 3D shape, seen from **other** angles, matches the real person | Only the angles photographed; not the hidden back of the head |
| **Synthetic recovery** (generated FLAME heads) | That the optimizer and correspondence can recover a known FLAME head, and how much depth is identifiable from one view | **Not** real-world likeness. Real faces aren't exactly FLAME shapes and MediaPipe's errors aren't simple noise |

**From one frontal photo we can measure:** feature positions and proportions in the image plane (widths, heights,
spacing); the face outline as seen from the front; expression; eye direction; head rotation.

**From one frontal photo we cannot measure:** nose projection and profile shape, chin and forehead depth, skull
length, back of the head, ear shape (ears are seen edge-on or hidden), anything hidden by hair. These come from
FLAME's statistical prior plus MediaPipe's rough depth estimate. **Without held-out photos their accuracy is
unknown.**

### 5.1 Held-out real-photo test (when consented references exist)
- **Inputs:** the fitting photo plus 1–3 **other** photos of the same person (ideally the same session): a
  three-quarter (~30–45° yaw) and a side (~90°). These are **never used for fitting**.
- **Procedure:** the fitted **shape is frozen**. For each held-out photo only the camera and head pose are
  re-estimated; expression is re-fitted only if the person's expression differs, reported separately as
  "shape-only" and "shape + re-fitted expression".
- **Three-quarter metrics:** MediaPipe landmark error in the held-out view (normalized by face height, chin to
  mid-brow, since IOD foreshortens with yaw) and outline distance from the selfie-segmentation face mask.
- **Side metrics:** MediaPipe is unreliable beyond ~60° yaw, so the profile is measured by **silhouette**: the
  rendered profile contour against the segmented outline. That gives nose-tip, subnasale, lip, chin and forehead
  offsets as % of face height, plus the mean contour distance. The five profile points are marked by you or by me
  with your confirmation, and the marks are saved.
- **Thresholds:** these are the **first real 3D measurements**, so I propose provisional targets (three-quarter
  landmark error ≤ 5 % of face height; profile mean contour distance ≤ 3 % of face height). They are reported as
  measured results, not used to declare likeness.

### 5.2 Per-view evaluation

| View | Evidence available with only the fitting photo | Extra evidence with held-out photos | Status reported as |
|---|---|---|---|
| **Front** | 2D landmarks (A3–A6), proportions/expression/gaze (§4), overlay + side-by-side | — | Measured |
| **Three-quarter** | Visual render only | Held-out landmark + outline errors (§5.1) | "Visual only, 3D accuracy unknown", or measured |
| **Side** | Visual render only | Profile silhouette errors (§5.1) | "Visual only, 3D accuracy unknown", or measured |
| Back | Visual render only | Not measurable from these photos | Inferred |

## 6. Validation of our own code and correspondence

| Test | Proves | Pass condition |
|---|---|---|
| T1 FLAME layer | Our implementation reproduces the official model file: zero parameters give the template; single shape and expression components match `template + basis × value`; jaw and eye rotations move only their skinned vertices; mean head symmetric | max deviation < 1e-5 m (linear parts); joint checks within float tolerance |
| T2 Registration residuals | The MediaPipe canonical mesh was deformed onto FLAME's face | median < 1.0 mm, max < 3.0 mm in the face region; each anchor reported |
| T3 Semantic overlay | Points sit on the right features (lid margin, not eyeball; vermilion border; inner lip line; brow ridge; alae; nose tip) | Front and side renders reviewed by me **and you** |
| T4 Synthetic recovery | The optimizer works and how much depth one view identifies (per-axis error) | 2D reprojection < 1 % IOD noise-free; 3D errors reported. **Not evidence of real likeness** |
| T5 Real-photo bias | Finds correspondence points consistently off across real faces | Needs ≥ 10 consented photos; otherwise reported as "not run" |

## 7. P0 deliverables and acceptance

### 7.1 Output folder `output/poc/<photo-name>/`

| File | Content |
|---|---|
| `00_reference.<ext>` | The original reference photo, unmodified copy |
| `01_front_clay.png`, `01_front_projected.png` | Front render from the photo's camera: geometry only, and evaluation-only projected |
| `02_threequarter_clay.png`, `02_threequarter_projected.png` | Three-quarter render (~35° yaw) |
| `03_side_clay.png`, `03_side_projected.png` | Side render (90°) |
| `04_landmark_overlay.png` | Photo with detected (green) vs fitted (red) landmarks, error vectors, outline contour; per-region colour coding |
| `05_front_comparison.png` | Photo, front render and a 50 % blend side by side |
| `06_heldout_*.png` | Held-out view comparisons (only when held-out photos are provided) |
| `poc_report.md` + `metrics.json` | All metrics in §4, §5, §6 and §7.2 with pass/fail and plain-language inaccuracy notes per view |
| `features_reconstructed_vs_inferred.md` | A per-run list (template below) |
| `poc.blend` | Blender 4.5.14 scene with the fitted head and cameras |
| `fit_params.npz`, `licence_snapshot.md` | Fitted parameters; the manifest rows used for this run |

**Reconstructed vs inferred (filled per run, e.g. ears are marked "observed" only if visible in the photo):**

| Category | Features |
|---|---|
| **Reconstructed from the photo (2D-measured)** | Positions and proportions of eyes, brows, nose (width, length in the image), mouth, face outline seen from the front; expression (mouth opening, lip shape, eyelid aperture, brows); eye direction; head pose |
| **Weakly constrained (prior + MediaPipe depth + shading)** | Nose projection, cheek depth, chin and forehead profile, jaw depth |
| **Inferred (FLAME prior only)** | Skull top and back, ears (unless visible), neck, eyeball shape and size |
| **Not modelled in P0** | Hair, teeth and mouth interior, eyelashes, skin texture, accessories and glasses |

### 7.2 Acceptance criteria (IOD = inter-ocular distance; MediaPipe's own error is ~2.8 % IOD)

| # | Criterion | Threshold |
|---|---|---|
| A1 | Runs end to end on your Ubuntu machine, CPU-only Python, Blender 4.5.14; only approved downloads | pass/fail |
| A2 | FLAME 2023 Open topology unchanged; expression, jaw and eye pose preserved (not neutralized) | pass/fail |
| A3 | Mean landmark error, fitting photo | ≤ 4.0 % IOD |
| A4 | Mean error per region (eyes, brows, nose, lips, outline) | each ≤ 6.0 % IOD |
| A5 | Eye corners, mouth corners, nose base | each ≤ 3.5 % IOD |
| A6 | Jaw/cheek outline vs face-mask boundary | ≤ 4.0 % IOD |
| A7 | Proportions, expression and gaze targets in §4 | as listed |
| A8 | Plausibility: shape within ±3 SD; no lid–eyeball or lip interpenetration > 0.5 mm | pass/fail |
| A9 | All §7.1 files produced, including the reconstructed-vs-inferred list | pass/fail |
| A10 | Per-view status reported as in §5.2; nothing called "accurate" without a measurement | pass/fail |
| A11 | T1–T4 pass; T5 and §5.1 reported if data exists | pass/fail |
| A12 | Same seed gives identical parameters | pass/fail |
| A13 | Only manifest-verified assets used; FLAME files hash-checked | pass/fail |
| A14 | Front comparison: no visibly misplaced features | **your sign-off** |

## 8. Download list for P0 (nothing happens before approval)

Everything is project-local: `.venv/` for packages, `.tools/uv/` for the uv binary, `.tools/python/` for Python
(`UV_INSTALL_DIR`, `UV_PYTHON_INSTALL_DIR` and `UV_CACHE_DIR=.cache/uv`). There are no system package changes, no
CUDA toolkit and no driver changes. Blender isn't modified; it's only launched headless with `--factory-startup`.

| # | Item | Approx. size | Licence |
|---|---|---|---|
| 1 | uv standalone binary | ~35 MB | MIT / Apache-2.0 |
| 2 | CPython 3.12 (via uv, project-local) | ~30 MB | PSF-2.0 |
| 3 | torch 2.15.0 **CPU-only** (`2.15.0+cpu` wheel, hash-pinned, from the PyTorch CPU wheel index) | 210 MB | permissive (Apache-2.0, BSD, MIT and others) |
| 4 | numpy, scipy, mediapipe, opencv-contrib-python + 25 pinned dependencies (`constraints-p0.txt`) | 211 MB | see `docs/licenses/LICENCE_MANIFEST.md` §C |
| 5 | Face Landmarker bundle | 3.7 MB | Apache-2.0 |
| 6 | Multiclass Selfie Segmenter | ~16 MB | Apache-2.0 |
| 7 | `FLAME2023Open.zip` (you download it) | unknown until signed in | Open Model License; contents verified per §2 |
| | **Total** | **≈ 0.49 GB + FLAME zip** | |

Python 3.12 is used because PyTorch 2.15 needs ≥ 3.11 and current NumPy needs ≥ 3.12. All wheels are
`manylinux_2_28`; Ubuntu 22.04 provides glibc 2.35.
**Not included:** CUDA PyTorch, SDXL, Real-ESRGAN, PyTorch3D, nvdiffrast, any other FLAME asset.

## 9. Later stages (summary; each needs its own approval)
- **v1a:**
  - printable hair: a scalp colour texture plus a separate hair shell mesh;
  - mouth interior and teeth if the expression shows them (a CC0 asset or none, to be decided);
  - base colour from registered projection of the photo, with unseen areas filled from nearby colour and
    **labelled as inferred**.
- **v1b:** `blender-print-texture` §1–§14 exactly as written on a copy:
  - orthographic registered albedo previews;
  - AI paint guides only for areas the reference shows;
  - one 4096 × 4096 colour image baked through an emission pass;
  - no roughness or normal-map reliance;
  - a packed separate `.blend`;
  - full verification.

  The image-editing model is chosen and licence-checked at that step. Still missing: the §5
  "painting-and-baking guidance" document.

## 10. What you need to provide for P0
1. **Explicit approval** of this plan and the §8 download list.
2. Then: the FLAME zip listing and hash (§2), the `scripts/check_env.sh` output, one consented reference photo,
   and, recommended for real 3D evaluation, consented held-out three-quarter and side photos of the same person.
