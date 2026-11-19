#!/usr/bin/env bash
# P0 setup: CPU-only, everything inside this project folder.
#   .tools/uv/      uv binary (from the official GitHub release, checksum-verified)
#   .tools/python/  CPython 3.12 managed by uv
#   .cache/uv/      uv download cache
#   .venv-p0/       Python environment for P0
#   models/         MediaPipe model files
# Does not use sudo, does not touch system Python, CUDA, drivers or Blender.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
UV_VERSION=0.13.9
TORCH_VERSION=2.15.0
export UV_INSTALL_DIR="$ROOT/.tools/uv" UV_PYTHON_INSTALL_DIR="$ROOT/.tools/python" UV_CACHE_DIR="$ROOT/.cache/uv"
export UV_NO_MODIFY_PATH=1 UV_PYTHON_PREFERENCE=only-managed

cat <<MSG
This will download (approximate sizes):
  uv ${UV_VERSION} standalone binary ............... ~18 MB   (MIT OR Apache-2.0)
  CPython 3.12 (project-local) ................... ~30 MB   (PSF-2.0)
  torch ${TORCH_VERSION} CPU-only (PyTorch CPU index) ... ~190 MB  (BSD-style, permissive)
  numpy, scipy, mediapipe, opencv-contrib-python
    + their dependencies (PyPI) .................. ~212 MB  (BSD / Apache-2.0 / MIT / PSF / MPL-2.0)
  MediaPipe face_landmarker.task ................. 3.8 MB   (Apache-2.0)
  MediaPipe selfie_multiclass_256x256.tflite ..... 16.4 MB  (Apache-2.0)
  Total ~0.47 GB download, ~1.3 GB on disk after install.
Nothing from FLAME is downloaded by this script.
MSG
read -r -p "Proceed with these downloads? [y/N] " ans
[[ "$ans" =~ ^[Yy]$ ]] || { echo "Cancelled. Nothing downloaded."; exit 0; }

mkdir -p "$UV_INSTALL_DIR" "$UV_PYTHON_INSTALL_DIR" "$UV_CACHE_DIR" models
UV="$UV_INSTALL_DIR/uv"
if [ ! -x "$UV" ]; then
  T="uv-x86_64-unknown-linux-gnu.tar.gz"
  BASE="https://github.com/astral-sh/uv/releases/download/${UV_VERSION}"
  TMP="$(mktemp -d)"
  curl -fsSL -o "$TMP/$T" "$BASE/$T"
  curl -fsSL -o "$TMP/$T.sha256" "$BASE/$T.sha256"
  (cd "$TMP" && sha256sum -c "$T.sha256")
  tar -xzf "$TMP/$T" -C "$TMP"
  install -m 755 "$TMP/uv-x86_64-unknown-linux-gnu/uv" "$UV"
  rm -rf "$TMP"
fi
"$UV" --version

"$UV" python install 3.12
"$UV" venv --python 3.12 .venv-p0
"$UV" pip install --python .venv-p0 "torch==${TORCH_VERSION}" --index-url https://download.pytorch.org/whl/cpu
"$UV" pip install --python .venv-p0 -r requirements-p0.txt

fetch() { [ -s "$2" ] || curl -fSL -o "$2" "$1"; }
fetch https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task models/face_landmarker.task
fetch https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite models/selfie_multiclass_256x256.tflite

.venv-p0/bin/python - <<'PY'
import torch, numpy, scipy, cv2, mediapipe
print("torch", torch.__version__, "| CUDA build:", torch.version.cuda, "| CUDA available:", torch.cuda.is_available())
print("numpy", numpy.__version__, "| scipy", scipy.__version__, "| cv2", cv2.__version__, "| mediapipe", mediapipe.__version__)
assert torch.version.cuda is None, "Expected the CPU-only torch build"
PY
mkdir -p output
"$UV" pip freeze --python .venv-p0 > output/p0_installed_packages.txt
echo "P0 environment ready. Installed package list: output/p0_installed_packages.txt"
