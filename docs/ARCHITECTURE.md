# Architecture

> **Status:** deferred. The current focus is the working visual experiment (see README and
> docs/TOOL_COMPARISON.md). This design applies once the experiment proves the approach.

## Principles
1. **Stages with typed contracts.** Each pipeline step is a `Stage` that reads and
   writes typed artifacts. Any stage can be swapped, cached or re-run on its own.
2. **Models behind adapters.** No pipeline code imports MICA or SMIRK directly. Each sits behind an
   interface (`ShapeEstimator`, `ExpressionEstimator`, `Renderer`, `Inpainter`, ...),
   so a non-commercial model can later be replaced by a licensed one.
3. **Two processes, two Pythons.** The ML side (PyTorch, CUDA) runs in its own venv. Blender's
   bundled Python runs only `bpy` code, started as `blender -b --python ...` with a
   JSON job file. Torch never runs inside Blender.
4. **Files are the interface.** Results go to a versioned job folder (`.npz`,
   `.png`/`.exr`, `.json`). That gives caching, debugging and a clean API boundary for the Studio.
5. **Lazy, optional heavy dependencies.** Extras such as `[recon]`, `[texture-diffusion]` and `[dev]`.
   Weights are fetched by a model manager into a cache, never committed to git.

## Package layout (planned)
```
src/c3d/
  core/          # Stage base, Pipeline runner, artifact types, config, logging, errors
  io/            # image loading, EXIF orientation, job folders, mesh I/O (OBJ/GLB/NPZ)
  preprocess/    # detection, landmarks (MediaPipe), alignment, face parsing, quality gate
  models/        # registry + weight manager (checksums, licenses, cache dir)
    adapters/    # mica.py, smirk.py, emoca.py, arcface.py, bisenet.py ...
  geometry/      # FLAME layer, neutralization, mesh ops, detail/displacement
  fitting/       # differentiable-rendering refinement, losses, schedules
  render/        # Renderer interface: nvdiffrast / pytorch3d backends
  texture/       # UV projection, visibility, de-lighting, symmetry fill, inpaint, map generation
  evaluation/    # identity similarity over multiple views, landmark error, report generation
  blender/       # runs ONLY in Blender's Python: scene build, materials, bake, export
  bridge/        # launches Blender as a subprocess, job-file protocol
  api/           # CLI (typer) now; FastAPI service + job queue for the Studio later
configs/         # YAML pipeline presets: fast / quality / cpu
tests/           # unit tests (no GPU) + golden-image integration tests (GPU-marked)
```

## Data contracts (core artifacts)
| Artifact | Contents |
|---|---|
| `InputImage` | RGB array, source metadata, EXIF-corrected |
| `FaceObservation` | bbox, 478 landmarks, aligned crop + transform, parsing masks, quality scores |
| `HeadParams` | FLAME β/ψ/θ, camera, SH lighting, the model version used |
| `HeadMesh` | vertices, faces, UVs, a neutral flag, topology id |
| `TextureSet` | albedo, normal, roughness, (displacement), provenance mask, resolution |
| `QualityReport` | identity similarity per view, landmark error, warnings, timings, model versions |

## Pipeline (v1)
```
LoadImage → Preprocess → QualityGate → EstimateShape(MICA) → EstimateExpression(SMIRK)
  → RefineFit(diff-render) → Neutralize → BuildTexture → Evaluate → BlenderAssemble → Export
```
Each stage declares its inputs, outputs, device needs and a cache key
(the hash of its inputs, config and model version).

## Blender layer
- A job JSON gives paths to the mesh `.npz` and the texture PNG/EXR files, plus export targets.
- `blender/build_head.py`: creates the mesh from arrays (`from_pydata`), sets the UVs and smooth
  shading, and adds a Principled BSDF with subsurface scattering, roughness and normal maps.
- `blender/bake.py`: Cycles bake (from high detail to low detail, or a combined bake) at 2K/4K, with GPU or CPU.
- `blender/export.py`: GLB (Studio/web), FBX (DCC tools), `.blend` (source).
- Later: eyes, teeth and tongue meshes; FLAME expressions as shape keys; a jaw/neck armature.

## Integration with the AI 3D Studio
- Same entry point everywhere: `c3d reconstruct photo.jpg --preset quality --out job/`.
- Later: a `POST /jobs` service with progress events per stage, a GPU worker pool, and an artifact
  store (local disk, then S3-compatible storage).
- Outputs are glTF 2.0, with the topology id fixed, so the Studio can animate any head the same way.

## Cross-cutting
- Config: pydantic models + YAML presets; every run writes its resolved config.
- Reproducibility: seeds, model hashes and the package version recorded in `QualityReport`.
- Privacy: face photos are biometric data. Job folders get a retention policy, there is no telemetry of
  images, and the Studio needs a consent flag before processing.
- License register: `models/registry.yaml` records the license and the commercial-use flag of each weight.
