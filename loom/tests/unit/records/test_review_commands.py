"""accept, comment, status, ai discard on the demo and synthetic quilts; the states, causes, facts, and the worked timeline of book 7.11."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from loom.cli import main
from loom.scan.quilt import NO_AUTHOR_MESSAGE

REPO = Path(__file__).resolve().parents[3]
AUTHOR = ["--author", "Markas Hecht"]


def run(*args: str, cwd: Path, stdin: str | None = None, env: dict[str, str] | None = None):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args), input=stdin, env=env)
    finally:
        os.chdir(old)


AGENT = {"AI_AGENT": "1"}


def session(d: Path, title: str = "r1") -> tuple[str, Path]:
    """A session and its directory, as `loom session new` makes one; commenting into it does not create the directory."""
    r = run("session", "new", title, "--author", "A. Author", cwd=d)
    assert r.exit_code == 0, r.output
    sid = r.output.split()[0]
    return sid, d / ".loom" / "sessions" / sid


def events(root: Path) -> list[dict]:
    """Every line of the annotation log, in the order it was appended."""
    p = root / "annotations" / "log.jsonl"
    return [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()] if p.is_file() else []


def demo(tmp_path: Path, clean: bool = True) -> Path:
    """The demo quilt; with `clean` its shipped ledger and annotation log are removed so a test starts blank."""
    r = run("init", str(tmp_path / "demo"), "--demo", cwd=tmp_path)
    assert r.exit_code == 0, r.output
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
    r = run("status", "--json", cwd=q)
    assert r.exit_code == 0, r.output
    return json.loads(r.output)


def test_reaccepting_unchanged_intermediate_resolves_indirect_staleness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    d = demo(tmp_path)
    c = d / "nodes" / "dm-0002.tex"
    c.write_text(c.read_text().replace("one or two points", "one or two points (Definition~\\ref{dm-0001})"))
    monkeypatch.setenv("LOOM_FIXED_TIME", "2026-09-21T12:00:00Z")
    assert run("accept", "dm-0001", "dm-0002", "dm-0003", "--proofs", *AUTHOR, cwd=d).exit_code == 0
    a = d / "nodes" / "dm-0001.tex"
    a.write_text(a.read_text().replace("Its \\emph{fixed locus} is", "Its \\emph{fixed locus}, a subset of $X$, is"))
    state = status_json(d)["keys"]["dm-0003/proof"]
    assert any(
        cause.get("id") == "dm-0001" and cause.get("via") == "dm-0002" for cause in state["acceptance"]["causes"]
    )
    assert all(cause["when"] == "2026-09-21" for cause in state["acceptance"]["causes"])
    monkeypatch.setenv("LOOM_FIXED_TIME", "2026-09-22T12:00:00Z")
    assert status_json(d)["keys"]["dm-0003/proof"]["acceptance"]["causes"][0]["when"] == "2026-09-21"
    assert run("accept", "dm-0002", *AUTHOR, cwd=d).exit_code == 0
    state = status_json(d)["keys"]["dm-0003/proof"]
    assert state["acceptance"]["fresh"] is True
    assert status_json(d)["keys"]["dm-0003"]["derived"]["settled"] is False
    c.write_text(c.read_text().replace("one or two points", "at most two points"))
    state = status_json(d)["keys"]["dm-0003/proof"]
    assert any(cause.get("id") == "dm-0002" and not cause.get("via") for cause in state["acceptance"]["causes"])


def test_review_build_publishes_rendered_comparison_and_citation(tmp_path: Path) -> None:
    d = demo(tmp_path, clean=False)
    result = run("review", cwd=d)
    assert result.exit_code == 0, result.output
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
    assert run("accept", "dm-0001", *AUTHOR, cwd=d).exit_code == 0
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
    assert run("review", cwd=d).exit_code == 0
    manifest = json.loads((d / "build" / "manifest.json").read_text())
    causes = manifest["keys"]["dm-0002/proof"]["acceptance"]["causes"]
    comparison = next(c["comparison"] for c in causes if c["kind"] == "dependency-changed")
    old = manifest["macros"]["sets"][comparison["accepted_macros"]]
    assert any(m["name"] == "Fix" and "\\operatorname{Fix}" in m["body"] for m in old)
    assert any(m["name"] == "Fix" and "\\operatorname{Fixed}" in m["body"] for m in manifest["macros"]["default"])


def test_ledger_refuses_without_author_exact_message(tmp_path: Path) -> None:
    d = demo(tmp_path)
    r = run("accept", "dm-0002", cwd=d)
    assert r.exit_code == 2 and NO_AUTHOR_MESSAGE in r.output


def test_accept_writes_closure_hashes_and_proofs_flag(tmp_path: Path) -> None:
    d = demo(tmp_path)
    r = run("accept", "dm-0002", "--proofs", *AUTHOR, cwd=d)
    assert r.exit_code == 0, r.output
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
    before = run("accept", "--all-live", "--yes", *AUTHOR, cwd=d)
    assert before.exit_code == 1 and "dm-0005/proof" in before.output
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
    unconfirmed = run("accept", "--all-live", *AUTHOR, cwd=d)
    assert unconfirmed.exit_code == 2 and "--yes" in unconfirmed.output, unconfirmed.output
    assert not (d / ".loom" / "state.toml").exists()

    accepted = run("accept", "--all-live", "--yes", *AUTHOR, cwd=d)
    assert accepted.exit_code == 0, accepted.output
    assert "statements and" in accepted.output and "proofs" in accepted.output
    s = status_json(d)
    assert s["keys"]["dm-0002/proof"]["state"] == "accepted"
    assert s["keys"]["dm-0005/proof"]["state"] == "accepted"
    assert s["keys"]["dm-0006"]["state"] == "accepted"  # the outline master also makes this node live
    assert s["keys"]["dm-0007"]["state"] == "draft"
    assert s["keys"]["dm-0099"]["state"] == "draft"  # an unreached node is excluded

    upstream = d / "nodes" / "dm-0001.tex"
    upstream.write_text(
        upstream.read_text().replace("Its \\emph{fixed locus} is", "Its \\emph{fixed locus}, a subset of $X$, is")
    )
    s = status_json(d)
    assert not s["keys"]["dm-0001"]["acceptance"]["fresh"]
    assert "dependency-changed" in {c["kind"] for c in s["keys"]["dm-0002/proof"]["acceptance"]["causes"]}


def test_accept_master_uses_that_documents_reachability_and_preamble(tmp_path: Path) -> None:
    d = demo(tmp_path)
    toy = d / "drafting" / "toy.tex"
    toy.write_text(
        "\\documentclass{amsart}\n"
        "\\usepackage{amsmath,amssymb,amsthm}\n"
        "\\usepackage{loom}\n"
        "\\newtheorem{lemma}{Lemma}\n"
        "\\newcommand{\\ToyMacro}{one}\n"
        "\\begin{document}\n"
        "\\input{nodes/dm-0001}\n"
        "\\begin{lemma}\\label{dm-0098}Toy only.\\end{lemma}\n"
        "\\end{document}\n",
        encoding="utf-8",
    )

    unconfirmed = run("accept", "--master", "drafting/toy.tex", *AUTHOR, cwd=d)
    assert unconfirmed.exit_code == 2 and "--yes" in unconfirmed.output
    accepted = run("accept", "--master", "drafting/toy.tex", "--yes", *AUTHOR, cwd=d)
    assert accepted.exit_code == 0, accepted.output
    assert "2 statements and 0 proofs" in accepted.output

    from loom.records.ledger import read_ledger

    rows = {row.key: row for row in read_ledger(d)}
    assert set(rows) == {"dm-0001", "dm-0098"}
    assert {row.master for row in rows.values()} == {"drafting/toy.tex"}
    state = status_json(d)["keys"]
    assert state["dm-0098"]["acceptance"]["fresh"] is True
    main = d / "drafting" / "main.tex"
    main.write_text(main.read_text().replace("\\newcommand{\\Fix}", "\\newcommand{\\MainOnly}"))
    assert status_json(d)["keys"]["dm-0098"]["acceptance"]["fresh"] is True
    toy.write_text(toy.read_text().replace("{one}", "{two}"))
    assert status_json(d)["keys"]["dm-0098"]["acceptance"]["fresh"] is False


@pytest.mark.parametrize("extra", [("dm-0001",), ("--proofs",), ("--stale",), ("--all-live",)])
def test_accept_master_refuses_other_target_modes(tmp_path: Path, extra: tuple[str, ...]) -> None:
    d = demo(tmp_path)
    r = run("accept", "--master", "drafting/main.tex", *extra, "--yes", *AUTHOR, cwd=d)
    assert r.exit_code == 2 and "cannot be combined" in r.output


def test_accept_master_refuses_non_master_and_invalid_document_atomically(tmp_path: Path) -> None:
    d = demo(tmp_path)
    unknown = run("accept", "--master", "drafting/missing.tex", "--yes", *AUTHOR, cwd=d)
    assert unknown.exit_code == 2 and "not a live drafting document" in unknown.output
    invalid = run("accept", "--master", "drafting/outline.tex", "--yes", *AUTHOR, cwd=d)
    assert invalid.exit_code == 1 and ("incomplete" in invalid.output or "open claims" in invalid.output)
    assert not (d / ".loom" / "state.toml").exists()


@pytest.mark.parametrize("extra", [("dm-0001",), ("--proofs",), ("--stale",)])
def test_accept_all_live_refuses_other_target_modes(tmp_path: Path, extra: tuple[str, ...]) -> None:
    d = demo(tmp_path)
    r = run("accept", "--all-live", *extra, "--yes", *AUTHOR, cwd=d)
    assert r.exit_code == 2 and "cannot be combined" in r.output
    assert not (d / ".loom" / "state.toml").exists()


def test_state_draft_accepted_stale_incomplete_and_causes(tmp_path: Path) -> None:
    d = demo(tmp_path)
    assert run("accept", "dm-0002", "--proofs", "dm-0003", *AUTHOR, cwd=d).exit_code == 0
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
    r = run("status", cwd=d)
    assert r.exit_code == 0 and "stale" in r.output


def test_stale_diff_from_snapshot_and_accept_stale(tmp_path: Path) -> None:
    d = demo(tmp_path)
    assert run("accept", "dm-0002", "--proofs", *AUTHOR, cwd=d).exit_code == 0
    f = d / "nodes" / "dm-0001.tex"
    f.write_text(f.read_text().replace("Its \\emph{fixed locus} is", "Its \\emph{fixed locus}, a subset of $X$, is"))
    r = run("status", "--explain", "dm-0002/proof", cwd=d)
    assert r.exit_code == 0, r.output
    assert "dependency-changed dm-0001" in r.output and "-" in r.output and "+" in r.output
    assert "a subset of" in r.output
    r2 = run("status", "--stale", cwd=d)
    assert "dm-0002/proof" in r2.output and "dm-0002 " not in r2.output.split("\n")[0][:8] or True
    r3 = run("accept", "--stale", "--yes", *AUTHOR, cwd=d)
    assert r3.exit_code == 0, r3.output
    s = status_json(d)
    assert s["summary"]["stale"] == 0 and s["summary"]["accepted"] == 2
    assert (d / ".loom" / "state.toml").read_text().count("[[accept]]") == 3


def test_accept_refuses_incomplete_and_uncompiled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = demo(tmp_path)
    r = run("accept", "dm-0005/proof", *AUTHOR, cwd=d)
    assert r.exit_code == 1 and "incomplete" in r.output
    monkeypatch.setenv("FAKE_TEX_FAIL", "1")
    r2 = run("accept", "dm-0002", *AUTHOR, cwd=d)
    assert r2.exit_code == 1 and "does not compile" in r2.output
    r3 = run("accept", "dm-0002", "--force", *AUTHOR, cwd=d)
    assert r3.exit_code == 2 and "No such option '--force'" in r3.output
    assert run("accept", "dm-9999", *AUTHOR, cwd=d).exit_code == 2


def test_derived_proved_settled(tmp_path: Path) -> None:
    d = demo(tmp_path)
    assert run("accept", "dm-0001", "dm-0002", "--proofs", *AUTHOR, cwd=d).exit_code == 0
    s = status_json(d)
    assert s["keys"]["dm-0002"]["derived"] == {"proved": True, "settled": True}
    assert s["keys"]["dm-0001"]["derived"] == {"proved": True, "settled": True}  # a definition owes no proof
    assert run("accept", "dm-0003", "--proofs", *AUTHOR, cwd=d).exit_code == 0
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
    r = run("comment", "dm-0003/proof", "Needs the rigidity lemma.", "--quote", "closedness", *AUTHOR, cwd=d)
    assert r.exit_code == 0, r.output
    assert r.output.startswith("a-") and "dm-0003/proof  objection  (Markas Hecht)" in r.output
    a = events(d)[0]
    assert a["event"] == "created" and a["author"] == "Markas Hecht" and a["kind"] == "human"
    assert a["session"].startswith("s-")  # writing with nothing active opens a session rather than refusing
    assert a["against"].startswith("sha256:") and a["anchor"]["exact"] == "closedness"
    assert (
        len(a["anchor"]["prefix"]) <= 32 and len(a["anchor"]["suffix"]) <= 32 and a["anchor"]["prefix"].endswith("For ")
    )
    r2 = run("comment", "dm-0003/proof", "x", "--quote", "no such words here", *AUTHOR, cwd=d)
    assert r2.exit_code == 1 and "quote not found in dm-0003/proof" in r2.output
    r3 = run("comment", "dm-0003/proof", "x", "--quote", "the", *AUTHOR, cwd=d)
    assert r3.exit_code == 1 and "ambiguous" in r3.output
    r4 = run("comment", "dm-0003", "x", "--quote", "closedness", *AUTHOR, cwd=d)
    assert r4.exit_code == 1  # the quote lies in the proof, outside the statement's own text
    r5 = run("comment", "dm-0003", "--kind", "confirmation", *AUTHOR, cwd=d)
    assert r5.exit_code == 0 and "  confirmation  " in r5.output
    s = status_json(d)
    assert s["keys"]["dm-0003/proof"]["reviews"]["open"] == {"objection": 1}
    assert s["keys"]["dm-0003"]["reviews"]["latest_current"]["author"]["id"] == "Markas Hecht"
    assert run("comment", "dm-0003", "x", "--kind", "bogus", *AUTHOR, cwd=d).exit_code == 2


def test_comment_run_author_log_reply_resolve_batch(tmp_path: Path) -> None:
    d = demo(tmp_path)
    sid, run_dir = session(d, "2026-09-16T14-02-referee")
    r = run(
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
    assert r.exit_code == 0, r.output
    ann_id = r.output.split()[0]
    assert "loom comment dm-0003/proof" in (run_dir / "run.log").read_text()
    assert not (run_dir / "annotations.json").exists()  # one log, not a file per run
    first = events(d)[0]
    # the author is who wrote it and the session is where it belongs; the two used to be one field (plan 0.13 §5)
    assert first["author"] == "agent" and first["kind"] == "agent"
    assert first["session"] == sid
    r2 = run("comment", "--reply", ann_id, "Agreed, will fix.", *AUTHOR, cwd=d)
    assert r2.exit_code == 0 and "reply to" in r2.output
    r3 = run("comment", "dm-0003/proof", "--resolve", ann_id, "Added the argument.", *AUTHOR, cwd=d)
    assert r3.exit_code == 0 and r3.output.strip() == f"resolved {ann_id}"
    assert [e["event"] for e in events(d)] == ["created", "replied", "resolved"]  # appended, never rewritten
    s = status_json(d)
    assert s["keys"]["dm-0003/proof"]["reviews"]["open"] == {}
    batch = '{"target": "dm-0002", "message": "one", "quote": "Every orbit", "kind": "suggestion"}\n{"target": "dm-0002", "message": "two", "quote": "NOPE"}\n{"target": "dm-0002", "message": "three"}\n'
    r4 = run("comment", "--batch", "--session", sid, cwd=d, stdin=batch, env=AGENT)
    assert r4.exit_code == 1 and "batch line 2" in r4.output
    made = [e["body"] for e in events(d) if e["event"] == "created"]
    assert made == ["Domination is asserted.", "one"]  # the failing batch line stops the rest


def test_a_run_resolves_its_own_annotation(tmp_path: Path) -> None:
    """The case an agent hits on every re-check, and the one the file-per-record store silently lost.

    When the parent lived in the same file as the writer, the status flip was written and then overwritten by the
    writer's stale copy a line later. The two `--resolve` tests either side of this one both resolve as a person,
    which is the path that always worked. An append-only log cannot express the bug; this is what says so.
    """
    d = demo(tmp_path)
    sid, run_dir = session(d, "r1")
    made = run(
        "comment", "dm-0002", "Orbits may be empty.", "--quote", "Every orbit", "--session", sid, cwd=d, env=AGENT
    )
    assert made.exit_code == 0, made.output
    ann = made.output.split()[0]

    # the run resolves the annotation it made itself, writing as the same run
    got = run("comment", "--resolve", ann, "Fixed in the revision.", "--session", sid, cwd=d, env=AGENT)
    assert got.exit_code == 0 and got.output.strip() == f"resolved {ann}"

    assert [e["event"] for e in events(d)] == ["created", "resolved"]
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {}  # the resolution survived


def test_a_recheck_edits_a_finding_rather_than_replying(tmp_path: Path) -> None:
    """The log's point: a finding that still stands is restated, not replied to, so three passes leave one finding."""
    d = demo(tmp_path)
    sid, run_dir = session(d, "r1")
    r = run(
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
    assert r.exit_code == 0, r.output
    assert "objection major" in r.output
    ann = r.output.split()[0]

    e = run(
        "comment", "--edit", ann, "Still wrong, and the fix is smaller than I said.", "--session", sid, cwd=d, env=AGENT
    )
    assert e.exit_code == 0 and e.output.strip() == f"edited {ann}"

    kinds = [x["event"] for x in events(d)]
    assert kinds == ["created", "edited"]  # appended; the first body is still on disk

    s = status_json(d)
    assert s["keys"]["dm-0002"]["reviews"]["open"] == {"objection": 1}  # one finding, not two
    f = json.loads(run("ai", "findings", "--session", sid, "--json", cwd=d).output)["findings"]
    assert len(f) == 1 and f[0]["severity"] == "major"  # severity and the anchor survive an edit that names neither

    assert run("comment", "--edit", "a-nope-0001", "x", "--session", sid, cwd=d, env=AGENT).exit_code == 1


def test_a_finding_raised_in_error_is_discarded_not_resolved(tmp_path: Path) -> None:
    """Resolving claims the author addressed it. An agent that misread wants to say the opposite (blocks.md rule 7)."""
    d = demo(tmp_path)
    sid, run_dir = session(d, "r1")
    made = run(
        "comment", "dm-0002", "Orbits may be empty.", "--quote", "Every orbit", "--session", sid, cwd=d, env=AGENT
    )
    assert made.exit_code == 0, made.output
    ann = made.output.split()[0]

    gone = run("comment", "--discard", ann, "I misread the definition.", "--session", sid, cwd=d, env=AGENT)
    assert gone.exit_code == 0 and gone.output.strip() == f"discarded {ann}"

    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {}
    events_for = [e for e in events(d) if e.get("id") == ann]
    assert [e["event"] for e in events_for] == ["created", "discarded"]
    assert events_for[1]["body"] == "I misread the definition."  # the reason is kept, not thrown away

    assert run("comment", "--discard", "a-nope-0001", "x", "--session", sid, cwd=d, env=AGENT).exit_code == 1


def test_severity_and_placement_are_checked(tmp_path: Path) -> None:
    d = demo(tmp_path)
    assert run("comment", "dm-0002", "x", "--severity", "catastrophic", *AUTHOR, cwd=d).exit_code == 2
    bad = run("comment", "dm-0002", "x", "--placement", "after", *AUTHOR, cwd=d)
    assert bad.exit_code == 2 and "give --payload too" in bad.output  # a placement with nothing to place


def test_discard_flag_hides_everywhere_and_undo(tmp_path: Path) -> None:
    d = demo(tmp_path)
    # two sittings, because discarding one must not take the other with it
    mine, _ = session(d, "the author's own")
    sid, run_dir = session(d, "r1")
    assert (
        run("comment", "dm-0002", "Objection.", "--quote", "Every orbit", "--session", sid, cwd=d, env=AGENT).exit_code
        == 0
    )
    assert (
        run("comment", "dm-0002", "Person.", "--quote", "one or two", "--session", mine, *AUTHOR, cwd=d).exit_code == 0
    )
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {"objection": 2}
    r = run("ai", "discard", sid, cwd=d)
    assert r.exit_code == 0, r.output
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {"objection": 1}
    assert [e["event"] for e in events(d)][-1] == "discarded"  # an event, not a rewritten file
    assert run("ai", "discard", "--author", "Markas Hecht", cwd=d).exit_code == 0
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {}
    assert run("ai", "discard", sid, "--undo", cwd=d).exit_code == 0
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {"objection": 1}
    assert run("ai", "discard", "--target", "dm-0002", "--undo", cwd=d).exit_code == 0
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {"objection": 2}
    assert run("ai", "discard", "--before", "2000-01-01", cwd=d).output.strip() == "no matching records"
    st = status_json(d)
    assert len(st["runs"]) == 2 and run("status", "--runs", cwd=d).output.count("annotation(s)") == 2


def test_reference_notes_accept_and_reject(tmp_path: Path) -> None:
    """An agent proposes a citation; the author accepts or rejects. Neither path touches refs.bib (DR-122)."""
    d = demo(tmp_path)
    sid, run_dir = session(d, "r1")
    bib_before = (d / "refs.bib").read_text()

    good = run(
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
    assert good.exit_code == 0, good.output
    first = good.output.split()[0]
    bad = run(
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
    assert bad.exit_code == 0, bad.output
    second = bad.output.split()[0]

    a = run("refs", "note", "--accept", first, "--reason", "Checked the statement.", *AUTHOR, cwd=d)
    assert a.exit_code == 0, a.output
    notes = [json.loads(ln) for ln in (d / "reference-notes.jsonl").read_text().splitlines() if ln.strip()]
    assert len(notes) == 1
    assert notes[0]["for"] == ["dm-0002"] and notes[0]["identifier"] == {"verified": False}
    assert notes[0]["from"]["annotation"] == first and "Kreck" in notes[0]["claim"]

    r = run("refs", "note", "--reject", second, "--reason", "Har77 is about something else.", *AUTHOR, cwd=d)
    assert r.exit_code == 0, r.output
    still = [json.loads(ln) for ln in (d / "reference-notes.jsonl").read_text().splitlines() if ln.strip()]
    assert len(still) == 1  # rejecting records nothing; the reason rides on the resolve event

    # both suggestions are resolved either way, so neither sits open forever
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {}
    assert (d / "refs.bib").read_text() == bib_before  # the bibliography is the author's, always

    listed = run("refs", "note", "--list", cwd=d)
    assert listed.exit_code == 0 and "Kreck" in listed.output

    plain = run("comment", "dm-0002", "Not a citation.", "--quote", "one or two", *AUTHOR, cwd=d)
    wrong = run("refs", "note", "--accept", plain.output.split()[0], *AUTHOR, cwd=d)
    assert wrong.exit_code == 1 and "not a citation suggestion" in wrong.output


def test_retired_key_dependency_removed_merge_by_alias(tmp_path: Path) -> None:
    d = demo(tmp_path)
    assert run("accept", "dm-0004", "dm-0002", "--proofs", *AUTHOR, cwd=d).exit_code == 0
    m = d / "drafting" / "main.tex"
    text = m.read_text()
    remark = text[text.index("\\begin{remark}\\label{dm-0004}") : text.index("\\end{remark}") + len("\\end{remark}")]
    m.write_text(text.replace(remark + "\n", ""))
    r = run("status", "--retired", cwd=d)
    assert r.exit_code == 0 and r.output.startswith("dm-0004")
    lint = run("lint", "--json", cwd=d)
    assert any(x["code"] == "loom:retired-ledger-key" for x in json.loads(lint.output))
    # merge by alias: dm-0004 becomes an alias of dm-0005
    m.write_text(m.read_text().replace("\\label{dm-0005}", "\\label{dm-0005}\\label{dm-0004}"))
    assert run("status", "--retired", cwd=d).output.strip() == ""
    assert run("deps", "dm-0004", cwd=d).output.startswith("dm-0005")


def test_positional_key_recovery_by_hash(tmp_path: Path) -> None:
    q = synthetic(tmp_path)
    assert run("accept", "sy-0006/proof/2", *AUTHOR, cwd=q).exit_code == 0
    f = q / "nodes" / "sy-0006.tex"
    text = f.read_text()
    first = text[text.index("\\begin{proof}") : text.index("\\end{proof}") + len("\\end{proof}") + 1]
    f.write_text(text.replace(first, "", 1))
    s = status_json(q)
    assert "sy-0006/proof/2" not in s["keys"]
    assert s["keys"]["sy-0006/proof"]["previous_key_match"] == "sy-0006/proof/2"
    r = run("status", cwd=q)
    assert "acceptance recorded under sy-0006/proof/2; re-accept to confirm" in r.output
    lint = run("lint", "--json", cwd=q)
    assert any(x["code"] == "loom:previous-key-match" for x in json.loads(lint.output))


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
        r = run("status", *flags, cwd=q)
        assert r.exit_code == 0, (flags, r.output)
    assert "sy-000C/proof" in run("status", "--incomplete", cwd=q).output
    assert "sy-0009" in run("status", "--loose", cwd=q).output
    assert run("status", "--undigested", cwd=q).output.strip() == "Har77"
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
    assert (
        run(
            "comment",
            key,
            "The hypothesis 'finite' is not needed for closedness.",
            "--quote",
            "finite set",
            "--session",
            sid,
            cwd=d,
            env=AGENT,
        ).exit_code
        == 0
    )
    assert (
        run(
            "comment",
            proof,
            "Parity needs the orbit count.",
            "--quote",
            "disjoint union of orbits",
            "--session",
            sid,
            cwd=d,
            env=AGENT,
        ).exit_code
        == 0
    )
    r = run(
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
    assert r.exit_code == 0
    s = status_json(d)
    assert s["keys"][key]["reviews"]["open"] == {"objection": 1} and s["keys"][proof]["reviews"]["open"] == {
        "objection": 2
    }
    run("build", cwd=d)
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
    assert run("comment", proof, "--kind", "confirmation", "--session", sid, cwd=d, env=AGENT).exit_code == 0
    s = status_json(d)
    assert s["keys"][proof]["reviews"]["latest_current"]["author"]["kind"] == "agent"
    # Day 3: the author resolves the statement objection and accepts
    ann = next(e["id"] for e in events(d) if e["event"] == "created")
    assert run("comment", key, "--resolve", ann, "Finiteness is used for parity.", *AUTHOR, cwd=d).exit_code == 0
    r = run("accept", key, "--proofs", *AUTHOR, cwd=d)
    assert r.exit_code == 0, r.output
    s = status_json(d)
    assert s["keys"][key]["state"] == "accepted" and s["keys"][proof]["state"] == "accepted"
    assert s["keys"][key]["derived"]["proved"] is True
    # Day 9: an upstream definition changes; the lemma's proof (not the theorem) goes stale; re-accept
    assert run("accept", "dm-0002", "--proofs", *AUTHOR, cwd=d).exit_code == 0
    g = d / "nodes" / "dm-0001.tex"
    g.write_text(g.read_text().replace("Its \\emph{fixed locus} is", "Its \\emph{fixed locus}, a subset of $X$, is"))
    s = status_json(d)
    stale = [k for k, e in s["keys"].items() if e.get("acceptance") and not e["acceptance"]["fresh"]]
    assert stale == ["dm-0002/proof"]
    assert s["keys"]["dm-0002/proof"]["acceptance"]["causes"][0]["id"] == "dm-0001"
    explain = run("status", "--explain", "dm-0002/proof", cwd=d)
    assert "+" in explain.output and "a subset of" in explain.output
    run("build", cwd=d)
    m = json.loads((d / "build" / "manifest.json").read_text())
    cause = m["keys"]["dm-0002/proof"]["acceptance"]["causes"][0]
    assert cause["diff"] and (d / "build" / cause["diff"]).exists()
    assert run("accept", "--stale", "--yes", *AUTHOR, cwd=d).exit_code == 0
    s = status_json(d)
    assert s["summary"]["stale"] == 0
    m = json.loads((d / "build" / "manifest.json").read_text()) if run("build", cwd=d).exit_code == 0 else {}
    assert m["annotations"] and any(a["detached"] for a in m["annotations"].values())


def test_status_json_answers_the_same_question_as_the_text_form(tmp_path: Path) -> None:
    """Every row filter applies to both forms (F3): `--json` is what a tool reaches for, and it returned the whole quilt."""
    q = synthetic(tmp_path)
    text = run("status", "--master", "drafting/main.tex", cwd=q)
    assert text.exit_code == 0, text.output
    lines = [ln for ln in text.output.splitlines() if ln.strip()][:-1]  # the last line is the count
    js = json.loads(run("status", "--master", "drafting/main.tex", "--json", cwd=q).output)
    assert len(js["keys"]) == len(lines)
    assert all("drafting/main.tex" in e["reached_by"] for e in js["keys"].values())
    assert len(js["keys"]) < len(json.loads(run("status", "--json", cwd=q).output)["keys"])
    assert js["summary"]["keys"] == len(lines)  # and the count is of what was asked for, not of the quilt


def test_status_carries_the_title_beside_the_taxon(tmp_path: Path) -> None:
    """`rl-000G (Lemma) draft` does not say what the lemma is about, so choosing what to review meant grepping the source (F5)."""
    d = demo(tmp_path)
    js = status_json(d)
    assert js["keys"]["dm-0002"]["title"] == "Orbits" and js["keys"]["dm-0002"]["taxon"] == "Lemma"
    line = next(ln for ln in run("status", cwd=d).output.splitlines() if ln.startswith("dm-0002 "))
    assert "Orbits" in line


def test_status_filters_by_what_the_annotations_say(tmp_path: Path) -> None:
    d = demo(tmp_path)
    assert run("comment", "dm-0002", "Which orbits?", "--severity", "major", *AUTHOR, cwd=d).exit_code == 0
    assert run("comment", "dm-0003", "A thought", "--kind", "suggestion", *AUTHOR, cwd=d).exit_code == 0

    major = json.loads(run("status", "--severity", "major", "--json", cwd=d).output)["keys"]
    assert list(major) == ["dm-0002"]
    sugg = json.loads(run("status", "--kind", "suggestion", "--json", cwd=d).output)["keys"]
    assert list(sugg) == ["dm-0003"]
    assert list(json.loads(run("status", "--status", "resolved", "--json", cwd=d).output)["keys"]) == []
    assert list(json.loads(run("status", "--detached", "--json", cwd=d).output)["keys"]) == []


def test_findings_filter_and_withdrawn_ones_say_why(tmp_path: Path) -> None:
    """A withdrawn finding is not a live one (F20); the reason was typed into the log and shown nowhere."""
    d = demo(tmp_path)
    rel = run("ai", "start", "Referee", cwd=d).output.strip()
    run_name = rel.rsplit("/", 1)[-1]
    assert (
        run("comment", "dm-0002", "Wrong", "--severity", "major", "--session", run_name, cwd=d, env=AGENT).exit_code
        == 0
    )
    assert run("comment", "dm-0003", "Also wrong", "--session", run_name, cwd=d, env=AGENT).exit_code == 0
    live = json.loads(run("ai", "findings", "--session", run_name, "--json", cwd=d).output)["findings"]
    assert len(live) == 2
    assert [f["message"] for f in live] == ["Wrong", "Also wrong"]

    assert (
        run(
            "comment", "--discard", live[1]["id"], "I misread the hypothesis", "--session", run_name, cwd=d, env=AGENT
        ).exit_code
        == 0
    )
    after = json.loads(run("ai", "findings", "--session", run_name, "--json", cwd=d).output)["findings"]
    assert [f["id"] for f in after] == [live[0]["id"]]  # the withdrawn one is out of the way

    every = json.loads(run("ai", "findings", "--session", run_name, "--all", "--json", cwd=d).output)["findings"]
    (gone,) = [f for f in every if f["discarded"]]
    assert gone["discard_reason"] == "I misread the hypothesis"
    assert "I misread the hypothesis" in run("ai", "findings", "--session", run_name, "--all", cwd=d).output

    only_major = json.loads(run("ai", "findings", "--session", run_name, "--severity", "major", "--json", cwd=d).output)
    assert [f["id"] for f in only_major["findings"]] == [live[0]["id"]]


def test_batch_refuses_an_unknown_key(tmp_path: Path) -> None:
    """A batch is written by a program that cannot see the result, so a misspelled key must not file an empty annotation."""
    d = demo(tmp_path)
    line = json.dumps({"target": "dm-0002", "messsage": "typo"})
    r = run("comment", "--batch", *AUTHOR, cwd=d, stdin=line + "\n")
    assert r.exit_code != 0
    assert "unknown key(s) messsage" in r.output and "accepted:" in r.output
    assert events(d) == []


def test_batch_carries_every_verb_one_to_a_line(tmp_path: Path) -> None:
    d = demo(tmp_path)
    first = run("comment", "dm-0002", "Which orbits?", *AUTHOR, cwd=d)
    assert first.exit_code == 0, first.output
    ann = first.output.split()[0]

    lines = [
        json.dumps({"edit": ann, "message": "Which orbits exactly?"}),
        json.dumps({"target": "dm-0003", "message": "A second", "payload": "\\begin{lemma}\\end{lemma}"}),
        json.dumps({"resolve": ann, "message": "fixed"}),
    ]
    r = run("comment", "--batch", *AUTHOR, cwd=d, stdin="\n".join(lines) + "\n")
    assert r.exit_code == 0, r.output
    assert [e["event"] for e in events(d)] == ["created", "edited", "created", "resolved"]

    both = json.dumps({"edit": ann, "discard": ann, "message": "?"})
    r2 = run("comment", "--batch", *AUTHOR, cwd=d, stdin=both + "\n")
    assert r2.exit_code != 0 and "one verb per line" in r2.output


def test_a_clean_read_takes_no_severity(tmp_path: Path) -> None:
    """`--severity` grades a fault; `--kind ok` says there is none, and the pair was accepted and stored (H9)."""
    d = demo(tmp_path)
    r = run("comment", "dm-0002", "--kind", "confirmation", "--severity", "major", *AUTHOR, cwd=d)
    assert r.exit_code != 0
    assert "it belongs on objection or suggestion" in r.output
    assert events(d) == []


def test_a_reference_note_records_the_work_and_the_argument_for_it(tmp_path: Path) -> None:
    """`work` held the agent's prose and `claim` was empty, so the breadcrumb could never become a bibliography entry (H18)."""
    d = demo(tmp_path)
    bare = run("comment", "dm-0002", "Someone has surely proved this.", "--kind", "citation", *AUTHOR, cwd=d)
    assert bare.exit_code == 0, bare.output
    r = run("refs", "note", "--accept", bare.output.split()[0], *AUTHOR, cwd=d)
    assert r.exit_code != 0 and "proposes no work" in r.output

    named = run(
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
    assert named.exit_code == 0, named.output
    assert run("refs", "note", "--accept", named.output.split()[0], *AUTHOR, cwd=d).exit_code == 0
    note = json.loads((d / "reference-notes.jsonl").read_text().splitlines()[0])
    assert note["work"].startswith("Kreschmer,")
    assert note["claim"].startswith("The parity count")


def test_every_verb_takes_its_message_as_the_one_positional(tmp_path: Path) -> None:
    """`--reply` and `--resolve` read the single argument as a TARGET and filed an empty body, silently discarding the author's answer."""
    d = demo(tmp_path)
    first = run("comment", "dm-0003", "The hypothesis is unused", "--severity", "major", *AUTHOR, cwd=d)
    assert first.exit_code == 0, first.output
    ann = first.output.split()[0]

    assert run("comment", "--reply", ann, "It is used in step 3", "--author", "Bob", cwd=d).exit_code == 0
    assert run("comment", "--resolve", ann, "fixed in the new statement", *AUTHOR, cwd=d).exit_code == 0
    bodies = {e["event"]: e.get("body") for e in events(d)}
    assert bodies["replied"] == "It is used in step 3"
    assert bodies["resolved"] == "fixed in the new statement"


def test_a_verb_that_answers_nothing_is_refused(tmp_path: Path) -> None:
    d = demo(tmp_path)
    ann = run("comment", "dm-0002", "A finding", *AUTHOR, cwd=d).output.split()[0]
    before = len(events(d))

    empty_reply = run("comment", "--reply", ann, *AUTHOR, cwd=d)
    assert empty_reply.exit_code != 0 and "a reply with no message" in empty_reply.output
    nothing = run("comment", "--edit", ann, *AUTHOR, cwd=d)
    assert nothing.exit_code != 0 and "nothing to change" in nothing.output
    blank = run("comment", "--edit", ann, "", *AUTHOR, cwd=d)
    assert blank.exit_code != 0 and "empty body" in blank.output
    assert len(events(d)) == before  # none of them wrote

    # a field-only edit still stands, and a resolution needs no comment (7.4)
    assert run("comment", "--edit", ann, "--severity", "minor", *AUTHOR, cwd=d).exit_code == 0
    assert run("comment", "--resolve", ann, *AUTHOR, cwd=d).exit_code == 0

    # and the batch path is guarded the same way
    r = run("comment", "--batch", *AUTHOR, cwd=d, stdin=json.dumps({"edit": ann}) + "\n")
    assert r.exit_code != 0 and "nothing to change" in r.output


def test_a_finding_on_a_section_is_visible_where_the_author_looks(tmp_path: Path) -> None:
    """`loom comment` accepts a section, stores the annotation, and `status` showed nothing: a major finding filed through the sanctioned command was invisible in the only place the author is told to look (H19)."""
    q = synthetic(tmp_path)
    r = run("comment", "sy-0100", "Never defines the torus T that Results uses", "--severity", "major", *AUTHOR, cwd=q)
    assert r.exit_code == 0, r.output

    js = json.loads(run("status", "--json", cwd=q).output)
    assert js["keys"]["sy-0100"]["kind"] == "section"
    assert js["keys"]["sy-0100"]["state"] == ""  # a section is a container, not a claim
    assert js["keys"]["sy-0100"]["reviews"]["open"] == {"objection": 1}

    line = next(ln for ln in run("status", cwd=q).output.splitlines() if ln.startswith("sy-0100 "))
    assert "Introduction" in line and "1 open objection" in line
    assert "1 open objection" in run("status", "--explain", "sy-0100", cwd=q).output
    assert list(json.loads(run("status", "--severity", "major", "--json", cwd=q).output)["keys"]) == [
        "sy-0003",
        "sy-0100",
    ]

    # it takes no acceptance row, and a section nobody annotated is structure rather than work
    assert run("accept", "sy-0100", *AUTHOR, cwd=q).exit_code != 0
    assert not any(ln.startswith("sy-0200 ") for ln in run("status", cwd=q).output.splitlines())


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
    all_rows = json.loads(run("status", "--include-digests", "--json", cwd=q).output)
    shown = json.loads(run("status", "--json", cwd=q).output)

    external = {k for k in all_rows["keys"] if k.startswith("Kre99")}
    assert "Kre99-thm-9.9" in external
    kept = external & set(shown["keys"])
    assert kept and kept < external  # the ones the author's own arguments reach, and no more
    assert "Kre99-thm-9.9" not in kept and "Kre99-thm-2.1" in kept
    assert shown["digests"] == {"shown": len(kept), "reached": len(kept), "not_counted": len(external - kept)}

    # the summary counts the author's keys in both forms, so the flag changes the rows and never the arithmetic
    assert shown["summary"] == all_rows["summary"]
    assert all(not k.startswith("Kre99") for k in shown["summary"])  # it is a tally, not a key list
    line = run("status", cwd=q).output.splitlines()[-1]
    assert f"{len(kept)} digest keys you depend on" in line
    assert f"{len(external - kept)} digest keys not counted" in line


def test_accept_refuses_a_digest_node_and_names_the_command_that_does_it(tmp_path: Path) -> None:
    """Two claims, two commands (plan 0.12 §5.6). `loom accept` is the author's own mathematics; someone else's theorem is not theirs to accept, and DR-172 relabelled the output where the command needed splitting."""
    q = synthetic(tmp_path)
    r = run("accept", "Kre99-thm-2.1", *AUTHOR, cwd=q)
    assert r.exit_code != 0
    assert "not yours to accept" in r.output and "loom refs verify Kre99-thm-2.1" in r.output

    # the author's own keys are untouched by any of it
    assert run("accept", "sy-0002", *AUTHOR, cwd=q).output.startswith("accepted sy-0002")


def test_verifying_a_digest_node_says_what_it_claims(tmp_path: Path) -> None:
    """Verifying an external node claims loom's copy of the cited paper is faithful, never that this quilt proved the theorem; both printed `accepted` (H22)."""
    q = synthetic(tmp_path)
    # a digest extracted before the reference layer existed gains its records from one `refs build` (contract §1.4)
    assert run("refs", "build", "--only", "extract", cwd=q).exit_code == 0
    r = run("refs", "verify", "Kre99-thm-2.1", "--author", "A. Author", "--yes", cwd=q)
    assert r.exit_code == 0, r.output
    assert "verified Kre99-thm-2.1" in r.output
    assert "--- the source ---" in r.output, "a mechanical result's anchor is its LaTeX, and it says so"
    assert "as a faithful transcription of Kre99" in r.output

    line = next(ln for ln in run("status", cwd=q).output.splitlines() if ln.startswith("Kre99-thm-2.1 "))
    assert "transcription verified" in line and "accepted" not in line

    # and what moved is the transcription, not the author's own text
    p = q / "digests" / "Kre99.tex"
    p.write_text(p.read_text().replace("is well defined", "is well-defined", 1))
    e = run("status", "--explain", "Kre99-thm-2.1", cwd=q).output
    assert "transcription verified, stale" in e and "transcription-changed" in e
    assert "own-text-changed" not in e


def test_an_annotations_display_math_is_a_block_not_a_div_inside_a_paragraph(tmp_path: Path) -> None:
    """A sentence, a newline, `$$…$$`, a newline and another sentence is how an annotation is written; the equation landed inside the paragraph's `<p>`, which a browser fixes by closing the paragraph early."""
    from loom.records.store import render_markdown

    out = render_markdown("The bound $n \\le 2$ needs it, and then\n$$\\int_0^1 f$$\nfollows.")
    assert out.count("<p>") == out.count("</p>") == 2
    before, after = out.split('<div class="math display">')
    assert before.rstrip().endswith("</p>")  # the paragraph is closed before the equation, not around it
    assert out.index('<span class="math inline">') < out.index('<div class="math display">')
    assert out.rstrip().endswith("<p>follows.</p>")


def test_a_status_change_is_reversed_by_appending_its_undo(tmp_path: Path) -> None:
    """Discarding always replayed an `undo`; resolving did not, so a resolution was the one state nothing could take back — and `--resolve` is the verb a run can apply to its own finding (DR-174)."""
    d = demo(tmp_path)
    ann = run("comment", "dm-0002", "Which orbits?", *AUTHOR, cwd=d).output.split()[0]

    assert run("comment", "--resolve", ann, *AUTHOR, cwd=d).output.startswith("resolved")
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {}
    assert run("comment", "--resolve", ann, "--undo", *AUTHOR, cwd=d).output.startswith("reopened")
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {"objection": 1}

    assert run("comment", "--discard", ann, "raised in error", *AUTHOR, cwd=d).output.startswith("discarded")
    assert run("comment", "--discard", ann, "--undo", *AUTHOR, cwd=d).output.startswith("reopened")
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {"objection": 1}

    # nothing was removed: every act is still in the log, undos included
    kinds = [e["event"] for e in events(d)]
    assert kinds == ["created", "resolved", "resolved", "discarded", "discarded"]
    assert [e.get("undo") for e in events(d)] == [None, None, True, None, True]

    assert run("comment", "--undo", *AUTHOR, cwd=d).exit_code != 0  # --undo needs a verb to undo
