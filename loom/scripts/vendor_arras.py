#!/usr/bin/env python3
"""Replace src/loom/assets/arras with a built arras bundle and stamp VERSION.

Usage: scripts/vendor_arras.py ../arras/build [--arras-dir ../arras] [--allow-dirty]. Refuses if arras's interface version (read from its src/lib/manifest/types.ts) differs from loom's INTERFACE_VERSION, so a loom clone never ships a viewer that misrenders its own manifests, and refuses when arras has uncommitted changes unless `--allow-dirty` is given, in which case VERSION names the commit with `-dirty`. Everything in the target but README.md is removed first, so no chunk of an earlier build survives. `scripts/checks/bundle.py` at the workspace root checks the result.
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


def arras_dirty(arras_dir: Path) -> bool:
    """Whether arras's tracked or untracked-and-not-ignored files differ from its HEAD; the build output is ignored."""
    try:
        return bool(
            subprocess.run(
                ["git", "-C", str(arras_dir), "status", "--porcelain", "--", "."],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
    except (OSError, subprocess.CalledProcessError):
        return False


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("build_dir", type=Path, help="arras build output (contains index.html)")
    ap.add_argument("--arras-dir", type=Path, default=None, help="arras checkout (default: parent of build_dir)")
    ap.add_argument(
        "--allow-dirty", action="store_true", help="vendor from uncommitted arras changes, stamping VERSION -dirty"
    )
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
    dirty = arras_dirty(arras_dir)
    if dirty and not args.allow_dirty:
        print(
            f"error: {arras_dir} has uncommitted changes, so VERSION could not name the commit this bundle is built from;"
            " commit them, or pass --allow-dirty to vendor anyway and stamp it -dirty",
            file=sys.stderr,
        )
        return 2
    for child in TARGET.iterdir():
        if child.name in KEEP:
            continue
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    shutil.copytree(build, TARGET, dirs_exist_ok=True, ignore=shutil.ignore_patterns("build"))
    commit = arras_commit(arras_dir) + ("-dirty" if dirty else "")
    stamp = f"arras {commit} interface {mine} vendored {datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
    (TARGET / "VERSION").write_text(stamp, encoding="utf-8")
    print(f"vendored {build} -> {TARGET}\n{stamp.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
