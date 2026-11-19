#!/usr/bin/env bash
# P0 setup: CPU-only, everything inside this project folder.
#   .tools/uv/      uv binary (official GitHub release, SHA-256 verified)
#   .tools/python/  CPython 3.12 managed by uv
#   .cache/uv/      uv download cache
#   .venv-p0/       Python environment for P0
#   models/         MediaPipe model files
#   output/         setup reports
# Never uses sudo; does not touch system Python, CUDA, NVIDIA drivers or Blender.
#
# Order:
#   A. Preflight (no downloads): tool check, manifest/constraints consistency, HEAD checks for the uv
#      archive + checksum and both MediaPipe model URLs, exact CPU-only torch wheel lookup.
#   B. Confirmation prompt.
#   C. uv + Python 3.12 + empty venv, then a dry-run resolution compared with the licence manifest.
#      Any unlisted / mismatched / CUDA package stops here, before any package is installed.
#   D. Install, then compare the installed environment with the manifest again.
#   E. MediaPipe models (sizes and SHA-256 recorded).
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
UV_VERSION=0.13.9
UV_TGZ="uv-x86_64-unknown-linux-gnu.tar.gz"
UV_BASE="https://github.com/astral-sh/uv/releases/download/${UV_VERSION}"
FACE_URL="https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
FACE_SIZE=3758596
SEG_URL="https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite"
SEG_SIZE=16371837
PYPI="https://pypi.org/simple"

# keep uv and Python strictly project-local; ignore any user/global uv configuration
export UV_INSTALL_DIR="$ROOT/.tools/uv" UV_PYTHON_INSTALL_DIR="$ROOT/.tools/python" UV_CACHE_DIR="$ROOT/.cache/uv"
export UV_NO_MODIFY_PATH=1 UV_PYTHON_PREFERENCE=only-managed UV_NO_CONFIG=1
unset UV_INDEX_URL UV_EXTRA_INDEX_URL UV_INDEX UV_DEFAULT_INDEX PIP_INDEX_URL PIP_EXTRA_INDEX_URL || true

fail() { echo "STOP: $*" >&2; exit 1; }
TOOLS="python3 scripts/p0_tools.py"

echo "== A. Preflight (no downloads)"
for t in curl tar sha256sum python3 install; do command -v "$t" >/dev/null || fail "required tool '$t' not found"; done
[ "$(uname -m)" = "x86_64" ] || fail "this setup targets x86_64 Linux"
$TOOLS check-sources || fail "licence manifest, constraints-p0.txt and requirements-p0.txt disagree"
echo "-- uv release archive and checksum"
$TOOLS head "$UV_BASE/$UV_TGZ" || fail "uv ${UV_VERSION} archive not available"
$TOOLS head "$UV_BASE/$UV_TGZ.sha256" || fail "uv ${UV_VERSION} checksum file not available"
echo "-- MediaPipe model URLs (exact files and expected sizes)"
$TOOLS head "$FACE_URL" "$FACE_SIZE" || fail "face_landmarker.task unavailable or changed size"
$TOOLS head "$SEG_URL" "$SEG_SIZE" || fail "selfie_multiclass_256x256.tflite unavailable or changed size"
echo "-- CPU-only torch wheel (CPython 3.12, Linux x86-64)"
TORCH_REF="$($TOOLS torch-wheel)" || fail "CPU-only torch 2.15.0 wheel for cp312/x86-64 not found"
echo "   $TORCH_REF"
TORCH_REQ="torch @ ${TORCH_REF}"

cat <<MSG

This will download (approximate sizes):
  uv ${UV_VERSION} standalone binary ............... 17 MB    (MIT OR Apache-2.0)
  CPython 3.12 (project-local) ................... ~30 MB   (PSF-2.0)
  torch 2.15.0+cpu (exact wheel above, hash-pinned) 210 MB   (Apache-2.0/BSD/MIT and other permissive)
  29 PyPI packages pinned in constraints-p0.txt .. ~211 MB  (see docs/licenses/LICENCE_MANIFEST.md)
  MediaPipe face_landmarker.task ................. 3.8 MB   (Apache-2.0)
  MediaPipe selfie_multiclass_256x256.tflite ..... 16.4 MB  (Apache-2.0)
  Total ~0.49 GB download, ~1.3 GB on disk.
