"""A person's look at the project's open files: each file's text as they last saw it, what changed since, and the two verbs that act on a change, keep and undo.

A look is `.loom/looked/<reviewer>.json`, `{who, when, files: {path: hash}}`, each file's text stored exactly in the history's `texts/` (`write_raw`). It covers every open text file: one the viewer shows that reads as UTF-8 and is at most 1 MB, LaTeX included. It is personal, by the reviewer name Review resolves, and taken when the person acts (keeping, undoing) or when `loom serve` starts and finds none, so it records what the person did, never a save (P13). A change is kept or undone as a whole file or one hunk at a time, a hunk being one of the diff's `@@` groups. Loom cannot tell who changed a file, only that it changed since the look.
"""

from __future__ import annotations

import difflib
import json
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loom.clock import stamp
from loom.paths import LOOKED

if TYPE_CHECKING:
    from loom.scan.quilt import Quilt

#: The ledger's line for a change undone, a plain line beside the steps; a keep writes `history.acts.KEEP`, and taking a look writes nothing.
UNDO = "undo"
#: Where each change's diff is published, under the build output.
DIFFS = "changes"
#: Lines of context around each hunk, as `unified_diff` prints them; a hunk's number is its place among these groups.
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
    hunks: int = 0  # the diff's `@@` groups, numbered from 0


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


def _groups(old: list[str], new: list[str]) -> list[list[tuple[str, int, int, int, int]]]:
    """The diff's hunks as opcode groups, the very groups `unified_diff` prints as `@@` lines, so hunk N here is the Nth the person saw."""
    return list(difflib.SequenceMatcher(None, old, new).get_grouped_opcodes(CONTEXT))


def _hunk(old: list[str], new: list[str], n: int, path: str) -> list[tuple[str, int, int, int, int]]:
    groups = _groups(old, new)
    if not 0 <= n < len(groups):
        raise LookRefused("no-such-hunk", f"{path} has no change number {n} since your look")
    return [op for op in groups[n] if op[0] != "equal"]


def _taken(old: list[str], new: list[str], ops: list[tuple[str, int, int, int, int]]) -> str:
    """`old` with one hunk's changes made, the others not: what the look holds after keeping that hunk."""
    out = list(old)
    for _tag, i1, i2, j1, j2 in reversed(ops):
        out[i1:i2] = new[j1:j2]
    return "".join(out)


def _reverted(old: list[str], new: list[str], ops: list[tuple[str, int, int, int, int]]) -> str:
    """`new` with one hunk's changes put back as they were at the look, the others left: what the file holds after undoing that hunk."""
    out = list(new)
    for _tag, i1, i2, j1, j2 in reversed(ops):
        out[j1:j2] = old[i1:i2]
    return "".join(out)


def _fresh(path: str, current: str | None, seen: str | None) -> None:
    """Refuse an act on a page drawn before the file last moved, so a hunk's number never names another change; `seen` None asks nothing."""
    from loom.scan.hashing import sha256

    if seen is not None and seen != (sha256(current) if current is not None else ""):
        raise LookRefused("stale", f"{path} changed since the page was drawn; look at it again")


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
        out.append(Change(rel, kind, before_hash, after_hash, diff, len(_groups(a, b))))
    return out


