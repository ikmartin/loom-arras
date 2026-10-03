"""Output cases for the refs commands; see `tests/output_cases/__init__.py`.

Nothing here touches the network: `refs resolve` and `refs fetch` run where they have nothing to ask for, and refuse without consent.
"""

from __future__ import annotations

from pathlib import Path

from tests.output_cases.base import Case, ingest_pdf

AUTHOR = ("--author", "Tester")
#: A quotation that is on the demo's p.1 of Calloway14.
QUOTED = "An involution of a topological space fixes a subspace"
PROPOSE = ("Calloway14", "--local", "rem-9.1", "--level", "1", "--page", "1", "--statement", "S")


def tex_file(q: Path) -> None:
    """A LaTeX file to file as a work's source, and a text file that is neither PDF nor LaTeX."""
    (q / "man12.tex").write_text("\\documentclass{article}\n\\begin{document}\nX.\n\\end{document}\n", encoding="utf-8")
    (q / "notes.txt").write_text("notes\n", encoding="utf-8")


def man12_source(q: Path) -> None:
    """Man12 holds a source, so no cited work is left for a fetch to get."""
    from tests.unit._quilts import work_home

    src = work_home(q, "Man12") / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "main.tex").write_text("\\documentclass{article}\n", encoding="utf-8")


def proposed(q: Path) -> None:
    """A proposal, Calloway14-rem-9.1, waiting on the author."""
    from tests.helpers import ok

    ok("refs", "propose", *PROPOSE, "--source-text", QUOTED, cwd=q)


def linked(q: Path) -> None:
    """One link, link-0001, between two of Calloway14's results."""
    from tests.helpers import ok

    ok("refs", "link", *LINK, *AUTHOR, cwd=q)


LINK = ("--from", "Calloway14-prop-3.2", "--to", "Calloway14-prop-3.3", "--kind", "depends-on", "--why", "w")

KIND: dict[str, str] = {
    "refs add": "report",
    "refs build": "report",
    "refs cite": "report",
    "refs coverage": "report",
    "refs discard": "report",
    "refs drop": "report",
    "refs fetch": "report",
    "refs find": "report",
    "refs forget": "report",
    "refs grep": "report",
    "refs ingest": "report",
    "refs link": "report",
    "refs links": "report",
    "refs locate": "raw",
    "refs map": "report",
    "refs match": "report",
    "refs overview": "raw",
    "refs page": "raw",
    "refs path": "raw",
    "refs propose": "report",
    "refs recheck": "report",
    "refs resolve": "report",
    "refs scan": "report",
    "refs unlink": "report",
    "refs unreadable": "report",
    "refs verify": "report",
    "refs why": "report",
}

