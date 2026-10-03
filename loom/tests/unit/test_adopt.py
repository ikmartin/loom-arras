"""AI contributions preserve author choices, require the exact inspected revision, and need no git repository."""

from pathlib import Path

import pytest

from loom.adopt import comparison, incorporate, prepare
from loom.history.ledger import load_history
from loom.history.steps import write_step
from loom.reshape.copy import plan_copy
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan
from loom.sync import SyncError

DOC = "drafting/main.tex"
COPY = "drafting-ai/proposal.tex"
TEXT = r"""\documentclass{article}
\newtheorem{lemma}{Lemma}
\begin{document}
Original introduction.
\begin{lemma}\label{zk-0001}
First statement.
\end{lemma}
\begin{lemma}\label{zk-0002}
Second statement uses \ref{zk-0001}.
\end{lemma}
\end{document}
"""


@pytest.fixture
def quilt(tmp_path: Path):
    from loom.scan.quilt import save_author

    save_author("Tester")
    (tmp_path / "drafting").mkdir()
    (tmp_path / "drafting-ai").mkdir()
    (tmp_path / "config.toml").write_text('[quilt]\nname="test"\nprefix="zk"\nmain="drafting/main.tex"\n')
    (tmp_path / DOC).write_text(TEXT)
    q = load_quilt(tmp_path)
    result = scan(q)
    history = load_history(q.history_dir)
    cp = plan_copy(result, history, DOC, COPY)
    (tmp_path / COPY).write_text(cp.text)
    write_step(
        history,
        "copy",
        "copy-proposal",
        cp.freeze,
        "Tester",
        {"from": DOC, "to": COPY, "bases": cp.bases},
        cp.source_text,
        "main.tex",
    )
    return q


def edit(q, old, new, path=COPY):
    file = q.root / path
    file.write_text(file.read_text().replace(old, new))


def test_selected_revision_and_repeat(quilt):
    edit(quilt, "First statement.", "Improved statement.")
    edit(quilt, "Second statement uses", "Another proposal uses")
    preview = prepare(scan(quilt), COPY, ["zk-0001"])
    assert "Improved" in preview["patch"] and "Another proposal" not in preview["patch"]
    incorporate(scan(quilt), COPY, preview["token"])
    assert "Improved" in (quilt.root / DOC).read_text()
    rows = {r["key"]: r for r in comparison(scan(quilt), COPY)["changes"]}
    assert rows["zk-0001"]["offered"] is False
    assert rows["zk-0002"]["offered"] is True
    assert not prepare(scan(quilt), COPY, [])["patch"]


def test_stale_preview_and_conflict(quilt):
    edit(quilt, "First statement.", "Proposal.")
    preview = prepare(scan(quilt), COPY)
    edit(quilt, "Proposal.", "Later proposal.")
    with pytest.raises(SyncError, match="changed"):
        incorporate(scan(quilt), COPY, preview["token"])
    assert (quilt.root / DOC).read_text() == TEXT
    edit(quilt, "First statement.", "Author change.", DOC)
    with pytest.raises(SyncError, match="both versions"):
        prepare(scan(quilt), COPY)


def test_document_group_and_new_dependency(quilt):
    edit(quilt, "Original introduction.", "Proposed introduction.")
    edit(quilt, "First statement.", "First statement uses \\ref{zk-0003-ai}.")
    edit(quilt, "\\end{document}", "\\begin{lemma}\\label{zk-0003-ai}\nNew support.\n\\end{lemma}\n\\end{document}")
    with pytest.raises(SyncError):
        prepare(scan(quilt), COPY, ["zk-0001"])
    preview = prepare(scan(quilt), COPY, ["zk-0001", "zk-0003"], True)
    incorporate(scan(quilt), COPY, preview["token"])
    assert "Proposed introduction." in (quilt.root / DOC).read_text()
    assert "zk-0003-ai" not in (quilt.root / DOC).read_text()


