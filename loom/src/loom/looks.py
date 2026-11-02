"""A person's look at the project's open files: each file's text as they last saw it, what changed since, and the two verbs that act on a change, keep and undo.

A look is `.loom/looked/<reviewer>.json`, `{who, when, files: {path: hash}}`, each file's text stored exactly in the history's `texts/` (`write_raw`). It covers every open text file: one the viewer shows that reads as UTF-8 and is at most 1 MB, LaTeX included. It is personal, by the reviewer name Review resolves, and taken when the person acts (keeping, undoing) or when `loom serve` starts and finds none, so it records what the person did, never a save (P13). Loom cannot tell who changed a file, only that it changed since the look.
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

#: The ledger's line for a change undone, a plain line beside the steps; a look is its own record, and writes none, since a preview pinned to the history (an adoption's) must not go stale because the person looked.
UNDO = "undo"
#: Where each change's diff is published, under the build output.
DIFFS = "changes"


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
        diff = "".join(
            difflib.unified_diff(
                old.splitlines(keepends=True),
                (text or "").splitlines(keepends=True),
                fromfile=f"a/{rel}" if before_hash else "/dev/null",
                tofile=f"b/{rel}" if text is not None else "/dev/null",
            )
        )
        out.append(Change(rel, kind, before_hash, after_hash, diff))
    return out


class LookRefused(Exception):
    """A keep or an undo that cannot be done, and why; `code` is the write API's."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def keep(quilt: Quilt, who: str, path: str | None = None) -> Look:
    """Keep the change to `path` (its entry in the look moves to its text now), or with no path keep everything (a new look)."""
    from loom.records.snapshots import write_raw

    look = read_look(quilt.root, who)
    if path is None or look is None:
        return take(quilt, who)
    now = open_texts(quilt)
    if path not in now and path not in look.files:
        raise LookRefused("no-such-change", f"{path} has not changed since your look")
    if path in now:
        look.files[path] = write_raw(quilt.root, now[path], quilt.history_dir)
    else:
        look.files.pop(path, None)
    look.when = stamp()
    _write(quilt.root, look)
    return look


def undo(quilt: Quilt, who: str, path: str) -> str:
    """Put `path` back as it was at `who`'s look, keeping its text now first; the ledger records both hashes. A file new since the look has nothing to go back to."""
    from loom.history.ledger import append_entry
    from loom.records.snapshots import read_raw, write_raw

    look = read_look(quilt.root, who)
    before_hash = look.files.get(path) if look else None
    if look is None or before_hash is None:
        raise LookRefused("nothing-to-undo", f"{path} was not there at your look: delete it yourself, or keep it")
    old = read_raw(quilt.root, before_hash, quilt.history_dir)
    if old is None:
        raise LookRefused("no-text", f"the text of {path} at your look is missing from the history")
    p = quilt.root / path
    current = open_texts(quilt).get(path)
    if current is None and p.exists():
        raise LookRefused("not-text", f"{path} is no longer a text file loom keeps; it is left as it is")
    now_hash = write_raw(quilt.root, current, quilt.history_dir) if current is not None else None
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".loom-tmp")
    tmp.write_text(old, encoding="utf-8")
    os.replace(tmp, p)
    append_entry(quilt.history_dir, UNDO, {"who": who, "path": path, "from": now_hash, "to": before_hash}, who)
    return before_hash


def attach_changes(quilt: Quilt, who: str, manifest: dict[str, Any], files: dict[str, str | bytes]) -> None:
    """Publish `who`'s changes since their look into `manifest["changes"]`, each diff under `DIFFS`, and the look's time as `changes_since`; nothing before a first look or without a reviewer."""
    look = read_look(quilt.root, who) if who else None
    if look is None:
        return
    entries: list[dict[str, Any]] = []
    for c in changes(quilt, who):
        entry: dict[str, Any] = {"path": c.path, "kind": c.kind}
        if c.diff:
            entry["diff"] = f"{DIFFS}/{c.path}.diff"
            files[entry["diff"]] = c.diff
        entries.append(entry)
    manifest["changes"] = entries
    manifest["changes_since"] = {"who": look.who, "when": look.when}
