#!/usr/bin/env python3
"""The vendored arras bundle is complete, committable and built for loom's interface (plan 0.14.1 phase 4).

Usage:
    scripts/checks/bundle.py

Fails when a file `index.html` needs is missing or git-ignored, or when `VERSION`'s interface differs from loom's `INTERFACE_VERSION`. Needed means `index.html`'s own links and imports, then transitively every file a module loads (static and dynamic imports, Vite's preload lists, `new URL(..., import.meta.url)` assets) or a stylesheet's `url(...)` names, and the pdf.js data directories. Warns, without failing, when a needed file is untracked, when `VERSION` is stamped `-dirty`, or when arras's sources have commits the stamped one lacks: the author vendors before committing. Exit 0 or 1.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "loom" / "src" / "loom" / "assets" / "arras"
VERSION_PY = ROOT / "loom" / "src" / "loom" / "version.py"
VENDOR = "cd arras && npm run build && cd ../loom && uv run python scripts/vendor_arras.py ../arras/build"

# the stamp is judged by the function `loom doctor` uses, which is standard library only
sys.path.insert(0, str(ROOT / "loom" / "src"))
from loom.arras_bundle import parse_stamp, staleness  # noqa: E402

Q = r"""["'`]"""
PATH = r"""((?:\.{1,2}|/_app)/[^"'`\s]+)"""
# only the forms that load a file: a string a bundled library merely carries (a module-map key, a fallback worker name) is not a need
LOADS = [
    re.compile(r"(?:\bfrom|\bimport)\s*" + Q + PATH + Q),  # static import and re-export
    re.compile(r"\bimport\(\s*" + Q + PATH + Q + r"\s*\)"),  # dynamic import
    re.compile(r"\bnew URL\(\s*" + Q + PATH + Q + r"\s*,\s*import\.meta\.url"),  # an asset beside the module
    re.compile(r"""\b(?:href|src)=["'](/_app/[^"']+)["']"""),  # index.html's links and scripts
]
MAP_DEPS = re.compile(r"__vite__mapDeps=.*?m\.f=\[([^\]]*)\]")  # Vite's preload list, relative to the module
CSS_URL = re.compile(r"""url\(\s*["']?(?!data:|https?:|#)([^"')\s]+)["']?\s*\)""")
PDFJS_DIR = re.compile(r"/pdfjs/([A-Za-z_]+)/")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False).stdout


def needed() -> tuple[set[Path], set[Path]]:
    """Every file the entry page reaches, and every pdf.js data directory a module names."""
    files: set[Path] = set()
    dirs: set[Path] = set()
    queue = [BUNDLE / "index.html"]
    while queue:
        page = queue.pop()
        if page in files:
            continue
        files.add(page)
        if not page.is_file() or page.suffix not in (".html", ".js", ".mjs", ".css"):
            continue
        text = page.read_text(encoding="utf-8", errors="replace")
        names = [m for pattern in LOADS for m in pattern.findall(text)]
        for deps in MAP_DEPS.findall(text):
            names += re.findall(r"""["'`]([^"'`]+)["'`]""", deps)
        if page.suffix == ".css":
            names += CSS_URL.findall(text)
        refs = [BUNDLE / n.lstrip("/") if n.startswith("/") else page.parent / n for n in names]
        dirs |= {BUNDLE / "pdfjs" / d for d in PDFJS_DIR.findall(text)}
        queue += [Path(*r.parts).resolve() for r in refs]
    return files, dirs


def interface_of(text: str, pattern: str) -> int | None:
    m = re.search(pattern, text, re.M)
    return int(m.group(1)) if m else None


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    version_file = BUNDLE / "VERSION"
    stamp = version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else ""
    stamped = parse_stamp(stamp)
    loom_iface = interface_of(VERSION_PY.read_text(encoding="utf-8"), r"^INTERFACE_VERSION\s*=\s*(\d+)")
    if stamped is None:
        errors.append(f"VERSION is {stamp!r}, not `arras <commit> interface <n> vendored <time>`")
    else:
        commit, iface = stamped
        if iface != loom_iface:
            errors.append(f"VERSION says interface {iface}; loom's INTERFACE_VERSION is {loom_iface}")
        warnings += [f"the bundle is {why}; vendor again once arras is committed" for why in staleness(ROOT, commit)]

    files, dirs = needed()
    rel = sorted(str(f.relative_to(ROOT)) for f in files if f.is_relative_to(ROOT))
    outside = sorted(str(f) for f in files if not f.is_relative_to(ROOT) or not f.is_relative_to(BUNDLE))
    errors += [f"index.html reaches {p}, outside the bundle" for p in outside]
    errors += [f"{p} is needed and missing" for p in rel if not (ROOT / p).is_file()]
    errors += [
        f"{d.relative_to(ROOT)}/ is named by a module and is missing or empty"
        for d in sorted(dirs)
        if not any(d.glob("*"))
    ]
    present = [p for p in rel if (ROOT / p).is_file()]
    for d in dirs:
        present += [str(f.relative_to(ROOT)) for f in d.rglob("*") if f.is_file()]
    if present:
        ignored = set(git("ls-files", "--others", "--ignored", "--exclude-standard", "--", *present).splitlines())
        untracked = set(git("ls-files", "--others", "--exclude-standard", "--", *present).splitlines())
        errors += [f"{p} is needed and git-ignored, so no commit can carry it" for p in sorted(ignored)]
        if untracked:
            warnings.append(
                f"{len(untracked)} needed files are untracked, e.g. {sorted(untracked)[0]}; `git add loom/src/loom/assets/arras` before committing"
            )

    for w in warnings:
        print(f"warn: {w}")
    for e in errors[:20]:
        print(e)
    if len(errors) > 20:
        print(f"... and {len(errors) - 20} more")
    if errors:
        print(f"fix: {VENDOR}")
        return 1
    note = f", {len(warnings)} warning{'s' if len(warnings) != 1 else ''}" if warnings else ""
    print(f"bundle: ok ({len(files)} files reached from index.html{note})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
