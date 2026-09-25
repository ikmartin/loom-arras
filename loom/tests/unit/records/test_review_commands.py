"""accept, comment, status, ai discard on the demo and synthetic quilts; the states, causes, facts, and the worked timeline of book 7.11."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from loom.scan.quilt import NO_AUTHOR_MESSAGE
from tests.helpers import edit, exits, json_of, ok, refused, the

REPO = Path(__file__).resolve().parents[3]
AUTHOR = ["--author", "Markas Hecht"]


AGENT = {"AI_AGENT": "1"}


def session(d: Path, title: str = "r1") -> tuple[str, Path]:
    """A session and its directory, as `loom session new` makes one; commenting into it does not create the directory."""
    r = ok("session", "new", title, "--author", "A. Author", cwd=d)
    sid = r.output.split()[0]
    return sid, d / ".loom" / "sessions" / sid


def events(root: Path) -> list[dict]:
    """Every line of the annotation log, in the order it was appended."""
    p = root / "annotations" / "log.jsonl"
    return [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()] if p.is_file() else []


def demo(tmp_path: Path, clean: bool = True) -> Path:
    """The demo quilt; with `clean` its shipped ledger and annotation log are removed so a test starts blank."""
    ok("init", str(tmp_path / "demo"), "--demo", cwd=tmp_path)
    d = tmp_path / "demo"
    if clean:
        shutil.rmtree(d / ".loom", ignore_errors=True)
        shutil.rmtree(d / "annotations", ignore_errors=True)
    return d


def test_demo_ships_two_accepted_one_stale_and_a_finished_session(tmp_path: Path) -> None:
    d = demo(tmp_path, clean=False)
    s = status_json(d)
    assert s["summary"]["accepted"] == 1 and s["summary"]["stale"] == 1
    assert s["keys"]["dm-0002/proof"]["acceptance"]["causes"][0]["id"] == "dm-0001"
    assert s["keys"]["dm-0003/proof"]["reviews"]["open"] == {
        "suggestion": 1,
        "objection": 1,
    }  # the author's suggestion and the agent's objection
    assert s["keys"]["dm-0003"]["reviews"]["open"] == {"suggestion": 1}  # the agent's suggestion on the statement
    notes = list((d / ".loom" / "sessions").glob("*/referee-dm-0003.notes.md"))
    assert len(notes) == 1, "the session the agent worked in keeps the notes it wrote"


def synthetic(tmp_path: Path) -> Path:
    dest = tmp_path / "synthetic"
    shutil.copytree(REPO / "tests" / "quilts" / "synthetic", dest)
    return dest


def status_json(q: Path) -> dict:  # type: ignore[type-arg]
    return json_of("status", "--json", cwd=q)


def test_reaccepting_unchanged_intermediate_resolves_indirect_staleness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    d = demo(tmp_path)
    c = d / "nodes" / "dm-0002.tex"
    c.write_text(c.read_text().replace("one or two points", "one or two points (Definition~\\ref{dm-0001})"))
    monkeypatch.setenv("LOOM_FIXED_TIME", "2026-09-21T12:00:00Z")
    ok("accept", "dm-0001", "dm-0002", "dm-0003", "--proofs", "--force", *AUTHOR, cwd=d)
    a = d / "nodes" / "dm-0001.tex"
    a.write_text(a.read_text().replace("Its \\emph{fixed locus} is", "Its \\emph{fixed locus}, a subset of $X$, is"))
    state = status_json(d)["keys"]["dm-0003/proof"]
    assert any(
        cause.get("id") == "dm-0001" and cause.get("via") == "dm-0002" for cause in state["acceptance"]["causes"]
    )
    assert all(cause["when"] == "2026-09-21" for cause in state["acceptance"]["causes"])
    monkeypatch.setenv("LOOM_FIXED_TIME", "2026-09-22T12:00:00Z")
    assert status_json(d)["keys"]["dm-0003/proof"]["acceptance"]["causes"][0]["when"] == "2026-09-21"
    ok("accept", "dm-0002", "--force", *AUTHOR, cwd=d)
    state = status_json(d)["keys"]["dm-0003/proof"]
    assert state["acceptance"]["fresh"] is True
    assert status_json(d)["keys"]["dm-0003"]["derived"]["settled"] is False
    c.write_text(c.read_text().replace("one or two points", "at most two points"))
    state = status_json(d)["keys"]["dm-0003/proof"]
    assert any(cause.get("id") == "dm-0002" and not cause.get("via") for cause in state["acceptance"]["causes"])


def test_review_build_publishes_rendered_comparison_and_citation(tmp_path: Path) -> None:
    d = demo(tmp_path, clean=False)
    ok("review", cwd=d)
    manifest = json.loads((d / "build" / "manifest.json").read_text())
    cause = manifest["keys"]["dm-0002/proof"]["acceptance"]["causes"][0]
    comparison = cause["comparison"]
    assert cause["citation"] in (d / "build" / manifest["masters"][0]["fragment"]).read_text()
    accepted_html = (d / "build" / comparison["accepted"]).read_text()
    current_html = (d / "build" / comparison["current"]).read_text()
    assert "fixed locus" in accepted_html
    assert "fixed locus" in current_html
    assert 'class="review-changed"' in accepted_html + current_html
    assert '<p class="review-changed"' not in accepted_html + current_html
    assert comparison["accepted_spans"] and comparison["current_spans"]


def test_observation_date_resets_after_a_cause_disappears(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = demo(tmp_path)
    ok("accept", "dm-0001", "--force", *AUTHOR, cwd=d)
    node = d / "nodes" / "dm-0001.tex"
    original = node.read_text()
    edited = original.replace("Its \\emph{fixed locus} is", "Its \\emph{fixed locus}, a subset of $X$, is")
    monkeypatch.setenv("LOOM_FIXED_TIME", "2026-09-21T12:00:00Z")
    node.write_text(edited)
    assert status_json(d)["keys"]["dm-0001"]["acceptance"]["causes"][0]["when"] == "2026-09-21"
    node.write_text(original)
    assert status_json(d)["keys"]["dm-0001"]["acceptance"]["fresh"] is True
    monkeypatch.setenv("LOOM_FIXED_TIME", "2026-09-23T12:00:00Z")
    node.write_text(edited)
    assert status_json(d)["keys"]["dm-0001"]["acceptance"]["causes"][0]["when"] == "2026-09-23"


def test_comparison_uses_preamble_saved_with_dependent_acceptance(tmp_path: Path) -> None:
    d = demo(tmp_path, clean=False)
    master = d / "drafting" / "main.tex"
    master.write_text(master.read_text().replace("\\operatorname{Fix}", "\\operatorname{Fixed}"))
    ok("review", cwd=d)
    manifest = json.loads((d / "build" / "manifest.json").read_text())
    causes = manifest["keys"]["dm-0002/proof"]["acceptance"]["causes"]
    comparison = the(causes, lambda c: c["kind"] == "dependency-changed", "dependency-changed cause")["comparison"]
    old = manifest["macros"]["sets"][comparison["accepted_macros"]]
    assert any(m["name"] == "Fix" and "\\operatorname{Fix}" in m["body"] for m in old)
    assert any(m["name"] == "Fix" and "\\operatorname{Fixed}" in m["body"] for m in manifest["macros"]["default"])


def test_ledger_refuses_without_author_exact_message(tmp_path: Path) -> None:
    d = demo(tmp_path)
    refused("accept", "dm-0002", "--force", cwd=d, code=2, match=NO_AUTHOR_MESSAGE)


def test_accept_writes_closure_hashes_and_proofs_flag(tmp_path: Path) -> None:
    d = demo(tmp_path)
    r = ok("accept", "dm-0002", "--proofs", *AUTHOR, cwd=d)
    assert "accepted dm-0002" in r.output and "accepted dm-0002/proof" in r.output
    ledger = (d / ".loom" / "state.toml").read_text()
    assert ledger.count("[[accept]]") == 2 and 'author = "Markas Hecht"' in ledger
    from loom.records.ledger import read_ledger

    rows = {r.key: r for r in read_ledger(d)}
    assert set(rows["dm-0002/proof"].closure) == {"dm-0001", "dm-0002"}
    assert rows["dm-0002"].closure == {}
    assert rows["dm-0002"].preamble.startswith("sha256:") and rows["dm-0002"].master == "drafting/main.tex"
    snaps = list((d / ".loom" / "history" / "texts").glob("*.tex"))
    assert len(snaps) >= 3
    s = status_json(d)
    assert s["keys"]["dm-0002"]["state"] == "accepted" and s["keys"]["dm-0002"]["acceptance"]["fresh"]
    assert s["keys"]["dm-0002/proof"]["acceptance"]["fresh"]
    assert s["summary"]["accepted"] == 2


def test_accept_all_live_selects_statements_and_proofs_and_tracks_changes(tmp_path: Path) -> None:
    d = demo(tmp_path)
    (d / "nodes" / "dm-0099.tex").write_text("\\begin{lemma}\\label{dm-0099}Loose.\\end{lemma}\n")
    refused("accept", "--all-live", "--yes", "--force", *AUTHOR, cwd=d, code=1, match="dm-0005/proof")
    assert not (d / ".loom" / "state.toml").exists()

    master = d / "drafting" / "main.tex"
    master.write_text(
        master.read_text()
        .replace(
            "\\incomplete{Say why the restriction is continuous when $X$ carries the constructible topology.}",
            "The restriction is continuous in the constructible topology.",
        )
        .replace("\\begin{remark}\\label{dm-0004}", "\\begin{remark}\\label{dm-0004}\n% !LOOM basis: local-proof")
    )
    candidate = d / "nodes" / "dm-0006.tex"
    candidate.write_text(
        candidate.read_text()
        .replace(
            "\\incomplete{Not yet attempted. The first clause should be immediate from the orbit decomposition of Lemma~\\ref{dm-0002}; the invariance clause is the part that needs an argument.}",
            "The count follows by partitioning into one- and two-point orbits.",
        )
        .replace(
            "\\begin{conjecture}[Orbit counting]\\label{dm-0006}",
            "\\begin{conjecture}[Orbit counting]\\label{dm-0006}\n% !LOOM basis: local-proof",
        )
    )
    outline = d / "drafting" / "outline.tex"
    outline.write_text(outline.read_text().replace("\\input{nodes/dm-0007}\n", ""))  # an open question stays loose
    refused("accept", "--all-live", "--force", *AUTHOR, cwd=d, code=2, match="--yes")
    assert not (d / ".loom" / "state.toml").exists()

    accepted = ok("accept", "--all-live", "--yes", "--force", *AUTHOR, cwd=d)
    assert "statements and" in accepted.output and "proofs" in accepted.output
    s = status_json(d)
    assert s["keys"]["dm-0002/proof"]["state"] == "accepted"
    assert s["keys"]["dm-0005/proof"]["state"] == "accepted"
    assert s["keys"]["dm-0006"]["state"] == "accepted"  # the outline master also makes this node live
    assert s["keys"]["dm-0007"]["state"] == "draft"
    assert s["keys"]["dm-0099"]["state"] == "draft"  # an unreached node is excluded


@pytest.mark.parametrize("extra", [("dm-0001",), ("--proofs",), ("--stale",)])
def test_accept_all_live_refuses_other_target_modes(tmp_path: Path, extra: tuple[str, ...]) -> None:
    d = demo(tmp_path)
    refused("accept", "--all-live", *extra, "--yes", "--force", *AUTHOR, cwd=d, code=2, match="cannot be combined")
    assert not (d / ".loom" / "state.toml").exists()


def test_state_draft_accepted_stale_incomplete_and_causes(tmp_path: Path) -> None:
    d = demo(tmp_path)
    ok("accept", "dm-0002", "--proofs", "dm-0003", *AUTHOR, cwd=d)
    s = status_json(d)
    assert s["keys"]["dm-0005/proof"]["state"] == "incomplete"
    assert s["keys"]["dm-0001"]["state"] == "draft"
    # dependency-changed: edit the definition the proof cites through \eqref
    f = d / "nodes" / "dm-0001.tex"
    f.write_text(f.read_text().replace("Its \\emph{fixed locus} is", "Its \\emph{fixed locus}, a subset of $X$, is"))
    s = status_json(d)
    proof = s["keys"]["dm-0002/proof"]
    assert proof["state"] == "accepted" and proof["acceptance"]["fresh"] is False
    assert [c["kind"] + " " + c.get("id", "") for c in proof["acceptance"]["causes"]] == ["dependency-changed dm-0001"]
    assert s["keys"]["dm-0002"]["acceptance"]["fresh"] is True
    # own-text-changed
    g = d / "nodes" / "dm-0002.tex"
    g.write_text(g.read_text().replace("one or two points", "at most two points"))
    s = status_json(d)
    assert "own-text-changed" in [c["kind"] for c in s["keys"]["dm-0002"]["acceptance"]["causes"]]
    # dependency-added: the theorem's statement now references the definition
    h = d / "nodes" / "dm-0003.tex"
    h.write_text(
        h.read_text().replace(
            "Let $(X,\\sigma)$ be a widget", "Let $(X,\\sigma)$ be a widget (Definition~\\ref{def:widget})"
        )
    )
    s = status_json(d)
    kinds = {c["kind"] for c in s["keys"]["dm-0003"]["acceptance"]["causes"]}
    assert {"own-text-changed", "dependency-added"} <= kinds
    # preamble-changed
    m = d / "drafting" / "main.tex"
    m.write_text(
        m.read_text().replace("\\newcommand{\\Fix}{\\operatorname{Fix}}", "\\newcommand{\\Fix}{\\operatorname{Fixed}}")
    )
    s = status_json(d)
    assert "preamble-changed" in {c["kind"] for c in s["keys"]["dm-0003"]["acceptance"]["causes"]}
    # dependency-removed
    f.unlink()
    (d / "drafting" / "main.tex").write_text(
        (d / "drafting" / "main.tex").read_text().replace("\\input{nodes/dm-0001}\n", "")
    )
    s = status_json(d)
    assert "dependency-removed" in {c["kind"] for c in s["keys"]["dm-0002/proof"]["acceptance"]["causes"]}
    row = the(
        ok("status", cwd=d).output.splitlines(), lambda ln: ln.startswith("dm-0002/proof "), "status row dm-0002/proof"
    )
    assert "accepted, stale" in row, row


def test_status_stale_lists_the_stale_rows_and_accept_stale_reaccepts_them(tmp_path: Path) -> None:
    """`--stale` lists the stale proof and not its fresh statement; `accept --stale` re-accepts exactly those rows, appending one ledger row to the two already there."""
    d = demo(tmp_path)
    ok("accept", "dm-0002", "--proofs", *AUTHOR, cwd=d)
    edit(d / "nodes" / "dm-0001.tex", "Its \\emph{fixed locus} is", "Its \\emph{fixed locus}, a subset of $X$, is")
    listed = ok("status", "--stale", cwd=d).output.splitlines()
    assert [ln.split()[0] for ln in listed[:-1]] == ["dm-0002/proof"], listed  # the last line is the summary
    ok("accept", "--stale", "--yes", "--force", *AUTHOR, cwd=d)
    s = status_json(d)
    assert s["summary"]["stale"] == 0 and s["summary"]["accepted"] == 2
    assert (d / ".loom" / "state.toml").read_text().count("[[accept]]") == 3


def test_accept_refuses_incomplete_and_uncompiled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = demo(tmp_path)
    refused("accept", "dm-0005/proof", *AUTHOR, cwd=d, code=1, match="incomplete")
    monkeypatch.setenv("FAKE_TEX_FAIL", "1")
    refused("accept", "dm-0002", *AUTHOR, cwd=d, code=1, match="does not compile")
    ok("accept", "dm-0002", "--force", *AUTHOR, cwd=d)
    refused("accept", "dm-9999", *AUTHOR, cwd=d, code=2, match="no such key: dm-9999")


def test_derived_proved_settled(tmp_path: Path) -> None:
    d = demo(tmp_path)
    ok("accept", "dm-0001", "dm-0002", "--proofs", *AUTHOR, cwd=d)
    s = status_json(d)
    assert s["keys"]["dm-0002"]["derived"] == {"proved": True, "settled": True}
    assert s["keys"]["dm-0001"]["derived"] == {"proved": True, "settled": True}  # a definition owes no proof
    ok("accept", "dm-0003", "--proofs", *AUTHOR, cwd=d)
    s = status_json(d)
    assert s["keys"]["dm-0003"]["derived"] == {
        "proved": True,
        "settled": True,
    }  # its proof's closure, dm-0002 and dm-0001, is settled
    f = d / "nodes" / "dm-0001.tex"
    f.write_text(f.read_text() + "\n% touched\n")
    s = status_json(d)
    assert s["keys"]["dm-0001"]["derived"]["proved"]  # comments do not change the hash


def test_comment_quote_rules_and_records(tmp_path: Path) -> None:
    d = demo(tmp_path)
    r = ok("comment", "dm-0003/proof", "Needs the rigidity lemma.", "--quote", "closedness", *AUTHOR, cwd=d)
    assert r.output.startswith("a-") and "dm-0003/proof  objection  (Markas Hecht)" in r.output
    a = events(d)[0]
    assert a["event"] == "created" and a["author"] == "Markas Hecht" and a["kind"] == "human"
    assert a["session"].startswith("s-")  # writing with nothing active opens a session rather than refusing
    assert a["against"].startswith("sha256:") and a["anchor"]["exact"] == "closedness"
    assert (
        len(a["anchor"]["prefix"]) <= 32 and len(a["anchor"]["suffix"]) <= 32 and a["anchor"]["prefix"].endswith("For ")
    )
    refused(
        "comment",
        "dm-0003/proof",
        "x",
        "--quote",
        "no such words here",
        *AUTHOR,
        cwd=d,
        code=1,
        match="quote not found in dm-0003/proof",
    )
    refused("comment", "dm-0003/proof", "x", "--quote", "the", *AUTHOR, cwd=d, code=1, match="ambiguous")
    # the quote lies in the proof, outside the statement's own text
    refused(
        "comment", "dm-0003", "x", "--quote", "closedness", *AUTHOR, cwd=d, code=1, match="quote not found in dm-0003"
    )
    r5 = ok("comment", "dm-0003", "--kind", "confirmation", *AUTHOR, cwd=d)
    assert "  confirmation  " in r5.output
    s = status_json(d)
    assert s["keys"]["dm-0003/proof"]["reviews"]["open"] == {"objection": 1}
    assert s["keys"]["dm-0003"]["reviews"]["latest_current"]["author"]["id"] == "Markas Hecht"
    refused("comment", "dm-0003", "x", "--kind", "bogus", *AUTHOR, cwd=d, code=2, match="kind must be one of")


def test_comment_run_author_log_reply_resolve(tmp_path: Path) -> None:
    """Who wrote a finding and which session it belongs to are two fields; a reply and a resolution each take their message as the one positional, and file it as the body rather than reading it as a target."""
    d = demo(tmp_path)
    sid, run_dir = session(d, "2026-09-16T14-02-referee")
    r = ok(
        "comment",
        "dm-0003/proof",
        "Domination is asserted.",
        "--quote",
        "diagonal is closed",
        "--session",
        sid,
        cwd=d,
        env=AGENT,
    )
    ann_id = r.output.split()[0]
    assert "loom comment dm-0003/proof" in (run_dir / "run.log").read_text()
    assert not (run_dir / "annotations.json").exists()  # one log, not a file per run
    first = events(d)[0]
    # the author is who wrote it and the session is where it belongs; the two used to be one field (plan 0.13 §5)
    assert first["author"] == "agent" and first["kind"] == "agent"
    assert first["session"] == sid
    r2 = ok("comment", "--reply", ann_id, "Agreed, will fix.", "--author", "Bob", cwd=d)
    assert "reply to" in r2.output
    r3 = ok("comment", "--resolve", ann_id, "Added the argument.", *AUTHOR, cwd=d)
    assert r3.output.strip() == f"resolved {ann_id}"
    assert [(e["event"], e.get("body")) for e in events(d)] == [
        ("created", "Domination is asserted."),
        ("replied", "Agreed, will fix."),
        ("resolved", "Added the argument."),
    ]  # appended, never rewritten
    s = status_json(d)
    assert s["keys"]["dm-0003/proof"]["reviews"]["open"] == {}


def test_a_run_resolves_its_own_annotation(tmp_path: Path) -> None:
    """The case an agent hits on every re-check, and the one the file-per-record store silently lost.

    When the parent lived in the same file as the writer, the status flip was written and then overwritten by the
    writer's stale copy a line later. The two `--resolve` tests either side of this one both resolve as a person,
    which is the path that always worked. An append-only log cannot express the bug; this is what says so.
    """
    d = demo(tmp_path)
    sid, run_dir = session(d, "r1")
    made = ok(
        "comment", "dm-0002", "Orbits may be empty.", "--quote", "Every orbit", "--session", sid, cwd=d, env=AGENT
    )
    ann = made.output.split()[0]

    # the run resolves the annotation it made itself, writing as the same run
    got = ok("comment", "--resolve", ann, "Fixed in the revision.", "--session", sid, cwd=d, env=AGENT)
    assert got.output.strip() == f"resolved {ann}"

    assert [e["event"] for e in events(d)] == ["created", "resolved"]
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {}  # the resolution survived


def test_a_recheck_edits_a_finding_rather_than_replying(tmp_path: Path) -> None:
    """The log's point: a finding that still stands is restated, not replied to, so three passes leave one finding."""
    d = demo(tmp_path)
    sid, run_dir = session(d, "r1")
    r = ok(
        "comment",
        "dm-0002",
        "Orbits may be empty.",
        "--quote",
        "Every orbit",
        "--kind",
        "objection",
        "--severity",
        "major",
        "--payload",
        "Every nonempty orbit...",
        "--placement",
        "replace",
        "--session",
        sid,
        cwd=d,
        env=AGENT,
    )
    assert "objection major" in r.output
    ann = r.output.split()[0]

    e = ok(
        "comment", "--edit", ann, "Still wrong, and the fix is smaller than I said.", "--session", sid, cwd=d, env=AGENT
    )
    assert e.output.strip() == f"edited {ann}"

    kinds = [x["event"] for x in events(d)]
    assert kinds == ["created", "edited"]  # appended; the first body is still on disk

    s = status_json(d)
    assert s["keys"]["dm-0002"]["reviews"]["open"] == {"objection": 1}  # one finding, not two
    f = json_of("ai", "findings", "--session", sid, "--json", cwd=d)["findings"]
    assert len(f) == 1 and f[0]["severity"] == "major"  # severity and the anchor survive an edit that names neither

    refused(
        "comment",
        "--edit",
        "a-nope-0001",
        "x",
        "--session",
        sid,
        cwd=d,
        env=AGENT,
        code=1,
        match="no annotation a-nope-0001",
    )


