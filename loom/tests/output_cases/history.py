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
    "atomize": "raw",
    "deloom": "report",
    "draft": "report",
    "stamp": "report",
    "fork": "raw",
    "revert": "raw",
    "live": "report",
    "mv": "report",
    "linearize": "report",
    "history": "report",
    "history show": "raw",
    "history restore": "report",
    "history verify": "report",
    "adopt": "report",
}

CASES: dict[str, list[Case]] = {
    "init": [
        Case(("../fresh", "--prefix", "zz", "--yes")),
        Case(("../fresh", "--prefix", "zz", "--yes", "--dry-run"), unchanged=True),
        Case(("../shown", "--demo")),
        Case(("../imported", "--from", "../paper/paper.tex", "--yes"), paper),
        Case(("../imported", "--from", "../paper/paper.tex", "--dry-run"), paper, unchanged=True),
        Case((), exit=2, unchanged=True, why="the current directory is already a quilt"),
        Case(("../fresh", "--prefix", "z-z"), exit=2, json=False, unchanged=True, why="not an id prefix"),
        Case(("../fresh", "--from", "../absent.tex"), exit=2, unchanged=True, why="no such file"),
    ],
    "id": [
        Case(("--next",)),
        Case(("drafting/main.tex",), json=False, why="every node already has an id: nothing to label"),
        Case(("drafting/main.tex", "--to", "build/labelled.tex"), json=False),
        Case(
            ("drafting/main.tex", "--to", "nodes/labelled.tex"),
            exit=2,
            json=False,
            unchanged=True,
            why="among the sources",
        ),
        Case(("nodes/absent.tex",), exit=2, json=False, unchanged=True, why="no such file"),
        Case(("--next", "--prefix", "a-b"), exit=2, unchanged=True, why="not an id prefix"),
        Case((), exit=2, unchanged=True, why="neither a file nor --next"),
    ],
    "import": [
        Case(("../paper/paper.tex", "--yes"), paper),
        Case(("../paper/paper.tex", "--dry-run"), paper, unchanged=True),
        Case(("../paper/paper.tex",), paper, exit=2, unchanged=True, why="no terminal to confirm on, and no --yes"),
        Case(("absent.tex", "--yes"), exit=2, unchanged=True, why="no such file"),
    ],
    "atomize": [
        Case(("drafting/main.tex", "--to", "drafting/spine.tex")),
        Case(("drafting/main.tex", "--to", "drafting/spine.tex", "--dry-run"), unchanged=True),
        Case(("--key", "dm-0004")),
        Case(("--key", "dm-0004", "--dry-run"), unchanged=True),
        Case(("--key", "dm-9999"), exit=2, unchanged=True, why="an unknown key"),
        Case(("drafting/absent.tex", "--to", "drafting/spine.tex"), exit=2, unchanged=True, why="no such file"),
        Case(("drafting/main.tex",), exit=2, unchanged=True, why="no destination"),
    ],
    "deloom": [
        Case(("main.tex", "--to", "build/plain.tex", "--keep-referenced-ids", "--keep-incomplete")),
        Case(
            ("main.tex", "--to", "build/plain.tex", "--keep-referenced-ids", "--keep-incomplete", "--dry-run"),
            unchanged=True,
        ),
        Case(("main.tex", "--to", "build/plain.tex"), exit=1, unchanged=True, why="an \\incomplete blocks it"),
        Case(("main.tex", "--to", "drafting/plain.tex"), exit=2, unchanged=True, why="among the sources"),
        Case(("absent", "--to", "build/plain.tex"), exit=2, unchanged=True, why="no such document"),
    ],
    "draft": [
        Case(("drafting/main.tex", "--ai", "aidoc.tex")),
        Case(("drafting/main.tex", "--ai", "aidoc.tex", "--dry-run"), unchanged=True),
        Case(("drafting/absent.tex", "--ai", "aidoc.tex"), exit=2, unchanged=True, why="no such document"),
    ],
    "stamp": [
        Case(("--message", "m")),
        Case(("--message", "m", "--dry-run"), unchanged=True),
        Case(("drafting/main.tex", "--message", "m", "--dry-run"), unchanged=True),
        Case(("--message", "again"), stamped, why="nothing has changed since the last stamp: exit 0 all the same"),
        Case(("drafting/absent.tex", "--message", "m"), exit=2, unchanged=True, why="no such document"),
    ],
    "fork": [
        Case(("dm-0001", "--in", "drafting/main.tex")),
        Case(("dm-0001", "--in", "drafting/main.tex", "--dry-run"), unchanged=True),
        Case(("dm-9999", "--in", "drafting/main.tex"), exit=2, unchanged=True, why="an unknown key"),
        Case(("dm-0001", "--in", "drafting/absent.tex"), exit=2, unchanged=True, why="no such document"),
        Case(("dm-0001", "--in", "drafting/main.tex", "--from", "@99"), exit=2, unchanged=True, why="no such step"),
        Case(("dm-0001", "--in", "drafting/main.tex", "--from", "yesterday"), exit=2, unchanged=True, why="not a step"),
    ],
    "revert": [
        Case(("dm-0001@1",)),
        Case(("dm-0001@9",), exit=2, unchanged=True, why="a step the history does not have"),
        Case(("dm-9999@1",), exit=2, unchanged=True, why="an unknown key"),
        Case(("dm-0001",), exit=2, unchanged=True, why="not an address"),
    ],
    "live": [
        Case(("drafting/solo.tex",), superseded),
        Case(("drafting/solo.tex", "--dry-run"), superseded, unchanged=True),
        Case(("drafting/main.tex",), exit=2, unchanged=True, why="not superseded"),
        Case(("drafting/absent.tex",), exit=2, unchanged=True, why="no such file"),
    ],
    "mv": [
        Case(("drafting/outline.tex", "drafting/plan.tex")),
        Case(("drafting/outline.tex", "drafting/plan.tex", "--dry-run"), unchanged=True),
        Case(("drafting/absent.tex", "drafting/plan.tex"), exit=2, unchanged=True, why="neither path exists"),
    ],
    "linearize": [
        Case(("drafting/solo.tex", "--to", "drafting/flat.tex"), solo_spine),
        Case(("drafting/solo.tex", "--to", "drafting/flat.tex", "--dry-run"), solo_spine, unchanged=True),
        Case(("drafting/absent.tex", "--to", "drafting/flat.tex"), exit=2, unchanged=True, why="no such file"),
        Case(
            ("drafting/solo.tex", "--to", "build/flat.tex"),
            solo_spine,
            exit=2,
            unchanged=True,
            why="a working document goes in drafting/",
        ),
    ],
    "history": [
        Case(()),
        Case(("dm-0001",)),
        Case(("dm-9999",), exit=2, unchanged=True, why="an unknown key, read as KEY"),
    ],
    "history show": [
        Case(("widgets-v1",)),
        Case(("widgets-v1", "--plain")),
        Case(("absent",), exit=2, unchanged=True, why="no such landmark"),
    ],
    "history restore": [
        Case(("widgets-v1", "--to", "drafting/restored.tex")),
        Case(("absent", "--to", "drafting/restored.tex"), exit=2, unchanged=True, why="no such landmark"),
        Case(("widgets-v1",), exit=2, unchanged=True, why="no --to"),
        Case(("widgets-v1", "--to", "nodes/restored.tex"), exit=2, unchanged=True, why="not in drafting/"),
    ],
    "history verify": [Case(())],
    "adopt": [
        Case(("contribution",), ai_copy),
        Case(("contribution", "--to", "build/adopt.patch"), ai_copy),
        Case(("contribution", "--to", "drafting/adopt.tex"), ai_copy, exit=2, unchanged=True, why="among the sources"),
        Case(("absent",), exit=2, unchanged=True, why="no such agent document"),
        Case(
            ("contribution",), ai_copy, exit=2, env=(("AI_AGENT", "1"),), unchanged=True, why="adoption is the author's"
        ),
    ],
}
