#!/usr/bin/env python3
"""No prose added since BASE is hard-wrapped (CLAUDE.md; plan 0.14.1 phase 4).

Usage:
    scripts/checks/hardwrap.py [--base REF] [--all]

A ratchet, not a sweep: only lines added since `--base` (default `$HARDWRAP_BASE`, else HEAD, so the working tree and the index against the last commit), plus every line of an untracked file, are judged; prose already wrapped is unwrapped when someone is next in there. `--all` judges every line of every file in scope and only reports a count per file, for measuring what is left.

A wrap is two consecutive lines of one paragraph, at least one of them added:

- markdown, outside fences, tables, headings, HTML and indented code: any two non-blank lines where the second is not a new list item, heading, table row, quote or fence;
- a Python docstring: two non-blank lines at one indentation where neither is structural (a list item, a NumPy section rule, `name : type`, `key: value`, an example, a heading line ending in a colon);
- a `#` or `//` comment, or a `*` line of a block comment: two lines at one indentation where the first does not end a sentence and the second begins in lower case, so a list of short comments is not mistaken for a paragraph.

Exit 0 when nothing added is wrapped, 1 otherwise, printing each pair.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCOPE = ("docs", "AGENTS.md", "CLAUDE.md", "scripts", "loom/src", "loom/tests", "loom/scripts", "arras/src", "arras/tests", "arras/scripts")
SKIP = re.compile(r"(^|/)(fixture|fixture-minimal|quilts|node_modules|_app|fake_latex)(/|$)|^docs/(reports|plans|long-prompts)/|\.min\.")
SUFFIXES = {".md", ".py", ".ts", ".js", ".mjs", ".svelte"}
FIX = "join each pair onto one line (CLAUDE.md: prose is never hard-wrapped), then rerun scripts/checks/hardwrap.py"

LIST = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s)")
MD_STRUCT = re.compile(r"^\s*(?:#{1,6}\s|\||>|<|```|~~~|---\s*$|\*\*\*\s*$|[-*+]\s|\d+[.)]\s|\[[^\]]+\]:\s)")
DOC_STRUCT = re.compile(
    r"^\s*(?:[-*+]\s|\d+[.)]\s|-{3,}\s*$|={3,}\s*$|\$ |>>> |\.\.\. |[\w.*]+ : |[\w./ -]{1,40}:\s*$|[\w.`-]{1,30}:\s+\S|[│├└┌─`<]|\S+\s{2,}\S)"
)
END = re.compile(r"[.:;!?)\]]$|[.:;!?][\"'`]$|\*/$|-->$")


def in_scope(path: str) -> bool:
    return path.startswith(SCOPE) and Path(path).suffix in SUFFIXES and not SKIP.search(path)


def added_lines(base: str) -> dict[str, set[int]]:
    """Line numbers (1-based, in the working tree) added since `base`; an untracked file counts whole."""
    out: dict[str, set[int]] = {}
    diff = subprocess.run(
        ["git", "diff", "-U0", "--no-color", "--no-ext-diff", base, "--", *SCOPE],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    path = ""
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else ""
        elif line.startswith("@@") and path:
            m = re.match(r"@@ -\S+ \+(\d+)(?:,(\d+))? @@", line)
            if m:
                start, count = int(m.group(1)), int(m.group(2) or "1")
                out.setdefault(path, set()).update(range(start, start + count))
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--", *SCOPE], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    for path in untracked:
        try:
            n = len((ROOT / path).read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeDecodeError):
            continue
        out[path] = set(range(1, n + 1))
    return {p: ls for p, ls in out.items() if in_scope(p)}


def markdown_pairs(lines: list[str]) -> list[int]:
    """Indices i where lines i and i+1 are one markdown paragraph."""
    pairs, fence, prev_blank = [], False, True
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith(("```", "~~~")):
            fence = not fence
        if fence or s.startswith(("```", "~~~")):
            prev_blank = False
            continue
        if not s:
            prev_blank = True
            continue
        code = prev_blank and (line.startswith("    ") or line.startswith("\t")) and not LIST.match(line)
        prev_blank = False
        if code or i + 1 >= len(lines):
            continue
        nxt = lines[i + 1]
        if not nxt.strip() or MD_STRUCT.match(nxt) or s.startswith(("|", "#", "<", ">")) or s.endswith(("  ", "\\")):
            continue
        if line.startswith((" ", "\t")) and not LIST.match(line) and not nxt.startswith((" ", "\t")):
            continue  # an indented block ending where the paragraph after it begins
        pairs.append(i)
    return pairs


def indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def python_pairs(lines: list[str]) -> list[int]:
    """Indices i where lines i and i+1 are one paragraph of a docstring or of a `#` comment."""
    pairs: list[int] = []
    quote: str | None = None
    doc = False  # the open string is a docstring: its opening quote began the statement
    for i, line in enumerate(lines):
        s = line.strip()
        opened = quote
        for q in ('"""', "'''"):
            n = s.count(q)
            if quote is None and n % 2 == 1:
                quote, doc = q, bool(re.match(r"[rRuU]?" + q, s))
                break
            if quote == q and n % 2 == 1:
                quote = None
                break
        if i + 1 >= len(lines):
            continue
        nxt = lines[i + 1]
        t = nxt.strip()
        if opened and quote == opened and doc:  # inside a docstring, on both lines
            if not s or not t or indent(line) != indent(nxt) or t.startswith(('"""', "'''")):
                continue
            if DOC_STRUCT.match(line) or DOC_STRUCT.match(nxt):
                continue
            pairs.append(i)
        elif quote is None and opened is None and s.startswith("#") and t.startswith("#") and indent(line) == indent(nxt):
            if comment_pair(line, s.lstrip("#").strip(), t.lstrip("#").strip()):
                pairs.append(i)
    return pairs


