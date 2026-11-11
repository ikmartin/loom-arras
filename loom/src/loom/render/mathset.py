"""Formulas set for the viewer's typesetter: TeX left as TeX, with what MathJax cannot read made plain, each display numbered as the document's aux numbers it, and a picture told apart from mathematics so TeX draws it.

A formula comes from the source, not from TeX4ht's rewriting of it, so a quote copies what the author wrote; TeX decided only where it stands.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from loom.scan.model import Macro
from loom.scan.source import blank_comments
from loom.scan.tokenize import match_group, read_args
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
#: Where a `\label` names an equation's number: `subequations` labels the parent number of the displays inside it.
EQUATION_ENVS = DISPLAY_ENVS | {"subequations"}
#: Environments the viewer's typesetter handles inside a display; anything else in one makes the display a picture.
MATH_SAFE_ENVS = {
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
    "CD",  # amscd, which the typesetter draws natively; a diagram but not a picture
}
#: Commands that draw rather than typeset; `\xymatrix@C=1cm{...}` continues the control word with xy's syntax, so only a letter does.
_DRAWS = re.compile(
    r"\\(xymatrix|xygraph|xybox|tikz|pgfplots|includegraphics|scalebox|resizebox|raisebox|parbox|fbox|shortstack)(?![A-Za-z])"
)
_ENV_IN = re.compile(r"\\begin\s*\{([^}]*)\}")
_LABEL = re.compile(r"\\label\s*\{([^}]*)\}")
_REF = re.compile(r"\\(eqref|ref|cref|Cref|autoref)\s*\{([^}]*)\}")
_TEXT_ARG = re.compile(r"\\(tag|text|mbox|textrm|textit|textbf|intertext|shortintertext)\s*\*?\s*\{")
_TEXT_SAFE_CMDS = frozenset(
    {"text", "textrm", "textbf", "textit", "textsc", "textsf", "texttt", "textup", "emph", "mbox"}
)
_NUMBERED_ROWS = ("align", "gather", "multline", "eqnarray", "alignat", "flalign")


def renders_as_math(tex: str) -> bool:
    """Whether a display is mathematics the typesetter can set, or a picture TeX must draw.

    An environment outside `MATH_SAFE_ENVS`, or a drawing command, makes it a picture: an allowlist sends an environment nobody anticipated to TeX, which can always draw it.
    """
    if _DRAWS.search(tex):
        return False
    return all(name.strip().rstrip("*") in MATH_SAFE_ENVS for name in _ENV_IN.findall(tex))


@dataclass
class Display:
    """A display as the viewer shows it: `tex` for the typesetter, or, when `picture`, the display for TeX to draw, unnumbered; its first label and the number the aux gives it."""

    tex: str
    label: str | None
    number: str | None
    picture: bool


def set_display(raw: str, env: str | None, numbers: Mapping[str, AuxNumber], macros: Mapping[str, Macro]) -> Display:
    """The display `raw`, as the source writes it (`\\begin{env}...\\end{env}`, or `\\[...\\]` when `env` is None), set for the viewer.

    A numbered environment's number rides on `\\tag`, row by row in a multi-row one, since the typesetter numbers nothing itself; comments go first, since a commented-out line carries a commented-out `\\label`.
    """
    raw = blank_comments(raw)
    if env is None:
        inner = re.sub(r"^\s*\\\[|\\\]\s*$", "", raw)
    else:
        m = re.match(r"\\begin\s*\{" + re.escape(env) + r"\}(.*)\\end\s*\{" + re.escape(env) + r"\}\s*$", raw, re.S)
        inner = m.group(1) if m else raw
    labels = _LABEL.findall(inner)
    first = re.sub(r"\s+", " ", labels[0]).strip() if labels else None
    number = _number(numbers, first) if first else None
    if env is None:
        tex = "\\[" + math_text(inner, numbers, macros) + "\\]"
    else:
        base, starred = env.rstrip("*"), env.endswith("*")
        if base in ("equation", "displaymath"):
            tag = f"\\tag{{{number}}}" if number and not starred else ""
            tex = "\\[" + tag + math_text(inner, numbers, macros) + "\\]"
        else:
            body = (
                _tag_rows(inner, numbers, macros)
                if not starred and base in _NUMBERED_ROWS
                else math_text(inner, numbers, macros)
            )
            tex = (
                f"\\[\\begin{{{base}}}{body}\\end{{{base}}}\\]"
                if base in ("split", "cases")
                else f"\\begin{{{base}*}}{body}\\end{{{base}*}}"
            )
    if not renders_as_math(tex):
        return Display(undisplay(raw), first, number, True)
    return Display(tex, first, number, False)


def undisplay(raw: str) -> str:
    """A display as TeX draws it for a picture: numbered environments starred and labels gone, so the picture carries no number of its own and a blank line a label left does not end the display."""
    out = re.sub(r"\\(begin|end)\s*\{(equation|align|gather|multline|eqnarray|alignat|flalign)\}", r"\\\1{\2*}", raw)
    out = _LABEL.sub("", out)
    return re.sub(r"\n[ \t]*\n+", "\n", out)


def math_text(tex: str, numbers: Mapping[str, AuxNumber], macros: Mapping[str, Macro]) -> str:
    """TeX math left for the viewer: comments and labels out, `\\qedhere` dropped, each reference its number, and a macro of the author's that only math mode accepts written between dollars where it sits in text.

    A comment inside a formula ends it at the first `%` for MathJax, which is how a commented-out row of an `align` swallowed its `\\end{align*}`; MathJax has no `\\ref`; and amsthm places the tombstone `\\qedhere` asks for, where the viewer has none to place.
    """
    tex = blank_comments(tex)
    tex = _LABEL.sub("", tex)
    tex = re.sub(r"\\qedhere(?![A-Za-z@])", "", tex)
    tex = _dollars_in_text(tex, macros)

    def ref(m: re.Match[str], upright: bool = True) -> str:
        lab = re.sub(r"\s+", " ", m.group(2)).strip()
        shown = _number(numbers, lab) or lab
        if m.group(1) == "eqref":
            shown = f"({shown})"
        # an argument TeX already reads as text, a \tag's, refuses \text: MathJax rejects the whole formula
        return f"\\text{{{shown}}}" if upright else shown

    tex = _refs_in_text_arguments(tex, ref)
    tex = _REF.sub(ref, tex)
    return tex.strip()


def _number(numbers: Mapping[str, AuxNumber], label: str) -> str | None:
    n = numbers.get(label)
    return n.number if n else None


def _tag_rows(inner: str, numbers: Mapping[str, AuxNumber], macros: Mapping[str, Macro]) -> str:
    """Each row of a numbered multi-row display with its own label's number as a `\\tag`."""
    out = []
    for piece in re.split(r"(\\\\(?:\[[^\]]*\])?)", inner):
        if piece.startswith("\\\\"):
            out.append(piece)
            continue
        labels = _LABEL.findall(piece)
        cleaned = math_text(piece, numbers, macros)
        if labels:
            num = _number(numbers, re.sub(r"\s+", " ", labels[0]).strip())
            if num and "\\tag" not in cleaned and "\\notag" not in cleaned:
                cleaned += f"\\tag{{{num}}}"
        out.append(cleaned)
    return "".join(out)


