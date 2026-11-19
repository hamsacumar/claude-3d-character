# Proposal: Photo to 3D Character to Print-Quality Texture

Status: **waiting for approval**. Nothing has been installed or downloaded.

## 0. What was found in this session

| Item | Status |
|---|---|
| `$blender-print-texture` | **Not found.** It is not in this repo, `~/.claude/skills`, `~/.claude/commands`, the user's claude.ai skills, the org plugin catalog, or public GitHub/web. The `$name` syntax is Codex's skill syntax, so it most likely lives in `~/.codex/skills/` (or a repo's `.agents/skills/`) on the machine where Jayashanka ran it. |
| Blender integration (MCP) | None installed. |
| Image generation in Claude | **None built in.** Codex has a built-in image generation tool; Claude Code does not. The "AI image editing" step needs an external image model (local or API). |
| Access to the Ubuntu machine | None. This is a cloud session, and no computer folder is shared with it. |

Agent Skills use the same `SKILL.md` format in Codex and Claude Code. Once the skill is placed at
`.claude/skills/blender-print-texture/SKILL.md` (with any scripts it references), Claude Code can run it as
`/blender-print-texture`. Its tool calls (image generation, Blender access) must then be mapped to
tools Claude actually has; see §3.

## 1. What creates the 3D geometry (Stage 1)

A texture skill does not create geometry. Stage 1 is a separate reconstruction step:

| Option | Ears, skull, eyes, neck | Hair | Identity | 4 GB VRAM | Commercial licence |
|---|---|---|---|---|---|
| **A. FLAME 2023 Open + our own photo fitting** (recommended) | Yes: a full statistical head with eyeballs and neck | Separate step (below) | Good. Dense 478-landmark fit plus fitting to the photo's pixels | Yes, ~1–2 GB | **FLAME 2023 Open is CC-BY-4.0** (commercial OK, attribution, no pornographic use). Earlier FLAME versions and MICA/SMIRK/DECA weights are non-commercial, so we write our own fitter |
| B. MICA + SMIRK regressors on FLAME | Yes | No | Very good | Yes | **Non-commercial** (research comparison only) |
| C. Hyper3D Rodin via Blender MCP | Yes (one mesh) | Yes (baked into the mesh) | Medium–good | Cloud | Paid; check the output terms. Probably the closest to an "AI makes the whole head" demo |
| D. Hunyuan3D-2 / TRELLIS (local image-to-3D) | Yes | Yes | Weak on faces | No (6–16 GB) | Tencent community licence / MIT |

**Plan A in detail:**
1. Analyze the photo:
   - MediaPipe 478 landmarks plus the multiclass selfie segmentation model, which separates hair, face skin, body skin and clothes (Apache-2.0, CPU).
   - Head pose and expression scores.
2. Fit FLAME to the photo by optimizing shape, expression, pose, camera, lighting and albedo with a differentiable renderer (PyTorch3D, BSD licence). The losses are:
   - the dense landmarks;
   - silhouette and segmentation masks;
   - photometric match on skin pixels;
   - regularizers that keep the head human-plausible.
3. Neutralize the expression, then subdivide (FLAME has ~5k vertices, so we go to ~80k for the render mesh).
4. Assemble the character in Blender:
   - FLAME head with eyeballs (iris and sclera materials), and teeth/tongue from CC0 MakeHuman/MPFB assets.
   - A neck-and-shoulder bust.
   - **Hair:** Blender hair curves. Their silhouette, colour and length come from the photo's hair mask and are shaped by a scalp cap on the fitted skull. A CC0 MPFB hair-card mesh is the fallback.
5. Check views: front, three-quarter, side and back renders, plus a landmark-reprojection error report.

## 2. Texture enhancement (Stage 2: the role of `blender-print-texture`)

Until I can read the skill this section is **my inference**, built from your description. I'll align it with the skill's real steps once I have the file.

1. **Inspect** the scene: meshes, materials, UV maps, existing images. Never modify the original. Work on a copy: `*_print_texture.blend`.
2. **Registered projection:** the Stage 1 fit gives the exact camera that lines the mesh up with the photo, so the photo can be projected onto the mesh's UV layout pixel-accurately. Each texel is weighted by visibility and viewing angle.
3. **AI-assisted image editing**, always on images that stay registered:
   - (a) Clean the photo: remove shadows and lighting, skin detail, sharper eyes, brows and lips.
   - (b) Render the model from side, back and top using the current texture, then refine each render with image-to-image or inpainting at low strength. The geometry stays put, so each render can be projected back from its known camera.
   - (c) Upscale (Real-ESRGAN, BSD) for 4K detail.
4. **Bake** all projections into one **4096 × 4096** colour atlas on the model's UVs, blending the seams. Also bake roughness and normal maps.
5. **Package:** save `character_albedo_4096.png` and a separate `character_print_texture.blend` with the texture packed. The original `.blend` and textures stay untouched.
6. **Verify:** front, three-quarter, side and back renders, compared with the photo.

### Which image AI (Claude cannot generate images itself)

| Option | Quality | Runs on | Licence / cost |
|---|---|---|---|
| **SDXL inpainting + img2img (diffusers, CPU offload)** | Good | 4 GB GPU, slow (~1–3 min per image), ~7 GB download | CreativeML Open RAIL++-M: commercial use allowed, with use restrictions |
| SD 1.5 inpainting | Fair | 4 GB GPU, fast, ~2 GB download | Open RAIL-M: commercial use allowed |
| Gemini 2.5 Flash Image / OpenAI gpt-image (API) | Very good at identity-preserving edits | Cloud | Paid; the photo leaves your machine |
| FLUX.1-dev / Kontext-dev | Very good | Too heavy for 4 GB | **Non-commercial** licence |

## 3. Can it all run through Claude + Blender on Ubuntu?

Yes, but **Claude has to run on the Ubuntu machine**. This cloud session cannot reach your Blender. Options:
- **Claude Code CLI on Ubuntu** in this repo folder. Optionally start it with `claude remote-control` so the session shows up in the Claude app.
- Blender control, either way:
  - (i) **headless scripts** (`blender -b --python …`): reproducible, and what the pipeline uses; or
  - (ii) **Blender MCP** (`ahujasid/blender-mcp`, MIT) for live, interactive inspection and edits. Its optional Rodin/Hunyuan generators are paid APIs.
- The image AI runs locally (SDXL or SD1.5) or via an API key.

## 4. Approvals needed before anything is installed

1. **The `blender-print-texture` skill files** (commit them to `.claude/skills/blender-print-texture/` or paste them).
2. **FLAME 2023 Open:** you register at flame.is.tue.mpg.de and download it (small; registration is personal).
3. **PyTorch (CUDA 12) + PyTorch3D:** ~3 GB of packages.
4. **Image model choice:** SDXL inpaint (~7 GB), SD1.5 inpaint (~2 GB), or a paid API.
5. **Real-ESRGAN x4 weights** (~65 MB), MediaPipe segmentation model (~16 MB), CC0 MPFB eyes/teeth/hair assets (~50–150 MB).
6. Optional: a Hyper3D Rodin trial or paid key, for a side-by-side comparison with option C.

## 5. Delivery order once approved

1. Stage 1-A: FLAME fit, then a bust with eyes and hair, as `character.blend`. Four-view verification.
2. Stage 2: the `blender-print-texture` steps on a copy, producing `character_print_texture.blend` + `character_albedo_4096.png`. Four-view verification.
3. Write a licence register for every model and asset used (`docs/LICENSES.md`).

The v0 MediaPipe prototype is kept only as a baseline for comparison. It is not developed further.