def test_name_only_is_offered_without_mathematical_change(quilt):
    edit(quilt, "\\begin{lemma}\\label{zk-0001-ai}", "\\begin{lemma}\\label{zk-0001-ai}\n% !LOOM name: A useful result")
    row = next(r for r in comparison(scan(quilt), COPY)["changes"] if r["key"] == "zk-0001")
    assert row["offered"] and not row["math_changed"]


def test_shared_node_is_updated_in_its_home(quilt):
    root = quilt.root
    (root / "nodes").mkdir()
    start = TEXT.index("\\begin{lemma}")
    end = TEXT.index("\\end{lemma}") + len("\\end{lemma}")
    (root / "nodes/zk-0001.tex").write_text(TEXT[start:end] + "\n")
    (root / DOC).write_text(TEXT[:start] + "\\input{nodes/zk-0001}" + TEXT[end:])
    (root / "drafting/other.tex").write_text(
        "\\documentclass{article}\n\\newtheorem{lemma}{Lemma}\n\\begin{document}\n\\input{nodes/zk-0001}\n\\end{document}\n"
    )
    edit(quilt, "First statement.", "Improved statement.")
    preview = prepare(scan(quilt), COPY, ["zk-0001"])
    assert preview["paths"] == ["nodes/zk-0001.tex"]
    incorporate(scan(quilt), COPY, preview["token"])
    assert "\\input{nodes/zk-0001}" in (root / DOC).read_text()
    assert "Improved statement." in (root / "nodes/zk-0001.tex").read_text()


def test_refresh_keeps_proposals_and_advances_prose_base(quilt):
    from loom.adopt import refresh
    from loom.drafts import copy_states

    edit(quilt, "First statement.", "Proposed lemma.")
    edit(quilt, "Second statement uses", "Author revision uses", DOC)
    edit(quilt, "Original introduction.", "Author introduction.", DOC)
    answer = refresh(scan(quilt), COPY)
    assert not answer["conflicts"]
    text = (quilt.root / COPY).read_text()
    assert "Proposed lemma." in text and "Author revision uses" in text and "Author introduction." in text
    assert not copy_states(scan(quilt), load_history(quilt.history_dir))[0].stale
    assert not refresh(scan(quilt), COPY)["updated"]


def test_record_failure_restores_source_and_history(quilt, monkeypatch):
    import loom.review_origins as origins

    edit(quilt, "First statement.", "Proposal.")
    preview = prepare(scan(quilt), COPY)
    ledger = (quilt.history_dir / "ledger.jsonl").read_bytes()
    entries = sorted(p.name for p in quilt.history_dir.iterdir())
    original_write = origins.write

    def fail(*args, **kwargs):
        raise SyncError("injected record failure")

    monkeypatch.setattr(origins, "write", fail)
    with pytest.raises(SyncError, match="injected"):
        incorporate(scan(quilt), COPY, preview["token"])
    assert (quilt.root / DOC).read_text() == TEXT
    assert (quilt.history_dir / "ledger.jsonl").read_bytes() == ledger
    assert sorted(p.name for p in quilt.history_dir.iterdir()) == entries
    assert not (quilt.root / ".loom/review-origins.json").exists()
    monkeypatch.setattr(origins, "write", original_write)
    incorporate(scan(quilt), COPY, preview["token"])


def test_api_choices_are_pinned_and_never_accept(quilt):
    from loom.render.api import ApiError, handle

    edit(quilt, "First statement.", "Proposal.")
    data = comparison(scan(quilt), COPY)
    base = {"copy": COPY, "reviewer": "Tester", "fingerprint": data["fingerprint"]}
    with pytest.raises(ApiError):
        handle(quilt.root, "adopt-decision", {**base, "reviewer": "", "keys": ["zk-0001"], "document": False})
    handle(quilt.root, "adopt-decision", {**base, "keys": ["zk-0001"], "document": False})
    preview = handle(quilt.root, "adopt-preview", base)["result"]
    assert (quilt.root / DOC).read_text() == TEXT
    answer = handle(quilt.root, "adopt-decision", {**base, "keys": [], "document": False, "kept": ["zk-0001"]})
    assert answer["result"]["kept"] == ["zk-0001"]
    with pytest.raises(ApiError, match="Selection changed"):
        handle(quilt.root, "adopt-finish", {**base, "token": preview["token"]})


