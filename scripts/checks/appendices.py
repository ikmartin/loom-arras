#!/usr/bin/env python3
"""Appendices C and D equal the files loom ships: `ai/rules.md` and `ai/modes/*.md` in C, `ai/orientation.md` in D (plan 0.14.1 phase 4).

Usage:
    scripts/checks/appendices.py [--write]

Each appendix is its own preamble, then every file after a `---` line, in full and in order (rules.md, then the modes by name). The shipped files are the source of truth; `--write` rewrites the appendices from them. Exit 0 when both agree, 1 otherwise.
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AI = ROOT / "loom" / "src" / "loom" / "assets" / "ai"
BOOK = ROOT / "docs" / "book"
FIX = "python3 scripts/checks/appendices.py --write"


def carried() -> dict[Path, list[Path]]:
    """Each appendix and the shipped files it reproduces, in the order it carries them."""
    return {
        BOOK / "C-mode-templates.md": [AI / "rules.md", *sorted((AI / "modes").glob("*.md"))],
        BOOK / "D-orientation.md": [AI / "orientation.md"],
    }


def expected(appendix: Path, files: list[Path]) -> str:
    """The appendix's own preamble (everything before the first `---` line) followed by each file after a rule."""
    preamble = appendix.read_text(encoding="utf-8").split("\n---\n", 1)[0].rstrip("\n")
    body = "".join("\n\n---\n\n" + f.read_text(encoding="utf-8").strip("\n") for f in files)
    return preamble + body + "\n"


def sections(text: str) -> list[str]:
    return [s.strip("\n") for s in text.split("\n---\n")[1:]]


def disagreements(appendix: Path, files: list[Path]) -> list[str]:
    """One line per shipped file the appendix lacks, misquotes or carries in excess, naming the first differing line."""
    have = sections(appendix.read_text(encoding="utf-8"))
    want = [f.read_text(encoding="utf-8").strip("\n") for f in files]
    out: list[str] = []
    for i in range(max(len(have), len(want))):
        if i >= len(have):
            out.append(f"{appendix.relative_to(ROOT)} lacks {files[i].relative_to(ROOT)}")
        elif i >= len(want):
            out.append(
                f"{appendix.relative_to(ROOT)} carries a section no shipped file has: {have[i].splitlines()[0]!r}"
            )
        elif have[i] != want[i]:
            diff = [
                line
                for line in difflib.unified_diff(want[i].splitlines(), have[i].splitlines(), lineterm="", n=0)
                if line[:1] in "+-" and line[:3] not in ("+++", "---")
            ]
            out.append(
                f"{appendix.relative_to(ROOT)} differs from {files[i].relative_to(ROOT)}; first lines (- shipped, + appendix):"
            )
            out.extend("    " + line[:160] for line in diff[:4])
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--write", action="store_true", help="rewrite the appendices from the shipped files")
    args = parser.parse_args()
    problems: list[str] = []
    for appendix, files in carried().items():
        want = expected(appendix, files)
        if appendix.read_text(encoding="utf-8") == want:
            continue
        if args.write:
            appendix.write_text(want, encoding="utf-8")
            print(f"rewrote {appendix.relative_to(ROOT)}")
        else:
            problems.extend(disagreements(appendix, files) or [f"{appendix.relative_to(ROOT)} differs in its layout"])
    if problems:
        print("\n".join(problems))
        print(f"fix: {FIX}")
        return 1
    print(f"appendices: ok ({sum(len(f) for f in carried().values())} shipped files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