CASES: dict[str, list[Case]] = {
    "refs add": [
        Case(("Man12", "man12.tex"), tex_file),
        Case(("Man12", "notes.txt"), tex_file, exit=2, why="neither a PDF nor LaTeX"),
        Case(("Nobody99", "man12.tex"), tex_file, exit=2, why="an unknown citekey"),
    ],
    "refs build": [
        Case(),
        Case(("--only", "polish"), exit=2, why="an unknown step"),
        Case(("Nobody99",), exit=2, why="an unknown citekey"),
    ],
    "refs cite": [
        Case(("--list",)),
        Case((), exit=2, why="neither --accept nor --reject"),
        Case(("--accept", "a-nope", *AUTHOR), exit=2, why="an unknown annotation"),
    ],
    "refs coverage": [
        Case(),
        Case(("Calloway14",)),
        Case(("Nobody99xyz",), exit=2, why="names no work"),
    ],
    "refs discard": [
        Case(("Calloway14-rem-9.1", "--reason", "r", *AUTHOR), proposed),
        Case(("Calloway14-prop-3.2", "--reason", "r", *AUTHOR), exit=1, why="a verified result is not discarded"),
        Case(("nope", "--reason", "r", *AUTHOR), exit=2, why="an unknown id"),
    ],
    "refs drop": [
        Case(("--work", "Calloway14", "--yes")),
        Case(("--unverified", "--yes"), why="nothing to drop"),
        Case((), exit=2, why="none of --work, --session, --unverified"),
        Case(("--work", "Calloway14"), exit=2, why="no --yes and no terminal to ask"),
        Case(("--work", "Nobody99", "--yes"), exit=2, why="an unknown work"),
    ],
    "refs fetch": [
        Case(("--fetch",), man12_source, why="offline: nothing is left to fetch"),
        Case((), exit=2, why="fetching is off"),
        Case(("Nobody99", "--fetch"), exit=2, why="an unknown citekey"),
    ],
    "refs find": [Case(("widget",)), Case(("involution",))],
    "refs forget": [
        Case(("Calloway14", "--why", "w", *AUTHOR)),
        Case(("Calloway14", *AUTHOR), exit=2, why="no --why"),
        Case(("zzz", "--why", "w", *AUTHOR), exit=2, why="neither a citekey nor a hash"),
    ],
    "refs grep": [
        Case(("involution",)),
        Case(("widget",)),
        Case(("a\\|b",), exit=2, why="a pattern, not a phrase"),
    ],
    "refs ingest": [
        Case(("refs",), ingest_pdf, poppler=True),
        Case(("refs", "--dry-run"), ingest_pdf, poppler=True),
        Case(("drafting",), exit=2, why="no PDFs there"),
    ],
    "refs link": [
        Case((*LINK, *AUTHOR)),
        Case(("--from", "nope", *LINK[2:], *AUTHOR), exit=2, why="an unknown result"),
        Case((*LINK[:4], "--kind", "rhymes-with", *LINK[6:], *AUTHOR), exit=2, why="an unknown kind"),
    ],
    "refs links": [Case(), Case(("Calloway14-prop-3.2",), linked)],
    "refs locate": [
        Case(("Calloway14", "Fixed loci of involutions", "--page", "1"), poppler=True),
        Case(("Calloway14", "no such words anywhere", "--page", "1"), exit=1, poppler=True, why="not on the page"),
        Case(("Man12", "x", "--page", "1"), exit=1, why="no mapped PDF"),
        Case(("Nobody99", "x", "--page", "1"), exit=2, why="an unknown citekey"),
    ],
    "refs map": [Case(), Case(("Nobody99",), exit=2, why="an unknown citekey")],
    "refs match": [Case()],
    "refs overview": [
        Case(("Calloway14",)),
        Case(("Man12",), exit=1, why="no digest"),
        Case(("Nobody99xyz",), exit=2, why="names no work"),
    ],
    "refs page": [
        Case(("Calloway14", "1")),
        Case(("Calloway14", "99"), exit=1, why="past the end"),
        Case(("Calloway14", "x"), exit=2, why="not a page"),
        Case(("Man12", "1"), exit=1, why="no page text"),
    ],
    "refs path": [
        Case(("Calloway14",)),
        Case(("Man12", "--pdf"), exit=1, why="nothing there yet"),
        Case(("Nobody99",), exit=2, why="an unknown citekey"),
    ],
    "refs propose": [
        Case((*PROPOSE, "--source-text", QUOTED)),
        Case((*PROPOSE, "--source-text", "words that are on no page"), exit=1, why="the quotation is not on the page"),
        Case(("Nobody99", *PROPOSE[1:], "--source-text", QUOTED), exit=2, why="an unknown citekey"),
    ],
    "refs recheck": [Case()],
    "refs resolve": [
        Case(("--resolve",), why="offline: every cited work states an identifier"),
        Case((), exit=2, why="looking up is off"),
        Case(("Nobody99", "--resolve"), exit=2, why="an unknown citekey"),
    ],
    "refs scan": [Case(), Case(("--dry-run",))],
    "refs unlink": [
        Case(("link-0001",), linked),
        Case(("link-0099",), exit=2, why="an unknown link"),
    ],
    "refs unreadable": [
        Case(("Man12", "--why", "no fixed version", *AUTHOR)),
        Case(("Man12", *AUTHOR), exit=2, why="no --why"),
        Case(("Nobody99", "--why", "w", *AUTHOR), exit=2, why="an unknown citekey"),
    ],
    "refs verify": [
        Case(("Calloway14-rem-9.1", "--yes", *AUTHOR), proposed),
        Case(("Calloway14-prop-3.2", "--yes", *AUTHOR), why="re-verifying a mechanical result"),
        Case(("Calloway14-prop-3.2", *AUTHOR), exit=2, why="no --yes and no terminal to ask"),
        Case(("nope", "--yes", *AUTHOR), exit=2, why="an unknown id"),
    ],
    "refs why": [
        Case(("Calloway14-prop-3.2",)),
        Case(("Calloway14-setup",)),
        Case(("nope",), exit=2, why="an unknown id"),
    ],
}
