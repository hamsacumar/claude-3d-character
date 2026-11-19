---
name: blender-print-texture
description: Enhance the colour texture of the figure(s) in the currently opened Blender file using reference images, registered orthographic painting views, AI-assisted raster painting and safe projection; bake one 4096x4096 colour image per figure, save it as a PNG and pack it into a separate .blend copy without changing the original file, geometry or UVs. Use when asked to run blender-print-texture or to create print-colour textures for a Blender figure.
---

# blender-print-texture

The section "Original instructions" below is the user's complete original `$blender-print-texture`
document, inserted verbatim (bracketed placeholders are part of the original and are filled in per
request). The section "Supplementary instructions" at the end is NOT part of the original. It records
additional requirements and environment notes and must never override or replace the original.

## Original instructions (verbatim)

<!-- BEGIN ORIGINAL blender-print-texture DOCUMENT (do not edit) -->
Use $blender-print-texture on the figure(s) in my currently opened Blender file.

REFERENCE AND SCOPE

* Use the reference images attached to this request for the current figure(s).
* Main reference for appearance: [identify the reference image].
* Areas to improve: [face, eyes, eyebrows, lips, teeth, hair, moustache/beard, neck, or specified clothing/accessory areas].
* Areas already approved and to preserve: [identify these areas].
* Save the results in a new folder beside the currently opened .blend file, unless I give another location.
* Final output: one 4096 × 4096 colour texture image per figure, packed into a separate .blend copy and also saved as a PNG.

1. INSPECT THE CURRENT FILE FIRST
   * Inspect the actual open Blender scene and establish its saved file path.
   * Identify the intended figure objects, mesh data, transforms, material slots, colour images and UV layers.
   * Check whether images are packed, externally linked, missing or modified without being saved.
   * Establish the latest working state. Do not silently use an older saved file when the open scene contains newer edits.
   * Inspect the UV layout for overlaps, insufficient island spacing, stretched areas and fragments too small to hold useful texture detail at 4K.
   * Distinguish overlapping UVs within one material from UVs that overlap because different materials originally used separate images.
   * Inspect the figure from suitable front, three-quarter, side and back views.
   * Adapt the inspection and painting views to the actual pose, including tilted or upward-looking heads.
2. PROTECT MY ORIGINAL WORK
   * Never overwrite the original .blend or original texture files.
   * Create a protected source backup and a separate working copy.
   * Make copied mesh, material and image datablocks independent so edits cannot affect the original through shared data.
   * Record the original geometry, topology, transforms and UV coordinates for verification.
   * Preserve geometry, topology, pose, proportions, expression, gaze direction, transforms, clothing and accessories.
   * Preserve previously repaired or approved textures.
   * This is a texture enhancement task. Do not sculpt, remesh, move vertices, change thickness or alter the pose.
   * If an apparent texture defect is actually caused by geometry, overlapping surfaces or shading normals, identify that separately. Do not disguise it with inappropriate painted shadows.
3. PRESERVE THE ORIGINAL UV LAYERS
   * Retain all original UV layers unchanged.
   * Reuse an existing UV layout when it can support one colour image without conflicting overlaps.
   * If necessary, create a separate print atlas UV layer and clearly explain why.
   * Never silently repack, replace or modify the original UV layer.
   * Give important facial features enough texture space for readable eyes, lips and hair detail.
   * Adapt the atlas allocation to this figure. The previous successful example used about 57% of atlas height for the head and 41% for the body, with padding; these are examples, not fixed requirements.
   * Do not leave important borders or visible details mapped to fragments smaller than useful texel coverage at 4K.
   * Provide adequate padding and inspect filtering across island borders.
   * If the print atlas needs adjustment, verify the resulting appearance on the model from multiple angles.
4. COMPARE WITH THE CURRENT REFERENCE
   * Use the identity, colours and appearance of this figure’s reference.
   * Do not reuse a previous figure’s identity, paint guide, projection coordinates or colour assumptions.
   * Identify specific differences before painting.
   * Aim for closer reference colouring and a clean, natural appearance.
   * Do not promise exact likeness from texture painting.
   * Do not claim that a 4K image adds geometric detail or that enlarging a low-resolution image creates genuine new detail.
   * Where the reference does not show an area, preserve the model’s existing appearance unless another supplied reference supports a change.
   * Do not invent unseen markings, garment patterns or accessories.
