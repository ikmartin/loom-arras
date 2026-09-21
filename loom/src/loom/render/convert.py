"""LaTeX to the semantic dialect (book 9.4, docs/specs/dialect.md).

A restricted translator over a node's own text: paragraphs, headings, lists, display math (left as TeX for the viewer), theorem-like environments and proofs, references, citations, footnotes, figures, simple tables, verbatim. Every block carries `data-src` back to its file offsets. Anything outside the contract renders exactly, per block, as SVG through `fallback.compile_svg`; nothing is silently dropped.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from loom.scan.envtree import norm_label
from loom.scan.macros import expand
from loom.scan.model import Diagnostic, Location, Macro, Taxon
from loom.scan.source import blank_comments
from loom.scan.tokenize import Tok, match_group, read_args, tokenize
from loom.tex.aux import AuxNumber

DISPLAY_ENVS = {
    "equation",
    "equation*",
    "align",
    "align*",
    "gather",
    "gather*",
    "multline",
    "multline*",
    "eqnarray",
    "eqnarray*",
    "alignat",
    "alignat*",
    "flalign",
    "flalign*",
    "displaymath",
    "split",
    "cases",
}
LIST_ENVS = {
    "itemize": "ul",
    "enumerate": "ol",
    "description": "dl",
    "compactitem": "ul",
    "compactenum": "ol",
    "inparaenum": "ol",
    "asparaenum": "ol",
    "enumeratei": "ol",
    "enumeratea": "ol",
    "enumerate1": "ol",
    "todolist": "ul",
}
CONTAINER_ENVS = {
    "center",
    "flushleft",
    "flushright",
    "quote",
    "quotation",
    "abstract",
    "frame",
    "block",
    "small",
    "footnotesize",
    "minipage",
}
DIAGRAM_ENVS = {"tikzcd", "tikzpicture", "xy", "xymatrix"}
# Environments a mathematics renderer handles inside a display; anything else in one means the block is a picture and belongs to the fallback (book 9.4.2).
MATH_SAFE_ENVS = {
    # the display environments themselves, which `display_env` wraps back up before this is asked
    "equation",
    "displaymath",
    "align",
    "gather",
    "multline",
    "eqnarray",
    "alignat",
    "flalign",
    "array",
    "matrix",
    "pmatrix",
    "bmatrix",
    "Bmatrix",
    "vmatrix",
    "Vmatrix",
    "smallmatrix",
    "cases",
    "dcases",
    "rcases",
    "aligned",
    "alignedat",
    "gathered",
    "split",
    "subarray",
    "subequations",
    "multlined",
    "CD",  # amscd, which a viewer's renderer draws natively; it is a diagram but not a picture
}
# Commands that draw rather than typeset. `\xymatrix` is the common one: it is a command, not an environment, so an environment test alone never sees it.
_DRAWS = re.compile(
    r"\\(xymatrix|xygraph|xybox|tikz|pgfplots|includegraphics|scalebox|resizebox|raisebox|parbox|fbox|shortstack)(?![A-Za-z])"
)  # `\xymatrix@C=1cm{...}` is `\xymatrix` followed by xy's own syntax, so only a letter continues the control word
_ENV_IN = re.compile(r"\\begin\s*\{([^}]*)\}")


def renders_as_math(tex: str) -> bool:
    """Whether a display block is mathematics a renderer can typeset, or a picture the fallback must compile.

    A block naming an environment outside `MATH_SAFE_ENVS`, or a drawing command, is a picture. Deciding by an allowlist rather than by a list of known offenders means an environment nobody anticipated goes to LaTeX, which can always render it, instead of to a renderer that cannot.
    """
    if _DRAWS.search(tex):
        return False
    return all(name.strip().rstrip("*") in MATH_SAFE_ENVS for name in _ENV_IN.findall(tex))


VERBATIM_ENVS = {"verbatim", "verbatim*", "lstlisting"}
SECTIONING = {
    "part": -1,
    "chapter": 0,
    "section": 1,
    "subsection": 2,
    "subsubsection": 3,
    "paragraph": 4,
    "subparagraph": 5,
}
REF_CMDS = {"ref", "eqref", "cref", "Cref", "autoref", "pageref", "vref", "Vref"}
CITE_CMDS = {
    "cite",
    "parencite",
    "textcite",
    "autocite",
    "citep",
    "citet",
    "Cite",
    "Parencite",
    "Textcite",
    "cites",
    "footcite",
    "citeauthor",
    "citeyear",
}
INLINE_WRAP = {
    "emph": "em",
    "textit": "em",
    "textbf": "strong",
    "texttt": "code",
    "textsc": "span.smallcaps",
    "underline": "u",
    "textsl": "em",
    "textup": "",
    "textrm": "",
    "textmd": "",
    "textnormal": "",
    "mbox": "",
    "hbox": "",
    "text": "",
    "textcolor": "!color",
    "color": "!decl",
    "mathrm": "",
}
IGNORED_CMDS = {
    "titlepage",
    "frametitle",
    "framesubtitle",
    "pause",
    "usetheme",
    "usecolortheme",
    "logo",
    "institute",
    "date",
    "author",
    "title",
    "subtitle",
    "thanks",
    "email",
    "address",
    "subjclass",
    "keywords",
    "urladdr",
    "dedicatory",
    "noindent",
    "indent",
    "newline",
    "smallskip",
    "medskip",
    "bigskip",
    "vspace",
    "vspace*",
    "hspace",
    "hspace*",
    "vfill",
    "hfill",
    "centering",
    "raggedright",
    "raggedleft",
    "label",
    "uses",
    "protect",
    "relax",
    "sloppy",
    "fussy",
    "allowbreak",
    "linebreak",
    "nolinebreak",
    "pagebreak",
    "nopagebreak",
    "newpage",
    "clearpage",
    "cleardoublepage",
    "maketitle",
    "tableofcontents",
    "printbibliography",
    "bibliography",
    "bibliographystyle",
    "addcontentsline",
    "thispagestyle",
    "pagestyle",
    "setcounter",
    "addtocounter",
    "numberwithin",
    "qed",
    "qedhere",
    "displaystyle",
    "footnotesize",
    "small",
    "large",
    "Large",
    "LARGE",
    "huge",
    "Huge",
    "normalsize",
    "scriptsize",
    "tiny",
    "em",
    "bf",
    "it",
    "rm",
    "sc",
    "tt",
    "sf",
    "bfseries",
    "itshape",
    "scshape",
    "ttfamily",
    "rmfamily",
    "sffamily",
    "upshape",
    "mdseries",
    "normalfont",
    "phantomsection",
    "index",
    "glossary",
    "nocite",
    "par",
    "leavevmode",
    "ignorespaces",
    "unskip",
    "frenchspacing",
    "nonfrenchspacing",
    "hyphenation",
    "selectlanguage",
}
SYMBOLS = {
    "S": "§",
    "P": "¶",
    "dots": "…",
    "ldots": "…",
    "textellipsis": "…",
    "&": "&amp;",
    "%": "%",
    "$": "$",
    "#": "#",
    "_": "_",
    "{": "{",
    "}": "}",
    "textbackslash": "\\",
    "textendash": "–",
    "textemdash": "—",
    "textquoteleft": "‘",
    "textquoteright": "’",
    "textquotedblleft": "“",
    "textquotedblright": "”",
    "TeX": "TeX",
    "LaTeX": "LaTeX",
    "LaTeXe": "LaTeX2e",
    "copyright": "©",
    "dag": "†",
    "ddag": "‡",
    "pounds": "£",
    "textdegree": "°",
    "textasciitilde": "~",
    "textasciicircum": "^",
    "textbar": "|",
    "textless": "&lt;",
    "textgreater": "&gt;",
    "textbullet": "•",
    "guillemotleft": "«",
    "guillemotright": "»",
    "ss": "ß",
    "ae": "æ",
    "AE": "Æ",
    "oe": "œ",
    "OE": "Œ",
    "o": "ø",
    "O": "Ø",
    "aa": "å",
    "AA": "Å",
    "i": "ı",
    "j": "ȷ",
    "l": "ł",
    "L": "Ł",
    " ": " ",
    ",": "\u2009",
    ";": "\u2005",
    "!": "",
    "@": "",
    "/": "",
    "-": "",
    "quad": "\u2003",
    "qquad": "\u2003\u2003",
    "space": " ",
    "enspace": "\u2002",
    "thinspace": "\u2009",
    "slash": "/",
    "textvisiblespace": "␣",
}
ACCENTS = {
    "'": "\u0301",
    "`": "\u0300",
    "^": "\u0302",
    '"': "\u0308",
    "~": "\u0303",
    "=": "\u0304",
    ".": "\u0307",
    "u": "\u0306",
    "v": "\u030c",
    "H": "\u030b",
    "c": "\u0327",
    "k": "\u0328",
    "b": "\u0331",
    "d": "\u0323",
    "r": "\u030a",
    "t": "\u0361",
}
MAX_MACRO_DEPTH = 8


@dataclass
class RenderContext:
    file: str
    text: str
    clean: str
    key: str
    labels: dict[str, str]
    regions: dict[str, str]  # region key -> container key
    numbers: dict[str, AuxNumber]
    macros: dict[str, Macro]
    taxa: dict[str, Taxon]
    child_at: dict[int, tuple[int, str]]
    child_html: Callable[[str], str]
    include_html: Callable[[str], str]  # for \input{...} lines: html for the included file's nodes
    fallback: Callable[[str, str, str], str]  # (latex, css_class, data_src) -> html
    cite_target: Callable[[str, str | None], str | None]
    cite_labels: dict[str, str] = field(default_factory=dict)  # citekey -> the label the compiled document prints
    diagnostics: list[Diagnostic] = field(default_factory=list)
    footnotes: int = 0
    region_ids: dict[str, str] = field(default_factory=dict)  # label -> element id
    highlight_spans: list[tuple[int, int]] = field(default_factory=list)  # comparison-only source ranges

    def src(self, a: int, b: int) -> str:
        return f"{self.file}:{a}:{b}"


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower() or "x"


def ligatures(s: str) -> str:
    s = s.replace("---", "—").replace("--", "–")
    s = s.replace("``", "“").replace("''", "”").replace("`", "‘").replace("'", "’")
    s = s.replace("~", "\u00a0")
    return s


_LABEL_IN_ENV = re.compile(r"\\label\s*\{([^}]*)\}")


def number_of(ctx: RenderContext, label: str) -> str | None:
    n = ctx.numbers.get(label)
    return n.number if n else None


TEXT_SAFE_CMDS = frozenset(
    {"text", "textrm", "textbf", "textit", "textsc", "textsf", "texttt", "textup", "emph", "mbox"}
)


def math_only(body: str) -> bool:
    """Whether a macro's body is something only math mode accepts: a superscript, a subscript, or any command outside the few that text mode has."""
    if re.search(r"[\^_]", body):
        return True
    return any(name not in TEXT_SAFE_CMDS for name in re.findall(r"\\([A-Za-z@]+)", body))


