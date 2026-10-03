"""What a rendering's cache key is made of beyond its own text: loom's version and rendering code, and the numbering read from the compiled documents.

Shared by the fragment cache (`build._input_hash`), the review previews (`review_compare._render`) and the comparison cache (`compare._cached`), so a converter change or a renumbering reaches all three alike.
"""

from __future__ import annotations

import hashlib
from functools import cache
from pathlib import Path

from loom.tex.aux import AuxNumber
from loom.version import __version__

#: The packages a rendering's output depends on; editing anything else in a checkout re-renders nothing.
RENDERING = ("render", "scan", "tex")


@cache
def code_hash() -> str:
    """A fingerprint of loom's rendering code, or '' for a released version, which its version string already identifies.

    In a checkout the version stays `0.1.0.dev0` across every edit, so a changed converter would otherwise hit the cache and republish the HTML it was meant to replace. Only `RENDERING`'s modules count, so editing the command line or the reference layer re-renders nothing. Read once per process, since a served quilt rebuilds on every keystroke.
    """
    if "dev" not in __version__:
        return ""
    package = Path(__file__).resolve().parent.parent
    h = hashlib.sha256()
    for sub in RENDERING:
        for path in sorted((package / sub).rglob("*.py")):
            h.update(path.relative_to(package).as_posix().encode())
            h.update(path.read_bytes())
    return h.hexdigest()[:16]


def aux_bytes(numbers: dict[str, dict[str, AuxNumber]], cite_labels: dict[str, dict[str, str]]) -> bytes:
    """Every master's number table and citation labels as one byte stream, serialised once per build rather than once per node."""
    parts: list[str] = []
    for m in sorted(numbers):
        for lab, num in sorted(numbers[m].items()):
            parts.append(f"{m}|{lab}|{num.number}|{num.page}")
    for m in sorted(cite_labels):
        for ck, lab in sorted(cite_labels[m].items()):
            parts.append(f"{m}|cite|{ck}|{lab}")
    return "".join(parts).encode()
