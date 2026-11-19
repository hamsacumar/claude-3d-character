#!/usr/bin/env bash
# Photo -> 3D head (no FLAME). Uses the existing project-local P0 environment and MediaPipe model.
#
#   scripts/make_head_v1.sh ~/Pictures/face.jpeg [--out DIR] [--use-cycles] [--depth-scale 1.0] [--no-open]
#
# Writes to output/head_v1/<photo name>/ by default:
#   00_reference.*, landmarks_overlay.png, analysis.json      (photo analysis)
#   head.blend, head_report.json                              (Blender 4.5 project)
#   01_front.png, 02_threequarter.png, 03_side.png, 04_sheet.png   (renders)
# Then opens head.blend in Blender. Downloads nothing; installs nothing.
set -euo pipefail
cd "$(dirname "$0")/.."
BLENDER="${BLENDER:-/usr/local/bin/blender}"
PY=.venv-p0/bin/python
[ $# -ge 1 ] || { sed -n '2,11p' "$0"; exit 1; }
PHOTO="$1"; shift
OUT="output/head_v1/$(basename "${PHOTO%.*}")"; OPEN=1; ENGINE=""; DEPTH=1.0
while [ $# -gt 0 ]; do
  case "$1" in
    --out) OUT="$2"; shift 2;;
    --use-cycles) ENGINE="--use-cycles"; shift;;
    --depth-scale) DEPTH="$2"; shift 2;;
    --no-open) OPEN=0; shift;;
    *) echo "unknown option: $1"; exit 1;;
  esac
done
[ -x "$PY" ] || { echo "Missing $PY (run scripts/setup_p0.sh)"; exit 1; }
[ -f models/face_landmarker.task ] || { echo "Missing models/face_landmarker.task"; exit 1; }
[ -f "$PHOTO" ] || { echo "Photo not found: $PHOTO"; exit 1; }
[ -x "$BLENDER" ] || { echo "Blender not found at $BLENDER (set BLENDER=...)"; exit 1; }

echo "== 1/3 Photo analysis (MediaPipe Face Landmarker)"
GLOG_minloglevel=2 "$PY" c3d/head_v1/analyze.py "$PHOTO" --out "$OUT" --depth-scale "$DEPTH"

echo "== 2/3 Building the head in Blender and rendering front / three-quarter / side"
"$BLENDER" -b --factory-startup --python c3d/head_v1/build_blend.py -- --dir "$OUT" --render $ENGINE 2>&1 \
  | grep -E "^Saved|Error|Traceback|File \"" || true
[ -f "$OUT/head.blend" ] || { echo "Blender build failed; rerun without the grep to see the log:"; \
  echo "  $BLENDER -b --factory-startup --python c3d/head_v1/build_blend.py -- --dir $OUT --render"; exit 1; }

"$PY" - "$OUT" <<'PY'
import sys, glob, cv2, numpy as np
out = sys.argv[1]
ims = [cv2.imread(f"{out}/{n}.png") for n in ("01_front", "02_threequarter", "03_side")]
ims = [i for i in ims if i is not None]
ref = cv2.imread(glob.glob(f"{out}/00_reference.*")[0])
if ims and ref is not None:
    h = ims[0].shape[0]
    ref = cv2.resize(ref, (int(ref.shape[1] * h / ref.shape[0]), h))
    cv2.imwrite(f"{out}/04_sheet.png", np.hstack([ref] + ims))
PY

echo "== 3/3 Done: $OUT/head.blend"
echo "   renders: $OUT/01_front.png $OUT/02_threequarter.png $OUT/03_side.png  sheet: $OUT/04_sheet.png"
echo "   report:  $OUT/head_report.json  analysis: $OUT/analysis.json"
if [ "$OPEN" = 1 ]; then nohup "$BLENDER" "$OUT/head.blend" >/dev/null 2>&1 & echo "Opening Blender..."; fi
