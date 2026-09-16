"""Ledger, snapshots, and selectors as units (book 7.2, 7.5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from loom.records.ledger import AcceptRow, append_rows, latest_rows, read_ledger
from loom.records.selectors import Selector, find_quote, make_selector, resolve_selector
from loom.records.snapshots import read_snapshot, write_snapshot


def test_ledger_append_only_and_latest_row_wins(tmp_path: Path) -> None:
    r1 = AcceptRow(
        "rl-0004", "A", "2026-09-16T14:02:11Z", "sha256:1", "sha256:p", "drafts/main.tex", {"rl-0002": "sha256:2"}
    )
    append_rows(tmp_path, [r1])
    text = (tmp_path / ".loom" / "state.toml").read_text()
    assert text.startswith("# .loom/state.toml -- written by `loom accept`. Do not edit.\nschema = 1\n")
    assert '[[accept]]\nkey = "rl-0004"' in text and '[accept.closure]\n"rl-0002" = "sha256:2"' in text
    r2 = AcceptRow("rl-0004", "B", "2026-09-17T00:00:00Z", "sha256:9", "sha256:p", "drafts/main.tex", {})
    append_rows(tmp_path, [r2])
    rows = read_ledger(tmp_path)
    assert [r.author for r in rows] == ["A", "B"] and rows[0].closure == {"rl-0002": "sha256:2"}
    assert latest_rows(rows)["rl-0004"].text == "sha256:9"
    assert (tmp_path / ".loom" / "state.toml").read_text().count("[[accept]]") == 2


def test_snapshots_content_addressed_never_overwritten(tmp_path: Path) -> None:
    h1, w1 = write_snapshot(tmp_path, "a\n\n\n b  \n")
    h2, w2 = write_snapshot(tmp_path, "a\n\n b\n")
    assert h1 == h2 and w1 and not w2
    p = tmp_path / ".loom" / "snapshots" / (h1.split(":")[1] + ".tex")
    assert p.read_text() == "a\n\n b\n"
    p.write_text("tampered")
    write_snapshot(tmp_path, "a\n\n b\n")
    assert p.read_text() == "tampered"  # never overwritten
    assert read_snapshot(tmp_path, h1) == "tampered" and read_snapshot(tmp_path, "sha256:nope") is None


def test_selector_resolution_unique_by_context_and_detached() -> None:
    text = "Let x be open. Then the inclusion is open by rigidity, and the inclusion is open again."
    sel = make_selector(text, "be open")
    assert sel.exact == "be open" and sel.prefix == "Let x " and sel.suffix.startswith(". Then")
    with pytest.raises(ValueError):
        make_selector(text, "inclusion is open")
    assert resolve_selector(text, sel) == (text.index("be open"), text.index("be open") + 7)
    ambiguous = Selector("inclusion is open", "and the ", " again")
    span = resolve_selector(text, ambiguous)
    assert span is not None and text[span[0] :].startswith("inclusion is open again")
    assert resolve_selector(text, Selector("vanished text")) is None
    assert resolve_selector("a  b\nc", Selector("a b c")) == (0, 6)
    assert find_quote("x  y", "x y") == [(0, 4)]
