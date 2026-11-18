#!/usr/bin/env python3
"""Photo -> 3D head (stage 1 of the experiment).

Runs in a normal Python venv (NOT inside Blender). Steps:

1. Analyze the photo: detect the face with MediaPipe Face Landmarker and get
   478 dense 3D landmarks, head pose and 52 expression blendshapes.
   Then run quality checks.
2. Reconstruct the face surface: the person's own 468 landmarks, connected with
   MediaPipe's canonical face topology (898 triangles), aligned into a frontal metric frame.
3. Complete the head: add a back of head, top of head and neck behind the face rim, sized from
   the person's face measurements. This part is INFERRED, not observed; the
   report marks it as inferred.
4. Texture: the visible face takes its colour straight from the photo (UVs = projected
   landmark positions). The inferred skin and hair regions use colours sampled
   from the photo.

Output (in --out): head_mesh.npz, face_texture.png, job.json, analysis.json,
landmarks_overlay.png.  Then `blender_build.py` turns this into a .blend file.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
CANONICAL_OBJ = HERE / "data" / "canonical_face_model.obj"
DEFAULT_MODEL = HERE.parent / "models" / "face_landmarker.task"

# MediaPipe landmark ids used below
LM_FOREHEAD_TOP = 10
LM_CHIN = 152
LM_FACE_LEFT_EDGE = 234   # image-left cheek edge near the ear
LM_FACE_RIGHT_EDGE = 454
LM_EYE_OUTER = (33, 263)
LM_FOREHEAD_SIDES = (109, 338)

HEAD_RINGS = 28
NECK_SEGMENTS = 32


# --------------------------------------------------------------------------- utils
def load_canonical():
    verts, faces = [], []
    with open(CANONICAL_OBJ) as fh:
        for line in fh:
            if line.startswith("v "):
                verts.append([float(x) for x in line.split()[1:4]])
            elif line.startswith("f "):
                faces.append([int(t.split("/")[0]) - 1 for t in line.split()[1:]])
    return np.asarray(verts, np.float64), np.asarray(faces, np.int64)


def boundary_loop(faces: np.ndarray) -> list[int]:
    """Return the ordered outer boundary (rim) loop of the face mesh."""
    count: dict[tuple[int, int], int] = {}
    for f in faces:
        for i in range(3):
            e = tuple(sorted((int(f[i]), int(f[(i + 1) % 3]))))
            count[e] = count.get(e, 0) + 1
    adj: dict[int, list[int]] = {}
    for (a, b), c in count.items():
        if c == 1:
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
    start = min(adj)
    loop, prev, cur = [start], -1, start
    while True:
        nxt = [n for n in adj[cur] if n != prev]
        nxt = nxt[0] if nxt else start
        if nxt == start:
            break
        loop.append(nxt)
        prev, cur = cur, nxt
    return loop


def umeyama(src: np.ndarray, dst: np.ndarray):
    """Similarity transform (s, R, t) minimising |s R src + t - dst|."""
    mu_s, mu_d = src.mean(0), dst.mean(0)
    xs, xd = src - mu_s, dst - mu_d
    cov = xd.T @ xs / len(src)
    U, S, Vt = np.linalg.svd(cov)
    D = np.eye(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        D[2, 2] = -1
    R = U @ D @ Vt
    var_s = (xs ** 2).sum() / len(src)
    s = np.trace(np.diag(S) @ D) / var_s
    t = mu_d - s * R @ mu_s
    return s, R, t


def euler_from_R(R: np.ndarray):
    """yaw (left/right turn), pitch (nod), roll (tilt) in degrees."""
    yaw = math.degrees(math.asin(max(-1.0, min(1.0, -R[2, 0]))))
    pitch = math.degrees(math.atan2(R[2, 1], R[2, 2]))
    roll = math.degrees(math.atan2(R[1, 0], R[0, 0]))
    return yaw, pitch, roll


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def median_color(img_rgb: np.ndarray, pts_px: np.ndarray, radius: int = 3):
    h, w = img_rgb.shape[:2]
    samples = []
    for x, y in pts_px.astype(int):
        x0, x1 = max(0, x - radius), min(w, x + radius + 1)
        y0, y1 = max(0, y - radius), min(h, y + radius + 1)
        if x1 > x0 and y1 > y0:
            samples.append(img_rgb[y0:y1, x0:x1].reshape(-1, 3))
    if not samples:
        return None
    return np.median(np.concatenate(samples), axis=0) / 255.0


def delta_e(a, b) -> float:
    """CIE76 colour difference of two sRGB colours in [0, 1]."""
    lab = cv2.cvtColor(np.array([[a, b]], np.float32), cv2.COLOR_RGB2LAB)[0]
    return float(np.linalg.norm(lab[0] - lab[1]))


def srgb_to_linear(c):
    c = np.asarray(c, np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


# --------------------------------------------------------------------------- analysis
def detect(image_rgb: np.ndarray, model_path: Path):
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    opts = vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.IMAGE,
        num_faces=2,
        output_face_blendshapes=True,
        output_facial_transformation_matrixes=True,
    )
    with vision.FaceLandmarker.create_from_options(opts) as lm:
        res = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(image_rgb)))
    if not res.face_landmarks:
        raise SystemExit("ERROR: no face detected in the photo.")
    h, w = image_rgb.shape[:2]
    # choose the largest face
    def area(lms):
        xs = [p.x for p in lms]; ys = [p.y for p in lms]
        return (max(xs) - min(xs)) * (max(ys) - min(ys))
    idx = max(range(len(res.face_landmarks)), key=lambda i: area(res.face_landmarks[i]))
    lms = res.face_landmarks[idx]
    pts = np.array([[p.x * w, p.y * h, p.z * w] for p in lms], np.float64)
    blend = {}
    if res.face_blendshapes:
        blend = {c.category_name: round(float(c.score), 3) for c in res.face_blendshapes[idx]}
    return pts, blend, len(res.face_landmarks)


# --------------------------------------------------------------------------- geometry
def build_head(face_v: np.ndarray, face_f: np.ndarray, rim: list[int]):
    """Close the head behind the reconstructed face (canonical frame, cm;
    x right, y up, z towards viewer). Returns verts, faces, shell weight,
    hair weight, extra info."""
    left, right = face_v[LM_FACE_LEFT_EDGE], face_v[LM_FACE_RIGHT_EDGE]
    eye_y = face_v[list(LM_EYE_OUTER), 1].mean()
    half_w = 0.5 * np.linalg.norm(right - left) * 1.06            # half head breadth
    center = np.array([(left[0] + right[0]) / 2, eye_y + 0.15 * half_w,
                       (left[2] + right[2]) / 2 - 0.12 * half_w])
    # asymmetric ellipsoid semi-axes (typical adult proportions, scaled by the face)
    ax = half_w
    ay_up, ay_dn = 1.42 * half_w, 1.15 * half_w
    az_back = 1.38 * half_w

    def ell_radius(d):
        ay = np.where(d[..., 1] >= 0, ay_up, ay_dn)
        az = np.where(d[..., 2] >= 0, 1.3 * half_w, az_back)
        return 1.0 / np.sqrt((d[..., 0] / ax) ** 2 + (d[..., 1] / ay) ** 2 + (d[..., 2] / az) ** 2)

    back = np.array([0.0, 0.0, -1.0])
    rim_p = face_v[rim]
    d0 = rim_p - center
    r0 = np.linalg.norm(d0, axis=1)
    d0 = d0 / r0[:, None]
    omega = np.arccos(np.clip(d0 @ back, -1, 1))

    verts = [face_v]
    n_face = len(face_v)
    ring_ids = [np.array(rim)]
    nxt = n_face
    for k in range(1, HEAD_RINGS):
        t = k / HEAD_RINGS
        so = np.sin(omega)
        a = np.sin((1 - t) * omega) / so
        b = np.sin(t * omega) / so
        d = a[:, None] * d0 + b[:, None] * back
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        w = smoothstep(0.0, 0.4, t)
        r = (1 - w) * r0 + w * ell_radius(d)
        verts.append(center + d * r[:, None])
        ring_ids.append(np.arange(nxt, nxt + len(rim)))
        nxt += len(rim)
    pole = center + back * az_back
    verts.append(pole[None])
    pole_id = nxt
    nxt += 1

    faces = [face_f]
    n = len(rim)
    shell_faces = []
    for k in range(len(ring_ids) - 1):
        r_a, r_b = ring_ids[k], ring_ids[k + 1]
        for i in range(n):
            j = (i + 1) % n
            shell_faces += [[r_a[i], r_a[j], r_b[j]], [r_a[i], r_b[j], r_b[i]]]
    last = ring_ids[-1]
    for i in range(n):
        shell_faces.append([last[i], last[(i + 1) % n], pole_id])
    shell_faces = np.array(shell_faces)

    V = np.concatenate(verts)
    # orient shell faces outward (away from head centre)
    tri = V[shell_faces]
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    out = (nrm * (tri.mean(1) - center)).sum(1)
    if (out < 0).mean() > 0.5:
        shell_faces = shell_faces[:, ::-1]
    # orient the face mesh towards +z (towards the viewer)
    tri = V[face_f]
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    if nrm[:, 2].mean() < 0:
        faces[0] = face_f[:, ::-1]
    faces.append(shell_faces)

    # --- neck (inferred): open cylinder whose top is hidden inside the head
    neck_r = 0.68 * half_w
    neck_c = np.array([center[0], 0.0, center[2] - 0.25 * half_w])
    y_top = center[1] - 0.35 * half_w
    y_bot = face_v[LM_CHIN, 1] - 0.9 * half_w
    ang = np.linspace(0, 2 * np.pi, NECK_SEGMENTS, endpoint=False)
    rings = []
    for y in np.linspace(y_top, y_bot, 6):
        rings.append(np.stack([neck_c[0] + neck_r * np.cos(ang), np.full_like(ang, y),
                               neck_c[2] + neck_r * 0.9 * np.sin(ang)], 1))
    neck_v = np.concatenate(rings)
    neck_f = []
    for k in range(len(rings) - 1):
        for i in range(NECK_SEGMENTS):
            j = (i + 1) % NECK_SEGMENTS
            a0, a1 = nxt + k * NECK_SEGMENTS + i, nxt + k * NECK_SEGMENTS + j
            b0, b1 = a0 + NECK_SEGMENTS, a1 + NECK_SEGMENTS
            neck_f += [[a0, b1, a1], [a0, b0, b1]]
    neck_f = np.array(neck_f)
    tri = neck_v[neck_f - nxt]
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    radial = tri.mean(1) - neck_c * np.array([1, 0, 1])
    radial[:, 1] = 0
    if ((nrm * radial).sum(1) < 0).mean() > 0.5:
        neck_f = neck_f[:, ::-1]
    V = np.concatenate([V, neck_v])
    faces.append(neck_f)
    F = np.concatenate(faces)

    # --- per-vertex weights: shell (0 = photo texture, 1 = inferred) and hair
    shell = np.ones(len(V))
    shell[:n_face] = 0.0
    rel = V - center
    hairline_y = face_v[LM_FOREHEAD_TOP, 1] - center[1] - 0.05 * half_w
    front_top = smoothstep(hairline_y - 0.1 * half_w, hairline_y + 0.15 * half_w, rel[:, 1])
    behind = smoothstep(0.15 * half_w, -0.35 * half_w, rel[:, 2])
    above_nape = smoothstep(-0.75 * half_w, -0.35 * half_w, rel[:, 1])
    hair = np.maximum(front_top, behind * above_nape)
    hair[:n_face] = 0.0
    hair[n_face + (HEAD_RINGS - 1) * n + 1:] = 0.0  # neck
    info = dict(center=center.tolist(), half_width_cm=float(half_w), n_face_vertices=int(n_face))
    return V, F, shell, hair, info


# --------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photo", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    ap.add_argument("--tex-size", type=int, default=2048)
    args = ap.parse_args(argv)

    if not args.model.exists():
        raise SystemExit(f"ERROR: landmark model not found at {args.model}. Run scripts/setup.sh first.")
    bgr = cv2.imread(str(args.photo), cv2.IMREAD_COLOR)  # applies EXIF orientation
    if bgr is None:
        raise SystemExit(f"ERROR: cannot read image {args.photo}")
    img = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    scale = 2048 / max(img.shape[:2])
    if scale < 1:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    H, W = img.shape[:2]
    args.out.mkdir(parents=True, exist_ok=True)

    # ---- 1. analysis
    pts, blendshapes, n_faces = detect(img, args.model)
    canon_v, canon_f = load_canonical()
    n_face = len(canon_v)  # 468 mesh vertices; 468..477 are iris points
    face_px = pts[:n_face]

    # photo frame -> right-handed (x right, y up, z towards camera)
    P = np.stack([face_px[:, 0], -face_px[:, 1], -face_px[:, 2]], 1)
    s, R, t = umeyama(P, canon_v)
    face_v = (s * (R @ P.T)).T + t                       # person's face, frontal, canonical cm
    yaw, pitch, roll = euler_from_R(R.T)
    fit_rms = float(np.sqrt(((face_v - canon_v) ** 2).sum(1).mean()))  # deviation from average face

    x0, y0 = face_px[:, :2].min(0)
    x1, y1 = face_px[:, :2].max(0)
    face_h_px = y1 - y0
    warnings = []
    if n_faces > 1:
        warnings.append(f"{n_faces} faces found; using the largest.")
    if face_h_px < 250:
        warnings.append(f"Face is small ({face_h_px:.0f}px tall); texture will be soft. >=500px recommended.")
    if abs(yaw) > 25:
        warnings.append(f"Head is turned {yaw:.0f} deg; the far side of the face will be stretched.")
    if abs(pitch) > 20:
        warnings.append(f"Head pitch {pitch:.0f} deg; a level, frontal photo works best.")
    expr = {k: v for k, v in blendshapes.items() if v > 0.4 and k != "_neutral"}
    if expr:
        warnings.append("Strong expression detected (" + ", ".join(sorted(expr)) +
                        "); geometry keeps this expression in v0.")

    # ---- 2/3. geometry
    rim = boundary_loop(canon_f)
    V, F, shell, hair, info = build_head(face_v, canon_f, rim)

    # visibility-aware texturing: face vertices seen at grazing angles in the photo (or on the
    # rim, where background/hair bleeds in) fade to the sampled skin colour
    vn = np.zeros_like(face_v)
    tri = face_v[F[:len(canon_f)]]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    for i in range(3):
        np.add.at(vn, F[:len(canon_f), i], fn)
    vn /= np.linalg.norm(vn, axis=1, keepdims=True) + 1e-9
    view = R @ np.array([0.0, 0.0, 1.0])            # photo camera direction in the canonical frame
    facing = vn @ view
    photo_conf = smoothstep(0.12, 0.45, facing)
    photo_conf[rim] = 0.0
    shell[:n_face] = 1.0 - photo_conf
    visible_pct = float((photo_conf > 0.5).mean() * 100)

    # ---- 4. texture: crop around the face, UVs from projected landmark positions
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    side = max(x1 - x0, y1 - y0) * 1.5
    cx0, cy0 = int(max(0, cx - side / 2)), int(max(0, cy - side / 2))
    cx1, cy1 = int(min(W, cx + side / 2)), int(min(H, cy + side / 2))
    crop = img[cy0:cy1, cx0:cx1]
    ch, cw = crop.shape[:2]
    tex = cv2.resize(crop, (args.tex_size, args.tex_size), interpolation=cv2.INTER_LANCZOS4)
    uv = np.zeros((len(V), 2))
    uv[:n_face, 0] = (face_px[:, 0] - cx0) / cw
    uv[:n_face, 1] = 1.0 - (face_px[:, 1] - cy0) / ch
    # inferred vertices take the UV of the nearest rim vertex (their colour comes from attributes)
    rim_uv = uv[rim]
    for k in range(1, HEAD_RINGS):
        base = n_face + (k - 1) * len(rim)
        uv[base:base + len(rim)] = rim_uv
    uv[n_face + (HEAD_RINGS - 1) * len(rim):] = rim_uv.mean(0)
    cv2.imwrite(str(args.out / "face_texture.png"), cv2.cvtColor(tex, cv2.COLOR_RGB2BGR))

    # colours for the inferred regions, sampled from the photo
    centroid = face_px[:, :2].mean(0)
    rim_px = face_px[rim, :2]
    skin = median_color(img, rim_px + 0.12 * (centroid - rim_px), radius=4)
    fh = face_h_px
    fx = face_px[list(LM_FOREHEAD_SIDES), 0]
    top = face_px[LM_FOREHEAD_TOP, 1]
    hair_pts = np.array([[x, y] for x in np.linspace(fx[0], fx[1], 7)
                         for y in np.linspace(top - 0.32 * fh, top - 0.12 * fh, 5)])
    hair_col = median_color(img, hair_pts, radius=4)
    hair_detected = True
    if hair_col is None:
        hair_col, hair_detected = np.array([0.12, 0.09, 0.07]), False
    elif delta_e(hair_col, skin) < 5.0:
        hair_detected = False  # forehead continues: bald / receding / very light hair
    if not hair_detected:
        hair *= 0.15
        warnings.append("No distinct hair colour above the forehead; scalp rendered mostly as skin.")

    np.savez_compressed(args.out / "head_mesh.npz", vertices=V / 100.0, faces=F.astype(np.int32),
                        uv=uv.astype(np.float32), shell=shell.astype(np.float32), hair=hair.astype(np.float32))

    # ---- overlay for inspection
    ov = cv2.cvtColor(img, cv2.COLOR_RGB2BGR).copy()
    for a, b, c in canon_f:
        tri = face_px[[a, b, c], :2].astype(np.int32)
        cv2.polylines(ov, [tri], True, (80, 220, 80), 1, cv2.LINE_AA)
    cv2.polylines(ov, [rim_px.astype(np.int32)], True, (0, 140, 255), 2, cv2.LINE_AA)
    cv2.imwrite(str(args.out / "landmarks_overlay.png"), ov)

    analysis = {
        "photo": str(args.photo),
        "image_size": [W, H],
        "faces_detected": n_faces,
        "face_bbox_px": [round(float(v)) for v in (x0, y0, x1, y1)],
        "head_pose_deg": {"yaw": round(yaw, 1), "pitch": round(pitch, 1), "roll": round(roll, 1)},
        "shape_deviation_from_average_cm": round(fit_rms, 3),
        "face_vertices_textured_from_photo_pct": round(visible_pct, 1),
        "skin_color_srgb": [round(float(c), 3) for c in skin],
        "hair_color_srgb": [round(float(c), 3) for c in hair_col],
        "hair_detected": hair_detected,
        "hair_vs_skin_delta_e": round(delta_e(hair_col, skin), 1),
        "top_expressions": dict(sorted(blendshapes.items(), key=lambda kv: -kv[1])[:6]),
        "warnings": warnings,
        "provenance": {
            "face_surface": "reconstructed from the photo (MediaPipe 3D landmarks, 468 vertices)",
            "face_texture": "projected directly from the photo",
            "back_of_head, scalp, neck": "inferred from face proportions; not observed",
            "ears, hair geometry, eyeballs, teeth": "not modelled in v0",
        },
    }
    (args.out / "analysis.json").write_text(json.dumps(analysis, indent=2))
    job = {
        "mesh": "head_mesh.npz",
        "texture": "face_texture.png",
        "photo": str(args.photo.resolve()),
        "skin_color_linear": srgb_to_linear(skin).round(4).tolist(),
        "hair_color_linear": srgb_to_linear(hair_col).round(4).tolist(),
        "blend": "head.blend",
        **info,
    }
    (args.out / "job.json").write_text(json.dumps(job, indent=2))

    print(f"Face found: {x1 - x0:.0f}x{face_h_px:.0f}px, yaw {yaw:.0f}, pitch {pitch:.0f}, roll {roll:.0f}")
    for w_ in warnings:
        print("WARNING:", w_)
    print(f"Mesh: {len(V)} vertices, {len(F)} triangles -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
