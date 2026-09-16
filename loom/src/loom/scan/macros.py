"""Macro definitions from the preamble closure (book 9.4.3, 8.3.1), replacing the sitegen regexes with brace matching.

Forms: \\newcommand{\\x}[n][default]{body}, \\newcommand\\x{body}, \\renewcommand, \\providecommand, \\def\\x#1#2{body}, \\DeclareMathOperator*{\\x}{body}, \\let\\a\\b, \\NewDocumentCommand\\x{argspec}{body}. Later definitions win. Expansion substitutes #n and is used for text-mode macros and macro display names.
"""

from __future__ import annotations

import re

from loom.scan.model import Macro
from loom.scan.tokenize import match_group, read_optional, skip_space

_HEAD = re.compile(
    r"\\(newcommand|renewcommand|providecommand|DeclareRobustCommand|NewDocumentCommand|RenewDocumentCommand"
    r"|ProvideDocumentCommand|DeclareMathOperator|def|let)(\*?)"
)
_NAME = re.compile(r"\\([A-Za-z@]+|.)")


def _read_name(text: str, pos: int) -> tuple[str | None, int]:
    p = skip_space(text, pos)
    if p < len(text) and text[p] == "{":
        q = match_group(text, p)
        inner = text[p + 1 : q - 1].strip() if q > 0 else ""
        m = _NAME.match(inner)
        return (m.group(1), q) if m and q > 0 else (None, pos)
    m = _NAME.match(text, p)
    return (m.group(1), m.end()) if m else (None, pos)


def _read_body(text: str, pos: int) -> tuple[str | None, int]:
    p = skip_space(text, pos)
    if p < len(text) and text[p] == "{":
        q = match_group(text, p)
        if q > 0:
            return text[p + 1 : q - 1], q
    return None, pos


_ALIAS = re.compile(
    r"\\(?:let|def)\s*\\([A-Za-z@]+)\s*=?\s*\\((?:re|provide)?newcommand|providecommand)\b"
    r"|\\(?:new|renew|provide)command\*?\s*\{?\\([A-Za-z@]+)\}?\s*\{\\((?:re|provide)?newcommand|providecommand)\}"
)


def expand_definition_aliases(text: str) -> str:
    """Rewrite uses of an alias such as `\\nc` (declared by `\\newcommand{\\nc}{\\newcommand}` or `\\let\\nc\\newcommand`) as the command it stands for, so definitions made through it are parsed."""
    for _ in range(4):  # an alias may be declared through another alias (\\nc{\\renc}{\\renewcommand})
        aliases: dict[str, str] = {}
        for a in _ALIAS.finditer(text):
            name = a.group(1) or a.group(3)
            target = a.group(2) or a.group(4)
            if name and target and name not in ("newcommand", "renewcommand", "providecommand"):
                aliases[name] = target
        if not aliases:
            return text
        pattern = re.compile(r"\\(" + "|".join(re.escape(n) for n in aliases) + r")(?![A-Za-z@])")
        table = dict(aliases)

        def _swap(mm: re.Match[str], al: dict[str, str] = table) -> str:
            return "\\" + al[mm.group(1)]

        text = pattern.sub(_swap, text)
    return text


