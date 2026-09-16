#!/usr/bin/env python3
"""Copy a built arras bundle into src/loom/assets/arras and stamp VERSION.

Usage: scripts/vendor_arras.py ../arras/build [--arras-dir ../arras]. Refuses if arras's interface version (read from its src/lib/manifest/types.ts) differs from loom's INTERFACE_VERSION, so a loom clone never ships a viewer that misrenders its own manifests.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE.parent / "src" / "loom" / "assets" / "arras"
KEEP = {"README.md"}


def loom_interface_version() -> int:
    text = (HERE.parent / "src" / "loom" / "version.py").read_text(encoding="utf-8")
    m = re.search(r"^INTERFACE_VERSION\s*=\s*(\d+)", text, re.M)
    return int(m.group(1)) if m else 1


def arras_interface_version(arras_dir: Path) -> int | None:
    types = arras_dir / "src" / "lib" / "manifest" / "types.ts"
    if not types.exists():
        return None
    m = re.search(r"INTERFACE_VERSION\s*=\s*(\d+)", types.read_text(encoding="utf-8"))
    return int(m.group(1)) if m else None


def arras_commit(arras_dir: Path) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(arras_dir), "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("build_dir", type=Path, help="arras build output (contains index.html)")
    ap.add_argument("--arras-dir", type=Path, default=None, help="arras checkout (default: parent of build_dir)")
    args = ap.parse_args(argv)
    build = args.build_dir.resolve()
    arras_dir = (args.arras_dir or build.parent).resolve()
    if not (build / "index.html").is_file():
        print(f"error: {build} has no index.html; run `npm run build` in arras first", file=sys.stderr)
        return 2
    mine, theirs = loom_interface_version(), arras_interface_version(arras_dir)
    if theirs is not None and theirs != mine:
        print(f"error: arras produces interface version {theirs}, loom expects {mine}", file=sys.stderr)
        return 2
    for child in TARGET.iterdir():
        if child.name in KEEP:
            continue
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    shutil.copytree(build, TARGET, dirs_exist_ok=True)
    stamp = f"arras {arras_commit(arras_dir)} interface {mine} vendored {datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
    (TARGET / "VERSION").write_text(stamp, encoding="utf-8")
    print(f"vendored {build} -> {TARGET}\n{stamp.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