def test_a_finding_raised_in_error_is_discarded_not_resolved(tmp_path: Path) -> None:
    """Resolving claims the author addressed it. An agent that misread wants to say the opposite (blocks.md rule 7)."""
    d = demo(tmp_path)
    sid, run_dir = session(d, "r1")
    made = ok(
        "comment", "dm-0002", "Orbits may be empty.", "--quote", "Every orbit", "--session", sid, cwd=d, env=AGENT
    )
    ann = made.output.split()[0]

    gone = ok("comment", "--discard", ann, "I misread the definition.", "--session", sid, cwd=d, env=AGENT)
    assert gone.output.strip() == f"discarded {ann}"

    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {}
    events_for = [e for e in events(d) if e.get("id") == ann]
    assert [e["event"] for e in events_for] == ["created", "discarded"]
    assert events_for[1]["body"] == "I misread the definition."  # the reason is kept, not thrown away

    refused(
        "comment",
        "--discard",
        "a-nope-0001",
        "x",
        "--session",
        sid,
        cwd=d,
        env=AGENT,
        code=1,
        match="no annotation a-nope-0001",
    )


def test_severity_and_placement_are_checked(tmp_path: Path) -> None:
    d = demo(tmp_path)
    refused(
        "comment",
        "dm-0002",
        "x",
        "--severity",
        "catastrophic",
        *AUTHOR,
        cwd=d,
        code=2,
        match="Invalid value for '--severity'",
    )
    # a placement with nothing to place
    refused("comment", "dm-0002", "x", "--placement", "after", *AUTHOR, cwd=d, code=2, match="give --payload too")


