"""A document's fragments from the HTML TeX made of it (plan 0.29.3): TeX decides what the document says, loom where each part came from and what it is.

`page_for` finds a document's page when it was made from the sources as they stand; until a compile lands, a document has none and the translator renders it. `DocumentHtml` gives the page the dialect's shape once per build. Each node TeX4ht stamped becomes the statement or proof the scan knows, wrapped as the dialect wraps it around TeX's own content; each heading whose words are a section's title opens that section; each reference names its target and each citation its key; each display is the source's, set as the translator sets one, numbered from the PDF's aux; and each block TeX read carries `data-src` where `tex.align` places its words. A node's own fragment is cut from its document's.
"""

from __future__ import annotations

import hashlib
import html
import json
import posixpath
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import TYPE_CHECKING

from loom.paths import document_build
from loom.render.assets import publish_graphic
from loom.render.convert import Converter, RenderContext, slug
from loom.render.normalise import normalise
from loom.scan.nodes import NodeRec
from loom.scan.sections import starred_at
from loom.scan.tokenize import read_args
from loom.tex.align import Source, rendered_words, source_words
from loom.tex.tex4ht import REPAIRED, SOURCE_SUFFIXES, SOURCES, definitions

if TYPE_CHECKING:
    from loom.render.fragments import FragmentRenderer
    from loom.scan.scan import ScanResult

VOID = frozenset({"br", "hr", "img"})
_HEADING = re.compile(r"h[1-6]")
_SECTION = re.compile(r"\\(part|chapter|section|subsection|subsubsection|paragraph|subparagraph)\*?\s*")
_DISPLAY = re.compile(r"\\begin\s*\{([A-Za-z]+\*?)\}|\\\[")


@dataclass
class Page:
    """A document's page as TeX4ht made it, current with its sources: the HTML, the displays it holds as placeholders, and a digest for the fragment cache."""

    html: str
    displays: dict[str, str]
    digest: str


def page_for(result: ScanResult, master: str) -> Page | None:
    """`master`'s page when the files it reads are as they were when the page was made; None when there is none, or when one has changed since."""
    root = result.quilt.root
    where = root / document_build(master) / "html"
    page = where / f"{Path(master).stem}.html"
    said = where / SOURCES
    if not page.is_file() or not said.is_file():
        return None
    try:
        read: dict[str, str] = json.loads(said.read_text(encoding="utf-8"))
        held = json.loads((where / REPAIRED).read_text(encoding="utf-8")) if (where / REPAIRED).is_file() else []
    except (OSError, ValueError):
        return None
    exp = result.expansions.get(master)
    closure = result.closures.get(master)
    for f in {master, *(exp.reached if exp else ()), *(closure.files if closure else ())}:
        if Path(f).suffix.lower() not in SOURCE_SUFFIXES:
            continue
        current = root / f
        if f not in read or not current.is_file() or hashlib.sha256(current.read_bytes()).hexdigest() != read[f]:
            return None
    text = page.read_text(encoding="utf-8", errors="replace")
    digest = hashlib.sha256(text.encode("utf-8") + said.read_bytes() + json.dumps(held).encode()).hexdigest()
    return Page(text, {str(i): r.get("tex", "") for i, r in enumerate(held)}, digest)


# ---- a small tree, enough to reshape what `normalise` wrote --------------------------------------------------------------


@dataclass
class El:
    tag: str
    attrs: dict[str, str]
    kids: list[El | str] = field(default_factory=list)

    @property
    def classes(self) -> list[str]:
        return self.attrs.get("class", "").split()


class _Tree(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = El("root", {})
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        el = El(tag, {k: v or "" for k, v in attrs})
        self.stack[-1].kids.append(el)
        if tag not in VOID:
            self.stack.append(el)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack[-1].kids.append(El(tag, {k: v or "" for k, v in attrs}))

    def handle_endtag(self, tag: str) -> None:
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data: str) -> None:
        self.stack[-1].kids.append(data)


def parse(fragment: str) -> El:
    t = _Tree()
    t.feed(fragment)
    t.close()
    return t.root


def html_of(node: El | str) -> str:
    if isinstance(node, str):
        return html.escape(node, quote=False)
    attrs = "".join(f' {k}="{html.escape(v, quote=True)}"' for k, v in node.attrs.items())
    if node.tag in VOID:
        return f"<{node.tag}{attrs}>"
    return f"<{node.tag}{attrs}>{''.join(html_of(k) for k in node.kids)}</{node.tag}>"


