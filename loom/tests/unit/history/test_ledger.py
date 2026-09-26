"""The history ledger and its steps (book 17.2-17.6): append-only lines, quilt-wide numbering, per-key versions, and what a malformed record does."""

from __future__ import annotations

import json
from pathlib import Path

from loom.history.ledger import append_entry, load_history
from loom.history.steps import infer_parent, slug, step_dirname
from loom.history.versions import parse_address, version_filename


def _write(tmp_path: Path, *lines: dict) -> Path:
    d = tmp_path / ".loom" / "history"
    d.mkdir(parents=True)
    (d / "ledger.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines), encoding="utf-8")
    return d


def test_empty_history_is_not_a_refusal(tmp_path: Path) -> None:
    h = load_history(tmp_path / ".loom" / "history")
    assert not h.exists and h.entries == [] and h.problems == []
    assert h.next_step() == 1 and h.latest_versions() == {} and h.recorded_ids() == set()


def test_steps_versions_and_addresses(tmp_path: Path) -> None:
    d = _write(
        tmp_path,
        {"when": "2026-09-13T09:00:00Z", "actor": "A", "action": "import", "step": 1, "dir": "0001-paper", "froze": {}},
        {
            "when": "2026-09-14T09:00:00Z",
            "actor": "A",
            "action": "canonize",
            "step": 2,
            "dir": "0002-paper-v1",
            "message": "First landmark",
            "froze": {"rl-0001": "sha256:a", "rl-0001/proof": "sha256:p"},
            "of": {"rl-0001/proof": "rl-0001@2"},
        },
        {"when": "2026-09-15T09:00:00Z", "actor": "A", "action": "draft", "from": {"path": "canon/paper.tex"}},
        {
            "when": "2026-09-16T09:00:00Z",
            "actor": "A",
            "action": "stamp",
            "step": 3,
            "dir": "0003-stamp-referee",
            "message": "Referee",
            "froze": {"rl-0001": "sha256:b"},
            "removed": ["rl-0002"],
        },
    )
    h = load_history(d)
    assert [e.step for e in h.steps()] == [1, 2, 3] and h.next_step() == 4
    assert h.resolve_step("2") is h.resolve_step("paper-v1") is h.resolve_step("0002-paper-v1")
    assert h.step(2).message == "First landmark" and h.step(3).name == "stamp-referee"
    assert h.latest_versions()["rl-0001"] == (3, "sha256:b")
    assert h.state_at(2)["rl-0001"] == (2, "sha256:a")
    assert [(v.step, v.hash, v.of) for v in h.versions_of("rl-0001")] == [(2, "sha256:a", None), (3, "sha256:b", None)]
    assert h.versions_of("rl-0001/proof")[0].of == "rl-0001@2"
    assert h.recorded_ids() == {"rl-0001", "rl-0002"}  # a removed id is recorded, and never allocated again
    assert h.removed_ids() == {"rl-0002": 3}
    assert h.entries[2].action == "draft" and h.entries[2].step is None  # not every line is a step


def test_a_malformed_line_is_reported_and_skipped(tmp_path: Path) -> None:
    d = tmp_path / ".loom" / "history"
    d.mkdir(parents=True)
    (d / "ledger.jsonl").write_text(
        json.dumps({"when": "x", "actor": None, "action": "canonize", "step": 2, "dir": "0002-a", "froze": {}})
        + "\nnot json\n"
        + json.dumps({"when": "x", "actor": None, "action": "canonize", "step": 1, "dir": "0001-b", "froze": {}})
        + "\n",
        encoding="utf-8",
    )
    h = load_history(d)
    assert [e.step for e in h.steps()] == [2]
    assert any("not JSON" in p for p in h.problems) and any("does not follow" in p for p in h.problems)


def test_append_is_a_line_and_the_cache_notices(tmp_path: Path) -> None:
    d = tmp_path / ".loom" / "history"
    assert load_history(d).entries == []
    e1 = append_entry(d, "live", {"path": "drafting/old.tex"}, "A")
    assert e1.line == 1 and load_history(d).entries[0].get("path") == "drafting/old.tex"
    e2 = append_entry(d, "live", {"path": "drafting/other.tex"}, None)
    assert e2.line == 2 and len(load_history(d).entries) == 2
    assert load_history(d).entries[1].actor is None  # a record of what loom was told never refuses for want of a name


def test_supersession_and_live(tmp_path: Path) -> None:
    d = _write(
        tmp_path,
        {"when": "1", "actor": None, "action": "atomize", "superseded": ["drafting/a.tex"], "to": ["drafting/b.tex"]},
        {"when": "2", "actor": None, "action": "linearize", "superseded": ["drafting/c.tex"], "to": "drafting/d.tex"},
        {"when": "3", "actor": None, "action": "live", "path": "drafting/a.tex"},
    )
    h = load_history(d)
    assert set(h.superseded_paths()) == {"drafting/c.tex"}


def test_parent_is_declared_inferred_or_unknown(tmp_path: Path) -> None:
    d = _write(
        tmp_path,
        {"when": "1", "actor": None, "action": "canonize", "step": 1, "dir": "0001-a", "froze": {"k": "h1", "j": "h2"}},
        {"when": "2", "actor": None, "action": "canonize", "step": 2, "dir": "0002-b", "froze": {"k": "h3"}},
    )
    h = load_history(d)
    assert infer_parent(h, {"k": "h3", "j": "h2"}, 1) == {"step": 1, "how": "declared"}
    assert infer_parent(h, {"k": "h3", "j": "h2"}, None)["step"] == 2  # the newest state sharing the most hashes
    assert infer_parent(h, {"k": "nope"}, None) == {"how": "unknown"}


def test_names_addresses_and_slugs() -> None:
    assert version_filename("rl-0001") == "rl-0001.tex"
    assert version_filename("rl-0001/proof") == "rl-0001.proof.tex"
    assert version_filename("rl-0001/proof/2") == "rl-0001.proof.2.tex"
    assert parse_address("rl-0001@3") == ("rl-0001", "3")
    assert parse_address("rl-0001/proof@paper-v2") == ("rl-0001/proof", "paper-v2")
    assert parse_address("rl-0001") is None
    assert slug("After the referee!") == "after-the-referee" and step_dirname(7, "paper-v2") == "0007-paper-v2"


def _moves(tmp_path: Path, *lines: dict) -> Path:
    """A ledger of conversions and moves, each line given its `when` and `actor`."""
    return _write(tmp_path, *({"when": str(i), "actor": None, **x} for i, x in enumerate(lines, start=1)))


def test_a_document_follows_a_chain_of_moves(tmp_path: Path) -> None:
    """atomize then linearize: the first path is wherever the last conversion put it, and a live path is itself."""
    d = _moves(
        tmp_path,
        {"action": "atomize", "from": ["drafting/a.tex"], "to": ["drafting/b.tex"], "superseded": ["drafting/a.tex"]},
        {"action": "linearize", "from": "drafting/b.tex", "to": "drafting/c.tex", "superseded": ["drafting/b.tex"]},
    )
    h = load_history(d)
    live = {"drafting/c.tex", "drafting/other.tex"}
    assert h.document_trail("drafting/a.tex", live) == ["drafting/a.tex", "drafting/b.tex", "drafting/c.tex"]
    assert h.current_document("drafting/a.tex", live) == "drafting/c.tex"
    assert h.current_document("drafting/b.tex", live) == "drafting/c.tex"
    assert h.current_document("drafting/other.tex", live) == "drafting/other.tex"
    # a live document is itself, even one a move once left: the walk stops at the first live path
    assert h.current_document("drafting/a.tex", live | {"drafting/a.tex"}) == "drafting/a.tex"


def test_live_makes_a_moved_path_its_own_again(tmp_path: Path) -> None:
    d = _moves(
        tmp_path,
        {"action": "linearize", "from": "drafting/a.tex", "to": "drafting/b.tex", "superseded": ["drafting/a.tex"]},
        {"action": "live", "path": "drafting/a.tex"},
    )
    h = load_history(d)
    assert h.successors() == {}
    assert h.current_document("drafting/a.tex", {"drafting/a.tex", "drafting/b.tex"}) == "drafting/a.tex"
    # made its own again and then gone: nothing leads anywhere
    assert h.current_document("drafting/a.tex", {"drafting/b.tex"}) is None


def test_a_path_nothing_moved_and_no_longer_live_is_gone(tmp_path: Path) -> None:
    d = _moves(
        tmp_path,
        {"action": "linearize", "from": "drafting/a.tex", "to": "drafting/b.tex", "superseded": ["drafting/a.tex"]},
    )
    h = load_history(d)
    assert h.current_document("drafting/x.tex", {"drafting/b.tex"}) is None
    assert h.document_trail("drafting/x.tex", {"drafting/b.tex"}) == ["drafting/x.tex"]
    # the chain ends at a document deleted by hand: gone, and the trail names where it was last
    assert h.current_document("drafting/a.tex", set()) is None
    assert h.document_trail("drafting/a.tex", set()) == ["drafting/a.tex", "drafting/b.tex"]


def test_a_retired_source_is_gone_and_its_atomized_spine_is_the_successor(tmp_path: Path) -> None:
    """atomize --retire moves the source to retired/; that copy is not a document, and the spine it wrote is where the document went."""
    d = _moves(
        tmp_path,
        {
            "action": "atomize",
            "from": ["drafting/a.tex", "drafting/b.tex"],
            "to": ["drafting/a2.tex", "drafting/b2.tex"],
            "superseded": [],
            "retired": ["retired/drafting/a.tex", "retired/drafting/b.tex"],
        },
    )
    h = load_history(d)
    live = {"drafting/a2.tex", "drafting/b2.tex"}
    assert h.successors() == {"drafting/a.tex": "drafting/a2.tex", "drafting/b.tex": "drafting/b2.tex"}
    assert h.current_document("drafting/b.tex", live) == "drafting/b2.tex"
    assert h.current_document("retired/drafting/a.tex", live) is None


def test_a_move_line_is_followed_the_latest_move_wins_and_a_cycle_ends(tmp_path: Path) -> None:
    d = _moves(
        tmp_path,
        {"action": "move", "from": "drafting/a.tex", "to": "drafting/b.tex"},
        {"action": "move", "from": "drafting/b.tex", "to": "drafting/a.tex"},
        {"action": "move", "from": "drafting/a.tex", "to": "drafting/c.tex"},
        # a landmark's `from` and `to` name a document and the canon copy it froze: not a move
        {
            "action": "canonize",
            "step": 1,
            "dir": "0001-v1",
            "from": {"path": "drafting/c.tex"},
            "to": {"path": "canon/v1.tex"},
        },
    )
    h = load_history(d)
    assert h.current_document("drafting/b.tex", {"drafting/c.tex"}) == "drafting/c.tex"
    assert h.current_document("drafting/c.tex", {"canon/v1.tex"}) is None
    # b -> a -> c, and with nothing live the walk stops rather than going round
    assert h.document_trail("drafting/b.tex", set()) == ["drafting/b.tex", "drafting/a.tex", "drafting/c.tex"]


def test_a_move_into_a_path_makes_it_that_document_s_own(tmp_path: Path) -> None:
    """`loom mv` into a path a conversion superseded or moved away from: the path is live again and no longer leads to where the old document went."""
    d = _moves(
        tmp_path,
        {"action": "linearize", "from": "drafting/a.tex", "to": "drafting/b.tex", "superseded": ["drafting/a.tex"]},
        {"action": "move", "from": "drafting/b.tex", "to": "drafting/a.tex", "moved": True},
    )
    h = load_history(d)
    assert h.superseded_paths() == {}
    assert h.successors() == {"drafting/b.tex": "drafting/a.tex"}
    assert h.current_document("drafting/b.tex", {"drafting/a.tex"}) == "drafting/a.tex"
    assert h.current_document("drafting/a.tex", {"drafting/a.tex"}) == "drafting/a.tex"