def test_document_choices_cannot_remove_a_kept_node(quilt):
    start = (quilt.root / COPY).read_text().index("\\begin{lemma}")
    end = (quilt.root / COPY).read_text().index("\\end{lemma}") + len("\\end{lemma}")
    file = quilt.root / COPY
    text = file.read_text()
    file.write_text(text[:start] + text[end:])
    with pytest.raises(SyncError, match="remove kept result"):
        prepare(scan(quilt), COPY, [], True)
    # The second lemma still refers to the removed first one, so even an explicit removal must refuse.
    with pytest.raises(SyncError):
        prepare(scan(quilt), COPY, ["zk-0001"], True)


def test_prose_merge_preserves_author_edit(quilt):
    edit(quilt, "First statement.", "AI revision.")
    edit(quilt, "\\end{document}", "New closing paragraph.\n\\end{document}")
    edit(quilt, "Original introduction.", "Author introduction.", DOC)
    preview = prepare(scan(quilt), COPY, ["zk-0001"], True)
    incorporate(scan(quilt), COPY, preview["token"])
    text = (quilt.root / DOC).read_text()
    assert "Author introduction." in text and "New closing paragraph." in text and "AI revision." in text
    assert not comparison(scan(quilt), COPY)["document_changed"]


def test_no_acceptance_written_and_history_verifies(quilt):
    from loom.history.checks import verify
    from loom.render.build import build

    edit(quilt, "First statement.", "AI revision.")
    p = prepare(scan(quilt), COPY, ["zk-0001"])
    incorporate(scan(quilt), COPY, p["token"])
    result = scan(quilt)
    assert not verify(result, load_history(quilt.history_dir))
    manifest = build(quilt).manifest
    assert next(r for r in manifest["unresolved"] if r["key"] == "zk-0001")["cause"] == "adopted"
    assert manifest["keys"]["zk-0001"]["state"] != "accepted"


def test_outside_result_is_forked_without_changing_its_document(quilt):
    root = quilt.root
    other = "drafting/other.tex"
    other_text = TEXT.replace("zk-0001", "zk-0003").replace("zk-0002", "zk-0004")
    (root / other).write_text(other_text)
    edit(
        quilt,
        "\\end{document}",
        "\\begin{lemma}\\label{zk-0003-ai}\nA separate version.\n\\end{lemma}\n\\end{document}",
    )
    p = prepare(scan(quilt), COPY, ["zk-0003"], True)
    assert p["adoption_base"]["mapping"]["zk-0003"] != "zk-0003"
    incorporate(scan(quilt), COPY, p["token"])
    assert (root / other).read_text() == other_text
    assert "A separate version." in (root / DOC).read_text()
    assert not [r for r in comparison(scan(quilt), COPY)["changes"] if r["offered"]]


def test_refresh_reports_both_changed_and_does_not_call_copy_fresh(quilt):
    from loom.adopt import refresh
    from loom.drafts import copy_states

    edit(quilt, "First statement.", "AI revision.")
    edit(quilt, "First statement.", "Author revision.", DOC)
    answer = refresh(scan(quilt), COPY)
    assert "zk-0001" in answer["conflicts"]
    # a conflict left unwritten is not "already up to date": it says what changed on both sides and what to do, and exits 1
    assert "changed on both sides" in answer["message"] and "zk-0001" in answer["message"]
    assert "already up to date" not in answer["message"]
    from tests.helpers import run

    assert run("ai", "refresh", COPY, cwd=quilt.root).exit_code == 1
    assert "AI revision." in (quilt.root / COPY).read_text()
    assert copy_states(scan(quilt), load_history(quilt.history_dir))[0].stale


