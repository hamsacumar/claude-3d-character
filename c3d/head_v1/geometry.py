"""Head geometry from MediaPipe landmarks: pure NumPy (runs in a venv, in Blender's Python and in tests).

Coordinate frame: canonical MediaPipe face frame in centimetres; x = towards the person's left (image right),
y = up, z = towards the camera.

The head is assembled from:
  * FACE: the person's own 468 MediaPipe 3D landmarks with MediaPipe's canonical triangle topology
    (forehead, cheeks, jaw line, chin, nose, eyelid margins, lips). Depth comes from MediaPipe's learned z.
  * EYE OPENINGS: the triangles filling each lid margin are removed; the margin is turned inward to form
    eyelid thickness and an eye socket that wraps a separate eyeball.
  * MOUTH: the inner-lip triangles are removed and replaced by a shallow mouth cavity behind the lips.
  * CRANIUM and NECK: lofted from the face outline to a superellipsoid sized from the face (inferred).
  * EARS: procedural ears sized and placed from facial landmarks (inferred, not observed).
"""
from __future__ import annotations

import collections
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CANONICAL_OBJ = HERE.parent / "data" / "canonical_face_model.obj"

# Ordered lid-margin and inner-lip loops (MediaPipe Face Mesh indices).
RIGHT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]   # person's right
LEFT_EYE = [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466]
INNER_LIPS = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191]
RIGHT_IRIS_CENTER, LEFT_IRIS_CENTER = 468, 473
LM_FACE_SIDE_R, LM_FACE_SIDE_L = 234, 454
LM_BROW_R, LM_BROW_L = 105, 334
LM_NOSE_BASE = 2
LM_CHIN = 152
LM_FOREHEAD_TOP = 10

EYEBALL_RADIUS = 1.2          # cm, adult average
HEAD_RINGS = 30
NECK_SEGMENTS = 40


@dataclass
class Part:
    name: str
    verts: np.ndarray
    faces: np.ndarray
    face_mat: np.ndarray                   # per-face material index
    info: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- basic helpers
def load_canonical(path: Path = CANONICAL_OBJ):
    verts, faces = [], []
    for line in open(path):
        if line.startswith("v "):
            verts.append([float(x) for x in line.split()[1:4]])
        elif line.startswith("f "):
            faces.append([int(t.split("/")[0]) - 1 for t in line.split()[1:]])
    return np.asarray(verts, float), np.asarray(faces, np.int64)


