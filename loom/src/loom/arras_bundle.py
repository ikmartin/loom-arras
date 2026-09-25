"""Locate the built arras bundle that `loom serve` serves at /, and read what its `VERSION` stamp says.

Lookup order: LOOM_ARRAS_BUNDLE, the optional `arras` pip package, the copy vendored under loom/assets/arras by scripts/vendor_arras.py. The vendored copy is what makes a bare clone of the loom repository sufficient. The stamp helpers are shared by `loom doctor` and the workspace's `scripts/checks/bundle.py`, so both judge a vendored bundle alike; they use the standard library only, since that check imports them without loom's environment.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

#: The arras paths a build reads; a commit touching only tests or docs leaves the bundle current.
BUILD_INPUTS = (
    "arras/src",
    "arras/static",
    "arras/package.json",
    "arras/package-lock.json",
    "arras/svelte.config.js",
    "arras/vite.config.ts",
)
#: What `scripts/vendor_arras.py` writes into `VERSION`.
STAMP = re.compile(r"arras (\S+) interface (\d+) vendored \S+")


@dataclass(frozen=True)
class BundleInfo:
    path: Path
    source: str
    version: str


def _read_version(path: Path) -> str:
    v = path / "VERSION"
    return v.read_text(encoding="utf-8").strip().splitlines()[0] if v.exists() else "unversioned"


def _valid(path: Path) -> bool:
    return (path / "index.html").is_file()


def vendored_path() -> Path:
    """Where the vendored copy lives inside the installed loom."""
    return Path(str(resources.files("loom") / "assets" / "arras"))


class BundleEnvError(Exception):
    """LOOM_ARRAS_BUNDLE is set and names no bundle; the message says what is wrong with it."""


def env_problem() -> str | None:
    """What is wrong with LOOM_ARRAS_BUNDLE when it is set and names no bundle, or None."""
    env = os.environ.get("LOOM_ARRAS_BUNDLE")
    if not env or _valid(Path(env).expanduser()):
        return None
    p = Path(env).expanduser()
    return f"LOOM_ARRAS_BUNDLE={env} " + ("has no index.html" if p.is_dir() else "is not a directory")


def find_bundle() -> BundleInfo | None:
    """The bundle `loom serve` serves, or None when there is none.

    A set LOOM_ARRAS_BUNDLE is the person's choice of viewer, so one that names no bundle raises BundleEnvError rather than falling through to another source: a fallback would serve a viewer nobody asked for, and a suite pointed at a fresh build would pass against the old one.
    """
    env = os.environ.get("LOOM_ARRAS_BUNDLE")
    if env:
        p = Path(env).expanduser()
        if _valid(p):
            return BundleInfo(p, "LOOM_ARRAS_BUNDLE", _read_version(p))
        raise BundleEnvError(env_problem() or f"LOOM_ARRAS_BUNDLE={env} names no bundle")
    try:
        import arras  # type: ignore[import-not-found]

        p = Path(str(arras.bundle_path()))
        if _valid(p):
            return BundleInfo(p, "arras package", _read_version(p))
    except (ImportError, AttributeError):
        pass
    vendored = vendored_path()
    if _valid(vendored):
        return BundleInfo(vendored, "vendored", _read_version(vendored))
    return None


def parse_stamp(version: str) -> tuple[str, int] | None:
    """The arras commit and interface version a `VERSION` line names; None when it is not a vendoring stamp."""
    m = STAMP.fullmatch(version.strip())
    return (m.group(1), int(m.group(2))) if m else None


def checkout_of(bundle: Path) -> Path | None:
    """The workspace root when `bundle` is the copy vendored inside a loom-arras checkout (`<root>/loom/src/loom/assets/arras`, with `<root>/arras` beside it); None for an installed loom."""
    parts = bundle.resolve().parents
    if len(parts) < 5:
        return None
    root = parts[4]
    return root if (root / "arras" / "package.json").is_file() and (root / ".git").exists() else None


def staleness(root: Path, commit: str, timeout: float = 10.0) -> list[str]:
    """Why a bundle stamped `commit` is older than the checkout at `root`'s arras: a `-dirty` stamp, or a commit touching BUILD_INPUTS that the stamped one lacks.

    Empty when neither holds or git cannot tell; every git call is bounded by `timeout`.
    """
    out: list[str] = []
    if commit.endswith("-dirty"):
        out.append(f"stamped {commit}: vendored from uncommitted arras changes")
        commit = commit.removesuffix("-dirty")

    def git(*args: str) -> subprocess.CompletedProcess[str] | None:
        try:
            return subprocess.run(
                ["git", *args], cwd=root, capture_output=True, text=True, timeout=timeout, check=False
            )
        except (OSError, subprocess.SubprocessError):
            return None

    log = git("log", "-1", "--format=%H", "--", *BUILD_INPUTS)
    last = log.stdout.strip() if log is not None and log.returncode == 0 else ""
    if last:
        behind = git("merge-base", "--is-ancestor", last, commit)
        if behind is not None and behind.returncode == 1:
            out.append(f"built from {commit}, but arras's sources changed in {last[:7]}")
        elif behind is not None and behind.returncode != 0:
            out.append(f"stamped with {commit}, which this repository does not have")
    return out
