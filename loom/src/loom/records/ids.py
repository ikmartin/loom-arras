"""The ids of what loom's shared logs hold: an annotation, a note, a session and a link.

Clones of a quilt write apart and merge later, so two records can reach one log under one id. `repeated` reports that (P13); it drops nothing and renumbers nothing, since which record an id should keep is not loom's to choose.
"""

from __future__ import annotations

import json
from pathlib import Path


def repeated(root: Path, rel: str, events: tuple[str, ...] = ()) -> list[tuple[int, str]]:
    """Every line of a log that gives an id to a second record: its line number and what to say of it.

    `events` names the events that give a record its id, where every other event only speaks of one; with none, every line is a record. Lines that cannot be read are the log's own reader's to report.
    """
    try:
        lines = (root / rel).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    first: dict[str, tuple[int, str]] = {}
    found: list[tuple[int, str]] = []
    for n, line in enumerate(lines, 1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict) or "id" not in record or (events and record.get("event") not in events):
            continue
        ident = str(record["id"])
        if ident not in first:
            first[ident] = (n, line)
            continue
        at, text = first[ident]
        if line.strip() == text.strip():
            found.append(
                (n, f"line {n} repeats line {at} word for word, so {ident} reads as written twice: delete line {n}")
            )
        else:
            found.append(
                (
                    n,
                    f"lines {at} and {n} are two records under one id, {ident}, so nothing can say which it means: change the id on one of them",
                )
            )
    return found