def test_discard_flag_hides_everywhere_and_undo(tmp_path: Path) -> None:
    d = demo(tmp_path)
    # two sittings, because discarding one must not take the other with it
    mine, _ = session(d, "the author's own")
    sid, run_dir = session(d, "r1")
    ok("comment", "dm-0002", "Objection.", "--quote", "Every orbit", "--session", sid, cwd=d, env=AGENT)
    ok("comment", "dm-0002", "Person.", "--quote", "one or two", "--session", mine, *AUTHOR, cwd=d)
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {"objection": 2}
    ok("ai", "discard", sid, cwd=d)
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {"objection": 1}
    assert [e["event"] for e in events(d)][-1] == "discarded"  # an event, not a rewritten file
    ok("ai", "discard", "--author", "Markas Hecht", cwd=d)
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {}
    ok("ai", "discard", sid, "--undo", cwd=d)
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {"objection": 1}
    ok("ai", "discard", "--target", "dm-0002", "--undo", cwd=d)
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {"objection": 2}
    assert ok("ai", "discard", "--before", "2000-01-01", cwd=d).output.strip() == "no matching records"
    st = status_json(d)
    assert len(st["runs"]) == 2 and ok("status", "--runs", cwd=d).output.count("annotation(s)") == 2


def test_reference_notes_accept_and_reject(tmp_path: Path) -> None:
    """An agent proposes a citation; the author accepts or rejects. Neither path touches refs.bib (DR-122)."""
    d = demo(tmp_path)
    sid, run_dir = session(d, "r1")
    bib_before = (d / "refs.bib").read_text()

    good = ok(
        "comment",
        "dm-0002",
        "Kreck 1999 proves this; cite it instead of arguing.",
        "--quote",
        "Every orbit",
        "--kind",
        "citation",
        "--payload",
        "K. Kreck, Surgery and duality, Ann. of Math. 149 (1999).",
        "--session",
        sid,
        cwd=d,
        env=AGENT,
    )
    first = good.output.split()[0]
    bad = ok(
        "comment",
        "dm-0003",
        "Har77 might cover this.",
        "--quote",
        "with $X$ a finite set",
        "--kind",
        "citation",
        "--session",
        sid,
        cwd=d,
        env=AGENT,
    )
    second = bad.output.split()[0]

    ok("refs", "note", "--accept", first, "--reason", "Checked the statement.", *AUTHOR, cwd=d)
    notes = [json.loads(ln) for ln in (d / "reference-notes.jsonl").read_text().splitlines() if ln.strip()]
    assert len(notes) == 1
    assert notes[0]["for"] == ["dm-0002"] and notes[0]["identifier"] == {"verified": False}
    assert notes[0]["from"]["annotation"] == first and "Kreck" in notes[0]["claim"]

    ok("refs", "note", "--reject", second, "--reason", "Har77 is about something else.", *AUTHOR, cwd=d)
    still = [json.loads(ln) for ln in (d / "reference-notes.jsonl").read_text().splitlines() if ln.strip()]
    assert len(still) == 1  # rejecting records nothing; the reason rides on the resolve event

    # both suggestions are resolved either way, so neither sits open forever
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {}
    assert (d / "refs.bib").read_text() == bib_before  # the bibliography is the author's, always

    listed = ok("refs", "note", "--list", cwd=d)
    assert "Kreck" in listed.output

    plain = ok("comment", "dm-0002", "Not a citation.", "--quote", "one or two", *AUTHOR, cwd=d)
    refused(
        "refs", "note", "--accept", plain.output.split()[0], *AUTHOR, cwd=d, code=1, match="not a citation suggestion"
    )


