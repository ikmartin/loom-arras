"""Locate the built arras bundle that `loom serve` serves at /.

Lookup order: LOOM_ARRAS_BUNDLE, the optional `arras` pip package, the copy vendored under loom/assets/arras by scripts/vendor_arras.py. The vendored copy is what makes a bare clone of the loom repository sufficient.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from importlib import resources
from pathlib import Path


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


def find_bundle() -> BundleInfo | None:
    env = os.environ.get("LOOM_ARRAS_BUNDLE")
    if env:
        p = Path(env).expanduser()
        if _valid(p):
            return BundleInfo(p, "LOOM_ARRAS_BUNDLE", _read_version(p))
    try:
        import arras  # type: ignore[import-not-found]

        p = Path(str(arras.bundle_path()))
        if _valid(p):
            return BundleInfo(p, "arras package", _read_version(p))
    except (ImportError, AttributeError):
        pass
    vendored = Path(str(resources.files("loom") / "assets" / "arras"))
    if _valid(vendored):
        return BundleInfo(vendored, "vendored", _read_version(vendored))
    return None
