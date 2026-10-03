"""Output cases for the core commands; see `tests/output_cases/__init__.py`."""

from __future__ import annotations

from pathlib import Path

from tests.output_cases.base import Case, author

FAIL_TEX = (("FAKE_TEX_FAIL", "1"),)


def duplicate_id(q: Path) -> None:
    """A second file defining `dm-0001`: an error diagnostic, which `lint`, `build` and `check` exit 1 on."""
    (q / "nodes" / "bad.tex").write_text("\\begin{lemma}\\label{dm-0001}\ndup\n\\end{lemma}\n", encoding="utf-8")


def stale(q: Path) -> None:
    """An accepted lemma whose dependency then changed, so its proof is stale."""
    from tests.helpers import edit, ok

    author(q)
    ok("accept", "dm-0002", "--proofs", "--force", cwd=q)
    edit(q / "nodes" / "dm-0001.tex", r"\sigma x = x", r"\sigma(x) = x")


KIND: dict[str, str] = {
    "accept": "report",
    "annotate": "report",
    "build": "report",
    "check": "report",
    "compile": "report",
    "deps": "report",
    "doctor": "report",
    "downstream": "report",
    "link": "raw",
    "lint": "report",
    "new": "report",
    "search": "report",
    "serve": "running",
    "source": "raw",
    "status": "report",
    "upgrade": "report",
}

NOWHERE = (("FAKE_TEX_FAIL_MATCH", "closures/"),)

