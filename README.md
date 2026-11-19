# Claude 3D Character

**Goal of the current experiment:** ONE FACE PHOTO → RECOGNIZABLE 3D HEAD → TEXTURED BLENDER PROJECT.

Code is developed in GitHub (Claude Code Web), and you run it locally on Ubuntu, where Blender lives.

## Run it on your Ubuntu machine
```bash
git clone https://github.com/hamsacumar/claude-3d-character.git
cd claude-3d-character
git checkout claude/stoic-faraday-bkh2da
scripts/setup.sh                       # venv + 3.7 MB MediaPipe model (CPU only)
scripts/make_head.sh ~/Pictures/face.jpg
```
This writes `output/face/head.blend` and opens it in Blender (`/usr/local/bin/blender`,
override with `BLENDER=/path/to/blender`). Options: `--render` writes Cycles preview PNGs,
`--no-open` skips launching the UI.

In Blender: the viewport is already in Material Preview. Orbit with the middle mouse button, press
`Numpad 0` for the portrait camera, `F12` to render, and `Space` to play the 240-frame turntable.
The source photo stands next to the head for comparison.

**Best input photo:** frontal (head turned less than 20°), even lighting, neutral expression, face at least 500 px tall,
no glasses or hair covering the face.

## What happens
1. `c3d/reconstruct.py` (venv, CPU) does three things:
   - It analyzes the photo: face detection, 478 dense 3D landmarks, head pose, 52 expression scores
     and quality warnings (`analysis.json`, `landmarks_overlay.png`).
   - It builds the face surface from the person's own landmarks and aligns it to a frontal metric frame.
     It then completes the head behind the face from those face proportions.
   - It projects the photo as the face texture. Vertices seen at grazing angles fade into the skin colour sampled from the photo.
2. `c3d/blender_build.py` (inside Blender) builds the scene:
   - the mesh, UVs and subdivision;
   - a skin material (photo texture, subsurface scattering, bump detail, sampled skin and hair colours);
   - 3-point lighting, an 85 mm camera, the turntable and the reference photo.

   The textures are packed into the `.blend`, so the file is self-contained.

## Docs
- [docs/TOOL_COMPARISON.md](docs/TOOL_COMPARISON.md): tool research and why v0 uses MediaPipe; the v1 upgrade path (FLAME)
- [docs/RECONSTRUCTION_APPROACH.md](docs/RECONSTRUCTION_APPROACH.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md),
  [docs/ROADMAP.md](docs/ROADMAP.md): the long-term production design (deferred until the experiment is done)

## Photo → 3D head without FLAME (`head_v1`)
```bash
scripts/make_head_v1.sh ~/Pictures/face.jpeg
```
Uses the project-local P0 environment (`.venv-p0`) and `models/face_landmarker.task`; downloads nothing.
Output in `output/head_v1/<photo>/`: `head.blend` (opens in Blender), front / three-quarter / side renders,
`04_sheet.png` (photo next to the renders), `analysis.json`, `head_report.json` (reconstructed vs inferred parts).
Options: `--use-cycles` (renders with Cycles instead of EEVEE), `--depth-scale 1.2` (exaggerate or flatten the
estimated face depth), `--no-open`. Code: `c3d/head_v1/` (analysis, NumPy geometry, Blender builder); tests:
`python tests/test_head_geometry.py`.
