"""Output cases for `library verify`, `discard`, `ignore`, `review`, `check`, `import` and `drop`; see `tests/output_cases/__init__.py`."""

from __future__ import annotations

from pathlib import Path

from tests.output_cases.base import Case

AS = ("--as", "Tester")
#: A quotation that is on the demo's p.1 of Calloway14.
QUOTED = "An involution of a topological space fixes a subspace"
#: The id `suggested` gives its citation suggestion, the clock being fixed.
SUGGESTION = "a-2026-01-02-0001"


def proposed(q: Path) -> None:
    """A proposal, Calloway14-rem-9.1, waiting on the author."""
    from tests.unit._quilts import propose

    propose(q, "Calloway14", "rem-9.1", 1, QUOTED, "S")


def suggested(q: Path) -> None:
    """An open citation suggestion on dm-0002, `SUGGESTION`, naming a work in its payload."""
    from tests.helpers import ok

    ok(
        "annotate", "dm-0002", "Cite Kreck rather than reproving it.", "--kind", "citation",
        "--payload", "M. Kreck, Surgery and duality, Ann. of Math. 149 (1999)", "--as", "Referee Agent",
        cwd=q, env={"LOOM_FIXED_TIME": "2026-01-02T00:00:00Z"},
    )  # fmt: skip


def both(q: Path) -> None:
    proposed(q)
    suggested(q)


def a_digest(q: Path) -> None:
    """A digest from another quilt to import: the demo's own Calloway14, copied outside the quilt."""
    (q.parent / "elsewhere.tex").write_text((q / "digests" / "Calloway14.tex").read_text(encoding="utf-8"))


ELSEWHERE = "../elsewhere.tex"

KIND: dict[str, str] = {
    "library check": "report",
    "library discard": "report",
    "library drop": "report",
    "library ignore": "report",
    "library import": "report",
    "library review": "report",
    "library verify": "report",
}

CASES: dict[str, list[Case]] = {
    "library verify": [
        Case(("Calloway14-rem-9.1", "--yes", *AS), proposed),
        Case(("Calloway14-prop-3.2", "--yes", *AS), why="verifying an extracted result"),
        Case((SUGGESTION, *AS), suggested, why="accepting a citation suggestion"),
        Case(("Calloway14-rem-9.1", SUGGESTION, "--yes", *AS), both, why="a result and a suggestion at once"),
        Case(("Calloway14-rem-9.1", "--dry-run", *AS), proposed, unchanged=True),
        Case(("Calloway14-prop-3.2", *AS), exit=2, unchanged=True, why="no --yes and no terminal to ask"),
        Case(
            ("Calloway14-rem-9.1", "Calloway14-prop-3.2", "--statement", "S", "--yes", *AS),
            proposed,
            exit=2,
            unchanged=True,
            why="--statement with two ids",
        ),
        Case(("nope", "--yes", *AS), exit=2, unchanged=True, why="an unknown id"),
        Case(("a-1999-01-01-0001", *AS), exit=2, unchanged=True, why="an unknown annotation"),
        Case(
            ("Calloway14-rem-9.1", "--yes", *AS),
            proposed,
            exit=2,
            unchanged=True,
            env=(("AI_AGENT", "1"),),
            why="the author's, refused under an agent",
        ),
    ],
    "library discard": [
        Case(("Calloway14-rem-9.1", "--why", "r", *AS), proposed),
        Case((SUGGESTION, "--why", "already cited", *AS), suggested, why="rejecting a citation suggestion"),
        Case(("Calloway14-rem-9.1", "--why", "r", "--dry-run", *AS), proposed, unchanged=True),
        Case(("Calloway14-prop-3.2", "--why", "r", *AS), exit=1, unchanged=True, why="an extracted result stays"),
        Case(("Calloway14-rem-9.1", *AS), proposed, exit=2, unchanged=True, why="no --why"),
        Case(("nope", "--why", "r", *AS), exit=2, unchanged=True, why="an unknown id"),
    ],
    "library ignore": [
        Case(("Man12", "--why", "no fixed version", *AS), why="no document: declared unreadable"),
        Case(("Calloway14", "--why", "not wanted", *AS), why="a stored document: set aside"),
        Case(("Man12", "--why", "w", "--dry-run", *AS), unchanged=True),
        Case(("Man12", "--why", "w", "--undo", *AS), exit=1, unchanged=True, why="nothing stands to undo"),
        Case(("Man12", *AS), exit=2, unchanged=True, why="no --why"),
        Case(("Nobody99xyz", "--why", "w", *AS), exit=2, unchanged=True, why="names no work"),
    ],
    "library review": [
        Case(),
        Case((), both, why="a proposal and a suggestion waiting"),
        Case(("Calloway14",), proposed),
        Case(("Nobody99xyz",), exit=2, unchanged=True, why="names no work"),
    ],
    "library check": [
        Case(unchanged=True),
        Case(("Calloway14",), unchanged=True),
        Case(("Nobody99xyz",), exit=2, unchanged=True, why="names no work"),
    ],
    "library import": [
        Case((ELSEWHERE, "--name", "Other20"), a_digest),
        Case((ELSEWHERE, "--name", "Other20", "--dry-run"), a_digest, unchanged=True),
        Case((ELSEWHERE,), a_digest, exit=2, unchanged=True, why="a digest of that name is already here"),
        Case(("nowhere.tex",), exit=2, unchanged=True, why="no such file"),
    ],
    "library drop": [
        Case(("--work", "Calloway14", "--yes")),
        Case(("--work", "Calloway14", "--dry-run"), unchanged=True),
        Case(("--proposed", "--yes"), unchanged=True, why="nothing to drop: extracted results are not proposals"),
        Case((), exit=2, unchanged=True, why="none of --work, --session, --proposed"),
        Case(("--work", "Calloway14"), exit=2, unchanged=True, why="no --yes and no terminal to ask"),
        Case(("--work", "Nobody99xyz", "--yes"), exit=2, unchanged=True, why="an unknown work"),
        Case(("--session", "s-1999-01-01-0001", "--yes"), exit=2, unchanged=True, why="an unknown session"),
    ],
}