def text_of(node: El | str, *, made: bool = True) -> str:
    """The text inside `node`; with `made` False, none of what TeX made or of mathematics."""
    if isinstance(node, str):
        return node
    if not made and ("data-made" in node.attrs or "math" in node.classes):
        return ""
    return "".join(text_of(k, made=made) for k in node.kids)


# ---- the shape --------------------------------------------------------------------------------------------------------


class DocumentHtml:
    """One document's page in the dialect's shape, and each of its nodes' fragments cut from it.

    Parameters
    ----------
    renderer : FragmentRenderer
        The build's renderer, whose scan, numbers and contexts this reads.
    master : str
        The document.
    page : Page
        Its page, current with its sources (`page_for`).
    """

    def __init__(self, renderer: FragmentRenderer, master: str, page: Page) -> None:
        self.r = renderer
        self.result = renderer.result
        self.master = master
        self.base = self.result.base_of(master)
        self.node = renderer.asm.nodes[master]
        self.ctx = renderer._context(self.node, "master")
        closure = self.result.closures.get(master)
        self.macros, self.environments = definitions(closure)
        self.heads = frozenset(
            w for t in (closure.taxa.values() if closure else ()) for w in rendered_words(t.name)
        ) | {"proof"}
        self._sources: dict[str, tuple[Source, list[int]] | None] = {}
        self._contexts: dict[str, RenderContext] = {}
        self.stamps: dict[tuple[str, int], str] = {}
        for key, n in self.result.nodes.items():
            if n.kind in ("environment", "proof") and master in n.reached_by and n.file in self.result.files:
                self.stamps.setdefault((n.file, self._line(n.file, n.start)), key)
        self.stamped: set[str] = set()
        # the blocks around the one being shaped, innermost last: file, start and end (None when the block has no span)
        self._where: list[tuple[str, int, int | None]] = []
        # each block's references, citations and formulas met so far, by what they name
        self._met: dict[tuple[str, int, str], int] = {}
        self._italic = False  # inside a statement set in italic, where upright text is the emphasized
        self._displays_taken: set[tuple[str, int]] = set()  # the source displays already given to one TeX4ht set
        self._next_section = 0
        self._section_list = self._section_nodes()
        tree = parse(normalise(page.html, page.displays).html)
        self.body = self._sections(self._inclusions(self._shape(tree)))
        for k in self.body:
            for e in _walk(k) if isinstance(k, El) else ():
                e.attrs.pop("data-head", None)  # what kind of heading TeX made, needed only to find the sections
        self.nodes: dict[str, str] = {}
        self._collect(self.body)
        #: every statement and proof the scan finds in the document is a node on the page; a page missing one (beamer's frames) is left to the translator
        self.complete = set(self.stamps.values()) <= self.stamped

    # -- where things are --
    def _line(self, file: str, offset: int) -> int:
        return self.result.files[file].text.count("\n", 0, offset) + 1

    def _rel(self, file: str) -> str:
        return self.master if not file else posixpath.normpath(posixpath.join(self.base, file))

    def _source(self, rel: str) -> tuple[Source, list[int]] | None:
        if rel not in self._sources:
            src = self.result.files.get(rel)
            self._sources[rel] = (
                (
                    Source(src.clean, self.macros, self.environments),
                    [0] + [m.end() for m in re.finditer("\n", src.clean)],
                )
                if src is not None
                else None
            )
        return self._sources[rel]

    def _offset(self, rel: str, line: int) -> int:
        known = self._source(rel)
        if known is None:
            return 0
        lines = known[1]
        return lines[min(max(line - 1, 0), len(lines) - 1)]

    def _at(self, el: El) -> tuple[str, int] | None:
        at = el.attrs.get("data-at")
        if at is None:
            return None
        file, _, line = at.rpartition(":")
        return self._rel(file), int(line) if line.isdigit() else 0

    def _context_for(self, rel: str) -> RenderContext:
        """The render context of the file `rel`, whose text a display's offsets index; the document's own for one with no node of its own."""
        if rel not in self._contexts:
            n = self.r.asm.nodes.get(rel)
            self._contexts[rel] = self.r._context(n, "master") if n is not None and rel != self.master else self.ctx
        return self._contexts[rel]

    # -- reshaping --
    def _shape(self, el: El) -> list[El | str]:
        """`el` and what is inside it in the dialect's shape: a list, since a wrapper TeX4ht made may be unwrapped."""
        cls = el.classes
        if el.tag == "div" and "node" in cls:
            return self._node(el)
        if "math" in cls:
            return [self._math(el)]
        if el.tag == "img":
            return [self._img(el)]
        place = self._place(el)
        at = self._at(el)
        if at is not None:
            rel, line = at
            start, end = (int(x) for x in place.rsplit(":", 2)[1:]) if place else (self._offset(rel, line), None)
            self._where.append((rel, start, end))
        try:
            kids = [k2 for k in el.kids for k2 in (self._shape(k) if isinstance(k, El) else [k])]
        finally:
            if at is not None:
                self._where.pop()
        if el.tag == "span" and "data-font" in el.attrs:
            emphasized = (el.attrs["data-font"] == "rm") == self._italic
            return [El("em", {}, kids)] if emphasized else kids
        kids = _paren_equations(kids)
        if el.tag == "a" and "ref" in cls:
            return [self._ref(el, kids)]
        if el.tag == "span" and "cite" in cls:
            return [self._cite(el, kids)]
        if el.tag == "root":
            return kids
        if place is None and el.tag in _ENVIRONS:
            place = self._list_source(kids, el, _ENVIRONS[el.tag])
        if place is None and el.tag in _CONTAINERS:
            place = _span_of(kids)
        attrs = {k: v for k, v in el.attrs.items() if k not in ("data-at", "data-made")}
        if place is not None:
            attrs["data-src"] = place
        return [El(el.tag, attrs, kids)]

    def _place(self, el: El) -> str | None:
        """`FILE:START:END` for a block whose words stand unbroken in its source, else None."""
        at = self._at(el)
        if at is None or "math" in el.classes:
            return None
        rel, line = at
        words = rendered_words(_own(el))
        known = self._source(rel)
        if len(words) < 2 or known is None:
            return None
        got = known[0].place(words, self._offset(rel, line), heads=self.heads)
        if got is None or not got.exact:
            return None
        start, end = _edge_formulas(self.result.files[rel].clean, got.start, got.end, el)
        return f"{rel}:{start}:{end}"

    def _img(self, el: El) -> El:
        """A picture: one TeX4ht drew, addressed beside its page in the build; else the graphic the source includes there, published as the translator publishes it."""
        src = el.attrs.get("src", "")
        page = self.result.quilt.root / document_build(self.master) / "html"
        build = self.r.plan.svg_out.parent
        if src and (page / src).is_file() and page.is_relative_to(build):
            return El("img", {"src": f"{page.relative_to(build).as_posix()}/{src}", "alt": ""}, [])
        m = self._command(_graphic_stem(src), _GRAPHICS, lambda m: [_graphic_stem(m.group(1))])
        if m is not None:
            rel, _err = publish_graphic(self.result.quilt.root, m.group(1).strip(), self.r.plan.svg_out, self.base)
            if rel is not None:
                return El("img", {"src": rel, "alt": ""}, [])
        return El("img", {"src": src, "alt": el.attrs.get("alt", "")}, [])

    def _ref(self, el: El, kids: list[El | str]) -> El:
        label = el.attrs.get("data-label", "")
        found = self._command(label, _REFS, lambda m: [m.group(2).strip()])
        command = found.group(0) if found is not None else f"\\ref{{{label}}}"
        target = self.ctx.labels.get(label)
        if target is None:
            return El("a", {"class": "ref ref-dangling", "data-target": label, "data-tex": command}, kids)
        eq = target in self.ctx.equations or command.startswith("\\eqref")
        attrs = {
            "class": "ref ref-eq" if eq else "ref",
            "data-target": target,
            "data-tex": command,
            "href": "#" + slug(target),
        }
        return El("a", attrs, kids)

    def _command(
        self, name: str, pattern: re.Pattern[str], names: Callable[[re.Match[str]], list[str]]
    ) -> re.Match[str] | None:
        """The command in the source of the block being shaped that names `name`, the next one after those already met there."""
        if not self._where:
            return None
        rel, offset, end = self._where[-1]
        src = self.result.files.get(rel)
        if src is None:
            return None
        seen = self._met.get((rel, offset, name), 0)
        self._met[(rel, offset, name)] = seen + 1
        count = 0
        for m in pattern.finditer(src.clean, offset, end if end is not None else offset + _UNPLACED_REACH):
            if name in names(m):
                if count == seen:
                    return m
                count += 1
        return None

    def _list_source(self, kids: list[El | str], el: El, envs: re.Pattern[str]) -> str | None:
        """A list's place: the list environment its first item is in, from `\\begin` to `\\end`, found from the first item placed, else from the line TeX4ht said the first item began on."""
        first = _span_of(kids)
        if first is not None:
            rel, start, _end = first.rsplit(":", 2)
            upto = int(start)
        else:
            # an item's line is where TeX4ht last said it was, at or before the list: the first list after it
            at = next((self._at(e) for e in _walk(el) if e is not el and "data-at" in e.attrs), None)
            known = self.result.files.get(at[0]) if at is not None else None
            if at is None or known is None:
                return None
            rel = at[0]
            ahead = envs.search(known.clean, self._offset(rel, at[1]))
            upto = ahead.end() if ahead is not None else 0
        src = self.result.files.get(rel)
        if src is None:
            return None
        opened = [m for m in envs.finditer(src.clean, 0, upto)]
        if not opened:
            return None
        m = opened[-1]
        close = re.compile(r"\\end\s*\{" + re.escape(m.group(1)) + r"\}").search(src.clean, m.end())
        return f"{rel}:{m.start()}:{close.end()}" if close is not None else None

    def _math(self, el: El) -> El:
        """A formula: a display as the translator sets the source's, numbered from the aux, else TeX4ht's TeX with its labels out and its references numbered."""
        tex = text_of(el)
        if "inline" in el.classes:
            inner = re.sub(r"^\s*\\\(|\\\)\s*$", "", tex)
            # TeX4ht writes a formula back with a space after each command; the source's own TeX is what a quote copies
            m = self._command(_spaceless(inner), _INLINE, lambda m: [_spaceless(m.group(1) or m.group(2) or "")])
            if m is not None:
                inner = m.group(1) or m.group(2) or ""
            return El("span", {"class": "math inline"}, ["\\(" + Converter(self.ctx).math_text(inner) + "\\)"])
        at = self._at(el)
        found = self._display_source(at, tex) if at is not None else None
        if found is not None:
            rel, start, end, env = found
            conv = Converter(self._context_for(rel))
            made = (
                conv.display_env(env, start, end)
                if env
                else conv.display_block(self.result.files[rel].text[start + 2 : end - 2], start, end, None)
            )
            shaped = parse(made).kids
            if shaped and isinstance(shaped[0], El):
                display = shaped[0]
                label = display.attrs.get("data-label")
                target = self.ctx.labels.get(label) if label else None
                if target is not None:
                    # the anchor a reference to it names, `#sy-0100-eq-prose`, whichever node holds it
                    display.attrs["id"] = slug(target)
                return display
        body = re.sub(r"^\s*\\begin\s*\{[^}]*\}|\\end\s*\{[^}]*\}\s*$|^\s*\\\[|\\\]\s*$", "", tex)
        return El("div", {"class": "math display"}, ["\\[" + Converter(self.ctx).math_text(body) + "\\]"])

    def _cite(self, el: El, kids: list[El | str]) -> El:
        """A citation with its key, and its note and target read from the `\\cite` the block it stands in has for that key, at or after the block's line."""
        key = next((k.attrs.get("data-citekey", "") for k in _walk(el) if "cite-label" in k.classes), "")
        attrs = {"class": "cite", "data-citekey": key}
        m = self._command(key, _CITES, lambda m: [k.strip() for k in m.group(2).split(",")]) if key else None
        found = (
            (m.group(0), re.sub(r"[\s~]+", " ", m.group(1)).strip() if m.group(1) else None) if m is not None else None
        )
        if found is not None:
            command, note = found
            attrs["data-tex"] = command
            if note:
                attrs["data-postnote"] = note
                target = self.r._cite_target(key, note)
                if target:
                    attrs["data-target"] = target
        else:
            attrs["data-tex"] = f"\\cite{{{key}}}"
        return El("span", attrs, _unwrap(kids, "cite-label"))

    def _inclusions(self, kids: list[El | str]) -> list[El | str]:
        """Each included file's content between its start and end marks, at one level, wrapped as the inclusion it is; a mark with no partner there is dropped."""
        kids = _lift_marks(kids)
        out: list[El | str] = []
        i = 0
        while i < len(kids):
            k = kids[i]
            if isinstance(k, El) and "loom-file" in k.classes:
                depth, j = 0, i + 1
                while j < len(kids):
                    c = kids[j]
                    if isinstance(c, El) and "loom-file" in c.classes:
                        depth += 1
                    elif isinstance(c, El) and "loom-file-end" in c.classes:
                        if depth == 0:
                            break
                        depth -= 1
                    j += 1
                rel = self._rel(k.attrs.get("data-file", ""))
                inner = self._inclusions(kids[i + 1 : j])
                if j < len(kids) and rel in self.r.asm.nodes and rel in self.result.files:
                    size = len(self.result.files[rel].text)
                    out.append(
                        El(
                            "div",
                            {"class": "included", "data-key": rel, "data-file": rel, "data-src": f"{rel}:0:{size}"},
                            inner,
                        )
                    )
                else:
                    out += inner
                i = j + 1
                continue
            if isinstance(k, El) and "loom-file-end" in k.classes:
                i += 1
                continue
            if isinstance(k, El):
                k.kids = self._inclusions(k.kids)
            out.append(k)
            i += 1
        return out

    def _display_source(self, at: tuple[str, int], tex: str) -> tuple[str, int, int, str | None] | None:
        """Where in the source a display TeX4ht set begins and ends, with its environment (None for `\\[`): the one near the line it said that reads as it does, else the first of its kind from that line; never one already taken.

        TeX4ht dates a display by the paragraph it stands in, so two displays a short paragraph apart share a line, and only what they say tells them apart.
        """
        rel, line = at
        src = self.result.files.get(rel)
        if src is None:
            return None
        head = _DISPLAY.match(tex.strip())
        if head is None:
            return None
        env = head.group(1)
        pattern = re.compile(r"\\begin\s*\{" + re.escape(env) + r"\}") if env else re.compile(r"(?<!\\)\\\[")
        closing = re.compile(r"\\end\s*\{" + re.escape(env) + r"\}") if env else re.compile(r"(?<!\\)\\\]")
        said = self._offset(rel, line)
        want = _spaceless(tex)
        first: tuple[int, int] | None = None
        chosen: tuple[int, int] | None = None
        for m in pattern.finditer(src.clean, max(0, said - _DISPLAY_REACH), said + _UNPLACED_REACH):
            c = closing.search(src.clean, m.end())
            if c is None:
                break
            if (rel, m.start()) in self._displays_taken:
                continue
            if _spaceless(src.clean[m.start() : c.end()]) == want:
                chosen = (m.start(), c.end())
                break
            if first is None and m.start() >= said - 200:
                first = (m.start(), c.end())
        chosen = chosen or first
        if chosen is None:
            return None
        self._displays_taken.add((rel, chosen[0]))
        return (rel, chosen[0], chosen[1], env)

    def _node(self, el: El) -> list[El | str]:
        """A node TeX4ht stamped, as the statement or proof the scan knows; unwrapped when the scan knows none there."""
        file, line = el.attrs.get("data-file", ""), el.attrs.get("data-line", "")
        rel = self._rel(file)
        key = next(
            (
                self.stamps[(rel, int(line) + d)]
                for d in (0, 1, -1)
                if line.isdigit() and (rel, int(line) + d) in self.stamps
            ),
            None,
        )
        known = self.result.nodes.get(key) if key is not None else None
        # a statement in a plain style is set in italic, and a word emphasized in it upright
        italic, self._italic = (
            self._italic,
            (known is not None and known.kind == "environment" and (known.style or "plain") == "plain"),
        )
        inner: list[El | str] = []
        try:
            for k in el.kids:
                # TeX4ht's own wrapper of a theorem or a proof gives way to the dialect's
                if isinstance(k, El) and k.tag == "div" and {"env", "proof"} & set(k.classes):
                    inner += [k3 for k2 in k.kids for k3 in (self._shape(k2) if isinstance(k2, El) else [k2])]
                else:
                    inner += self._shape(k) if isinstance(k, El) else [k]
        finally:
            self._italic = italic
        if key is None:
            return inner
        self.stamped.add(key)
        n = self.result.nodes[key]
        head = _take_head(inner)
        src = f"{n.file}:{n.start}:{n.end}"
        if n.kind == "proof":
            said = re.sub(r"[.:\s]+$", "", html.unescape(text_of(head))).strip() if head is not None else ""
            attrs = {"class": "env env-proof", "id": slug(key)}
            if n.id:
                attrs["data-id"] = n.id
            attrs["data-key"] = key
            if n.of:
                attrs["data-of"] = n.of
            attrs["data-src"] = src
            attrs.update(_pairs(self.r, n))
            attrs["open"] = ""
            return [El("details", attrs, [El("summary", {"class": "env-label"}, [said or "Proof"]), *inner])]
        attrs = {"class": f"env env-{slug(n.taxon or n.env or 'env')}", "id": slug(key)}
        if n.id:
            attrs["data-id"] = n.id
        attrs.update({"data-key": key, "data-taxon": n.taxon or "", "data-style": n.style or "plain", "data-src": src})
        attrs.update(_pairs(self.r, n))
        if n.digest:
            attrs["data-macros"] = n.digest
        label = parse(f'<p class="env-label">{self.r._label_html(n, self.r._context(n, "master"))}</p>').kids
        return [El("div", attrs, [*label, *inner])]

    # -- sections --
    def _sections(self, kids: list[El | str]) -> list[El | str]:
        """The document's top level with each heading that opens one of the scan's sections wrapped with what follows it, to the next heading of its level or above."""
        sections = self._section_list
        out: list[El | str] = []
        open_: list[tuple[int, El]] = []
        for k in kids:
            if isinstance(k, El) and "included" in k.classes:
                k.kids = self._sections(k.kids)
                (open_[-1][1].kids if open_ else out).append(k)
                continue
            # a heading on its own line, or one run in at the head of a paragraph, as amsart sets a subsection
            run_in = _run_in(k)
            if isinstance(k, El) and (_HEADING.fullmatch(k.tag) or run_in is not None):
                if k.attrs.get("data-head") == "titleHead":
                    continue  # the document's title, which the fragment's own heading carries
                head = run_in if run_in is not None else k
                words = rendered_words(text_of(head, made=False))
                j = self._next_section
                hit = next((i for i in range(j, min(j + 4, len(sections))) if sections[i][1] == words), None)
                if hit is not None:
                    key, _words = sections[hit]
                    self._next_section = hit + 1
                    n = self.result.nodes[key]
                    level = n.level if n.level is not None else 1
                    while open_ and open_[-1][0] >= level:
                        open_.pop()
                    sec = self._section_el(n, head)
                    if run_in is not None:
                        k.kids.remove(run_in)
                        if text_of(k).strip():
                            sec.kids.append(k)
                    (open_[-1][1].kids if open_ else out).append(sec)
                    open_.append((level, sec))
                    continue
            (open_[-1][1].kids if open_ else out).append(k)
        return out

    def _section_nodes(self) -> list[tuple[str, list[str]]]:
        exp = self.result.expansions.get(self.master)
        found = []
        for key, n in self.result.nodes.items():
            if n.kind != "section" or self.master not in n.reached_by or n.file not in self.result.files:
                continue
            at = exp.exp_offset(n.file, n.start) if exp is not None else None
            if at is None:
                continue
            clean = self.result.files[n.file].clean
            m = _SECTION.match(clean, n.start)
            (_short, title), _spans, _end = read_args(clean, m.end() if m else n.start, "om")
            found.append((at, key, [w.text for w in source_words(title or "", self.macros, self.environments)]))
        return [(key, words) for _, key, words in sorted(found)]

    def _section_el(self, n: NodeRec, heading: El) -> El:
        clean = self.result.files[n.file].clean
        m = _SECTION.match(clean, n.start)
        _args, _spans, heading_end = read_args(clean, m.end() if m else n.start, "om")
        level = n.level if n.level is not None else 1
        h = El(f"h{min(max(level, 1), 6)}", {"data-src": f"{n.file}:{n.start}:{heading_end}"}, heading.kids)
        if starred_at(clean, n.start):
            h.kids = [k for k in h.kids if not (isinstance(k, El) and "number" in k.classes)]
        attrs = {"id": slug(n.key)}
        attrs.update({"data-id": n.id} if n.id else {"data-key": n.key})
        attrs.update({"data-level": str(level), "data-src": f"{n.file}:{n.start}:{n.end}"})
        return El("section", attrs, [h])

    # -- the nodes' own fragments --
    def _collect(self, kids: list[El | str]) -> None:
        proofs: dict[str, list[str]] = {}
        found: list[tuple[str, El]] = []
        for el in (e for k in kids if isinstance(k, El) for e in _walk(k)):
            key = el.attrs.get("data-key") or (el.attrs.get("data-id") if el.tag == "section" else None)
            if not key or key not in self.result.nodes:
                continue
            if el.tag == "details" and el.attrs.get("data-of"):
                proofs.setdefault(el.attrs["data-of"], []).append(html_of(el))
            found.append((key, el))
        for key, el in found:
            n = self.result.nodes[key]
            self.nodes[key] = html_of(el) + ("".join(proofs.get(key, [])) if n.kind == "environment" else "")

    def master_html(self) -> str:
        return "".join(html_of(k) for k in self.body)


