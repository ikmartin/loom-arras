"""`reference-notes.jsonl`: works an agent proposed citing and the author accepted (book 8.9.1, plan 0.10 Part F).

A cheap stand-in, and deliberately so. When an agent suggests replacing an argument with a citation, the work it names is usually not in `refs.bib` at all -- so there is no entry to resolve, nothing for `loom:unresolved-work` to complain about, and no identity for loom to bind. Adding the bibliography entry is the author's job and always was (DR-122), but authors are lazy about references, and a suggestion accepted in a run that is later discarded is a verification done twice.

So accepting one appends a line here: what the work was, which keys wanted it, and which run proposed it. It never touches `refs.bib`, `refs/` or the manifest, it deduplicates nothing and resolves nothing. It is a breadcrumb trail for the day the author is no longer lazy, and where a confirmed identity eventually lives is deferred with the rest of `refs/`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

NOTES = "reference-notes.jsonl"


def notes_path(root: Path) -> Path:
    return root / NOTES


def append_note(root: Path, note: dict[str, Any]) -> None:
    with notes_path(root).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(note, ensure_ascii=False, sort_keys=True) + "\n")


def read_notes(root: Path) -> list[dict[str, Any]]:
    p = notes_path(root)
    if not p.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            out.append(item)
    return out
