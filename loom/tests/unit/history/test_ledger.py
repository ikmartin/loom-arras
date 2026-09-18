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