def test_retired_key_dependency_removed_merge_by_alias(tmp_path: Path) -> None:
    d = demo(tmp_path)
    ok("accept", "dm-0004", "dm-0002", "--proofs", *AUTHOR, cwd=d)
    m = d / "drafting" / "main.tex"
    text = m.read_text()
    remark = text[text.index("\\begin{remark}\\label{dm-0004}") : text.index("\\end{remark}") + len("\\end{remark}")]
    m.write_text(text.replace(remark + "\n", ""))
    r = ok("status", "--retired", cwd=d)
    assert r.output.startswith("dm-0004")
    lint = json_of("lint", "--json", cwd=d)
    assert any(x["code"] == "loom:retired-ledger-key" for x in lint)
    # merge by alias: dm-0004 becomes an alias of dm-0005
    m.write_text(m.read_text().replace("\\label{dm-0005}", "\\label{dm-0005}\\label{dm-0004}"))
    assert ok("status", "--retired", cwd=d).output.strip() == ""
    assert ok("deps", "dm-0004", cwd=d).output.startswith("dm-0005")


def test_positional_key_recovery_by_hash(tmp_path: Path) -> None:
    q = synthetic(tmp_path)
    ok("accept", "sy-0006/proof/2", "--force", *AUTHOR, cwd=q)
    f = q / "nodes" / "sy-0006.tex"
    text = f.read_text()
    first = text[text.index("\\begin{proof}") : text.index("\\end{proof}") + len("\\end{proof}") + 1]
    f.write_text(text.replace(first, "", 1))
    s = status_json(q)
    assert "sy-0006/proof/2" not in s["keys"]
    assert s["keys"]["sy-0006/proof"]["previous_key_match"] == "sy-0006/proof/2"
    r = ok("status", cwd=q)
    assert "acceptance recorded under sy-0006/proof/2; re-accept to confirm" in r.output
    lint = json_of("lint", "--json", cwd=q, code=1)
    assert any(x["code"] == "loom:previous-key-match" for x in lint)


