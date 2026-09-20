"""Line anchoring (book 5.2.3, DR-40): `\\begin` and `\\end` of theorem-like environments and proofs alone on their lines.

The scanner reads by character offset and does not care; `atomize` moves whole lines and refuses violations; `import --fix-anchoring` rewrites the copy so the lines become anchored without changing the typeset output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from loom.scan.source import blank_comments
from loom.scan.tokenize import EnvNode, env_tree, read_optional

_LABELS = re.compile(r"(\s*\\label\s*\{[^}]*\})+")


@dataclass(frozen=True)
class Violation:
    line: int
    env: str
    kind: str  # begin | end


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def anchoring_violations(text: str, theorem_names: set[str]) -> list[Violation]:
    clean = blank_comments(text)
    names = set(theorem_names) | {"proof"}
    roots, _ = env_tree(clean)
    out: list[Violation] = []

    def walk(nodes: list[EnvNode]) -> None:
        for node in nodes:
            if node.name in names:
                line_start = clean.rfind("\n", 0, node.start) + 1
                if clean[line_start : node.start].strip():
                    out.append(Violation(_line_of(clean, node.start), node.name, "begin"))
                _, _, _, after_opt = read_optional(clean, node.start + len(clean[node.start :].split("}", 1)[0]) + 1)
                m = _LABELS.match(clean, after_opt)
                head_end = m.end() if m else after_opt
                nl = clean.find("\n", head_end)
                nl = len(clean) if nl < 0 else nl
                if clean[head_end:nl].strip():
                    out.append(Violation(_line_of(clean, node.start), node.name, "begin"))
                if node.end > 0:
                    end_cmd = clean.rfind("\\end", 0, node.end)
                    ls = clean.rfind("\n", 0, end_cmd) + 1
                    if clean[ls:end_cmd].strip():
                        out.append(Violation(_line_of(clean, end_cmd), node.name, "end"))
                    nl2 = clean.find("\n", node.end)
                    nl2 = len(clean) if nl2 < 0 else nl2
                    if clean[node.end : nl2].strip():
                        out.append(Violation(_line_of(clean, end_cmd), node.name, "end"))
            walk(node.children)

    walk(roots)
    seen: set[tuple[int, str, str]] = set()
    uniq = []
    for v in out:
        k = (v.line, v.env, v.kind)
        if k not in seen:
            seen.add(k)
            uniq.append(v)
    return sorted(uniq, key=lambda v: (v.line, v.kind))


def fix_anchoring(text: str, theorem_names: set[str]) -> str:
    """Insert line breaks so every theorem-like `\\begin`/`\\end` stands alone; the output typesets identically because a line break is a space in TeX and the environments start and end in vertical mode."""
    clean = blank_comments(text)
    names = set(theorem_names) | {"proof"}
    roots, _ = env_tree(clean)
    inserts: list[int] = []

    def walk(nodes: list[EnvNode]) -> None:
        for node in nodes:
            if node.name in names:
                line_start = clean.rfind("\n", 0, node.start) + 1
                if clean[line_start : node.start].strip():
                    inserts.append(node.start)
                brace = clean.find("}", node.start) + 1
                _, _, _, after_opt = read_optional(clean, brace)
                m = _LABELS.match(clean, after_opt)
                head_end = m.end() if m else after_opt
                nl = clean.find("\n", head_end)
                nl = len(clean) if nl < 0 else nl
                if clean[head_end:nl].strip():
                    inserts.append(head_end)
                if node.end > 0:
                    end_cmd = clean.rfind("\\end", 0, node.end)
                    ls = clean.rfind("\n", 0, end_cmd) + 1
                    if clean[ls:end_cmd].strip():
                        inserts.append(end_cmd)
                    nl2 = clean.find("\n", node.end)
                    nl2 = len(clean) if nl2 < 0 else nl2
                    if clean[node.end : nl2].strip():
                        inserts.append(node.end)
            walk(node.children)

    walk(roots)
    out = text
    for pos in sorted(set(inserts), reverse=True):
        left = out[:pos].rstrip(" \t")
        right = out[pos:].lstrip(" \t")
        out = left + "\n" + right
    return out