def _dollars_in_body(body: str, macros: dict[str, Macro]) -> str:
    """One `\\text{…}` body with each math-only macro of the author's, and its arguments, written between dollars."""
    out: list[str] = []
    i = 0
    for m in re.finditer(r"\\([A-Za-z@]+)", body):
        if m.start() < i or body.count("$", 0, m.start()) % 2:  # already written inside math
            continue
        macro = macros.get(m.group(1))
        if macro is None or not math_only(macro.body):
            continue
        _, _, after = read_args(body, m.end(), "m" * macro.args)
        out.append(body[i : m.start()])
        out.append("$" + body[m.start() : after] + "$")
        i = after
    out.append(body[i:])
    return "".join(out)


_REF = re.compile(r"\\(eqref|ref|cref|Cref|autoref)\s*\{([^}]*)\}")
_TEXT_ARG = re.compile(r"\\(tag|text|mbox|textrm|textit|textbf|intertext|shortintertext)\s*\*?\s*\{")


def _sub_refs_in_text_arguments(tex: str, repl: Callable[[re.Match[str], bool], str]) -> str:
    """Replace every reference inside a text-mode argument with its bare number, leaving the rest of the formula alone.

    `\\tag{Equation \\eqref{eqn:9}}` is an ordinary thing to write and its argument is already text, so the `\\text{…}` that keeps a label upright everywhere else is an error there. Brace-matched rather than regexed, because these arguments nest.
    """
    out: list[str] = []
    pos = 0
    while True:
        m = _TEXT_ARG.search(tex, pos)
        if m is None:
            out.append(tex[pos:])
            return "".join(out)
        depth = 1
        i = m.end()
        while i < len(tex) and depth:
            depth += {"{": 1, "}": -1}.get(tex[i], 0)
            i += 1
        out.append(tex[pos : m.end()])
        out.append(_REF.sub(lambda r: repl(r, False), tex[m.end() : i]))
        pos = i


