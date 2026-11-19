#!/usr/bin/env python3
"""P0 setup safety checks. Standard library only; never installs or downloads packages.

Sub-commands
  check-sources            Manifest allow-list <-> constraints-p0.txt <-> requirements-p0.txt consistency,
                           and every allow-list entry appears in a manifest licence table.
  torch-wheel              Find the exact CPU-only torch wheel for CPython 3.12 / Linux x86-64 on the
                           PyTorch CPU index (reads the index page only) and print "<url>#sha256=<hash>".
  head URL [SIZE]          HTTP HEAD (following redirects); fails unless the final status is 200 and,
                           if SIZE is given, Content-Length equals SIZE.
  compare FILE [--phase]   Compare a package list (uv dry-run output or `uv pip freeze`) with the
                           allow-list. Reports unlisted, missing and version-mismatched packages and
                           any CUDA package. Exit status 1 on any problem.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "docs" / "licenses" / "LICENCE_MANIFEST.md"
CONSTRAINTS = ROOT / "constraints-p0.txt"
REQUIREMENTS = ROOT / "requirements-p0.txt"
TORCH_VERSION = "2.15.0"
TORCH_INDEX = "https://download.pytorch.org/whl/cpu/torch/"
# Exact wheel confirmed 2026-11-19 (209,530,490 bytes; metadata: no CUDA dependencies).
TORCH_WHEEL = "torch-2.15.0+cpu-cp312-cp312-manylinux_2_28_x86_64.whl"
TORCH_SHA256 = "0955c7e3446326293f48af18fad67872fa31dee5a36a87690eb9e5be8b465be3"
FORBIDDEN = re.compile(r"^(nvidia-.*|cuda-.*|triton)$")
UA = {"User-Agent": "c3d-p0-preflight/1.0"}


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_pins(lines) -> dict[str, str]:
    pins = {}
    for raw in lines:
        line = raw.split("#", 1)[0].strip()
        m = re.match(r"^([A-Za-z0-9_.\-]+)\s*==\s*([^\s;]+)$", line)
        if m:
            pins[norm(m.group(1))] = m.group(2)
    return pins


def allow_list() -> dict[str, str]:
    text = MANIFEST.read_text(encoding="utf-8")
    m = re.search(r"```p0-allowed-packages\n(.*?)```", text, re.S)
    if not m:
        sys.exit(f"ERROR: no p0-allowed-packages block in {MANIFEST}")
    return parse_pins(m.group(1).splitlines())


# --------------------------------------------------------------------------- check-sources
def cmd_check_sources(_args) -> int:
    allowed = allow_list()
    text = MANIFEST.read_text(encoding="utf-8")
    tables = text[: text.index("```p0-allowed-packages")]
    problems = []
    for name in allowed:
        # a licence table row must mention the package (names in tables may use '-' or '_')
        if not re.search(rf"\|[^|\n]*\b{re.escape(name)}\b", tables.replace("_", "-").lower()):
            problems.append(f"allow-list entry '{name}' has no row in the manifest licence tables")
    cons = parse_pins(CONSTRAINTS.read_text().splitlines())
    expected = {k: v for k, v in allowed.items() if k != "torch"}
    for k in sorted(set(expected) | set(cons)):
        if expected.get(k) != cons.get(k):
            problems.append(f"constraints-p0.txt mismatch for {k}: manifest={expected.get(k)} constraints={cons.get(k)}")
    reqs = parse_pins(REQUIREMENTS.read_text().splitlines())
    for k, v in reqs.items():
        if allowed.get(k) != v:
            problems.append(f"requirements-p0.txt pins {k}=={v} but manifest allows {allowed.get(k)}")
    if not allowed.get("torch", "").endswith("+cpu"):
        problems.append("manifest must allow only a '+cpu' torch build")
    for p in problems:
        print("PROBLEM:", p)
    print(f"check-sources: {len(allowed)} allowed packages, {len(problems)} problem(s)")
    return 1 if problems else 0


# --------------------------------------------------------------------------- torch-wheel
def cmd_torch_wheel(_args) -> int:
    want = allow_list().get("torch")
    if want != f"{TORCH_VERSION}+cpu":
        sys.exit(f"ERROR: manifest torch pin is {want!r}, expected {TORCH_VERSION}+cpu")
    req = urllib.request.Request(TORCH_INDEX, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            page = r.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: cannot read the PyTorch CPU index {TORCH_INDEX}: {exc}", file=sys.stderr)
        return 1
    hits = []
    for href in re.findall(r'href="([^"]+)"', page):
        href = html.unescape(href)
        url_part, _, frag = href.partition("#")
        fname = urllib.parse.unquote(url_part.rsplit("/", 1)[-1])
        if not fname.startswith(f"torch-{TORCH_VERSION}+cpu-cp312-cp312-"):
            continue
        if not re.search(r"(manylinux[^-]*_x86_64|linux_x86_64)\.whl$", fname):
            continue
        sha = re.search(r"sha256=([0-9a-f]{64})", frag)
        hits.append((fname, urllib.parse.urljoin(TORCH_INDEX, url_part), sha.group(1) if sha else None))
    if not hits:
        print(f"ERROR: no torch-{TORCH_VERSION}+cpu wheel for cp312 Linux x86-64 on {TORCH_INDEX}", file=sys.stderr)
        return 1
    # prefer the manylinux_2_28 build (Ubuntu 22.04 glibc 2.35 satisfies it)
    hits.sort(key=lambda h: ("manylinux_2_28" not in h[0], h[0]))
    fname, url, sha = hits[0]
    if "+cu" in fname or "cuda" in fname.lower():
        print(f"ERROR: selected wheel is not CPU-only: {fname}", file=sys.stderr)
        return 1
    if not sha:
        print(f"ERROR: index gives no sha256 for {fname}; refusing an unverified wheel", file=sys.stderr)
        return 1
    if fname != TORCH_WHEEL or sha != TORCH_SHA256:
        print(f"ERROR: index now offers {fname} sha256={sha}; expected {TORCH_WHEEL} sha256={TORCH_SHA256}. "
              "Stopping so the change can be reviewed.", file=sys.stderr)
        return 1
    print(f"{url}#sha256={sha}")
    print(f"selected: {fname}", file=sys.stderr)
    return 0


# --------------------------------------------------------------------------- head
def cmd_head(args) -> int:
    req = urllib.request.Request(args.url, method="HEAD", headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            code, length = r.status, r.headers.get("Content-Length")
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL  {args.url}  ({exc})")
        return 1
    ok = code == 200 and (args.size is None or str(args.size) == str(length))
    print(f"{'OK  ' if ok else 'FAIL'}  {args.url}  status={code} length={length}"
          + (f" expected={args.size}" if args.size is not None else ""))
    return 0 if ok else 1


# --------------------------------------------------------------------------- compare
def read_package_list(path: Path) -> dict[str, str]:
    pkgs = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        line = re.sub(r"^[+~]\s*", "", line)          # uv dry-run: " + name==ver"
        line = re.sub(r"\s+\(from .*\)$", "", line)   # uv dry-run: "name==ver (from <url>)"
        m = re.match(r"^([A-Za-z0-9_.\-]+)\s*==\s*(\S+)$", line)
        if m:
            pkgs[norm(m.group(1))] = m.group(2)
            continue
        m = re.match(r"^([A-Za-z0-9_.\-]+)\s*@\s*(\S+)$", line)   # direct URL installs
        if m:
            fname = urllib.parse.unquote(m.group(2).split("#")[0].rsplit("/", 1)[-1])
            v = re.match(rf"^{re.escape(m.group(1).replace('-', '_'))}-([^-]+)-", fname, re.I)
            pkgs[norm(m.group(1))] = v.group(1) if v else "url"
    return pkgs


def cmd_compare(args) -> int:
    allowed = allow_list()
    got = read_package_list(Path(args.file))
    unlisted = sorted(k for k in got if k not in allowed)
    missing = sorted(k for k in allowed if k not in got)
    mismatched = sorted(k for k in got if k in allowed and got[k] != allowed[k])
    forbidden = sorted(k for k in got if FORBIDDEN.match(k))
    lines = [f"Licence manifest comparison ({args.phase}) against {MANIFEST.relative_to(ROOT)}",
             f"  packages found:      {len(got)}",
             f"  allowed by manifest: {len(allowed)}"]
    for title, items in (("UNLISTED (not in manifest, licence unverified)", unlisted),
                         ("VERSION MISMATCH", [f"{k}: found {got[k]}, manifest {allowed[k]}" for k in mismatched]),
                         ("CUDA / GPU PACKAGES (forbidden in P0)", forbidden),
                         ("MISSING (in manifest, not present)", missing)):
        lines.append(f"  {title}: {len(items)}")
        lines += [f"    - {i}" for i in items]
    failed = bool(unlisted or mismatched or forbidden or (missing and args.phase == "installed"))
    lines.append("RESULT: " + ("FAIL" if failed else "PASS")
                 + ("" if args.phase == "installed" or not missing else "  (missing entries are reported only at the dry-run stage)"))
    report = "\n".join(lines)
    print(report)
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(report + "\n")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check-sources").set_defaults(fn=cmd_check_sources)
    sub.add_parser("torch-wheel").set_defaults(fn=cmd_torch_wheel)
    h = sub.add_parser("head"); h.add_argument("url"); h.add_argument("size", nargs="?"); h.set_defaults(fn=cmd_head)
    c = sub.add_parser("compare"); c.add_argument("file")
    c.add_argument("--phase", choices=["dry-run", "installed"], required=True)
    c.add_argument("--report"); c.set_defaults(fn=cmd_compare)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