def boundary_loops(faces: np.ndarray) -> list[list[int]]:
    count = collections.Counter()
    for f in faces:
        for i in range(3):
            count[tuple(sorted((int(f[i]), int(f[(i + 1) % 3]))))] += 1
    adj = collections.defaultdict(list)
    for (a, b), c in count.items():
        if c == 1:
            adj[a].append(b)
            adj[b].append(a)
    seen, loops = set(), []
    for s in sorted(adj):
        if s in seen:
            continue
        loop, prev, cur = [s], -1, s
        seen.add(s)
        while True:
            nxt = [n for n in adj[cur] if n != prev and n not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            loop.append(cur)
            seen.add(cur)
        loops.append(loop)
    return loops


def umeyama(src, dst):
    mu_s, mu_d = src.mean(0), dst.mean(0)
    xs, xd = src - mu_s, dst - mu_d
    U, S, Vt = np.linalg.svd(xd.T @ xs / len(src))
    D = np.eye(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        D[2, 2] = -1
    R = U @ D @ Vt
    s = np.trace(np.diag(S) @ D) / ((xs ** 2).sum() / len(src))
    return s, R, mu_d - s * R @ mu_s


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def normalize(v):
    return v / (np.linalg.norm(v, axis=-1, keepdims=True) + 1e-12)


def _point_in_poly(pt, poly):
    x, y = pt
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def interior_faces(V, F, ring):
    """Triangles made only of ring vertices whose centroid lies inside the ring (the opening fill)."""
    s = set(ring)
    poly = V[ring][:, :2]
    return [i for i, f in enumerate(F) if all(int(v) in s for v in f) and _point_in_poly(V[f].mean(0)[:2], poly)]


# --------------------------------------------------------------------------- face + openings
def face_with_openings(V478: np.ndarray, Fc: np.ndarray, canon_V: np.ndarray):
    """Remove eye/mouth fill triangles (decided on the canonical mesh, so it works for closed eyes too)."""
    remove = set()
    for ring in (RIGHT_EYE, LEFT_EYE, INNER_LIPS):
        remove.update(interior_faces(canon_V, Fc, ring))
    keep = np.array([f for i, f in enumerate(Fc) if i not in remove])
    return V478[:468].copy(), keep


def eye_socket(V, ring, iris_center, radius=EYEBALL_RADIUS):
    """Eyelid thickness + socket around an eyeball. Returns (new verts, faces using global indices
    for ring verts and local offset for new verts), eyeball centre and gaze direction."""
    ring_p = V[ring]
    c = ring_p.mean(0)
    # eyeball sits behind the lid margin; its front pole is just in front of the margin centroid
    centre = c + np.array([0.0, 0.0, -radius * 0.78])
    # gaze: from eyeball centre through the iris landmark (x/y from the photo; z completed on the sphere)
    d = iris_center[:2] - centre[:2]
    dz = np.sqrt(max(radius ** 2 - (d ** 2).sum(), 0.2 * radius ** 2))
    gaze = normalize(np.array([d[0], d[1], dz]))
    dirs = normalize(ring_p - centre)
    ring_a = centre + dirs * radius * 1.012                    # lid inner edge resting on the eyeball
    back = normalize(dirs + np.array([0.0, 0.0, -0.9]))
    ring_b = centre + back * radius * 0.92                     # socket wall, hidden behind the eyeball
    cap = centre + np.array([0.0, 0.0, -radius * 0.6])
    return ring_a, ring_b, cap, centre, gaze


def mouth_cavity(V, ring):
    p = V[ring]
    m = p.mean(0)
    ring_a = p + (m - p) * 0.12 + np.array([0.0, 0.0, -0.35])
    ring_b = p + (m - p) * 0.45 + np.array([0.0, 0.0, -1.7])
    cap = m + np.array([0.0, 0.0, -2.1])
    return ring_a, ring_b, cap


def _bridge(a_ids, b_ids):
    n = len(a_ids)
    out = []
    for i in range(n):
        j = (i + 1) % n
        out += [[a_ids[i], a_ids[j], b_ids[j]], [a_ids[i], b_ids[j], b_ids[i]]]
    return out


def _fan(ids, cap_id):
    n = len(ids)
    return [[ids[i], ids[(i + 1) % n], cap_id] for i in range(n)]


# --------------------------------------------------------------------------- cranium
@dataclass
class Skull:
    centre: np.ndarray
    ax: float
    ay_up: float
    ay_dn: float
    az_front: float
    az_back: float
    p: float = 2.3

    def radius(self, d):
        ay = np.where(d[..., 1] >= 0, self.ay_up, self.ay_dn)
        az = np.where(d[..., 2] >= 0, self.az_front, self.az_back)
        s = (np.abs(d[..., 0] / self.ax) ** self.p + np.abs(d[..., 1] / ay) ** self.p
             + np.abs(d[..., 2] / az) ** self.p)
        return s ** (-1.0 / self.p)

    def surface_x(self, y, z):
        dy = (y - self.centre[1]) / (self.ay_up if y >= self.centre[1] else self.ay_dn)
        dz = (z - self.centre[2]) / (self.az_front if z >= self.centre[2] else self.az_back)
        rest = max(1.0 - abs(dy) ** self.p - abs(dz) ** self.p, 0.0)
        return self.ax * rest ** (1.0 / self.p)


def make_skull(V) -> Skull:
    left, right = V[LM_FACE_SIDE_R], V[LM_FACE_SIDE_L]
    eye_y = V[[33, 263], 1].mean()
    half_w = 0.5 * np.linalg.norm(right - left) * 1.05
    centre = np.array([(left[0] + right[0]) / 2, eye_y + 0.2 * half_w, (left[2] + right[2]) / 2 - 0.15 * half_w])
    return Skull(centre, ax=half_w, ay_up=1.40 * half_w, ay_dn=1.12 * half_w,
                 az_front=1.25 * half_w, az_back=1.32 * half_w)


def cranium_loft(V, rim, skull: Skull, start_index: int, rings=HEAD_RINGS):
    """Rings from the face outline to the back pole, blending into the skull surface."""
    back = np.array([0.0, 0.0, -1.0])
    rim_p = V[rim]
    d0 = rim_p - skull.centre
    r0 = np.linalg.norm(d0, axis=1)
    d0 = d0 / r0[:, None]
    omega = np.arccos(np.clip(d0 @ back, -1, 1))
    verts, ring_ids = [], [list(rim)]
    nxt = start_index
    for k in range(1, rings):
        t = k / rings
        so = np.sin(omega)
        d = (np.sin((1 - t) * omega) / so)[:, None] * d0 + (np.sin(t * omega) / so)[:, None] * back
        d = normalize(d)
        w = smoothstep(0.0, 0.45, t)
        r = (1 - w) * r0 + w * skull.radius(d)
        verts.append(skull.centre + d * r[:, None])
        ring_ids.append(list(range(nxt, nxt + len(rim))))
        nxt += len(rim)
    pole = skull.centre + back * skull.az_back
    verts.append(pole[None])
    pole_id = nxt
    faces = []
    for k in range(len(ring_ids) - 1):
        faces += _bridge(ring_ids[k], ring_ids[k + 1])
    faces += _fan(ring_ids[-1], pole_id)
    return np.concatenate(verts), faces


def neck(V, skull: Skull, start_index: int):
    r = 0.66 * skull.ax
    cx, cz = skull.centre[0], skull.centre[2] + 0.02 * skull.ax
    y_top = skull.centre[1] - 0.45 * skull.ax
    y_bot = V[LM_CHIN, 1] - 1.0 * skull.ax
    ang = np.linspace(0, 2 * np.pi, NECK_SEGMENTS, endpoint=False)
    rings = [np.stack([cx + r * np.cos(ang), np.full_like(ang, y), cz + r * 0.92 * np.sin(ang)], 1)
             for y in np.linspace(y_top, y_bot, 7)]
    verts = np.concatenate(rings)
    faces = []
    for k in range(len(rings) - 1):
        a = [start_index + k * NECK_SEGMENTS + i for i in range(NECK_SEGMENTS)]
        b = [start_index + (k + 1) * NECK_SEGMENTS + i for i in range(NECK_SEGMENTS)]
        faces += _bridge(a, b)
    return verts, faces


# --------------------------------------------------------------------------- ears
def ear(V, skull: Skull, side: int, rings=12, segs=48):
    """Procedural ear (helix rim, antihelix ridge, concha bowl, lobe). side=-1 person's right, +1 left.
    Height spans brow to nose base (classical proportion); position from the face-side landmark."""
    brow_y = V[[LM_BROW_R, LM_BROW_L], 1].mean()
    base_y = V[LM_NOSE_BASE, 1]
    h = 0.92 * (brow_y - base_y)
    w = 0.55 * h
    side_lm = V[LM_FACE_SIDE_R if side < 0 else LM_FACE_SIDE_L]
    cy = base_y + 0.48 * h
    cz = side_lm[2] - 0.75 - 0.5 * w
    x_s = skull.surface_x(cy, cz)
    theta = np.linspace(0, 2 * np.pi, segs, endpoint=False)          # 0 = towards the face, pi/2 = up
    rho = np.linspace(0, 1, rings + 1)[1:]
    # outline: wider at the top, narrow lobe at the bottom, flatter front edge
    width = 0.5 * w * (1 - 0.30 * np.clip(-np.sin(theta), 0, 1)) * (1 - 0.15 * np.clip(np.cos(theta), 0, 1))
    height = 0.5 * h * np.ones_like(theta)
    T, Rh = np.meshgrid(theta, rho)                                  # (rings, segs)
    f_coord = (width[None] * np.cos(T)) * Rh
    u_coord = (height[None] * np.sin(T)) * Rh
    helix_fade = 1 - 0.75 * smoothstep(0.3, 0.9, np.cos(T)) * smoothstep(-0.2, 0.6, -np.sin(T) + 0.3)
    lobe = smoothstep(0.2, 0.9, -np.sin(T))
    relief = (-0.30 * (1 - smoothstep(0.0, 0.5, Rh)) * (1 - lobe)                       # concha bowl
              + 0.32 * np.exp(-((Rh - 0.62) / 0.10) ** 2) * (1 - lobe)                   # antihelix
              + 0.45 * np.exp(-((Rh - 0.90) / 0.07) ** 2) * helix_fade * (1 - 0.5 * lobe)  # helix rim
              + 0.12 * lobe)
    flare = np.clip(-f_coord, 0, None) * np.tan(np.radians(22))       # back of the ear stands off the head
    o_front = 0.32 + relief + flare
    o_back = flare * 0.85 - 0.25                                      # rear skin, slightly inside the skull
    front = np.stack([f_coord, u_coord, o_front], -1).reshape(-1, 3)
    backv = np.stack([f_coord, u_coord, o_back], -1).reshape(-1, 3)
    centre_f = np.array([[0.0, 0.0, 0.32 - 0.30]])
    centre_b = np.array([[0.0, 0.0, -0.25]])
    local = np.concatenate([centre_f, front, centre_b, backv])
    nf = 1 + rings * segs
    faces = []
    def idx(layer, r, s):
        return layer * nf + 1 + r * segs + (s % segs)
    for layer in (0, 1):
        c = layer * nf
        faces += [[c, idx(layer, 0, s), idx(layer, 0, s + 1)] for s in range(segs)]
        for r in range(rings - 1):
            for s in range(segs):
                faces += [[idx(layer, r, s), idx(layer, r + 1, s), idx(layer, r + 1, s + 1)],
                          [idx(layer, r, s), idx(layer, r + 1, s + 1), idx(layer, r, s + 1)]]
    for s in range(segs):                                             # outer edge: front to back
        a0, a1 = idx(0, rings - 1, s), idx(0, rings - 1, s + 1)
        b0, b1 = idx(1, rings - 1, s), idx(1, rings - 1, s + 1)
        faces += [[a0, b0, b1], [a0, b1, a1]]
    faces = np.array(faces)
    # back layer faces must point the other way
    back_mask = np.all(faces >= nf, axis=1)
    faces[back_mask] = faces[back_mask][:, ::-1]
    # local (forward, up, outward) -> canonical (x, y, z)
    world = np.stack([side * (x_s + local[:, 2]), cy + local[:, 1], cz + local[:, 0]], 1)
    if side < 0:                                                      # mirrored: keep normals outward
        faces = faces[:, ::-1]
    return Part(f"Ear_{'R' if side < 0 else 'L'}", world, faces, np.zeros(len(faces), np.int64),
                info=dict(height_cm=float(h), width_cm=float(w), centre=[float(side * x_s), float(cy), float(cz)]))


# --------------------------------------------------------------------------- assemble
def build_head(V478: np.ndarray, canon_V: np.ndarray, canon_F: np.ndarray):
    """Returns parts: Head (face+eyelids+mouth+cranium+neck), Ear_R, Ear_L, and eyeball specs."""
    rim = max(boundary_loops(canon_F), key=len)
    Vf, Ff = face_with_openings(V478, canon_F, canon_V)
    verts = [Vf]
    faces = [list(map(list, Ff))]
    mats = [[0] * len(Ff)]
    nxt = len(Vf)
    eyes = []
    for ring, iris in ((RIGHT_EYE, V478[RIGHT_IRIS_CENTER]), (LEFT_EYE, V478[LEFT_IRIS_CENTER])):
        ra, rb, cap, centre, gaze = eye_socket(Vf, ring, iris)
        a_ids = list(range(nxt, nxt + len(ring)))
        b_ids = list(range(nxt + len(ring), nxt + 2 * len(ring)))
        cap_id = nxt + 2 * len(ring)
        verts += [ra, rb, cap[None]]
        f = _bridge(list(ring), a_ids) + _bridge(a_ids, b_ids) + _fan(b_ids, cap_id)
        faces.append(f)
        mats.append([0] * len(f))
        nxt = cap_id + 1
        eyes.append(dict(centre=centre, gaze=gaze, radius=EYEBALL_RADIUS))
    ra, rb, cap = mouth_cavity(Vf, INNER_LIPS)
    a_ids = list(range(nxt, nxt + len(INNER_LIPS)))
    b_ids = list(range(nxt + len(INNER_LIPS), nxt + 2 * len(INNER_LIPS)))
    cap_id = nxt + 2 * len(INNER_LIPS)
    verts += [ra, rb, cap[None]]
    f_lip = _bridge(list(INNER_LIPS), a_ids)
    f_cav = _bridge(a_ids, b_ids) + _fan(b_ids, cap_id)
    faces += [f_lip, f_cav]
    mats += [[0] * len(f_lip), [1] * len(f_cav)]
    nxt = cap_id + 1
    skull = make_skull(Vf)
    cv, cf = cranium_loft(Vf, rim, skull, nxt)
    verts.append(cv); faces.append(cf); mats.append([0] * len(cf))
    nxt += len(cv)
    nv, nf_ = neck(Vf, skull, nxt)
    verts.append(nv); faces.append(nf_); mats.append([0] * len(nf_))
    V = np.concatenate(verts)
    F = np.array([f for group in faces for f in group], np.int64)
    M = np.array([m for group in mats for m in group], np.int64)
    head = Part("Head", V, F, M, info=dict(n_face_vertices=len(Vf), skull=dict(
        centre=skull.centre.tolist(), half_width_cm=skull.ax)))
    return head, [ear(Vf, skull, -1), ear(Vf, skull, +1)], eyes, skull
