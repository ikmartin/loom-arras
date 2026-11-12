"""The manifest's `changes`: every change waiting on the person (`pending.py`), each drawn in its block with its old words and its new; and the suggested edits as their record (`suggested_edits`).

A change is drawn in the leaf of the document's fragment that holds its words: the smallest element with a `data-src` round them that holds no other block, a paragraph, a list item's own text, a statement's or a proof's own text, a display. A change with no such leaf, across an environment's head or `\\end` round other blocks or in a list's options, is structural: it has no block, only its `place`, the source range of its own words. The block is made by TeX with the build's other previews, its text as the person kept it with each change's new words set after its old ones, joined by `JOIN`, and each side marked `span.change[data-change][data-side]` (`changes.mark_changes`); a block TeX refuses shows as its source, marked the same way. A change is widened to whole formulas and displays, never past its leaf, since half a formula is no TeX, and to the whole leaf when it crosses an environment's head or its `\\end`. The annotations on the block are drawn on the kept words, and each one a change touches again on the new words as `mark.annotation.moved`.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from loom.render.marks import MarkEntry, place_marks
from loom.render.markup import esc

if TYPE_CHECKING:
    from loom.pending import Pending
    from loom.records.store import Records
    from loom.render.fragments import FragmentRenderer
    from loom.scan.scan import ScanResult

#: Where each change's block is published, and its patch.
FRAGMENTS = "fragments/changes"
DIFFS = "changes"
_MATH = re.compile(
    r"\$\$.*?\$\$|(?<![\\$])\$(?!\$)(?:\\.|[^$\\])+?\$|\\\(.*?\\\)|\\\[.*?\\\]"
    r"|\\begin\{(equation|align|gather|multline|flalign|alignat|eqnarray|displaymath|math)(\*?)\}.*?\\end\{\1\2\}",
    re.S,
)
_ENV = re.compile(r"\\(?:begin|end)\{")
#: What stands between a change's old words and its new in a merged block: a space, so the last old word and the first new one stay two words; for TeX4ht an element of its own, so two formulas side by side stay two; and an empty group, so the words after it stand apart from `\\fi`.
JOIN = " \\ifdefined\\HCode\\HCode{<span></span>}\\fi{}"
_PREVIEW_SRC = re.compile(r'data-src="([^"]*review-[0-9a-f]{20}\.tex):\d+:\d+"')


@dataclass
class _Piece:
    """The changes standing together in one place of a block: their ids, the stretch of the file now they cover, widened, and each change's own stretch with its old and new text."""

    ids: list[str]
    at: tuple[int, int]
    #: each change's stretch, its old and new text, and which of the two the file holds now: 1 for an in-place edit's new words, 0 for the words a suggested edit replaces
    cores: list[tuple[int, int, str, str, int]]

    @property
    def infile(self) -> int | None:
        """Which side the file holds now, 1 the new and 0 the old; None when the piece's changes differ."""
        held = {c[4] for c in self.cores}
        return held.pop() if len(held) == 1 else None

    def side(self, text: str, new: bool) -> str:
        """The stretch as kept (`new` False) or with the changes made."""
        out, pos = [], self.at[0]
        for c0, c1, old, made, _infile in sorted(self.cores):
            out += [text[pos:c0], made if new else old]
            pos = c1
        out.append(text[pos : self.at[1]])
        return "".join(out)


@dataclass
class _Block:
    """A leaf holding changes: its file, the stretch of it the merged text is made of, the document's element it stands for (`src`, its `data-src` range), the key it is read as, and its pieces."""

    path: str
    start: int
    end: int
    key: str
    pieces: list[_Piece] = field(default_factory=list)
    src: tuple[int, int] = (0, 0)


def _widened(text: str, block: tuple[int, int], a: int, b: int) -> tuple[int, int]:
    """`a`..`b` widened to the whole formulas and displays of `block` it cuts into."""
    moved = True
    while moved:
        moved = False
        for m in _MATH.finditer(text, block[0], block[1]):
            s, e = m.start(), m.end()
            if (s < a < e or s < b < e) and (s < a or b < e):
                a, b, moved = min(a, s), max(b, e), True
    return a, b


