# Implementation Roadmap

Each phase ends with something that can be demonstrated, and with a measured identity score.

## Phase 0: Foundations (no heavy dependencies)
- Repository scaffold: `pyproject.toml` (with extras), the `src/c3d` package, ruff, mypy, pytest, CI.
- Core: `Stage`/`Pipeline`, artifact dataclasses, config presets, job folders, logging.
- Model registry + weight manager (download is disabled until phase 1).
- Blender bridge: launch Blender headless, build a test mesh from `.npz`, export GLB. This checks Blender 4.5 `bpy` end to end.
- **Exit:** `c3d reconstruct` runs end to end with stub stages and outputs a placeholder GLB.

## Phase 1: Model spike and evaluation harness
- Build an evaluation set: 30–50 consented or permissively licensed photos (frontal, 3/4, varied
  ethnicity, age, lighting, glasses or beard). Optionally add the NoW benchmark for shape error.
- Install the candidates in an isolated environment. Compare MICA, EMOCA/DECA, SMIRK and newer trackers
  on identity similarity, NoW error, speed and VRAM.
- Licensing decision: research-only (FLAME / ArcFace) versus a commercial path.
- **Exit:** a written model choice backed by numbers.

## Phase 2: Geometry v1
- Preprocessing (MediaPipe, parsing, quality gate).
- MICA shape + SMIRK expression/pose adapters.
- Refinement with differentiable rendering (landmark, photometric, silhouette and identity losses).
- Neutralization; export of an untextured head to Blender.
- **Exit:** a neutral FLAME head with identity similarity ≥ target (set in phase 1), in under 30 s on a 12 GB GPU.

## Phase 3: Texture v1
- UV projection with visibility, SH de-lighting, mirror fill, prior-based fill and seam blending.
- Generated normal and roughness maps; skin shader in Blender with subsurface scattering; Cycles bake.
- Provenance mask in the outputs.
- **Exit:** a textured GLB a human reviewer recognizes as the same person; multi-view report.

## Phase 4: Quality upgrades
- Detail displacement (DECA-style or HRN-style), learned de-lighting and albedo, diffusion UV inpainting.
- Texture super-resolution; eyes, teeth and inner mouth assets.
- **Exit:** a measurable improvement over v1 on the evaluation set.

## Phase 5: Rig and Studio integration
- FLAME expressions as Blender shape keys, a jaw/eye/neck armature, ARKit-style blendshape mapping.
- FastAPI job service, progress events, GPU worker, artifact storage.

## Phase 6: Full character
- SMPL-X body that shares the FLAME head; body shape from a photo or chosen by the user.
- Hair and accessories (strand or card generation, or image-to-3D for hair only), clothing.
- **Exit:** a rigged full-body character from one photo plus user choices.

## Main risks
| Risk | Mitigation |
|---|---|
| Non-commercial licenses (FLAME, BFM, ArcFace, MICA) | Decide in phase 1; adapters let us swap models; registry tracks licenses |
| Identity drift in neutral or profile views | Identity loss + multi-view identity metric used as a CI gate |
| Baked-in lighting in the texture | SH de-lighting now, a learned model in phase 4 |
| Hair and occlusions | Masked out in v1, separate assets later |
| VRAM on user hardware | Presets; diffusion is optional; CPU fallback for small inputs |
