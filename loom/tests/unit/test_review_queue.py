"""Pending review choices do not bypass stale upstream mathematics."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from loom.render.api import ApiError, handle
from loom.render.build import build
from loom.scan.quilt import load_quilt


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
