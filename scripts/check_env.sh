#!/usr/bin/env bash
# Read-only environment report: installs nothing, downloads nothing.
# Run on the Ubuntu machine and paste the output back to Claude.
cd "$(dirname "$0")/.." || exit 1
echo "== OS";      lsb_release -ds 2>/dev/null || cat /etc/os-release | head -2; uname -r
echo "== glibc";   ldd --version | head -1
echo "== CPU/RAM"; nproc; free -h | sed -n '1,2p'
echo "== Disk (repo)"; df -h . | tail -1
echo "== NVIDIA";  nvidia-smi --query-gpu=name,driver_version,memory.total,compute_cap --format=csv 2>&1 | head -3
nvidia-smi 2>/dev/null | grep -o "CUDA Version: [0-9.]*"
echo "== nvcc";    (nvcc --version 2>/dev/null || ls -d /usr/local/cuda* 2>/dev/null || echo "no CUDA toolkit") | tail -2
echo "== gcc";     gcc --version 2>/dev/null | head -1
echo "== Python";  for p in python3 python3.10 python3.11 python3.12; do command -v $p >/dev/null && echo "$p: $($p --version 2>&1)"; done
echo "== uv";      uv --version 2>/dev/null || echo "uv not installed"
echo "== Blender"; B="${BLENDER:-/usr/local/bin/blender}"; "$B" --version 2>/dev/null | head -1
"$B" -b --factory-startup --python-expr "import sys, bpy; print('blender python', sys.version.split()[0]); \
import _cycles; print('cycles devices', _cycles.available_devices('CUDA'), _cycles.available_devices('OPTIX'))" 2>/dev/null \
  | grep -E "blender python|cycles devices"
echo "== Shared libraries needed by MediaPipe (EGL/GLES) and optional PortAudio"
for l in libEGL.so.1 libGLESv2.so.2 libportaudio.so.2; do ldconfig -p | grep -q "$l" && echo "$l: found" || echo "$l: MISSING"; done
echo "== Network reachability (HEAD requests only, nothing downloaded)"
for u in https://pypi.org/simple/ https://download.pytorch.org/whl/cpu/ https://storage.googleapis.com/mediapipe-models/ https://github.com/astral-sh/uv/releases https://flame.is.tue.mpg.de/; do
  printf '%s -> ' "$u"; curl -sS -o /dev/null -I -m 15 -w '%{http_code}\n' "$u" 2>&1 | tail -1; done
echo "== Existing torch (if any)"; python3 -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())" 2>&1 | tail -1