@dataclass(frozen=True)
class _Element:
    """One element of the document's fragments with a `data-src` in a file: its range, whether it is a block of its own (a statement, a proof, an inclusion, a section, a labelled key), and its id."""

    start: int
    end: int
    block: bool
    ident: str | None


_BLOCK_CLASSES = frozenset({"env", "env-proof", "include", "included"})


def _elements(result: ScanResult, manifest: dict[str, Any], files: dict[str, str | bytes], path: str) -> list[_Element]:
    """Every element of the fragments that draw `path` (its statements' and proofs' own, and each document's holding it) whose `data-src` is in it."""
    from loom.paths import BUILD

    rels = [
        str(entry.get("fragment") or "")
        for key, entry in manifest.get("nodes", {}).items()
        if result.nodes.get(key) is not None and result.nodes[key].file == path
    ]
    rels += [str(m.get("fragment") or "") for m in manifest.get("masters", [])]
    seen: dict[tuple[int, int], _Element] = {}
    for rel in dict.fromkeys(filter(None, rels)):
        html = files.get(rel)
        if not isinstance(html, str) or not html:
            disk = result.quilt.root / BUILD / rel
            html = disk.read_text(encoding="utf-8") if disk.is_file() else ""
        if f'data-src="{path}:' not in html:
            continue
        for m in _START_TAG.finditer(html):
            attrs = m.group(2)
            src = re.search(rf'\bdata-src="{re.escape(path)}:(\d+):(\d+)"', attrs)
            if src is None:
                continue
            named = re.search(r'\bclass="([^"]*)"', attrs)
            classes = set(named.group(1).split()) if named else set()
            ident = re.search(r'\bid="([^"]+)"', attrs)
            block = (
                m.group(1) in ("section", "details")
                or bool(classes & _BLOCK_CLASSES)
                or "data-key" in attrs
                or "data-label" in attrs
            )
            at = (int(src.group(1)), int(src.group(2)))
            was = seen.get(at)
            seen[at] = _Element(
                at[0],
                at[1],
                block or bool(was and was.block),
                (was.ident if was else None) or (ident.group(1) if ident else None),
            )
    return list(seen.values())


def _reach(text: str, end: int) -> int:
    """Where an element ending at `end` reaches: to the end of its line when that is a few characters on, since the offsets TeX4ht gives a paragraph stop short of its last word's end."""
    line = text.find("\n", end)
    return line if 0 <= line - end <= 3 else end


def _leaf(elements: list[_Element], a: int, b: int, text: str = "") -> _Element | None:
    """The leaf holding `a`..`b`: the smallest element whose range holds it, when it holds no block but itself; None for a change with no such leaf, a structural one."""
    holding = [e for e in elements if e.start <= a and b <= _reach(text, e.end) and e.start < e.end]
    if not holding:
        return None
    leaf = min(holding, key=lambda e: (e.end - e.start, not e.block))
    inside = [
        e
        for e in elements
        if e.block and leaf.start <= e.start and e.end <= leaf.end and (e.start, e.end) != (leaf.start, leaf.end)
    ]
    return None if inside else leaf


_HEAD = re.compile(r"\\(begin|end)\{([^}]*)\}")


def _round_blocks(result: ScanResult, path: str, text: str, words: tuple[int, int], old: str) -> bool:
    """Whether a change's words, as the file holds them or as they were, open or close an environment that holds a statement or a proof: a list of exercises with their proofs, say, whose options or head it edits."""
    if not (_ENV.search(old) or _ENV.search(text[words[0] : words[1]])):
        return False
    nodes = [(n.start, n.end) for n in result.nodes.values() if n.file == path and n.kind in ("environment", "proof")]
    for m in _HEAD.finditer(text, max(0, words[0] - 1), min(len(text), words[1] + 1)):
        if not (words[0] <= m.start() < words[1] or m.start() <= words[0] < m.end()):
            continue
        a, b = _extent(text, m)
        if any(a <= s0 and e0 <= b and (s0, e0) != (a, b) for s0, e0 in nodes):
            return True
    return False


