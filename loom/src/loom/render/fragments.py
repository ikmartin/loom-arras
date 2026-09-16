"""Fragments: one HTML file per node, per master, and per digest (book 9.3).

A node fragment renders the node's own text with placeholders for child claimants; a master fragment renders the master's document with every inclusion expanded in place; a digest fragment renders the digest file as a document. All three come from one Converter with two `child_html` policies.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from loom.render.assets import publish_graphic
from loom.render.convert import Converter, RenderContext, esc, slug
from loom.render.fallback import compile_svg, fallback_figure
from loom.scan.model import Diagnostic, Env, Location, Macro
from loom.scan.nodes import NodeRec
from loom.scan.scan import ScanResult
from loom.scan.tokenize import read_args
from loom.tex.aux import AuxNumber
from loom.tex.bundle import _macro_block


def _title_base(env: Env | None, node: NodeRec) -> int:
    """Source offset of the node's title text, so inline spans in a title point into the file; the title may sit inside a brace group in the optional argument."""
    if env is None or not env.optarg_span:
        return node.start
    off = env.optarg.find(node.title) if env.optarg and node.title else -1
    return env.optarg_span[0] + (off if off >= 0 else 0)


@dataclass
class RenderPlan:
    result: ScanResult
    numbers: dict[str, dict[str, AuxNumber]]  # per master
    svg_cache: Path
    svg_out: Path
    diagnostics: list[Diagnostic] = field(default_factory=list)
    fallback_preamble: dict[str, str] = field(default_factory=dict)


