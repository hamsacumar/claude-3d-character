#!/usr/bin/env python3
"""Step 1 (project venv): analyze the photo with MediaPipe Face Landmarker.

Writes to --out:
  landmarks.npz     478 landmarks aligned to MediaPipe's canonical metric frame (cm), pixel landmarks,
                    sampled colours (linear RGB), pose
  analysis.json     pose, expression scores, colours, warnings
  00_reference.*    copy of the input photo
  landmarks_overlay.png
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from c3d.head_v1 import geometry as G  # noqa: E402

DEFAULT_MODEL = ROOT / "models" / "face_landmarker.task"


def detect(img_rgb, model_path):
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision
    opts = vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.IMAGE, num_faces=2,
        output_face_blendshapes=True, output_facial_transformation_matrixes=True)
    with vision.FaceLandmarker.create_from_options(opts) as lm:
        res = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(img_rgb)))
    if not res.face_landmarks:
        raise SystemExit("ERROR: no face detected in the photo.")
    h, w = img_rgb.shape[:2]
    areas = [np.ptp([p.x for p in f]) * np.ptp([p.y for p in f]) for f in res.face_landmarks]
    i = int(np.argmax(areas))
    pts = np.array([[p.x * w, p.y * h, p.z * w] for p in res.face_landmarks[i]], float)
    blend = {c.category_name: round(float(c.score), 3) for c in res.face_blendshapes[i]} if res.face_blendshapes else {}
    return pts, blend, len(res.face_landmarks)


def median_rgb(img, pts, r=3):
    h, w = img.shape[:2]
    s = [img[max(0, y - r):min(h, y + r + 1), max(0, x - r):min(w, x + r + 1)].reshape(-1, 3)
         for x, y in np.round(pts).astype(int) if 0 <= x < w and 0 <= y < h]
    return (np.median(np.concatenate(s), 0) / 255.0) if s else None


def srgb_to_linear(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def iris_colour(img, px, centre_id):
    """Median colour of the iris ring (between pupil and limbus), excluding very dark and very bright pixels."""
    c = px[centre_id, :2]
    radius = np.mean(np.linalg.norm(px[centre_id + 1:centre_id + 5, :2] - c, axis=1))
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.hypot(xx - c[0], yy - c[1])
    mask = (d > radius * 0.45) & (d < radius * 0.9)
    vals = img[mask].astype(float)
    if len(vals) < 5:
        return None, float(radius)
    lum = vals.mean(1)
    keep = vals[(lum > np.percentile(lum, 15)) & (lum < np.percentile(lum, 90))]
    return (np.median(keep if len(keep) else vals, 0) / 255.0), float(radius)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("photo", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    ap.add_argument("--depth-scale", type=float, default=1.0,
                    help="scale MediaPipe's estimated depth (z); 1.0 = as estimated")
    a = ap.parse_args(argv)
    if not a.model.exists():
        raise SystemExit(f"ERROR: model not found: {a.model}")
    bgr = cv2.imread(str(a.photo), cv2.IMREAD_COLOR)
    if bgr is None:
        raise SystemExit(f"ERROR: cannot read {a.photo}")
    img = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    s = 2048 / max(img.shape[:2])
    if s < 1:
        img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    H, W = img.shape[:2]
    a.out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(a.photo, a.out / f"00_reference{a.photo.suffix.lower()}")

    px, blend, n_faces = detect(img, a.model)
    canon_V, canon_F = G.load_canonical()
    P = np.stack([px[:, 0], -px[:, 1], -px[:, 2] * a.depth_scale], 1)     # x right, y up, z to camera
    s_, R, t = G.umeyama(P[:468], canon_V)
    V478 = (s_ * (R @ P.T)).T + t
    Rh = R.T
    yaw = math.degrees(math.asin(max(-1.0, min(1.0, -Rh[2, 0]))))
    pitch = math.degrees(math.atan2(Rh[2, 1], Rh[2, 2]))
    roll = math.degrees(math.atan2(Rh[1, 0], Rh[0, 0]))

    centroid = px[:468, :2].mean(0)
    rim = max(G.boundary_loops(canon_F), key=len)
    skin = median_rgb(img, px[rim, :2] + 0.18 * (centroid - px[rim, :2]), 4)
    lips = median_rgb(img, px[[0, 17, 37, 267, 84, 314, 39, 269, 181, 405], :2], 2)
    iris_r, iris_rad_r = iris_colour(img, px, 468)
    iris_l, iris_rad_l = iris_colour(img, px, 473)
    irises = [c for c in (iris_r, iris_l) if c is not None]
    iris = np.mean(irises, 0) if irises else np.array([0.25, 0.18, 0.12])

    face_h = np.ptp(px[:468, 1])
    iod = np.linalg.norm(px[33, :2] - px[263, :2])
    warnings = []
    if n_faces > 1:
        warnings.append(f"{n_faces} faces found; using the largest.")
    if face_h < 300:
        warnings.append(f"Face is only {face_h:.0f}px tall; landmarks are less precise.")
    if abs(yaw) > 20:
        warnings.append(f"Head turned {yaw:.0f} deg; the far side is estimated less reliably.")
    if iris_rad_r < 6 or iris_rad_l < 6:
        warnings.append("Irises are very small in the photo; eye colour is approximate.")

    np.savez_compressed(a.out / "landmarks.npz", V478=V478, px=px, image_size=np.array([W, H]),
                        skin_lin=srgb_to_linear(skin), lips_lin=srgb_to_linear(lips),
                        iris_lin=srgb_to_linear(iris), depth_scale=a.depth_scale)

    ov = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    for f in canon_F:
        cv2.polylines(ov, [px[f, :2].astype(np.int32)], True, (90, 200, 90), 1, cv2.LINE_AA)
    for ring, col in ((G.RIGHT_EYE, (255, 160, 0)), (G.LEFT_EYE, (255, 160, 0)), (G.INNER_LIPS, (0, 80, 255))):
        cv2.polylines(ov, [px[ring, :2].astype(np.int32)], True, col, 2, cv2.LINE_AA)
    cv2.polylines(ov, [px[rim, :2].astype(np.int32)], True, (0, 220, 255), 2, cv2.LINE_AA)
    cv2.imwrite(str(a.out / "landmarks_overlay.png"), ov)

    analysis = dict(
        photo=str(a.photo), image_size=[W, H], faces_detected=n_faces,
        face_height_px=round(float(face_h)), inter_ocular_px=round(float(iod), 1),
        head_pose_deg=dict(yaw=round(yaw, 1), pitch=round(pitch, 1), roll=round(roll, 1)),
        depth_scale=a.depth_scale,
        colours_srgb=dict(skin=np.round(skin, 3).tolist(), lips=np.round(lips, 3).tolist(),
                          iris=np.round(iris, 3).tolist()),
        top_expressions=dict(sorted(blend.items(), key=lambda kv: -kv[1])[:8]),
        warnings=warnings)
    (a.out / "analysis.json").write_text(json.dumps(analysis, indent=2))
    print(f"Face {face_h:.0f}px tall, yaw {yaw:.0f}, pitch {pitch:.0f}, roll {roll:.0f}")
    for w_ in warnings:
        print("WARNING:", w_)
    return 0


if __name__ == "__main__":
    sys.exit(main())