def _extent(text: str, head: re.Match[str]) -> tuple[int, int]:
    """Where the environment whose `\\begin` or `\\end` is `head` starts and ends."""
    name = re.escape(head.group(2))
    if head.group(1) == "begin":
        depth = 0
        for m in re.finditer(rf"\\(begin|end)\{{{name}\}}", text[head.start() :]):
            depth += 1 if m.group(1) == "begin" else -1
            if depth == 0:
                return head.start(), head.start() + m.end()
        return head.start(), len(text)
    depth = 0
    for m in reversed(list(re.finditer(rf"\\(begin|end)\{{{name}\}}", text[: head.end()]))):
        depth += 1 if m.group(1) == "end" else -1
        if depth == 0:
            return m.start(), head.end()
    return 0, head.end()


def _blocks(
    result: ScanResult, changes: list[Pending], then: dict[str, str], elements: Any
) -> tuple[list[_Block], set[str]]:
    """The blocks the changes stand in, each the leaf of the document's fragment that holds the change's words (`_leaf`), with its pieces in the file's order, those that meet once widened made one; and the ids of the changes with no leaf, which are structural.

    `elements(path)` gives the document's elements in a file. A piece is widened to whole formulas and displays, never past its leaf.
    """
    from loom.records.edits import Placed, compose

    placed = {e.id: pl for e, pl in compose(result, [c.edit for c in changes if c.edit]) if isinstance(pl, Placed)}
    blocks: dict[tuple[str, int, int], _Block] = {}
    structural: set[str] = set()
    for c in changes:
        src = result.files.get(c.path)
        if src is None:
            continue
        text = src.text
        if c.kind == "edit":
            words = (c.at[0], c.at[1])
            core = (c.span[0], c.span[1], then.get(c.path, "")[c.was[0] : c.was[1]], text[c.span[0] : c.span[1]], 1)
        elif c.id in placed:
            pl = placed[c.id]
            words = pl.at
            core = (pl.at[0], pl.at[1], text[pl.at[0] : pl.at[1]], pl.text, 0)
        else:
            continue
        leaf = None if _round_blocks(result, c.path, text, words, c.old) else _leaf(elements(c.path), *words, text)
        if leaf is None:
            structural.add(c.id)
            continue
        reach = max(_reach(text, leaf.end), words[1])
        if not (leaf.start <= core[0] and core[1] <= reach):
            # the space around the change's words runs past its leaf: the words alone
            core = (words[0], words[1], c.old, text[words[0] : words[1]], 1) if c.kind == "edit" else core
        holding = [
            (n.end - n.start, n.key)
            for n in result.nodes.values()
            if n.file == c.path and n.start <= leaf.start and leaf.end <= n.end
        ]
        key = min(holding)[1] if holding else (result.default_master or "")
        piece = _Piece([c.id], _widened(text, (leaf.start, reach), core[0], core[1]), [core])
        block = blocks.setdefault(
            (c.path, leaf.start, leaf.end), _Block(c.path, leaf.start, reach, key, src=(leaf.start, leaf.end))
        )
        block.end = max(block.end, reach)
        block.pieces.append(piece)
    # a leaf inside another one is drawn in it, so no two blocks the viewer swaps in overlap
    for small in sorted(blocks.values(), key=lambda b: b.end - b.start):
        big = next(
            (
                b
                for b in blocks.values()
                if b is not small and b.path == small.path and b.start <= small.start and small.end <= b.end
            ),
            None,
        )
        if big is not None:
            big.pieces += small.pieces
            del blocks[(small.path, *small.src)]
    for b in blocks.values():
        together: list[_Piece] = []
        for p in sorted(b.pieces, key=lambda x: x.at):
            if together and p.at[0] <= together[-1].at[1] and (p.at[0] < together[-1].at[1] or p.at[0] == p.at[1]):
                last = together[-1]
                last.ids += p.ids
                last.cores += p.cores
                last.at = (last.at[0], max(last.at[1], p.at[1]))
                continue
            together.append(p)
        b.pieces = together
    return list(blocks.values()), structural


