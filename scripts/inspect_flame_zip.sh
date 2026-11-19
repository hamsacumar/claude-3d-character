#!/usr/bin/env bash
# Read-only inspection of FLAME2023Open.zip. Extracts NOTHING to disk and loads no model.
# Every member is only streamed through hash/type/disassembly tools in memory.
#
#   scripts/inspect_flame_zip.sh [path/to/FLAME2023Open.zip]
#
# Output is printed and saved to output/flame_inspection_<UTC timestamp>.txt.
# Send that file (or the printed output) back to Claude for the licence review.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
ZIP="${1:-third_party/flame2023_open/FLAME2023Open.zip}"
[ -f "$ZIP" ] || { echo "Not found: $ZIP"; exit 1; }
for t in unzip sha256sum file python3; do command -v "$t" >/dev/null || { echo "Missing tool: $t"; exit 1; }; done
mkdir -p output
OUT="output/flame_inspection_$(date -u +%Y%m%dT%H%M%SZ)_$$.txt"
exec > >(tee "$OUT") 2>&1

echo "# FLAME2023Open.zip inspection ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
echo "Nothing is extracted to disk; no model is loaded."
echo
echo "== 1. Archive"
ls -l "$ZIP"
sha256sum "$ZIP"
file -b "$ZIP"

echo
echo "== 2. Integrity test (CRC check of every member, in memory)"
if unzip -tq "$ZIP"; then echo "INTEGRITY: OK"; else echo "INTEGRITY: FAILED, stop the review"; fi

echo
echo "== 3. Listing (verbose: permissions, sizes, compression, dates)"
unzip -Zl "$ZIP"

echo
echo "== 4. Safety checks"
python3 -I - "$ZIP" <<'PY'
import sys, zipfile, stat
z = zipfile.ZipFile(sys.argv[1])
issues = 0
total = 0
for i in z.infolist():
    total += i.file_size
    name = i.filename
    mode = (i.external_attr >> 16) & 0o177777
    flags = []
    if name.startswith("/") or ".." in name.split("/"): flags.append("PATH TRAVERSAL")
    if stat.S_ISLNK(mode): flags.append("SYMLINK")
    if i.flag_bits & 0x1: flags.append("ENCRYPTED")
    if name.lower().endswith((".zip", ".tar", ".gz", ".tgz", ".7z", ".rar", ".bz2", ".xz")): flags.append("NESTED ARCHIVE")
    if i.compress_size and i.file_size / i.compress_size > 200: flags.append("EXTREME COMPRESSION RATIO")
    if flags:
        issues += 1
        print(f"  {name}: {', '.join(flags)}")
print(f"  members: {len(z.infolist())}, total uncompressed: {total/1e6:.1f} MB")
print("SAFETY:", "OK" if not issues else f"{issues} member(s) flagged, stop the review")
PY

echo
echo "== 5. Per-member SHA-256 and detected type (streamed, not written to disk)"
unzip -Z1 "$ZIP" | while IFS= read -r m; do
  case "$m" in */) continue;; esac
  h="$(unzip -p "$ZIP" "$m" | sha256sum | cut -d' ' -f1)"
  ty="$(unzip -p "$ZIP" "$m" | head -c 65536 | file -b - | cut -c1-70)"
  printf '%s  %s  [%s]\n' "$h" "$m" "$ty"
done

echo
echo "== 6. Licence / readme / notice documents inside the archive (full text)"
found=0
while IFS= read -r m; do
  found=1
  echo "----- BEGIN $m"; unzip -p "$ZIP" "$m" | head -c 200000; echo; echo "----- END $m"
done < <(unzip -Z1 "$ZIP" | grep -iE '(licen[cs]e|readme|notice|copying|terms|citation|attribution)[^/]*$|\.(txt|md|rst)$')
[ "$found" = 1 ] || echo "(no licence/readme/text documents found inside the archive)"

echo
echo "== 7. Pickle members: modules the pickle would import (disassembled only, never unpickled)"
while IFS= read -r m; do
  echo "--- $m"
  unzip -p "$ZIP" "$m" | python3 -I -c '
import io, pickletools, sys
data = sys.stdin.buffer.read()
strings, globs = [], set()
for op, arg, pos in pickletools.genops(io.BytesIO(data)):
    if isinstance(arg, str) and op.name.endswith(("UNICODE", "STRING")):
        strings = (strings + [arg])[-2:]
    if op.name == "GLOBAL":
        globs.add(arg.replace(" ", "."))
    elif op.name == "STACK_GLOBAL" and len(strings) == 2:
        globs.add(".".join(strings))
expected = ("numpy", "scipy.sparse", "chumpy", "collections.OrderedDict", "_codecs.encode", "copy_reg._reconstructor", "copyreg._reconstructor", "__builtin__.object", "builtins.object")
unexpected = sorted(g for g in globs if not g.startswith(expected))
print("  bytes:", len(data))
print("  imports referenced:", sorted(globs))
print("  UNEXPECTED imports (would execute other code if unpickled):", unexpected or "none")
' || echo "  (could not disassemble: treat as unsafe)"
done < <(unzip -Z1 "$ZIP" | grep -iE '\.(pkl|pickle|p)$')

echo
echo "== 8. NumPy archives (.npz): member names only (no arrays loaded)"
while IFS= read -r m; do
  echo "--- $m"
  unzip -p "$ZIP" "$m" | python3 -I -c '
import io, sys, zipfile
z = zipfile.ZipFile(io.BytesIO(sys.stdin.buffer.read()))
for i in z.infolist(): print(f"  {i.filename}  {i.file_size} bytes")
' || echo "  (could not list)"
done < <(unzip -Z1 "$ZIP" | grep -iE '\.npz$')

echo
echo "== Done. Saved to $OUT"
