# Claude 3D Character

Reconstruct a recognizable, textured 3D human head from **one** face photograph,
and grow it into a full rigged 3D character for the AI 3D Studio.

Status: **design phase**. No code or model weights yet.

- [docs/RECONSTRUCTION_APPROACH.md](docs/RECONSTRUCTION_APPROACH.md): how we get from one photo to a 3D face
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): the modules, data contracts and runtime layout
- [docs/MODEL_SURVEY.md](docs/MODEL_SURVEY.md): candidate models, licenses and GPU cost
- [docs/ROADMAP.md](docs/ROADMAP.md): the phased implementation plan

Target stack: Python 3.11, PyTorch (reconstruction side), Blender 4.5 LTS + `bpy`
(assembly, UV, baking, export).
