---
name: blender-print-texture
description: Enhance the colour texture of an existing Blender character using a reference photograph, AI-assisted image editing and registered texture projection; bake a 4096x4096 colour atlas and save it with a separate packed .blend, without modifying the original model. Use when asked to run blender-print-texture or to create print-quality textures for a Blender model.
---

# blender-print-texture

> **STATUS: INCOMPLETE. The original instructions have not been pasted in yet.**
> The user's original `$blender-print-texture` document has not been provided to Claude in this
> repository or conversation. It belongs, **verbatim and complete**, in the section
> "Original instructions" below.
>
> **If you are Claude and the section below still contains only the placeholder: STOP. Do not run
> this workflow from the summary. Ask the user for the original document.**

## Original instructions (verbatim, unedited)

<!-- PASTE THE COMPLETE ORIGINAL blender-print-texture INSTRUCTIONS HERE, UNCHANGED. -->
_(not yet provided)_

---

## Requirements the user stated in conversation (not a substitute for the original)

These are the requirements the user gave when asking for this workflow. They supplement the
original instructions and must not replace them.

- Inspect the current Blender scene: meshes, materials and UV maps.
- Use the supplied photograph as the appearance reference.
- Generate detailed, natural-looking facial (and body) textures; improve skin, eyes, eyebrows,
  lips, hair and other relevant details.
- Use AI-assisted image editing and registered texture projection where appropriate.
- Produce a 4096 x 4096 colour texture atlas.
- Bake the result and pack the texture into a **separate** Blender project.
- Preserve the original model and its geometry. Never overwrite original projects or textures.
- Save the final `.blend` and the texture PNG separately.
- Verify from front, three-quarter, side and back views.
- Use the installed Blender 4.5.14. Do not use paid services or download large models without approval.

## How this repository connects to the skill (added by Claude, not part of the original)

- This skill does **not** create geometry. The geometry comes from the Stage 1 FLAME 2023 Open
  fitter in this repo (see `docs/IMPLEMENTATION_PLAN_V1.md`).
- Claude Code has no built-in image generation. Wherever the original instructions call for AI
  image generation or editing, use the approved local model pipeline in this repo; until that
  exists, ask the user.
