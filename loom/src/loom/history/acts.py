"""A version of a document at each of the author's acts, and a version put back.

A version is a landmark (`stamp_document`): Keep and Undo in Changes keep one, taking changes in keeps one first, the author records one by hand, and restoring keeps the text it replaces as one. `restore` writes a version back into its document file by file; `put_back` writes back the text an undo set aside.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loom.history.ledger import Entry, History, append_entry, load_history
from loom.scan.scan import ScanResult

#: The ledger's line for a file kept in Changes, beside `undo`'s.
KEEP = "keep"
#: The ledger's line for a version or a set-aside text put back.
RESTORE = "restore"


@dataclass
class Kept:
    """What keeping a version of each document did: the documents a version was kept of, and those none was kept of, with why ('' when nothing had changed since its newest)."""

    kept: list[str]
    skipped: dict[str, str]

    def said(self) -> str:
        """The answer's tail: which versions were kept, and why one was not, in the person's words."""
        out = []
        if self.kept:
            out.append(f"a version of {', '.join(Path(d).name for d in self.kept)} is kept")
        for doc, why in self.skipped.items():
            if why:
                out.append(f"no version of {Path(doc).name} was kept: {why}")
        return "; ".join(out)


def documents_reaching(result: ScanResult, paths: list[str] | None) -> list[str]:
    """The person's live documents whose text is made of one of `paths` (`steps.document_files`), or every one of them for None."""
    from loom.history.steps import document_files

    docs = [m for m in result.masters if result.document_role(m) == "person"]
    if paths is None:
        return docs
    wanted = set(paths)
    return [d for d in docs if wanted & set(document_files(result, d))]


def versions_of(history: History, doc: str, live: list[str]) -> list[Entry]:
    """Every landmark whose document is now `doc`, oldest first: its versions."""
    out = []
    for e in history.landmarks():
        recorded = (e.get("drafted") or {}).get("path") if e.action == "import" else e.get("in")
        if isinstance(recorded, str) and history.current_document(recorded, live) == doc:
            out.append(e)
    return out


def keep_versions(result: ScanResult, paths: list[str] | None, kept_for: str, message: str, actor: str | None) -> Kept:
    """Keep a version of each of the person's documents made of one of `paths`, as the act `kept_for` (`keep`, `undo`, `restore`), unless its text is its newest version's.

    A document that cannot be stamped (one reaching a conflicted key) is skipped with the reason; the act it accompanies goes ahead, since a version is kept for it, never asked of it.
    """
    from loom.history.steps import free_name, plan_document_stamp, slug, stamp_document, text_hash

    out = Kept([], {})
    for doc in documents_reaching(result, paths):
        history = load_history(result.quilt.history_dir)
        try:
            _, text = plan_document_stamp(result, history, doc)
        except ValueError as exc:
            out.skipped[doc] = str(exc).split(";")[0]
            continue
        newest = versions_of(history, doc, result.masters)
        if newest and (newest[-1].get("to") or {}).get("hash") == text_hash(text):
            out.skipped[doc] = ""
            continue
        name = free_name(history, slug(f"{Path(doc).stem} {kept_for}", limit=120))
        stamp_document(result, history, doc, name, message, actor, kept_for=kept_for)
        out.kept.append(doc)
    return out


