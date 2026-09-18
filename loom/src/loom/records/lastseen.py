"""The last text loom saw for every key, so an annotation's anchor can be frozen when the author edits under it (book 7.5).

An annotation records `against`: the hash of the text it was written about. When that text changes, the words the annotation quotes are gone from the quilt, and with them any chance of showing a reader what was being objected to. Freezing means copying the old text into `.loom/history/texts/` at the moment loom notices it moved.

Noticing requires having the old text, not merely its hash, which is why this keeps a copy of the quilt rather than a table of digests: once the author saves, the previous text exists nowhere else. The copy is bounded -- one text per key, rewritten in place -- and only texts an annotation actually points at are ever frozen, so a quilt nobody has reviewed pays nothing but the cache itself.

Two edits between two scans leave an annotation **unanchored**: loom never saw the text in between and will not pretend it did.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from loom.records.snapshots import write_snapshot
from loom.scan.hashing import hash_text

if TYPE_CHECKING:
    from loom.records.annotations import Record
    from loom.scan.scan import ScanResult

CACHE = "last-seen.json"
GITIGNORE_LINE = CACHE  # derived from the quilt, rebuilt on demand, and never worth committing
VERSION = 1


def cache_path(root: Path, history_dir: Path | None = None) -> Path:
    return (history_dir or root / ".loom" / "history").parent / CACHE


def read_last_seen(root: Path, history_dir: Path | None = None) -> dict[str, str]:
    p = cache_path(root, history_dir)
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict) or data.get("version") != VERSION:
        return {}
    keys = data.get("keys")
    return {str(k): str(v) for k, v in keys.items()} if isinstance(keys, dict) else {}


def write_last_seen(root: Path, texts: dict[str, str], history_dir: Path | None = None) -> None:
    p = cache_path(root, history_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps({"version": VERSION, "keys": texts}, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def current_texts(result: ScanResult) -> dict[str, str]:
    """The own text of every key that has one, which is what every hash is taken over."""
    from loom.render.manifest import own_text

    out: dict[str, str] = {}
    for key, node in result.assembly.nodes.items():
        try:
            out[key] = own_text(result, node)
        except (KeyError, AttributeError):
            continue
    return out


def freeze_moved(result: ScanResult, records: list[Record], history_dir: Path | None = None) -> list[str]:
    """Freeze the previous text of every key that moved and that an annotation was written against; returns those keys.

    Called wherever loom rebuilds, which is the moment it can still see both texts. A key that moved with no annotation pointing at its old text costs one hash comparison and nothing else.
    """
    root = result.quilt.root
    wanted = {a.target_hash for rec in records for a in rec.annotations if a.target_hash}
    previous = read_last_seen(root, history_dir)
    texts = current_texts(result)
    frozen: list[str] = []
    for key, text in texts.items():
        old = previous.get(key)
        if old is None or old == text:
            continue
        if hash_text(old) in wanted:
            write_snapshot(root, old, history_dir)
            frozen.append(key)
    write_last_seen(root, texts, history_dir)
    return sorted(frozen)


def ensure_gitignore_line(root: Path) -> bool:
    """Keep the cache out of version control, as one appended line in a file the author owns; True when it wrote."""
    p = root / ".gitignore"
    existing = p.read_text(encoding="utf-8") if p.is_file() else ""
    if GITIGNORE_LINE in existing.splitlines():
        return False
    p.write_text(existing.rstrip("\n") + ("\n" if existing else "") + GITIGNORE_LINE + "\n", encoding="utf-8")
    return True