def parse_macros(text: str) -> dict[str, Macro]:
    """Parse every recognised definition in comment-blanked text; the returned dict maps macro name (no backslash) to its last definition."""
    text = expand_definition_aliases(text)
    macros: dict[str, Macro] = {}
    for m in _HEAD.finditer(text):
        head, star = m.group(1), m.group(2)
        pos = m.end()
        if head == "let":
            a, pos = _read_name(text, pos)
            p = skip_space(text, pos)
            if p < len(text) and text[p] == "=":
                pos = p + 1
            b, pos = _read_name(text, pos)
            if a and b:
                target = macros.get(b)
                macros[a] = Macro(a, target.args if target else 0, target.body if target else "\\" + b, kind="let")
            continue
        if head == "def":
            name, pos = _read_name(text, pos)
            if not name:
                continue
            params = re.match(r"\s*((?:#\d)*)", text[pos:])
            nargs = len(re.findall(r"#\d", params.group(1))) if params else 0
            pos += params.end() if params else 0
            body, pos = _read_body(text, pos)
            if body is not None:
                macros[name] = Macro(name, nargs, body, kind="def")
            continue
        if head == "DeclareMathOperator":
            name, pos = _read_name(text, pos)
            body, pos = _read_body(text, pos)
            if name and body is not None:
                op = "\\operatorname*" if star else "\\operatorname"
                macros[name] = Macro(name, 0, f"{op}{{{body}}}", kind="operator")
            continue
        if head.endswith("DocumentCommand"):
            name, pos = _read_name(text, pos)
            spec, pos = _read_body(text, pos)
            body, pos = _read_body(text, pos)
            if name and body is not None:
                nargs = len(re.findall(r"[a-zA-Z]", (spec or "").replace("O{", "o{")))
                macros[name] = Macro(name, nargs, body, kind="xparse")
            continue
        name, pos = _read_name(text, pos)
        if not name:
            continue
        nargs = 0
        default: str | None = None
        opt, _, _, pos2 = read_optional(text, pos)
        if opt is not None and opt.strip().isdigit():
            nargs = int(opt.strip())
            pos = pos2
            opt2, _, _, pos3 = read_optional(text, pos)
            if opt2 is not None:
                default = opt2
                pos = pos3
        body, pos = _read_body(text, pos)
        if body is not None:
            macros[name] = Macro(name, nargs, body, default=default, kind="newcommand")
    return macros


def expand(macro: Macro, args: list[str]) -> str:
    body = macro.body
    for i in range(macro.args, 0, -1):
        val = args[i - 1] if i - 1 < len(args) else (macro.default or "")
        body = body.replace(f"#{i}", val)
    return body


_IF = re.compile(r"\\(if[a-zA-Z@]*|else|fi)(?![a-zA-Z@])")


def _branches(body: str, start: int) -> tuple[str, str, int] | None:
    """The then-branch, else-branch and end offset of the conditional whose `\\if...` begins at `start`, or None when it is unterminated."""
    depth = 0
    split = -1
    pos = start
    while True:
        m = _IF.search(body, pos)
        if m is None:
            return None
        word = m.group(1)
        if word.startswith("if"):
            depth += 1
        elif word == "else":
            if depth == 1 and split < 0:
                split = m.start()
                then_end = m.start()
                else_start = m.end()
        else:  # fi
            depth -= 1
            if depth == 0:
                if split < 0:
                    return body[_IF.match(body, start).end() : m.start()], "", m.end()  # type: ignore[union-attr]
                return body[_IF.match(body, start).end() : then_end], body[else_start : m.start()], m.end()  # type: ignore[union-attr]
        pos = m.end()


def resolve_conditionals(body: str) -> str:
    """Rewrite the TeX conditionals a viewer's math renderer cannot evaluate.

    MathJax implements no conditionals at all, so `\\newcommand\\arr{\\ifinner\\to\\else\\longrightarrow\\fi}` reaches the page as the words `\\ifinner`, `\\else` and `\\fi` set in error red beside two arrows. `\\ifinner` asks whether the formula is inline, which is exactly what `\\mathchoice` selects on, so it is rewritten to one; `\\ifmmode` is always true inside math and takes its first branch. Anything else is left alone, since guessing a branch would silently change the mathematics.
    """
    out = body
    for _ in range(8):  # a branch may itself hold a conditional
        m = re.search(r"\\(ifinner|ifmmode)(?![a-zA-Z@])", out)
        if m is None:
            return out
        got = _branches(out, m.start())
        if got is None:
            return out
        then, other, end = got
        then, other = then.lstrip(" "), other.lstrip(" ")  # TeX skips the spaces that follow a control word
        if m.group(1) == "ifmmode":
            rep = then
        else:
            rep = "\\mathchoice{" + other + "}{" + then + "}{" + then + "}{" + then + "}"
        out = out[: m.start()] + rep + out[end:]
    return out