def _trim(text: str, a: int, b: int, n: int, side: int, base: int = 0) -> list[int]:
    """`[start, end, n, side]` of `text[a:b]` less the space either side, shifted by `base`."""
    while a < b and text[a].isspace():
        a += 1
    while b > a and text[b - 1].isspace():
        b -= 1
    return [base + a, base + b, n, side]


def _merged(text: str, block: _Block) -> tuple[str, list[list[int]], list[tuple[int, int, int, int, int, int | None]]]:
    """The block's text as kept with each piece's new text after its old, joined by `JOIN`; the spans `[start, end, n, side]` of each side's words; and `(file start, file end, merged start, old end, new end, side the file holds)` for each piece, which annotations and offsets are placed through."""
    if any(_ENV.search(c[2]) or _ENV.search(c[3]) for p in block.pieces for c in p.cores):
        # a change across an environment's head or its end is the whole block, kept and made
        whole = _Piece(
            [i for p in block.pieces for i in p.ids],
            (block.start, block.end),
            [c for p in block.pieces for c in p.cores],
        )
        kept, made = whole.side(text, False), whole.side(text, True)
        out = kept + JOIN + made
        block.pieces = [whole]
        return (
            out,
            [_trim(out, 0, len(kept), 0, 0), _trim(out, len(kept) + len(JOIN), len(out), 0, 1)],
            [(block.start, block.end, 0, len(kept), len(out), whole.infile)],
        )
    parts: list[str] = []
    spans: list[list[int]] = []
    where: list[tuple[int, int, int, int, int, int | None]] = []
    pos, size = block.start, 0
    for n, p in enumerate(block.pieces):
        parts.append(text[pos : p.at[0]])
        size += p.at[0] - pos
        old, new = p.side(text, False), p.side(text, True)
        joined = old + JOIN + new
        parts.append(joined)
        spans += [_trim(joined, 0, len(old), n, 0, size), _trim(joined, len(old) + len(JOIN), len(joined), n, 1, size)]
        where.append((p.at[0], p.at[1], size, size + len(old), size + len(joined), p.infile))
        size += len(joined)
        pos = p.at[1]
    parts.append(text[pos : block.end])
    return "".join(parts), spans, where


def _plain(x: int, where: list[tuple[int, int, int, int, int, int | None]], start: int) -> int:
    """A place of the file outside every piece as a place of the merged text."""
    out = x - start
    for _f0, f1, _m0, _old_end, new_end, _infile in where:
        if x < f1:
            break
        out = new_end + (x - f1)
    return out


def _to_file(m: int, where: list[tuple[int, int, int, int, int, int | None]], start: int) -> int | None:
    """A place of the merged text as a place of the file now: outside every piece it moves with the text, on the side of a piece the file holds it is that side's place there, and on the other side, or the joiner between them, it has none."""
    file_at, merged_at = start, 0
    for f0, f1, m0, old_end, new_end, infile in where:
        if m < m0:
            break
        if m == m0 or m == new_end:
            # a piece's edges are the edges of its stretch of the file, whichever side the file holds
            return f0 if m == m0 else f1
        if m <= old_end:
            return f0 + (m - m0) if infile == 0 else None
        if m < new_end:
            return f0 + (m - old_end - len(JOIN)) if infile == 1 and m >= old_end + len(JOIN) else None
        file_at, merged_at = f1, new_end
    return file_at + (m - merged_at)


def _range_to_file(
    a: int, b: int, where: list[tuple[int, int, int, int, int, int | None]], start: int
) -> tuple[int | None, int | None]:
    """A range of the merged text as a range of the file now: an edge on words the file does not hold goes to the edge of the piece's stretch when the range runs across the whole piece, as an element holding a change does; a range on such words alone has none."""
    fa, fb = _to_file(a, where, start), _to_file(b, where, start)
    for f0, f1, m0, old_end, new_end, _infile in where:
        if fa is None and m0 <= a <= new_end and b >= new_end:
            # as far into the stretch as it is into its side
            fa = min(f1, f0 + a - (m0 if a <= old_end else old_end + len(JOIN)))
        if fb is None and m0 <= b <= new_end and a <= m0:
            fb = max(f0, f1 - ((old_end if b <= old_end else new_end) - b))
    return fa, fb


