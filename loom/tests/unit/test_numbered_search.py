"""`loom search "Theorem 3.4"`: a result named as the reader sees it, resolved against each drafting document's numbering (0.14 study, F23)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from loom.cli import main


def run(*args: str, cwd: Path):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args))
    finally:
        os.chdir(old)


@pytest.fixture
def q(tmp_path: Path) -> Path:
    assert run("init", str(tmp_path / "q"), "--demo", cwd=tmp_path).exit_code == 0
    q = tmp_path / "q"
    # two compiles that number the same nodes differently: the paper, and an outline of it
    for stem, labels in (
        ("main", {"dm-0001": "1.1", "eq:fix": "1", "dm-0002": "1.2", "dm-0003": "1.3"}),
        ("outline", {"dm-0001": "1", "dm-0002": "1.3"}),
    ):
        (q / "build" / stem).mkdir(parents=True, exist_ok=True)
        aux = "".join(f"\\newlabel{{{k}}}{{{{{n}}}{{1}}}}\n" for k, n in labels.items())
        (q / "build" / stem / f"{stem}.aux").write_text(aux, encoding="utf-8")
    return q


def found(q: Path, *args: str) -> list[dict[str, object]]:
    r = run("search", *args, "--json", cwd=q)
    assert r.exit_code == 0, r.output
    return json.loads(r.output)


def test_a_number_names_what_every_document_numbers_so_the_default_first(q: Path) -> None:
    assert [(e["key"], e["document"], e["default"]) for e in found(q, "1.3")] == [
        ("dm-0003", "drafting/main.tex", True),
        ("dm-0002", "drafting/outline.tex", False),
    ]
    # the taxon narrows it, in any document
    assert [e["key"] for e in found(q, "Theorem 1.3")] == ["dm-0003"]
    assert [(e["key"], e["default"]) for e in found(q, "Lemma 1.3")] == [("dm-0002", False)]
    # an equation by its number in parentheses
    [eq] = found(q, "(1)")
    assert str(eq["key"]).startswith("dm-0001#") and eq["number"] == "(1)"


def test_in_asks_one_document(q: Path) -> None:
    assert [e["key"] for e in found(q, "1.3", "--in", "outline")] == ["dm-0002"]
    assert [e["key"] for e in found(q, "1.3", "--in", "drafting/main.tex")] == ["dm-0003"]
    bad = run("search", "1.3", "--in", "nowhere", cwd=q)
    assert bad.exit_code != 0 and "names no drafting document" in bad.output
    words = run("search", "widget", "--in", "main", cwd=q)
    assert words.exit_code != 0 and "resolve a number" in words.output


def test_a_number_nothing_carries_says_so_and_words_are_still_words(q: Path) -> None:
    none = run("search", "Theorem 9.9", cwd=q)
    assert none.exit_code == 0 and "nothing is numbered Theorem 9.9" in none.output
    # a bare number nothing is numbered is looked for as text, as ever
    assert run("search", "2026", cwd=q).exit_code == 0
    assert [e["key"] for e in found(q, "Widget")][:1] == ["dm-0001"]