def _refs_in_text_arguments(tex: str, repl: Callable[[re.Match[str], bool], str]) -> str:
    """Each reference inside a text-mode argument (`\\tag{...}`, `\\text{...}`) replaced bare, brace-matched since these nest."""
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


def _math_only(body: str) -> bool:
    """Whether a macro's body is something only math mode accepts: a script, or a command text mode lacks."""
    if re.search(r"[\^_]", body):
        return True
    return any(name not in _TEXT_SAFE_CMDS for name in re.findall(r"\\([A-Za-z@]+)", body))


def _dollars_in_text(tex: str, macros: Mapping[str, Macro]) -> str:
    """Inside each `\\text{...}`, a macro of the author's whose body only math mode accepts written between dollars.

    LaTeX runs `\\text{nodes of \\ul C}` because `\\ul` opens math itself; MathJax's text mode has no `\\underline` and refuses the formula. `\\text{nodes of $\\ul C$}` is the same document to LaTeX and sets in both.
    """
    if not macros or ("\\text" not in tex and "\\mbox" not in tex):
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
        body = tex[opening + 1 : close - 1]
        pieces: list[str] = []
        j = 0
        for c in re.finditer(r"\\([A-Za-z@]+)", body):
            if c.start() < j or body.count("$", 0, c.start()) % 2:
                continue
            macro = macros.get(c.group(1))
            if macro is None or not _math_only(macro.body):
                continue
            _, _, after = read_args(body, c.end(), "m" * macro.args)
            pieces += [body[j : c.start()], "$" + body[c.start() : after] + "$"]
            j = after
        pieces.append(body[j:])
        out.append("".join(pieces))
        i = close - 1
    out.append(tex[i:])
    return "".join(out)