def test_an_empty_selection_says_when_document_changes_wait(quilt):
    """Adopt said "No changes to incorporate" while a prose change waited behind --document-changes (CLI study, defect 10)."""
    edit(quilt, "Original introduction.", "Proposed introduction.")
    preview = prepare(scan(quilt), COPY, [])
    assert not preview["patch"] and preview["document_waiting"]
    from loom.adopt import nothing_to_incorporate

    assert "--document-changes" in nothing_to_incorporate(preview)


def test_identical_changes_are_not_conflicts(quilt):
    edit(quilt, "First statement.", "Same revision.")
    edit(quilt, "First statement.", "Same revision.", DOC)
    row = next(r for r in comparison(scan(quilt), COPY)["changes"] if r["key"] == "zk-0001")
    assert row["class"] == "identical" and not row["offered"]
    assert not prepare(scan(quilt), COPY, [])["patch"]


def test_removing_shared_inclusion_preserves_node_file(quilt):
    root = quilt.root
    (root / "nodes").mkdir()
    start = TEXT.index("\\begin{lemma}")
    end = TEXT.index("\\end{lemma}") + len("\\end{lemma}")
    node_text = TEXT[start:end] + "\n"
    (root / "nodes/zk-0001.tex").write_text(node_text)
    (root / DOC).write_text(TEXT[:start] + "\\input{nodes/zk-0001}" + TEXT[end:])
    copy_text = (root / COPY).read_text()
    start = copy_text.index("\\begin{lemma}")
    end = copy_text.index("\\end{lemma}") + len("\\end{lemma}")
    (root / COPY).write_text(
        (copy_text[:start] + copy_text[end:]).replace(
            "Second statement uses \\ref{zk-0001-ai}.", "Independent statement."
        )
    )
    preview = prepare(scan(quilt), COPY, ["zk-0001", "zk-0002"], True)
    incorporate(scan(quilt), COPY, preview["token"])
    assert (root / "nodes/zk-0001.tex").read_text() == node_text
    assert "\\input{nodes/zk-0001}" not in (root / DOC).read_text()


def test_annotations_and_acceptances_are_not_rewritten(quilt):
    import json

    from loom.review_origins import read

    root = quilt.root
    annotations = root / "annotations/log.jsonl"
    annotations.parent.mkdir()
    annotations.write_text("")
    edit(quilt, "\\begin{lemma}\\label{zk-0001-ai}", "\\begin{lemma}\\label{zk-0001-ai}\n% !LOOM name: Better name")
    preview = prepare(scan(quilt), COPY, ["zk-0001"])
    incorporate(scan(quilt), COPY, preview["token"])
    assert annotations.read_text() == ""
    assert not read(root)
    assert not (root / ".loom/state.toml").exists()
    origin_file = root / ".loom/review-origins.json"
    assert json.loads(origin_file.read_text()) == {}


def test_cli_requires_explicit_incorporation_after_noninteractive_preview(quilt):
    import json

    from tests.helpers import ok

    edit(quilt, "First statement.", "CLI proposal.")
    preview = json.loads(ok("adopt", COPY, "zk-0001", "--json", cwd=quilt.root).stdout)
    assert (quilt.root / DOC).read_text() == TEXT
    ok("adopt", COPY, "zk-0001", cwd=quilt.root)
    assert (quilt.root / DOC).read_text() == TEXT
    ok("adopt", COPY, "--incorporate", preview["token"], cwd=quilt.root)
    assert "CLI proposal." in (quilt.root / DOC).read_text()
    ok("history", "verify", cwd=quilt.root)


def test_agent_command_surface_cannot_incorporate(quilt):
    from loom.ai.layout import AGENT_COMMANDS
    from tests.helpers import run

    assert "adopt" not in AGENT_COMMANDS and "ai refresh" in AGENT_COMMANDS
    answer = run("adopt", COPY, "--json", cwd=quilt.root, env={"AI_AGENT": "1"})
    assert answer.exit_code != 0
    assert (quilt.root / DOC).read_text() == TEXT


