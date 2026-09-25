"""`loom search "Theorem 3.4"`: a result named as the reader sees it, resolved against each drafting document's numbering (0.14 study, F23)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers import json_of, ok, refused


@pytest.fixture
def q(tmp_path: Path) -> Path:
    ok("init", str(tmp_path / "q"), "--demo", cwd=tmp_path)
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
    return json_of("search", *args, "--json", cwd=q)


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
    refused("search", "1.3", "--in", "nowhere", code=2, match="names no drafting document", cwd=q)
    refused("search", "widget", "--in", "main", code=2, match="resolve a number", cwd=q)


def test_a_number_nothing_carries_says_so_and_words_are_still_words(q: Path) -> None:
    none = ok("search", "Theorem 9.9", cwd=q)
    assert "nothing is numbered Theorem 9.9" in none.output
    # a bare number nothing is numbered is looked for as text, as ever
    ok("search", "2026", cwd=q)
    assert [e["key"] for e in found(q, "Widget")][:1] == ["dm-0001"]