class LookRefused(Exception):
    """A keep or an undo that cannot be done, and why; `code` is the write API's."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def keep(quilt: Quilt, who: str, path: str | None = None, *, hunk: int | None = None, seen: str | None = None) -> Look:
    """Keep the change to `path` (its entry in the look moves to its text now), one of its hunks (the look takes that change alone), or with no path keep everything (a new look).

    The look's time stays that of the person's last whole look, so the changes still listed are still since it. Each keep writes a `keep` line naming what it kept. `seen` is the file's hash as the page showed it; a file that has moved on since is refused (`stale`).
    """
    from loom.history.acts import KEEP
    from loom.history.ledger import append_entry
    from loom.records.snapshots import read_raw, write_raw

    look = read_look(quilt.root, who)
    if path is None or look is None:
        moved = [c.path for c in changes(quilt, who)] if look else []
        look = take(quilt, who)
        if moved:
            append_entry(quilt.history_dir, KEEP, {"who": who, "paths": moved}, who)
        return look
    now = open_texts(quilt)
    _fresh(path, now.get(path), seen)
    if path not in now and path not in look.files:
        raise LookRefused("no-such-change", f"{path} has not changed since your look")
    if hunk is not None:
        before = look.files.get(path)
        old = (read_raw(quilt.root, before, quilt.history_dir) or "") if before else ""
        a, b = _lines(old), _lines(now.get(path, ""))
        look.files[path] = write_raw(quilt.root, _taken(a, b, _hunk(a, b, hunk, path)), quilt.history_dir)
    elif path in now:
        look.files[path] = write_raw(quilt.root, now[path], quilt.history_dir)
    else:
        look.files.pop(path, None)
    _write(quilt.root, look)
    entry: dict[str, Any] = {"who": who, "path": path, "to": look.files.get(path)}
    if hunk is not None:
        entry["hunk"] = hunk
    append_entry(quilt.history_dir, KEEP, entry, who)
    return look


def undo(
    quilt: Quilt,
    who: str,
    path: str,
    *,
    hunk: int | None = None,
    seen: str | None = None,
    before: Callable[[], None] | None = None,
) -> str | None:
    """Put `path` back as it was at `who`'s look, or put one of its hunks back, keeping its text now first; the ledger records both hashes, and the hunk.

    A file new since the look is removed, its text kept first, and the line's `to` is null. `seen` is the file's hash as the page showed it; a file that has moved on since is refused (`stale`). `before` runs once the undo is sure to act and before anything is written (the write API keeps a version there). Returns the hash of the text the file now holds, None when it was removed.
    """
    from loom.history.ledger import append_entry
    from loom.records.snapshots import read_raw, write_raw

    look = read_look(quilt.root, who)
    before_hash = look.files.get(path) if look else None
    p = quilt.root / path
    current = open_texts(quilt).get(path)
    if current is None and p.exists():
        raise LookRefused("not-text", f"{path} is no longer a text file loom keeps; it is left as it is")
    _fresh(path, current, seen)
    if look is None or (before_hash is None and current is None):
        raise LookRefused("nothing-to-undo", f"{path} has not changed since your look")
    old = read_raw(quilt.root, before_hash, quilt.history_dir) if before_hash else ""
    if old is None:
        raise LookRefused("no-text", f"the text of {path} at your look is missing from the history")
    back = (
        old
        if hunk is None
        else _reverted(_lines(old), _lines(current or ""), _hunk(_lines(old), _lines(current or ""), hunk, path))
    )
    if before is not None:
        before()
    now_hash = write_raw(quilt.root, current, quilt.history_dir) if current is not None else None
    entry: dict[str, Any] = {"who": who, "path": path, "from": now_hash}
    if hunk is not None:
        entry["hunk"] = hunk
    if before_hash is None and not back:
        p.unlink()
        append_entry(quilt.history_dir, UNDO, entry | {"to": None}, who)
        return None
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".loom-tmp")
    tmp.write_text(back, encoding="utf-8")
    os.replace(tmp, p)
    to = before_hash if hunk is None else write_raw(quilt.root, back, quilt.history_dir)
    append_entry(quilt.history_dir, UNDO, entry | {"to": to}, who)
    return to


def attach_changes(quilt: Quilt, who: str, manifest: dict[str, Any], files: dict[str, str | bytes]) -> None:
    """Publish `who`'s changes since their look into `manifest["changes"]`, each diff under `DIFFS`, and the look's time as `changes_since`; nothing before a first look or without a reviewer."""
    look = read_look(quilt.root, who) if who else None
    if look is None:
        return
    entries: list[dict[str, Any]] = []
    for c in changes(quilt, who):
        entry: dict[str, Any] = {"path": c.path, "kind": c.kind, "hash": c.after, "hunks": c.hunks}
        if c.diff:
            entry["diff"] = f"{DIFFS}/{c.path}.diff"
            files[entry["diff"]] = c.diff
        entries.append(entry)
    manifest["changes"] = entries
    manifest["changes_since"] = {"who": look.who, "when": look.when}