def dollars_in_text(tex: str, macros: dict[str, Macro]) -> str:
    """Inside every `\\text{…}`, write a macro whose body only math mode accepts between dollars.

    LaTeX runs `\\text{nodes of \\ul C}` because `\\ul` opens math itself; MathJax's text mode has no `\\underline` and refuses the whole formula, which is what showed the ACGS proof as its source. `\\text{nodes of $\\ul C$}` is the same document to LaTeX and renders in both.
    """
    if not macros or "\\text" not in tex and "\\mbox" not in tex:
        return tex
    out: list[str] = []
    i = 0
    for m in re.finditer(r"\\(?:text|mbox)\s*\{", tex):
        if m.start() < i:
            continue
        opening = m.end() - 1
        close = match_group(tex, opening, "{", "}")
        if close <= 0:
            continue
        out.append(tex[i : opening + 1])
        out.append(_dollars_in_body(tex[opening + 1 : close - 1], macros))
        i = close - 1
    out.append(tex[i:])
    return "".join(out)


class Converter:
    def __init__(self, ctx: RenderContext) -> None:
        self.ctx = ctx

    def _changed(self, start: int, end: int) -> bool:
        return any((a < end and b > start) or (a == b and start < a < end) for a, b in self.ctx.highlight_spans)

    def _prose(self, value: str, start: int) -> str:
        """Mark only source characters that changed, before ligatures and escaping alter them."""
        if not self.ctx.highlight_spans:
            return esc(ligatures(value))
        end = start + len(value)
        cuts = {start, end}
        for a, b in self.ctx.highlight_spans:
            if start < a < end:
                cuts.add(a)
            if start < b < end:
                cuts.add(b)
        points = sorted(cuts)
        out: list[str] = []
        for a, b in zip(points, points[1:]):
            if any(lo == hi == a for lo, hi in self.ctx.highlight_spans):
                out.append('<span class="review-change-point" aria-label="edit point"></span>')
            piece = esc(ligatures(value[a - start : b - start]))
            if any(lo < b and hi > a for lo, hi in self.ctx.highlight_spans):
                piece = f'<mark class="review-changed">{piece}</mark>'
            out.append(piece)
        if any(lo == hi == end for lo, hi in self.ctx.highlight_spans):
            out.append('<span class="review-change-point" aria-label="edit point"></span>')
        return "".join(out)

    # ---- ranges and blocks -------------------------------------------------

    def render_range(self, a: int, b: int) -> str:
        """Render file text [a, b) as blocks, substituting child claimants and inclusion lines."""
        out: list[str] = []
        pos = a
        while pos < b:
            child = self.ctx.child_at.get(pos)
            if child is not None:
                end, key = child
                out.append(self.ctx.child_html(key))
                pos = end
                continue
            nxt = min([s for s in self.ctx.child_at if pos < s < b] + [b])
            out.append(self._blocks(pos, nxt))
            pos = nxt
        return "".join(out)

    def _blocks(self, a: int, b: int) -> str:
        toks = [t for t in tokenize(self.ctx.clean[a:b])]
        toks = [Tok(t.kind, t.start + a, t.end + a, t.value) for t in toks]
        return self._walk(toks, a, b)

    def _walk(self, toks: list[Tok], a: int, b: int) -> str:
        ctx = self.ctx
        clean = ctx.clean
        out: list[str] = []
        para: list[str] = []
        pstart = [a]
        fallback_reason: list[str | None] = [None]

        def flush(pend: int) -> None:
            body = "".join(para)
            if body.strip():
                if fallback_reason[0]:
                    latex = ctx.text[pstart[0] : pend].strip()
                    ctx.diagnostics.append(
                        Diagnostic(
                            "info",
                            "loom:converter-fallback",
                            f"{fallback_reason[0]} in {ctx.key}; rendered as SVG",
                            [Location(ctx.file, 0)],
                            [ctx.key],
                        )
                    )
                    out.append(ctx.fallback(latex, "fallback", ctx.src(pstart[0], pend)))
                else:
                    out.append(f'<p data-src="{ctx.src(pstart[0], pend)}">{body.strip()}</p>')
            para.clear()
            fallback_reason[0] = None

        def emit_text(value: str, start: int) -> None:
            parts = re.split(r"(\n[ \t]*\n\s*)", value)
            offset = start
            for k, part in enumerate(parts):
                if k % 2 == 1:
                    flush(offset)
                    offset += len(part)
                    pstart[0] = offset
                    continue
                if part:
                    if not para and not part.strip():
                        pstart[0] = offset + len(part)
                    para.append(self._prose(part, offset))
                offset += len(part)

        i = 0
        n = len(toks)
        while i < n:
            t = toks[i]
            if not para:
                pstart[0] = t.start
            if t.kind == "text":
                emit_text(t.value, t.start)
                i += 1
                continue
            if t.kind == "begin":
                env = t.value
                end_idx = self._matching_end(toks, i)
                env_end = toks[end_idx].end if end_idx is not None else b
                if env in DISPLAY_ENVS:
                    flush(t.start)
                    out.append(self.display_env(env, t.start, env_end))
                elif env in LIST_ENVS:
                    flush(t.start)
                    out.append(self.list_env(env, t.start, env_end, toks[i + 1 : end_idx] if end_idx else []))
                elif env in DIAGRAM_ENVS:
                    flush(t.start)
                    out.append(ctx.fallback(ctx.text[t.start : env_end], "diagram", ctx.src(t.start, env_end)))
                elif env in VERBATIM_ENVS:
                    flush(t.start)
                    inner = ctx.text[t.end : toks[end_idx].start] if end_idx else ctx.text[t.end : env_end]
                    code = esc(inner.strip("\n"))
                    out.append(f'<pre data-src="{ctx.src(t.start, env_end)}"><code>{code}</code></pre>')
                elif env in ("figure", "figure*", "table", "table*", "wrapfigure"):
                    flush(t.start)
                    out.append(self.figure_env(t, env_end, end_idx, toks))
                elif env in ("tabular", "tabular*", "array", "longtable"):
                    flush(t.start)
                    out.append(self.tabular_env(t, env_end, end_idx))
                elif env in CONTAINER_ENVS:
                    flush(t.start)
                    inner_start = toks[i + 1].start if end_idx and i + 1 < end_idx else t.end
                    inner_end = toks[end_idx].start if end_idx else env_end
                    _, _, after = (
                        read_args(clean, t.end, "o") if env in ("frame", "block", "minipage") else (None, None, t.end)
                    )
                    if env == "minipage":
                        _, _, after = read_args(clean, after, "m")
                    inner = self.render_range(max(after, inner_start if inner_start > after else after), inner_end)
                    tag = "blockquote" if env in ("quote", "quotation", "abstract") else "div"
                    if tag == "div":
                        out.append(inner)
                    else:
                        out.append(f'<{tag} data-src="{ctx.src(t.start, env_end)}">{inner}</{tag}>')
                elif t.start in ctx.child_at:
                    flush(t.start)
                    out.append(ctx.child_html(ctx.child_at[t.start][1]))
                elif env in ("proof",) or env in ctx.taxa:
                    flush(t.start)
                    out.append(self.inline_env(t, env, env_end, end_idx, toks))
                elif env in ("document",):
                    i += 1
                    continue
                else:
                    flush(t.start)
                    ctx.diagnostics.append(
                        Diagnostic(
                            "info",
                            "loom:converter-fallback",
                            f"environment {env} in {ctx.key}; rendered as SVG",
                            [Location(ctx.file, 0)],
                            [ctx.key],
                        )
                    )
                    out.append(ctx.fallback(ctx.text[t.start : env_end], "fallback", ctx.src(t.start, env_end)))
                i = (end_idx + 1) if end_idx is not None else n
                continue
            if t.kind == "end":
                i += 1
                continue
            if t.kind == "math":
                if t.value in ("$$", "\\["):
                    close_val = "$$" if t.value == "$$" else "\\]"
                    j = next(
                        (k for k in range(i + 1, n) if toks[k].kind == "math" and toks[k].value == close_val), None
                    )
                    flush(t.start)
                    end = toks[j].end if j is not None else b
                    inner = ctx.text[t.end : toks[j].start] if j is not None else ctx.text[t.end : b]
                    out.append(self.display_block(inner, t.start, end, None))
                    i = (j + 1) if j is not None else n
                    continue
                if t.value in ("$", "\\("):
                    close_val = "$" if t.value == "$" else "\\)"
                    j = next(
                        (k for k in range(i + 1, n) if toks[k].kind == "math" and toks[k].value == close_val), None
                    )
                    inner = ctx.text[t.end : toks[j].start] if j is not None else ctx.text[t.end : b]
                    changed = " review-changed" if self._changed(t.start, toks[j].end if j is not None else b) else ""
                    para.append(f'<span class="math inline{changed}">\\({esc(self.math_text(inner))}\\)</span>')
                    i = (j + 1) if j is not None else n
                    continue
                i += 1
                continue
            if t.kind == "verb":
                para.append(f"<code>{esc(t.value)}</code>")
                i += 1
                continue
            if t.kind == "verbatim":
                i += 1
                continue
            if t.kind == "open":
                j = self._matching_close(toks, i)
                inner_html, reason = self.inline_range(toks[i + 1 : j], toks[i].end, toks[j].start if j < n else b)
                para.append(inner_html)
                if reason and not fallback_reason[0]:
                    fallback_reason[0] = reason
                i = j + 1
                continue
            if t.kind in ("close", "bopen", "bclose"):
                if t.kind in ("bopen", "bclose"):
                    para.append(esc(t.value))
                i += 1
                continue
            if t.kind == "cmd":
                name = t.value
                if name in ("iffalse", "if0"):
                    i = self._skip_conditional(toks, i)
                    continue
                if name.rstrip("*") in SECTIONING:
                    flush(t.start)
                    (short, title), spans, after = read_args(clean, t.end, "om")
                    level = SECTIONING[name.rstrip("*")]
                    h = min(max(level, 1), 6)
                    title_html = self.inline_text(title or "", spans[1][0]) if title is not None else ""
                    lm = re.match(r"\s*\\label\s*\{([^}]*)\}", clean[after:])
                    hid = f' id="{slug(norm_label(lm.group(1)))}"' if lm else ""
                    out.append(f'<h{h}{hid} data-src="{ctx.src(t.start, after)}">{title_html}</h{h}>')
                    i, tail = self._resume(toks, i, after)
                    if tail:
                        emit_text(ctx.text[tail[0] : tail[1]], tail[0])
                    continue
                if name in ("input", "include", "nest"):
                    flush(t.start)
                    (arg,), spans, after = read_args(clean, t.end, "m")
                    out.append(ctx.include_html(arg or ""))
                    i, tail = self._resume(toks, i, after)
                    if tail:
                        emit_text(ctx.text[tail[0] : tail[1]], tail[0])
                    continue
                if name == "includegraphics":
                    flush(t.start)
                    (opts, arg), spans, after = read_args(clean, t.end, "om")
                    out.append(ctx.include_html("graphics:" + (arg or "")))
                    i, tail = self._resume(toks, i, after)
                    if tail:
                        emit_text(ctx.text[tail[0] : tail[1]], tail[0])
                    continue
                if name == "item":
                    i += 1
                    continue
                piece, after, reason = self.inline_command(t, toks, i, b)
                if piece is not None:
                    para.append(piece)
                if reason and not fallback_reason[0]:
                    fallback_reason[0] = reason
                if after > t.end:
                    i, tail = self._resume(toks, i, after)
                    if tail:
                        emit_text(ctx.text[tail[0] : tail[1]], tail[0])
                else:
                    i += 1
                continue
            i += 1
        flush(b)
        return "".join(out)

    # ---- helpers over the token list --------------------------------------

    def _matching_end(self, toks: list[Tok], i: int) -> int | None:
        depth = 0
        name = toks[i].value
        for k in range(i, len(toks)):
            if toks[k].kind == "begin" and toks[k].value == name:
                depth += 1
            elif toks[k].kind == "end" and toks[k].value == name:
                depth -= 1
                if depth == 0:
                    return k
        return None

    def _matching_close(self, toks: list[Tok], i: int) -> int:
        depth = 0
        for k in range(i, len(toks)):
            if toks[k].kind == "open":
                depth += 1
            elif toks[k].kind == "close":
                depth -= 1
                if depth == 0:
                    return k
        return len(toks)

    def _skip_conditional(self, toks: list[Tok], i: int) -> int:
        """Skip from an \\iffalse to its matching \\fi, honouring nested conditionals."""
        depth = 0
        for k in range(i, len(toks)):
            t = toks[k]
            if t.kind != "cmd":
                continue
            if t.value.startswith("if") and t.value not in ("iff",):
                depth += 1
            elif t.value == "fi":
                depth -= 1
                if depth == 0:
                    return k + 1
        return len(toks)

    def _skip_to(self, toks: list[Tok], i: int, pos: int) -> int:
        k = i + 1
        while k < len(toks) and toks[k].start < pos:
            k += 1
        return k

    def _resume(self, toks: list[Tok], i: int, pos: int) -> tuple[int, tuple[int, int] | None]:
        """Where to carry on after a command's arguments, and the text they ended in the middle of.

        An argument written without braces — the `e` of `\\'etale`, the path of `\\input file.tex` — is taken from inside the text that follows the command, and the rest of that text (`tale topology…`) is still text. Returns the next token's index and the span of any such remainder.
        """
        k = self._skip_to(toks, i, pos)
        prev = toks[k - 1] if k - 1 > i else None
        if prev is not None and prev.kind == "text" and prev.start < pos < prev.end:
            return k, (pos, prev.end)
        return k, None

    # ---- inline ----------------------------------------------------------------

    def inline_text(self, text: str, base: int, depth: int = 0) -> str:
        """Convert a LaTeX string in text mode (a title, a footnote body, a macro expansion) to inline HTML."""
        toks = [Tok(t.kind, t.start + base, t.end + base, t.value) for t in tokenize(text)]
        html_out, _ = self.inline_range(toks, base, base + len(text), text_override=text, depth=depth)
        return html_out

    def inline_range(
        self, toks: list[Tok], a: int, b: int, text_override: str | None = None, depth: int = 0
    ) -> tuple[str, str | None]:
        ctx = self.ctx
        raw = text_override
        base = a if raw is not None else 0

        def rawslice(x: int, y: int) -> str:
            return raw[x - base : y - base] if raw is not None else ctx.text[x:y]

        out: list[str] = []
        reason: str | None = None
        i = 0
        n = len(toks)
        while i < n:
            t = toks[i]
            if t.kind == "text":
                out.append(self._prose(t.value, t.start))
            elif t.kind == "math":
                if t.value in ("$", "\\(", "$$", "\\["):
                    close_val = {"$": "$", "\\(": "\\)", "$$": "$$", "\\[": "\\]"}[t.value]
                    j = next(
                        (k for k in range(i + 1, n) if toks[k].kind == "math" and toks[k].value == close_val), None
                    )
                    inner = rawslice(t.end, toks[j].start) if j is not None else rawslice(t.end, b)
                    changed = " review-changed" if self._changed(t.start, toks[j].end if j is not None else b) else ""
                    out.append(f'<span class="math inline{changed}">\\({esc(self.math_text(inner))}\\)</span>')
                    i = (j + 1) if j is not None else n
                    continue
            elif t.kind == "open":
                j = self._matching_close(toks, i)
                close_start = toks[j].start if j < n else b
                # the override handed down must start where the inner range starts, or every offset inside the group is off by the prefix
                inner_override = rawslice(toks[i].end, close_start) if raw is not None else None
                inner_html, r = self.inline_range(toks[i + 1 : j], toks[i].end, close_start, inner_override, depth)
                out.append(inner_html)
                reason = reason or r
                i = j + 1
                continue
            elif t.kind == "verb":
                out.append(f"<code>{esc(t.value)}</code>")
            elif t.kind == "cmd":
                piece, after, r = self.inline_command(t, toks, i, b, text_override, depth, origin=base)
                if piece is not None:
                    out.append(piece)
                reason = reason or r
                if after > t.end:
                    i, tail = self._resume(toks, i, after)
                    if tail:
                        out.append(esc(ligatures(rawslice(*tail))))
                    continue
            elif t.kind in ("begin", "end"):
                reason = reason or f"environment {t.value} inside a paragraph"
            i += 1
        return "".join(out), reason

    def inline_command(
        self,
        t: Tok,
        toks: list[Tok],
        i: int,
        b: int,
        text_override: str | None = None,
        depth: int = 0,
        origin: int | None = None,
    ) -> tuple[str | None, int, str | None]:
        """Render one command in text mode. Returns (html or None, position after its arguments, fallback reason or None). `origin` is the absolute offset where `text_override` starts."""
        ctx = self.ctx
        clean = ctx.clean if text_override is None else None
        name = t.value

        def args(spec: str) -> tuple[list[str | None], list[tuple[int, int]], int]:
            if clean is not None:
                return read_args(clean, t.end, spec)
            base = origin if origin is not None else (toks[0].start if toks else t.start)
            local = text_override or ""
            vals, spans, after = read_args(local, t.end - base, spec)
            return vals, [(s + base, e + base) for s, e in spans], after + base

        if name in REF_CMDS:
            (arg,), spans, after = args("m")
            return self.ref_html(name, arg or "", spans[0], t.start), after, None
        if name in CITE_CMDS:
            (o1, o2, keys), spans, after = args("oom")
            post = o2 if o2 is not None else o1
            return self.cite_html(keys or "", post), after, None
        if name == "footnote":
            (body,), spans, after = args("m")
            ctx.footnotes += 1
            inner = self.inline_text(body or "", spans[0][0], depth + 1)
            return f'<span class="footnote" data-n="{ctx.footnotes}">{inner}</span>', after, None
        if name == "url":
            (u,), spans, after = args("m")
            return f'<a class="url" href="{html.escape(u or "", quote=True)}">{esc(u or "")}</a>', after, None
        if name == "href":
            (u, label), spans, after = args("mm")
            inner = self.inline_text(label or "", spans[1][0], depth + 1)
            return f'<a class="url" href="{html.escape(u or "", quote=True)}">{inner}</a>', after, None
        if name == "incomplete":
            (body,), spans, after = args("m")
            inner = self.inline_text(body or "", spans[0][0], depth + 1)
            return f'<span class="incomplete" data-key="{html.escape(ctx.key, quote=True)}">{inner}</span>', after, None
        if name in ("label", "uses"):
            (_,), _, after = args("m")
            return None, after, None
        if name in (
            "newcommand",
            "renewcommand",
            "providecommand",
            "DeclareMathOperator",
            "def",
            "let",
            "newtheorem",
            "theoremstyle",
            "newenvironment",
            "renewenvironment",
            "setlength",
            "newlength",
            "newcounter",
        ):
            return None, self._skip_definition(name, t, text_override, toks), None
        if name == "\\":
            (_,), _, after = args("o")
            return "<br>", max(after, t.end), None
        if name in INLINE_WRAP:
            tag = INLINE_WRAP[name]
            if tag == "!color":
                (_, colour, body), spans, after = args("omm")
                inner = self.inline_text(body or "", spans[2][0], depth + 1)
                # the colour's LaTeX name travels to the viewer, which knows the common ones and lets anything else inherit; dropping it lost an author's own convention for marking unverified text
                named = html.escape(re.sub(r"\s+", " ", colour or "").strip(), quote=True)
                return (f'<span class="tex-color" data-color="{named}">{inner}</span>' if named else inner), after, None
            if tag == "!decl":
                (_, _), _, after = args("om")
                return None, after, None
            (body,), spans, after = args("m")
            inner = self.inline_text(body or "", spans[0][0], depth + 1)
            if not tag:
                return inner, after, None
            if "." in tag:
                el, cls = tag.split(".")
                return f'<{el} class="{cls}">{inner}</{el}>', after, None
            return f"<{tag}>{inner}</{tag}>", after, None
        if name in ACCENTS:
            (body,), spans, after = args("m")
            base_char = (body or "").strip("{}") or ""
            if base_char in ("\\i", "\\j"):
                base_char = "ı" if base_char == "\\i" else "ȷ"
            return esc(base_char + ACCENTS[name]) if base_char else "", after, None
        if name in SYMBOLS:
            return SYMBOLS[name], t.end, None
        if name in IGNORED_CMDS:
            spec = {
                "frametitle": "m",
                "framesubtitle": "m",
                "usetheme": "om",
                "usecolortheme": "om",
                "logo": "m",
                "institute": "om",
                "date": "om",
                "author": "om",
                "title": "om",
                "subtitle": "om",
                "thanks": "m",
                "email": "m",
                "address": "m",
                "subjclass": "om",
                "keywords": "m",
                "urladdr": "m",
                "dedicatory": "m",
                "vspace": "m",
                "vspace*": "m",
                "hspace": "m",
                "hspace*": "m",
                "bibliography": "m",
                "bibliographystyle": "m",
                "setcounter": "mm",
                "addtocounter": "mm",
                "numberwithin": "mm",
                "thispagestyle": "m",
                "pagestyle": "m",
                "addcontentsline": "mmm",
                "index": "m",
                "nocite": "m",
                "hyphenation": "m",
                "selectlanguage": "m",
            }.get(name, "")
            _, _, after = args(spec) if spec else ([], [], t.end)
            return None, after, None
        if name in ("textsuperscript", "textsubscript"):
            (body,), spans, after = args("m")
            return self.inline_text(body or "", spans[0][0], depth + 1), after, None
        if name in ("caption",):
            (_, body), spans, after = args("om")
            return self.inline_text(body or "", spans[1][0], depth + 1), after, None
        macro = ctx.macros.get(name)
        if macro is not None and depth < MAX_MACRO_DEPTH:
            spec = ("o" if macro.default is not None else "") + "m" * (
                macro.args - (1 if macro.default is not None else 0)
            )
            vals, spans, after = args(spec) if spec else ([], [], t.end)
            arg_values = [v if v is not None else (macro.default or "") for v in vals]
            expansion = expand(macro, arg_values)
            if not expansion.strip():
                return None, after, None
            # whether a macro is mathematics is a property of its definition, not of what it is applied to: testing the expansion made `\red{... \cite{author_Title2025} ...}` mathematics because a citekey holds an underscore, and set a paragraph of prose in the renderer's error colour
            if (
                re.search(r"\\(mathrm|mathbf|mathcal|mathbb|frac|operatorname)\b|[\^_]", macro.body)
                and "$" not in expansion
            ):
                return f'<span class="math inline">\\({esc(expansion)}\\)</span>', after, None
            return self.inline_text(expansion, t.start, depth + 1), after, None
        return esc("\\" + name), t.end, f"unknown command \\{name}"

    def _skip_definition(self, name: str, t: Tok, text_override: str | None, toks: list[Tok]) -> int:
        """Position after a definition command and its arguments, which the converter never renders."""
        from loom.scan.macros import _read_body, _read_name

        text = self.ctx.clean if text_override is None else text_override
        base = 0 if text_override is None else (toks[0].start if toks else t.start)
        pos = t.end - base
        if name == "let":
            _, pos = _read_name(text, pos)
            if pos < len(text) and text[pos] == "=":
                pos += 1
            _, pos = _read_name(text, pos)
            return pos + base
        if name in ("theoremstyle", "setlength", "newlength", "newcounter"):
            _, _, after = read_args(text, pos, "m" if name != "setlength" else "mm")
            return after + base
        if name == "newtheorem":
            _, _, after = read_args(text, pos, "momo")
            return after + base
        if name in ("newenvironment", "renewenvironment"):
            _, _, after = read_args(text, pos, "moomm")
            return after + base
        if name == "def":
            _, pos = _read_name(text, pos)
            m = re.match(r"[^{]*", text[pos:])
            pos += m.end() if m else 0
            _, pos = _read_body(text, pos)
            return pos + base
        _, pos = _read_name(text, pos)
        _, _, pos = read_args(text, pos, "oo")
        _, pos = _read_body(text, pos)
        if name == "DeclareMathOperator":
            pass
        return pos + base

    def ref_html(self, cmd: str, label: str, span: tuple[int, int], offset: int) -> str:
        ctx = self.ctx
        parts = [re.sub(r"\s+", " ", x).strip() for x in (label.split(",") if cmd in ("cref", "Cref") else [label])]
        pieces = []
        for lab in parts:
            target = ctx.labels.get(lab)
            num = number_of(ctx, lab)
            if target is None:
                pieces.append(f'<a class="ref ref-dangling" data-target="{html.escape(lab, quote=True)}">??</a>')
                continue
            container = ctx.regions.get(target, target)
            is_region = target in ctx.regions
            text = num if num else (lab if is_region else target)
            if cmd == "eqref" or (is_region and cmd != "pageref"):
                text = f"({num})" if num else f"({lab})"
                cls = "ref ref-eq"
            else:
                cls = "ref"
            href = "#" + slug(target)
            cite_id = f"cite-{slug(ctx.file)}-{offset}-{slug(target)}"
            pieces.append(
                f'<a id="{cite_id}" class="{cls}" data-target="{html.escape(target, quote=True)}" href="{href}">{esc(text)}</a>'
            )
            _ = container
        return ", ".join(pieces)

    def cite_html(self, keys: str, postnote: str | None) -> str:
        ctx = self.ctx
        out = []
        for ck in [re.sub(r"\s+", " ", k).strip() for k in keys.split(",") if k.strip()]:
            target = ctx.cite_target(ck, postnote)
            attrs = f' data-citekey="{html.escape(ck, quote=True)}"'
            if postnote:
                attrs += f' data-postnote="{html.escape(postnote, quote=True)}"'
            if target:
                attrs += f' data-target="{html.escape(target, quote=True)}"'
            label = (
                f"[{esc(ctx.cite_labels.get(ck, ck))}"
                + (f", {self.inline_text(postnote, 0, MAX_MACRO_DEPTH)}" if postnote else "")
                + "]"
            )
            out.append(f'<span class="cite"{attrs}>{label}</span>')
        return " ".join(out)

    # ---- math -------------------------------------------------------------------

    def math_text(self, tex: str) -> str:
        """TeX math left for the viewer: comments and labels removed, `\\qedhere` dropped, references replaced by their numbers or labels so MathJax never sees \\ref, and a macro of the author's written between dollars where it sits in text.

        A comment inside a formula is what the author sees as deleted mathematics; leaving it in ends the formula at the first `%` for MathJax, which is how a commented-out line of an `align` swallowed its own `\\end{align*}`.
        """
        tex = blank_comments(tex)
        tex = re.sub(r"\\label\s*\{[^}]*\}", "", tex)
        tex = re.sub(r"\\qedhere(?![A-Za-z@])", "", tex)  # amsthm places the tombstone; the viewer has none to place
        tex = dollars_in_text(tex, self.ctx.macros)

        def ref_repl(m: re.Match[str], upright: bool = True) -> str:
            lab = re.sub(r"\s+", " ", m.group(2)).strip()
            shown = number_of(self.ctx, lab) or lab
            if m.group(1) == "eqref":
                shown = f"({shown})"
            # `\text{…}` keeps a label upright, and inside an argument LaTeX already reads as text it is an error:
            # MathJax refuses the whole formula with "\text is only supported in math mode", which is how
            # `\tag{Equation \eqref{…}}` published as its own source on a yellow ground.
            return f"\\text{{{shown}}}" if upright else shown

        tex = _sub_refs_in_text_arguments(tex, ref_repl)
        tex = re.sub(_REF, ref_repl, tex)
        return tex.strip()

    def display_env(self, env: str, start: int, end: int) -> str:
        ctx = self.ctx
        raw = blank_comments(
            ctx.text[start:end]
        )  # a commented-out line carries a commented-out \label, which is not the block's number
        m = re.match(r"\\begin\s*\{" + re.escape(env) + r"\}(.*)\\end\s*\{" + re.escape(env) + r"\}\s*$", raw, re.S)
        inner = m.group(1) if m else raw
        labels = re.findall(r"\\label\s*\{([^}]*)\}", inner)
        first = re.sub(r"\s+", " ", labels[0]).strip() if labels else None
        body = self.math_text(inner)
        base = env.rstrip("*")
        starred = env.endswith("*")
        if base in ("equation", "displaymath"):
            num = number_of(ctx, first) if first else None
            tex = "\\[" + (f"\\tag{{{num}}}" if num and not starred else "") + body + "\\]"
        else:
            if not starred and base in ("align", "gather", "multline", "eqnarray", "alignat", "flalign"):
                body = self._tag_lines(inner)
            tex = (
                f"\\begin{{{base}*}}{body}\\end{{{base}*}}"
                if base not in ("split", "cases")
                else f"\\[\\begin{{{base}}}{body}\\end{{{base}}}\\]"
            )
        return self.display_block_html(tex, start, end, first)

    def _tag_lines(self, inner: str) -> str:
        lines = re.split(r"(\\\\(?:\[[^\]]*\])?)", inner)
        out = []
        for piece in lines:
            if piece.startswith("\\\\"):
                out.append(piece)
                continue
            labels = re.findall(r"\\label\s*\{([^}]*)\}", piece)
            cleaned = self.math_text(piece)
            if labels:
                num = number_of(self.ctx, re.sub(r"\s+", " ", labels[0]).strip())
                if num and "\\tag" not in cleaned and "\\notag" not in cleaned:
                    cleaned = cleaned + f"\\tag{{{num}}}"
            out.append(cleaned)
        return "".join(out)

    def display_block(self, inner: str, start: int, end: int, label: str | None) -> str:
        return self.display_block_html("\\[" + self.math_text(inner) + "\\]", start, end, label)

    def display_block_html(self, tex: str, start: int, end: int, label: str | None) -> str:
        ctx = self.ctx
        src = ctx.src(start, end)
        num = number_of(ctx, label) if label else None
        if not renders_as_math(tex):
            # a commutative diagram written inside a display environment is a picture; handing it to the viewer's mathematics renderer sets the whole block in error colour
            figure = ctx.fallback(self._undisplay(ctx.text[start:end]), "diagram", src)
            extra = ""
            if label:
                extra += f' id="{slug(ctx.key + "-" + label)}" data-label="{html.escape(label, quote=True)}"'
            if num:
                extra += f' data-number="{html.escape(num, quote=True)}"'
            return figure.replace("<figure ", f"<figure{extra} ", 1) if extra else figure
        attrs = f' data-src="{src}"'
        if label:
            attrs += f' id="{slug(ctx.key + "-" + label)}" data-label="{html.escape(label, quote=True)}"'
            if num:
                attrs += f' data-number="{html.escape(num, quote=True)}"'
        changed = " review-changed" if self._changed(start, end) else ""
        return f'<div class="math display{changed}"{attrs}>{esc(tex)}</div>'

    @staticmethod
    def _undisplay(raw: str) -> str:
        """The block as the fallback should compile it: numbered display environments starred, so the picture carries no number of its own.

        The number the document gave it is on the figure, where a viewer can print it; a standalone compile would otherwise start counting again and print (1).
        """
        out = re.sub(
            r"\\(begin|end)\s*\{(equation|align|gather|multline|eqnarray|alignat|flalign)\}", r"\\\1{\2*}", raw
        )
        out = re.sub(r"\\label\s*\{[^}]*\}", "", out)
        # a label alone on its line leaves a blank one behind, and a blank line inside a display environment is a LaTeX error
        return re.sub(r"\n[ \t]*\n+", "\n", out)

    # ---- lists, figures, tables ----------------------------------------------------

    def list_env(self, env: str, start: int, end: int, inner_toks: list[Tok]) -> str:
        ctx = self.ctx
        tag = LIST_ENVS[env]
        begin_len = len(re.match(r"\\begin\s*\{[^}]*\}", ctx.clean[start:]).group(0))  # type: ignore[union-attr]
        _, _, after = read_args(ctx.clean, start + begin_len, "o")
        body_start = after
        end_m = re.search(r"\\end\s*\{" + re.escape(env) + r"\}\s*$", ctx.clean[start:end])
        body_end = start + end_m.start() if end_m else end
        items = self._split_items(body_start, body_end)
        parts = [f'<{tag} data-src="{ctx.src(start, end)}">']
        for opt, a, b in items:
            inner = self.render_range(a, b)
            inner = (
                re.sub(r'^<p data-src="[^"]*">(.*)</p>$', r"\1", inner.strip(), flags=re.S)
                if inner.count("<p ") == 1
                else inner
            )
            if tag == "dl":
                parts.append(f"<dt>{self.inline_text(opt or '', a)}</dt><dd>{inner}</dd>")
            elif opt is not None:
                parts.append(f'<li data-label="{html.escape(opt, quote=True)}">{inner}</li>')
            else:
                parts.append(f"<li>{inner}</li>")
        parts.append(f"</{tag}>")
        return "".join(parts)

    def _split_items(self, a: int, b: int) -> list[tuple[str | None, int, int]]:
        clean = self.ctx.clean
        items: list[tuple[str | None, int, int]] = []
        depth = 0
        pos = a
        current: tuple[str | None, int] | None = None
        for t in tokenize(clean[a:b]):
            s = t.start + a
            if t.kind == "begin":
                depth += 1
            elif t.kind == "end":
                depth -= 1
            elif t.kind == "cmd" and t.value == "item" and depth == 0:
                if current is not None:
                    items.append((current[0], current[1], s))
                (opt,), _, after = read_args(clean, t.end + a, "o")
                current = (opt, after)
        if current is not None:
            items.append((current[0], current[1], b))
        _ = pos
        return items

    def figure_env(self, t: Tok, env_end: int, end_idx: int | None, toks: list[Tok]) -> str:
        ctx = self.ctx
        inner_start = read_args(ctx.clean, t.end, "o")[2]
        inner_end = toks[end_idx].start if end_idx is not None else env_end
        inner_raw = ctx.clean[inner_start:inner_end]
        cap = re.search(r"\\caption\s*(\[[^\]]*\])?\s*\{", inner_raw)
        caption_html = ""
        body_ranges: list[tuple[int, int]] = []
        if cap:
            cstart = inner_start + cap.start()
            cend = match_group(ctx.clean, inner_start + cap.end() - 1)
            caption_html = f"<figcaption>{self.inline_text(ctx.clean[inner_start + cap.end() : cend - 1], inner_start + cap.end())}</figcaption>"
            body_ranges = [(inner_start, cstart), (cend, inner_end)]
        else:
            body_ranges = [(inner_start, inner_end)]
        body = "".join(self.render_range(x, y) for x, y in body_ranges if y > x)
        body = re.sub(r'<p data-src="[^"]*">\s*</p>', "", body)
        return f'<figure data-src="{ctx.src(t.start, env_end)}">{body}{caption_html}</figure>'

    def inline_env(self, t: Tok, env: str, env_end: int, end_idx: int | None, toks: list[Tok]) -> str:
        """A theorem-like environment or a proof written inline in a container, as HTML rather than as an SVG picture of itself.

        The markup matches what a node fragment carries (`fragments.py`), minus the node identity: an environment written inline claims no key.
        """
        ctx = self.ctx
        (title,), spans, after = read_args(ctx.clean, t.end, "o")
        body_end = toks[end_idx].start if end_idx is not None else env_end
        body = self.render_range(after, body_end)
        data_src = ctx.src(t.start, env_end)
        if env == "proof":
            title_html = f' <span class="title">{self.inline_text(title, spans[0][0])}</span>' if title else ""
            return f'<details class="env env-proof" data-src="{data_src}" open><summary class="env-label">Proof{title_html}</summary>{body}</details>'
        taxon = ctx.taxa.get(env)
        name = taxon.name if taxon else env.capitalize()
        style = taxon.style if taxon else "plain"
        num = None
        for m in _LABEL_IN_ENV.finditer(ctx.clean, t.start, body_end):
            num = number_of(ctx, norm_label(m.group(1)))
            if num:
                break
        parts = [f'<span class="taxon">{esc(name)}</span>']
        if num:
            parts.append(f' <span class="number">{esc(num)}</span>')
        if title:
            parts.append(f' <span class="title">({self.inline_text(title, spans[0][0])})</span>')
        # an unclaimed environment carries no identity (DR-86) but still needs an anchor, or no link into a canon document can land
        first_label = next((norm_label(m.group(1)) for m in _LABEL_IN_ENV.finditer(ctx.clean, t.start, body_end)), None)
        ident = f' id="{slug(first_label)}"' if first_label else ""
        attrs = (
            f'class="env env-{slug(name)}"{ident} data-taxon="{html.escape(name, quote=True)}" '
            f'data-style="{html.escape(style, quote=True)}" data-src="{data_src}"'
        )
        return f'<div {attrs}><p class="env-label">{"".join(parts)}</p>{body}</div>'

    def tabular_env(self, t: Tok, env_end: int, end_idx: int | None) -> str:
        ctx = self.ctx
        raw = ctx.text[t.start : env_end]
        m = re.match(
            r"\\begin\s*\{(tabular\*?|array|longtable)\}\s*(\{[^}]*\})?\s*(\{[^}]*\})?(.*)\\end\s*\{\1\}", raw, re.S
        )
        if not m:
            return ctx.fallback(raw, "fallback", ctx.src(t.start, env_end))
        body = m.group(4)
        if re.search(r"\\(multicolumn|multirow|cline|cmidrule|parbox|begin\{)", body):
            ctx.diagnostics.append(
                Diagnostic(
                    "info",
                    "loom:converter-fallback",
                    f"complex table in {ctx.key}; rendered as SVG",
                    [Location(ctx.file, 0)],
                    [ctx.key],
                )
            )
            return ctx.fallback(raw, "fallback", ctx.src(t.start, env_end))
        body = re.sub(r"\\(hline|toprule|midrule|bottomrule)", "", body)
        rows = [r for r in re.split(r"\\\\(?:\[[^\]]*\])?", body) if r.strip()]
        html_rows = []
        for r in rows:
            cells = [self.inline_text(c.strip(), 0, MAX_MACRO_DEPTH) for c in r.split("&")]
            html_rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        return f'<table data-src="{ctx.src(t.start, env_end)}"><tbody>{"".join(html_rows)}</tbody></table>'
