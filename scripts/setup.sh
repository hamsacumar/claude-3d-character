#!/usr/bin/env bash
# One-time setup on Ubuntu 22.04: Python venv + the 3.7 MB MediaPipe face landmark model.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! python3 -m venv --help >/dev/null 2>&1; then
  echo "Installing python3-venv (needs sudo)..."; sudo apt-get install -y python3-venv
fi
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q

mkdir -p models
MODEL=models/face_landmarker.task
if [ ! -s "$MODEL" ]; then
  echo "Downloading MediaPipe Face Landmarker model (3.7 MB, Apache-2.0)..."
  curl -fSL -o "$MODEL" \
    https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
fi

BLENDER="${BLENDER:-/usr/local/bin/blender}"
if [ -x "$BLENDER" ]; then "$BLENDER" --version | head -1; else echo "WARNING: Blender not found at $BLENDER (set BLENDER=...)"; fi
echo "Setup complete. Next: scripts/make_head.sh path/to/face.jpg"
