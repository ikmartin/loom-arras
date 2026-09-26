"""Acceptance history and pending work belong to a reviewer, even in one shared quilt."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from loom.cli.review import write_acceptance
from loom.records.ledger import read_ledger
from loom.records.store import Records
from loom.render.api import ApiError, handle
from loom.render.build import build
from loom.review_queue import clear_accepted, decide, pending
from loom.scan.quilt import load_quilt, resolve_author, save_author, user_config_path
from loom.scan.scan import scan
from tests.helpers import ok


@pytest.fixture
def quilt(tmp_path: Path):
    root = tmp_path / "quilt"
    shutil.copytree(Path(__file__).resolve().parents[1] / "quilts/synthetic", root)
    (root / ".loom/state.toml").unlink()
    return load_quilt(root)


def edit(quilt):
    path = quilt.root / "drafting/main.tex"
    path.write_text(path.read_text().replace("a pair of a set", "a pair consisting of a set"))


def test_other_acceptance_never_replaces_personal_snapshot_or_clears_queue(quilt):
    save_author("Bob")
    result = scan(quilt)
    write_acceptance(result, ["sy-0001", "sy-0002", "sy-0002/proof"], "Bob")
    before = Records(quilt.root).latest["sy-0001"]
    edit(quilt)
    stale = build(quilt).manifest
    decide(scan(quilt), "sy-0001", "ok")
    observations = (quilt.root / ".loom/review-observations.json").read_bytes()
    write_acceptance(scan(quilt), ["sy-0001", "sy-0002"], "Alice")
    after = build(quilt).manifest
    assert after["keys"]["sy-0001"]["acceptance"] == stale["keys"]["sy-0001"]["acceptance"]
    assert Records(quilt.root).latest["sy-0001"] == before
    assert pending(scan(quilt)) == ["sy-0001"]
    assert (quilt.root / ".loom/review-observations.json").read_bytes() == observations
    assert {a["author"]: a["fresh"] for a in after["keys"]["sy-0001"]["acceptances"]} == {"Alice": True, "Bob": False}
    assert any(c.get("via") == "sy-0002" for c in after["keys"]["sy-0002/proof"]["acceptance"]["causes"])
    assert not after["nodes"]["sy-0002"]["derived"]["settled"]
    save_author("Carol")
    never = build(quilt).manifest
    assert never["keys"]["sy-0001"]["state"] == "draft"
    assert never["unresolved"] == []
    assert not never["nodes"]["sy-0002"]["derived"]["proved"]


def test_finish_is_personal_and_switch_refuses_old_tab(quilt, monkeypatch):
    save_author("Bob")
    write_acceptance(scan(quilt), ["sy-0001"], "Bob")
    edit(quilt)
    build(quilt)
    handle(quilt.root, "review-decision", {"key": "sy-0001", "status": "ok", "reviewer": "Bob"})
    write_acceptance(scan(quilt), ["sy-0001"], "Alice")
    decide(scan(quilt), "sy-0001", "ok", "Alice")
    monkeypatch.setattr("loom.cli.review._master_compiles", lambda *_: (True, ""))
    save_author("Alice")
    before = read_ledger(quilt.root)
    with pytest.raises(ApiError, match="Reviewer changed"):
        handle(quilt.root, "review-finish", {"reviewer": "Bob"})
    assert read_ledger(quilt.root) == before
    assert "already accepted" in handle(quilt.root, "review-finish", {"reviewer": "Alice"})["result"]
    assert pending(scan(quilt), "Bob") == ["sy-0001"]
    save_author("Bob")
    assert handle(quilt.root, "review-finish", {"reviewer": "Bob"})["result"] == "accepted 1 keys"
    assert pending(scan(quilt), "Bob") == []
    assert Records(quilt.root).latest["sy-0001"].author == "Bob"
    assert Records(quilt.root, reviewer="Alice").latest["sy-0001"].author == "Alice"


def test_local_identity_settings_and_missing_identity(quilt):
    with (quilt.root / "config.toml").open("a") as out:
        out.write('\n[author]\nname = "Alice"\n')
    assert build(quilt).manifest["reviewer"]["name"] == ""
    with pytest.raises(ApiError, match="Choose your reviewer"):
        handle(quilt.root, "review-finish", {"reviewer": "Alice"})
    config = user_config_path()
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        '# keep me\n[refs]\nfetch = true\n[author]\nname = "Old"\nextra = "kept"\n[quilt]\nengine = "xelatex"\n'
    )
    handle(quilt.root, "reviewer-settings", {"name": "  Bob  "})
    assert resolve_author(None, quilt.root)[0] == "Bob"
    assert resolve_author("Carol", quilt.root)[0] == "Carol"
    assert "# keep me" in config.read_text() and 'extra = "kept"' in config.read_text()
    before = config.read_bytes()
    with pytest.raises(ApiError):
        handle(quilt.root, "reviewer-settings", {"name": "\n"})
    assert config.read_bytes() == before


def test_legacy_choices_are_preserved_not_adopted_and_caches_are_partitioned(quilt):
    save_author("Bob")
    write_acceptance(scan(quilt), ["sy-0001"], "Bob")
    write_acceptance(scan(quilt), ["sy-0001"], "Alice")
    decide(scan(quilt), "sy-0001", "ok")
    decisions = quilt.root / ".loom/review-decisions.json"
    legacy = json.loads(decisions.read_text())["reviewers"]["Bob"]
    decisions.write_text(json.dumps(legacy))
    assert pending(scan(quilt)) == []
    edit(quilt)
    bob = build(quilt).manifest
    assert bob["legacy_review_decisions"]
    assert bob["unresolved"][0]["status"] == "needs-review"
    cache = quilt.root / ".loom/review-observations.json"
    first = json.loads(cache.read_text())["reviewers"]["Bob"]
    save_author("Alice")
    build(quilt)
    assert json.loads(cache.read_text())["reviewers"]["Bob"] == first
    decide(scan(quilt), "sy-0001", "ok")
    clear_accepted(quilt.root, ["sy-0001"])
    assert json.loads(decisions.read_text())["legacy"] == legacy


def test_cli_override_selects_its_own_stale_rows_without_changing_settings(quilt, monkeypatch):
    save_author("Bob")
    write_acceptance(scan(quilt), ["sy-0001"], "Alice")
    edit(quilt)
    monkeypatch.setattr("loom.cli.review._master_compiles", lambda *_: (True, ""))
    ok("accept", "--stale", "--yes", "--author", "Alice", cwd=quilt.root)
    assert Records(quilt.root, reviewer="Alice").key_states(scan(quilt))["sy-0001"].fresh
    assert "sy-0001" not in Records(quilt.root).latest
    assert resolve_author(None, quilt.root)[0] == "Bob"


def test_external_transcription_verification_remains_shared(quilt):
    result = scan(quilt)
    external = next(
        key
        for key, node in result.nodes.items()
        if node.external and node.kind == "environment" and not node.file.endswith(".proposed.tex")
    )
    write_acceptance(result, [external], "Alice")
    save_author("Bob")
    state = Records(quilt.root).key_states(result)[external]
    assert state.row.author == "Alice" and state.fresh
