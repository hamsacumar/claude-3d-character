"""Step 2 (inside Blender 4.5): build the 3D head from landmarks.npz and save head.blend.

  blender -b --factory-startup --python c3d/head_v1/build_blend.py -- --dir OUT [--render] [--use-cycles]

Objects: Head (face, eyelids, mouth, cranium, neck), Ear_R, Ear_L, Eye_R, Eye_L, Reference_Photo,
cameras Cam_Front / Cam_ThreeQuarter / Cam_Side, three area lights.
"""
import json
import math
import sys
from pathlib import Path

import bpy  # noqa: I001  (bpy must be imported before bmesh in the standalone module)
import bmesh
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from c3d.head_v1 import geometry as G  # noqa: E402

CM = 0.01


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    d = Path(argv[argv.index("--dir") + 1]).resolve()
    return d, "--render" in argv, "--use-cycles" in argv


def to_blender(v_cm):
    """canonical (x, y up, z to viewer) cm -> Blender (x, -z, y) metres; the face looks along -Y."""
    v = np.asarray(v_cm, float) * CM
    return np.stack([v[..., 0], -v[..., 2], v[..., 1]], -1)


def make_object(name, verts_cm, faces, face_mats, materials, subsurf=2):
    me = bpy.data.meshes.new(name)
    me.from_pydata(to_blender(verts_cm).tolist(), [], np.asarray(faces).tolist())
    me.update()
    me.validate()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    for m in materials:
        me.materials.append(m)
    if len(face_mats) == len(me.polygons):
        me.polygons.foreach_set("material_index", np.asarray(face_mats, np.int32))
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    if subsurf:
        m = ob.modifiers.new("Subdivision", "SUBSURF")
        m.levels, m.render_levels = 1, subsurf
    return ob


def principled(name, colour, rough=0.5, sss=0.0, coat=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    b = mat.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*colour, 1.0)
    b.inputs["Roughness"].default_value = rough
    for key in ("Subsurface Weight", "Subsurface"):
        if key in b.inputs:
            b.inputs[key].default_value = sss
            break
    if "Subsurface Radius" in b.inputs:
        b.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.2)
    if "Subsurface Scale" in b.inputs:
        b.inputs["Subsurface Scale"].default_value = 0.004
    if coat and "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = coat
    mat.diffuse_color = (*colour, 1.0)
    return mat


def eye_material(iris_lin):
    """Procedural eye: sclera, iris (photo colour) and pupil, around the eyeball's local +Y (gaze) axis."""
    mat = bpy.data.materials.new("Eye")
    mat.use_nodes = True
    nt = mat.node_tree
    N, L = nt.nodes, nt.links
    b = N.get("Principled BSDF")
    tc = N.new("ShaderNodeTexCoord")
    nrm = N.new("ShaderNodeVectorMath"); nrm.operation = "NORMALIZE"
    L.new(tc.outputs["Object"], nrm.inputs[0])
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(nrm.outputs["Vector"], sep.inputs[0])
    ramp = N.new("ShaderNodeValToRGB")
    L.new(sep.outputs["Y"], ramp.inputs["Fac"])
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.80, (0.78, 0.74, 0.70, 1)             # sclera (not pure white)
    els[1].position, els[1].color = 0.86, (*[c * 0.8 for c in iris_lin], 1)   # limbus
    e = els.new(0.90); e.color = (*iris_lin, 1)                                # iris
    e = els.new(0.955); e.color = (*[c * 0.7 for c in iris_lin], 1)
    e = els.new(0.965); e.color = (0.01, 0.01, 0.01, 1)                        # pupil
    L.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.08
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = 1.0
    mat.diffuse_color = (0.8, 0.78, 0.75, 1)
    return mat


def eyeball(name, spec, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=spec["radius"] * CM,
                                         location=Vector(to_blender(spec["centre"]).tolist()))
    ob = bpy.context.active_object
    ob.name = name
    gaze = Vector(to_blender(spec["gaze"]).tolist()).normalized()
    # local +Y must point along the gaze
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = Vector((0, 1, 0)).rotation_difference(gaze)
    ob.data.materials.append(mat)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def reference_plane(photo, height, x_off):
    img = bpy.data.images.load(str(photo))
    w, h = img.size
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(x_off, 0.0, height / 2))
    p = bpy.context.active_object
    p.name = "Reference_Photo"
    p.scale = (height * w / h, height, 1)
    p.rotation_euler = (math.radians(90), 0, 0)
    mat = bpy.data.materials.new("Reference_Photo")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
    e = nt.nodes.new("ShaderNodeEmission")
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(t.outputs["Color"], e.inputs["Color"])
    nt.links.new(e.outputs[0], o.inputs["Surface"])
    p.data.materials.append(mat)
    return p


