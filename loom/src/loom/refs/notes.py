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


#: The two answers to a citation suggestion.
DECISIONS = ("accept", "reject")


def find_citation(root: Path, ann_id: str, decision: str = "reject") -> tuple[Any, Any]:
    """(record, annotation) for an open citation suggestion that `decide_citation` can act on.

    LookupError when no annotation has the id; ValueError when it is not a citation or is no longer open, and on `accept` when it proposes no work (`work` comes from the payload, so a suggestion without one has nothing to record).
    """
    from loom.records.annotations import find_annotation
    from loom.records.store import Records

    found = find_annotation(Records(root).records, ann_id)
    if found is None:
        raise LookupError(f"no annotation {ann_id}")
    record, ann = found
    if ann.kind != "citation":
        raise ValueError(f"{ann_id} is a {ann.kind}, not a citation suggestion")
    if ann.status != "open":
        raise ValueError(f"{ann_id} is {ann.status} already; nothing waits on it")
    if decision == "accept" and not ann.payload:
        raise ValueError(f"{ann_id} proposes no work; a citation suggestion names one in --payload")
    return record, ann


def decide_citation(
    root: Path,
    annotation: str,
    decision: str,
    why: str | None,
    who: str,
    session: str | None,
    *,
    dry_run: bool = False,
) -> dict[str, Any] | None:
    """Accept or reject a citation suggestion: the one writer behind `loom library verify|discard` and the write API's `library-cite`.

    Parameters
    ----------
    root : Path
        The quilt.
    annotation : str
        The suggestion's annotation id.
    decision : str
        `accept` appends a reference note and resolves the suggestion; `reject` only resolves it.
    why : str or None
        Rides on the resolve event; default the decision's own word.
    who : str
        The author deciding.
    session : str or None
        The session the resolve event is filed under; None files it under none.
    dry_run : bool, default False
        Check everything and write nothing.

    Returns
    -------
    dict or None
        The note appended on accept (`work` the payload, `claim` the body), else None.

    Raises
    ------
    LookupError
        No annotation has the id.
    ValueError
        An unknown decision, or a suggestion `find_citation` refuses.

    Notes
    -----
    Neither touches the author's bibliography: a candidate becomes a work's identity when their own entry says so (DR-122).
    """
    from loom.clock import stamp
    from loom.records.log import append

    if decision not in DECISIONS:
        raise ValueError("decision must be accept or reject")
    record, ann = find_citation(root, annotation, decision)
    now = stamp()
    note = (
        {
            "work": ann.payload,
            "for": [ann.target_key],
            "claim": ann.body,
            "identifier": {"verified": False},
            "accepted": {"when": now, "who": who},
            "from": {"session": record.rel, "annotation": annotation},
        }
        if decision == "accept"
        else None
    )
    if dry_run:
        return note
    if note is not None:
        append_note(root, note)
    event: dict[str, Any] = {
        "event": "resolved",
        "id": annotation,
        "when": now,
        "author": who,
        "kind": "human",
        "body": why or f"{decision}ed",
    }
    if session:
        event["session"] = session
    append(root, event)
    return note
