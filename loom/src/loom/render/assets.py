"""Graphics for fragments: PDF figures become SVG (pdftocairo, else dvisvgm --pdf), raster images are copied; everything lands content-addressed under build/svg/ (book 9.4.1)."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path


def _digest(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()[:16]


def resolve_graphic(root: Path, name: str) -> Path | None:
    name = name.strip()
    for cand in (name, name + ".pdf", name + ".png", name + ".jpg", name + ".jpeg", name + ".svg"):
        p = root / cand
        if p.is_file():
            return p
    return None


def publish_graphic(root: Path, name: str, svg_dir: Path) -> tuple[str | None, str | None]:
    """Return (relative asset path under build/, error). PDF -> SVG conversion, PNG/JPEG/SVG copied."""
    src = resolve_graphic(root, name)
    if src is None:
        return None, f"graphic {name} not found"
    svg_dir.mkdir(parents=True, exist_ok=True)
    stamp = _digest(src)
    if src.suffix.lower() in (".png", ".jpg", ".jpeg", ".svg"):
        out = svg_dir / f"{stamp}{src.suffix.lower()}"
        if not out.exists():
            shutil.copy(src, out)
        return f"svg/{out.name}", None
    out = svg_dir / f"{stamp}.svg"
    if out.exists():
        return f"svg/{out.name}", None
    pdftocairo = shutil.which("pdftocairo")
    if pdftocairo:
        proc = subprocess.run(
            [pdftocairo, "-svg", str(src), str(out)], capture_output=True, text=True, errors="replace", check=False
        )
        if proc.returncode == 0 and out.exists():
            return f"svg/{out.name}", None
    dvisvgm = shutil.which("dvisvgm")
    if dvisvgm:
        proc = subprocess.run(
            [dvisvgm, "--pdf", "--no-fonts", f"--output={out}", str(src)],
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
        )
        if proc.returncode == 0 and out.exists():
            return f"svg/{out.name}", None
    return None, f"could not convert {name} to SVG (pdftocairo or dvisvgm --pdf needed)"