#: References and citations as their commands are written; group 2 holds the labels or keys.
_REFS = re.compile(r"\\(eqref|ref|cref|Cref|autoref|pageref)\*?\s*\{([^}]*)\}")
_CITES = re.compile(r"\\(?:cite|citep|citet|Cite|parencite|textcite|autocite)\*?\s*(?:\[([^\]]*)\])?\s*\{([^}]*)\}")
_LIST = re.compile(r"\\begin\s*\{(itemize|enumerate|description|compactitem|compactenum|inparaenum)\}")
#: An inline formula as the source writes it, `\(...\)` or `$...$`; group 1 or 2 holds its TeX.
_INLINE = re.compile(r"\\\((.*?)\\\)|(?<![\\$])\$(?!\$)((?:\\.|[^$\\])+?)\$", re.DOTALL)
#: How far before the line TeX4ht gave a display its source is looked for: the paragraph the display stands in may begin well before it.
_DISPLAY_REACH = 4000
#: How far past a block's line a command is looked for when the block has no source span to bound the search.
_UNPLACED_REACH = 20000


#: What may stand between a block's words and what it prints at its edge without words of its own: spacing and punctuation.
_BETWEEN = r"[\s.,;:!?()\[\]~-]*"
#: What a block may begin or end with that prints no words the source has: a formula, a reference, a citation.
_WORDLESS = (
    r"(?:\\\(.*?\\\)|(?<![\\$])\$(?!\$)(?:\\.|[^$\\])+?\$"
    r"|\\(?:eqref|ref|cref|Cref|autoref|pageref)\*?\s*\{[^}]*\}"
    r"|\\(?:cite|citep|citet|Cite|parencite|textcite|autocite)\*?\s*(?:\[[^\]]*\])?\s*\{[^}]*\})"
)
_WORDLESS_AFTER = re.compile(_BETWEEN + _WORDLESS, re.DOTALL)
_WORDLESS_ANY = re.compile(_WORDLESS, re.DOTALL)
_ONLY_BETWEEN = re.compile(_BETWEEN + r"\Z")