def test_the_document_as_it_was_is_a_landmark(quilt):
    from tests.helpers import ok

    edit(quilt, "First statement.", "AI revision.")
    edit(quilt, "Original introduction.", "Author prose since the copy.", DOC)
    before = (quilt.root / DOC).read_text()
    preview = prepare(scan(quilt), COPY, ["zk-0001"])
    answer = incorporate(scan(quilt), COPY, preview["token"])
    assert (
        answer["landmark"] == "main-before-adopt-proposal"
        and "landmark main-before-adopt-proposal" in answer["message"]
    )
    assert "AI revision." in (quilt.root / DOC).read_text()
    steps = list(load_history(quilt.history_dir).steps())
    assert [e.action for e in steps[-2:]] == ["stamp", "adopt"] and answer["step"] == steps[-1].step
    assert steps[-2].get("landmark") == "main-before-adopt-proposal.tex"
    shown = ok("history", "show", "main-before-adopt-proposal", cwd=quilt.root).stdout
    assert "Author prose since the copy." in shown and "First statement." in shown
    assert shown == before


def test_a_second_adoption_numbers_its_landmark(quilt):
    edit(quilt, "First statement.", "AI revision.")
    incorporate(scan(quilt), COPY, prepare(scan(quilt), COPY, ["zk-0001"])["token"])
    edit(quilt, "Second statement uses", "A second revision uses")
    answer = incorporate(scan(quilt), COPY, prepare(scan(quilt), COPY, ["zk-0002"])["token"])
    assert answer["landmark"] == "main-before-adopt-proposal-2"


def test_a_git_quilt_is_left_uncommitted(quilt):
    from loom.sync import git, revision

    git(quilt.root, "init", "-b", "main")
    git(quilt.root, "config", "user.name", "Tester")
    git(quilt.root, "config", "user.email", "tester@example.test")
    git(quilt.root, "add", ".")
    git(quilt.root, "commit", "-m", "baseline")
    head = revision(quilt.root, "HEAD")
    edit(quilt, "First statement.", "AI revision.")
    incorporate(scan(quilt), COPY, prepare(scan(quilt), COPY, ["zk-0001"])["token"])
    assert revision(quilt.root, "HEAD") == head
    assert not git(quilt.root, "diff", "--cached").strip()


def test_an_author_edit_after_the_preview_refuses_it(quilt):
    edit(quilt, "First statement.", "AI revision.")
    preview = prepare(scan(quilt), COPY, ["zk-0001"])
    edit(quilt, "Original introduction.", "Edited after the preview.", DOC)
    with pytest.raises(SyncError, match="changed"):
        incorporate(scan(quilt), COPY, preview["token"])
    assert "Edited after the preview." in (quilt.root / DOC).read_text()


def test_keys_that_name_no_change_are_answered_with_the_command(quilt):
    edit(quilt, "First statement.", "AI revision.")
    with pytest.raises(SyncError) as refused:
        prepare(scan(quilt), COPY, ["draft5.tex"])
    message = str(refused.value)
    assert "never writes another document" in message and "zk-0001" in message
    assert "loom adopt proposal.tex" in message


def test_a_new_result_names_the_flag_that_places_it(quilt):
    edit(quilt, "\\end{document}", "\\begin{lemma}\\label{zk-0003-ai}\nNew support.\n\\end{lemma}\n\\end{document}")
    with pytest.raises(SyncError, match="--document-changes"):
        prepare(scan(quilt), COPY, ["zk-0003"])


def test_theorems_declared_in_a_local_style_are_results(quilt):
    root = quilt.root
    (root / "thm.sty").write_text("\\newtheorem{claim}{Claim}\n")
    for path in (DOC, COPY):
        text = (root / path).read_text()
        (root / path).write_text(
            text.replace("\\begin{document}", "\\usepackage{thm}\n\\begin{document}", 1).replace("{lemma}", "{claim}")
        )
    rows = {r["key"]: r for r in comparison(scan(quilt), COPY)["changes"]}
    assert {"zk-0001", "zk-0002"} <= set(rows)
    assert not [k for k in rows if "#proof:" in k]


