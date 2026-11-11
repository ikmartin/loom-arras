"""Fragments: one HTML file per node, per master, and per digest, every one from HTML TeX made.

A document is read from the page its compile made (`fromhtml`), and its nodes are cut from that page. Text no compile makes, a node no document reaches and a digest, is made by TeX as snippets under the preamble of the document that owns it (`snippets`), and shaped the same way. What TeX has not made, a document not yet compiled, a node its page lacks, a text TeX refused, is shown as its source (`sourceview`), never as an approximation.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import posixpath
import re
import threading
from bisect import bisect_right
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loom.paths import document_build
from loom.render.assets import publish_picture
from loom.render.mathset import EQUATION_ENVS
from loom.scan.hashing import pair_hash
from loom.scan.labels import plain_key
from loom.scan.model import Diagnostic, Env, Macro, SourceFile
from loom.scan.nodes import NodeRec
from loom.scan.preamble import PreambleClosure
from loom.scan.scan import ScanResult
from loom.scan.tokenize import read_args
from loom.tex.aux import AuxNumber
from loom.tex.bundle import _macro_block
from loom.tex.runner import normalise_engine

if TYPE_CHECKING:
    from loom.render.fromhtml import DocumentHtml, Page


@dataclass
class RenderPlan:
    result: ScanResult
    numbers: dict[str, dict[str, AuxNumber]]  # per master
    cache: Path  # the build's cache directory, `.loom/build/cache`
    svg_out: Path  # where pictures and graphics are published, `.loom/build/svg`
    cite_labels: dict[str, dict[str, str]] = field(default_factory=dict)  # per master: citekey -> printed label
    diagnostics: list[Diagnostic] = field(default_factory=list)
    pages: dict[str, Any] = field(
        default_factory=dict
    )  # per master: its page as TeX made it, current with its sources, or None
    tex: bool = True  # whether TeX may run for snippets and pictures; without it they come from the cache alone


@dataclass
class Owner:
    """The document text is read in terms of: its file, the directory its names resolve in, its preamble closure, the numbers and citation labels its compile printed, its macros, its preamble as written (class included) for TeX to run under, its aux, and its engine."""

    key: str
    base: str
    closure: PreambleClosure | None
    numbers: dict[str, AuxNumber]
    cite_labels: dict[str, str]
    macros: dict[str, Macro]
    preamble: str
    aux: Path | None = None
    engine: str = "pdflatex"


#: Where a document's body begins and ends.
_BEGIN = re.compile(r"\\begin\s*\{document\}")
_END = re.compile(r"\\end\s*\{document\}")
_OPEN = re.compile(r"\\(begin|end)\s*\{([^}]*)\}")


def bare_preamble(taxa: dict[str, Any]) -> str:
    """A preamble for text no document owns: amsart, the AMS packages, and every theorem-like environment the quilt declares."""
    lines = ["\\documentclass{amsart}", "\\usepackage{amsmath,amssymb,amsthm}"]
    for env, t in sorted(taxa.items()):
        if env != "proof" and re.fullmatch(r"[A-Za-z@*]+", env):
            lines.append(f"\\newtheorem{{{env}}}{{{getattr(t, 'name', env)}}}")
    return "\n".join(lines)


class FragmentRenderer:
    def __init__(self, plan: RenderPlan) -> None:
        self.plan = plan
        self.result = plan.result
        self.asm = plan.result.assembly
        self.env_at: dict[tuple[str, int], Env] = {}
        for path, fe in self.asm.envs.items():
            for env in fe.all_envs():
                self.env_at[(path, env.start)] = env
        self.equations = _equation_regions(self.result)
        self.master_titles = {m: master_title(self.result, m) for m in self.result.masters}
        # a reference with no number prints its target's title; a title carrying TeX would print as source, so those keep the key
        self.titles = {k: n.title for k, n in self.asm.nodes.items() if n.title and not re.search(r"[\\$]", n.title)}
        # Per thread: `loom build` renders on a pool, and a diagnostic list shared between renders would mix them.
        self._local = threading.local()
        self._shaping = threading.Lock()
        self._shaped: dict[str, DocumentHtml | None] = {}
        self._owners: dict[str, Owner] = {}
        # what snippets made, by key: node fragments, a digest's document, a document's body
        self._made: dict[str, str] = {}
        self._made_digests: dict[str, str] = {}
        self._made_masters: dict[str, str] = {}
        self.previews = _Previews(self)

    @cached_property
    def salt(self) -> str:
        """What a rendering depends on beyond its own text and preamble: loom's version and rendering code, the numbering, and the labels, regions and titles a reference resolves against.

        A cached preview is keyed on it (`review_compare._render`), so a renumbering, a label that moved or a change to loom renders it again.
        """
        from loom.render.keys import aux_bytes, code_hash
        from loom.version import __version__

        h = hashlib.sha256()
        h.update(__version__.encode())
        h.update(code_hash().encode())
        h.update(aux_bytes(self.plan.numbers, self.plan.cite_labels))
        h.update(
            json.dumps(
                [
                    sorted(self.asm.labels.items()),
                    sorted((k, r.container) for k, r in self.asm.regions.items()),
                    sorted(self.equations),
                    sorted(self.titles.items()),
                ]
            ).encode()
        )
        return h.hexdigest()

    @property
    def _sink(self) -> list[Diagnostic]:
        """Where this thread's diagnostics go: the job's own list inside `collecting`, else the plan's."""
        sink: list[Diagnostic] | None = getattr(self._local, "sink", None)
        return self.plan.diagnostics if sink is None else sink

    @contextmanager
    def collecting(self) -> Iterator[list[Diagnostic]]:
        """Collect this thread's diagnostics apart, so a pool's renders are reported in job order rather than in the order they finish."""
        sink: list[Diagnostic] = []
        self._local.sink = sink
        try:
            yield sink
        finally:
            self._local.sink = None

    # ---- whose terms text is read in ----------------------------------------------

    def owner_of(self, node: NodeRec) -> Owner:
        """The document a node is read in terms of: itself for a document, the default one where it reaches the node, else the first that does, else the default one."""
        dm = self.result.default_master
        if node.kind == "master":
            return self.owner(node.key)
        if dm and dm in node.reached_by:
            return self.owner(dm)
        return self.owner(node.reached_by[0] if node.reached_by else dm)

    def owner(self, master: str | None) -> Owner:
        """The document `master` as an `Owner`; with no document at all, the quilt's theorems under a bare preamble."""
        key = master or ""
        if key in self._owners:
            return self._owners[key]
        result = self.result
        engine = normalise_engine(result.quilt.config.engine)
        if not master or master not in result.files:
            made = Owner("", "", None, {}, {}, {}, bare_preamble(result.taxa), None, engine)
        else:
            closure = result.closures.get(master)
            src = result.files[master]
            begin = _BEGIN.search(src.clean)
            aux = result.quilt.root / document_build(master) / f"{Path(master).stem}.aux"
            made = Owner(
                master,
                result.base_of(master),
                closure,
                self.plan.numbers.get(master, {}),
                self.plan.cite_labels.get(master, {}),
                dict(closure.macros) if closure else {},
                src.text[: begin.start()] if begin else bare_preamble(result.taxa),
                aux if aux.is_file() else None,
                normalise_engine((closure.engine if closure else None) or result.quilt.config.engine),
            )
        self._owners[key] = made
        return made

    def envs(self, owner: Owner) -> list[str]:
        """The environments a run stamps as nodes: the owner's theorem-like ones, else the quilt's, and proofs."""
        taxa = owner.closure.taxa if owner.closure else self.result.taxa
        return [*taxa, "proof"]

    def _cite_target(self, citekey: str, postnote: str | None) -> str | None:
        for e in self.result.edges.edges:
            if e.via == "postnote" and e.label == f"{citekey}|{postnote}":
                return e.to
        return None

    def _pair_attrs(self, node: NodeRec) -> list[str]:
        """`data-pair` and `data-hash`, what compare pairs a node by; none for a node whose key names no id.

        The pair is the key with its derived id made plain; the hash is `pair_hash` over the node's own text, the text the history versions.
        """
        import html

        from loom.render.manifest import own_text

        head = self.result.nodes.get(node.key.split("/", 1)[0])
        if head is None or not head.id:
            return []
        return [
            f'data-pair="{html.escape(plain_key(node.key), quote=True)}"',
            f'data-hash="{pair_hash(own_text(self.result, node))}"',
        ]

    # ---- TeX for text no compile makes ---------------------------------------------

    def pictures(self, owner: Owner, displays: list[str]) -> list[str | None]:
        """Each display TeX draws as a picture under `owner`'s preamble, published under `svg/`: its path, or None where TeX drew none."""
        from loom.render.snippets import render_snippets

        cache = self.plan.cache / "snippets"
        made = render_snippets(
            self.result.quilt.root,
            owner.base,
            owner.preamble,
            displays,
            cache,
            engine=owner.engine,
            math="svg",
            tex=self.plan.tex,
        )
        out: list[str | None] = []
        for display, s in zip(displays, made.made, strict=True):
            m = re.search(r'<img src="([^"]+)"', s.html or "")
            picture = cache / m.group(1) if m else None
            if picture is not None and picture.is_file():
                out.append(publish_picture(picture, self.plan.svg_out))
                continue
            self._refused(owner.key, display, s.error, s.cached)
            out.append(None)
        return out

    def _refused(self, where: str, text: str, error: str, cached: bool) -> None:
        """A warning for a text TeX refused, once, where the build made it: a machine that runs no TeX refuses nothing."""
        if cached or not error or error.startswith(("TeX is not run", "make4ht is not", "TeX4ht made no page")):
            return
        first = " ".join(text.split())[:60]
        self._sink.append(
            Diagnostic(
                "warning", "loom:snippet-failed", f"TeX could not make {first!r} in {where or 'the quilt'}: {error}", []
            )
        )

    def snippet_page(
        self,
        owner: Owner,
        regions: list[tuple[str, int, int]],
        only: list[str],
        *,
        preamble: str | None = None,
        files: dict[str, SourceFile] | None = None,
        pairs: dict[str, str] | None = None,
        labels: dict[str, str] | None = None,
    ) -> DocumentHtml:
        """`regions` of `files` (the scan's by default), each `(file, start, end)`, made by TeX in one batch under `owner`'s preamble (or `preamble`) and shaped as a page is; a region TeX refused stands as its source.

        `only` names the nodes the regions hold, in order: a node region TeX refused is shown as that node's source, so the node still has its fragment.
        """
        from loom.render.fromhtml import DocumentHtml, Page
        from loom.render.snippets import render_snippets
        from loom.render.sourceview import source_block, source_env

        files = files if files is not None else dict(self.result.files)
        cache = self.plan.cache / "snippets"
        texts = [files[f].text[a:b] for f, a, b in regions]
        made = render_snippets(
            self.result.quilt.root,
            owner.base,
            preamble if preamble is not None else owner.preamble,
            texts,
            cache,
            envs=self.envs(owner),
            engine=owner.engine,
            aux=owner.aux,
            tex=self.plan.tex,
        )
        envs = set(self.envs(owner))
        pieces: list[str] = []
        for (f, a, b), text, s in zip(regions, texts, made.made, strict=True):
            line = files[f].text.count("\n", 0, a) + 1
            named = posixpath.relpath(f, owner.base or ".")
            if s.html is None:
                self._refused(f, text, s.error, s.cached)
                pieces.append(source_env(files[f], a, b, named, line, envs) or source_block(f, a, b, files[f].text))
                continue
            pieces.append(_lines_in(s.html, named, line))
        page = Page("\n".join(pieces), {}, "", where=cache, normalised=True)
        return DocumentHtml(self, owner, page, only=only, files=files, pairs=pairs, labels=labels)

    def prepare(self, keys: list[str] | None = None) -> None:
        """Make by TeX, before fragments are cut, what no compile makes among `keys` (default all): the nodes no document reaches, each in one batch under the default document's preamble, and each digest under its own.

        Done once per build, ahead of the fragments that read it, so each preamble is paid for once rather than once per node.
        """
        result = self.result
        wanted = set(keys) if keys is not None else None
        digests = result.assembly.digest_files
        loose = [
            k
            for k, n in result.nodes.items()
            if n.kind in ("environment", "proof", "section")
            and not n.reached_by
            and n.file in result.files
            and n.file not in digests
            and (wanted is None or k in wanted)
        ]
        if loose:
            owner = self.owner(result.default_master)
            loose.sort(key=lambda k: (result.nodes[k].file, result.nodes[k].start))
            regions = _outermost([(result.nodes[k].file, result.nodes[k].start, result.nodes[k].end) for k in loose])
            doc = self.snippet_page(owner, regions, _within(result, regions))
            self._made.update({k: _from_tex(_stamp_first(v, "node")) for k, v in doc.nodes.items()})
        todo = []
        for file in sorted(digests):
            held = [k for k, n in result.nodes.items() if n.file == file and n.kind != "file"]
            if wanted is None or file in wanted or set(held) & wanted:
                todo.append(file)
        # each digest is its own preamble, so its own run: a few at once, as a long list of texts runs a few at once
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=max(1, min(4, (os.cpu_count() or 2) // 2))) as pool:
            list(pool.map(self._prepare_digest, todo))

    def _prepare_digest(self, file: str) -> None:
        """A digest as a document: its body after the macro block, cut into texts at its statements, made under the default document's preamble with the packages its header requires and its macro block."""
        from loom.scan.digests import loaded_packages, required_packages

        result = self.result
        src = result.files[file]
        end_block = re.search(r"^\s*%\s*!LOOM\s+end\s+macros\s*$", src.text, re.M)
        start = end_block.end() if end_block else 0
        owner = self.owner(result.default_master)
        loaded = loaded_packages(owner.closure) if owner.closure else set()
        extra = "".join(f"\\usepackage{{{p}}}\n" for p in required_packages(result.assembly, file) if p not in loaded)
        preamble = owner.preamble.rstrip("\n") + "\n" + extra + _macro_block(result, file) + "\n"
        nodes = sorted(
            (k for k, n in result.nodes.items() if n.file == file and n.kind in ("environment", "proof", "section")),
            key=lambda k: result.nodes[k].start,
        )
        regions = body_regions(result, file, start, len(src.text))
        # its own preamble for its diagrams too, which draw with its macros
        doc = self.snippet_page(dataclasses.replace(owner, preamble=preamble), regions, nodes)
        self._made.update({k: _from_tex(_stamp_first(v, "node")) for k, v in doc.nodes.items()})
        self._made_digests[file] = doc.master_html()

    def prepare_document(self, master: str) -> None:
        """A document no compile has made, made by TeX as snippets of its body: a section draft, read in its saved context."""
        result = self.result
        src = result.files[master]
        begin, end = _BEGIN.search(src.clean), _END.search(src.clean)
        regions = body_regions(result, master, begin.end() if begin else 0, end.start() if end else len(src.text))
        nodes = sorted(
            (
                k
                for k, n in result.nodes.items()
                if master in n.reached_by and n.kind in ("environment", "proof", "section")
            ),
            key=lambda k: (result.nodes[k].file != master, result.nodes[k].file, result.nodes[k].start),
        )
        doc = self.snippet_page(self.owner(master), regions, nodes)
        self._made_masters[master] = doc.master_html()
        self._made.update({k: _from_tex(_stamp_first(v, "node")) for k, v in doc.nodes.items()})

    # ---- fragments -----------------------------------------------------------

    def _document_html(self, master: str) -> DocumentHtml | None:
        """`master`'s page in the dialect's shape, made once per build and shared by its nodes; None without a page, or with one that lost a node.

        A page on which a statement or proof the document holds was neither stamped nor found by its words (beamer's frames, which TeX4ht sets as bare text) cannot say where that node is, so the document shows as its source, every node with its identity, rather than as a page that has lost some.
        """
        from loom.render.fromhtml import DocumentHtml

        page: Page | None = self.plan.pages.get(master)
        if page is None:
            return None
        with self._shaping:
            if master not in self._shaped:
                doc = DocumentHtml(self, self.owner(master), page)
                self._shaped[master] = doc if doc.complete else None
            return self._shaped[master]

    def node_fragment(self, key: str) -> str:
        """A node's fragment: cut from the page of the default document, else of the first that reaches it; else made as a snippet; else its source."""
        from loom.render.sourceview import source_node

        n = self.asm.nodes[key]
        for m in sorted(n.reached_by, key=lambda m: m != self.result.default_master):
            doc = self._document_html(m)
            if doc is not None and key in doc.nodes:
                return _from_tex(_stamp_first(doc.nodes[key], "node"))
        if key in self._made:
            return self._made[key]
        return _stamp_first(source_node(self, key), "node")

    def master_fragment(self, master: str) -> str:
        """A document's fragment: its page, else the body snippets made of it, else its source."""
        from loom.render.markup import esc
        from loom.render.sourceview import source_body

        title = self.master_titles.get(master) or master
        head = f'<h1 data-src="{master}:0:0">{esc(title)}</h1>'
        doc = self._document_html(master)
        if doc is not None:
            cls = _DOCUMENTCLASS.search(self.result.files[master].clean) if master in self.result.files else None
            if cls is not None:
                head = head.replace("<h1 ", f'<h1 data-documentclass="{esc(cls.group(1).strip())}" ', 1)
            return _from_tex(_stamp_first(head + doc.master_html(), "master"))
        if master in self._made_masters:
            return _from_tex(_stamp_first(head + self._made_masters[master], "master"))
        src = self.result.files[master]
        begin, end = _BEGIN.search(src.clean), _END.search(src.clean)
        body = source_body(
            self, master, begin.end() if begin else 0, end.start() if end else len(src.text), owner=self.owner(master)
        )
        return _stamp_first(head + body, "master")

    def digest_fragment(self, file: str) -> str:
        """The digest file as a document, after its macro block, which is loaded around every statement and never shown: made by TeX, else its source."""
        from loom.render.sourceview import source_body

        if file not in self._made_digests:
            self._prepare_digest(file)
        made = self._made_digests.get(file)
        if made is not None:
            return _from_tex(_stamp_first(made, "digest"))
        text = self.result.files[file].text
        m = re.search(r"^\s*%\s*!LOOM\s+end\s+macros\s*$", text, re.M)
        return _stamp_first(source_body(self, file, m.end() if m else 0, len(text)), "digest")


def body_regions(result: ScanResult, file: str, start: int, end: int) -> list[tuple[str, int, int]]:
    """`file[start:end]` cut into texts at each statement and proof standing at its top level, outside every environment: the statement, the proof, and the prose between, blank prose left out.

    A statement inside a list or another environment stays in its prose, which TeX must read whole.
    """
    clean = result.files[file].clean
    claims = sorted(
        (n.start, n.end)
        for n in result.nodes.values()
        if n.file == file and n.kind in ("environment", "proof") and start <= n.start and n.end <= end
    )
    out: list[tuple[str, int, int]] = []
    pos = start
    for a, b in claims:
        if a < pos or _depth(clean, start, a) != 0:
            continue
        if clean[pos:a].strip():
            out.append((file, pos, a))
        out.append((file, a, b))
        pos = b
    if clean[pos:end].strip():
        out.append((file, pos, end))
    return out


def _depth(clean: str, start: int, at: int) -> int:
    """How many environments other than `document` stand open at `at`, counted from `start`."""
    depth = 0
    for m in _OPEN.finditer(clean, start, at):
        if m.group(2).strip() == "document":
            continue
        depth += 1 if m.group(1) == "begin" else -1
    return max(depth, 0)


def _outermost(regions: list[tuple[str, int, int]]) -> list[tuple[str, int, int]]:
    """The regions no other region holds, in order."""
    out: list[tuple[str, int, int]] = []
    for f, a, b in sorted(regions, key=lambda r: (r[0], r[1], -r[2])):
        if out and out[-1][0] == f and a >= out[-1][1] and b <= out[-1][2]:
            continue
        out.append((f, a, b))
    return out


def _within(result: ScanResult, regions: list[tuple[str, int, int]]) -> list[str]:
    """Every node inside `regions`, in their order."""
    out: list[tuple[int, int, str]] = []
    for i, (f, a, b) in enumerate(regions):
        for k, n in result.nodes.items():
            if n.file == f and n.kind in ("environment", "proof", "section") and a <= n.start and n.end <= b:
                out.append((i, n.start, k))
    return [k for _, _, k in sorted(out)]


_NODE_LINE = re.compile(r'data-file="" data-line="(\d+)"')


def _lines_in(html: str, file: str, first: int) -> str:
    """A text's HTML, whose lines count from its own first line and whose file TeX named '', as the lines of `file` from line `first`."""
    named = html.replace('data-at=":', f'data-at="{file}:')
    named = re.sub(
        rf'(data-at="{re.escape(file)}:)(\d+)(")',
        lambda m: f"{m.group(1)}{int(m.group(2)) + first - 1}{m.group(3)}",
        named,
    )
    return _NODE_LINE.sub(lambda m: f'data-file="{file}" data-line="{int(m.group(1)) + first - 1}"', named)


class _Previews:
    """Texts made as snippets for a preview, asked for during a build and made together at `make`, one batch per preamble."""

    def __init__(self, renderer: FragmentRenderer) -> None:
        self.r = renderer
        self.asked: list[Later] = []
        self._lock = threading.Lock()

    def ask(self, key: str, text: str, preamble: str | None, spans: list[list[int]]) -> Later:
        """A preview of `text` drawn as `key`, read under `preamble` (None: the document's own), its `spans` marked as changed; made at `make`."""
        later = Later(key, text, preamble, spans)
        with self._lock:
            self.asked.append(later)
        return later

    def on_made(self, later: Later, then: Callable[[str], None]) -> None:
        """Hand `later`'s markup to `then` once it is made."""
        later.then.append(then)

    def make(self) -> None:
        """Make every preview asked for and not yet made, and hand each to what waits on it."""
        from loom.render.changes import preview_html

        with self._lock:
            pending = [p for p in self.asked if p.html is None]
            self.asked = []
        groups: dict[tuple[str, str], list[Later]] = {}
        for p in pending:
            owner = _preview_owner(self.r, p)
            groups.setdefault((owner.key, owner.preamble if p.preamble is None else p.preamble), []).append(p)
        for group in groups.values():
            for p, made in zip(group, preview_html(self.r, group), strict=True):
                p.html = made
                for then in p.then:
                    then(made)


@dataclass
class Later:
    """A preview asked for: the key it is drawn as, its text, the preamble it is read under (a document's closure as recorded), the spans of it that changed; `html` once made."""

    key: str
    text: str
    preamble: str | None
    spans: list[list[int]]
    html: str | None = None
    then: list[Callable[[str], None]] = field(default_factory=list)


def _preview_owner(r: FragmentRenderer, p: Later) -> Owner:
    """The document a preview is read in: its key's own where its closure is the preamble, else another whose closure is, else its key's with the preamble as given.

    The key's own comes first: an agent's copy shares its document's closure and was likely never compiled, so its aux would print no numbers.
    """
    result = r.result
    node = result.nodes.get(result.dependencies.owners.get(p.key, p.key))
    own = r.owner_of(node) if node is not None else r.owner(result.default_master)
    for master in [own.key, *result.masters]:
        closure = result.closures.get(master)
        if closure is not None and closure.raw_text() == p.preamble:
            p.preamble = None  # the document's own, which loads its local files itself
            return r.owner(master)
    return own


def _equation_regions(result: ScanResult) -> set[str]:
    """Region keys whose label sits in display mathematics, which a `\\ref` sets in parentheses.

    Any other region, an enumerated item or a figure, prints its number bare. Only the outermost display of each nesting is kept, so the spans are disjoint and one bisect finds a label's.
    """
    spans: dict[str, list[tuple[int, int]]] = {}

    def walk(path: str, env: Env) -> None:
        if env.name in EQUATION_ENVS:
            spans.setdefault(path, []).append((env.start, env.end))
            return
        for child in env.children:
            walk(path, child)

    for path, fe in result.assembly.envs.items():
        for root in fe.roots:
            walk(path, root)
    starts = {path: [a for a, _ in s] for path, s in spans.items()}
    out: set[str] = set()
    for key, r in result.assembly.regions.items():
        i = bisect_right(starts.get(r.file, []), r.offset) - 1
        if i >= 0 and r.offset < spans[r.file][i][1]:
            out.add(key)
    return out


#: A document's class, which the paper formats set its title and heads by.
_DOCUMENTCLASS = re.compile(r"\\documentclass\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}")


def _from_tex(fragment: str) -> str:
    """Mark a fragment made from HTML TeX made, on its first element: its blocks carry `data-src` where loom placed them, and only there."""
    return re.sub(r"(<\w+)", r'\1 data-from="tex"', fragment, count=1)


def _stamp_first(fragment: str, kind: str) -> str:
    m = re.match(r"\s*<(\w+)", fragment)
    if not m:
        return fragment
    i = m.end()
    return fragment[:i] + f' data-fragment="{kind}"' + fragment[i:]


def master_title(result: ScanResult, master: str) -> str | None:
    src = result.files.get(master)
    if src is None:
        return None
    m = re.search(r"\\title\s*(\[[^\]]*\])?\s*\{", src.clean)
    if not m:
        return None
    from loom.scan.tokenize import match_group

    end = match_group(src.clean, m.end() - 1)
    if end < 0:
        return None
    raw = src.text[m.end() : end - 1]
    return plain_text(raw)


_MATH_SPAN = re.compile(r"\$[^$]*\$|\\\((?:.|\n)*?\\\)")
_TEXORPDF = re.compile(r"\\texorpdfstring(?![A-Za-z@])")


def _tex_strings(latex: str) -> str:
    """Each `\\texorpdfstring{TEX}{PDF}` as TEX, the form the document typesets; PDF is for the PDF's bookmarks alone."""
    while m := _TEXORPDF.search(latex):
        (tex, _), _, after = read_args(latex, m.end(), "mm")
        if tex is None:
            break
        latex = latex[: m.start()] + tex + latex[after:]
    return latex


def plain_text(latex: str) -> str:
    """A text-only rendering of a title: macros with one argument keep their argument, the rest is dropped, and inline math is kept as written.

    Math is left as LaTeX rather than stripped because stripping it destroyed the title: a section called `Structure of $\\Sigma$` became `Structure of $ $`. A viewer typesets what it can and shows the source otherwise; nothing is lost either way.
    """

    def outside(part: str) -> str:
        s = re.sub(r"\\(cite|label|uses|footnote|thanks)\s*(\[[^\]]*\])*\s*\{[^}]*\}", "", part)
        s = re.sub(r"\\[A-Za-z@]+\*?\s*(\[[^\]]*\])?\s*\{", "{", s)
        s = re.sub(r"\\[A-Za-z@]+\*?", " ", s)
        return s.replace("{", "").replace("}", "").replace("~", " ").replace("--", "–")

    latex = _tex_strings(latex)
    out: list[str] = []
    pos = 0
    for m in _MATH_SPAN.finditer(latex):
        out.append(outside(latex[pos : m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(outside(latex[pos:]))
    return re.sub(r"\s+", " ", "".join(out)).strip()


def plain_title(latex: str, width: int = 60) -> str:
    """`plain_text(latex)`, cut at a word with `…` past `width`: a title in a terminal row (T4), where an identifier is never cut but a title may be."""
    title = plain_text(latex)
    if len(title) <= width:
        return title
    cut = title.rfind(" ", 0, width - 1)
    return title[: cut if cut > 0 else width - 1].rstrip(",;:") + "…"


def digest_macro_set(result: ScanResult, file: str) -> list[dict[str, object]]:
    from loom.scan.macros import parse_macros, to_mathjax

    block = _macro_block(result, file)
    return to_mathjax(parse_macros(block)) if block else []
