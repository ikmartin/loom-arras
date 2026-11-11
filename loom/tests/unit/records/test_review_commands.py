"""accept, comment, status, ai delete on the demo and synthetic quilts; the states, causes, facts, and a worked timeline."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from loom.scan.quilt import NO_AUTHOR_MESSAGE
from tests.helpers import edit, exits, flat, json_of, ok, refused, the

REPO = Path(__file__).resolve().parents[3]
AUTHOR = ["--author", "Markas Hecht"]
AS = ["--as", "Markas Hecht"]


@pytest.fixture(autouse=True)
def local_reviewer(request):
    from loom.scan.quilt import save_author

    if request.node.name != "test_ledger_refuses_without_author_exact_message":
        save_author("Markas Hecht")


AGENT = {"AI_AGENT": "1"}


def session(d: Path, title: str = "r1") -> tuple[str, Path]:
    """A session and its directory, as `loom session new` makes one; commenting into it does not create the directory."""
    r = ok("session", "new", "--name", title, "--as", "A. Author", cwd=d)
    sid = r.output.split()[0]
    return sid, d / ".loom" / "sessions" / sid


def events(root: Path) -> list[dict]:
    """Every line of the annotation log, in the order it was appended."""
    p = root / ".loom/annotations" / "log.jsonl"
    return [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()] if p.is_file() else []


def demo(tmp_path: Path, clean: bool = True) -> Path:
    """The demo quilt; with `clean` its shipped ledger and annotation log are removed so a test starts blank."""
    ok("init", str(tmp_path / "demo"), "--demo", cwd=tmp_path)
    d = tmp_path / "demo"
    if clean:
        shutil.rmtree(d / ".loom", ignore_errors=True)
        shutil.rmtree(d / ".loom/annotations", ignore_errors=True)
    return d


def test_demo_ships_two_accepted_one_stale_and_a_finished_session(tmp_path: Path) -> None:
    d = demo(tmp_path, clean=False)
    from loom.scan.quilt import save_author

    save_author("The loom demo")
    s = status_json(d)
    assert s["summary"]["accepted"] == 1 and s["summary"]["stale"] == 1
    assert s["keys"]["dm-0002/proof"]["acceptance"]["causes"][0]["id"] == "equation:eq:fix"
    assert s["keys"]["dm-0003/proof"]["reviews"]["open"] == {
        "suggestion": 1,
        "revision": 1,
    }  # the author's suggestion and the agent's revision
    assert s["keys"]["dm-0003"]["reviews"]["open"] == {"suggestion": 1}  # the agent's suggestion on the statement
    reports = [
        p for p in (d / ".loom" / "sessions").glob("*/inbox.jsonl") if "Mode: referee, on dm-0003." in p.read_text()
    ]
    assert len(reports) == 1, "the session the agent worked in keeps its report, in its transcript"


def synthetic(tmp_path: Path) -> Path:
    dest = tmp_path / "synthetic"
    shutil.copytree(REPO / "tests" / "quilts" / "synthetic", dest)
    return dest


def status_json(q: Path) -> dict:  # type: ignore[type-arg]
    return json_of("status", "--json", cwd=q)


#: A status row: indented once under its group's heading, unlike a row's wrapped tail or a group's `fix:` line.
ROW = re.compile(r"^  (?!fix: |next: )\S")


def status_rows(output: str) -> list[tuple[str, str]]:
    """Each row of `loom status` as (its group's heading, its text), a wrapped row joined back into one line; every row ends with its key."""
    rows: list[tuple[str, str]] = []
    heading = ""
    for ln in output.splitlines():
        if ln and not ln.startswith(" "):
            heading = ln
        elif ROW.match(ln):
            rows.append((heading, ln.strip()))
        elif ln.startswith("    ") and not ln.lstrip().startswith(("fix: ", "next: ")) and rows:
            rows[-1] = (rows[-1][0], rows[-1][1] + " " + ln.strip())
    return rows


def status_row(output: str, key: str) -> str:
    """The status row of `key`, prefixed by the heading of the group it is in."""
    heading, text = the(status_rows(output), lambda r: r[1].split()[-1:] == [key], f"status row {key}")
    return f"{heading}: {text}"


def test_reaccepting_unchanged_intermediate_resolves_indirect_staleness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    d = demo(tmp_path)
    c = d / "drafting" / "nodes" / "dm-0002.tex"
    c.write_text(c.read_text().replace("one or two points", "one or two points (Definition~\\ref{dm-0001})"))
    monkeypatch.setenv("LOOM_FIXED_TIME", "2026-09-21T12:00:00Z")
    ok("accept", "dm-0001", "dm-0002", "dm-0003", "--proofs", "--force", *AS, cwd=d)
    a = d / "drafting" / "nodes" / "dm-0001.tex"
    a.write_text(a.read_text().replace("Its \\emph{fixed locus} is", "Its \\emph{fixed locus}, a subset of $X$, is"))
    state = status_json(d)["keys"]["dm-0003/proof"]
    assert any(
        cause.get("id") == "dm-0001" and cause.get("via") == "dm-0002" for cause in state["acceptance"]["causes"]
    )
    assert all(cause["when"] == "2026-09-21" for cause in state["acceptance"]["causes"])
    monkeypatch.setenv("LOOM_FIXED_TIME", "2026-09-22T12:00:00Z")
    assert status_json(d)["keys"]["dm-0003/proof"]["acceptance"]["causes"][0]["when"] == "2026-09-21"
    ok("accept", "dm-0002", "--force", *AS, cwd=d)
    state = status_json(d)["keys"]["dm-0003/proof"]
    assert state["acceptance"]["fresh"] is True
    assert status_json(d)["keys"]["dm-0003"]["derived"]["settled"] is False
    c.write_text(c.read_text().replace("one or two points", "at most two points"))
    state = status_json(d)["keys"]["dm-0003/proof"]
    assert any(cause.get("id") == "dm-0002" and not cause.get("via") for cause in state["acceptance"]["causes"])


def test_build_publishes_rendered_comparison_and_citation(tmp_path: Path) -> None:
    d = demo(tmp_path, clean=False)
    from loom.scan.quilt import save_author

    save_author("The loom demo")
    ok("build", cwd=d)
    manifest = json.loads((d / ".loom/build" / "manifest.json").read_text())
    cause = manifest["keys"]["dm-0002/proof"]["acceptance"]["causes"][0]
    comparison = cause["comparison"]
    assert cause["citation"] in (d / ".loom/build" / manifest["masters"][0]["fragment"]).read_text()
    accepted_html = (d / ".loom/build" / comparison["accepted"]).read_text()
    current_html = (d / ".loom/build" / comparison["current"]).read_text()
    assert "sigma" in accepted_html
    assert "sigma" in current_html
    assert "review-changed" in accepted_html + current_html
    assert '<p class="review-changed"' not in accepted_html + current_html
    assert comparison["accepted_spans"] and comparison["current_spans"]


def test_observation_date_resets_after_a_cause_disappears(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = demo(tmp_path)
    ok("accept", "dm-0001", "--force", *AS, cwd=d)
    node = d / "drafting" / "nodes" / "dm-0001.tex"
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
    from loom.scan.quilt import save_author

    save_author("The loom demo")
    master = d / "drafting" / "main.tex"
    master.write_text(master.read_text().replace("\\operatorname{Fix}", "\\operatorname{Fixed}"))
    ok("build", cwd=d)
    manifest = json.loads((d / ".loom/build" / "manifest.json").read_text())
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
    r = ok("accept", "dm-0002", "--proofs", *AS, cwd=d)
    assert r.output.splitlines()[0] == "accepted dm-0002 and dm-0002/proof as Markas Hecht"
    ledger = (d / ".loom" / "state.toml").read_text()
    assert ledger.count("[[accept]]") == 2 and 'author = "Markas Hecht"' in ledger
    from loom.records.ledger import read_ledger

    rows = {r.key: r for r in read_ledger(d)}
    assert set(rows["dm-0002/proof"].closure) == {"equation:eq:fix", "dm-0002"}
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
    (d / "drafting" / "nodes" / "dm-0099.tex").write_text("\\begin{lemma}\\label{dm-0099}Loose.\\end{lemma}\n")
    refused("accept", "--all-live", "--yes", "--force", *AS, cwd=d, code=1, match="dm-0005/proof")
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
    candidate = d / "drafting" / "nodes" / "dm-0006.tex"
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
    refused("accept", "--all-live", "--force", *AS, cwd=d, code=2, match="--yes")
    assert not (d / ".loom" / "state.toml").exists()

    accepted = ok("accept", "--all-live", "--yes", "--force", *AS, cwd=d)
    assert "statements and" in accepted.output and "proofs" in accepted.output
    s = status_json(d)
    assert s["keys"]["dm-0002/proof"]["state"] == "accepted"
    assert s["keys"]["dm-0005/proof"]["state"] == "accepted"
    assert s["keys"]["dm-0006"]["state"] == "accepted"  # the outline master also makes this node live
    assert s["keys"]["dm-0007"]["state"] == "draft"
    assert s["keys"]["dm-0099"]["state"] == "draft"  # an unreached node is excluded


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

    refused("accept", "--master", "drafting/toy.tex", *AS, cwd=d, code=2, match="--yes")
    accepted = ok("accept", "--master", "drafting/toy.tex", "--yes", "--force", *AS, cwd=d)
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
    refused("accept", "--master", "drafting/main.tex", *extra, "--yes", *AS, cwd=d, code=2, match="cannot be combined")


def test_accept_master_refuses_non_master_and_invalid_document_atomically(tmp_path: Path) -> None:
    d = demo(tmp_path)
    refused(
        "accept",
        "--master",
        "drafting/missing.tex",
        "--yes",
        *AS,
        cwd=d,
        code=2,
        match="not a live document of yours",
    )
    refused(
        "accept",
        "--master",
        "drafting/outline.tex",
        "--yes",
        *AS,
        cwd=d,
        code=1,
        match="live incomplete keys prevent --master drafting/outline.tex",
    )
    assert not (d / ".loom" / "state.toml").exists()


@pytest.mark.parametrize("extra", [("dm-0001",), ("--proofs",), ("--stale",)])
def test_accept_all_live_refuses_other_target_modes(tmp_path: Path, extra: tuple[str, ...]) -> None:
    d = demo(tmp_path)
    refused("accept", "--all-live", *extra, "--yes", "--force", *AS, cwd=d, code=2, match="cannot be combined")
    assert not (d / ".loom" / "state.toml").exists()


def test_state_draft_accepted_stale_incomplete_and_causes(tmp_path: Path) -> None:
    d = demo(tmp_path)
    ok("accept", "dm-0002", "--proofs", "dm-0003", *AS, cwd=d)
    s = status_json(d)
    assert s["keys"]["dm-0005/proof"]["state"] == "incomplete"
    assert s["keys"]["dm-0001"]["state"] == "draft"
    # dependency-changed: edit the definition the proof cites through \eqref
    f = d / "drafting" / "nodes" / "dm-0001.tex"
    f.write_text(f.read_text().replace(r"\sigma x = x", r"\sigma(x) = x"))
    s = status_json(d)
    proof = s["keys"]["dm-0002/proof"]
    assert proof["state"] == "accepted" and proof["acceptance"]["fresh"] is False
    assert [c["kind"] + " " + c.get("id", "") for c in proof["acceptance"]["causes"]] == [
        "dependency-changed equation:eq:fix"
    ]
    assert s["keys"]["dm-0002"]["acceptance"]["fresh"] is True
    # own-text-changed
    g = d / "drafting" / "nodes" / "dm-0002.tex"
    g.write_text(g.read_text().replace("one or two points", "at most two points"))
    s = status_json(d)
    assert "own-text-changed" in [c["kind"] for c in s["keys"]["dm-0002"]["acceptance"]["causes"]]
    # dependency-added: the theorem's statement now references the definition
    h = d / "drafting" / "nodes" / "dm-0003.tex"
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
    row = status_row(ok("status", cwd=d).output, "dm-0002/proof")
    assert row.startswith("stale (") and "equation eq:fix is no longer available" in row, row
    assert "\\ref" not in row and "-removed" not in row  # the reader's words, not the cause's code (T4)


def test_status_stale_lists_the_stale_rows_and_accept_stale_reaccepts_them(tmp_path: Path) -> None:
    """`--stale` lists the stale proof and not its fresh statement; `accept --stale` re-accepts exactly those rows, appending one ledger row to the two already there."""
    d = demo(tmp_path)
    ok("accept", "dm-0002", "--proofs", *AS, cwd=d)
    edit(d / "drafting" / "nodes" / "dm-0001.tex", r"\sigma x = x", r"\sigma(x) = x")
    listed = ok("status", "--stale", cwd=d).output.splitlines()
    assert listed[0] == "1 key of yours match: 1 stale", listed  # the first line is the summary
    assert [text.split()[-1] for _, text in status_rows("\n".join(listed))] == ["dm-0002/proof"], listed
    ok("accept", "--stale", "--yes", "--force", *AS, cwd=d)
    s = status_json(d)
    assert s["summary"]["stale"] == 0 and s["summary"]["accepted"] == 2
    assert (d / ".loom" / "state.toml").read_text().count("[[accept]]") == 3


def test_accept_refuses_incomplete_and_uncompiled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = demo(tmp_path)
    refused("accept", "dm-0005/proof", *AS, cwd=d, code=1, match="incomplete")
    monkeypatch.setenv("FAKE_TEX_FAIL", "1")
    refused("accept", "dm-0002", *AS, cwd=d, code=1, match="does not compile")
    ok("accept", "dm-0002", "--force", *AS, cwd=d)
    refused("accept", "dm-9999", *AS, cwd=d, code=2, match="no such key: dm-9999")


def test_derived_proved_settled(tmp_path: Path) -> None:
    d = demo(tmp_path)
    ok("accept", "dm-0001", "dm-0002", "--proofs", *AS, cwd=d)
    s = status_json(d)
    assert s["keys"]["dm-0002"]["derived"] == {"proved": True, "settled": True}
    assert s["keys"]["dm-0001"]["derived"] == {"proved": True, "settled": True}  # a definition owes no proof
    ok("accept", "dm-0003", "--proofs", *AS, cwd=d)
    s = status_json(d)
    assert s["keys"]["dm-0003"]["derived"] == {
        "proved": True,
        "settled": True,
    }  # its proof's closure, dm-0002 and dm-0001, is settled
    f = d / "drafting" / "nodes" / "dm-0001.tex"
    f.write_text(f.read_text() + "\n% touched\n")
    s = status_json(d)
    assert s["keys"]["dm-0001"]["derived"]["proved"]  # comments do not change the hash


def test_comment_quote_rules_and_records(tmp_path: Path) -> None:
    d = demo(tmp_path)
    r = ok(
        "annotate",
        "dm-0003/proof",
        "Needs the rigidity lemma.",
        "--quote",
        "closedness",
        "--type",
        "revision",
        *AS,
        cwd=d,
    )
    assert r.output.startswith("a-") and "dm-0003/proof  revision  (Markas Hecht)" in r.output
    a = events(d)[0]
    # the type it names, nothing set on it, and the whole look it is drawn with should the type go
    assert (a["type"], a["look"], a["drawn"]) == (
        "revision",
        {},
        {"color": "red", "style": "highlight", "weight": 2, "opacity": 65},
    )
    assert a["event"] == "created" and a["author"] == "Markas Hecht" and a["kind"] == "human"
    assert "session" not in a and not (d / ".loom/sessions").exists()  # writing opens no session
    assert a["against"].startswith("sha256:") and a["anchor"]["exact"] == "closedness"
    assert (
        len(a["anchor"]["prefix"]) <= 32 and len(a["anchor"]["suffix"]) <= 32 and a["anchor"]["prefix"].endswith("For ")
    )
    refused(
        "annotate",
        "dm-0003/proof",
        "x",
        "--quote",
        "no such words here",
        *AS,
        cwd=d,
        code=2,
        match="quote not found in dm-0003/proof; `loom source dm-0003/proof` prints its text",
    )
    refused("annotate", "dm-0003/proof", "x", "--quote", "the", *AS, cwd=d, code=2, match="ambiguous")
    # the quote lies in the proof, outside the statement's own text
    refused("annotate", "dm-0003", "x", "--quote", "closedness", *AS, cwd=d, code=2, match="quote not found in dm-0003")
    r5 = ok("annotate", "dm-0003", "Read; fine.", "--type", "note", *AS, cwd=d)
    assert "  note  " in r5.output
    s = status_json(d)
    assert s["keys"]["dm-0003/proof"]["reviews"]["open"] == {"revision": 1}
    assert s["keys"]["dm-0003"]["reviews"]["open"] == {}  # a note only informs, so it is never open
    refused(
        "annotate",
        "dm-0003",
        "x",
        "--type",
        "bogus",
        *AS,
        cwd=d,
        code=2,
        match="no type 'bogus' in this quilt; its types are",
    )


def test_comment_run_author_log_reply_resolve(tmp_path: Path) -> None:
    """An annotation carries who wrote it, when, and the version it was written on, and belongs to no session; a reply and a resolution each take their message as the one positional, and file it as the body rather than reading it as a target."""
    d = demo(tmp_path)
    sid, run_dir = session(d, "2026-09-16T14-02-referee")
    r = ok(
        "annotate",
        "dm-0003/proof",
        "Domination is asserted.",
        "--quote",
        "diagonal is closed",
        "--type",
        "revision",
        "--as",
        "agent",
        cwd=d,
        env=AGENT,
    )
    ann_id = r.output.split()[0]
    # nothing of it is the session's: no line in its command log, and no session on the event, however one is active
    assert not (run_dir / "run.log").exists() or "loom annotate" not in (run_dir / "run.log").read_text()
    first = events(d)[0]
    assert first["author"] == "agent" and first["kind"] == "agent"
    assert "session" not in first and first["when"] and first["against"].startswith("sha256:")
    refused("annotate", "dm-0003", "x", "--session", sid, *AS, cwd=d, code=2, match="No such option '--session'")
    r2 = ok("annotate", "--reply", ann_id, "Agreed, will fix.", "--as", "Bob", cwd=d)
    assert "reply to" in r2.output
    r3 = ok("annotate", "--resolve", ann_id, "Added the argument.", *AS, cwd=d)
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
    made = ok(
        "annotate",
        "dm-0002",
        "Orbits may be empty.",
        "--quote",
        "Every orbit",
        "--type",
        "revision",
        "--as",
        "agent",
        cwd=d,
        env=AGENT,
    )
    ann = made.output.split()[0]

    # the run resolves the annotation it made itself, writing as the same run
    got = ok("annotate", "--resolve", ann, "Fixed in the revision.", "--as", "agent", cwd=d, env=AGENT)
    assert got.output.strip() == f"resolved {ann}"

    assert [e["event"] for e in events(d)] == ["created", "resolved"]
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {}  # the resolution survived


def test_a_recheck_edits_a_finding_rather_than_replying(tmp_path: Path) -> None:
    """The log's point: a finding that still stands is restated, not replied to, so three passes leave one finding."""
    d = demo(tmp_path)
    r = ok(
        "annotate",
        "dm-0002",
        "Orbits may be empty.",
        "--quote",
        "Every orbit",
        "--type",
        "revision",
        "--as",
        "agent",
        cwd=d,
        env=AGENT,
    )
    assert "  revision  " in r.output
    ann = r.output.split()[0]

    e = ok(
        "annotate",
        "--edit",
        ann,
        "Still wrong, and the fix is smaller than I said.",
        "--as",
        "agent",
        cwd=d,
        env=AGENT,
    )
    assert e.output.strip() == f"edited {ann}"

    kinds = [x["event"] for x in events(d)]
    assert kinds == ["created", "edited"]  # appended; the first body is still on disk

    s = status_json(d)
    assert s["keys"]["dm-0002"]["reviews"]["open"] == {"revision": 1}  # one finding, not two
    f = json_of("ai", "annotations", "--by", "agent", "--json", cwd=d)["annotations"]
    assert len(f) == 1 and f[0]["type"] == "revision"  # the type and the anchor survive an edit that names neither

    refused(
        "annotate",
        "--edit",
        "a-nope-0001",
        "x",
        "--as",
        "agent",
        cwd=d,
        env=AGENT,
        code=2,
        match="no annotation a-nope-0001",
    )


def test_an_annotation_is_deleted_with_its_replies_and_an_agent_deletes_only_its_own(tmp_path: Path) -> None:
    """Resolving claims the author addressed it; an agent that misread deletes what it raised instead (rules.md item 7), and nothing of it stays in the log."""
    d = demo(tmp_path)
    as_agent = ("--as", "agent")
    made = ok(
        "annotate", "dm-0002", "Orbits may be empty.", "--quote", "Every orbit", "--type", "revision", *as_agent,
        cwd=d, env=AGENT,
    )  # fmt: skip
    ann = made.output.split()[0]
    reply = ok("annotate", "--reply", ann, "Are they?", *AS, cwd=d).output.split()[0]
    ok("annotate", "--reply", reply, "No: I misread the definition.", *as_agent, cwd=d, env=AGENT)
    mine = ok("annotate", "dm-0003", "Which set?", "--type", "question", *AS, cwd=d).output.split()[0]
    theirs = ok(
        "annotate", "dm-0003", "A gap.", "--type", "revision", "--as", "Other Agent", cwd=d, env=AGENT
    ).output.split()[0]

    # an agent deletes only what it wrote: neither the person's nor another agent's
    for other in (mine, theirs):
        r = refused("annotate", "--delete", other, *as_agent, cwd=d, env=AGENT, code=2, match="an agent deletes only")
        assert "its own annotations" in flat(r.output)
    before = events(d)
    dry = ok("annotate", "--delete", ann, "--dry-run", *as_agent, cwd=d, env=AGENT).output
    assert dry.startswith("dry run:") and f"delete {ann}" in dry
    assert events(d) == before

    gone = ok("annotate", "--delete", ann, *as_agent, cwd=d, env=AGENT)
    assert gone.output.strip() == f"deleted {ann} and 2 replies to it"
    assert not [e for e in events(d) if ann in (e.get("id"), e.get("reply_to")) or e.get("reply_to") == reply]
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {}
    # nothing is left of it, so a second deletion finds nothing, and an agent deleting its own tells nobody
    refused("annotate", "--delete", ann, *as_agent, cwd=d, env=AGENT, code=2, match=f"no annotation {ann}")
    assert not (d / ".loom/since" / "deleted.jsonl").exists()

    # a person deletes anyone's
    assert ok("annotate", "--delete", theirs, *AS, cwd=d).output.strip() == f"deleted {theirs}"
    assert [e["id"] for e in events(d)] == [mine]
    # what is left is still a log that reads, and the history still verifies
    from loom.records.log import replay

    assert replay(d)[1] == []
    ok("history", "verify", cwd=d)


def test_status_never_says_a_key_was_reviewed_clean(tmp_path: Path) -> None:
    """Plan 0.30, decision 6: a highlight with nothing said, a note, or a revision resolved says nothing about whether a key was reviewed, so status never claims it was (P15)."""
    d = demo(tmp_path)
    ok("annotate", "dm-0002", "--quote", "Every orbit", *AS, cwd=d)
    ok("annotate", "dm-0003", "Read through.", "--type", "note", *AS, cwd=d)
    gap = ok("annotate", "dm-0006", "A gap.", "--type", "revision", *AS, cwd=d).output.split()[0]
    ok("annotate", "--resolve", gap, "Closed.", *AS, cwd=d)
    for args in (("status",), ("status", "--json"), ("status", "--reading")):
        out = ok(*args, cwd=d).output
        assert "reviewed clean" not in out and "reviewed_clean" not in out, args
    assert all(
        not row["reviews"]["open"]
        for key, row in status_json(d)["keys"].items()
        if key in ("dm-0002", "dm-0003", "dm-0006")
    )


def test_a_deletion_takes_no_message(tmp_path: Path) -> None:
    """A deletion leaves nothing to carry a reason, so words given with it are refused rather than dropped without a word."""
    d = demo(tmp_path)
    ann = ok("annotate", "dm-0002", "A finding", "--type", "revision", *AS, cwd=d).output.split()[0]
    refused("annotate", "--delete", ann, "I misread it.", *AS, cwd=d, code=2, match="give the id alone")
    assert [e["id"] for e in events(d)] == [ann]


def test_the_look_is_checked_and_an_annotation_carries_no_proposed_text(tmp_path: Path) -> None:
    d = demo(tmp_path)
    refused("annotate", "dm-0002", "x", "--color", "mauve", *AS, cwd=d, code=2, match="Invalid value for '--color'")
    refused("annotate", "dm-0002", "x", "--weight", "6", *AS, cwd=d, code=2, match="Invalid value for '--weight'")
    refused("annotate", "dm-0002", "x", "--opacity", "101", *AS, cwd=d, code=2, match="Invalid value for '--opacity'")
    # proposed text is a suggested edit of its own (`loom suggest`)
    for flag in ("--payload", "--placement", "--applied"):
        refused("annotate", "dm-0002", "x", flag, "y", *AS, cwd=d, code=2, match=f"No such option '{flag}'")
    # what is set on an annotation is drawn over its type's look
    ok("annotate", "dm-0002", "x", "--type", "question", "--color", "green", "--style", "strike", *AS, cwd=d)
    a = events(d)[-1]
    assert (a["type"], a["look"]) == ("question", {"color": "green", "style": "strike"})
    assert a["drawn"] == {"color": "green", "style": "strike", "weight": 2, "opacity": 60}


def test_ai_delete_takes_what_every_filter_names_and_nothing_else(tmp_path: Path) -> None:
    """`loom ai delete` is the person's bulk delete: every filter given must hold, replies go with what they answer, and with nobody at a terminal it asks for --yes."""
    d = demo(tmp_path)
    agents = ok(
        "annotate", "dm-0002", "Objection.", "--quote", "Every orbit", "--type", "revision",
        "--as", "agent", cwd=d, env=AGENT,
    ).output.split()[0]  # fmt: skip
    ok("annotate", "--reply", agents, "Fair.", *AS, cwd=d)
    person = ok(
        "annotate", "dm-0002", "Person.", "--quote", "one or two", "--type", "revision", *AS, cwd=d
    ).output.split()[0]
    elsewhere = ok("annotate", "dm-0003", "Elsewhere.", "--type", "question", *AS, cwd=d).output.split()[0]
    before = events(d)

    refused("ai", "delete", *AS, cwd=d, code=2, match="give --by, --target, --before or --version")
    # a word that is no date is refused, not compared as text, where it would sort after every date
    refused("ai", "delete", "--before", "yesterday", "--yes", *AS, cwd=d, code=2, match="yesterday")
    refused("ai", "delete", "--target", "dm-9999", "--yes", *AS, cwd=d, code=2, match="dm-9999")
    refused("ai", "delete", "--by", "agent", *AS, cwd=d, code=2, match="--yes deletes them")
    refused("ai", "delete", "--by", "agent", "--yes", "--as", "agent", cwd=d, env=AGENT, code=2, match="the author's")
    assert events(d) == before

    planned = json_of("ai", "delete", "--by", "Markas Hecht", "--target", "dm-0002", "--dry-run", "--json", cwd=d)
    assert planned["deleted"] == [person] and events(d) == before
    assert json_of("ai", "delete", "--before", "2000-01-01", "--yes", "--json", *AS, cwd=d)["deleted"] == []
    assert events(d) == before

    # both filters hold: the person's on dm-0002, not the person's on dm-0003
    ok("ai", "delete", "--by", "Markas Hecht", "--target", "dm-0002", "--yes", *AS, cwd=d)
    assert {e["id"] for e in events(d) if e["event"] == "created"} == {agents, elsewhere}
    # by the version it was written on, with the reply that answers it
    version = the(events(d), lambda e: e.get("id") == agents, "the agent's")["against"]
    ok("ai", "delete", "--version", version, "--yes", *AS, cwd=d)
    assert [e["id"] for e in events(d)] == [elsewhere]
    # the agent hears of it once, from its next `loom since`
    told = [json.loads(x) for x in (d / ".loom/since" / "deleted.jsonl").read_text().splitlines()]
    assert [(x["to"], x["id"], x["type"], x["quote"]) for x in told] == [("agent", agents, "revision", "Every orbit")]


def test_retired_key_dependency_removed_merge_by_alias(tmp_path: Path) -> None:
    d = demo(tmp_path)
    ok("accept", "dm-0004", "dm-0002", "--proofs", *AS, cwd=d)
    m = d / "drafting" / "main.tex"
    text = m.read_text()
    remark = text[text.index("\\begin{remark}\\label{dm-0004}") : text.index("\\end{remark}") + len("\\end{remark}")]
    m.write_text(text.replace(remark + "\n", ""))
    r = ok("status", "--retired", cwd=d)
    assert r.output.startswith("1 retired key") and r.output.splitlines()[2].split()[-1] == "dm-0004"
    lint = json_of("lint", "--json", cwd=d)["diagnostics"]
    assert any(x["code"] == "loom:retired-ledger-key" for x in lint)
    # merge by alias: dm-0004 becomes an alias of dm-0005
    m.write_text(m.read_text().replace("\\label{dm-0005}", "\\label{dm-0005}\\label{dm-0004}"))
    assert ok("status", "--retired", cwd=d).output.strip() == "no retired keys"
    assert ok("deps", "dm-0004", cwd=d).output.startswith("dm-0005")


def test_positional_key_recovery_by_hash(tmp_path: Path) -> None:
    q = synthetic(tmp_path)
    ok("accept", "sy-0006/proof/2", "--force", *AS, cwd=q)
    f = q / "drafting" / "nodes" / "sy-0006.tex"
    text = f.read_text()
    first = text[text.index("\\begin{proof}") : text.index("\\end{proof}") + len("\\end{proof}") + 1]
    f.write_text(text.replace(first, "", 1))
    s = status_json(q)
    assert "sy-0006/proof/2" not in s["keys"]
    assert s["keys"]["sy-0006/proof"]["previous_key_match"] == "sy-0006/proof/2"
    r = status_row(ok("status", cwd=q).output, "sy-0006/proof")
    assert "acceptance recorded under sy-0006/proof/2; re-accept to confirm" in r
    lint = json_of("lint", "--json", cwd=q, code=1)["diagnostics"]
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
        ["--master", "drafting/main.tex"],
        ["--tag", "orbits"],
    ):
        ok("status", *flags, cwd=q)
    assert "sy-000C/proof" in ok("status", "--incomplete", cwd=q).output
    assert "sy-0009" in ok("status", "--loose", cwd=q).output
    undigested = ok("status", "--undigested", cwd=q).output.splitlines()
    assert undigested[0].startswith("1 work") and undigested[2:] == ["Har77"]
    j = status_json(q)
    envelope = {"verdict", "ok", "exit", "groups", "notes"}
    assert set(j) - envelope == {
        "summary", "keys", "agent_documents", "undigested", "retired", "digests", "reading", "unmatched",
    }  # fmt: skip
    assert j["summary"]["incomplete"] == 1


def test_timeline_7_11(tmp_path: Path) -> None:
    d = demo(tmp_path)
    key, proof = "dm-0003", "dm-0003/proof"
    # Day 1: draft, never annotated; a referee run leaves three revisions
    s = status_json(d)
    assert s["keys"][key]["state"] == "draft" and s["keys"][key]["reviews"]["annotations"] == []
    ok(
        "annotate",
        key,
        "The hypothesis 'finite' is not needed for closedness.",
        "--quote",
        "finite set",
        "--type",
        "revision",
        "--as",
        "agent",
        cwd=d,
        env=AGENT,
    )
    ok(
        "annotate",
        proof,
        "Parity needs the orbit count.",
        "--quote",
        "disjoint union of orbits",
        "--type",
        "revision",
        "--as",
        "agent",
        cwd=d,
        env=AGENT,
    )
    ok(
        "annotate",
        proof,
        "Diagonal argument needs Hausdorff stated.",
        "--quote",
        "diagonal is closed",
        "--type",
        "revision",
        "--as",
        "agent",
        cwd=d,
        env=AGENT,
    )
    s = status_json(d)
    assert s["keys"][key]["reviews"]["open"] == {"revision": 1} and s["keys"][proof]["reviews"]["open"] == {
        "revision": 2
    }
    ok("build", cwd=d)
    frag = (d / ".loom/build" / "fragments" / "nodes" / "dm-0003.html").read_text()
    assert frag.count('<mark class="annotation"') == 3
    # Day 2: the author rewrites the proof; the proof annotations detach; the agent re-checks clean
    f = d / "drafting" / "nodes" / "dm-0003.tex"
    old = f.read_text()
    new = (
        old[: old.index("\\begin{proof}")]
        + "\\begin{proof}\n\\uses{dm-0002}\nBy Lemma~\\ref{lem:orbits}, $X$ splits into orbits of size one or two, so the parities agree. Closedness: the fixed locus is the preimage of the diagonal, which is closed since $X$ is Hausdorff.\n\\end{proof}\n"
    )
    f.write_text(new)
    s = status_json(d)
    assert s["keys"][proof]["reviews"]["detached"] == 2
    ok(
        "annotate",
        proof,
        "Read through; nothing to add.",
        "--type",
        "note",
        "--as",
        "agent",
        cwd=d,
        env=AGENT,
    )
    s = status_json(d)
    # a note only informs: it is on the proof and opens nothing
    assert [a["type"] for a in s["keys"][proof]["reviews"]["annotations"]].count("note") == 1
    assert s["keys"][proof]["reviews"]["open"] == {"revision": 2}
    # Day 3: the author resolves the statement's revision and accepts
    ann = next(e["id"] for e in events(d) if e["event"] == "created")
    ok("annotate", key, "--resolve", ann, "Finiteness is used for parity.", *AS, cwd=d)
    ok("accept", key, "--proofs", *AS, cwd=d)
    s = status_json(d)
    assert s["keys"][key]["state"] == "accepted" and s["keys"][proof]["state"] == "accepted"
    assert s["keys"][key]["derived"]["proved"] is True
    # Day 9: an upstream definition changes; the lemma's proof (not the theorem) goes stale; re-accept
    ok("accept", "dm-0002", "--proofs", *AS, cwd=d)
    g = d / "drafting" / "nodes" / "dm-0001.tex"
    g.write_text(g.read_text().replace(r"\sigma x = x", r"\sigma(x) = x"))
    s = status_json(d)
    stale = [k for k, e in s["keys"].items() if e.get("acceptance") and not e["acceptance"]["fresh"]]
    assert stale == ["dm-0002/proof"]
    assert s["keys"]["dm-0002/proof"]["acceptance"]["causes"][0]["id"] == "equation:eq:fix"
    explain = ok("status", "--explain", "dm-0002/proof", cwd=d)
    diff = [ln.strip() for ln in explain.output.splitlines()]
    assert "equation eq:fix changed" in explain.output
    assert any(ln.startswith("-") and r"\sigma x = x" in ln for ln in diff), explain.output
    assert any(ln.startswith("+") and r"\sigma(x) = x" in ln for ln in diff), explain.output
    ok("build", cwd=d)
    m = json.loads((d / ".loom/build" / "manifest.json").read_text())
    cause = m["keys"]["dm-0002/proof"]["acceptance"]["causes"][0]
    assert cause["diff"] and (d / ".loom/build" / cause["diff"]).exists()
    ok("accept", "--stale", "--yes", "--force", *AS, cwd=d)
    s = status_json(d)
    assert s["summary"]["stale"] == 0
    ok("build", cwd=d)
    m = json.loads((d / ".loom/build" / "manifest.json").read_text())
    assert m["annotations"] and any(a["detached"] for a in m["annotations"].values())


def test_status_json_answers_the_same_question_as_the_text_form(tmp_path: Path) -> None:
    """Every row filter applies to both forms (F3): `--json` is what a tool reaches for, and it returned the whole quilt."""
    q = synthetic(tmp_path)
    text = ok("status", "--master", "drafting/main.tex", cwd=q)
    # the author's rows; the cited works' are summarised after them, one line per work
    lines = [t for heading, t in status_rows(text.output) if not heading.startswith("in cited works")]
    js = json_of("status", "--master", "drafting/main.tex", "--json", cwd=q)
    assert all(ln.split()[-1] in js["keys"] for ln in lines)
    assert all("drafting/main.tex" in e["reached_by"] for e in js["keys"].values())
    assert len(js["keys"]) < len(json_of("status", "--json", cwd=q)["keys"])
    assert js["summary"]["keys"] == len(lines)  # and the count is of what was asked for, not of the quilt


def test_status_carries_the_title_beside_the_taxon(tmp_path: Path) -> None:
    """`rl-000G (Lemma) draft` does not say what the lemma is about, so choosing what to review meant grepping the source (F5)."""
    d = demo(tmp_path)
    js = status_json(d)
    assert js["keys"]["dm-0002"]["title"] == "Orbits" and js["keys"]["dm-0002"]["taxon"] == "Lemma"
    line = status_row(ok("status", cwd=d).output, "dm-0002")
    assert "Orbits" in line


def test_status_filters_by_what_the_annotations_say(tmp_path: Path) -> None:
    d = demo(tmp_path)
    ok("annotate", "dm-0002", "Which orbits?", "--type", "revision", *AS, cwd=d)
    ok("annotate", "dm-0003", "A thought", "--type", "suggestion", *AS, cwd=d)

    revisions = json_of("status", "--type", "Revision", "--json", cwd=d)["keys"]  # a type by its name, in any case
    assert list(revisions) == ["dm-0002"]
    sugg = json_of("status", "--type", "suggestion", "--json", cwd=d)["keys"]
    assert list(sugg) == ["dm-0003"]
    refused("status", "--type", "objection", cwd=d, code=2, match="no type 'objection' in this quilt; its types are")
    assert list(json_of("status", "--status", "resolved", "--json", cwd=d)["keys"]) == []
    assert list(json_of("status", "--detached", "--json", cwd=d)["keys"]) == []


def test_an_agent_lists_its_own_annotations_and_a_deleted_one_is_gone(tmp_path: Path) -> None:
    """What `ai annotations` lists is what stands: a deleted annotation is in no listing, and there is nothing withdrawn to ask for."""
    d = demo(tmp_path)
    as_agent = ("--as", "agent")
    ok("annotate", "dm-0002", "Wrong", "--type", "revision", *as_agent, cwd=d, env=AGENT)
    ok("annotate", "dm-0003", "Also wrong", *as_agent, cwd=d, env=AGENT)
    live = json_of("ai", "annotations", "--by", "agent", "--json", cwd=d)["annotations"]
    assert [f["message"] for f in live] == ["Wrong", "Also wrong"]
    assert not {"discarded", "discard_reason"} & set(live[0])

    ok("annotate", "--delete", live[1]["id"], *as_agent, cwd=d, env=AGENT)
    after = json_of("ai", "annotations", "--by", "agent", "--json", cwd=d)["annotations"]
    assert [f["id"] for f in after] == [live[0]["id"]]
    refused("ai", "annotations", "--all", cwd=d, code=2, match="No such option")
    revisions = json_of("ai", "annotations", "--by", "agent", "--type", "revision", "--json", cwd=d)
    assert [f["id"] for f in revisions["annotations"]] == [live[0]["id"]]


def test_ai_annotations_lists_every_annotation_and_each_filter_narrows_it(tmp_path: Path) -> None:
    """With no filter every annotation in the quilt; `--by`, `--target`, `--type` and `--status` each narrow it, and together every one must hold."""
    d = demo(tmp_path, clean=False)  # the shipped store, for a note on a page of a cited work
    mine = ok("annotate", "dm-0002", "Which orbits?", "--type", "question", *AS, cwd=d).output.split()[0]
    theirs = ok(
        "annotate", "dm-0002", "Wrong.", "--type", "revision", "--as", "agent", cwd=d, env=AGENT
    ).output.split()[0]
    elsewhere = ok("annotate", "dm-0003", "Fine.", "--type", "note", *AS, cwd=d).output.split()[0]
    ok("annotate", "--resolve", mine, "Answered.", *AS, cwd=d)

    def listed(*flags: str) -> list[str]:
        return [a["id"] for a in json_of("ai", "annotations", *flags, "--json", cwd=d)["annotations"]]

    assert {mine, theirs, elsewhere} <= set(listed())
    assert listed("--by", "Markas Hecht") == [mine, elsewhere]
    assert sorted(listed("--target", "dm-0002")) == sorted([mine, theirs])
    assert listed("--target", "dm-0002", "--status", "open") == [theirs]
    assert listed("--by", "Markas Hecht", "--type", "Note") == [elsewhere]
    assert listed("--by", "Nobody") == []
    assert ok("ai", "annotations", "--by", "Nobody", cwd=d).stdout.startswith("no annotations match")
    # a citekey reaches the notes on its pages, which carry the work's identifier as their target
    page = ok(
        "annotate", "Calloway14", "On page one.", "--page", "1", "--box", "72,72,300,120", *AS, cwd=d
    ).output.split()[0]
    assert listed("--target", "Calloway14") == [page]


BATCH = [
    pytest.param(
        [{"edit": "{ann}", "message": "Which orbits exactly?"},
         {"target": "dm-0003", "message": "A second", "quote": "finite set"},
         {"resolve": "{ann}", "message": "fixed"}],
        0, None, [("edited", "Which orbits exactly?"), ("created", "A second"), ("resolved", "fixed")],
        id="every-verb-one-to-a-line",
    ),
    # a batch is written by a program that cannot see the result, so a misspelled key must not file an empty annotation
    pytest.param([{"target": "dm-0002", "messsage": "typo"}], 2, "unknown key(s) messsage", [], id="unknown-key"),
    pytest.param([{"edit": "{ann}", "delete": "{ann}", "message": "?"}], 2, "one verb per line", [], id="two-verbs"),
    pytest.param([{"edit": "{ann}"}], 2, "nothing to change", [], id="answers-nothing"),
    pytest.param([{"edit": "{ann}", "message": "x", "quote": "Every orbit"}], 2, "--quote would be lost", [], id="an-edit-moves-no-anchor"),
    pytest.param([{"delete": "{ann}", "color": "red"}], 2, "--color would be lost", [], id="a-deletion-carries-nothing"),
    pytest.param([{"edit": "{ann}", "color": "green"}], 0, None, [("edited", None)], id="an-edit-carries-a-look"),
    pytest.param([{"target": "dm-0002", "message": "x", "payload": "y"}], 2, "unknown key(s) payload", [], id="no-payload"),
    # every line is checked before any is written, so a failing line leaves nothing half done (the re-grade's K3)
    pytest.param(
        [{"target": "dm-0002", "message": "one", "quote": "Every orbit", "type": "suggestion"},
         {"target": "dm-0002", "message": "two", "quote": "NOPE"},
         {"target": "dm-0002", "message": "three"}],
        2, "batch line 2", [],
        id="checks-every-line-before-writing-any",
    ),
    pytest.param(
        [{"target": "dm-0002", "message": "one"}, {"target": "dm-9999", "message": "two"}],
        2, "nothing was written", [],
        id="an-unknown-key-on-a-later-line",
    ),
    pytest.param([{"target": "dm-0002", "type": "revision"}], 2, "needs words", [], id="an-empty-revision"),
    pytest.param([{"target": "dm-0002", "message": "a second"}, {"delete": "{ann}"}], 0, None, None, id="a-deletion-takes-the-line"),
]  # fmt: skip


@pytest.mark.parametrize(("lines", "code", "match", "wrote"), BATCH)
def test_a_batch_carries_every_verb_and_refuses_line_by_line(
    tmp_path: Path, lines: list[dict[str, str]], code: int, match: str | None, wrote: list[tuple[str, str]] | None
) -> None:
    """`comment --batch` reads one JSON object per line against an existing finding `{ann}`; `wrote` is the events it appends, in order, or None where `{ann}` is deleted and only the second annotation stands."""
    d = demo(tmp_path)
    ann = ok("annotate", "dm-0002", "Which orbits?", "--type", "question", *AS, cwd=d).output.split()[0]
    stdin = "".join(json.dumps({k: v.replace("{ann}", ann) for k, v in line.items()}) + "\n" for line in lines)
    r = exits(code, "annotate", "--batch", *AS, cwd=d, stdin=stdin, match=match)
    if match == "unknown key(s) messsage":
        assert "accepted:" in r.output, r.output  # the refusal names the keys a line may carry
    if wrote is None:
        assert f"deleted {ann}" in r.output and [(e["event"], e["body"]) for e in events(d)] == [
            ("created", "a second")
        ]
        return
    assert [(e["event"], e.get("body")) for e in events(d)[1:]] == wrote


def test_an_annotation_that_stays_open_needs_a_message_and_one_that_informs_does_not(tmp_path: Path) -> None:
    """The re-grade: an annotation that asks something and says nothing was filed, exit 0; a note, or an untyped mark, with no words is the record that the target was read."""
    d = demo(tmp_path)
    for type_given in ("revision", "Suggestion", "question"):
        refused("annotate", "dm-0002", "--type", type_given, *AS, cwd=d, code=2, match="needs words")
        refused("annotate", "dm-0002", "  ", "--type", type_given, *AS, cwd=d, code=2, match="needs words")
    assert events(d) == []
    ok("annotate", "dm-0002", *AS, cwd=d)
    ok("annotate", "dm-0002", "--type", "note", *AS, cwd=d)
    assert [e["type"] for e in events(d)] == [None, "note"]


def test_a_type_is_named_by_its_id_or_its_name_and_one_the_quilt_lacks_is_refused(tmp_path: Path) -> None:
    d = demo(tmp_path)
    ok("annotate", "dm-0002", "Fine.", "--type", "NOTE", *AS, cwd=d)
    ok("annotate", "dm-0002", "Why?", "--type", "Question", *AS, cwd=d)
    assert [e["type"] for e in events(d)] == ["note", "question"]
    r = refused("annotate", "dm-0002", "Why?", "--type", "objection", *AS, cwd=d, code=2, match="no type 'objection'")
    assert "revision (Revision)" in flat(r.output)  # the refusal names the quilt's types
    assert len(events(d)) == 2


def test_a_reply_refuses_what_it_cannot_carry(tmp_path: Path) -> None:
    """The 0.14 study: an agent replied "a replacement is attached" with proposed text, and the text was dropped without a word."""
    d = demo(tmp_path)
    ann = ok("annotate", "dm-0002", "A finding", "--type", "revision", *AS, cwd=d).output.split()[0]
    before = len(events(d))
    for extra in (("--type", "note"), ("--color", "red"), ("--quote", "finite set")):
        for verb in ("--reply", "--resolve"):
            refused(
                "annotate",
                verb,
                ann,
                "A replacement is attached.",
                *extra,
                *AS,
                cwd=d,
                code=2,
                match=f"{extra[0]} would be lost",
            )
    assert len(events(d)) == before


def test_an_edit_or_a_deletion_refuses_what_it_cannot_carry(tmp_path: Path) -> None:
    """`--edit ID --quote ..` exited 0 and wrote an edit with no anchor (the anchoring critique, 2026-10-03); a deletion carries nothing beside its id, and two verbs in one call ran one."""
    d = demo(tmp_path)
    ann = ok("annotate", "dm-0002", "A finding", "--quote", "Every orbit", *AS, cwd=d).output.split()[0]
    before = len(events(d))
    for verb, extra in (
        ("--edit", ("--quote", "one or two")),
        ("--edit", ("--page", "3")),
        ("--delete", ("--type", "note")),
        ("--delete", ("--quote", "one or two")),
        ("--delete", ("--color", "red")),
    ):
        refused("annotate", verb, ann, "Restated.", *extra, *AS, cwd=d, code=2, match=f"{extra[0]} would be lost")
    refused("annotate", "--delete", ann, "--reply", ann, *AS, cwd=d, code=2, match="one verb per call")
    refused("annotate", "--edit", ann, "x", "--reply", ann, *AS, cwd=d, code=2, match="one verb per call")
    assert len(events(d)) == before

    # a look is one of the fields an edit restates, and an edit of it alone is a change
    ok("annotate", "--edit", ann, "--color", "green", *AS, cwd=d)
    [f] = json_of("ai", "annotations", "--json", cwd=d)["annotations"]
    assert f["quote"] == "Every orbit" and events(d)[-1]["look"] == {"color": "green"}


def test_a_quote_copied_from_the_source_is_marked_where_it_is(tmp_path: Path) -> None:
    """The anchoring critique (2026-10-03): quotes `annotate` accepted -- one opening with `\\noindent`, one with `\\S~\\ref`, one with a TeX dash -- were marked as their whole section or paragraph. Each is marked on its own words."""
    d = synthetic(tmp_path)
    edit(
        d / "drafting" / "sections" / "results.tex",
        "deferred to the end of the section.\n",
        "deferred to the end of the section.\n\n\\noindent\\textbf{Problem 1:} decide whether every widget is tame.\n\n"
        "As shown in (\\S~\\ref{sy-0201}) the consequences follow -- mostly.\n",
    )
    quotes = ["\\noindent\\textbf{Problem 1:}", "(\\S~\\ref{sy-0201})", "follow -- mostly"]
    ids = [ok("annotate", "sy-0200", "Look.", "--quote", q, *AS, cwd=d).output.split()[0] for q in quotes]
    exits(1, "build", cwd=d)
    frag = (d / ".loom/build" / "fragments" / "nodes" / "sy-0200.html").read_text()
    assert "annotation-block" not in frag
    for ann in ids:
        assert f'<mark class="annotation" data-annotation="{ann}">' in frag, ann


def test_a_verb_that_answers_nothing_is_refused(tmp_path: Path) -> None:
    d = demo(tmp_path)
    ann = ok("annotate", "dm-0002", "A finding", "--type", "revision", *AS, cwd=d).output.split()[0]
    before = len(events(d))

    refused("annotate", "--reply", ann, *AS, cwd=d, code=2, match="a reply with no message")
    refused("annotate", "--edit", ann, *AS, cwd=d, code=2, match="nothing to change")
    refused("annotate", "--edit", ann, "", *AS, cwd=d, code=2, match="empty body")
    assert len(events(d)) == before  # none of them wrote

    # a field-only edit still stands, and a resolution needs no comment
    ok("annotate", "--edit", ann, "--color", "purple", *AS, cwd=d)
    ok("annotate", "--resolve", ann, *AS, cwd=d)


def test_a_finding_on_a_section_is_visible_where_the_author_looks(tmp_path: Path) -> None:
    """`loom annotate` accepts a section, stores the annotation, and `status` showed nothing: a major finding filed through the sanctioned command was invisible in the only place the author is told to look (H19)."""
    q = synthetic(tmp_path)
    ok(
        "annotate",
        "sy-0100",
        "Never defines the torus T that Results uses",
        "--type",
        "revision",
        *AS,
        cwd=q,
    )

    js = json_of("status", "--json", cwd=q)
    assert js["keys"]["sy-0100"]["kind"] == "section"
    assert js["keys"]["sy-0100"]["state"] == ""  # a section is a container, not a claim
    assert js["keys"]["sy-0100"]["reviews"]["open"] == {"revision": 1}

    line = status_row(ok("status", cwd=q).output, "sy-0100")
    assert "Introduction" in line and "1 open revision" in line
    assert "1 open revision" in ok("status", "--explain", "sy-0100", cwd=q).output
    assert list(json_of("status", "--type", "revision", "--json", cwd=q)["keys"]) == [
        "sy-0003",
        "sy-0100",
    ]

    # it takes no acceptance row, and a section nobody annotated is structure rather than work
    refused("accept", "sy-0100", *AS, cwd=q, code=2, match="sy-0100 is not a statement or proof key")
    assert not any(ln.split()[-1:] == ["sy-0200"] for ln in ok("status", cwd=q).output.splitlines())


def test_status_is_the_authors_to_do_list_not_the_literatures(tmp_path: Path) -> None:
    """A digest holds every result of a cited paper; relloc printed 150 rows of which 92 were Manolache's, and the summary counted his one `incomplete` and his 92 `loose` as the author's (F4, A3, A4)."""
    q = synthetic(tmp_path)
    # a result of the cited paper that nothing in this quilt uses, which is most of a real digest
    digest = q / ".loom/digests" / "Kre99.tex"
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
    line = status_row(ok("status", cwd=q).output, "Kre99")  # the cited work's keys, summarised on one line
    assert f"{len(kept)} results you depend on" in line
    assert f"{len(external - kept)} not counted" in line


def test_accept_refuses_a_digest_node_and_names_the_command_that_does_it(tmp_path: Path) -> None:
    """Two claims, two commands (plan 0.12 §5.6). `loom accept` is the author's own mathematics; someone else's theorem is not theirs to accept, and DR-172 relabelled the output where the command needed splitting."""
    q = synthetic(tmp_path)
    r = refused("accept", "Kre99-thm-2.1", *AS, cwd=q, code=2, match="not yours to accept")
    assert "loom library verify Kre99-thm-2.1" in r.output

    # the author's own keys are untouched by any of it
    assert ok("accept", "sy-0002", *AS, cwd=q).output.startswith("accepted sy-0002")


def test_verifying_a_digest_node_says_what_it_claims(tmp_path: Path) -> None:
    """Verifying an external node claims loom's copy of the cited paper is faithful, never that this quilt proved the theorem; both printed `accepted` (H22)."""
    q = synthetic(tmp_path)
    # a digest extracted before the reference layer existed gains its records from one `library update` (contract §1.4)
    ok("library", "update", "--only", "extract", cwd=q)
    r = ok("library", "verify", "Kre99-thm-2.1", "--as", "A. Author", "--yes", cwd=q)
    assert "verified Kre99-thm-2.1" in r.output
    assert "--- the source ---" in r.output, "a mechanical result's anchor is its LaTeX, and it says so"
    assert "as a faithful transcription of Kre99" in r.output

    line = status_row(ok("status", cwd=q).output, "Kre99")  # a cited work's keys are summarised by work
    assert "transcription verified" in line and "accepted" not in line

    # and what moved is the transcription, not the author's own text
    p = q / ".loom/digests" / "Kre99.tex"
    p.write_text(p.read_text().replace("is well defined", "is well-defined", 1))
    e = ok("status", "--explain", "Kre99-thm-2.1", cwd=q).output
    assert "transcription verified, stale" in e and "its transcription changed" in e
    assert "edited" not in e


def test_a_status_change_is_reversed_by_appending_its_undo(tmp_path: Path) -> None:
    """A resolution is taken back by appending its undo, so it is never the one state nothing can reverse — and `--resolve` is the verb a run can apply to its own finding (DR-174)."""
    d = demo(tmp_path)
    ann = ok("annotate", "dm-0002", "Which orbits?", "--type", "revision", *AS, cwd=d).output.split()[0]

    assert ok("annotate", "--resolve", ann, *AS, cwd=d).output.startswith("resolved")
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {}
    assert ok("annotate", "--resolve", ann, "--undo", *AS, cwd=d).output.startswith("reopened")
    assert status_json(d)["keys"]["dm-0002"]["reviews"]["open"] == {"revision": 1}

    # nothing was removed: every act is still in the log, the undo included
    assert [(e["event"], e.get("undo")) for e in events(d)] == [
        ("created", None),
        ("resolved", None),
        ("resolved", True),
    ]

    refused(
        "annotate", "--undo", *AS, cwd=d, code=2, match="--undo applies to --resolve"
    )  # --undo needs a verb to undo
    # a deletion is not undone from the command line: nothing of it is left to put back
    refused("annotate", "--delete", ann, "--undo", *AS, cwd=d, code=2, match="--undo applies to --resolve")


def test_a_comment_on_an_equation_marks_its_display(tmp_path: Path) -> None:
    """A comment on a region key with no quote -- a box drawn round an equation -- marks the display itself, so the reader can click it; nothing is put inside the formula."""
    d = synthetic(tmp_path)
    ok(
        "annotate",
        "sy-0001#eq:fix",
        "The fixed locus wants a name.",
        "--as",
        "agent",
        cwd=d,
        env=AGENT,
    )
    ann = [e["id"] for e in events(d) if e["event"] == "created"][-1]
    exits(1, "build", cwd=d)
    frag = (d / ".loom/build" / "fragments" / "nodes" / "sy-0001.html").read_text()
    display = next(ln for ln in frag.split("<div") if 'data-label="eq:fix"' in ln)
    assert "annotation-block" in display and ann in display
    assert "<mark" not in display


def test_an_annotation_may_name_the_document_it_is_read_in(tmp_path: Path) -> None:
    """A claim about a node that holds in one document names it with --in (plan 0.15, decision 9): recorded, published, copied onto replies, and refused where the document does not hold the node."""
    d = demo(tmp_path)
    r = ok(
        "annotate",
        "dm-0002",
        "Redundant here: dm-0001 already covers it.",
        "--in",
        "drafting/outline.tex",
        *AS,
        cwd=d,
    )
    ann = r.output.split()[0]
    assert events(d)[-1]["in"] == "drafting/outline.tex"
    reply = ok("annotate", "--reply", ann, "Agreed.", *AS, cwd=d).output.split()[0]
    assert events(d)[-1]["in"] == "drafting/outline.tex"  # a reply is read where its parent is
    ok("build", cwd=d)
    m = json.loads((d / ".loom/build" / "manifest.json").read_text())
    assert (
        m["annotations"][ann]["in"] == "drafting/outline.tex"
        and m["annotations"][reply]["in"] == "drafting/outline.tex"
    )
    assert m["annotations"][ann]["anchored"] is False and m["annotations"][ann]["detached"] is False
    # a document that is no master, and a master that does not hold the node
    refused(
        "annotate",
        "dm-0002",
        "x",
        "--in",
        "drafting/nodes/dm-0002.tex",
        *AS,
        cwd=d,
        code=2,
        match="is not a document of this quilt",
    )
    refused(
        "annotate",
        "dm-0003",
        "x",
        "--in",
        "drafting/outline.tex",
        *AS,
        cwd=d,
        code=2,
        match="does not hold dm-0003",
    )
    # batch takes the same key
    ok(
        "annotate",
        "--batch",
        *AS,
        cwd=d,
        stdin='{"target": "dm-0001", "message": "In the outline only.", "in": "drafting/outline.tex"}\n',
    )
    assert events(d)[-1]["in"] == "drafting/outline.tex"


def test_an_annotation_whose_document_stops_holding_the_node_is_detached(tmp_path: Path) -> None:
    d = demo(tmp_path)
    ann = ok("annotate", "dm-0002", "Only here.", "--in", "drafting/outline.tex", *AS, cwd=d).output.split()[0]
    outline = d / "drafting" / "outline.tex"
    edit(outline, "\\input{nodes/dm-0002}", "% dm-0002 taken out")
    # the outline now refers to a node it no longer holds, so the build reports an error and publishes all the same
    exits(1, "build", cwd=d, match="reference-to-loose")
    m = json.loads((d / ".loom/build" / "manifest.json").read_text())
    assert m["annotations"][ann]["detached"] is True


def test_rewriting_one_unattached_proof_detaches_only_the_annotation_on_its_words(tmp_path: Path) -> None:
    d = demo(tmp_path)
    main = d / "drafting" / "main.tex"
    answers = (
        "\\begin{enumerate}\n\\item One.\n\\begin{proof}\nThe first answer is short.\n\\end{proof}\n"
        "\\item Two.\n\\begin{proof}\nThe second answer is unique.\n\\end{proof}\n\\end{enumerate}\n"
    )
    edit(main, "\\end{document}", answers + "\\end{document}")
    first, second = sorted(
        (k for k in status_json(d)["keys"] if "#proof:" in k), key=lambda k: int(k.rsplit(":", 1)[1])
    )
    rewritten = ok("annotate", first, "A hint.", "--quote", "The first answer is short", *AS, cwd=d).output.split()[0]
    kept = ok("annotate", second, "Another.", "--quote", "The second answer is unique", *AS, cwd=d).output.split()[0]
    edit(main, "The first answer is short.", "This answer has been rewritten at considerably greater length.")
    exits(1, "build", cwd=d, match="unattached-proof")
    annotations = json.loads((d / ".loom/build" / "manifest.json").read_text())["annotations"]
    assert annotations[rewritten]["detached"] is True
    assert annotations[kept]["detached"] is False


# ---- documents that move (plan 0.16 phase 1) ---------------------------------------------------

FLAT = ("drafting/main.tex", "--to", "drafting/main-flat.tex", "--keep-shared", "--no-check")


def test_an_acceptance_follows_its_document_through_a_linearize_and_back(tmp_path: Path) -> None:
    """The 2026-09-26 reproduction: dm-0001 accepted in main.tex stays fresh when main.tex is linearized, and stays fresh when `loom live` makes main.tex its own again."""
    d = demo(tmp_path)
    ok("accept", "dm-0001", "--force", *AS, cwd=d)
    ok("linearize", *FLAT, cwd=d)
    acc = status_json(d)["keys"]["dm-0001"]["acceptance"]
    assert acc["fresh"] is True, acc
    ok("live", "drafting/main.tex", cwd=d)
    assert status_json(d)["keys"]["dm-0001"]["acceptance"]["fresh"] is True


def test_a_changed_preamble_is_still_found_in_the_document_it_moved_to(tmp_path: Path) -> None:
    """Following the move compares against the document as it is now, so a real preamble change after a linearize still reads as one."""
    d = demo(tmp_path)
    ok("accept", "dm-0001", "--force", *AS, cwd=d)
    ok("linearize", *FLAT, cwd=d)
    edit(d / "drafting" / "main-flat.tex", "\\begin{document}", "\\newcommand{\\widgetset}{W}\n\\begin{document}")
    causes = status_json(d)["keys"]["dm-0001"]["acceptance"]["causes"]
    assert [c["kind"] for c in causes] == ["preamble-changed"]


def test_accept_stale_after_a_linearize_records_the_new_document_and_is_fresh(tmp_path: Path) -> None:
    d = demo(tmp_path)
    ok("accept", "dm-0001", "--force", *AS, cwd=d)
    edit(
        d / "drafting" / "nodes" / "dm-0001.tex",
        "Its \\emph{fixed locus} is",
        "Its \\emph{fixed locus}, a subset of $X$, is",
    )
    ok("linearize", *FLAT, cwd=d)
    assert status_json(d)["keys"]["dm-0001"]["acceptance"]["fresh"] is False
    ok("accept", "--stale", "--yes", "--force", *AS, cwd=d)
    assert status_json(d)["keys"]["dm-0001"]["acceptance"]["fresh"] is True
    rows = (d / ".loom" / "state.toml").read_text().split("[[accept]]")
    assert 'master = "drafting/main-flat.tex"' in rows[-1]


def test_a_document_deleted_by_hand_is_gone_not_changed(tmp_path: Path) -> None:
    """With nothing recording where it went, the rows read `document-gone` naming the path, `loom lint` says so once with the command that records the move, and `accept --stale` writes against a live document."""
    d = demo(tmp_path)
    ok("accept", "dm-0001", "dm-0002", "--force", *AS, cwd=d)
    ok("annotate", "dm-0001", "Read here.", "--in", "drafting/main.tex", *AS, cwd=d)
    (d / "drafting" / "main.tex").unlink()
    causes = status_json(d)["keys"]["dm-0001"]["acceptance"]["causes"]
    assert causes == [{"kind": "document-gone", "id": "drafting/main.tex", "diff": None, "when": causes[0]["when"]}]
    assert "drafting/main.tex, which it was accepted in, is unavailable" in flat(ok("status", cwd=d).output)
    gone = [x for x in json_of("lint", "--json", cwd=d)["diagnostics"] if x["code"] == "loom:document-gone"]
    assert gone == [
        {
            "severity": "warning",
            "code": "loom:document-gone",
            "message": "drafting/main.tex is gone and the history does not say where it went; 2 acceptance rows and 1 annotation name it",
            "locations": [],
            "keys": ["dm-0001", "dm-0002"],
            "fixes": [
                {"label": "record where it went, NEW being its path now", "command": "loom mv drafting/main.tex NEW"}
            ],
            "subject": "record",
            "owner": "person",
        }
    ]
    ok("accept", "--stale", "--yes", "--force", *AS, cwd=d)
    assert 'master = "drafting/outline.tex"' in (d / ".loom" / "state.toml").read_text().split("[[accept]]")[-1]
    assert status_json(d)["keys"]["dm-0001"]["acceptance"]["fresh"] is True


def test_an_annotation_in_a_linearized_document_is_drawn_in_what_it_became(tmp_path: Path) -> None:
    """`in` and a whole-document target follow the document: the manifest publishes where it is now, and the mark is baked into that document's fragment."""
    d = demo(tmp_path)
    ann = ok(
        "annotate",
        "dm-0003",
        "Say which topology.",
        "--quote",
        "closed in every topology",
        "--in",
        "drafting/main.tex",
        *AS,
        cwd=d,
    ).output.split()[0]
    whole = ok("annotate", "drafting/main.tex", "The title is too long.", *AS, cwd=d).output.split()[0]
    ok("linearize", *FLAT, cwd=d)
    ok("build", cwd=d)
    m = json.loads((d / ".loom/build" / "manifest.json").read_text())
    got = m["annotations"][ann]
    assert got["in"] == "drafting/main-flat.tex" and got["detached"] is False and got["anchored"] is True, got
    assert m["annotations"][whole]["target"]["key"] == "drafting/main-flat.tex"
    assert m["annotations"][whole]["detached"] is False
    assert ann in (d / ".loom/build" / "fragments" / "masters" / "drafting" / "main-flat.html").read_text()
    # the record keeps the path it was written with
    assert [e["in"] for e in events(d) if e.get("id") == ann] == ["drafting/main.tex"]


def test_a_proposed_theorem_and_proof_are_rendered_as_the_document_renders_them(tmp_path: Path) -> None:
    """A proposal that is a whole result reached the viewer as TeX, and MathJax drew each environment as an error; the publisher renders a suggested edit's text beside the TeX."""
    d = demo(tmp_path)
    proposed = "\\begin{lemma}\\label{dm-0002-ai}\nEvery nonempty orbit has \\(1\\) or \\(2\\) points.\n\\end{lemma}\n\\begin{proof}\n\\uses{dm-0001}\nBy definition.\n\\end{proof}"
    made = json_of(
        "suggest",
        "dm-0002",
        "--with",
        proposed,
        "--comment",
        "A sharper statement.",
        "--as",
        "agent",
        "--json",
        cwd=d,
        env=AGENT,
    )
    ok("build", cwd=d)
    entry = json.loads((d / ".loom/build/manifest.json").read_text())["suggested_edits"][made["edit"]]
    assert entry["with"] == proposed
    html = entry["with_html"]
    assert 'class="env env-lemma"' in html and "env-proof" in html
    assert "\\begin{" not in html and "\\uses" not in html and 'id="' not in html


def test_a_conflicted_id_is_a_row_of_its_own_and_its_definitions_are_not(tmp_path: Path) -> None:
    """Two live files defining one id left status listing two positional keys and a clean summary, never the word conflicted (CLI study, defect 11)."""
    q = synthetic(tmp_path)
    keys = status_json(q)["keys"]
    assert keys["sy-999B"]["state"] == "conflicted"
    assert keys["sy-999B"]["conflict"] == ["drafting/nodes/sy-999B.tex", "drafting/talk.tex"]
    assert not [k for k in keys if "#lemma:" in k and k.startswith(("drafting/talk.tex", "drafting/nodes/sy-999B.tex"))]
    said = ok("status", cwd=q).output
    assert "loom fork sy-999B --in drafting/talk.tex" in said
    assert ": 1 conflicted," in said.splitlines()[0]  # the verdict counts it, first


def test_explain_names_another_reviewers_acceptance(tmp_path: Path) -> None:
    """The re-grade: `status --explain dm-0002` said "never accepted" while the ledger held an acceptance by "The loom demo"; the local reviewer has none, which is what the state counts, and the other is named beside it."""
    d = demo(tmp_path, clean=False)
    r = ok("status", "--explain", "dm-0002", cwd=d)
    assert "never accepted" not in r.stdout
    assert "not accepted by you (Markas Hecht); accepted by The loom demo on 2026-09-16" in " ".join(r.stdout.split())


def test_status_counts_each_agent_documents_work_apart_from_the_authors(tmp_path: Path) -> None:
    """What waits in an agent document -- an `\\incomplete`, an open annotation -- is listed under that document, and never among the author's rows (plan 0.21.2)."""
    q = synthetic(tmp_path)
    s = status_json(q)
    a = s["agent_documents"][".loom/copies/aidoc.tex"]
    assert a["source"] == "drafting/main.tex"
    assert list(a["keys"]) == ["sy-000C-ai/proof"] and a["keys"]["sy-000C-ai/proof"]["counterpart"] == "sy-000C/proof"
    assert a["summary"] == {"keys": 1, "incomplete": 1, "open": 0}
    assert not [
        k for k in s["keys"] if "-ai" in k or k.startswith(".loom/copies/")
    ]  # the author's rows stay the author's
    out = ok("status", cwd=q).stdout
    assert (
        "in .loom/copies/aidoc.tex (1)" in out and "next: loom status --master .loom/copies/aidoc.tex --in-order" in out
    )
    assert "; 1 agent document: .loom/copies/aidoc.tex 1 incomplete" in " ".join(out.split("\n\n")[0].split())
    assert "- agent documents: .loom/copies/aidoc.tex 1 incomplete" in ok("ai", "orient", cwd=q).stdout
    # a filter applies to the agent documents as to the author's keys
    assert (
        json_of("status", "--master", "drafting/main.tex", "--json", cwd=q)["agent_documents"][
            ".loom/copies/aidoc.tex"
        ]["keys"]
        == {}
    )


def test_an_agent_closes_any_annotation_on_an_agent_document_and_still_may_not_accept(tmp_path: Path) -> None:
    """Full privilege on an agent document (plan 0.21.2): an agent resolves and edits another agent's annotation and the author's alike; it deletes only its own, there as anywhere, and the author's acts still refuse it."""
    q = synthetic(tmp_path)
    key = "sy-000C-ai/proof"

    def filed(who: str, body: str, env: dict[str, str] | None = None) -> str:
        return ok("annotate", key, body, "--type", "question", "--as", who, cwd=q, env=env or {}).stdout.split()[0]

    referee = filed("Referee Agent", "Which definition?", AGENT)
    mine = filed("Markas Hecht", "Is this step needed?")
    other = filed("Referee Agent", "A second thought.", AGENT)
    ok("annotate", "--resolve", referee, "Answered in the text.", "--as", "Simplify Agent", cwd=q, env=AGENT)
    ok(
        "annotate",
        "--edit",
        mine,
        "Is this step needed, or does Definition 3 give it?",
        "--as",
        "Simplify Agent",
        cwd=q,
        env=AGENT,
    )
    refused(
        "annotate", "--delete", other, "--as", "Simplify Agent", cwd=q, env=AGENT, code=2, match="deletes only its own"
    )
    acts = {
        (e["event"], e["id"]): e["author"]
        for e in events(q)
        if e["event"] in ("resolved", "edited") and e.get("id") in (referee, mine, other)
    }
    assert acts == {("resolved", referee): "Simplify Agent", ("edited", mine): "Simplify Agent"}
    ok("annotate", "--delete", other, "--as", "Referee Agent", cwd=q, env=AGENT)
    assert other not in {e.get("id") for e in events(q)}
    refused("accept", "sy-0001", "--as", "Simplify Agent", cwd=q, env=AGENT, code=2, match="may not run")


def test_status_rows_read_as_the_reader_reads_them(tmp_path: Path) -> None:
    """T4: the re-grade's `status` printed raw, cut LaTeX titles (`Proof of Lemma~\\ref{lem:indepen…`), causes as codes and no theorem numbers; a row's title is plain, and its kind carries the number the last build printed."""
    d = demo(tmp_path)
    edit(
        d / "drafting" / "nodes" / "dm-0002.tex",
        "\\begin{lemma}[Orbits]",
        "\\begin{lemma}[\\emph{Orbits} of $\\sigma$]",
    )
    aux = d / ".loom/build" / "drafting" / "main" / "main.aux"
    aux.parent.mkdir(parents=True, exist_ok=True)
    aux.write_text("\\newlabel{dm-0002}{{2.1}{3}}\n")
    row = status_row(ok("status", cwd=d).output, "dm-0002")
    assert "Lemma 2.1" in row and "Orbits of $\\sigma$" in row and "\\emph" not in row, row
    aux.unlink()
    assert "Lemma 2.1" not in status_row(ok("status", cwd=d).output, "dm-0002")  # no build, no number


def test_accept_says_what_it_did_and_what_it_did_not(tmp_path: Path) -> None:
    """T7: the re-grade's `accept dm-0001` twice wrote two rows and said "accepted" both times, and `--force` over a failing compile said only "accepted"; T3: `--all-live` refused for an incomplete key and named no way to accept the rest."""
    d = demo(tmp_path)
    first = ok("accept", "dm-0001", "--force", *AS, cwd=d)
    assert "without compiling drafting/main.tex, as --force asks" in flat(first.output), first.output
    rows = (d / ".loom" / "state.toml").read_text()
    again = ok("accept", "dm-0001", "--force", *AS, cwd=d)
    assert "already accepted as Markas Hecht: dm-0001; nothing written" in flat(again.output), again.output
    assert (d / ".loom" / "state.toml").read_text() == rows
    r = refused("accept", "--all-live", "--yes", "--force", *AS, cwd=d, code=1, match="dm-0005/proof")
    rest = flat(r.output).split("Accept the rest by key: ")[1].split()
    assert rest[:2] == ["loom", "accept"] and "dm-0005/proof" not in rest, rest
    ok(*rest[1:], "--force", *AS, cwd=d)  # the command it names accepts them


def test_a_reply_and_an_edit_are_checked_as_a_new_annotation_is(tmp_path: Path) -> None:
    """K3 (DR-334): a reply carries its text only, an edit's type is checked against the quilt's as a new annotation's is, and only a type that stays open is resolved."""
    d = demo(tmp_path)
    note = ok("annotate", "dm-0002", "Read; fine.", "--type", "note", *AS, cwd=d).output.split()[0]
    before = len(events(d))
    refused("annotate", "--reply", note, "Why?", "--type", "question", *AS, cwd=d, code=2, match="--type would be lost")
    refused("annotate", "--edit", note, "--type", "bogus", *AS, cwd=d, code=2, match="no type 'bogus' in this quilt")
    refused("annotate", "--edit", note, "--weight", "0", *AS, cwd=d, code=2, match="Invalid value for '--weight'")
    refused("annotate", "--resolve", note, *AS, cwd=d, code=2, match="only informs, so there is nothing to resolve")
    assert len(events(d)) == before
    ok("annotate", "--reply", note, "Which orbits?", *AS, cwd=d)
    assert "type" not in events(d)[-1]  # a reply is dialogue, with no type of its own

    # retyped, it is drawn as its new type unless something is set on it, and then it can be resolved
    ok("annotate", "--edit", note, "--type", "question", *AS, cwd=d)
    assert (events(d)[-1]["type"], events(d)[-1]["drawn"]["color"]) == ("question", "blue")
    ok("annotate", "--resolve", note, *AS, cwd=d)
    # '' takes the type off and keeps what is set on it
    ok("annotate", "--edit", note, "--type", "", "--color", "pink", *AS, cwd=d)
    last = events(d)[-1]
    assert (last["type"], last["look"], last["drawn"]["color"]) == (None, {"color": "pink"}, "pink")


def test_cited_works_nothing_depends_on_are_one_line(tmp_path: Path) -> None:
    """T2: on relloc `status` ended with 52 rows of "N not counted  CITEKEY", the same sentence 52 times."""
    from tests.unit._quilts import showcase

    q = showcase(tmp_path)
    out = ok("status", cwd=q).stdout
    cited = out.split("in cited works", 1)[1]
    idle = [ln for ln in cited.splitlines() if "none you depend on, not counted" in ln]
    assert len(idle) == 1 and not any(re.match(r"^\s+\d+ not counted\s", ln) for ln in cited.splitlines()), cited
