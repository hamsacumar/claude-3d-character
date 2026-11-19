# Licence manifest

The rule: **any asset whose licence is unclear is excluded.** Nothing in this manifest is downloaded,
installed or committed until the user approves the final plan and download list.

Status values: `verified` (licence read from a primary source) · `pending` (not yet identifiable) ·
`excluded` (non-commercial or unclear: never used).

## A. FLAME 2023 Open (kept separate from every other asset)

Location once approved: `third_party/flame2023_open/` (git-ignored until every file below is `verified`).
No other FLAME asset may be placed in this folder or loaded by the code. The loader accepts only the files
and SHA-256 hashes listed here.

Licence evidence: `docs/licenses/FLAME_licence_record_2026-11-19.md` (official Open Model License text,
read 2026-11-19).

| File (inside `FLAME2023Open.zip`) | SHA-256 | Source | Licence | Commercial use | Redistribution | Status |
|---|---|---|---|---|---|---|
| `FLAME2023Open.zip` (the archive itself) | to record | download.is.tue.mpg.de (`sfile=FLAME2023Open.zip`), via the user's sign-in | Open Model License (CC Attribution, homepage: CC-BY-4.0) | Yes, with attribution; no pornographic, fake, libelous, misleading or defamatory content | Yes, with credit, licence link and change notice | pending: contents unknown |
| *each file listed by `unzip -l`* | to record | same | **must be shown to be part of "the FLAME 2023 Open model, and software"**; anything else (e.g. a README pointing to other licences, texture or mask files) is checked separately | — | — | pending |

The ZIP is committed to GitHub only after **every** row is `verified`. Any file that isn't verified is
deleted from the working copy, not ignored.

## B. Excluded FLAME assets (never used)

| Asset | Licence | Reason |
|---|---|---|
| FLAME 2017 / 2019 / 2020 / 2023 (non-Open), FLAME Blender add-on | MPI academic licence | Non-commercial |
| FLAME texture space | CC BY-NC-SA 4.0 | Non-commercial |
| Registered D3DFACS data | MPI data licence | Non-commercial |
| FLAME vertex masks, landmark embeddings, other separate downloads | Not named by the Open Model License | Unclear, so excluded |
| MICA / DECA / EMOCA / SMIRK code and weights (incl. MICA's MediaPipe embedding) | Non-commercial | Non-commercial |

## C. Proof-of-concept dependencies (verified 2026-11-19)

| Item | Version | Source checked | Licence | Commercial | Redistribution |
|---|---|---|---|---|---|
| uv (environment manager, standalone binary, SHA-256 checked) | 0.13.9 | PyPI metadata / astral-sh/uv release | MIT or Apache-2.0 | Yes | Yes |
| CPython (installed by uv, project-local) | 3.12.x | python.org | PSF-2.0 | Yes | Yes |
| torch (CPU-only wheel, from download.pytorch.org/whl/cpu) | 2.15.0 | PyPI metadata (same project licence) | Apache-2.0 AND BSD-2/3-Clause AND MIT AND BSL-1.0 AND ISC AND Zlib (all permissive) | Yes | Yes, with notices |
| numpy | 2.5.5 | PyPI metadata | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | Yes | Yes |
| scipy | 1.18.1 | PyPI metadata | BSD-3-Clause | Yes | Yes |
| opencv-contrib-python (pulled in by mediapipe; replaces opencv-python, which must not be installed alongside it) | 5.1.0.95 | PyPI metadata | Apache-2.0 | Yes | Yes |
| mediapipe | 1.2.3 | PyPI metadata | Apache-2.0 | Yes | Yes |
| Face Landmarker bundle: `face_detector.tflite` (BlazeFace short range) | 2023-05-03 | Google model card | Apache-2.0 | Yes | Yes |
| Face Landmarker bundle: `face_landmarks_detector.tflite` (Face Mesh V2) | 2022-09-15 | Google model card | Apache-2.0 | Yes | Yes |
| Face Landmarker bundle: `face_blendshapes.tflite` (Blendshape V2) | 2022-11-11 | Google model card | Apache-2.0 | Yes | Yes |
| Multiclass Selfie Segmenter (`selfie_multiclass_256x256.tflite`) | 2023-05-10 | Google model card | Apache-2.0 | Yes | Yes |
| MediaPipe canonical face mesh (`c3d/data/canonical_face_model.obj`) | — | google-ai-edge/mediapipe repository | Apache-2.0 | Yes | Yes (NOTICE kept) |
| Blender | 4.5.14 (user-installed) | blender.org | GPL-3 (program); output files are not covered by the GPL | Yes | n/a (not redistributed) |

### C.1 Transitive dependencies (resolved from PyPI metadata, 2026-11-19)

| Package | Version | Licence | Commercial | Pulled in by |
|---|---|---|---|---|
| matplotlib | 3.11.2 | Matplotlib licence (PSF-based, permissive) | Yes | mediapipe |
| absl-py | 2.5.1 | Apache-2.0 | Yes | mediapipe |
| flatbuffers | 25.12.19 | Apache-2.0 | Yes | mediapipe |
| sounddevice | 0.5.6 | MIT | Yes | mediapipe (audio tasks only; not used) |
| certifi | 2026.10.23 | MPL-2.0 (file-level copyleft; used unmodified) | Yes | mediapipe |
| cffi / pycparser | 2.1.1 / 3.12 | MIT-0 / BSD-3-Clause | Yes | sounddevice |
| contourpy, cycler, kiwisolver | 1.4.0, 0.12.1, 1.5.1 | BSD-3-Clause | Yes | matplotlib |
| fonttools | 4.68.0 | MIT | Yes | matplotlib |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | Yes | matplotlib |
| pillow | 13.0.0 | MIT-CMU | Yes | matplotlib |
| pyparsing | 3.3.3 | MIT | Yes | matplotlib |
| python-dateutil / six | 4.0.0 / 1.17.0 | BSD-3-Clause / MIT | Yes | matplotlib |
| filelock | 4.2.12 | MIT | Yes | torch |
| typing-extensions | 4.16.0 | PSF-2.0 | Yes | torch |
| setuptools | 84.2.1 | MIT | Yes | torch |
| sympy / mpmath | 1.14.0 / 1.4.1 | BSD | Yes | torch |
| networkx | 3.7 | BSD-3-Clause | Yes | torch |
| jinja2 / markupsafe | 3.1.6 / 3.0.4 | BSD-3-Clause | Yes | torch |
| fsspec | 2026.9.0 | BSD-3-Clause | Yes | torch |

The exact installed set is recorded by `scripts/setup_p0.sh` in `output/p0_installed_packages.txt` and compared against this table; any package not listed here is reported before use.

## D. Later stages: not approved, to be verified individually at their own approval step
SDXL inpainting 0.1, sdxl-vae-fp16-fix, Real-ESRGAN weights, spandrel, MakeHuman/MPFB CC0 assets, CUDA PyTorch.