def _wordless(k: El | str) -> bool:
    return isinstance(k, El) and (
        ("math" in k.classes and "inline" in k.classes) or bool({"ref", "cite"} & set(k.classes))
    )


def _edge_formulas(clean: str, start: int, end: int, el: El) -> tuple[int, int]:
    """`start` and `end` widened over the formulas, references and citations `el` begins and ends with, which a placement by words leaves outside."""
    lead = trail = 0
    for k in el.kids:
        if _wordless(k):
            lead += 1
        elif any(c.isalnum() for c in (k if isinstance(k, str) else text_of(k))):
            break
    for k in reversed(el.kids):
        if _wordless(k):
            trail += 1
        elif any(c.isalnum() for c in (k if isinstance(k, str) else text_of(k))):
            break
    for _ in range(trail):
        m = _WORDLESS_AFTER.match(clean, end)
        if m is None:
            break
        end = m.end()
    for _ in range(lead):
        before = [
            m
            for m in _WORDLESS_ANY.finditer(clean, max(0, start - 2000), start)
            if _ONLY_BETWEEN.match(clean, m.end(), start)
        ]
        if not before:
            break
        start = before[-1].start()
    return start, end


#: An included graphic, its name in group 1.
_GRAPHICS = re.compile(r"\\includegraphics\*?\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}")


