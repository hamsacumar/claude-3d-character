"""Stage 2: build the Blender project from reconstruct.py's output.

Runs INSIDE Blender (tested with the Blender 4.5 and 5.x Python APIs):

    blender -b --factory-startup --python c3d/blender_build.py -- --job OUT/job.json [--render]

Creates OUT/head.blend containing:
  * "Head": the reconstructed head mesh, with UVs, a subdivision surface modifier and a skin shader
    (photo texture, subsurface scattering, bump detail from the photo)
  * "Reference_Photo": the source photo on a plane next to the head, for comparison
  * a 3-point light rig, a portrait camera and a 240-frame turntable orbit
With --render it also writes OUT/preview_front.png and OUT/preview_threequarter.png.
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    job = Path(argv[argv.index("--job") + 1]).resolve()
    return job, "--render" in argv, ("--cycles" in argv or "--render" in argv)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def set_input(node, names, value):
    """Set the first matching input socket (socket names differ across Blender versions)."""
    for n in names if isinstance(names, (list, tuple)) else [names]:
        if n in node.inputs:
            node.inputs[n].default_value = value
            return True
    return False


def build_mesh(job_dir: Path, job: dict):
    data = np.load(job_dir / job["mesh"])
    V, F, UV = data["vertices"], data["faces"], data["uv"]
    # canonical frame (x right, y up, z to viewer) -> Blender (x right, z up, face looks along -Y)
    Vb = np.stack([V[:, 0], -V[:, 2], V[:, 1]], 1)
    mesh = bpy.data.meshes.new("HeadMesh")
    mesh.from_pydata(Vb.tolist(), [], F.tolist())
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="PhotoUV")
    loop_vi = np.empty(len(mesh.loops), np.int64)
    mesh.loops.foreach_get("vertex_index", loop_vi)
    uv_layer.data.foreach_set("uv", UV[loop_vi].astype(np.float32).ravel())
    for name in ("shell", "hair"):
        attr = mesh.attributes.new(name=name, type="FLOAT", domain="POINT")
        attr.data.foreach_set("value", data[name].astype(np.float32))
    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    mesh.validate()

    obj = bpy.data.objects.new("Head", mesh)
    bpy.context.collection.objects.link(obj)
    # put the bottom of the neck at z=0
    zmin = Vb[:, 2].min()
    obj.location = (0.0, 0.0, -zmin)
    sub = obj.modifiers.new("Smooth", "SUBSURF")
    sub.levels = 2
    sub.render_levels = 3
    return obj, float(Vb[:, 2].max() - zmin)


def skin_material(job_dir: Path, job: dict):
    mat = bpy.data.materials.new("Skin_PhotoProjected")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    N, L = nt.nodes, nt.links

    out = N.new("ShaderNodeOutputMaterial"); out.location = (900, 0)
    bsdf = N.new("ShaderNodeBsdfPrincipled"); bsdf.location = (600, 0)
    L.new(bsdf.outputs[0], out.inputs["Surface"])

    uv = N.new("ShaderNodeUVMap"); uv.uv_map = "PhotoUV"; uv.location = (-900, 200)
    tex = N.new("ShaderNodeTexImage"); tex.location = (-700, 200)
    tex.image = bpy.data.images.load(str(job_dir / job["texture"]))
    tex.extension = "EXTEND"
    L.new(uv.outputs["UV"], tex.inputs["Vector"])

    def attr_node(name, y):
        a = N.new("ShaderNodeAttribute"); a.attribute_type = "GEOMETRY"
        a.attribute_name = name; a.location = (-700, y)
        return a
    shell, hair = attr_node("shell", -100), attr_node("hair", -300)

    def rgb_node(col, y, label):
        n = N.new("ShaderNodeRGB"); n.label = label; n.location = (-500, y)
        n.outputs[0].default_value = (*col, 1.0)
        return n
    skin_rgb = rgb_node(job["skin_color_linear"], -450, "Skin colour (from photo)")
    hair_rgb = rgb_node(job["hair_color_linear"], -650, "Hair colour (from photo)")

    def mix(a, b, fac, x):
        m = N.new("ShaderNodeMix"); m.data_type = "RGBA"; m.location = (x, 0)
        L.new(fac, m.inputs["Factor"]); L.new(a, m.inputs[6]); L.new(b, m.inputs[7])
        return m.outputs[2]
    col = mix(tex.outputs["Color"], skin_rgb.outputs[0], shell.outputs["Fac"], -250)
    # simple strand-like variation for the inferred hair region
    wave = N.new("ShaderNodeTexWave"); wave.location = (-500, -850)
    wave.wave_type = "BANDS"; wave.bands_direction = "Z"
    wave.inputs["Scale"].default_value = 60.0
    wave.inputs["Distortion"].default_value = 6.0
    wave.inputs["Detail"].default_value = 4.0
    hair_var = N.new("ShaderNodeMix"); hair_var.data_type = "RGBA"; hair_var.location = (-250, -650)
    hair_var.blend_type = "MULTIPLY"
    L.new(wave.outputs["Fac"], hair_var.inputs["Factor"])
    hair_var.inputs["Factor"].default_value = 0.35
    L.new(hair_rgb.outputs[0], hair_var.inputs[6])
    hair_var.inputs[7].default_value = (0.55, 0.55, 0.55, 1.0)
    col = mix(col, hair_var.outputs[2], hair.outputs["Fac"], 0)
    L.new(col, bsdf.inputs["Base Color"])

    # roughness: skin 0.45, hair 0.7
    rough = N.new("ShaderNodeMapRange"); rough.location = (250, -300)
    L.new(hair.outputs["Fac"], rough.inputs["Value"])
    rough.inputs["To Min"].default_value = 0.45
    rough.inputs["To Max"].default_value = 0.7
    L.new(rough.outputs["Result"], bsdf.inputs["Roughness"])

    # skin subsurface scattering
    set_input(bsdf, ["Subsurface Weight", "Subsurface"], 0.12)
    set_input(bsdf, "Subsurface Radius", (1.0, 0.35, 0.2))
    set_input(bsdf, "Subsurface Scale", 0.004)
    set_input(bsdf, ["Specular IOR Level", "Specular"], 0.4)

    # fine detail: bump from the photo's luminance, only on the photo-textured face
    bw = N.new("ShaderNodeRGBToBW"); bw.location = (-250, 350)
    L.new(tex.outputs["Color"], bw.inputs[0])
    inv = N.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.location = (0, 500)
    inv.inputs[0].default_value = 1.0
    L.new(shell.outputs["Fac"], inv.inputs[1])
    strength = N.new("ShaderNodeMath"); strength.operation = "MULTIPLY"; strength.location = (200, 500)
    L.new(inv.outputs[0], strength.inputs[0]); strength.inputs[1].default_value = 0.25
    bump = N.new("ShaderNodeBump"); bump.location = (350, 300)
    bump.inputs["Distance"].default_value = 0.0004
    L.new(strength.outputs[0], bump.inputs["Strength"])
    L.new(bw.outputs[0], bump.inputs["Height"])
    L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def reference_plane(photo: Path, head_height: float):
    if not photo.exists():
        return
    img = bpy.data.images.load(str(photo))
    w, h = img.size
    ph = head_height * 1.1
    pw = ph * w / h
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(-(pw / 2 + 0.25), 0.05, ph / 2))
    plane = bpy.context.active_object
    plane.name = "Reference_Photo"
    plane.scale = (pw, ph, 1)
    plane.rotation_euler = (math.radians(90), 0, 0)
    mat = bpy.data.materials.new("Reference_Photo")
    mat.use_nodes = True
    nt = mat.node_tree; nt.nodes.clear()
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
    e = nt.nodes.new("ShaderNodeEmission")
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(t.outputs["Color"], e.inputs["Color"])
    nt.links.new(e.outputs[0], o.inputs["Surface"])
    plane.data.materials.append(mat)


def lights_and_camera(head_center: Vector, head_height: float):
    def area(name, loc, energy, size, color=(1, 1, 1)):
        d = bpy.data.lights.new(name, "AREA"); d.energy = energy; d.size = size; d.color = color
        o = bpy.data.objects.new(name, d); bpy.context.collection.objects.link(o)
        o.location = head_center + Vector(loc)
        con = o.constraints.new("TRACK_TO"); con.target = target; con.track_axis = "TRACK_NEGATIVE_Z"
        return o

    target = bpy.data.objects.new("Head_Target", None)
    bpy.context.collection.objects.link(target)
    target.location = head_center
    area("Key", (0.55, -0.75, 0.35), 60, 0.6, (1.0, 0.96, 0.9))
    area("Fill", (-0.7, -0.6, 0.05), 20, 0.9, (0.9, 0.95, 1.0))
    area("Rim", (0.0, 0.8, 0.5), 45, 0.5)

    # turntable: the camera orbits around an empty at head height
    pivot = bpy.data.objects.new("Turntable", None)
    bpy.context.collection.objects.link(pivot)
    pivot.location = head_center
    cam_d = bpy.data.cameras.new("Camera"); cam_d.lens = 85
    cam = bpy.data.objects.new("Camera", cam_d)
    bpy.context.collection.objects.link(cam)
    cam.parent = pivot
    dist = head_height * 4.6
    cam.location = (0, -dist, 0.02)
    con = cam.constraints.new("TRACK_TO"); con.target = target; con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    scene = bpy.context.scene
    scene.camera = cam
    scene.frame_start, scene.frame_end = 1, 240
    pivot.rotation_euler = (0, 0, 0)
    pivot.keyframe_insert("rotation_euler", index=2, frame=1)
    pivot.rotation_euler = (0, 0, math.radians(360))
    pivot.keyframe_insert("rotation_euler", index=2, frame=241)
    act = pivot.animation_data.action
    fcurves = getattr(act, "fcurves", None)
    if fcurves is None:  # Blender 5 layered actions
        fcurves = [fc for layer in act.layers for strip in layer.strips
                   for bag in strip.channelbags for fc in bag.fcurves]
    for fc in fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    return pivot


def setup_world_and_render(use_cycles: bool):
    scene = bpy.context.scene
    world = bpy.data.worlds.new("World"); scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.03, 0.03, 0.035, 1)
    bg.inputs["Strength"].default_value = 1.0
    scene.render.resolution_x, scene.render.resolution_y = 1080, 1350
    scene.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in
        scene.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
    if use_cycles:
        scene.render.engine = "CYCLES"
        scene.cycles.samples = 64
        scene.cycles.use_denoising = True
    else:
        for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
            try:
                scene.render.engine = eng
                break
            except TypeError:
                continue


def viewport_material_preview():
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                for space in area.spaces:
                    if space.type == "VIEW_3D":
                        space.shading.type = "MATERIAL"


def main():
    job_path, do_render, use_cycles = parse_args()
    job_dir = job_path.parent
    job = json.loads(job_path.read_text())

    clear_scene()
    head, head_height = build_mesh(job_dir, job)
    head.data.materials.append(skin_material(job_dir, job))
    zmax = head_height  # neck bottom sits at z=0, so the crown is at z=head_height
    head_center = Vector((0, 0, zmax - 0.13))  # around eye level, roughly 13 cm below the crown
    reference_plane(Path(job["photo"]), zmax)
    lights_and_camera(head_center, 0.26)
    setup_world_and_render(use_cycles)
    viewport_material_preview()

    blend = job_dir / job["blend"]
    try:
        bpy.ops.file.pack_all()  # embed photo + texture so the .blend is self-contained
    except RuntimeError as exc:
        print("WARNING: could not pack images:", exc)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    print(f"Saved {blend}")

    if do_render:
        scene = bpy.context.scene
        scene.render.resolution_percentage = 50
        scene.cycles.samples = 32
        pivot = bpy.data.objects["Turntable"]
        ref = bpy.data.objects.get("Reference_Photo")
        if ref:
            ref.hide_render = True
        for name, frame in (("front", 1), ("threequarter", 21), ("profile", 61)):
            scene.frame_set(frame)
            scene.render.filepath = str(job_dir / f"preview_{name}.png")
            bpy.ops.render.render(write_still=True)
        if ref:
            ref.hide_render = False
        scene.frame_set(1)


if __name__ == "__main__":
    main()
