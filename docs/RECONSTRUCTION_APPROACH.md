# Reconstructing a 3D Face from One Photograph

## The core problem

One photo is a 2D projection. Depth, the far side of the head, and the true skin
color (separate from lighting) are not observed. The missing information has to
come from a **prior**: a learned model of what human heads look like.
Every design choice below is about using a strong prior while keeping the
person's identity.

## Chosen strategy: a parametric head model with fitting by rendering

We represent the head with **FLAME**, a parametric head model (about 5k vertices,
fixed topology, fixed UV layout):

```
mesh = FLAME(shape β [identity], expression ψ, jaw/neck/eye pose θ)
```

Why a parametric model instead of a generic image-to-3D model (TRELLIS, Hunyuan3D, LGM):

| Need | Parametric model (FLAME) | Generic image-to-3D |
|---|---|---|
| Real, clean 3D geometry | Yes: watertight, fixed topology | Yes, but noisy topology |
| Identity preservation | Good, and measurable | Weak: faces drift toward "average" |
| Fixed UV layout for textures | Yes | No: a new UV per asset |
| Rigging and animation later | Yes: blendshapes, jaw and eyes built in | No |
| Fits a full-body model (SMPL-X) | Yes: SMPL-X shares FLAME's head | No |

Generic models stay an option for hair and accessories (later phases), not the face.

## Pipeline, step by step

```
photo
 │ 1. Preprocess:     detect face → 478 landmarks → align/crop → face parsing mask
 │                    → quality gate (yaw, blur, occlusion, resolution)
 │ 2. Identity prior: identity network (ArcFace features → FLAME β), e.g. MICA
 │ 3. Initial fit:    regressor for expression, pose, camera, lighting (e.g. SMIRK / EMOCA)
 │ 4. Refinement:     differentiable rendering, optimizing β, ψ, θ, camera, SH lighting, albedo
 │                    losses: landmarks + photometric (skin mask) + silhouette
 │                          + identity (ArcFace cosine of render vs photo)
 │                          + regularizer that keeps β close to the step-2 prior
 │ 5. Neutralize:     set ψ = 0 and pose = rest → neutral identity mesh
 │ 6. Detail:         estimate a displacement/normal map for wrinkles and pores (optional, phase 3)
 │ 7. Texture:        project photo → FLAME UV, remove lighting, mirror-fill,
 │                    fill hidden areas from an albedo prior or diffusion inpainting,
 │                    then derive normal and roughness maps
 │ 8. Blender:        build mesh + UVs, skin shader with subsurface scattering, bake, export GLB/FBX/.blend
 ▼
textured, neutral, rig-ready 3D head + quality report
```

### How each step protects identity
- **Step 2** predicts face shape from an identity embedding, so the result is
  robust to the photo's expression and lighting. A plain landmark fit tends to
  confuse expression with shape.
- **Step 4** adds an identity loss: the rendered face must look like the
  same person to a face-recognition network, not only line up with the landmarks.
- **Step 5** separates expression from identity, so a smiling photo still gives a neutral head.
- **Evaluation**: we render the result at several yaw angles and measure
  ArcFace similarity to the input photo. That number is our main identity
  metric and the gate for continuous integration (CI).

### Texture: what is real and what is generated
- The visible skin comes from the photo itself (projected into UV space), so it is
  as faithful as the input.
- Lighting is removed using the spherical-harmonics (SH) lighting estimated in step 4. This is
  approximate; hard shadows and specular highlights need a learned de-lighting step (phase 3).
- Regions the camera could not see (far cheek, under the chin, ears, scalp) are
  filled in this order: the mirrored visible side, then a statistical UV albedo prior,
  then diffusion inpainting in UV space. Each texel records where it came from in a
  **provenance mask** in the output, so the Studio can show which parts were generated.

## Known limits of single-image reconstruction
- **Depth ambiguity**: nose projection and face depth are partly guessed from the prior. A 3/4-view photo helps.
- **Hair, beard and glasses** are not part of FLAME. They are masked out in v1 and
  handled as separate assets later.
- **Back of the head and ears** are inferred, not observed.
- The input should be a well-lit photo, roughly frontal (yaw within ±30°), with the face at least 256 px.
  The quality gate rejects or warns on other photos.