def test_status_filters_and_never_fails(tmp_path: Path) -> None:
    q = synthetic(tmp_path)
    for flags in (
        ["--stale"],
        ["--draft"],
        ["--incomplete"],
        ["--loose"],
        ["--undigested"],
        ["--unmatched-cites"],
        ["--retired"],
        ["--runs"],
        ["--master", "drafting/main.tex"],
        ["--tag", "orbits"],
    ):
        ok("status", *flags, cwd=q)
    assert "sy-000C/proof" in ok("status", "--incomplete", cwd=q).output
    assert "sy-0009" in ok("status", "--loose", cwd=q).output
    assert ok("status", "--undigested", cwd=q).output.strip() == "Har77"
    j = status_json(q)
    assert set(j) == {"summary", "keys", "runs", "undigested", "retired", "digests", "reading"}
    assert j["summary"]["incomplete"] == 1


def test_timeline_7_11(tmp_path: Path) -> None:
    d = demo(tmp_path)
    key, proof = "dm-0003", "dm-0003/proof"
    sid, run_dir = session(d, "2026-09-16T14-02-referee")
    # Day 1: draft, never reviewed; a referee run leaves three objections
    s = status_json(d)
    assert s["keys"][key]["state"] == "draft" and s["keys"][key]["reviews"]["latest_any"] is None
    ok(
        "comment",
        key,
        "The hypothesis 'finite' is not needed for closedness.",
        "--quote",
        "finite set",
        "--session",
        sid,
        cwd=d,
        env=AGENT,
    )
    ok(
        "comment",
        proof,
        "Parity needs the orbit count.",
        "--quote",
        "disjoint union of orbits",
        "--session",
        sid,
        cwd=d,
        env=AGENT,
    )
    ok(
        "comment",
        proof,
        "Diagonal argument needs Hausdorff stated.",
        "--quote",
        "diagonal is closed",
        "--session",
        sid,
        cwd=d,
        env=AGENT,
    )
    s = status_json(d)
    assert s["keys"][key]["reviews"]["open"] == {"objection": 1} and s["keys"][proof]["reviews"]["open"] == {
        "objection": 2
    }
    ok("build", cwd=d)
    frag = (d / "build" / "fragments" / "nodes" / "dm-0003.html").read_text()
    assert frag.count('<mark class="annotation"') == 3
    # Day 2: the author rewrites the proof; the proof annotations detach; the agent re-checks clean
    f = d / "nodes" / "dm-0003.tex"
    old = f.read_text()
    new = (
        old[: old.index("\\begin{proof}")]
        + "\\begin{proof}\n\\uses{dm-0002}\nBy Lemma~\\ref{lem:orbits}, $X$ splits into orbits of size one or two, so the parities agree. Closedness: the fixed locus is the preimage of the diagonal, which is closed since $X$ is Hausdorff.\n\\end{proof}\n"
    )
    f.write_text(new)
    s = status_json(d)
    assert s["keys"][proof]["reviews"]["detached"] == 2
    ok("comment", proof, "--kind", "confirmation", "--session", sid, cwd=d, env=AGENT)
    s = status_json(d)
    assert s["keys"][proof]["reviews"]["latest_current"]["author"]["kind"] == "agent"
    # Day 3: the author resolves the statement objection and accepts
    ann = next(e["id"] for e in events(d) if e["event"] == "created")
    ok("comment", key, "--resolve", ann, "Finiteness is used for parity.", *AUTHOR, cwd=d)
    ok("accept", key, "--proofs", *AUTHOR, cwd=d)
    s = status_json(d)
    assert s["keys"][key]["state"] == "accepted" and s["keys"][proof]["state"] == "accepted"
    assert s["keys"][key]["derived"]["proved"] is True
    # Day 9: an upstream definition changes; the lemma's proof (not the theorem) goes stale; re-accept
    ok("accept", "dm-0002", "--proofs", *AUTHOR, cwd=d)
    g = d / "nodes" / "dm-0001.tex"
    g.write_text(g.read_text().replace("Its \\emph{fixed locus} is", "Its \\emph{fixed locus}, a subset of $X$, is"))
    s = status_json(d)
    stale = [k for k, e in s["keys"].items() if e.get("acceptance") and not e["acceptance"]["fresh"]]
    assert stale == ["dm-0002/proof"]
    assert s["keys"]["dm-0002/proof"]["acceptance"]["causes"][0]["id"] == "dm-0001"
    explain = ok("status", "--explain", "dm-0002/proof", cwd=d)
    diff = [ln.strip() for ln in explain.output.splitlines()]
    assert "dependency-changed dm-0001" in explain.output
    assert any(ln.startswith("-") and ln.endswith("Its \\emph{fixed locus} is") for ln in diff), explain.output
    assert any(ln.startswith("+") and ln.endswith("Its \\emph{fixed locus}, a subset of $X$, is") for ln in diff), (
        explain.output
    )
    ok("build", cwd=d)
    m = json.loads((d / "build" / "manifest.json").read_text())
    cause = m["keys"]["dm-0002/proof"]["acceptance"]["causes"][0]
    assert cause["diff"] and (d / "build" / cause["diff"]).exists()
    ok("accept", "--stale", "--yes", "--force", *AUTHOR, cwd=d)
    s = status_json(d)
    assert s["summary"]["stale"] == 0
    ok("build", cwd=d)
    m = json.loads((d / "build" / "manifest.json").read_text())
    assert m["annotations"] and any(a["detached"] for a in m["annotations"].values())


