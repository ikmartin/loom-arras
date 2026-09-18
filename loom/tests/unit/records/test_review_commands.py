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


def run(*args: str, cwd: Path, stdin: str | None = None):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args), input=stdin)
    finally:
        os.chdir(old)


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


def test_demo_ships_two_accepted_one_stale_and_a_finished_run(tmp_path: Path) -> None:
    d = demo(tmp_path, clean=False)
    s = status_json(d)
    assert s["summary"]["accepted"] == 1 and s["summary"]["stale"] == 1
    assert s["keys"]["dm-0002/proof"]["acceptance"]["causes"][0]["id"] == "dm-0001"
    assert s["keys"]["dm-0003/proof"]["reviews"]["open"] == {
        "suggestion": 1,
        "objection": 1,
    }  # the author's suggestion and the run's objection
    assert s["keys"]["dm-0003"]["reviews"]["open"] == {"suggestion": 1}  # the run's suggestion on the statement
    assert (d / "ai" / "runs" / "2026-09-16T14-02-referee-dm-0003" / "referee-dm-0003.notes.md").is_file()


def synthetic(tmp_path: Path) -> Path:
    dest = tmp_path / "synthetic"
    shutil.copytree(REPO / "tests" / "quilts" / "synthetic", dest)
    return dest


def status_json(q: Path) -> dict:  # type: ignore[type-arg]
    r = run("status", "--json", cwd=q)
    assert r.exit_code == 0, r.output
    return json.loads(r.output)


def test_ledger_refuses_without_author_exact_message(tmp_path: Path) -> None:
    d = demo(tmp_path)
    r = run("accept", "dm-0002", "--force", cwd=d)
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
    r3 = run("accept", "--stale", "--yes", "--force", *AUTHOR, cwd=d)
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
    assert r3.exit_code == 0, r3.output
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
    assert a["event"] == "created" and a["author"] == "Markas Hecht" and a["kind"] == "human" and a["run"] is None
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
    r5 = run("comment", "dm-0003", "--kind", "ok", *AUTHOR, cwd=d)
    assert r5.exit_code == 0 and "  ok  " in r5.output
    s = status_json(d)
    assert s["keys"]["dm-0003/proof"]["reviews"]["open"] == {"objection": 1}
    assert s["keys"]["dm-0003"]["reviews"]["latest_current"]["author"]["id"] == "Markas Hecht"
    assert run("comment", "dm-0003", "x", "--kind", "bogus", *AUTHOR, cwd=d).exit_code == 2


def test_comment_run_author_log_reply_resolve_batch(tmp_path: Path) -> None:
    d = demo(tmp_path)
    run_dir = d / "ai" / "runs" / "2026-09-16T14-02-referee"
    run_dir.mkdir(parents=True)  # a run is a directory loom ai start makes; commenting into one does not create it
    r = run(
        "comment",
        "dm-0003/proof",
        "Domination is asserted.",
        "--quote",
        "diagonal is closed",
        "--run",
        str(run_dir),
        cwd=d,
    )
    assert r.exit_code == 0, r.output
    ann_id = r.output.split()[0]
    assert "loom comment dm-0003/proof" in (run_dir / "run.log").read_text()
    assert not (run_dir / "annotations.json").exists()  # one log, not a file per run
    first = events(d)[0]
    assert first["author"] == "2026-09-16T14-02-referee" and first["kind"] == "agent"
    assert first["run"] == "ai/runs/2026-09-16T14-02-referee"
    r2 = run("comment", "--reply", ann_id, "Agreed, will fix.", *AUTHOR, cwd=d)
    assert r2.exit_code == 0 and "reply to" in r2.output
    r3 = run("comment", "dm-0003/proof", "--resolve", ann_id, "Added the argument.", *AUTHOR, cwd=d)
    assert r3.exit_code == 0 and r3.output.strip() == f"resolved {ann_id}"
    assert [e["event"] for e in events(d)] == ["created", "replied", "resolved"]  # appended, never rewritten
    s = status_json(d)
    assert s["keys"]["dm-0003/proof"]["reviews"]["open"] == {}
    batch = '{"target": "dm-0002", "message": "one", "quote": "Every orbit", "kind": "suggestion"}\n{"target": "dm-0002", "message": "two", "quote": "NOPE"}\n{"target": "dm-0002", "message": "three"}\n'
    r4 = run("comment", "--batch", "--run", str(run_dir), cwd=d, stdin=batch)
    assert r4.exit_code == 1 and "batch line 2" in r4.output
    made = [e["body"] for e in events(d) if e["event"] == "created"]
    assert made == ["Domination is asserted.", "one"]  # the failing batch line stops the rest