CASES: dict[str, list[Case]] = {
    "accept": [
        Case(("dm-0001",), setup=author),
        Case(("dm-0002", "--proofs", "--force"), setup=author),
        Case(("--stale", "--yes"), setup=author, why="nothing is stale"),
        Case(("--stale", "--yes", "--force"), setup=stale),
        Case(("dm-9999", "--force"), setup=author, exit=2, unchanged=True, why="a key that names nothing"),
        Case(("dm-0001", "--dry-run"), setup=author, unchanged=True),
        Case(
            ("--all-live", "--dry-run", "--force"),
            setup=author,
            exit=1,
            unchanged=True,
            why="a dry run asks no confirmation, and still refuses an incomplete proof",
        ),
        Case(("dm-0001", "--as", "Referee (Agent)"), exit=2, unchanged=True, why="an agent does not accept"),
        Case(("--stale", "--force"), setup=stale, exit=2, why="confirmation, off a terminal, needs --yes"),
        Case(("--all-live", "--yes", "--force"), setup=author, exit=1, why="an incomplete proof is in scope"),
        Case(("dm-0002",), setup=author, env=FAIL_TEX, exit=1, why="its document does not compile"),
    ],
    "annotate": [
        Case(("dm-0002", "Which orbits?", "--as", "Tester")),
        Case(("dm-0002", "Which orbits?", "--kind", "objection", "--severity", "major", "--as", "Tester")),
        Case(("dm-9999", "Nothing here", "--as", "Tester"), exit=2, unchanged=True, why="a key that names nothing"),
        Case(
            ("--resolve", "a-2000-01-01-0001", "--as", "Tester"),
            exit=2,
            unchanged=True,
            why="an annotation that does not exist",
        ),
        Case(("dm-0002", "x", "--in", "nope.tex", "--as", "Tester"), exit=2, unchanged=True, why="no such document"),
        Case(("dm-0002", "x", "--session", "nope", "--as", "Tester"), exit=2, unchanged=True, why="no such session"),
        Case(("dm-0002", "Which orbits?", "--as", "Tester", "--dry-run"), unchanged=True),
        Case(("dm-0002", "x", "--quote", "not in the text", "--as", "Tester"), exit=1, why="a quote not in the text"),
    ],
    "build": [
        Case(),
        Case(("--keys", "dm-0001")),
        Case(("--keys", "dm-9999"), exit=2, unchanged=True, why="a key that names nothing"),
        Case((), setup=duplicate_id, exit=1, why="an error diagnostic; the build is still published"),
    ],
    "check": [
        Case(()),
        Case(("--closures", "all"), env=NOWHERE, exit=1, why="every closure fails"),
        Case((), setup=duplicate_id, exit=1, why="an error diagnostic"),
    ],
    "compile": [
        Case(()),
        Case(("dm-0003",)),
        Case(("drafting/outline.tex",)),
        Case((), env=FAIL_TEX, exit=1, why="the document does not compile"),
        Case(("dm-9999",), exit=2, unchanged=True, why="a key that names nothing"),
        Case(("dm-0003", "--session", "nope"), exit=2, unchanged=True, why="a session that names nothing"),
    ],
    "deps": [
        Case(("dm-0003",)),
        Case(("dm-0003", "--closure")),
        Case(("dm-0002/proof",)),
        Case(("dm-9999",), exit=2, unchanged=True, why="a key that names nothing"),
        Case(("dm-0003", "--session", "nope"), exit=2, unchanged=True, why="a session that names nothing"),
    ],
    "doctor": [
        Case((), setup=author),
        Case(("--strict",), exit=2, why="no author name, a warning, counts as a failure"),
    ],
    "downstream": [
        Case(("dm-0001",)),
        Case(("dm-0003",), why="annotations on the key and its proof"),
        Case(("dm-9999",), exit=2, unchanged=True, why="an id that names nothing"),
        Case(("dm-9999", "--session", "nope"), exit=2, unchanged=True, why="a session that names nothing"),
    ],
    "link": [
        Case(("dm-0001",)),
        Case(("Calloway14", "--page", "1")),
        Case(("nope",), exit=2, unchanged=True, why="a key that names nothing (CLI study G1)"),
    ],
    "lint": [
        Case(()),
        Case(("--nodes",)),
        Case((), setup=duplicate_id, exit=1, why="an error diagnostic"),
        Case(("--nodes",), setup=duplicate_id, exit=1, why="an id defined twice"),
    ],
    "new": [
        Case(("lemma", "A new lemma")),
        Case(("definition",)),
        Case(("lemma", "--dry-run"), unchanged=True),
        Case(("nonsense",), exit=2, unchanged=True, why="no such taxon"),
        Case(("lemma", "--prefix", "a-b"), exit=2, unchanged=True, why="not an id prefix"),
        Case(("lemma", "--session", "nope"), exit=2, unchanged=True, why="a session that names nothing"),
    ],
    "search": [
        Case(("widget",)),
        Case(("dm",), why="every node, ordered by number"),
        Case(("Theorem 3.4",), why="a number no document prints"),
        Case(("nothing-is-called-this",)),
        Case(("Theorem 1", "--in", "nope.tex"), exit=2, unchanged=True, why="a document that does not exist"),
    ],
    "source": [
        Case(("dm-0001",)),
        Case(("dm-0003", "--closure")),
        Case(("drafting/main.tex",)),
        Case(("dm-9999",), exit=2, unchanged=True, why="a key that names nothing"),
    ],
    "status": [
        Case(()),
        Case((), setup=stale, why="a stale proof leads"),
        Case(("--include-digests",)),
        Case(("--stale",), why="no rows match"),
        Case(("--explain", "dm-0003")),
        Case(("--explain", "dm-0002/proof"), setup=stale, why="a cause and its diff"),
        Case(("--reading",)),
        Case(("--runs",)),
        Case(("--retired",)),
        Case(("--undigested",)),
        Case(("--unmatched-cites",)),
        Case((), setup=duplicate_id, why="a conflicted id is listed, and status still exits 0"),
        Case(("--kind", "obj")),
        Case(("--master", "drafting/main.tex")),
        Case(("--tag", "orbits")),
        Case(("--explain", "dm-9999"), exit=2, unchanged=True, why="a key that names nothing"),
        Case(("--kind", "nonsense"), exit=2, unchanged=True, why="not an annotation's kind"),
        Case(("--master", "nope.tex"), exit=2, unchanged=True, why="not a document of the quilt"),
        Case(("--tag", "nope"), exit=2, unchanged=True, why="a tag no node carries"),
        Case(("--session", "nope"), exit=2, unchanged=True, why="a session that names nothing"),
    ],
    "upgrade": [Case(()), Case(("--dry-run",), unchanged=True)],
}