class RestoreRefused(Exception):
    """A version that cannot be put back, and why; `code` is the write API's."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def cannot_restore(result: ScanResult, history: History, entry: Entry) -> str:
    """Why the version `entry` cannot be put back into its document, in the person's words; '' when it can.

    The import is the paper as received, before loom gave its blocks ids. A version that kept no file texts (stamped before they were kept) is one flat text, which goes back only into a document of one file.
    """
    from loom.history.steps import document_files

    if entry.action == "import":
        return "This is the paper as loom received it, before its blocks had ids; putting it back would take every id away."
    recorded = entry.get("in")
    doc = history.current_document(recorded, result.masters) if isinstance(recorded, str) else None
    if not doc or result.document_role(doc) != "person":
        return "Its document is no longer one of yours."
    if not entry.get("files") and len(document_files(result, doc)) > 1:
        return "This version was kept as one text, and the document is now several files."
    return ""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".loom-tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def restore(result: ScanResult, doc: str, version: str, actor: str | None) -> dict[str, Any]:
    """Put `doc` back as the version `version` (a landmark's path or name) holds it, keeping its text now as a version first (P7), and record it.

    Writes each file the version kept (`files`), or its flat text into a document of one file. Raises RestoreRefused for a version that is not `doc`'s or cannot be put back (`cannot_restore`). Returns the paths written, the version's label, and the label of the version that holds the text it replaced (a new one, or the newest when nothing had changed since).
    """
    from loom.records.snapshots import read_raw

    root = result.quilt.root
    history = load_history(result.quilt.history_dir)
    entry = _version(history, root, version)
    if entry is None or entry not in versions_of(history, doc, result.masters):
        raise RestoreRefused("unknown-version", f"{version} is not a version of {doc}")
    why = cannot_restore(result, history, entry)
    if why:
        raise RestoreRefused("cannot-restore", why)
    files: dict[str, str] = {}
    if entry.get("files"):
        for path, digest in entry.get("files").items():
            text = read_raw(root, digest, result.quilt.history_dir)
            if text is None:
                raise RestoreRefused("no-text", f"the text of {path} in this version is missing from the history")
            files[path] = text
    else:
        files[doc] = history.landmark_path(entry).read_text(encoding="utf-8")
    label = _label(history, entry, doc, result.masters)
    kept = keep_versions(result, [doc], "restore", f"Before restoring “{label}”", actor)
    if doc in kept.skipped and kept.skipped[doc]:
        raise RestoreRefused("cannot-keep", f"its text now cannot be kept first: {kept.skipped[doc]}")
    written = [
        p for p, text in files.items() if not (root / p).is_file() or (root / p).read_text(encoding="utf-8") != text
    ]
    for p in written:
        _write(root / p, files[p])
    append_entry(
        result.quilt.history_dir,
        RESTORE,
        {"from": {"landmark": entry.get("landmark"), "step": entry.step}, "in": doc, "paths": written},
        actor,
    )
    history = load_history(result.quilt.history_dir)
    newest = versions_of(history, doc, result.masters)[-1]
    return {"paths": written, "label": label, "before": _label(history, newest, doc, result.masters)}


def _label(history: History, entry: Entry, doc: str, live: list[str]) -> str:
    """A version as an answer names it: its message, with its time when another version of the document has the same message ("Kept an edit, 2026-11-04 07:52")."""
    said = entry.message or entry.name
    alike = [e for e in versions_of(history, doc, live) if (e.message or e.name) == said]
    return f"{said}, {entry.when[:16].replace('T', ' ')}" if len(alike) > 1 else said


def _version(history: History, root: Path, ref: str) -> Entry | None:
    """A landmark by its quilt-relative path, else by its name or step (`History.landmark`)."""
    for e in history.landmarks():
        if history.landmark_path(e).relative_to(root).as_posix() == ref:
            return e
    return history.landmark(ref)


def put_back(root: Path, history_dir: Path, path: str, digest: str, actor: str | None, texts: dict[str, str]) -> str:
    """Write back into `path` the text an undo set aside (`digest`), keeping the file's text now first; returns the hash it replaced, None for a file that was gone.

    `texts` is the open files' texts now (`looks.open_texts`); only a file loom shows may be put back.
    """
    from loom.records.snapshots import read_raw, write_raw

    text = read_raw(root, digest, history_dir)
    if text is None:
        raise RestoreRefused("no-text", f"that text of {path} is missing from the history")
    p = root / path
    if p.exists() and path not in texts:
        raise RestoreRefused("not-text", f"{path} is no longer a text file loom keeps")
    now = texts.get(path)
    before = write_raw(root, now, history_dir) if now is not None else None
    _write(p, text)
    append_entry(history_dir, RESTORE, {"path": path, "from": before, "to": digest}, actor)
    return before or ""