5. PREPARE REGISTERED PAINTING VIEWS
   * Produce flat diffuse/albedo previews using known orthographic cameras.
   * Record each camera’s projection transform, framing and bounds.
   * Use additional views when needed for the actual head pose or requested repair.
   * Keep projection coordinates consistent with the figure’s current transforms.
   * Use these previews as the exact edit targets for AI-assisted raster painting.
   * Read the blender-print-texture painting-and-baking guidance before generating or projecting paint guides.
6. CREATE AND CHECK THE PAINT GUIDE
   * Use the available imagegen skill and built-in image generation/editing tool for AI-assisted painting.
   * Clearly identify which input is the model edit target and which input is the appearance reference.
   * Edit surface colour only.
   * Lock the target camera, framing, silhouette and anatomical feature positions.
   * Preserve eye centres, pupil direction, eyelid edges, eyebrows, nose, lips, smile, teeth placement, hairline and facial-hair boundaries.
   * Preserve the existing expression and head orientation.
   * Do not apply a guide that changes anatomy, shifts facial features or moves garment boundaries.
   * Inspect the generated guide before using it.
   * If it drifts, reject it, correct the alignment or reduce the affected area.
   * Save the actual image-edit prompt set with the project outputs.
7. FACE, EYE AND HAIR COLOUR GOALS
   * Match the reference skin tone with natural warmth and restrained colour variation.
   * Avoid orange skin, excessive pinkness, strong makeup or noisy pore detail that looks dirty at miniature scale.
   * Keep head and neck colours consistent, with restrained blending where necessary.
   * Improve eye readability within the existing eye geometry.
   * Match the reference iris colour, preserve the gaze, add subtle iris variation, dark central pupils and small restrained catchlights.
   * Keep eye whites natural rather than pure bright white.
   * Follow existing eyebrow, hair and facial-hair forms with subtle strand colour variation.
   * Avoid black painted grooves, excessive contrast and shiny highlights that look unnatural when printed.
   * Keep lips naturally coloured with soft shading.
   * If teeth are visible, use natural off-white colouring and preserve their existing positions.
   * Keep mouth corners and spaces around the teeth softly shaded rather than making them look like black holes.
   * Do not invent teeth, eyelashes, freckles or facial hair absent from the reference.
8. CLOTHING AND ACCESSORY PROTECTION
   * Preserve approved clothing and accessory textures by default.
   * Modify clothing or accessories only where I explicitly request cleanup.
   * Protect checks, stripes, dots, embroidery, logos, trim, stitching and other intentional patterns.
   * Remove unwanted colour spill, stains and smudges without erasing intentional pattern details.
   * Keep skin colour off clothing, scarf colour off skin and shirt, and strap colours inside their intended borders.
   * Follow the actual curved surfaces and garment folds.
   * Inspect requested pattern repairs from all relevant sides.
   * Do not make a repair look correct only from the painting camera while introducing visible seams elsewhere.
   * Blend repair boundaries into surrounding approved colours.
   * Avoid broad repainting of good areas when a local correction is sufficient.
9. PROJECT AND BLEND SAFELY
   * Project only registered, inspected guides onto copied materials.
   * Restrict each guide to the intended surface regions.
   * Use appropriate material/region masks, surface visibility checks, angle falloff and projection bounds.
   * Do not project through the head, through clothing or onto hidden or unrelated surfaces.
   * Fade toward side and back regions where appropriate.
   * Preserve existing colours outside the intended repair.
   * Inspect for doubled features, ghosting, stretched paint, hairline halos, abrupt neck transitions, colour bleeding and projection seams.
   * Correct these before proceeding to the final texture.
10. COMBINE INTO ONE PRINT COLOUR IMAGE
   * Prepare one 4096 × 4096 colour image per figure.
   * Bake the composed colour through an emission/unlit colour pass.
   * Use intentional colour management and avoid applying display transforms twice.
   * Do not bake studio lighting, specular reflections, dramatic highlights or new hard shadows into the colour image.
   * Select the correct bake UV layer, destination image and active image node in every contributing material.
   * Cache and restore polygon material indices when changing material slots. Do not allow rebuilding material slots to assign the wrong source texture to faces.
   * Use adequate bake margins without allowing neighbouring islands to contaminate each other.
   * Inspect small islands and thin borders for missing coverage, dark speckles and filtering problems.
   * If temporary supersampling is useful, resolve the result carefully to a final 4096 × 4096 image.
   * Do not leave an 8K intermediate as the final deliverable.
