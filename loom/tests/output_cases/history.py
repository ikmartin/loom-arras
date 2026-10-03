"""Output cases for the history commands, and `init`, `id`, `import`, `atomize`, `deloom` and `adopt`; see `tests/output_cases/__init__.py`."""

from __future__ import annotations

from pathlib import Path

from tests.output_cases.base import Case, ai_copy, solo_spine

PAPER = r"""\documentclass{amsart}
\newtheorem{lemma}{Lemma}
\begin{document}
\section{Setup}
\begin{lemma}\label{lem:a}
Alpha.
\end{lemma}
\end{document}
"""


def paper(q: Path) -> None:
    """A paper of one lemma beside the quilt, at `../paper/paper.tex`."""
    p = q.parent / "paper"
    p.mkdir(exist_ok=True)
    (p / "paper.tex").write_text(PAPER, encoding="utf-8")


def stamped(q: Path) -> None:
    """A stamp just made, so the next one has nothing to record."""
    from tests.helpers import ok

    ok("stamp", "-m", "first", cwd=q)


def superseded(q: Path) -> None:
    """`drafting/solo.tex`, superseded by the flat copy `linearize` wrote of it."""
    from tests.helpers import ok

    solo_spine(q)
    ok("linearize", "drafting/solo.tex", "--to", "drafting/flat.tex", cwd=q)


KIND: dict[str, str] = {
    "init": "report",
    "id": "raw",
    "import": "report",
    "atomize": "report",
    "deloom": "report",
    "draft": "report",
    "stamp": "report",
    "fork": "raw",
    "revert": "raw",
    "live": "report",
    "mv": "report",
    "linearize": "report",
    "history": "report",
    "adopt": "report",
}

CASES: dict[str, list[Case]] = {
    "init": [
        Case(("../fresh", "--prefix", "zz", "--yes")),
        Case(("../shown", "--demo")),
        Case(("../imported", "--from", "../paper/paper.tex", "--yes"), paper),
        Case((), exit=2, why="the current directory is already a quilt"),
    ],
    "id": [
        Case(("--next",)),
        Case(("drafting/main.tex",), json=False, why="every node already has an id: nothing to label"),
        Case(("nodes/absent.tex",), exit=2, json=False, why="no such file"),
        Case((), exit=2, why="neither a file nor --next"),
    ],
    "import": [
        Case(("../paper/paper.tex", "--yes"), paper),
        Case(("../paper/paper.tex",), paper, exit=2, why="no terminal to confirm on, and no --yes"),
        Case(("absent.tex", "--yes"), exit=2, why="no such file"),
    ],
    "atomize": [
        Case(("drafting/main.tex", "drafting/spine.tex"), json=False),
        Case(("--key", "dm-9999"), exit=2, why="an unknown key"),
        Case(("drafting/main.tex",), exit=2, json=False, why="no destination"),
    ],
    "deloom": [
        Case(("main.tex", "--to", "build/plain.tex", "--keep-referenced-ids", "--keep-incomplete")),
        Case(("main.tex", "--to", "build/plain.tex"), exit=1, why="an \\incomplete blocks it"),
        Case(("absent", "--to", "build/plain.tex"), exit=2, why="no such document"),
    ],
    "draft": [
        Case(("drafting/main.tex", "--ai", "aidoc.tex")),
        Case(("drafting/absent.tex", "--ai", "aidoc.tex"), exit=2, why="no such document"),
    ],
    "stamp": [
        Case(("--message", "m")),
        Case(("--message", "again"), stamped, why="nothing has changed since the last stamp: exit 0 all the same"),
        Case(("drafting/absent.tex", "--message", "m"), exit=2, why="no such document"),
    ],
    "fork": [
        Case(("dm-0001", "--in", "drafting/main.tex")),
        Case(("dm-9999", "--in", "drafting/main.tex"), exit=2, why="an unknown key"),
    ],
    "revert": [
        Case(("dm-0001@1",)),
        Case(("dm-0001@9",), exit=2, why="a step the history does not have"),
        Case(("dm-0001",), exit=2, why="not an address"),
    ],
    "live": [
        Case(("drafting/solo.tex",), superseded),
        Case(("drafting/main.tex",), exit=2, why="not superseded"),
    ],
    "mv": [
        Case(("drafting/outline.tex", "drafting/plan.tex")),
        Case(("drafting/absent.tex", "drafting/plan.tex"), exit=2, why="neither path exists"),
    ],
    "linearize": [
        Case(("drafting/solo.tex", "--to", "drafting/flat.tex"), solo_spine),
        Case(("drafting/absent.tex", "--to", "drafting/flat.tex"), exit=2, why="no such file"),
    ],
    "history": [
        Case(()),
        Case(("dm-0001",)),
        Case(("verify",)),
        Case(("restore", "widgets-v1", "--to", "drafting/restored.tex")),
        Case(("show", "absent"), exit=2, why="no such landmark; `history show` prints a landmark's text, raw"),
        Case(("restore", "widgets-v1"), exit=2, why="no --to"),
    ],
    "adopt": [
        Case(("contribution",), ai_copy),
        Case(("contribution",), ai_copy, exit=2, env=(("AI_AGENT", "1"),), why="adoption is the author's"),
    ],
}
