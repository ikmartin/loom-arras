"""Previews of a key's text, made by TeX under the preamble they are read in, with the words that changed marked afterwards.

A comparison shows the text a key had beside the text it has; each side is made as a snippet (`snippets`), shaped as a page is, and then each rendered word is aligned with the source word it came from (`tex.align`), so a word whose source changed is wrapped in `mark.review-changed`, a formula or display whose source changed takes the class, and a deletion leaves a `span.review-change-point`. A side TeX refused shows its source, its changed spans marked the same way.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import posixpath
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from loom.render.markup import esc
from loom.render.publish import write_atomic
from loom.scan.model import SourceFile
from loom.scan.source import blank_comments
from loom.tex.align import rendered_words, source_words

if TYPE_CHECKING:
    from loom.render.fragments import FragmentRenderer, Later, Owner
    from loom.render.fromhtml import El

_TOKEN = re.compile(r"[^\W_][\w'’]*", re.UNICODE)
_INLINE = re.compile(r"\\\((.*?)\\\)|(?<![\\$])\$(?!\$)((?:\\.|[^$\\])+?)\$", re.DOTALL)
_POINT = '<span class="review-change-point" aria-label="edit point"></span>'


def preview_html(r: FragmentRenderer, group: Sequence[Later]) -> list[str]:
    """Each preview of `group`, which share a document and a preamble, made in one batch: from `.loom/build/cache/previews/` where made before, else by TeX."""
    from loom.render.fragments import _preview_owner
    from loom.render.snippets import render_snippets

    if not group:
        return []
    owner = _preview_owner(r, group[0])
    preamble = group[0].preamble if group[0].preamble is not None else owner.preamble
    if "\\documentclass" not in preamble:
        preamble = "\\documentclass{amsart}\n" + preamble
    keys = [
        hashlib.sha256(json.dumps([r.salt, p.key, owner.key, p.text, preamble, p.spans]).encode()).hexdigest()[:32]
        for p in group
    ]
    cache = r.plan.cache / "previews"
    out: list[str | None] = [
        (cache / f"{k}.html").read_text(encoding="utf-8") if (cache / f"{k}.html").is_file() else None for k in keys
    ]
    todo = [i for i, o in enumerate(out) if o is None]
    if not todo:
        return [o or "" for o in out]
    made = render_snippets(
        r.result.quilt.root,
        owner.base,
        preamble,
        [group[i].text for i in todo],
        r.plan.cache / "snippets",
        envs=r.envs(owner),
        engine=owner.engine,
        aux=owner.aux,
        tex=r.plan.tex,
    )
    for i, s in zip(todo, made.made, strict=True):
        p = group[i]
        markup = (
            _shaped(r, owner, p, s.html) if s.html is not None else marked_source(_named(owner, p), p.text, p.spans)
        )
        # drawn beside a live document whose anchors carry the same labels
        markup = "\n".join(line.rstrip() for line in re.sub(r'(?<=\s)id="[^"]*"', "", markup).split("\n"))
        # a side TeX refused is remembered; one the machine could not make, with no TeX4ht, is made again next time
        if s.html is not None or not s.error.startswith(("TeX is not run", "make4ht", "TeX4ht made no page")):
            write_atomic(cache / f"{keys[i]}.html", markup)
        out[i] = markup
    return [o or "" for o in out]


def _shaped(r: FragmentRenderer, owner: Owner, p: Later, made: str) -> str:
    """One preview's snippet shaped as a page is, under a file of its own beside the owner's, and its changed words marked."""
    from loom.render.fragments import _from_tex, _lines_in
    from loom.render.fromhtml import DocumentHtml, Page, html_of

    file = _named(owner, p)
    clean = blank_comments(p.text)
    src = SourceFile(file, Path(file), p.text, clean, "utf-8", False)
    page = Page(
        _lines_in(made, posixpath.relpath(file, owner.base or "."), 1),
        {},
        "",
        where=r.plan.cache / "snippets",
        normalised=True,
    )
    doc = DocumentHtml(r, owner, page, only=[], files={file: src}, pairs={})
    macros = {m.name: m.body for m in owner.macros.values()}
    body = mark_changes(doc.body, file, clean, p.spans, macros)
    return _from_tex("".join(html_of(k) for k in body))


def _named(owner: Owner, p: Later) -> str:
    """The file a preview's text stands in, of its own, beside the owner's: what its `data-src` names."""
    return posixpath.join(owner.base, "review-" + hashlib.sha256(p.text.encode()).hexdigest()[:20] + ".tex")


#: A change's side, as `span.change[data-side]` names it.
SIDES = ("old", "new")


def _label(spans: Sequence[Sequence[int]], a: int, b: int) -> tuple[int, int] | bool | None:
    """What marks source `a`..`b`: a change's `(n, side)` for a span of four, `[start, end, n, side]`; True for a changed span of two; None for none."""
    for span in spans:
        lo, hi = span[0], span[1]
        if (lo < b and hi > a) or (lo == hi and a < lo < b):
            return (span[2], span[3]) if len(span) == 4 else True
    return None