Nothing from FLAME is downloaded by this script.
MSG
read -r -p "Proceed with these downloads? [y/N] " ans
[[ "$ans" =~ ^[Yy]$ ]] || { echo "Cancelled. Nothing downloaded."; exit 0; }

echo "== C. uv, Python 3.12, empty environment"
mkdir -p "$UV_INSTALL_DIR" "$UV_PYTHON_INSTALL_DIR" "$UV_CACHE_DIR" models output
UV="$UV_INSTALL_DIR/uv"
if [ ! -x "$UV" ]; then
  TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
  curl -fsSL -o "$TMP/$UV_TGZ" "$UV_BASE/$UV_TGZ"
  curl -fsSL -o "$TMP/$UV_TGZ.sha256" "$UV_BASE/$UV_TGZ.sha256"
  (cd "$TMP" && sha256sum -c "$UV_TGZ.sha256") || fail "uv archive checksum mismatch"
  tar -xzf "$TMP/$UV_TGZ" -C "$TMP"
  install -m 755 "$TMP/uv-x86_64-unknown-linux-gnu/uv" "$UV"
fi
"$UV" --version | grep -q "uv ${UV_VERSION}" || fail "unexpected uv version: $("$UV" --version)"
"$UV" python install 3.12
[ -d .venv-p0 ] || "$UV" venv --python 3.12 .venv-p0
.venv-p0/bin/python -c 'import sys; assert sys.version_info[:2]==(3,12), sys.version; assert sys.prefix.startswith("'"$ROOT"'"), sys.prefix'

INSTALL_ARGS=(--python .venv-p0 --index-url "$PYPI" --constraint constraints-p0.txt "$TORCH_REQ" -r requirements-p0.txt)
echo "-- dry-run resolution (installs nothing)"
"$UV" pip install --dry-run "${INSTALL_ARGS[@]}" 2>&1 | tee output/p0_dry_run.txt
$TOOLS compare output/p0_dry_run.txt --phase dry-run --report output/p0_licence_check_dry_run.txt \
  || fail "resolved package set does not match the licence manifest (nothing has been installed)"

echo "== D. Install"
"$UV" pip install "${INSTALL_ARGS[@]}"
"$UV" pip freeze --python .venv-p0 > output/p0_installed_packages.txt
$TOOLS compare output/p0_installed_packages.txt --phase installed --report output/p0_licence_check_installed.txt \
  || fail "installed environment does not match the licence manifest"
.venv-p0/bin/python - <<'PY'
import torch, numpy, scipy, cv2, mediapipe
print("torch", torch.__version__, "| CUDA build:", torch.version.cuda, "| CUDA available:", torch.cuda.is_available())
print("numpy", numpy.__version__, "| scipy", scipy.__version__, "| cv2", cv2.__version__, "| mediapipe", mediapipe.__version__)
assert torch.__version__ == "2.15.0+cpu", torch.__version__
assert torch.version.cuda is None, "Expected the CPU-only torch build"
PY

echo "== E. MediaPipe models"
fetch() {  # url dest expected_size
  [ -s "$2" ] || curl -fSL -o "$2" "$1"
  [ "$(stat -c %s "$2")" = "$3" ] || fail "$2 has unexpected size $(stat -c %s "$2") (expected $3)"
}
fetch "$FACE_URL" models/face_landmarker.task "$FACE_SIZE"
fetch "$SEG_URL" models/selfie_multiclass_256x256.tflite "$SEG_SIZE"
sha256sum models/face_landmarker.task models/selfie_multiclass_256x256.tflite | tee output/p0_model_hashes.txt

echo
echo "P0 environment ready (CPU-only, project-local)."
echo "Reports: output/p0_dry_run.txt, output/p0_licence_check_dry_run.txt,"
echo "         output/p0_licence_check_installed.txt, output/p0_installed_packages.txt, output/p0_model_hashes.txt"
