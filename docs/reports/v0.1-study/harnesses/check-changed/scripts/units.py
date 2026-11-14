"""Units of a text that a Changed row would name: LaTeX statements and proofs, LaTeX prose by section, Markdown sections, whole other files. And which units a change between two texts touches.

A LaTeX block is a theorem-like environment (declared by \\newtheorem in the quilt) or a proof, keyed by its first label, else by name and ordinal. Prose is text outside every block, keyed by the section heading above it. A Markdown section runs from a heading to the next heading of any level, keyed by the heading's words and their ordinal. Line diffs, not word diffs: a block spans lines, so the units touched are the same, and the copy's 600 KB diff stays in seconds.
"""
from __future__ import annotations

import bisect
import difflib
import re

THM: set[str] = set()
_LABEL = re.compile(r"\\label\{([^}]*)\}")
_SEC = re.compile(r"\\(?:sub)*section\*?\{")
_MDH = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t#]*$", re.M)
_FENCE = re.compile(r"^(```|~~~)", re.M)


def set_envs(names):
    THM.clear()
    THM.update(names)
    THM.add("proof")


def kind_of(path: str) -> str:
    if path.endswith(".tex"):
        return "tex"
    if path.endswith(".md"):
        return "md"
    return "other"


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def tex_units(text: str):
    """[(start, end, key, ukind)] with ukind 'block' or 'prose'; blocks innermost-last order irrelevant."""
    if not THM:
        raise RuntimeError("set_envs first")
    pat = re.compile(r"\\(begin|end)\{(" + "|".join(sorted(map(re.escape, THM), key=len, reverse=True)) + r")\*?\}")
    stack = []
    blocks = []
    counts: dict[str, int] = {}
    for m in pat.finditer(text):
        if m.group(1) == "begin":
            stack.append((m.group(2), m.start()))
        else:
            for i in range(len(stack) - 1, -1, -1):
                if stack[i][0] == m.group(2):
                    name, s = stack.pop(i)
                    e = m.end()
                    head = text[s : min(e, s + 400)]
                    lab = _LABEL.search(head)
                    counts[name] = counts.get(name, 0) + 1
                    key = lab.group(1) if lab and name != "proof" else None
                    blocks.append([s, e, key, name])
                    break
    blocks.sort()
    # a proof's key: the statement before it, as loom keys a proof by the result it proves
    last_stmt = None
    ordn: dict[str, int] = {}
    out = []
    for s, e, key, name in blocks:
        if name == "proof":
            k = f"{last_stmt}/proof" if last_stmt else None
            if k is None or any(o[2] == k for o in out[-3:]):
                ordn["proof"] = ordn.get("proof", 0) + 1
                k = f"#proof:{ordn['proof']}"
            out.append((s, e, k, "block"))
        else:
            if key is None:
                ordn[name] = ordn.get(name, 0) + 1
                key = f"#{name}:{ordn[name]}"
            last_stmt = key
            out.append((s, e, key, "block"))
    # prose: the gaps between top-level blocks, keyed by the last section heading
    secs = [(m.start(), text[m.end() : text.find("}", m.end())][:50]) for m in _SEC.finditer(text)]
    sec_starts = [s for s, _ in secs]
    tops = []
    end = -1
    for s, e, k, u in out:
        if s >= end:
            tops.append((s, e))
            end = e
        else:
            end = max(end, e)
    gaps = []
    pos = 0
    for s, e in tops:
        if s > pos:
            gaps.append((pos, s))
        pos = max(pos, e)
    if pos < len(text):
        gaps.append((pos, len(text)))
    for s, e in gaps:
        # split a gap at section headings inside it
        cuts = [s] + [x for x in sec_starts if s < x < e] + [e]
        for a, b in zip(cuts, cuts[1:]):
            i = bisect.bisect_right(sec_starts, a) - 1
            title = secs[i][1] if i >= 0 else "(front)"
            out.append((a, b, "prose:" + _slug(title) + f"@{i}", "prose"))
    return out


def md_units(text: str):
    # headings outside fenced code
    fences = [m.start() for m in _FENCE.finditer(text)]
    inside = []
    for a, b in zip(fences[::2], fences[1::2]):
        inside.append((a, b))
    heads = [m for m in _MDH.finditer(text) if not any(a <= m.start() < b for a, b in inside)]
    out = []
    seen: dict[str, int] = {}
    starts = [0] + [m.start() for m in heads]
    keys = ["md:(top)"]
    for m in heads:
        s = _slug(m.group(2))
        seen[s] = seen.get(s, 0) + 1
        keys.append(f"md:{s}#{seen[s]}")
    ends = starts[1:] + [len(text)]
    for s, e, k in zip(starts, ends, keys):
        if e > s or k == "md:(top)":
            out.append((s, e, k, "md"))
    return out


def units(path: str, text: str):
    k = kind_of(path)
    if k == "tex":
        return tex_units(text)
    if k == "md":
        return md_units(text)
    return [(0, len(text), "file", "other")]


def _lines(t: str):
    return t.splitlines(keepends=True)


def spans(old: str, new: str):
    """Changed spans as (o0, o1, n0, n1) character offsets, from a line diff."""
    a, b = _lines(old), _lines(new)
    oa = [0]
    for x in a:
        oa.append(oa[-1] + len(x))
    ob = [0]
    for x in b:
        ob.append(ob[-1] + len(x))
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return [(oa[i1], oa[i2], ob[j1], ob[j2]) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal"]


def quick_span(old: str, new: str):
    """One span from common prefix and suffix: exact for a single edit."""
    lo, hi = 0, min(len(old), len(new))
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if old[:mid] == new[:mid]:
            lo = mid
        else:
            hi = mid - 1
    p = lo
    lo, hi = 0, min(len(old), len(new)) - p
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if old[len(old) - mid :] == new[len(new) - mid :]:
            lo = mid
        else:
            hi = mid - 1
    s = lo
    return [(p, len(old) - s, p, len(new) - s)]


def touched(path: str, old: str | None, new: str | None, sp=None, uold=None, unew=None):
    """{(ukind, key)} a change from old to new touches; a block inside a block counts both, as pending._blocks does."""
    if old is None and new is None:
        return set()
    if old is None:
        return {("newfile", path)} | {(u[3], u[2]) for u in (unew or units(path, new))}
    if new is None:
        return {("gonefile", path)}
    if sp is None:
        sp = spans(old, new)
    un = unew if unew is not None else units(path, new)
    uo = uold if uold is not None else units(path, old)
    hit = set()
    for o0, o1, n0, n1 in sp:
        got = False
        for s, e, k, u in un:
            if (s < n1 and n0 < e) or (n0 == n1 and s <= n0 < e):
                hit.add((u, k))
                got = got or u == "block"
        # a block that was removed: found in the old text only
        for s, e, k, u in uo:
            if u == "block" and s < o1 and o0 < e and (o0 <= s and e <= o1):
                hit.add(("removed", k))
    return hit