def _open(label: tuple[int, int] | bool) -> tuple[str, str]:
    """The tag that opens a marked run and the one that closes it."""
    if label is True:
        return '<mark class="review-changed">', "</mark>"
    assert isinstance(label, tuple)
    return f'<span class="change" data-change="{label[0]}" data-side="{SIDES[label[1]]}">', "</span>"


def marked_source(file: str, text: str, spans: Sequence[Sequence[int]]) -> str:
    """`text`, standing in `file`, as `pre.source` with its spans marked: a side TeX refused.

    A span of two, `[start, end]`, is a change `mark.review-changed` shows, a point an edit point; a span of four, `[start, end, n, side]`, is the old or new words of change `n`, wrapped in `span.change[data-change][data-side]`.
    """
    cuts = sorted({0, len(text), *(x for span in spans for x in span[:2] if 0 <= x <= len(text))})
    points = [span for span in spans if len(span) == 2 and span[0] == span[1]]
    out: list[str] = []
    for a, b in zip(cuts, cuts[1:], strict=False):
        if any(span[0] == a for span in points):
            out.append(_POINT)
        piece = esc(text[a:b])
        label = _label(spans, a, b)
        if label is None or label is False:
            out.append(piece)
        else:
            head, tail = _open(label)
            out.append(f"{head}{piece}{tail}")
    if any(span[0] == len(text) for span in points):
        out.append(_POINT)
    return f'<pre class="source" data-src="{file}:0:{len(text)}">{"".join(out)}</pre>'


def mark_changes(
    body: list[El | str], file: str, clean: str, spans: Sequence[Sequence[int]], macros: Mapping[str, str]
) -> list[El | str]:
    """`body` with what changed in its source marked: each rendered word aligned with the source word it came from, a formula with the source formula it is, a display by its `data-src`.

    A span of two, `[start, end]`, marks changed words `mark.review-changed` and a point an edit point; a span of four, `[start, end, n, side]`, the old or new words of change `n`, wrapped in `span.change[data-change][data-side]`, a formula or display taking the class `change` and the two attributes.
    """
    from loom.render.fromhtml import El, _walk, text_of

    if not spans:
        return body

    def changed(a: int, b: int) -> tuple[int, int] | bool | None:
        return _label(spans, a, b)

    def put(el: El, label: tuple[int, int] | bool | None) -> None:
        if label is True:
            el.attrs["class"] += " review-changed"
        elif isinstance(label, tuple):
            el.attrs["class"] += " change"
            el.attrs["data-change"], el.attrs["data-side"] = str(label[0]), SIDES[label[1]]

    # the formulas, in order, against the source's
    formulas = [m for m in _INLINE.finditer(clean)]
    k = 0
    for top in body:
        for el in _walk(top) if isinstance(top, El) else ():
            if "math" not in el.classes:
                continue
            if "display" in el.classes or el.tag == "figure":
                at = el.attrs.get("data-src", "")
                f, _, rest = at.partition(":")
                a, _, b = rest.partition(":")
                if f == file and a.isdigit() and b.isdigit():
                    put(el, changed(int(a), int(b)))
                continue
            want = re.sub(r"\s+", "", re.sub(r"^\\\(|\\\)$", "", text_of(el).strip()))
            while k < len(formulas) and re.sub(r"\s+", "", formulas[k].group(1) or formulas[k].group(2) or "") != want:
                k += 1
            if k < len(formulas):
                put(el, changed(formulas[k].start(), formulas[k].end()))
                k += 1
    # the words, in order, against the source's
    tokens: list[tuple[El, int, int, int, str]] = []  # parent, kid index, start, end in that string, folded word
    for top in body:
        if isinstance(top, El):
            _tokens(top, tokens)
    words = source_words(clean, macros)
    matcher = difflib.SequenceMatcher(None, [w.text for w in words], [t[4] for t in tokens], autojunk=False)
    found: list[tuple[int, int] | None] = [None] * len(tokens)
    for blk in matcher.get_matching_blocks():
        for d in range(blk.size):
            w = words[blk.a + d]
            found[blk.b + d] = (w.start, w.end)
    # an unmatched word stands for the source between the matched words around it
    lo = 0
    marked: list[tuple[int, int] | bool | None] = []
    for i, t in enumerate(found):
        if t is not None:
            lo = t[1]
            marked.append(changed(*t))
            continue
        hi = next((x[0] for x in found[i + 1 :] if x is not None), len(clean))
        marked.append(changed(lo, max(lo + 1, hi)))
    points: dict[int, int] = {}  # token index after which an edit point stands -> how many
    for span in spans:
        a, b = span[0], span[1]
        if a != b or len(span) == 4:
            continue
        after = max((i for i, t in enumerate(found) if t is not None and t[1] <= a), default=-1)
        points[after] = points.get(after, 0) + 1
    by_string: dict[tuple[int, int], list[tuple[int, int, tuple[int, int] | bool | None, int]]] = {}
    parents: dict[int, El] = {}
    for i, (parent, kid, a, b, _w) in enumerate(tokens):
        parents[id(parent)] = parent
        by_string.setdefault((id(parent), kid), []).append((a, b, marked[i], points.get(i, 0)))
    for (pid, kid), toks in sorted(by_string.items(), key=lambda x: (x[0][0], -x[0][1])):
        parent = parents[pid]
        s = parent.kids[kid]
        assert isinstance(s, str)
        parent.kids[kid : kid + 1] = _wrap(s, toks)
    if -1 in points and body:
        first = next((k for k in body if isinstance(k, El)), None)
        if first is not None:
            first.kids[0:0] = [El("span", {"class": "review-change-point", "aria-label": "edit point"}, [])] * points[
                -1
            ]
    for top in body:
        if isinstance(top, El):
            _said_sides(top, spans)
    return body


