"""Canon documents as fragments (book 9.3, 17.1): a landmark is rendered as the document it is, with no node identity, no marks, and no numbers loom did not compile itself.

The canon directory is never scanned, so nothing here goes through the assembly: the file is read on its own, its preamble closure is built from itself, and its labels anchor within the page.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loom.history.ledger import Entry, History
from loom.render.assets import publish_graphic
from loom.render.convert import Converter, RenderContext, esc
from loom.render.fragments import FragmentRenderer, plain_text
from loom.scan.digests import loaded_packages
from loom.scan.envtree import norm_label
from loom.scan.macros import compatibility_macros, declared_alphabets, package_macros, to_mathjax
from loom.scan.model import Diagnostic, Location, SourceFile
from loom.scan.preamble import PreambleClosure, build_closure, document_start
from loom.scan.quilt import Quilt
from loom.scan.scan import ScanResult
from loom.scan.source import read_source
from loom.tex.aux import read_cite_labels, read_numbers

_LABEL = re.compile(r"\\label\s*\{([^}]*)\}")


@dataclass
class CanonDoc:
    path: str  # quilt-relative
    stem: str
    src: SourceFile
    closure: PreambleClosure
    title: str
    step: Entry | None = None
    labels: dict[str, str] = field(default_factory=dict)


def title_of(src: SourceFile) -> str | None:
    from loom.scan.tokenize import match_group

    m = re.search(r"\\title\s*(\[[^\]]*\])?\s*\{", src.clean)
    if not m:
        return None
    end = match_group(src.clean, m.end() - 1)
    return plain_text(src.text[m.end() : end - 1]) if end > 0 else None


def load_canon(quilt: Quilt, result: ScanResult, history: History) -> list[CanonDoc]:
    """One CanonDoc per canon document, read outside the scan (`result.files` is left alone) and closed over its own preamble."""
    out: list[CanonDoc] = []
    for rel in result.canon_files:
        src = read_source(quilt.root, rel)
        from loom.scan.directives import parse_directives

        closure = build_closure(src, quilt.root, {}, parse_directives(src))
        stem = Path(rel).stem
        labels = {norm_label(m.group(1)): norm_label(m.group(1)) for m in _LABEL.finditer(src.clean)}
        out.append(
            CanonDoc(
                path=rel,
                stem=stem,
                src=src,
                closure=closure,
                title=title_of(src) or stem,
                step=history.step_for_path(rel),
                labels=labels,
            )
        )
    return out


def canon_fragment_path(doc: CanonDoc) -> str:
    return f"fragments/canon/{doc.stem}.html"


def macro_set(doc: CanonDoc) -> list[dict[str, Any]]:
    """The MathJax macros of the canon's own preamble: a landmark renders as it compiled, whatever the drafting documents have since become."""
    macros = {
        k: v for k, v in doc.closure.macros.items() if v.kind != "let" and k not in ("uses", "incomplete", "nest")
    }
    for name, macro in declared_alphabets(doc.closure.clean_text()).items():
        macros.setdefault(name, macro)
    for name, macro in package_macros(loaded_packages(doc.closure)).items():
        macros.setdefault(name, macro)
    macros.update(compatibility_macros(macros))
    return to_mathjax(macros)


class CanonRenderer:
    """Renders canon documents with the FragmentRenderer's fallback machinery but none of its identity."""

    def __init__(self, renderer: FragmentRenderer) -> None:
        self.renderer = renderer
        self.result = renderer.result
        self.root = renderer.result.quilt.root

    def _context(self, doc: CanonDoc) -> RenderContext:
        seen: set[str] = set()

        def include(arg: str) -> str:
            # a canonized document is flat; an \input that survives is one someone put there by hand, so inline the file if it exists and say so if it does not
            if arg.startswith("graphics:"):
                rel, err = publish_graphic(self.root, arg[len("graphics:") :], self.renderer.plan.svg_out)
                if rel is None:
                    return f'<figure class="fallback failed" data-src="{doc.path}:0:0"><pre>{esc(arg)}</pre></figure>'
                return f'<figure data-src="{doc.path}:0:0"><img src="{rel}"></figure>'
            from loom.scan.expand import resolve_inclusion

            rel, problem = resolve_inclusion(self.root, arg)
            if rel is None or rel in seen:
                if problem != "system":
                    ctx.diagnostics.append(
                        Diagnostic(
                            "error",
                            "missing-include",
                            f"\\input{{{arg}}} names no file",
                            [Location(doc.path, 1)],
                        )
                    )
                return ""
            seen.add(rel)
            child = read_source(self.root, rel)
            sub = Converter(_child_context(ctx, child))
            return f'<div class="included" data-file="{esc(rel)}">{sub.render_range(0, len(child.clean))}</div>'

        ctx = RenderContext(
            file=doc.path,
            text=doc.src.text,
            clean=doc.src.clean,
            key=doc.path,
            labels=doc.labels,
            regions={},
            numbers=read_numbers(self.root, doc.path),
            cite_labels=read_cite_labels(self.root, doc.path),
            macros=doc.closure.macros,
            taxa=doc.closure.taxa,
            child_at={},
            child_html=lambda key: "",
            include_html=include,
            fallback=self.renderer._fallback_for_preamble(_preamble_for(doc.closure), doc.path),
            cite_target=self.renderer._cite_target,
        )
        return ctx

    def fragment(self, doc: CanonDoc) -> str:
        ctx = self._context(doc)
        body_start = document_start(doc.src)
        start = 0
        if body_start is not None:
            m = re.search(r"\\begin\s*\{document\}", doc.src.clean)
            start = m.end() if m else 0
        end_m = re.search(r"\\end\s*\{document\}", doc.src.clean)
        end = end_m.start() if end_m else len(doc.src.clean)
        conv = Converter(ctx)
        body = conv.render_range(start, end)
        self.renderer._sink.extend(ctx.diagnostics)
        head = f'<h1 data-src="{doc.path}:0:0">{esc(doc.title)}</h1>'
        return _stamp(head + body, doc)


def _child_context(ctx: RenderContext, child: SourceFile) -> RenderContext:
    import dataclasses

    return dataclasses.replace(ctx, file=child.path, text=child.text, clean=child.clean, key=child.path)


def _stamp(fragment: str, doc: CanonDoc) -> str:
    m = re.match(r"\s*<(\w+)", fragment)
    if not m:
        return fragment
    i = m.end()
    return fragment[:i] + f' data-fragment="canon" data-macros="canon:{esc(doc.stem)}"' + fragment[i:]


def _preamble_for(closure: PreambleClosure) -> str:
    """The canon's own preamble text: it is flat and self-contained, so its first fragment is the whole of it."""
    first = closure.fragments[0] if closure.fragments else None
    return first.src.text[first.start : first.end] if first else ""


def canon_entry(doc: CanonDoc, fragment: str, hashed: str) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "path": doc.path,
        "stem": doc.stem,
        "title": doc.title,
        "fragment": fragment,
        "hash": hashed,
    }
    if doc.step is not None and doc.step.step is not None:
        entry["step"] = f"{doc.step.step:04d}"
        entry["name"] = doc.step.name
        if doc.step.message:
            entry["message"] = doc.step.message
        entry["when"] = doc.step.when
    return entry
