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
| torch (CPU-only wheel `torch-2.15.0+cpu-cp312-cp312-manylinux_2_28_x86_64.whl`, 209,530,490 bytes, SHA-256 `0955c7e3…5be3`, from the PyTorch CPU index) | 2.15.0+cpu | Wheel metadata (`License-Expression`, `Requires-Dist`: no CUDA dependencies), read 2026-11-19 | Apache-2.0 AND BSD-2/3-Clause AND MIT AND BSL-1.0 AND ISC AND Zlib (all permissive) | Yes | Yes, with notices |
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
| contourpy, cycler, kiwisolver | 1.4.0, 0.12.1, 1.5.1 | BSD-3-Clause (cycler and kiwisolver: BSD-3-Clause per PyPI classifiers) | Yes | matplotlib |
| fonttools | 4.68.0 | MIT | Yes | matplotlib |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | Yes | matplotlib |
| pillow | 13.0.0 | MIT-CMU | Yes | matplotlib |
| pyparsing | 3.3.3 | MIT | Yes | matplotlib |
| python-dateutil | 4.0.0 | BSD-3-Clause (dual Apache-2.0) | Yes | matplotlib |
| tzdata | 2026.6 | Apache-2.0 | Yes | python-dateutil 4.x |
| filelock | 4.2.12 | MIT | Yes | torch |
| typing-extensions | 4.16.0 | PSF-2.0 | Yes | torch |
| setuptools | 84.2.1 | MIT | Yes | torch |
| sympy / mpmath | 1.14.0 / 1.3.0 | BSD / BSD-3-Clause | Yes | torch (mpmath via sympy, which requires mpmath<1.4) |
| networkx | 3.7 | BSD-3-Clause | Yes | torch |
| jinja2 / markupsafe | 3.1.6 / 3.0.4 | BSD-3-Clause | Yes | torch |
| fsspec | 2026.9.0 | BSD-3-Clause | Yes | torch |

### C.2 Machine-readable allow-list (checked by `scripts/p0_tools.py`)

Resolved from PyPI metadata for CPython 3.12, Linux x86-64, glibc 2.35 (2026-11-19). `scripts/setup_p0.sh`
compares (1) uv's dry-run resolution **before anything is installed** and (2) the installed environment
**after** installation against this list. Any package that isn't listed, any version mismatch, or any CUDA
package (`nvidia-*`, `cuda-*`, `triton`) stops the setup. Each entry must also appear in a table above.
`constraints-p0.txt` must equal this list without `torch`.

```p0-allowed-packages
torch==2.15.0+cpu
absl-py==2.5.1
certifi==2026.10.23
cffi==2.1.1
contourpy==1.4.0
cycler==0.12.1
filelock==4.2.12
flatbuffers==25.12.19
fonttools==4.68.0
fsspec==2026.9.0
jinja2==3.1.6
kiwisolver==1.5.1
markupsafe==3.0.4
matplotlib==3.11.2
mediapipe==1.2.3
mpmath==1.3.0
networkx==3.7
numpy==2.5.5
opencv-contrib-python==5.1.0.95
packaging==26.3
pillow==13.0.0
pycparser==3.12
pyparsing==3.3.3
python-dateutil==4.0.0
scipy==1.18.1
setuptools==84.2.1
sounddevice==0.5.6
sympy==1.14.0
typing-extensions==4.16.0
tzdata==2026.6
```

## D. Later stages: not approved, to be verified individually at their own approval step
SDXL inpainting 0.1, sdxl-vae-fp16-fix, Real-ESRGAN weights, spandrel, MakeHuman/MPFB CC0 assets, CUDA PyTorch.
