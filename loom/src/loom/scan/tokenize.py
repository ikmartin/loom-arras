"""A restricted LaTeX tokenizer over comment-blanked text (book 5.1.4).

Yields commands, environment begin/end, groups, math delimiters, verbatim spans, and text runs with character offsets. It is not a TeX interpreter: it recognises surface forms and leaves the rest as text. Brace matching crosses newlines, so a citation or package list split over lines is one group.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field

VERBATIM_ENVS = {"verbatim", "verbatim*", "lstlisting", "comment", "filecontents", "filecontents*"}
MATH_SINGLE = {"(": "\\(", ")": "\\)", "[": "\\[", "]": "\\]"}

_SPECIAL = re.compile(
    r"\\begin\s*\{([^}]*)\}"  # 1 begin
    r"|\\end\s*\{([^}]*)\}"  # 2 end
    r"|\\verb\*?(\S)"  # 3 verb
    r"|\\([A-Za-z@]+\*?)"  # 4 command
    r"|\\(.)"  # 5 escaped char
    r"|(\$\$|\$)"  # 6 dollars
    r"|([{}\[\]])",  # 7 group delimiters
    re.S,
)


@dataclass(frozen=True)
class Tok:
    kind: str  # cmd begin end verb verbatim math open close bopen bclose text
    start: int
    end: int
    value: str


def tokenize(text: str) -> list[Tok]:
    toks: list[Tok] = []
    pos = 0
    n = len(text)
    while pos < n:
        m = _SPECIAL.search(text, pos)
        if m is None:
            toks.append(Tok("text", pos, n, text[pos:n]))
            break
        if m.start() > pos:
            toks.append(Tok("text", pos, m.start(), text[pos : m.start()]))
        if m.group(1) is not None:
            env = m.group(1).strip()
            toks.append(Tok("begin", m.start(), m.end(), env))
            pos = m.end()
            if env in VERBATIM_ENVS:
                close = re.compile(r"\\end\s*\{" + re.escape(env) + r"\}")
                cm = close.search(text, pos)
                stop = cm.start() if cm else n
                toks.append(Tok("verbatim", pos, stop, text[pos:stop]))
                if cm:
                    toks.append(Tok("end", cm.start(), cm.end(), env))
                    pos = cm.end()
                else:
                    pos = n
            continue
        if m.group(2) is not None:
            toks.append(Tok("end", m.start(), m.end(), m.group(2).strip()))
        elif m.group(3) is not None:
            delim = m.group(3)
            stop = text.find(delim, m.end())
            stop = n if stop < 0 else stop + 1
            toks.append(Tok("verb", m.start(), stop, text[m.end() : stop - 1]))
            pos = stop
            continue
        elif m.group(4) is not None:
            toks.append(Tok("cmd", m.start(), m.end(), m.group(4)))
        elif m.group(5) is not None:
            ch = m.group(5)
            if ch in MATH_SINGLE:
                toks.append(Tok("math", m.start(), m.end(), MATH_SINGLE[ch]))
            else:
                toks.append(Tok("cmd", m.start(), m.end(), ch))
        elif m.group(6) is not None:
            toks.append(Tok("math", m.start(), m.end(), m.group(6)))
        else:
            ch = m.group(7)
            kind = {"{": "open", "}": "close", "[": "bopen", "]": "bclose"}[ch]
            toks.append(Tok(kind, m.start(), m.end(), ch))
        pos = m.end()
    return toks


def iter_commands(text: str, names: set[str] | None = None) -> Iterator[Tok]:
    for t in tokenize(text):
        if t.kind == "cmd" and (names is None or t.value in names):
            yield t


def match_group(text: str, pos: int, open_ch: str = "{", close_ch: str = "}") -> int:
    """Given text[pos] == open_ch, return the offset just past the matching close_ch; escaped delimiters and inner braces are honoured. Returns -1 if unbalanced."""
    if pos >= len(text) or text[pos] != open_ch:
        return -1
    depth = 0
    i = pos
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "{" and open_ch != "{":
            j = match_group(text, i, "{", "}")
            i = j if j > 0 else i + 1
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def skip_space(text: str, pos: int, allow_newline: bool = True) -> int:
    n = len(text)
    while pos < n and text[pos] in " \t\n":
        if text[pos] == "\n" and not allow_newline:
            break
        pos += 1
    return pos


def read_optional(text: str, pos: int) -> tuple[str | None, int, int, int]:
    """Read an optional [..] argument at pos (after whitespace without a blank line). Returns (content, content_start, content_end, next_pos)."""
    p = skip_space(text, pos)
    if text[pos:p].count("\n") > 1:
        return None, pos, pos, pos
    if p < len(text) and text[p] == "[":
        q = match_group(text, p, "[", "]")
        if q > 0:
            return text[p + 1 : q - 1], p + 1, q - 1, q
    return None, pos, pos, pos


def read_mandatory(text: str, pos: int) -> tuple[str | None, int, int, int]:
    """Read a mandatory {..} argument at pos (after whitespace). Returns (content, content_start, content_end, next_pos); a single token without braces counts too."""
    p = skip_space(text, pos)
    if p < len(text) and text[p] == "{":
        q = match_group(text, p, "{", "}")
        if q > 0:
            return text[p + 1 : q - 1], p + 1, q - 1, q
        return None, pos, pos, pos
    if p < len(text) and text[p] == "\\":
        m = re.match(r"\\[A-Za-z@]+\*?|\\.", text[p:])
        if m:
            return m.group(0), p, p + len(m.group(0)), p + len(m.group(0))
    if p < len(text) and not text[p].isspace():
        return text[p], p, p + 1, p + 1
    return None, pos, pos, pos


def read_args(text: str, pos: int, spec: str) -> tuple[list[str | None], list[tuple[int, int]], int]:
    """Read arguments after a command per spec: 'o' optional, 'm' mandatory. Returns values, (start,end) spans, next position."""
    values: list[str | None] = []
    spans: list[tuple[int, int]] = []
    for kind in spec:
        if kind == "o":
            v, s, e, pos = read_optional(text, pos)
        else:
            v, s, e, pos = read_mandatory(text, pos)
        values.append(v)
        spans.append((s, e))
    return values, spans, pos


def env_tree(text: str) -> tuple[list[EnvNode], list[tuple[str, int, str]]]:
    """Nest every environment in the text. Returns top-level environments and a list of problems (kind, offset, env)."""
    roots: list[EnvNode] = []
    stack: list[EnvNode] = []
    problems: list[tuple[str, int, str]] = []
    for t in tokenize(text):
        if t.kind == "begin":
            optarg, s, e, body = read_optional(text, t.end)
            node = EnvNode(t.value, t.start, -1, body, -1, optarg, (s, e) if optarg is not None else None)
            if stack:
                stack[-1].children.append(node)
                node.parent = stack[-1]
            else:
                roots.append(node)
            stack.append(node)
        elif t.kind == "end":
            if stack and stack[-1].name == t.value:
                node = stack.pop()
                node.body_end = t.start
                node.end = t.end
            else:
                idx = next((i for i in range(len(stack) - 1, -1, -1) if stack[i].name == t.value), None)
                if idx is None:
                    problems.append(("end-without-begin", t.start, t.value))
                else:
                    for orphan in stack[idx + 1 :]:
                        problems.append(("unclosed", orphan.start, orphan.name))
                        orphan.body_end = t.start
                        orphan.end = t.start
                    node = stack[idx]
                    del stack[idx:]
                    node.body_end = t.start
                    node.end = t.end
    for orphan in stack:
        problems.append(("unclosed", orphan.start, orphan.name))
        orphan.body_end = len(text)
        orphan.end = len(text)
    return roots, problems


@dataclass
class EnvNode:
    name: str
    start: int
    end: int
    body_start: int
    body_end: int
    optarg: str | None
    optarg_span: tuple[int, int] | None
    children: list[EnvNode] = field(default_factory=list)
    parent: EnvNode | None = None

    def walk(self) -> Iterator[EnvNode]:
        yield self
        for c in self.children:
            yield from c.walk()
