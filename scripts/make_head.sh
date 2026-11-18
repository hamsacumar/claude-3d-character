#!/usr/bin/env bash
# ONE FACE PHOTO -> 3D HEAD -> TEXTURED BLENDER PROJECT -> opens in Blender.
#
#   scripts/make_head.sh photo.jpg [--out DIR] [--no-open] [--render]
#
#   --render   also render preview_front/threequarter/profile.png with Cycles (slower)
#   --no-open  only create the .blend, don't launch the Blender UI
set -euo pipefail
cd "$(dirname "$0")/.."
BLENDER="${BLENDER:-/usr/local/bin/blender}"

[ $# -ge 1 ] || { sed -n '2,8p' "$0"; exit 1; }
PHOTO="$1"; shift
NAME="$(basename "${PHOTO%.*}")"
OUT="output/$NAME"; OPEN=1; RENDER=""
while [ $# -gt 0 ]; do
  case "$1" in
    --out) OUT="$2"; shift 2;;
    --no-open) OPEN=0; shift;;
    --render) RENDER="--render"; shift;;
    *) echo "unknown option $1"; exit 1;;
  esac
done
[ -x .venv/bin/python ] || { echo "Run scripts/setup.sh first"; exit 1; }

echo "== 1/3 Analyzing photo and reconstructing head"
GLOG_minloglevel=2 .venv/bin/python c3d/reconstruct.py "$PHOTO" --out "$OUT"

echo "== 2/3 Building Blender project"
"$BLENDER" -b --factory-startup --python c3d/blender_build.py -- --job "$OUT/job.json" $RENDER 2>&1 \
  | grep -E "Saved|Error|ERROR|WARNING|Traceback" || true
[ -f "$OUT/head.blend" ] || { echo "Blender build failed (run the blender command above without the grep to see why)"; exit 1; }

echo "== 3/3 Done: $OUT/head.blend   (analysis: $OUT/analysis.json)"
if [ "$OPEN" = 1 ]; then
  echo "Opening Blender..."
  nohup "$BLENDER" "$OUT/head.blend" >/dev/null 2>&1 &
fi