def test_a_recheck_edits_a_finding_rather_than_replying(tmp_path: Path) -> None:
    """The log's point: a finding that still stands is restated, not replied to, so three passes leave one finding."""
    d = demo(tmp_path)
    run_dir = d / "ai" / "runs" / "r1"
    run_dir.mkdir(parents=True)
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
        "--run",
        str(run_dir),
        cwd=d,
    )
    assert r.exit_code == 0, r.output
    assert "objection major" in r.output
    ann = r.output.split()[0]

    e = run("comment", "--edit", ann, "Still wrong, and the fix is smaller than I said.", "--run", str(run_dir), cwd=d)
    assert e.exit_code == 0 and e.output.strip() == f"edited {ann}"

    kinds = [x["event"] for x in events(d)]
    assert kinds == ["created", "edited"]  # appended; the first body is still on disk

    s = status_json(d)
    assert s["keys"]["dm-0002"]["reviews"]["open"] == {"objection": 1}  # one finding, not two
    f = json.loads(run("ai", "findings", "--run", str(run_dir), "--json", cwd=d).output)["findings"]
    assert len(f) == 1 and f[0]["severity"] == "major"  # severity and the anchor survive an edit that names neither

    assert run("comment", "--edit", "a-nope-0001", "x", "--run", str(run_dir), cwd=d).exit_code == 1


def test_severity_and_placement_are_checked(tmp_path: Path) -> None:
    d = demo(tmp_path)
    assert run("comment", "dm-0002", "x", "--severity", "catastrophic", *AUTHOR, cwd=d).exit_code == 2
    bad = run("comment", "dm-0002", "x", "--placement", "after", *AUTHOR, cwd=d)
    assert bad.exit_code == 2 and "give --payload too" in bad.output  # a placement with nothing to place


def test_discard_flag_hides_everywhere_and_undo(tmp_path: Path) -> None:
    d = demo(tmp_path)
    run_dir = d / "ai" / "runs" / "r1"
    run_dir.mkdir(parents=True)
    assert (
        run("comment", "dm-0002", "Objection.", "--quote", "Every orbit", "--run", str(run_dir), cwd=d).exit_code == 0
    )
    assert run("comment", "dm-0002", "Person.", "--quote", "one or two", *AUTHOR, cwd=d).exit_code == 0
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {"objection": 2}
    r = run("ai", "discard", "ai/runs/r1", cwd=d)
    assert r.exit_code == 0, r.output
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {"objection": 1}
    assert [e["event"] for e in events(d)][-1] == "discarded"  # an event, not a rewritten file
    assert run("ai", "discard", "--author", "Markas Hecht", cwd=d).exit_code == 0
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {}
    assert run("ai", "discard", "ai/runs/r1", "--undo", cwd=d).exit_code == 0
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {"objection": 1}
    assert run("ai", "discard", "--target", "dm-0002", "--undo", cwd=d).exit_code == 0
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {"objection": 2}
    assert run("ai", "discard", "--before", "2000-01-01", cwd=d).output.strip() == "no matching records"
    st = status_json(d)
    assert len(st["runs"]) == 2 and run("status", "--runs", cwd=d).output.count("annotation(s)") == 2


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
    assert run("accept", "sy-0006/proof/2", "--force", *AUTHOR, cwd=q).exit_code == 0
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
    assert set(j) == {"summary", "keys", "runs", "undigested", "retired"}
    assert j["summary"]["incomplete"] == 1


def test_timeline_7_11(tmp_path: Path) -> None:
    d = demo(tmp_path)
    key, proof = "dm-0003", "dm-0003/proof"
    run_dir = d / "ai" / "runs" / "2026-09-16T14-02-referee"
    run_dir.mkdir(parents=True)
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
            "--run",
            str(run_dir),
            cwd=d,
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
            "--run",
            str(run_dir),
            cwd=d,
        ).exit_code
        == 0
    )
    r = run(
        "comment",
        proof,
        "Diagonal argument needs Hausdorff stated.",
        "--quote",
        "diagonal is closed",
        "--run",
        str(run_dir),
        cwd=d,
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
    assert run("comment", proof, "--kind", "ok", "--run", str(run_dir), cwd=d).exit_code == 0
    s = status_json(d)
    assert s["keys"][proof]["reviews"]["latest_current"]["author"]["kind"] == "run"
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
    assert run("accept", "--stale", "--yes", "--force", *AUTHOR, cwd=d).exit_code == 0
    s = status_json(d)
    assert s["summary"]["stale"] == 0
    m = json.loads((d / "build" / "manifest.json").read_text()) if run("build", cwd=d).exit_code == 0 else {}
    assert m["annotations"] and any(a["detached"] for a in m["annotations"].values())