def _said_sides(el: El, spans: Sequence[Sequence[int]]) -> None:
    """Wrap each element `el` holds that TeX made of a command, a reference or a citation, whose source (`data-at`) lies in a side of a change, in that side's `span.change`: it has no words of its own to be marked by."""
    from loom.render.fromhtml import El

    for i, kid in enumerate(el.kids):
        if not isinstance(kid, El):
            continue
        at = kid.attrs.get("data-at", "")
        label = _label(spans, int(at), int(at) + 1) if at.isdigit() and "math" not in kid.classes else None
        if isinstance(label, tuple):
            attrs = {"class": "change", "data-change": str(label[0]), "data-side": SIDES[label[1]]}
            el.kids[i] = El("span", attrs, [kid])
            continue
        if "change" not in kid.classes:
            _said_sides(kid, spans)


def _tokens(el: El, out: list[tuple[El, int, int, int, str]]) -> None:
    """Every word of `el`'s own strings, outside what TeX made and outside mathematics, with where it stands."""
    from loom.render.fromhtml import El

    if "data-made" in el.attrs or "math" in el.classes or "env-label" in el.classes or el.tag == "summary":
        return
    for i, k in enumerate(el.kids):
        if isinstance(k, El):
            _tokens(k, out)
            continue
        for m in _TOKEN.finditer(k):
            for w in rendered_words(m.group(0)):
                out.append((el, i, m.start(), m.end(), w))


def _wrap(s: str, toks: list[tuple[int, int, tuple[int, int] | bool | None, int]]) -> list[El | str]:
    """`s` with each run of words marked alike, and the space between them, wrapped: in `mark.review-changed`, or in `span.change` for a change's side; and edit points after the words they follow."""
    from loom.render.fromhtml import El

    out: list[El | str] = []
    pos = 0
    run: tuple[int, int] | None = None
    held: tuple[int, int] | bool | None = None

    def flush() -> None:
        nonlocal run
        if run is not None:
            if held is True:
                out.append(El("mark", {"class": "review-changed"}, [s[run[0] : run[1]]]))
            elif isinstance(held, tuple):
                attrs = {"class": "change", "data-change": str(held[0]), "data-side": SIDES[held[1]]}
                out.append(El("span", attrs, [s[run[0] : run[1]]]))
            run = None

    seen: set[tuple[int, int]] = set()
    for a, b, marked, points in toks:
        if (a, b) in seen:
            continue
        seen.add((a, b))
        if marked and run is not None and marked != held:
            flush()
        if marked:
            if run is None:
                if a > pos:
                    out.append(s[pos:a])
                run = (a, b)
                held = marked
            else:
                run = (run[0], b)
            pos = b
        else:
            flush()
            if b > pos:
                out.append(s[pos:b])
            pos = b
        if points:
            flush()
            out += [El("span", {"class": "review-change-point", "aria-label": "edit point"}, []) for _ in range(points)]
    flush()
    if pos < len(s):
        out.append(s[pos:])
    return [k for k in out if not (isinstance(k, str) and not k)]
