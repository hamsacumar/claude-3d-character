#!/usr/bin/env bash
# Read-only inspection of FLAME2023Open.zip. Extracts NOTHING to disk.
# Prints: archive hash, file list, SHA-256 of every member (streamed), and the full
# text of any licence/readme files inside the archive. Paste the output back to Claude.
set -euo pipefail
ZIP="${1:-third_party/flame2023_open/FLAME2023Open.zip}"
[ -f "$ZIP" ] || { echo "Not found: $ZIP"; exit 1; }
echo "== Archive"; ls -l "$ZIP"; sha256sum "$ZIP"
echo "== Listing"; unzip -l "$ZIP"
echo "== Integrity test (no extraction)"; unzip -tq "$ZIP"
echo "== SHA-256 per member (streamed, not written to disk)"
unzip -Z1 "$ZIP" | while IFS= read -r m; do
  case "$m" in */) continue;; esac
  printf '%s  %s\n' "$(unzip -p "$ZIP" "$m" | sha256sum | cut -d' ' -f1)" "$m"
done
echo "== Text documents inside the archive (licence/readme/notice), printed in full"
unzip -Z1 "$ZIP" | grep -iE '(licen[cs]e|readme|notice|copying|terms)[^/]*$|\.(txt|md)$' | while IFS= read -r m; do
  echo "----- BEGIN $m"; unzip -p "$ZIP" "$m" | head -c 200000; echo; echo "----- END $m"
done
echo "== Python pickle members: modules the pickle would import (disassembled only, never loaded)"
unzip -Z1 "$ZIP" | grep -iE '\.pkl$' | while IFS= read -r m; do
  echo "--- $m"
  unzip -p "$ZIP" "$m" | python3 -I -c '
import pickletools, sys, io
data = sys.stdin.buffer.read()
# Disassemble only (never unpickle): list global references the pickle would import.
globs = set(); last = []
for op, arg, pos in pickletools.genops(io.BytesIO(data)):
    if op.name in ("SHORT_BINUNICODE","BINUNICODE","UNICODE","STRING","BINSTRING","SHORT_BINSTRING"):
        last.append(arg); last = last[-2:]
    if op.name == "GLOBAL": globs.add(arg.replace(" ", "."))
    if op.name == "STACK_GLOBAL" and len(last) == 2: globs.add(".".join(map(str, last)))
print("bytes:", len(data)); print("imports referenced:", sorted(globs))
' || echo "(could not disassemble)"
done
