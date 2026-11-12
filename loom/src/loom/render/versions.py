"""The version an annotation was written on, for one whose quoted words are gone: that version made by TeX with every annotation written on it marked, and an empty mark where its words were in the text now.

Loom keeps every version an annotation is written against, by hash (`records/snapshots.py`). An annotation whose words are gone is `detached` and draws nowhere in the text now; its version is published under `fragments/versions/`, one per hash, and the place its words were is found by aligning the version's words with the text now: where its words were replaced, the replacement's start; where they were cut, the word after them.
"""

from __future__ import annotations

import difflib
import re
from bisect import bisect_right
from dataclasses import dataclass
from typing import Any

from loom.records.annotations import Annotation
from loom.records.selectors import Selector, resolve_selector
from loom.records.snapshots import read_snapshot
from loom.records.store import Records
from loom.render.fragments import FragmentRenderer
from loom.render.marks import MarkEntry, place_marks
from loom.scan.nodes import NodeRec
from loom.scan.scan import ScanResult

#: Where a version's fragment is published.
VERSIONS = "fragments/versions"
#: How many words beside the place a gone mark is found by in a fragment.
CONTEXT_WORDS = 4
#: A word a fragment prints as written: no formula, command, group or comment in it.
_PLAIN = re.compile(r"^[^\s$\\{}%]+$")
_CHILD = re.compile(r"^% !LOOM child: .*\n", re.M)
#: The file a preview's text stands in (`changes._named`), which its blocks' `data-src` name.
_PREVIEW_SRC = re.compile(r'data-src="([^"]*review-[0-9a-f]{20}\.tex):\d+:\d+"')


@dataclass
class Gone:
    """An annotation whose quoted words are gone: the version it was written on, and the empty mark where its words were, or None when nothing aligns."""

    annotation: Annotation
    key: str
    node: NodeRec | None
    old: str
    entry: MarkEntry | None
    #: carried by a kept change onto its new words, where it stands: its version is published, and it needs no empty mark
    carried: bool = False


def _fragment_of(digest: str) -> str:
    """Where a version's fragment is published: named by the hash's first sixteen hex characters."""
    return f"{VERSIONS}/{digest.split(':', 1)[-1][:16]}.html"


def _tokens(text: str) -> list[tuple[str, int, int]]:
    return [(m.group(), m.start(), m.end()) for m in re.finditer(r"\S+", text)]


def aligned(old: str, new: str, at: int) -> int | None:
    """Where the word of `old` at offset `at` stands in `new`, the two texts aligned word by word.

    Parameters
    ----------
    old : str
        The text as it was.
    new : str
        The text now.
    at : int
        An offset in `old`; the word it falls in, or the next word after it, is placed.

    Returns
    -------
    int or None
        The offset in `new` of the same word where it survives, of what replaced it, or of the word after a cut; past the last word, the end of the new text's last word; None when no word of the two aligns.
    """
    left, right = _tokens(old), _tokens(new)
    opcodes = difflib.SequenceMatcher(None, [t[0] for t in left], [t[0] for t in right], autojunk=False).get_opcodes()
    if not any(tag == "equal" for tag, *_ in opcodes):
        return None
    i = bisect_right([t[2] for t in left], at)
    for tag, a, b, c, _d in opcodes:
        if a <= i < b:
            j = c + (i - a) if tag == "equal" else c
            return right[j][1] if j < len(right) else right[-1][2]
    return right[-1][2] if right else 0


def _beside(own: str, point: int) -> tuple[str, bool]:
    """The words a gone mark is found by, and whether they follow it: up to `CONTEXT_WORDS` plain words of its paragraph before the place, else after it; ('', True) when there are none, which puts the mark at its block's start."""
    head = re.split(r"\n\s*\n", own[:point])[-1]
    before: list[str] = []
    for word in reversed(head.split()):
        if not _PLAIN.match(word) or len(before) == CONTEXT_WORDS:
            break
        before.insert(0, word)
    if before:
        return " ".join(before), False
    tail = re.split(r"\n\s*\n", own[point:])[0]
    after: list[str] = []
    for word in tail.split():
        if not _PLAIN.match(word) or len(after) == CONTEXT_WORDS:
            break
        after.append(word)
    return " ".join(after), True


def _file_point(pieces: list[tuple[int, int, int]], at: int) -> int | None:
    """A place in the own text as an offset in its file: inside a piece, or at the end of the piece it closes."""
    for cstart, fstart, length in pieces:
        if cstart <= at <= cstart + length:
            return fstart + (at - cstart)
    return None


def _kept_text(result: ScanResult, digest: str) -> str | None:
    """A version as kept, without the lines that stand for its children: the text its annotations were quoted from."""
    text = read_snapshot(result.quilt.root, digest, result.quilt.history_dir)
    return None if text is None else _CHILD.sub("", text)


