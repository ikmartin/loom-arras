"""`digests/unreadable.json`: what the author has said loom should stop chasing (plan 0.13 §4, book 8.14).

Two claims live here, both the author's and both keyed by what the author can name. **Unreadable** says a cited work has no document to hold -- the Stacks Project is a living work with no fixed version -- so the invariant's lint stops asking for a PDF that does not exist. **Forgotten** says a document in the store is not wanted as a bibliography entry, so `refs scan` stops re-offering one for it.

Nothing in a bibliography entry states either fact, and loom will not infer them: an entry with no identifier looks exactly like one whose identifier nobody has typed yet. So they are declared, with a reason, or not at all.

Appended rather than edited, like every other record loom keeps: `--undo` writes another event, and the current state is the fold. The file is loom's, beside the bibliography and never inside it, because the author's `.bib` is theirs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loom.clock import stamp

FILE = "digests/unreadable.json"

#: The two claims. `unreadable` is keyed by citekey, `forget` by citekey or `sha256:<hash>`.
KINDS = ("unreadable", "forget")


@dataclass(frozen=True)
class Declaration:
    """One standing claim: what it is about, why, and who made it."""

    kind: str
    key: str
    why: str
    who: str
    when: str


def path_of(root: Path) -> Path:
    return root / FILE


def load_events(root: Path) -> list[dict[str, Any]]:
    """Every event ever appended, in order; an absent or unreadable file reads as none.

    Read rather than trusted: a corrupt file costs a suppressed declaration, which shows up as a lint warning returning, and never as a loss.
    """
    p = path_of(root)
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    events = data.get("events") if isinstance(data, dict) else None
    return [e for e in events if isinstance(e, dict)] if isinstance(events, list) else []


def declarations(root: Path, kind: str) -> dict[str, Declaration]:
    """The claims of one kind that stand now, by key.

    Parameters
    ----------
    root : Path
        The quilt.
    kind : str
        One of `KINDS`.

    Returns
    -------
    dict of str to Declaration
        Keyed by citekey, or by `sha256:<hash>` for a forgotten document with no entry. An undone claim is absent.
    """
    out: dict[str, Declaration] = {}
    for e in load_events(root):
        if e.get("kind") != kind or not e.get("key"):
            continue
        key = str(e["key"])
        if e.get("undo"):
            out.pop(key, None)
            continue
        out[key] = Declaration(
            kind=kind,
            key=key,
            why=str(e.get("why", "")),
            who=str(e.get("who", "")),
            when=str(e.get("when", "")),
        )
    return out


def declare(root: Path, kind: str, key: str, why: str, who: str, *, undo: bool = False) -> Declaration | None:
    """Append one claim, or its undoing.

    Parameters
    ----------
    root : Path
        The quilt.
    kind : str
        One of `KINDS`.
    key : str
        The citekey, or `sha256:<hash>` for a stored document no entry names.
    why : str
        The reason, which is required in both directions: undoing a claim is also a claim.
    who : str
        The author, as `resolve_author` settled it.
    undo : bool, default False
        Withdraw the standing claim instead of making one.

    Returns
    -------
    Declaration or None
        What now stands for this key, or None when it was undone.
    """
    if kind not in KINDS:
        raise ValueError(f"unknown declaration: {kind}")
    event: dict[str, Any] = {"kind": kind, "key": key, "why": why, "who": who, "when": stamp()}
    if undo:
        event["undo"] = True
    p = path_of(root)
    events = load_events(root)
    events.append(event)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"events": events}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return declarations(root, kind).get(key)


def is_unreadable(root: Path, citekey: str) -> Declaration | None:
    """The standing unreadable claim for one work, or None; the lint and the build report both ask this."""
    return declarations(root, "unreadable").get(citekey)
