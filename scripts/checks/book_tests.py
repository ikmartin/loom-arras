#!/usr/bin/env python3
"""Every test book chapter 14 names exists, and every test it says was not written does not (book 14.7; plan 0.14.1 phase 4).

Usage:
    scripts/checks/book_tests.py

Reads `docs/book/14-tests.md`:

- a backticked `test_*` name must be a test function under `loom/tests/`, except in a paragraph that begins "Not written", where a name outside parentheses must NOT exist (it is the claim that it was not written) and a name inside them must;
- on a list item, a double-quoted title outside backticks must be a `test(...)`, `it(...)` or `describe(...)` title under `arras/tests/` or in an `arras/src/**/*.spec.ts`; `<...>` in the book and `${...}` in a title match anything;
- a backticked path to a test source (under a `tests/` or `test/` directory, or a `.spec.ts` or `.e2e.ts` file) must exist under the workspace, `loom/` or `arras/`.

Exit 0 when all hold, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHAPTER = ROOT / "docs" / "book" / "14-tests.md"
BASES = (ROOT, ROOT / "loom", ROOT / "arras")
FIX = "edit docs/book/14-tests.md to name the test as it is now (or restore the test), then rerun scripts/checks/book_tests.py"

TITLE = re.compile(r"""\b(?:test|it|describe)(?:\.\w+)*\(\s*(['"`])((?:\\.|(?!\1).)*)\1""", re.S)
NAME = re.compile(r"`(test_\w+)(?:\[[^\]`]*\])?`")
SOURCE = re.compile(
    r"`((?:[\w.-]+/)*tests?/(?:[\w.-]+/)*[\w.-]+\.(?:py|ts|mjs|sh)|(?:[\w.-]+/)*[\w.-]+\.(?:spec|e2e)\.ts)`"
)
WILD = "\0"  # stands for a `${...}` in a title or a `<...>` in the book


def loom_tests() -> set[str]:
    return {
        n
        for p in (ROOT / "loom" / "tests").rglob("*.py")
        for n in re.findall(r"^\s*(?:async\s+)?def\s+(test_\w+)", p.read_text(encoding="utf-8", errors="replace"), re.M)
    }


def arras_titles() -> list[str]:
    files = [*(ROOT / "arras" / "tests").rglob("*.ts"), *(ROOT / "arras" / "src").rglob("*.spec.ts")]
    titles = [t for p in files for _, t in TITLE.findall(p.read_text(encoding="utf-8", errors="replace"))]
    return [re.sub(r"\$\{[^}]*\}", WILD, t.replace("\\'", "'").replace('\\"', '"')) for t in titles]


def matches(pattern: str, text: str) -> bool:
    """Whether `text` is `pattern` with each WILD standing for anything."""
    return re.fullmatch(".*".join(re.escape(part) for part in pattern.split(WILD)), text, re.S) is not None


def outside_parentheses(text: str) -> tuple[str, str]:
    """The paragraph split into what lies outside every parenthesis and what lies inside one."""
    out, inside, depth = [], [], 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")" and depth:
            depth -= 1
            continue
        (inside if depth else out).append(ch)
    return "".join(out), "".join(inside)


def main() -> int:
    text = CHAPTER.read_text(encoding="utf-8")
    tests, titles = loom_tests(), arras_titles()
    problems: list[str] = []
    for number, para in enumerate(text.split("\n"), 1):
        where = f"14-tests.md:{number}"
        if para.startswith("Not written"):
            claimed, cited = outside_parentheses(para)
            problems += [
                f"{where}: {n} is listed as not written, but loom/tests has it"
                for n in NAME.findall(claimed)
                if n in tests
            ]
            problems += [
                f"{where}: {n} is named and no test in loom/tests has that name"
                for n in NAME.findall(cited)
                if n not in tests
            ]
        else:
            problems += [
                f"{where}: {n} is named and no test in loom/tests has that name"
                for n in NAME.findall(para)
                if n not in tests
            ]
        for quoted in re.findall(r'"([^"]+)"', re.sub(r"`[^`]*`", "", para)) if para.startswith("- ") else []:
            pattern = re.sub(r"<[^>]*>", WILD, quoted)
            if not any(matches(pattern, t) or matches(t, pattern) for t in titles):
                problems.append(f'{where}: no arras test is titled "{quoted}"')
        for src in SOURCE.findall(para):
            if not any((base / src).exists() for base in BASES):
                problems.append(f"{where}: {src} does not exist")
    if problems:
        print("\n".join(problems))
        print(f"fix: {FIX}")
        return 1
    print(f"book tests: ok ({len(set(NAME.findall(text)))} test names, chapter 14)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
