"""`loom ai promote PATH` (book 11.7): copy a digest out of a run into `digests/`; never touch the run's file.

A drafted node is not promoted: the author previews it in arras and pastes it where they decide, taking an id from `loom id --next` (DR-140).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from loom.scan.scan import ScanResult

_DIGEST = re.compile(r"^%\s*!LOOM\s+digest:\s*(\S+)", re.M)

NODE_REFUSAL = (
    "promote copies digests only; preview a suggested node in arras and paste it, with an id from loom id --next"
)


@dataclass
class Promotion:
    kind: str  # digest
    target: str  # quilt-relative
    text: str


def plan_promotion(result: ScanResult, path: Path) -> Promotion:
    text = path.read_text(encoding="utf-8")
    m = _DIGEST.search(text)
    if m is None:
        if path.name.startswith("ingest-"):
            raise ValueError(f"{path.name} has no `% !LOOM digest:` header")
        raise ValueError(NODE_REFUSAL)
    return Promotion("digest", f"digests/{m.group(1)}.tex", text)


def write_promotion(root: Path, plan: Promotion, replace: bool) -> Path:
    dest = root / plan.target
    if dest.exists() and not replace:
        raise FileExistsError(str(dest))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(plan.text, encoding="utf-8")
    return dest