class FragmentRenderer:
    def __init__(self, plan: RenderPlan) -> None:
        self.plan = plan
        self.result = plan.result
        self.asm = plan.result.assembly
        self.env_at: dict[tuple[str, int], Env] = {}
        for path, fe in self.asm.envs.items():
            for env in fe.all_envs():
                self.env_at[(path, env.start)] = env
        self.master_titles = {m: master_title(self.result, m) for m in self.result.masters}

    # ---- contexts -----------------------------------------------------------

    def _numbers_for(self, node: NodeRec) -> dict[str, AuxNumber]:
        dm = self.result.default_master
        if dm and dm in self.plan.numbers and (dm in node.reached_by or node.kind == "master"):
            return self.plan.numbers[dm]
        for m in node.reached_by:
            if m in self.plan.numbers:
                return self.plan.numbers[m]
        return self.plan.numbers.get(dm, {}) if dm else {}

    def _macros_for(self, node: NodeRec) -> dict[str, Macro]:
        dm = self.result.default_master
        closure = self.result.closures.get(dm) if dm else None
        return closure.macros if closure else {}

    def _fallback_preamble(self, master: str | None) -> str:
        if master is None:
            return ""
        if master not in self.plan.fallback_preamble:
            closure = self.result.closures.get(master)
            text = closure.raw_text() if closure else ""
            text = re.sub(r"\\documentclass(\[[^\]]*\])?\{[^}]*\}", "", text)
            text = re.sub(r"^\s*%.*$", "", text, flags=re.M)
            text = re.sub(
                r"\\(title|author|date|address|email|thanks|subjclass|keywords)\s*(\[[^\]]*\])?\{", r"\\@gobble{", text
            )
            self.plan.fallback_preamble[master] = text
        return self.plan.fallback_preamble[master]

    def _fallback(self, master: str | None) -> Callable[[str, str, str], str]:
        preamble = self._fallback_preamble(master)

        def render(latex: str, css: str, data_src: str) -> str:
            root = self.result.quilt.root
            res = compile_svg(latex, preamble, self.plan.svg_cache, texinputs=root)
            if res.svg is None:
                minimal = "\\usepackage{amsmath,amssymb,amsthm}\n\\usepackage{tikz}\n\\usetikzlibrary{cd}\n"
                res = compile_svg(latex, minimal, self.plan.svg_cache, texinputs=root)
            if res.svg is None:
                self.plan.diagnostics.append(
                    Diagnostic("warning", "loom:converter-fallback", f"SVG fallback failed: {res.error}", [], [])
                )
            return fallback_figure(latex, res, css, data_src)

        return render

    def _cite_target(self, citekey: str, postnote: str | None) -> str | None:
        for e in self.result.edges.edges:
            if e.via == "postnote" and e.label == f"{citekey}|{postnote}":
                return e.to
        return None

    def _context(self, node: NodeRec, mode: str) -> RenderContext:
        src = self.result.files[node.file]
        child_at = {}
        for ck in node.claimants:
            c = self.asm.nodes[ck]
            child_at[c.start] = (c.end, ck)
        master = self.result.default_master if node.kind != "master" else node.key
        if node.kind != "master" and node.reached_by and self.result.default_master not in node.reached_by:
            master = node.reached_by[0]
        ctx = RenderContext(
            file=node.file,
            text=src.text,
            clean=src.clean,
            key=node.key,
            labels=self.asm.labels,
            regions={k: r.container for k, r in self.asm.regions.items()},
            numbers=self._numbers_for(node),
            macros=self._macros_for(node),
            taxa=self.result.taxa,
            child_at=child_at,
            child_html=(lambda key: self._placeholder(key))
            if mode == "node"
            else (lambda key: self.render_node_html(key, "master")),
            include_html=lambda arg: self._include_html(arg, node, mode),
            fallback=self._fallback(master),
            cite_target=self._cite_target,
        )
        return ctx

    def _placeholder(self, key: str) -> str:
        return f'<div class="include" data-key="{html.escape(key, quote=True)}"></div>'

    def _include_html(self, arg: str, node: NodeRec, mode: str) -> str:
        root = self.result.quilt.root
        if arg.startswith("graphics:"):
            rel, err = publish_graphic(root, arg[len("graphics:") :], self.plan.svg_out)
            if rel is None:
                self.plan.diagnostics.append(
                    Diagnostic(
                        "warning",
                        "loom:converter-fallback",
                        err or "graphic missing",
                        [Location(node.file, 0)],
                        [node.key],
                    )
                )
                return f'<figure class="fallback failed" data-src="{node.file}:0:0" data-src-text="{html.escape(arg, quote=True)}"><pre>{esc(arg)}</pre></figure>'
            return f'<figure data-src="{node.file}:0:0"><img src="{rel}"></figure>'
        from loom.scan.expand import resolve_inclusion

        rel, _ = resolve_inclusion(root, arg)
        if rel is None or rel not in self.asm.nodes:
            return ""
        container = self.asm.nodes[rel]
        if mode == "node":
            keys = [k for k in container.claimants if self.asm.nodes[k].kind in ("environment", "section")] or [rel]
            return "".join(self._placeholder(k) for k in keys)
        inner = self.render_container_body(container, "master")
        return f'<div class="included" data-key="{html.escape(rel, quote=True)}" data-file="{html.escape(rel, quote=True)}" data-src="{rel}:0:{len(self.result.files[rel].text)}">{inner}</div>'

    # ---- rendering nodes ------------------------------------------------------

    def render_node_html(self, key: str, mode: str) -> str:
        """A node's HTML. In node mode a statement carries all its proofs; in master mode proofs are rendered where they sit, as claimants of the surrounding text."""
        node = self.asm.nodes[key]
        if node.kind == "environment":
            out = self._environment_html(node, mode)
            if mode == "node":
                out += "".join(self._proof_html(self.asm.nodes[pk], mode) for pk in node.proofs)
            return out
        if node.kind == "proof":
            return self._proof_html(node, mode)
        if node.kind == "section":
            return self._section_html(node, mode)
        return self.render_container_body(node, mode)

    def _env_of(self, node: NodeRec) -> Env | None:
        return self.env_at.get((node.file, node.start))

    def _label_html(self, node: NodeRec, ctx: RenderContext) -> str:
        num = None
        for lab in [node.id, *node.labels]:
            if lab and lab in ctx.numbers:
                num = ctx.numbers[lab].number
                break
        parts = [f'<span class="taxon">{esc(node.taxon or "")}</span>']
        if num:
            parts.append(f' <span class="number">{esc(num)}</span>')
        if node.title:
            conv = Converter(ctx)
            env = self._env_of(node)
            base = _title_base(env, node)
            parts.append(f' <span class="title">({conv.inline_text(node.title, base)})</span>')
        return "".join(parts)

    def _environment_html(self, node: NodeRec, mode: str) -> str:
        ctx = self._context(node, mode)
        env = self._env_of(node)
        conv = Converter(ctx)
        body = conv.render_range(env.body_start, env.body_end) if env else ""
        self.plan.diagnostics.extend(ctx.diagnostics)
        attrs = [f'class="env env-{slug(node.taxon or node.env or "env")}"']
        if node.id:
            attrs.append(f'data-id="{html.escape(node.id, quote=True)}"')
        attrs.append(f'data-key="{html.escape(node.key, quote=True)}"')
        attrs.append(f'data-taxon="{html.escape(node.taxon or "", quote=True)}"')
        attrs.append(f'data-style="{html.escape(node.style or "plain", quote=True)}"')
        attrs.append(f'data-src="{ctx.src(node.start, node.end)}"')
        if node.digest:
            attrs.append(f'data-macros="{html.escape(node.digest, quote=True)}"')
        label = self._label_html(node, ctx)
        return f'<div {" ".join(attrs)}><p class="env-label">{label}</p>{body}</div>'

    def _proof_html(self, node: NodeRec, mode: str) -> str:
        ctx = self._context(node, mode)
        env = self._env_of(node)
        conv = Converter(ctx)
        body = conv.render_range(env.body_start, env.body_end) if env else ""
        self.plan.diagnostics.extend(ctx.diagnostics)
        title = ""
        if node.title:
            base = _title_base(env, node)
            title = f'<span class="title"> {conv.inline_text(node.title, base)}</span>'
        attrs = ['class="env env-proof"', f'data-key="{html.escape(node.key, quote=True)}"']
        if node.id:
            attrs.insert(1, f'data-id="{html.escape(node.id, quote=True)}"')
        if node.of:
            attrs.append(f'data-of="{html.escape(node.of, quote=True)}"')
        attrs.append(f'data-src="{ctx.src(node.start, node.end)}"')
        return f'<details {" ".join(attrs)} open><summary class="env-label">Proof{title}</summary>{body}</details>'

    def _section_html(self, node: NodeRec, mode: str) -> str:
        ctx = self._context(node, mode)
        src = self.result.files[node.file]
        m = re.match(
            r"\\(part|chapter|section|subsection|subsubsection|paragraph|subparagraph)\*?\s*", src.clean[node.start :]
        )
        after = node.start + (m.end() if m else 0)
        (short, title), spans, heading_end = read_args(src.clean, after, "om")
        conv = Converter(ctx)
        title_html = conv.inline_text(title or "", spans[1][0]) if title else ""
        num = None
        for lab in [node.id, *node.labels]:
            if lab and lab in ctx.numbers:
                num = ctx.numbers[lab].number
                break
        level = node.level if node.level is not None else 1
        h = min(max(level, 1), 6)
        number_html = f'<span class="number">{esc(num)}</span> ' if num else ""
        body = conv.render_range(heading_end, node.end)
        self.plan.diagnostics.extend(ctx.diagnostics)
        ident = (
            f'data-id="{html.escape(node.id, quote=True)}"'
            if node.id
            else f'data-key="{html.escape(node.key, quote=True)}"'
        )
        return f'<section {ident} data-level="{level}" data-src="{ctx.src(node.start, node.end)}"><h{h} data-src="{ctx.src(node.start, heading_end)}">{number_html}{title_html}</h{h}>{body}</section>'

    def render_container_body(self, node: NodeRec, mode: str) -> str:
        """The prose of a master or file container with its claimants; for masters, the document body only."""
        ctx = self._context(node, mode)
        src = self.result.files[node.file]
        start = node.body_start
        end_m = re.search(r"\\end\s*\{document\}", src.clean)
        end = end_m.start() if end_m else len(src.clean)
        if node.kind == "master":
            bm = re.search(r"\\begin\s*\{document\}", src.clean)
            start = bm.end() if bm else 0
        conv = Converter(ctx)
        body = conv.render_range(start, end)
        self.plan.diagnostics.extend(ctx.diagnostics)
        return body

    # ---- fragments -----------------------------------------------------------

    def node_fragment(self, key: str) -> str:
        html_out = self.render_node_html(key, "node")
        return _stamp_first(html_out, "node")

    def master_fragment(self, master: str) -> str:
        node = self.asm.nodes[master]
        title = self.master_titles.get(master) or master
        head = f'<h1 data-src="{master}:0:0">{esc(title)}</h1>'
        return _stamp_first(head + self.render_container_body(node, "master"), "master")

    def digest_fragment(self, file: str) -> str:
        node = self.asm.nodes[file]
        return _stamp_first(self.render_container_body(node, "master"), "digest")


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


def plain_text(latex: str) -> str:
    """A crude text-only rendering of a title: macros with one argument keep their argument, the rest is dropped."""
    s = re.sub(r"\\(cite|label|uses|footnote|thanks)\s*(\[[^\]]*\])*\s*\{[^}]*\}", "", latex)
    s = re.sub(r"\\[A-Za-z@]+\*?\s*(\[[^\]]*\])?\s*\{", "{", s)
    s = re.sub(r"\\[A-Za-z@]+\*?", " ", s)
    s = s.replace("{", "").replace("}", "").replace("~", " ").replace("--", "–")
    return re.sub(r"\s+", " ", s).strip()


def digest_macro_set(result: ScanResult, file: str) -> list[dict[str, object]]:
    from loom.scan.macros import parse_macros, to_mathjax

    block = _macro_block(result, file)
    return to_mathjax(parse_macros(block)) if block else []