def _graphic_stem(name: str) -> str:
    """A graphic's name without its extension, and without the `-` TeX4ht puts before the one it converts to: `figures/fig.pdf` and `figures/fig-.png` are both `figures/fig`."""
    return re.sub(r"-?\.[A-Za-z0-9]+$", "", name.strip())


def _spaceless(tex: str) -> str:
    return re.sub(r"\s+", "", tex)


_TABLE = re.compile(r"\\begin\s*\{(tabular\*?|tabularx|longtable|array)\}")
#: The environments a container element is set from, whose span is its place when its own blocks are too short to place.
_ENVIRONS = {"ul": _LIST, "ol": _LIST, "dl": _LIST, "table": _TABLE}


def _paren_equations(kids: list[El | str]) -> list[El | str]:
    """An equation reference with its parentheses inside its link, `(2)`, as `\\eqref` prints it and the translator links it."""
    out = list(kids)
    for i, k in enumerate(out):
        if not (isinstance(k, El) and k.tag == "a" and k.attrs.get("data-tex", "").startswith("\\eqref")):
            continue
        before = out[i - 1] if i else None
        after = out[i + 1] if i + 1 < len(out) else None
        if (
            isinstance(before, str)
            and before.rstrip().endswith("(")
            and isinstance(after, str)
            and after.lstrip().startswith(")")
        ):
            out[i - 1] = before.rstrip()[:-1]
            out[i + 1] = after.lstrip()[1:]
            k.kids = ["(", *k.kids, ")"]
    return out