def test_two_separate_prose_edits_on_each_side_merge(quilt):
    edit(quilt, "Original introduction.", "AI introduction.")
    edit(quilt, "\\end{document}", "AI closing.\n\\end{document}")
    edit(quilt, "\\begin{lemma}\\label{zk-0002}", "Author bridge.\n\\begin{lemma}\\label{zk-0002}", DOC)
    data = comparison(scan(quilt), COPY)
    assert not data["document_conflict"]
    assert "AI introduction." in data["merged_document"] and "Author bridge." in data["merged_document"]


def test_changed_preview_proposal_snapshot_is_reported_by_history_verify(quilt):
    from loom.history.checks import verify

    edit(quilt, "First statement.", "AI revision.")
    p = prepare(scan(quilt), COPY)
    incorporate(scan(quilt), COPY, p["token"])
    history = load_history(quilt.history_dir)
    adopted = next(e for e in history.entries if e.action == "adopt")
    (quilt.history_dir / adopted.dir / "proposal.tex").write_text("altered snapshot")
    assert any(d.code == "loom:history-edited" for d in verify(scan(quilt), history))


def test_new_proof_records_its_current_author_statement(quilt):
    edit(quilt, "First statement.", "Author revised statement.", DOC)
    draft = quilt.root / COPY
    draft.write_text(
        draft.read_text().replace("\\end{lemma}", "\\end{lemma}\n\\begin{proof}\nProposed proof.\n\\end{proof}", 1)
    )
    result = scan(quilt)
    proof = next(key for key, n in result.nodes.items() if n.kind == "proof")
    from loom.scan.labels import plain_key

    preview = prepare(result, COPY, [plain_key(proof)], True)
    incorporate(scan(quilt), COPY, preview["token"])
    history = load_history(quilt.history_dir)
    stamp, entry = list(history.steps())[-2:]
    # the landmark's stamp recorded the author's statement, so the proof is of that version
    assert entry.get("of")[plain_key(proof)] == f"zk-0001@{stamp.step}"
    assert "zk-0001" in stamp.get("froze")
    from loom.history.checks import verify

    assert not [d for d in verify(scan(quilt), history) if d.severity == "error"]


def _incoming_preview(quilt):
    from loom.render.api import handle

    data = comparison(scan(quilt), COPY)
    payload = {"copy": COPY, "reviewer": "Tester", "fingerprint": data["fingerprint"]}
    handle(quilt.root, "adopt-decision", {**payload, "keys": ["zk-0001"], "document": False})
    return handle(quilt.root, "adopt-preview", payload)["result"]


def test_incoming_explicit_acceptance_keeps_unvisited_dependents_pending(quilt, monkeypatch):
    from loom.records.store import Records
    from loom.render.api import handle
    from loom.render.build import build

    edit(quilt, "First statement.", "Improved statement.")
    preview = _incoming_preview(quilt)
    assert {r["key"] for r in preview["review"]["items"]} == {"zk-0001", "zk-0002"}
    monkeypatch.setattr("loom.cli.review._master_compiles", lambda *_: (True, ""))
    answer = handle(
        quilt.root,
        "adopt-finish",
        {
            "copy": COPY,
            "reviewer": "Tester",
            "token": preview["token"],
            "review_token": preview["review"]["token"],
            "accept": ["zk-0001"],
        },
    )["result"]
    assert answer["accepted"] == ["zk-0001"]
    assert answer["pending"] == ["zk-0002"]
    assert "zk-0001" in Records(quilt.root, quilt.history_dir).latest
    rows = build(quilt).manifest["unresolved"]
    assert "zk-0001" not in {r["key"] for r in rows}
    assert next(r for r in rows if r["key"] == "zk-0002")["status"] == "needs-review"