def test_status_json_answers_the_same_question_as_the_text_form(tmp_path: Path) -> None:
    """Every row filter applies to both forms (F3): `--json` is what a tool reaches for, and it returned the whole quilt."""
    q = synthetic(tmp_path)
    text = ok("status", "--master", "drafting/main.tex", cwd=q)
    lines = [ln for ln in text.output.splitlines() if ln.strip()][:-1]  # the last line is the count
    js = json_of("status", "--master", "drafting/main.tex", "--json", cwd=q)
    assert len(js["keys"]) == len(lines)
    assert all("drafting/main.tex" in e["reached_by"] for e in js["keys"].values())
    assert len(js["keys"]) < len(json_of("status", "--json", cwd=q)["keys"])
    assert js["summary"]["keys"] == len(lines)  # and the count is of what was asked for, not of the quilt


def test_status_carries_the_title_beside_the_taxon(tmp_path: Path) -> None:
    """`rl-000G (Lemma) draft` does not say what the lemma is about, so choosing what to review meant grepping the source (F5)."""
    d = demo(tmp_path)
    js = status_json(d)
    assert js["keys"]["dm-0002"]["title"] == "Orbits" and js["keys"]["dm-0002"]["taxon"] == "Lemma"
    line = the(ok("status", cwd=d).output.splitlines(), lambda ln: ln.startswith("dm-0002 "), "status row dm-0002")
    assert "Orbits" in line


def test_status_filters_by_what_the_annotations_say(tmp_path: Path) -> None:
    d = demo(tmp_path)
    ok("comment", "dm-0002", "Which orbits?", "--severity", "major", *AUTHOR, cwd=d)
    ok("comment", "dm-0003", "A thought", "--kind", "suggestion", *AUTHOR, cwd=d)

    major = json_of("status", "--severity", "major", "--json", cwd=d)["keys"]
    assert list(major) == ["dm-0002"]
    sugg = json_of("status", "--kind", "suggestion", "--json", cwd=d)["keys"]
    assert list(sugg) == ["dm-0003"]
    assert list(json_of("status", "--status", "resolved", "--json", cwd=d)["keys"]) == []
    assert list(json_of("status", "--detached", "--json", cwd=d)["keys"]) == []


def test_findings_filter_and_withdrawn_ones_say_why(tmp_path: Path) -> None:
    """A withdrawn finding is not a live one (F20); the reason was typed into the log and shown nowhere."""
    d = demo(tmp_path)
    rel = ok("ai", "start", "Referee", cwd=d).output.strip()
    run_name = rel.rsplit("/", 1)[-1]
    ok("comment", "dm-0002", "Wrong", "--severity", "major", "--session", run_name, cwd=d, env=AGENT)
    ok("comment", "dm-0003", "Also wrong", "--session", run_name, cwd=d, env=AGENT)
    live = json_of("ai", "findings", "--session", run_name, "--json", cwd=d)["findings"]
    assert len(live) == 2
    assert [f["message"] for f in live] == ["Wrong", "Also wrong"]

    ok("comment", "--discard", live[1]["id"], "I misread the hypothesis", "--session", run_name, cwd=d, env=AGENT)
    after = json_of("ai", "findings", "--session", run_name, "--json", cwd=d)["findings"]
    assert [f["id"] for f in after] == [live[0]["id"]]  # the withdrawn one is out of the way

    every = json_of("ai", "findings", "--session", run_name, "--all", "--json", cwd=d)["findings"]
    gone = the(every, lambda f: f["discarded"], "discarded finding")
    assert gone["discard_reason"] == "I misread the hypothesis"
    assert "I misread the hypothesis" in ok("ai", "findings", "--session", run_name, "--all", cwd=d).output

    only_major = json_of("ai", "findings", "--session", run_name, "--severity", "major", "--json", cwd=d)
    assert [f["id"] for f in only_major["findings"]] == [live[0]["id"]]