def _from_file(x: int, where: list[tuple[int, int, int, int, int, int | None]], start: int) -> int:
    """A place of the file now as a place of the merged text: inside a piece, on the side the file holds."""
    file_at, merged_at = start, 0
    for f0, f1, m0, old_end, new_end, infile in where:
        if x < f0:
            break
        if x <= f1:
            return old_end + len(JOIN) + (x - f0) if infile == 1 else m0 + (x - f0) if infile == 0 else m0
        file_at, merged_at = f1, new_end
    return merged_at + (x - file_at)


def _gone(
    block: _Block, marks: dict[str, list[MarkEntry]], where: list[tuple[int, int, int, int, int, int | None]], src: str
) -> list[MarkEntry]:
    """The empty marks the document draws in the block, where an annotation's words are gone (`versions.py`), as places of the merged text."""
    from dataclasses import replace

    seen: set[tuple[str, int]] = set()
    out: list[MarkEntry] = []
    for entries in marks.values():
        for e in entries:
            if (
                not e.gone
                or e.file != block.path
                or not block.start <= e.start <= block.end
                or (e.ann_id, e.start) in seen
            ):
                continue
            seen.add((e.ann_id, e.start))
            at = _from_file(e.start, where, block.start)
            out.append(replace(e, file=src, start=at, end=at, in_doc=None))
    return out


_START_TAG = re.compile(r"<([A-Za-z][\w-]*)\b([^>]*)>")


def _ids(elements: list[_Element], path: str) -> dict[str, str]:
    """The ids of the document's own elements in a file, by their `data-src`."""
    return {f"{path}:{e.start}:{e.end}": e.ident for e in elements if e.ident}


def _in_document(
    html: str, block: _Block, where: list[tuple[int, int, int, int, int, int | None]], src: str, ids: dict[str, str]
) -> str:
    """The merged block in the document's terms: each element's `data-src` as the file's own offsets where the file holds its words, and none on words it does not hold yet; and the id the document's element at the same place carries."""

    def tag(m: re.Match[str]) -> str:
        attrs = m.group(2)
        found = re.search(rf'\sdata-src="{re.escape(src)}:(\d+):(\d+)"', attrs)
        if found is None:
            return m.group(0)
        a, b = _range_to_file(int(found.group(1)), int(found.group(2)), where, block.start)
        if a is None or b is None:
            attrs = attrs[: found.start()] + ' data-new="true"' + attrs[found.end() :]
        else:
            at = f"{block.path}:{a}:{b}"
            attrs = attrs[: found.start()] + f' data-src="{at}"' + attrs[found.end() :]
            if at in ids and not re.search(r'\sid="', attrs):
                attrs += f' id="{ids[at]}"'
        return f"<{m.group(1)}{attrs}>"

    return _START_TAG.sub(tag, html)