@pytest.mark.parametrize("accepted", [[], ["zk-9999"], ["zk-0001", "zk-0001"]])
def test_incoming_defaults_and_invalid_acceptance(quilt, accepted):
    from loom.records.store import Records
    from loom.render.api import ApiError, handle

    edit(quilt, "First statement.", "Improved statement.")
    preview = _incoming_preview(quilt)
    payload = {
        "copy": COPY,
        "reviewer": "Tester",
        "token": preview["token"],
        "review_token": preview["review"]["token"],
        "accept": accepted,
    }
    if accepted:
        with pytest.raises(ApiError, match="distinct mathematical blocks"):
            handle(quilt.root, "adopt-finish", payload)
        assert "Improved statement" not in (quilt.root / DOC).read_text()
    else:
        answer = handle(quilt.root, "adopt-finish", payload)["result"]
        assert answer["accepted"] == []
        assert set(answer["pending"]) == {"zk-0001", "zk-0002"}
    assert not Records(quilt.root, quilt.history_dir).latest


def test_incoming_preview_rejects_changed_source_and_reviewer(quilt):
    from loom.render.api import ApiError, handle

    edit(quilt, "First statement.", "Improved statement.")
    preview = _incoming_preview(quilt)
    payload = {
        "copy": COPY,
        "reviewer": "Tester",
        "token": preview["token"],
        "review_token": preview["review"]["token"],
        "accept": ["zk-0001"],
    }
    with pytest.raises(ApiError, match="reviewer name"):
        handle(quilt.root, "adopt-finish", {**payload, "reviewer": "Other"})
    edit(quilt, "Second statement uses", "Edited support uses", DOC)
    with pytest.raises(ApiError, match="changed"):
        handle(quilt.root, "adopt-finish", payload)
    assert "Improved statement" not in (quilt.root / DOC).read_text()


def test_incoming_compile_failure_reports_incorporated_but_pending(quilt, monkeypatch):
    from loom.records.store import Records
    from loom.render.api import handle

    edit(quilt, "First statement.", "Improved statement.")
    preview = _incoming_preview(quilt)
    monkeypatch.setattr("loom.cli.review._master_compiles", lambda *_: (False, "bad TeX"))
    answer = handle(
        quilt.root,
        "adopt-finish",
        {
            "copy": COPY,
            "reviewer": "Tester",
            "token": preview["token"],
            "review_token": preview["review"]["token"],
            "accept": ["zk-0001"],
        },
    )["result"]
    assert "Improved statement" in (quilt.root / DOC).read_text()
    assert "bad TeX" in answer["acceptance_error"]
    assert not answer["accepted"]
    assert not Records(quilt.root, quilt.history_dir).latest


def test_incoming_unchanged_proof_has_its_own_decision(quilt):
    from loom.incorporation_review import preview

    # Preview a revised statement in a source that already has its proof.
    edit(quilt, "\\end{lemma}", "\\end{lemma}\n\\begin{proof}An existing proof.\\end{proof}", DOC)
    before = scan(quilt)
    source = (quilt.root / DOC).read_text()
    view = preview(
        before,
        {DOC: source.replace("First statement.", "Improved statement.")},
        {"kind": "adopt", "token": "example"},
        "Tester",
    )
    proofs = [r for r in view["items"] if r["key"] in before.nodes and before.nodes[r["key"]].kind == "proof"]
    assert proofs
    assert proofs[0]["reason"] == "Existing proof · statement changed in the AI revision"
    assert proofs[0]["local"] and proofs[0]["proposed"]
    assert not proofs[0]["unavailable"]


def test_incoming_source_change_during_compile_does_not_accept(quilt, monkeypatch):
    from loom.records.store import Records
    from loom.render.api import handle

    edit(quilt, "First statement.", "Improved statement.")
    preview = _incoming_preview(quilt)

    def compile_and_edit(*_):
        edit(quilt, "Improved statement.", "Edited during compilation.", DOC)
        return True, ""

    monkeypatch.setattr("loom.cli.review._master_compiles", compile_and_edit)
    answer = handle(
        quilt.root,
        "adopt-finish",
        {
            "copy": COPY,
            "reviewer": "Tester",
            "token": preview["token"],
            "review_token": preview["review"]["token"],
            "accept": ["zk-0001"],
        },
    )["result"]
    assert "Source changed during compilation" in answer["acceptance_error"]
    assert not Records(quilt.root, quilt.history_dir).latest