def _run_in(k: El | str) -> El | None:
    """The heading run in at the head of paragraph `k`, a `span` TeX4ht marked as a heading, else None."""
    if not isinstance(k, El) or k.tag != "p":
        return None
    first = next((c for c in k.kids if not (isinstance(c, str) and not c.strip())), None)
    return first if isinstance(first, El) and first.tag == "span" and first.attrs.get("data-head") else None


def _is_mark(k: El | str) -> bool:
    return isinstance(k, El) and bool({"loom-file", "loom-file-end"} & set(k.classes))


def _lift_marks(kids: list[El | str]) -> list[El | str]:
    """A file's mark at the edge of an element, with nothing but space beside it there, moved out beside the element: TeX4ht opens a paragraph before an `\\input`, so a file's start lands at the end of one; an element left with nothing but space goes."""
    out: list[El | str] = []
    for k in kids:
        if not isinstance(k, El) or _is_mark(k):
            out.append(k)
            continue
        before: list[El | str] = []
        after: list[El | str] = []
        while k.kids and (_is_mark(k.kids[0]) or (isinstance(k.kids[0], str) and not k.kids[0].strip())):
            first = k.kids.pop(0)
            if _is_mark(first):
                before.append(first)
        while k.kids and (_is_mark(k.kids[-1]) or (isinstance(k.kids[-1], str) and not k.kids[-1].strip())):
            last = k.kids.pop()
            if _is_mark(last):
                after.insert(0, last)
        out += before
        if k.kids or k.tag in VOID or k.tag not in ("p", "span"):
            out.append(k)
        out += after
    return out


