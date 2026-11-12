"""A person's look at the project's open files: each file's text as they last saw it, and which files changed since.

A look is `.loom/looked/<reviewer>.json`, `{who, when, files: {path: hash}}`, each file's text stored exactly in the history's `texts/` (`write_raw`). It covers every open text file: one the viewer shows that reads as UTF-8 and is at most 1 MB, LaTeX included. It is personal, by the reviewer name Review resolves, and taken when the person acts or when `loom serve` starts and finds none, so it records what the person did, never a save (P13). What changed since it is cut into changes by words, and kept or discarded one by one, in `pending.py`. Loom cannot tell who changed a file, only that it changed since the look.
"""

from __future__ import annotations

import difflib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loom.clock import stamp
from loom.paths import LOOKED

if TYPE_CHECKING:
    from loom.scan.quilt import Quilt

#: The ledger's line for a change discarded, a plain line beside the steps; a keep writes `history.acts.KEEP`, and taking a look writes nothing.
UNDO = "undo"
#: Lines of context around a change, as `unified_diff` prints them.
CONTEXT = 3


@dataclass
class Look:
    """One person's look: who, when, and each open file's text by its hash."""

    who: str
    when: str
    files: dict[str, str] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {"who": self.who, "when": self.when, "files": dict(sorted(self.files.items()))}


@dataclass(frozen=True)
class Change:
    """One open file changed since the look: `changed`, `new` (not there at the look) or `gone` (there at the look, not now)."""

    path: str
    kind: str
    before: str | None  # the look's hash
    after: str | None  # the hash now
    diff: str  # unified, `a/PATH` to `b/PATH`


def look_path(root: Path, who: str) -> Path:
    from loom.since import slug

    return root / LOOKED / f"{slug(who)}.json"


def read_look(root: Path, who: str) -> Look | None:
    """`who`'s last look, or None before their first (or when the file does not parse, which is the same thing)."""
    try:
        data = json.loads(look_path(root, who).read_text(encoding="utf-8"))
        return Look(str(data["who"]), str(data["when"]), {str(k): str(v) for k, v in data.get("files", {}).items()})
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def _write(root: Path, look: Look) -> None:
    p = look_path(root, look.who)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".loom-tmp")
    tmp.write_text(json.dumps(look.to_json(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def open_texts(quilt: Quilt) -> dict[str, str]:
    """Every open text file's text by its path: shown, UTF-8 and at most 1 MB."""
    from loom.files import TEXT_LIMIT, Shown

    out: dict[str, str] = {}
    for rel in Shown.of(quilt).walk():
        p = quilt.root / rel
        try:
            if p.stat().st_size > TEXT_LIMIT:
                continue
            data = p.read_bytes()
            if b"\x00" in data[:8192]:
                continue
            out[rel] = data.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
    return out


def take(quilt: Quilt, who: str) -> Look:
    """A new look by `who` at every open file now, each text stored."""
    from loom.records.snapshots import write_raw

    hist = quilt.history_dir
    files = {rel: write_raw(quilt.root, text, hist) for rel, text in open_texts(quilt).items()}
    look = Look(who, stamp(), files)
    _write(quilt.root, look)
    return look


def _lines(text: str) -> list[str]:
    return text.splitlines(keepends=True)


def changes(quilt: Quilt, who: str) -> list[Change]:
    """What changed in the open files since `who`'s last look, by path; empty before their first."""
    from loom.records.snapshots import read_raw
    from loom.scan.hashing import sha256

    look = read_look(quilt.root, who)
    if look is None:
        return []
    now = open_texts(quilt)
    out: list[Change] = []
    for rel in sorted(set(now) | set(look.files)):
        before_hash = look.files.get(rel)
        text = now.get(rel)
        after_hash = sha256(text) if text is not None else None
        if before_hash == after_hash:
            continue
        old = (read_raw(quilt.root, before_hash, quilt.history_dir) or "") if before_hash else ""
        kind = "new" if before_hash is None else "gone" if text is None else "changed"
        a, b = _lines(old), _lines(text or "")
        diff = "".join(
            difflib.unified_diff(
                a,
                b,
                fromfile=f"a/{rel}" if before_hash else "/dev/null",
                tofile=f"b/{rel}" if text is not None else "/dev/null",
                n=CONTEXT,
            )
        )
        out.append(Change(rel, kind, before_hash, after_hash, diff))
    return out


def keep_all(quilt: Quilt, who: str) -> Look:
    """A new look by `who` at every open file, with a `keep` line naming the files that had changed since the last; a first look writes none."""
    from loom.history.acts import KEEP
    from loom.history.ledger import append_entry

    moved = [c.path for c in changes(quilt, who)] if read_look(quilt.root, who) else []
    look = take(quilt, who)
    if moved:
        append_entry(quilt.history_dir, KEEP, {"who": who, "paths": moved}, who)
    return look


def take_line(quilt: Quilt, who: str, path: str, before: str, after: str, line: int) -> None:
    """Take the one line a person just changed in the viewer into their look, so a change they made there is not listed back to them (`loom.tasks`).

    Every other change to the file stays listed. A line the look does not hold as `before` does is part of a change already listed, and stays in it. `line` is a line of `tasks.split_lines`; no ledger line, since the act that called this writes its own.
    """
    from loom.records.snapshots import read_raw, write_raw
    from loom.tasks import split_lines

    look = read_look(quilt.root, who)
    seen = look.files.get(path) if look else None
    old = read_raw(quilt.root, seen, quilt.history_dir) if seen else None
    if look is None or old is None:
        return
    if old == before:
        look.files[path] = write_raw(quilt.root, after, quilt.history_dir)
        _write(quilt.root, look)
        return
    held, now = split_lines(old), split_lines(before)
    for tag, i1, _i2, j1, j2 in difflib.SequenceMatcher(None, held, now).get_opcodes():
        if tag == "equal" and j1 <= line < j2:
            held[i1 + line - j1] = split_lines(after)[line]
            look.files[path] = write_raw(quilt.root, "".join(held), quilt.history_dir)
            _write(quilt.root, look)
            return