11. AO AND OTHER MAPS
   * AO is optional; do not add it automatically.
   * If requested or clearly useful, bake AO separately and blend it gently into the final colour image.
   * Avoid dirty-looking skin and overly dark eye sockets, nostrils, mouth corners, folds or seams.
   * The final printing workflow must work from the single colour image.
   * Do not rely on separate bump, normal, displacement, roughness or metallic maps for details the colour printer cannot reproduce from those maps.
   * Do not paint strong fake lighting to imitate physical surface detail.
12. BUILD THE FINAL MATERIAL
   * Assign a simple final material that reads the figure’s final colour image through the correct print UV layer.
   * Keep one final colour image per figure.
   * Save the colour PNG and pack it into the copied .blend.
   * Preserve source materials and textures in the original or protected backup.
   * Check that the finished copy does not depend on missing images or temporary processing files.
13. VERIFY BEFORE CLAIMING COMPLETION
   * Compare before-and-after front, three-quarter and side views, plus the back where relevant.
   * Inspect eyes, gaze, eyelids, mouth corners, teeth, eyebrows, hairline, facial hair and neck transitions.
   * Inspect every specifically requested clothing or accessory repair.
   * Check for unintended changes to approved body and clothing colours.
   * Check for UV conflicts, missing texel coverage, colour bleeding, black speckles, stretched patterns and new visible seams.
   * Verify the final image is exactly 4096 × 4096.
   * Verify one final colour image per figure and that it is packed.
   * Verify geometry, topology, transforms and original UV coordinates remain unchanged.
   * If shading normals were intentionally adjusted, report that separately.
   * Save comparable before-and-after previews.
   * Do not call the task complete while a required bake, save or visual check is still pending.
14. SAVE, OPEN AND REPORT
   * Save the separate final .blend and final PNG in the requested output folder.
   * Keep file names clear enough to identify the final deliverables.
   * Avoid unnecessary duplicate .blend files and large unused bake intermediates.
   * Remove only temporary files created during this task when they are no longer needed; do not delete my source files or unrelated work.
   * Open the finished copy in Blender when possible.
   * Verify that Blender actually loaded the final saved version before saying it is open.
   * If it could not be opened or refreshed, explain that accurately.
   * Report the actual changes, validation results, final .blend and PNG paths, any print UV changes and remaining limitations.
   * Distinguish an AI-generated paint guide from the finished texture and from the file actually loaded in Blender.
   * Be honest about remaining defects; do not describe an unresolved result as seamless or exact.
   * Keep me informed with brief progress updates during long processing or bakes.

Proceed with the authorized texture work on the copy. Ask only when a genuinely missing decision prevents safe, useful progress.
<!-- END ORIGINAL blender-print-texture DOCUMENT -->

---

## Supplementary instructions (NOT part of the original document)

These were added separately. They supplement the original and never override it. Where they
conflict with the original, follow the original and report the conflict to the user.

### A. Requirements the user stated in conversation
- Use the user's installed Blender 4.5.14 (`/usr/local/bin/blender` on Ubuntu 22.04).
- Do not use paid services, require API keys, install large packages or download model weights
  without the user's explicit approval.
- Check the licence of every model, checkpoint, dependency and image-generation model individually;
  the output is intended for a commercial AI 3D Studio.
- Save the final `.blend` and texture PNG separately; never overwrite original projects or textures.
- Verify the final model from front, three-quarter, side and back views.

### B. Environment notes for running this skill in Claude Code (added by Claude)
- **Geometry:** this skill only enhances textures and must not change geometry (original §2). In this
  repository the figure itself comes from the separate Stage 1 FLAME 2023 Open reconstruction
  (`docs/IMPLEMENTATION_PLAN_V1.md`).
- **Original §5 "painting-and-baking guidance":** the original refers to a companion guidance document
  that has not been supplied. If it exists, it must be added beside this file (e.g.
  `references/painting-and-baking.md`) and read before §5–§6. If it is not available, tell the user
  rather than inventing its content.
- **Original §6 "imagegen skill and built-in image generation/editing tool":** these are Codex tools.
  Claude Code has no built-in image generation. Map this step to an approved local image-editing
  pipeline (planned: SDXL inpainting via diffusers; see `docs/IMPLEMENTATION_PLAN_V1.md`). Until that is
  approved and installed, stop before §6 and ask the user. Claude can still inspect and accept or
  reject a generated guide visually (original §6 "Inspect the generated guide before using it").
- **Original §1 / §14 "currently opened Blender file" / "Open the finished copy":** Claude can only
  reach the open Blender session when it runs on the user's machine with a live Blender connection
  (e.g. Blender MCP) or when the user saves the file and provides its path for headless
  `blender -b` processing. A cloud session cannot see or open the user's Blender; say so accurately
  (original §14).