def _marks(
    result: ScanResult,
    block: _Block,
    where: list[tuple[int, int, int, int, int, int | None]],
    resolved: list[Any],
    src: str,
    merged: str,
) -> list[MarkEntry]:
    """The annotations on the block's words: on the kept words, and each one a change touches again on the new words."""
    from loom.records.store import Records

    out: list[MarkEntry] = []
    for res in resolved:
        a = res.annotation
        node = result.nodes.get(res.target)
        if res.span is None or res.detached or node is None or node.file != block.path or a.in_reply_to:
            continue
        span = Records.to_file_span(Records.own_pieces(result, node)[1], res.span)
        if span is None or not (block.start <= span[0] and span[1] <= block.end):
            continue
        lo, hi = span
        touched = [w for w in where if (w[0] < hi and lo < w[1]) or (lo == hi and w[0] <= lo <= w[1])]
        if not touched:
            x, y = _plain(lo, where, block.start), _plain(hi, where, block.start)
            if x < y:
                out.append(MarkEntry(a.id, merged[x:y], src, x, y))
            continue
        # the kept words up to the change's old side's end, and from its new side on, moved
        x = _plain(lo, where, block.start) if lo < touched[0][0] else touched[0][2]
        y = touched[-1][3]
        nx = touched[0][3] + len(JOIN)
        ny = _plain(hi, where, block.start) if hi > touched[-1][1] else touched[-1][4]
        for s0, s1, moved in ((x, y, False), (nx, ny, True)):
            s0, s1 = _inward(merged, s0, s1)
            if s0 < s1:
                out.append(MarkEntry(a.id, merged[s0:s1], src, s0, s1, moved=moved))
    return out


def _inward(text: str, a: int, b: int) -> tuple[int, int]:
    """`a`..`b` less the space and the joiner either side."""
    while a < b and (text[a].isspace() or text.startswith(JOIN, a)):
        a += len(JOIN) if text.startswith(JOIN, a) else 1
    while b > a and (text[b - 1].isspace() or text[max(0, b - len(JOIN)) : b] == JOIN):
        b -= len(JOIN) if text[max(0, b - len(JOIN)) : b] == JOIN else 1
    return a, b


def attach_pending(
    result: ScanResult,
    records: Records,
    renderer: FragmentRenderer,
    manifest: dict[str, Any],
    files: dict[str, str | bytes],
    marks: dict[str, list[MarkEntry]] | None = None,
) -> None:
    """Publish every change waiting on the person as `manifest["changes"]`, each with its block drawn under `fragments/changes/` and its patch under `changes/`, the look's time as `changes_since`, and the suggested edits as `suggested_edits`.

    Parameters
    ----------
    result : ScanResult
        The scan the build renders.
    records : Records
        The quilt's records, which give the annotations drawn on each block.
    renderer : FragmentRenderer
        The build's renderer, whose previews make the blocks and each change's new text.
    manifest : dict
        The manifest, its annotations written.
    files : dict of str to str or bytes
        The build's files; the blocks and patches are added.
    marks : dict of str to list of MarkEntry, optional
        The marks the document's fragments carry, by node (`build._marks_by_node`), whose empty marks each block carries too.
    """
    from loom.looks import read_look
    from loom.pending import in_place, look_texts, patch_of, reviewer, suggested
    from loom.records.edits import replay
    from loom.records.store import render_markdown

    who = reviewer(result)
    look = read_look(result.quilt.root, who) if who and result.quilt.config.track_edits else None
    if look is not None:
        manifest["changes_since"] = {"who": look.who, "when": look.when}
    changes = (in_place(result, who) if who else []) + suggested(result)
    texts = look_texts(result, who) if who else None
    then = texts[0] if texts else {}
    rows: dict[str, dict[str, Any]] = {}
    for c in changes:
        row = c.to_dict()
        row.update({"new_html": None, "comment_html": render_markdown(c.comment) if c.comment else None})
        # where its own words stand in the source, which a viewer marks in the margin when it has no block
        place = (
            {"src": f"{c.path}:{c.at[0]}:{c.at[1]}"} if c.path and (c.kind == "edit" or c.state != "unplaced") else None
        )
        row.update({"block": None, "place": place, "diff": None})
        patch = patch_of(result, c, who)
        if patch:
            row["diff"] = f"{DIFFS}/{c.id}.diff"
            files[row["diff"]] = patch
        rows[c.id] = row
    records_out: dict[str, Any] = {}
    for edit in sorted(replay(result.quilt.root)[0], key=lambda e: e.created):
        record = edit.to_dict()
        record["author"] = {**record["author"], "label": edit.author_id}
        record["with_html"] = None
        record["comment_html"] = render_markdown(edit.comment) if edit.comment else None
        records_out[edit.id] = record
        _ask_new(
            result,
            renderer,
            edit.target_key,
            edit.with_text,
            [(record, "with_html"), *([(rows[edit.id], "new_html")] if edit.id in rows else [])],
        )
    for c in changes:
        if c.kind == "edit":
            _ask_new(result, renderer, c.key or "", c.new, [(rows[c.id], "new_html")])
    resolved = records.resolved(result)
    drawn = [c for c in changes if c.kind == "edit" or c.state in ("ready", "taken")]
    found: dict[str, list[_Element]] = {}

    def elements(path: str) -> list[_Element]:
        if path not in found:
            found[path] = _elements(result, manifest, files, path)
        return found[path]

    blocks, _structural = _blocks(result, drawn, then, elements)
    for block in blocks:
        _draw(result, renderer, block, rows, resolved, files, marks or {}, _ids(elements(block.path), block.path))
    manifest["changes"] = list(rows.values())
    manifest["suggested_edits"] = records_out


