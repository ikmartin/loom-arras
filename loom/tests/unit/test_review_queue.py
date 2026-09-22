"""Pending review choices do not bypass stale upstream mathematics."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from loom.cli.review import write_acceptance
from loom.records.store import Records
from loom.render.api import ApiError, handle
from loom.render.build import build
from loom.review_queue import decide
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