def gone_annotations(result: ScanResult, records: Records) -> list[Gone]:
    """Every annotation whose quoted words are gone from its key and whose version loom keeps, with the empty mark where its words were in the text now.

    A reply follows what it answers, and one on a page or a whole work has no key text. An annotation whose words still stand in its key is detached because its document no longer holds the key, and is not here; one on a key that is gone has no place.

    Parameters
    ----------
    result : ScanResult
        The scan the build renders.
    records : Records
        The quilt's records, resolved against `result`.

    Returns
    -------
    list of Gone
        One per such annotation, in the log's order; `entry` None where no word aligns or the key is gone.

    See Also
    --------
    gone_marks : the empty marks, by the fragment that shows them.
    attach_versions : the manifest's `version` and the version fragments.
    """
    out: list[Gone] = []
    kept: dict[str, str | None] = {}
    for res in records.resolved(result):
        a = res.annotation
        if a.earlier and res.recorded and not res.detached and a.target_hash and a.page is None:
            old = kept.setdefault(a.target_hash, _kept_text(result, a.target_hash))
            if old is not None and resolve_selector(old, Selector(a.earlier.get("quote", ""))) is not None:
                out.append(Gone(a, res.target, result.nodes.get(res.target), old, None, carried=True))
            continue
        if not (res.detached and res.recorded) or a.in_reply_to or a.selector is None:
            continue
        if a.anchor is not None or a.page is not None or not a.target_hash:
            continue
        if a.target_hash not in kept:
            kept[a.target_hash] = _kept_text(result, a.target_hash)
        old = kept[a.target_hash]
        if old is None or resolve_selector(old, a.selector) is None:
            continue
        node = result.nodes.get(res.target)
        if node is None:
            region = result.assembly.regions.get(res.target)
            node = result.nodes.get(region.container) if region else None
        entry = None
        if node is not None:
            own, pieces = Records.own_pieces(result, node)
            if resolve_selector(own, a.selector) is not None:
                continue
            span = resolve_selector(old, a.selector)
            at = aligned(old, own, span[0]) if span else None
            point = _file_point(pieces, at) if at is not None else None
            if at is not None and point is not None:
                words, lead = _beside(own, at)
                entry = MarkEntry(a.id, words, node.file, point, point, res.in_doc, gone=True, lead=lead)
        out.append(Gone(a, res.target, node, old, entry))
    return out


def gone_marks(gone: list[Gone]) -> dict[str, list[MarkEntry]]:
    """The empty marks of `gone`, by the node whose fragment shows them: a proof's under its statement, and on the proof's own page.

    Parameters
    ----------
    gone : list of Gone
        As `gone_annotations` gives them.

    Returns
    -------
    dict of str to list of MarkEntry
        By node key, in the shape the build's other marks take (`build._marks_by_node`).
    """
    out: dict[str, list[MarkEntry]] = {}
    for g in gone:
        if g.entry is None or g.node is None:
            continue
        n = g.node
        owner = n.of if n.kind == "proof" and n.of else n.key
        out.setdefault(owner, []).append(g.entry)
        if owner != n.key:
            out.setdefault(n.key, []).append(g.entry)
    return out


def attach_versions(
    result: ScanResult,
    records: Records,
    renderer: FragmentRenderer,
    manifest: dict[str, Any],
    files: dict[str, str | bytes],
    gone: list[Gone],
) -> None:
    """Give each annotation of `gone` its `version: {hash, fragment, at}`, and ask for each version's fragment once: its text made by TeX with the build's other previews, every annotation quoted from it marked.

    The fragments are filled when the build makes its previews (`FragmentRenderer.previews.make`), so this runs before that and after `Records.apply` has written the annotations.

    Parameters
    ----------
    result : ScanResult
        The scan the build renders.
    records : Records
        The quilt's records.
    renderer : FragmentRenderer
        The build's renderer, whose previews make the fragments.
    manifest : dict
        The manifest, its `annotations` written.
    files : dict of str to str or bytes
        The build's files; each version's fragment is added under `fragments/versions/`.
    gone : list of Gone
        As `gone_annotations` gives them.
    """
    rows = manifest.get("annotations", {})
    on_hash: dict[str, list[Annotation]] = {}
    for rec in records.records:
        for a in rec.annotations:
            if a.in_reply_to is None and a.selector is not None and a.anchor is None and a.page is None:
                on_hash.setdefault(a.target_hash, []).append(a)
    asked: set[str] = set()
    for g in gone:
        digest = g.annotation.target_hash
        path = _fragment_of(digest)
        row = rows.get(g.annotation.id)
        if row is not None:
            row["version"] = {"hash": digest, "fragment": path, "at": g.entry is not None or g.carried}
        if digest in asked:
            continue
        asked.add(digest)
        # a carried annotation is marked on the words it was on, which this version holds
        said = {a.id: Selector(a.earlier["quote"]) if a.earlier else a.selector for a in on_hash[digest]}
        quoted = [(i, sel.exact, resolve_selector(g.old, sel)) for i, sel in said.items() if sel and sel.exact]
        files[path] = ""
        later = renderer.previews.ask(g.node.key if g.node else g.key, g.old, None, [])

        def took(html: str, path: str = path, quoted: list[tuple[str, str, tuple[int, int] | None]] = quoted) -> None:
            src = _PREVIEW_SRC.search(html)
            entries = [MarkEntry(i, q, src.group(1), s[0], s[1]) for i, q, s in quoted if s] if src else []
            files[path] = place_marks(html, entries)

        renderer.previews.on_made(later, took)