#: Blocks that hold blocks: placed, when their own words are none, from the first to the last place of what they hold.
_CONTAINERS = frozenset({"dl", "ul", "ol", "table", "blockquote"})


def _span_of(kids: list[El | str]) -> str | None:
    """`FILE:START:END` from the first placed block inside `kids` to the last, when they are all in one file."""
    spans = []
    for k in kids:
        if isinstance(k, El):
            for e in _walk(k):
                src = e.attrs.get("data-src")
                if src and e.tag not in ("section", "details", "div"):
                    file, start, end = src.rsplit(":", 2)
                    spans.append((file, int(start), int(end)))
    if not spans or len({f for f, _, _ in spans}) != 1:
        return None
    return f"{spans[0][0]}:{min(s for _, s, _ in spans)}:{max(e for _, _, e in spans)}"


def _walk(el: El):  # type: ignore[no-untyped-def]
    yield el
    for k in el.kids:
        if isinstance(k, El):
            yield from _walk(k)


def _own(el: El) -> str:
    """A block's own words: none of a block inside it, of what TeX made, or of mathematics."""
    out = []
    for k in el.kids:
        if isinstance(k, str):
            out.append(k)
        elif "data-at" not in k.attrs and "data-made" not in k.attrs and "math" not in k.classes:
            out.append(" " + _own(k) + " " if k.tag in ("br",) else _own(k))
        else:
            out.append(" ")
    return "".join(out)


def _unwrap(kids: list[El | str], cls: str) -> list[El | str]:
    out: list[El | str] = []
    for k in kids:
        if isinstance(k, El) and cls in k.classes:
            out += k.kids
        else:
            out.append(k)
    return out


def _take_head(kids: list[El | str]) -> El | None:
    """Remove and return the head TeX printed for a theorem or a proof, the first `span.head` in the first paragraph."""
    for k in kids:
        if isinstance(k, El):
            for i, c in enumerate(k.kids):
                if isinstance(c, El) and "head" in c.classes:
                    del k.kids[i]
                    return c
            if k.tag == "p":
                return None
    return None


def _pairs(renderer: FragmentRenderer, n: NodeRec) -> dict[str, str]:
    out = {}
    for a in renderer._pair_attrs(n):
        k, _, v = a.partition("=")
        out[k] = html.unescape(v.strip('"'))
    return out