# LaTeX commands an author's macro body may use that a viewer's mathematics renderer does not implement, with the closest form it does. Each keeps the content and gives up only presentation, which is the trade a red error message loses on both sides.
COMPATIBILITY: dict[str, tuple[int, str]] = {  # name -> (argument count, body)
    "ensuremath": (1, "#1"),  # inside a formula this is the identity, which is where a macro body is always used
    "scalebox": (2, "#2"),  # the scale is given up; the content is not
    "resizebox": (3, "#3"),
    "raisebox": (2, "#2"),
    "mbox": (1, r"\text{#1}"),
    "hbox": (1, r"\text{#1}"),
}

# `\DeclareMathAlphabet{\name}{encoding}{family}{series}{shape}` declares a font a renderer does not have. The family is mapped to the nearest alphabet the renderer does have; an unrecognised family becomes upright roman, which is legible and honest, rather than an error.
_ALPHABET = re.compile(r"\\DeclareMathAlphabet\s*\{\s*\\([A-Za-z@]+)\s*\}\s*\{[^}]*\}\s*\{([^}]*)\}")
_FAMILY_ALPHABET = {
    "pzc": "mathcal",  # Zapf Chancery, the usual choice for a script alphabet
    "rsfs": "mathscr",
    "eus": "mathscr",
    "euf": "mathfrak",
    "bbold": "mathbb",
    "dsrom": "mathbb",
    "cmss": "mathsf",
    "cmtt": "mathtt",
}


def declared_alphabets(text: str) -> dict[str, Macro]:
    r"""Alphabets declared with `\DeclareMathAlphabet`, as macros mapping each to the nearest alphabet a renderer has."""
    out: dict[str, Macro] = {}
    for m in _ALPHABET.finditer(text):
        name, family = m.group(1), m.group(2).strip()
        target = _FAMILY_ALPHABET.get(family, "mathrm")
        out[name] = Macro(name=name, args=1, body=f"\\{target}{{#1}}")
    return out


def compatibility_macros(used: dict[str, Macro]) -> dict[str, Macro]:
    """The compatibility definitions any published body actually needs, so nothing is defined for a renderer that will never see it."""
    bodies = "".join(m.body for m in used.values())
    return {
        name: Macro(name=name, args=args, body=body)
        for name, (args, body) in COMPATIBILITY.items()
        if re.search(r"\\" + name + r"(?![A-Za-z@])", bodies)
    }


def to_mathjax(macros: dict[str, Macro]) -> list[dict[str, object]]:
    """The manifest's macro list: {name, args, body}, sorted by name (book specs/manifest.md §14)."""
    return [
        {"name": m.name, "args": m.args, "body": resolve_conditionals(m.body)}
        for m in sorted(macros.values(), key=lambda x: x.name)
    ]


MATH_ONLY_HINTS = re.compile(
    r"\\(mathrm|mathbf|mathcal|mathbb|mathfrak|mathscr|operatorname|frac|sqrt|sum|prod|int|to|colon|widetilde|hat|bar|otimes|oplus|cdot|langle|rangle|alpha|beta|gamma|delta|Delta|epsilon|lambda|mu|nu|pi|sigma|tau|phi|psi|omega|Omega|Gamma|Sigma|infty|partial|nabla|circ|times|leq|geq|neq|subset|subseteq|in|forall|exists|left|right)\b|[\^_]"
)


def is_math_macro(macro: Macro) -> bool:
    """Heuristic: a macro whose body only makes sense in math mode is left to MathJax; the converter expands the others in text."""
    return bool(MATH_ONLY_HINTS.search(macro.body)) or macro.kind == "operator"