def comment_pair(line: str, a: str, b: str) -> bool:
    """Whether two consecutive comment lines are one sentence broken across them.

    Comments here are lower case with no closing stop, so two stacked comments read like one broken sentence; what tells a wrap apart is that it broke near a column limit, so the first line must end between 90 and 125 columns.
    """
    if not a or not b or END.search(a) or LIST.match(b) or not 90 <= len(line.rstrip()) <= 125:
        return False
    return bool(re.match(r"[a-z(`\"'—–]", b)) and not re.match(r"[a-z_]\w*(\.\w+)*\s*[=(\[]", b)


def slash_pairs(lines: list[str]) -> list[int]:
    """Indices i where lines i and i+1 are one sentence of a `//` comment or a `*` block-comment line."""
    pairs = []
    for i in range(len(lines) - 1):
        a, b = lines[i].strip(), lines[i + 1].strip()
        if indent(lines[i]) != indent(lines[i + 1]):
            continue
        for mark in ("//", "*"):
            if a.startswith(mark) and b.startswith(mark) and not a.startswith(("/**", "*/")) and not b.startswith("*/"):
                if comment_pair(lines[i], a[len(mark) :].strip(), b[len(mark) :].strip()):
                    pairs.append(i)
                break
    return pairs


def pairs_of(path: str, lines: list[str]) -> list[int]:
    suffix = Path(path).suffix
    if suffix == ".md":
        return markdown_pairs(lines)
    if suffix == ".py":
        return python_pairs(lines)
    return slash_pairs(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    # CI sets HARDWRAP_BASE to the push's or pull request's base, since a clean checkout has nothing added since HEAD (docs.yml)
    base = os.environ.get("HARDWRAP_BASE") or "HEAD"
    parser.add_argument("--base", default=base, help="judge lines added since this commit (default $HARDWRAP_BASE, else HEAD)")
    parser.add_argument("--all", action="store_true", help="count wrapped pairs in every file in scope, added or not")
    args = parser.parse_args()
    if args.all:
        files = subprocess.run(["git", "ls-files", "--", *SCOPE], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
        total = 0
        for path in filter(in_scope, files):
            try:
                n = len(pairs_of(path, (ROOT / path).read_text(encoding="utf-8").splitlines()))
            except (OSError, UnicodeDecodeError):
                continue
            if n:
                total += n
                print(f"{n:4d}  {path}")
        print(f"{total} wrapped pair(s) in all; the check judges only what is added")
        return 0
    bad: list[str] = []
    for path, added in sorted(added_lines(args.base).items()):
        try:
            lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for i in pairs_of(path, lines):
            if i + 1 in added or i + 2 in added:
                bad.append(f"{path}:{i + 1}\n    {lines[i].strip()[:110]}\n    {lines[i + 1].strip()[:110]}")
    if bad:
        print(f"hard-wrapped prose added since {args.base}:")
        print("\n".join(bad))
        print(f"fix: {FIX}")
        return 1
    print(f"hardwrap: ok (nothing added since {args.base} is hard-wrapped)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
