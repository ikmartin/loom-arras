"""Review › Needs review: every block of the person's not freshly accepted is listed with why, and accepted from the viewer only as far as loom can accept it."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from loom.cli.review import write_acceptance
from loom.records.store import Records
from loom.render.api import ApiError, handle
from loom.render.build import build
from loom.review_queue import keep_pending
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan

REVIEWER = "The synthetic quilt"


@pytest.fixture(autouse=True)
def local_reviewer():
    from loom.scan.quilt import save_author

    save_author(REVIEWER)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    root = tmp_path / "quilt"
    shutil.copytree(
        Path(__file__).resolve().parents[1] / "quilts" / "synthetic",
        root,
        ignore=shutil.ignore_patterns("build", ".git"),
    )
    return root


@pytest.fixture
def compiles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("loom.cli.review._master_compiles", lambda _result, _master=None: (True, ""))


def _rows(root: Path) -> dict[str, dict]:
    return {row["key"]: row for row in build(load_quilt(root)).manifest["unresolved"]}


def _accept(root: Path, *keys: str) -> dict:
    return handle(root, "review-accept", {"reviewer": REVIEWER, "keys": list(keys)})


def _edit(root: Path) -> None:
    path = root / "drafting" / "main.tex"
    path.write_text(
        path.read_text(encoding="utf-8").replace("a pair of a set", "a pair consisting of a set"), encoding="utf-8"
    )


def test_every_unaccepted_block_of_the_persons_is_listed_with_why(root: Path) -> None:
    rows = _rows(root)
    manifest = build(load_quilt(root)).manifest
    stale = {k for k, e in manifest["keys"].items() if e.get("acceptance", {}).get("fresh") is False}
    never = {
        k
        for k, e in manifest["keys"].items()
        if "acceptance" not in e
        and e.get("kind") in ("statement", "proof")
        and not manifest["nodes"].get(e["node"], {}).get("external")
    }
    assert stale and {k for k, r in rows.items() if r["cause"] == "earlier-change"} == stale
    assert {k for k, r in rows.items() if r["cause"] == "never-accepted"} <= never
    assert "sy-0003" not in rows  # fresh
    assert not [k for k in rows if k.startswith("Kre99")]  # a digest's results are verified, not accepted
    assert "status" not in rows["sy-0001"] and "review_covered" not in manifest


def test_an_agent_copys_blocks_are_not_the_persons_to_accept(root: Path) -> None:
    quilt = load_quilt(root)
    result = scan(quilt)
    derived = [k for k, n in result.nodes.items() if n.derived_of]
    assert derived, "the synthetic quilt holds an agent's copy"
    rows = _rows(root)
    assert not [k for k in derived if k in rows]


def test_a_block_loom_cannot_accept_says_why(root: Path) -> None:
    rows = _rows(root)
    assert rows["sy-000B"]["refusal"] == "Its basis is not said; a % !LOOM basis: line inside it says it."
    assert rows["sy-000C/proof"]["refusal"].startswith("It is marked incomplete: Show that there are no fixed points")
    assert not rows["sy-000C/proof"]["refusal"].endswith("..")
    assert rows["sy-0001"]["refusal"] == ""


def test_accept_records_at_once_and_the_block_leaves_the_queue(root: Path, compiles: None) -> None:
    rows = _rows(root)
    assert rows["sy-0004"]["cause"] in ("earlier-change", "never-accepted")
    answer = _accept(root, "sy-0001")
    assert answer["accepted"] == ["sy-0001"] and answer["refused"] == []
    assert answer["result"] == "accepted 1 of 1"
    assert Records(root, load_quilt(root).history_dir).latest["sy-0001"].author == REVIEWER
    assert "sy-0001" not in _rows(root)


def test_a_selection_accepts_what_it_can_and_says_why_for_the_rest(root: Path, compiles: None) -> None:
    _rows(root)
    answer = _accept(root, "sy-0002", "sy-000B", "drafting/talk.tex#lemma:1")
    assert answer["accepted"] == ["drafting/talk.tex#lemma:1"]
    assert answer["refused"] == [
        {"key": "sy-0002", "why": "Accept Widget first, or with it."},
        {"key": "sy-000B", "why": "Its basis is not said; a % !LOOM basis: line inside it says it."},
    ]
    assert answer["result"] == "accepted 1 of 3"
    # accepted with what it rests on, it is accepted
    assert _accept(root, "sy-0001", "sy-0002")["accepted"] == ["sy-0001", "sy-0002"]


def test_nothing_accepted_is_an_answer_not_an_error(root: Path, compiles: None) -> None:
    _rows(root)
    answer = _accept(root, "sy-000E")
    assert answer["ok"] and answer["accepted"] == [] and answer["refused"][0]["key"] == "sy-000E"


def test_reaccepting_a_dependency_unchanged_clears_what_rests_on_it_through_it(root: Path, compiles: None) -> None:
    quilt = load_quilt(root)
    write_acceptance(scan(quilt), ["sy-0001", "sy-0002", "sy-0002/proof"], REVIEWER)
    proof = Records(root, quilt.history_dir).latest["sy-0002/proof"]
    _edit(root)
    manifest = build(quilt).manifest
    assert any(c.get("via") == "sy-0002" for c in manifest["keys"]["sy-0002/proof"]["acceptance"]["causes"])
    assert _accept(root, "sy-0001", "sy-0002")["accepted"] == ["sy-0001", "sy-0002"]
    after = build(quilt).manifest
    assert after["keys"]["sy-0002/proof"]["acceptance"]["fresh"] is True
    assert "sy-0002/proof" not in {r["key"] for r in after["unresolved"]}
    assert Records(root, quilt.history_dir).latest["sy-0002/proof"] == proof


def test_a_block_taken_in_and_left_unchecked_stays_though_its_acceptance_is_fresh(root: Path) -> None:
    quilt = load_quilt(root)
    write_acceptance(scan(quilt), ["sy-0001"], REVIEWER)
    assert "sy-0001" not in _rows(root)
    keep_pending(scan(quilt), ["sy-0001"], REVIEWER)
    assert "sy-0001" in _rows(root)


def test_accept_refuses_a_stale_page_an_agent_and_a_document_that_does_not_compile(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _rows(root)
    with pytest.raises(ApiError, match="sy-0003 is not awaiting review") as e:
        _accept(root, "sy-0003")
    assert (e.value.code, e.value.status) == ("not-unresolved", 409)
    with pytest.raises(ApiError, match="only the author accepts") as e:
        handle(root, "review-accept", {"reviewer": REVIEWER, "keys": ["sy-0001"], "author": "Referee (Agent)"})
    assert e.value.status == 403
    with pytest.raises(ApiError) as e:
        handle(root, "review-accept", {"reviewer": REVIEWER, "keys": []})
    assert e.value.code == "bad-field"
    monkeypatch.setattr(
        "loom.cli.review._master_compiles", lambda _result, _master=None: (False, "Undefined control sequence")
    )
    with pytest.raises(ApiError, match="does not compile: Undefined control sequence") as e:
        _accept(root, "sy-0001")
    assert e.value.code == "compile-failed"
    assert "sy-0001" in _rows(root)