def rig(target_loc):
    target = bpy.data.objects.new("Head_Target", None)
    bpy.context.collection.objects.link(target)
    target.location = target_loc

    def area(name, loc, energy, size):
        d = bpy.data.lights.new(name, "AREA"); d.energy = energy; d.size = size
        o = bpy.data.objects.new(name, d); bpy.context.collection.objects.link(o)
        o.location = target_loc + Vector(loc)
        c = o.constraints.new("TRACK_TO"); c.target = target; c.track_axis = "TRACK_NEGATIVE_Z"
    area("Key", (0.5, -0.8, 0.35), 55, 0.7)
    area("Fill", (-0.7, -0.6, 0.0), 22, 1.0)
    area("Rim", (0.0, 0.8, 0.45), 40, 0.6)

    cams = {}
    for name, yaw in (("Cam_Front", 0), ("Cam_ThreeQuarter", 35), ("Cam_Side", 90)):
        cd = bpy.data.cameras.new(name); cd.lens = 85
        c = bpy.data.objects.new(name, cd); bpy.context.collection.objects.link(c)
        dist = 1.15
        a = math.radians(yaw)
        # orbit to the person's left (+X) so the side view shows the left profile
        c.location = target_loc + Vector((dist * math.sin(a), -dist * math.cos(a), 0.0))
        k = c.constraints.new("TRACK_TO"); k.target = target; k.track_axis = "TRACK_NEGATIVE_Z"; k.up_axis = "UP_Y"
        cams[name] = c
    bpy.context.scene.camera = cams["Cam_Front"]
    return cams


def main():
    out, do_render, use_cycles = args()
    d = np.load(out / "landmarks.npz")
    V478 = d["V478"]
    canon_V, canon_F = G.load_canonical()
    head, ears, eyes, skull = G.build_head(V478, canon_V, canon_F)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    skin = principled("Skin", tuple(d["skin_lin"]), rough=0.5, sss=0.12)
    mouth = principled("Mouth_Interior", (0.18, 0.04, 0.04), rough=0.6)
    eye_mat = eye_material(tuple(d["iris_lin"]))

    head_ob = make_object("Head", head.verts, head.faces, head.face_mat, [skin, mouth])
    ear_obs = [make_object(e.name, e.verts, e.faces, e.face_mat, [skin]) for e in ears]
    eye_obs = [eyeball(n, s, eye_mat) for n, s in zip(("Eye_R", "Eye_L"), eyes)]

    # stand the head on the ground: lowest neck point at z = 0
    zmin = min(min((o.matrix_world @ v.co).z for v in o.data.vertices) for o in [head_ob] + ear_obs)
    for o in [head_ob] + ear_obs + eye_obs:
        o.location.z -= zmin
    bpy.context.view_layer.update()          # refresh matrix_world after moving the objects
    zmax = max((head_ob.matrix_world @ v.co).z for v in head_ob.data.vertices)
    eye_z = sum((o.matrix_world.translation.z) for o in eye_obs) / 2
    target = Vector((0.0, 0.0, eye_z - 0.02))

    photo = next(out.glob("00_reference.*"), None)
    if photo:
        reference_plane(photo, zmax * 0.75, -0.42)
    rig(target)

    scene = bpy.context.scene
    world = bpy.data.worlds.new("World"); scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.04, 0.04, 0.045, 1)
    scene.render.resolution_x, scene.render.resolution_y = 1000, 1250
    if use_cycles:
        scene.render.engine = "CYCLES"; scene.cycles.samples = 48; scene.cycles.use_denoising = True
    else:
        for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
            try:
                scene.render.engine = eng
                break
            except TypeError:
                pass
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.shading.type = "MATERIAL"

    report = dict(
        objects={o.name: dict(vertices=len(o.data.vertices), faces=len(o.data.polygons))
                 for o in [head_ob] + ear_obs + eye_obs},
        head_height_cm=round(zmax * 100, 1),
        skull=head.info["skull"], ears=[e.info for e in ears],
        eyes=[dict(centre_cm=np.round(e["centre"], 2).tolist(), gaze=np.round(e["gaze"], 3).tolist()) for e in eyes],
        reconstructed_vs_inferred={
            "from_photo_landmarks": ["forehead (lower part)", "cheeks", "jaw line", "chin", "nose",
                                     "eyelid margins and eye openings", "lips and mouth opening",
                                     "expression", "gaze direction", "iris colour", "skin colour"],
            "depth": "MediaPipe's learned per-landmark depth estimate (not measured)",
            "inferred_from_proportions": ["upper forehead and cranium", "back of head", "ears (procedural)",
                                          "eye sockets and eyeballs (average size)", "mouth interior", "neck"],
            "not_modelled": ["hair", "teeth", "eyelashes", "eyebrow hair", "skin texture from the photo"],
        })
    (out / "head_report.json").write_text(json.dumps(report, indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "head.blend"))
    print("Saved", out / "head.blend")

    if do_render:
        ref = bpy.data.objects.get("Reference_Photo")
        if ref:
            ref.hide_render = True
        for name, fname in (("Cam_Front", "01_front"), ("Cam_ThreeQuarter", "02_threequarter"), ("Cam_Side", "03_side")):
            scene.camera = bpy.data.objects[name]
            scene.render.filepath = str(out / f"{fname}.png")
            bpy.ops.render.render(write_still=True)
        if ref:
            ref.hide_render = False
        scene.camera = bpy.data.objects["Cam_Front"]


if __name__ == "__main__":
    main()
