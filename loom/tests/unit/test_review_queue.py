"""Pending review choices do not bypass stale upstream mathematics."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from loom.cli.review import write_acceptance
from loom.records.store import Records
from loom.render.api import ApiError, handle
from loom.render.build import build
from loom.review_queue import decide, pending
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan


def test_pending_ok_survives_build_and_waits_for_upstream(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[1] / "quilts" / "synthetic"
    root = tmp_path / "quilt"
    shutil.copytree(source, root, ignore=shutil.ignore_patterns("build", ".git"))
    build(load_quilt(root))
    assert handle(root, "review-decision", {"key": "sy-0002", "status": "ok"})["ok"]
    row = next(row for row in build(load_quilt(root)).manifest["unresolved"] if row["key"] == "sy-0002")
    assert row["status"] == "ok"
    with pytest.raises(ApiError, match="review sy-0001 before finishing sy-0002"):
        handle(root, "review-finish", {})


def test_requires_attention_returns_to_queue_when_block_changes(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[1] / "quilts" / "synthetic"
    root = tmp_path / "quilt"
    shutil.copytree(source, root, ignore=shutil.ignore_patterns("build", ".git"))
    result = scan(load_quilt(root))
    decide(result, "sy-0001", "requires-attention")
    row = next(row for row in build(load_quilt(root)).manifest["unresolved"] if row["key"] == "sy-0001")
    assert row["status"] == "requires-attention"

    path = root / "drafting" / "main.tex"
    path.write_text(
        path.read_text(encoding="utf-8").replace("a pair of a set", "a pair consisting of a set"), encoding="utf-8"
    )
    changed = next(row for row in build(load_quilt(root)).manifest["unresolved"] if row["key"] == "sy-0001")
    assert changed["status"] == "needs-review"
    assert changed["invalidated"] is True


def test_transitive_attention_clears_after_upstream_ok_is_finished(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = Path(__file__).resolve().parents[1] / "quilts" / "synthetic"
    root = tmp_path / "quilt"
    shutil.copytree(source, root, ignore=shutil.ignore_patterns("build", ".git"))
    quilt = load_quilt(root)
    write_acceptance(scan(quilt), ["sy-0001", "sy-0002", "sy-0002/proof"], "Test author")
    proof_acceptance = Records(root, quilt.history_dir).latest["sy-0002/proof"]

    path = root / "drafting" / "main.tex"
    path.write_text(
        path.read_text(encoding="utf-8").replace("a pair of a set", "a pair consisting of a set"), encoding="utf-8"
    )
    manifest = build(quilt).manifest
    assert manifest["keys"]["sy-0002/proof"]["acceptance"]["fresh"] is False
    assert any(c.get("via") == "sy-0002" for c in manifest["keys"]["sy-0002/proof"]["acceptance"]["causes"])
    assert handle(root, "review-decision", {"key": "sy-0002/proof", "status": "requires-attention"})["ok"]
    for key in ("sy-0001", "sy-0002"):
        assert handle(root, "review-decision", {"key": key, "status": "ok"})["ok"]
    covered = build(quilt).manifest
    assert covered["keys"]["sy-0002/proof"]["acceptance"]["fresh"] is False
    assert not any(row["key"] == "sy-0002/proof" for row in covered["unresolved"])
    assert {row["key"] for row in covered["unresolved"] if row["status"] == "ok"} == {"sy-0001", "sy-0002"}

    node_path = root / "nodes" / "sy-0002.tex"
    original_node = node_path.read_text(encoding="utf-8")
    node_path.write_text(original_node.replace("Every orbit", "Each orbit"), encoding="utf-8")
    invalidated = build(quilt).manifest["unresolved"]
    assert any(row["key"] == "sy-0002" and row["status"] == "needs-review" for row in invalidated)
    assert any(row["key"] == "sy-0002/proof" and row["status"] == "needs-review" for row in invalidated)
    node_path.write_text(original_node, encoding="utf-8")

    monkeypatch.setattr("loom.cli.review._master_compiles", lambda _result: (True, ""))
    monkeypatch.setattr("loom.cli.review._author", lambda _explicit, _root: "Test author")
    assert handle(root, "review-finish", {})["ok"]
    after = build(quilt).manifest
    assert after["keys"]["sy-0002/proof"]["acceptance"]["fresh"] is True
    assert not any(row["key"] == "sy-0002/proof" for row in after["unresolved"])
    assert Records(root, quilt.history_dir).latest["sy-0002/proof"] == proof_acceptance


def test_fresh_pending_ok_remains_visible_until_finish(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[1] / "quilts" / "synthetic"
    root = tmp_path / "quilt"
    shutil.copytree(source, root, ignore=shutil.ignore_patterns("build", ".git"))
    quilt = load_quilt(root)
    write_acceptance(scan(quilt), ["sy-0001"], "Test author")
    decide(scan(quilt), "sy-0001", "ok")
    row = next(row for row in build(quilt).manifest["unresolved"] if row["key"] == "sy-0001")
    assert row["status"] == "ok"


def _synthetic(tmp_path: Path) -> Path:
    root = tmp_path / "quilt"
    shutil.copytree(
        Path(__file__).resolve().parents[1] / "quilts" / "synthetic",
        root,
        ignore=shutil.ignore_patterns("build", ".git"),
    )
    return root


def test_a_decision_is_refused_for_a_bad_status_or_a_key_that_is_not_reviewable(tmp_path: Path) -> None:
    root = _synthetic(tmp_path)
    result = scan(load_quilt(root))
    with pytest.raises(ValueError, match="decision must be ok or requires-attention"):
        decide(result, "sy-0002", "fine")
    for key in ("sy-0200", "sy-9999"):  # a section, and no key at all
        with pytest.raises(ValueError, match=f"{key} is not a reviewable statement or proof"):
            decide(result, key, "ok")
    assert pending(result) == []  # nothing refused was written
    build(load_quilt(root))
    with pytest.raises(ApiError, match="sy-0200 is not awaiting review") as e:
        handle(root, "review-decision", {"key": "sy-0200", "status": "ok"})
    assert (e.value.code, e.value.status) == ("not-unresolved", 409)


def test_an_ok_whose_block_changed_is_refused_at_finish_until_it_is_decided_again(tmp_path: Path) -> None:
    """An OK is a decision about one text: finishing after the block was edited is refused, and nothing is accepted."""
    root = _synthetic(tmp_path)
    build(load_quilt(root))
    before = Records(root, load_quilt(root).history_dir).latest.get("sy-0001")
    assert handle(root, "review-decision", {"key": "sy-0001", "status": "ok"})["ok"]
    assert pending(scan(load_quilt(root))) == ["sy-0001"]
    path = root / "drafting" / "main.tex"
    path.write_text(
        path.read_text(encoding="utf-8").replace("a pair of a set", "a pair consisting of a set"), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="sy-0001 changed since OK; review it again"):
        pending(scan(load_quilt(root)))
    with pytest.raises(ApiError, match="sy-0001 changed since OK") as e:
        handle(root, "review-finish", {})
    assert e.value.code == "review-changed"
    assert Records(root, load_quilt(root).history_dir).latest.get("sy-0001") == before
    decide(scan(load_quilt(root)), "sy-0001", "ok")  # decided again, on the new text
    assert pending(scan(load_quilt(root))) == ["sy-0001"]


def test_requires_attention_can_be_reopened_as_ok_and_clear_accepted_forgets_only_what_it_names(tmp_path: Path) -> None:
    """Book 7.6.2: a block marked as requiring attention may later be marked OK; finishing clears the decisions it accepted and no others."""
    from loom.review_queue import _read, clear_accepted

    root = _synthetic(tmp_path)
    result = scan(load_quilt(root))
    decide(result, "sy-0001", "requires-attention")
    decide(result, "sy-0002", "requires-attention")
    assert pending(result) == []
    decide(result, "sy-0001", "ok")
    assert pending(result) == ["sy-0001"]
    clear_accepted(root, ["sy-0001"])
    assert {k: v["status"] for k, v in _read(root).items()} == {"sy-0002": "requires-attention"}