BATCH = [
    pytest.param(
        [{"edit": "{ann}", "message": "Which orbits exactly?"},
         {"target": "dm-0003", "message": "A second", "payload": "\\begin{lemma}\\end{lemma}"},
         {"resolve": "{ann}", "message": "fixed"}],
        0, None, [("edited", "Which orbits exactly?"), ("created", "A second"), ("resolved", "fixed")],
        id="every-verb-one-to-a-line",
    ),
    # a batch is written by a program that cannot see the result, so a misspelled key must not file an empty annotation
    pytest.param([{"target": "dm-0002", "messsage": "typo"}], 1, "unknown key(s) messsage", [], id="unknown-key"),
    pytest.param([{"edit": "{ann}", "discard": "{ann}", "message": "?"}], 1, "one verb per line", [], id="two-verbs"),
    pytest.param([{"edit": "{ann}"}], 1, "nothing to change", [], id="answers-nothing"),
    # the failing line stops the rest, and what came before it stands
    pytest.param(
        [{"target": "dm-0002", "message": "one", "quote": "Every orbit", "kind": "suggestion"},
         {"target": "dm-0002", "message": "two", "quote": "NOPE"},
         {"target": "dm-0002", "message": "three"}],
        1, "batch line 2", [("created", "one")],
        id="stops-at-the-failing-line",
    ),
]  # fmt: skip


@pytest.mark.parametrize(("lines", "code", "match", "wrote"), BATCH)
def test_a_batch_carries_every_verb_and_refuses_line_by_line(
    tmp_path: Path, lines: list[dict[str, str]], code: int, match: str | None, wrote: list[tuple[str, str]]
) -> None:
    """`comment --batch` reads one JSON object per line against an existing finding `{ann}`; `wrote` is the events it appends, in order."""
    d = demo(tmp_path)
    ann = ok("comment", "dm-0002", "Which orbits?", *AUTHOR, cwd=d).output.split()[0]
    stdin = "".join(json.dumps({k: v.replace("{ann}", ann) for k, v in line.items()}) + "\n" for line in lines)
    r = exits(code, "comment", "--batch", *AUTHOR, cwd=d, stdin=stdin, match=match)
    if match == "unknown key(s) messsage":
        assert "accepted:" in r.output, r.output  # the refusal names the keys a line may carry
    assert [(e["event"], e.get("body")) for e in events(d)[1:]] == wrote


def test_a_clean_read_takes_no_severity(tmp_path: Path) -> None:
    """`--severity` grades a fault; `--kind ok` says there is none, and the pair was accepted and stored (H9)."""
    d = demo(tmp_path)
    refused(
        "comment",
        "dm-0002",
        "--kind",
        "confirmation",
        "--severity",
        "major",
        *AUTHOR,
        cwd=d,
        code=2,
        match="it belongs on objection or suggestion",
    )
    assert events(d) == []


def test_a_kind_is_named_by_any_unambiguous_prefix_and_severity_only_grades_a_fault(tmp_path: Path) -> None:
    """`confirmation` is longer than `ok` was, and the extra letters should cost nothing."""
    from loom.records.annotations import full_kind

    assert full_kind("conf") == "confirmation"
    assert full_kind("n") == "note"
    assert full_kind("objection") == "objection"
    assert full_kind("c") is None, "citation and confirmation both start with c, so it must refuse rather than guess"
    assert full_kind("zzz") is None

    d = demo(tmp_path)
    ok("comment", "dm-0002", "Fine.", "--kind", "conf", *AUTHOR, cwd=d)
    assert events(d)[-1]["annotation_kind"] == "confirmation"
    refused(
        "comment", "dm-0002", "Why?", "--kind", "question", "--severity", "major", *AUTHOR,
        code=2, match="belongs on objection or suggestion", cwd=d,
    )  # fmt: skip


def test_a_reference_note_records_the_work_and_the_argument_for_it(tmp_path: Path) -> None:
    """`work` held the agent's prose and `claim` was empty, so the breadcrumb could never become a bibliography entry (H18)."""
    d = demo(tmp_path)
    bare = ok("comment", "dm-0002", "Someone has surely proved this.", "--kind", "citation", *AUTHOR, cwd=d)
    refused("refs", "note", "--accept", bare.output.split()[0], *AUTHOR, cwd=d, code=1, match="proposes no work")

    named = ok(
        "comment",
        "dm-0002",
        "The parity count is Kreschmer's; cite it rather than reproving it.",
        "--kind",
        "citation",
        "--payload",
        "Kreschmer, Cycle groups of finite permutation actions, J. Alg. 1999",
        *AUTHOR,
        cwd=d,
    )
    ok("refs", "note", "--accept", named.output.split()[0], *AUTHOR, cwd=d)
    note = json.loads((d / "reference-notes.jsonl").read_text().splitlines()[0])
    assert note["work"].startswith("Kreschmer,")
    assert note["claim"].startswith("The parity count")


def test_a_reply_refuses_what_it_cannot_carry(tmp_path: Path) -> None:
    """The 0.14 study: an agent replied "a replacement is attached" with `--payload`, and the payload was dropped without a word."""
    d = demo(tmp_path)
    ann = ok("comment", "dm-0002", "A finding", *AUTHOR, cwd=d).output.split()[0]
    before = len(events(d))
    for extra in (("--payload", "New sentence."), ("--severity", "minor"), ("--quote", "finite set")):
        for verb in ("--reply", "--resolve"):
            refused(
                "comment",
                verb,
                ann,
                "A replacement is attached.",
                *extra,
                *AUTHOR,
                cwd=d,
                code=2,
                match=f"{extra[0]} would be lost",
            )
    assert len(events(d)) == before


def test_a_verb_that_answers_nothing_is_refused(tmp_path: Path) -> None:
    d = demo(tmp_path)
    ann = ok("comment", "dm-0002", "A finding", *AUTHOR, cwd=d).output.split()[0]
    before = len(events(d))

    refused("comment", "--reply", ann, *AUTHOR, cwd=d, code=2, match="a reply with no message")
    refused("comment", "--edit", ann, *AUTHOR, cwd=d, code=2, match="nothing to change")
    refused("comment", "--edit", ann, "", *AUTHOR, cwd=d, code=2, match="empty body")
    assert len(events(d)) == before  # none of them wrote

    # a field-only edit still stands, and a resolution needs no comment (7.4)
    ok("comment", "--edit", ann, "--severity", "minor", *AUTHOR, cwd=d)
    ok("comment", "--resolve", ann, *AUTHOR, cwd=d)


def test_a_finding_on_a_section_is_visible_where_the_author_looks(tmp_path: Path) -> None:
    """`loom comment` accepts a section, stores the annotation, and `status` showed nothing: a major finding filed through the sanctioned command was invisible in the only place the author is told to look (H19)."""
    q = synthetic(tmp_path)
    ok("comment", "sy-0100", "Never defines the torus T that Results uses", "--severity", "major", *AUTHOR, cwd=q)

    js = json_of("status", "--json", cwd=q)
    assert js["keys"]["sy-0100"]["kind"] == "section"
    assert js["keys"]["sy-0100"]["state"] == ""  # a section is a container, not a claim
    assert js["keys"]["sy-0100"]["reviews"]["open"] == {"objection": 1}

    line = the(ok("status", cwd=q).output.splitlines(), lambda ln: ln.startswith("sy-0100 "), "status row sy-0100")
    assert "Introduction" in line and "1 open objection" in line
    assert "1 open objection" in ok("status", "--explain", "sy-0100", cwd=q).output
    assert list(json_of("status", "--severity", "major", "--json", cwd=q)["keys"]) == [
        "sy-0003",
        "sy-0100",
    ]

    # it takes no acceptance row, and a section nobody annotated is structure rather than work
    refused("accept", "sy-0100", *AUTHOR, cwd=q, code=2, match="sy-0100 is not a statement or proof key")
    assert not any(ln.startswith("sy-0200 ") for ln in ok("status", cwd=q).output.splitlines())