def _ask_new(
    result: ScanResult, renderer: FragmentRenderer, key: str, text: str, into: list[tuple[dict[str, Any], str]]
) -> None:
    """Ask for new text made by TeX in the terms of `key`, else the default document, set into each `(row, field)` when the build's previews are made; None when TeX refuses it, so the viewer shows the TeX as it is.

    New text may be a whole theorem and its proof, which only TeX reads: the viewer's own prose renderer handles a sentence, and hands `\\begin{theorem}` to MathJax, which draws it as an error.
    """
    from loom.records.edits import node_of

    node = node_of(result, key) if key else None
    node = node or result.nodes.get(result.default_master or "")
    if not text.strip() or node is None:
        return
    later = renderer.previews.ask(node.key, text.strip(), None, [])

    def took(html: str) -> None:
        for row, name in into:
            row[name] = None if html.startswith('<pre class="source"') else html

    renderer.previews.on_made(later, took)


def _draw(
    result: ScanResult,
    renderer: FragmentRenderer,
    block: _Block,
    rows: dict[str, dict[str, Any]],
    resolved: list[Any],
    files: dict[str, str | bytes],
    marks: dict[str, list[MarkEntry]],
    ids: dict[str, str],
) -> None:
    """Ask for one block's merged text made by TeX, and set each of its changes' `block` to it: its annotations, the document's empty marks in it, the document's offsets and ids put in once it is made."""
    text = result.files[block.path].text
    merged, spans, where = _merged(text, block)
    names = [" ".join(p.ids) for p in block.pieces]
    digest = hashlib.sha256(repr((block.path, merged, spans, names)).encode()).hexdigest()[:16]
    path = f"{FRAGMENTS}/{digest}.html"
    said = {"src": f"{block.path}:{block.src[0]}:{block.src[1]}", "fragment": path}
    for p in block.pieces:
        for cid in p.ids:
            if cid in rows:
                rows[cid]["block"] = said
    files[path] = ""
    later = renderer.previews.ask(block.key, merged, None, spans)

    def took(html: str) -> None:
        html = re.sub(r'data-change="(\d+)"', lambda m: f'data-change="{names[int(m.group(1))]}"', html)
        found = _PREVIEW_SRC.search(html)
        if found is None:
            files[path] = html
            return
        src = found.group(1)
        html = place_marks(html, _marks(result, block, where, resolved, src, merged))
        html = place_marks(html, _gone(block, marks, where, src))
        html = _in_document(html, block, where, src, ids)
        if ' data-src="' not in html:
            # TeX4ht placed nothing of a text on one line: the block is the leaf, by its own range
            at = f"{block.path}:{block.src[0]}:{block.src[1]}"
            extra = f' data-src="{at}"' + (f' id="{ids[at]}"' if at in ids else "")
            html = re.sub(r"^(\s*<[A-Za-z][\w-]*)", lambda m: m.group(1) + extra, html, count=1)
        # a block TeX refused shows its source, where the joiner is no part of what the person wrote
        files[path] = html.replace(esc(JOIN), "") if html.startswith('<pre class="source"') else html

    renderer.previews.on_made(later, took)
