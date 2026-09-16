"""The arras viewer bundle as a Python package: `bundle_path()` is the directory `loom serve` (or any static server) serves at /."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

__version__ = "0.1.0a0"


def bundle_path() -> Path:
    """Directory containing the built viewer's index.html."""
    return Path(str(resources.files("arras") / "bundle"))