def test_status_is_the_authors_to_do_list_not_the_literatures(tmp_path: Path) -> None:
    """A digest holds every result of a cited paper; relloc printed 150 rows of which 92 were Manolache's, and the summary counted his one `incomplete` and his 92 `loose` as the author's (F4, A3, A4)."""
    q = synthetic(tmp_path)
    # a result of the cited paper that nothing in this quilt uses, which is most of a real digest
    digest = q / "digests" / "Kre99.tex"
    digest.write_text(
        digest.read_text()
        + "\n\\begin{theorem}[{\\cite[Theorem 9.9, p.~40]{Kre99}}]\\label{Kre99-thm-9.9}\n"
        + "An unrelated result nobody here leans on.\n\\end{theorem}\n"
    )
    all_rows = json_of("status", "--include-digests", "--json", cwd=q)
    shown = json_of("status", "--json", cwd=q)

    external = {k for k in all_rows["keys"] if k.startswith("Kre99")}
    assert "Kre99-thm-9.9" in external
    kept = external & set(shown["keys"])
    assert kept and kept < external  # the ones the author's own arguments reach, and no more
    assert "Kre99-thm-9.9" not in kept and "Kre99-thm-2.1" in kept
    assert shown["digests"] == {"shown": len(kept), "reached": len(kept), "not_counted": len(external - kept)}

    # the summary counts the author's keys in both forms, so the flag changes the rows and never the arithmetic
    assert shown["summary"] == all_rows["summary"]
    assert all(not k.startswith("Kre99") for k in shown["summary"])  # it is a tally, not a key list
    line = ok("status", cwd=q).output.splitlines()[-1]
    assert f"{len(kept)} digest keys you depend on" in line
    assert f"{len(external - kept)} digest keys not counted" in line


def test_accept_refuses_a_digest_node_and_names_the_command_that_does_it(tmp_path: Path) -> None:
    """Two claims, two commands (plan 0.12 §5.6). `loom accept` is the author's own mathematics; someone else's theorem is not theirs to accept, and DR-172 relabelled the output where the command needed splitting."""
    q = synthetic(tmp_path)
    r = refused("accept", "Kre99-thm-2.1", *AUTHOR, cwd=q, code=2, match="not yours to accept")
    assert "loom refs verify Kre99-thm-2.1" in r.output

    # the author's own keys are untouched by any of it
    assert ok("accept", "sy-0002", *AUTHOR, cwd=q).output.startswith("accepted sy-0002")


def test_verifying_a_digest_node_says_what_it_claims(tmp_path: Path) -> None:
    """Verifying an external node claims loom's copy of the cited paper is faithful, never that this quilt proved the theorem; both printed `accepted` (H22)."""
    q = synthetic(tmp_path)
    # a digest extracted before the reference layer existed gains its records from one `refs build` (contract §1.4)
    ok("refs", "build", "--only", "extract", cwd=q)
    r = ok("refs", "verify", "Kre99-thm-2.1", "--author", "A. Author", "--yes", cwd=q)
    assert "verified Kre99-thm-2.1" in r.output
    assert "--- the source ---" in r.output, "a mechanical result's anchor is its LaTeX, and it says so"
    assert "as a faithful transcription of Kre99" in r.output

    line = the(
        ok("status", cwd=q).output.splitlines(), lambda ln: ln.startswith("Kre99-thm-2.1 "), "status row Kre99-thm-2.1"
    )
    assert "transcription verified" in line and "accepted" not in line

    # and what moved is the transcription, not the author's own text
    p = q / "digests" / "Kre99.tex"
    p.write_text(p.read_text().replace("is well defined", "is well-defined", 1))
    e = ok("status", "--explain", "Kre99-thm-2.1", cwd=q).output
    assert "transcription verified, stale" in e and "transcription-changed" in e
    assert "own-text-changed" not in e


def test_a_status_change_is_reversed_by_appending_its_undo(tmp_path: Path) -> None:
    """Discarding always replayed an `undo`; resolving did not, so a resolution was the one state nothing could take back — and `--resolve` is the verb a run can apply to its own finding (DR-174)."""
    d = demo(tmp_path)
    ann = ok("comment", "dm-0002", "Which orbits?", *AUTHOR, cwd=d).output.split()[0]

    assert ok("comment", "--resolve", ann, *AUTHOR, cwd=d).output.startswith("resolved")
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {}
    assert ok("comment", "--resolve", ann, "--undo", *AUTHOR, cwd=d).output.startswith("reopened")
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {"objection": 1}

    assert ok("comment", "--discard", ann, "raised in error", *AUTHOR, cwd=d).output.startswith("discarded")
    assert ok("comment", "--discard", ann, "--undo", *AUTHOR, cwd=d).output.startswith("reopened")
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {"objection": 1}

    # nothing was removed: every act is still in the log, undos included
    kinds = [e["event"] for e in events(d)]
    assert kinds == ["created", "resolved", "resolved", "discarded", "discarded"]
    assert [e.get("undo") for e in events(d)] == [None, None, True, None, True]

    refused(
        "comment", "--undo", *AUTHOR, cwd=d, code=2, match="--undo applies to --resolve or --discard"
    )  # --undo needs a verb to undo


def test_a_comment_on_an_equation_marks_its_display(tmp_path: Path) -> None:
    """A comment on a region key with no quote -- a box drawn round an equation -- marks the display itself, so the reader can click it; nothing is put inside the formula."""
    d = synthetic(tmp_path)
    sid, _ = session(d)
    ok("comment", "sy-0001#eq:fix", "The fixed locus wants a name.", "--session", sid, cwd=d, env=AGENT)
    ann = [e["id"] for e in events(d) if e["event"] == "created"][-1]
    exits(1, "build", cwd=d)
    frag = (d / "build" / "fragments" / "nodes" / "sy-0001.html").read_text()
    display = next(ln for ln in frag.split("<div") if 'data-label="eq:fix"' in ln)
    assert "annotation-block" in display and ann in display
    assert "<mark" not in display
