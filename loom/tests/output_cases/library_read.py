"""Output cases for the bare `library` report, `read`, `search`, `why`, `propose`, `locate` and `relate`; see `tests/output_cases/__init__.py`."""

from __future__ import annotations

from pathlib import Path

from tests.output_cases.base import Case

AS = ("--as", "Tester")
#: A quotation that is on the demo's p.1 of Calloway14.
QUOTED = "An involution of a topological space fixes a subspace"
PROPOSE = ("Calloway14", "--local", "rem-9.1", "--level", "1", "--page", "1", "--statement", "S")
RELATE = ("Calloway14-prop-3.2", "Calloway14-prop-3.3", "--kind", "depends-on", "--why", "w")


def proposed(q: Path) -> None:
    """A proposal, Calloway14-rem-9.1, waiting for review."""
    from tests.helpers import ok

    ok("library", "propose", *PROPOSE, "--source-text", QUOTED, cwd=q)


def related(q: Path) -> None:
    """One relation, link-0001, between two of Calloway14's results, asserted by a person."""
    from tests.helpers import ok

    ok("library", "relate", *RELATE, *AS, cwd=q)


def cited_all(q: Path) -> None:
    """The author's documents cite Har77 (no document, no identifier) and Man12 (an arXiv id, nothing fetched)."""
    node = q / "nodes" / "dm-0003.tex"
    node.write_text(node.read_text(encoding="utf-8") + "\nCompare \\cite{Har77} and \\cite{Man12}.\n", encoding="utf-8")


KIND: dict[str, str] = {
    "library": "report",
    "library locate": "raw",
    "library propose": "report",
    "library read": "raw",
    "library relate": "report",
    "library search": "report",
    "library why": "report",
}

CASES: dict[str, list[Case]] = {
    "library": [
        Case(),
        Case((), cited_all, why="cited works with no document: each under its cause, with the command that clears it"),
        Case((), proposed, why="a proposal waiting for review"),
        Case(("Calloway14",)),
        Case(("manolache",), why="a fragment of an author's name"),
        Case(("Calloway14-prop-3.2",), why="a result id names its work"),
        Case(("Nobody99xyz",), exit=2, unchanged=True, why="names no work"),
    ],
    "library read": [
        Case(("Calloway14", "1")),
        Case(("Calloway14", "1-2")),
        Case(("Calloway14",), why="the digest's Overview"),
        Case(("Calloway14", "--where", "dir")),
        Case(("Man12", "--where", "pdf"), exit=1, unchanged=True, why="nothing there yet"),
        Case(("Calloway14", "99"), exit=1, unchanged=True, why="past the end"),
        Case(("Calloway14", "x"), exit=2, unchanged=True, why="not a page"),
        Case(("Calloway14", "1", "--where", "pdf"), exit=2, unchanged=True, why="PAGES and --where"),
        Case(("Calloway14", "--where", "paper"), exit=2, unchanged=True, why="not a place"),
        Case(("Man12", "1"), exit=1, unchanged=True, why="no page text"),
        Case(("Man12",), exit=1, unchanged=True, why="no digest"),
        Case(("Nobody99",), exit=2, unchanged=True, why="names no work"),
    ],
    "library search": [
        Case(("involution",)),
        Case(("Involution FIXED",), why="every term, any case"),
        Case(("widget",), why="nothing matches: the page search is named"),
        Case(("fixed", "--pages")),
        Case(("involution", "--work", "Calloway14", "--limit", "1")),
        Case(("a\\|b",), exit=2, unchanged=True, why="a pattern, not words"),
        Case(("x", "--work", "Nobody99"), exit=2, unchanged=True, why="--work names no work"),
        Case(("x", "--limit", "0"), exit=2, unchanged=True, why="a limit below one"),
    ],
    "library why": [
        Case(("Calloway14-prop-3.2",)),
        Case(("Calloway14-setup",)),
        Case(("Calloway14-prop-3.2", "--depth", "2"), related, why="with a relation"),
        Case(("nope",), exit=2, unchanged=True, why="an unknown id"),
        Case(("a-2026-01-01-0001",), exit=2, unchanged=True, why="an unknown annotation"),
        Case(("Calloway14-prop-3.2", "--depth", "0"), exit=2, unchanged=True, why="a depth below one"),
    ],
    "library propose": [
        Case((*PROPOSE, "--source-text", QUOTED)),
        Case((*PROPOSE, "--source-text", QUOTED, "--dry-run"), unchanged=True),
        Case(
            (*PROPOSE, "--source-text", "words that are on no page"),
            exit=1,
            unchanged=True,
            why="the quotation is not on the page",
        ),
        Case(("Nobody99", *PROPOSE[1:], "--source-text", QUOTED), exit=2, unchanged=True, why="names no work"),
    ],
    "library locate": [
        Case(("Calloway14", "Fixed loci of involutions", "--page", "1"), poppler=True),
        Case(("Calloway14", "no such words anywhere", "--page", "1"), exit=1, poppler=True, why="not on the page"),
        Case(("Man12", "x", "--page", "1"), exit=1, unchanged=True, why="no mapped PDF"),
        Case(("Nobody99", "x", "--page", "1"), exit=2, unchanged=True, why="names no work"),
    ],
    "library relate": [
        Case((*RELATE, *AS)),
        Case((*RELATE, *AS, "--dry-run"), unchanged=True),
        Case(("nope", *RELATE[1:], *AS), exit=2, unchanged=True, why="an unknown result"),
        Case((*RELATE[:3], "rhymes-with", *RELATE[4:], *AS), exit=2, unchanged=True, why="an unknown kind"),
        Case(("--undo", "link-0001", "--why", "a misreading", *AS), related),
        Case(("--undo", "link-0001", "--why", "a misreading", *AS, "--dry-run"), related, unchanged=True),
        Case(("--undo", "link-0099", "--why", "w"), exit=2, unchanged=True, why="an unknown relation"),
        Case((*RELATE, "--undo", "link-0001"), related, exit=2, unchanged=True, why="FROM TO and --undo"),
        Case(("--why", "w"), exit=2, unchanged=True, why="neither FROM TO nor --undo"),
    ],
}
