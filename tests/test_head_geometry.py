"""Geometry sanity tests for c3d/head_v1 (pure NumPy; run: python -m pytest tests/ or python tests/test_head_geometry.py)."""
import collections
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from c3d.head_v1 import geometry as G  # noqa: E402


def _canonical_478():
    V, F = G.load_canonical()
    iris = []
    for ring in (G.RIGHT_EYE, G.LEFT_EYE):          # 468..472 right iris, 473..477 left iris
        c = V[ring].mean(0)
        iris += [c] + [c + d for d in ([0.5, 0, 0], [0, 0.5, 0], [-0.5, 0, 0], [0, -0.5, 0])]
    return np.vstack([V, np.array(iris)]), V, F


def _boundary_loops(F):
    return G.boundary_loops(F)


def _edge_use(F):
    c = collections.Counter()
    for f in F:
        for i in range(3):
            c[tuple(sorted((int(f[i]), int(f[(i + 1) % 3]))))] += 1
    return c


def test_openings_removed_exactly():
    V478, V, F = _canonical_478()
    _, keep = G.face_with_openings(V478, F, V)
    assert len(F) - len(keep) == 14 + 14 + 18
    loops = _boundary_loops(keep)
    assert sorted(len(l) for l in loops) == sorted([36, 16, 16, 20])


def test_head_closed_except_neck():
    V478, V, F = _canonical_478()
    head, ears, eyes, skull = G.build_head(V478, V, F)
    assert np.isfinite(head.verts).all() and head.faces.max() < len(head.verts)
    use = _edge_use(head.faces)
    assert max(use.values()) <= 2, "non-manifold edge"
    loops = _boundary_loops(head.faces)
    assert len(loops) == 2 and all(len(l) == G.NECK_SEGMENTS for l in loops), [len(l) for l in loops]
    for e in ears:
        assert np.isfinite(e.verts).all()
        eu = _edge_use(e.faces)
        assert all(v == 2 for v in eu.values()), "ear must be a closed surface"
    for eye in eyes:
        assert abs(np.linalg.norm(eye["gaze"]) - 1) < 1e-6 and eye["gaze"][2] > 0.5


def test_proportions_plausible():
    V478, V, F = _canonical_478()
    head, ears, eyes, skull = G.build_head(V478, V, F)
    hv = head.verts
    length = hv[:, 2].max() - hv[:, 2].min()            # nose tip to back of head (incl. neck offset)
    breadth = hv[:, 0].max() - hv[:, 0].min()
    assert 17 < length < 25, length
    assert 13 < breadth < 19, breadth
    for e in ears:
        assert 5 < e.info["height_cm"] < 8.5, e.info


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
