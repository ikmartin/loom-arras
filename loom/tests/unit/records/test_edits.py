"""Suggested edits (plan 0.30, decision 10): filed with `loom suggest`, placed by `replace`, `before` and `after` or on the key's body, printed as a patch, kept or discarded by the person, published with their change, and told to the agent that suggested them."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from loom.records.edits import Edit, Unplaced, body_span, find, is_taken, patch, place, replay
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan
from tests.helpers import copy, edit, exits, flat, json_of, ok, refused, run
from tests.unit._quilts import demo

LEMMA = "drafting/nodes/dm-0002.tex"
AGENT = {"AI_AGENT": "1"}


@pytest.fixture(autouse=True)
def tom() -> None:
    """The person keeping and discarding, by the name their config gives `loom changes`."""
    from loom.scan.quilt import save_author

    save_author("Tom")


def suggest(q: Path, *args: str, who: str = "Tom", key: str = "dm-0002", env: dict[str, str] | None = None) -> str:
    """File a suggested edit on `key`, returning its id."""
    return str(json_of("suggest", key, *args, "--as", who, "--json", cwd=q, env=env)["edit"])


def placed(q: Path, edit_id: str) -> tuple[Any, Edit]:
    found = find(q, edit_id)
    assert found is not None
    return scan(load_quilt(q)), found


def log(q: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in (q / ".loom/edits" / "log.jsonl").read_text().splitlines() if x.strip()]


def test_filing_records_the_key_the_words_the_new_text_and_where_it_goes(tmp_path: Path) -> None:
    q = demo(tmp_path)
    ann = ok("annotate", "dm-0002", "Too vague.", "--type", "revision", "--as", "Tom", cwd=q).stdout.split()[0]
    said = ok(
        "suggest", "dm-0002", "--quote", "one or two points", "--with", "at most two points", "--answers", ann,
        "--comment", "Sharper.", "--as", "Tom", cwd=q,
    ).stdout  # fmt: skip
    e = log(q)[-1]
    assert said.startswith(e["id"]) and e["id"].startswith("e-") and "replace" in said and "dm-0002" in said
    assert (e["target"], e["anchor"]["exact"], e["with"], e["placement"], e["answers"], e["comment"]) == (
        "dm-0002",
        "one or two points",
        "at most two points",
        "replace",
        ann,
        "Sharper.",
    )
    assert e["against"].startswith("sha256:") and (e["author"], e["kind"]) == ("Tom", "human")
    before = suggest(q, "--quote", "Every orbit", "--with", "Plainly,", "--before")
    after = suggest(q, "--quote", "one or two points", "--with", "(and never more)", "--after")
    body = suggest(q, "--with", "\\uses{dm-0001}", "--before")
    assert [find(q, x).placement for x in (before, after, body)] == ["before", "after", "before"]  # type: ignore[union-attr]
    assert find(q, body).selector is None  # type: ignore[union-attr]
    # the new text from stdin, as LaTeX a shell would mangle
    piped = json_of(
        "suggest",
        "dm-0002",
        "--quote",
        "Every orbit",
        "--with",
        "-",
        "--as",
        "Tom",
        "--json",
        cwd=q,
        stdin="Each orbit",
    )
    assert find(q, piped["edit"]).with_text == "Each orbit"  # type: ignore[union-attr]
    # a dry run writes nothing
    n = len(log(q))
    ok("suggest", "dm-0002", "--with", "x", "--dry-run", "--as", "Tom", cwd=q)
    assert len(log(q)) == n


def test_what_an_edit_cannot_say_is_refused_by_name(tmp_path: Path) -> None:
    q = demo(tmp_path)
    before = log(q)
    base = ("suggest", "dm-0002", "--as", "Tom")
    refused(*base, "--quote", "no such words", "--with", "x", cwd=q, code=2, match="quote not found in dm-0002")
    refused(*base, "--quote", "o", "--with", "x", cwd=q, code=2, match="ambiguous")
    refused(*base, "--with", "x", "--before", "--after", cwd=q, code=2, match="--before and --after")
    refused(*base, "--with", "x", "--answers", "a-1999-01-01-ekn992", cwd=q, code=2, match="no annotation")
    refused(*base, "--with", "", cwd=q, code=2, match="needs --quote")
    refused(
        *base, "--quote", "Every orbit", "--with", "", "--after", cwd=q, code=2, match="neither --before nor --after"
    )
    refused(*base, "--quote", "Every orbit", "--with", "Every orbit", cwd=q, code=2, match="changes nothing")
    refused("suggest", "dm-9999", "--with", "x", "--as", "Tom", cwd=q, code=2, match="dm-9999")
    assert log(q) == before


def test_replace_takes_exactly_the_quoted_words(tmp_path: Path) -> None:
    q = demo(tmp_path)
    p_ = place(*placed(q, suggest(q, "--quote", "one or two points", "--with", "at most two points")))
    assert p_.taken.count("at most two points") == 1 and "one or two points" not in p_.taken
    assert p_.own.replace("one or two points", "at most two points") == p_.taken and not p_.moved
    result, e = placed(q, find_last(q))
    assert patch(result, place(result, e)).startswith(f"--- a/{LEMMA}")


def find_last(q: Path) -> str:
    return replay(q)[0][-1].id


def test_after_and_before_go_right_beside_the_quote_joined_by_a_space(tmp_path: Path) -> None:
    q = demo(tmp_path)
    after = suggest(q, "--quote", "one or two points", "--with", "(and never more)", "--after")
    before = suggest(q, "--quote", "Every orbit", "--with", "Plainly,", "--before")
    assert "has one or two points (and never more), and" in place(*placed(q, after)).taken
    assert "Plainly, Every orbit of a widget" in place(*placed(q, before)).taken


def test_with_no_quote_the_anchor_is_the_body(tmp_path: Path) -> None:
    q = demo(tmp_path)
    whole = place(*placed(q, suggest(q, "--with", "Each orbit has one or two points.")))
    # the head and the end stay: the label is the key's identity, and the body is all it replaces
    assert whole.taken.startswith(
        "\\begin{lemma}[Orbits]\\label{dm-0002}\\label{lem:orbits}\nEach orbit has one or two points."
    )
    assert whole.taken.rstrip().endswith("\\end{lemma}") and "Every orbit" not in whole.taken
    tail = place(*placed(q, suggest(q, "--with", "Hence orbits are small.", "--after")))
    assert "union of the one-point orbits.\nHence orbits are small.\n\\end{lemma}" in tail.taken
    head = place(*placed(q, suggest(q, "--with", "\\uses{dm-0001}", "--before")))
    assert "\\label{lem:orbits}\n\\uses{dm-0001}\nEvery orbit" in head.taken


def test_the_body_skips_the_head_its_label_and_its_uses() -> None:
    own = "\\begin{proof}\n\\uses{dm-0002}\nBy Lemma~\\ref{lem:orbits} it holds.\n\\end{proof}"
    a, b = body_span(own)
    assert own[a:b] == "By Lemma~\\ref{lem:orbits} it holds."
    titled = "\\begin{theorem}[{\\cite[Theorem 2.1]{Kre99}}]\\label{x}\nStatement.\n\\end{theorem}"
    a, b = body_span(titled)
    assert titled[a:b] == "Statement."


def test_an_empty_text_deletes_the_quote(tmp_path: Path) -> None:
    q = demo(tmp_path)
    gone = suggest(q, "--quote", ", and $\\Fix(\\sigma)$ is the union of the one-point orbits", "--with", "")
    assert "has one or two points.\n" in place(*placed(q, gone)).taken


def test_a_quote_that_no_longer_stands_once_is_refused_and_a_moved_text_whose_quote_stands_is_said(
    tmp_path: Path,
) -> None:
    q = demo(tmp_path)
    a = suggest(q, "--quote", "one or two points", "--with", "at most two points")
    edit(q / LEMMA, "the union of the one-point orbits", "the union of the orbits of size one")
    assert place(*placed(q, a)).moved
    edit(q / LEMMA, "one or two points", "one point or two")
    with pytest.raises(Unplaced, match="no longer stands"):
        place(*placed(q, a))
    edit(q / LEMMA, "one point or two", "one or two points, one or two points")
    with pytest.raises(Unplaced, match="2 times"):
        place(*placed(q, a))


def test_is_taken_for_each_placement(tmp_path: Path) -> None:
    q = demo(tmp_path)
    rep = suggest(q, "--quote", "one or two points", "--with", "at most two points")
    ins = suggest(q, "--quote", "Every orbit", "--with", "Plainly,", "--before")
    gone = suggest(q, "--quote", " of a widget", "--with", "")
    for a in (rep, ins, gone):
        assert not is_taken(*placed(q, a))
    edit(q / LEMMA, "Every orbit of a widget has one or two points", "Plainly, Every orbit has at most two points")
    for a in (rep, ins, gone):
        assert is_taken(*placed(q, a)), a


def test_the_cli_lists_edits_and_prints_the_patch(tmp_path: Path) -> None:
    q = demo(tmp_path)
    mine = suggest(q, "--quote", "one or two points", "--with", "at most two points")
    theirs = suggest(q, "--quote", "Every orbit", "--with", "Each orbit", who="Referee Agent", env=AGENT)
    out = ok("changes", mine, cwd=q).stdout
    assert out.startswith(f"--- a/{LEMMA}") and "+Every orbit of a widget has at most two points" in out
    data = json_of("changes", mine, "--json", cwd=q)
    assert data["change"]["path"] == LEMMA and data["patch"] == out
    exits(2, "changes", "e-1999-01-01-ekn992", cwd=q, match="no change e-1999-01-01-ekn992")
    assert {mine, theirs} <= {c["id"] for c in json_of("changes", "--json", cwd=q)["changes"]}
    assert [e["id"] for e in json_of("changes", "--by", "Tom", "--json", cwd=q)["edits"]] == [mine]
    assert [e["id"] for e in json_of("changes", "--by", "Referee Agent", "--json", cwd=q)["edits"]] == [theirs]
    ok("suggest", "--withdraw", theirs, "--why", "not needed", "--as", "Referee Agent", cwd=q, env=AGENT)
    listed = json_of("changes", "--by", "Referee Agent", "--json", cwd=q)["edits"]
    assert [(e["id"], e["status"], e["why"]) for e in listed] == [(theirs, "discarded", "not needed")]
    edit(q / LEMMA, "one or two points", "at most two points")
    (row,) = [c for c in json_of("changes", "--json", cwd=q)["changes"] if c["id"] == mine]
    assert row["state"] == "taken"


def test_keep_writes_it_in_keeping_a_version_first_and_keeping_it_resolves_what_it_answers(tmp_path: Path) -> None:
    from loom.history.acts import APPLY
    from loom.history.ledger import load_history
    from loom.records.annotations import find_annotation, load_records
    from loom.render.manifest import key_hash

    q = demo(tmp_path)
    ann = ok("annotate", "dm-0002", "Too vague.", "--type", "revision", "--as", "Tom", cwd=q).stdout.split()[0]
    a = suggest(
        q,
        "--quote",
        "one or two points",
        "--with",
        "at most two points",
        "--answers",
        ann,
        who="Referee Agent",
        env=AGENT,
    )
    refused("changes", "--keep", a, cwd=q, env=AGENT, code=2, match="author's")
    out = flat(ok("changes", "--keep", a, cwd=q).stdout)
    assert out.startswith("kept 1 change")
    assert "at most two points" in (q / LEMMA).read_text() and "one or two points" not in (q / LEMMA).read_text()
    result, e = placed(q, a)
    assert e.status == "kept" and e.kept == {"hash": key_hash(result, "dm-0002")}
    found = find_annotation(load_records(q)[0], ann)
    assert found is not None and found[1].status == "resolved" and found[1].resolved_why == f"kept suggested edit {a}"
    history = load_history(result.quilt.history_dir)
    kept = [x for x in history.landmarks() if x.get("kept_for") == APPLY]
    assert kept and kept[-1].message == "Before keeping a suggested edit"
    line = [x for x in history.entries if x.action == APPLY][-1]
    assert (line.get("edit"), line.get("key"), line.get("path")) == (a, "dm-0002", LEMMA)
    exits(2, "changes", "--keep", a, cwd=q, match=f"no change {a}")
    # an edit the author took by hand is kept without writing, and discarding leaves what it answers alone
    other = ok("annotate", "dm-0002", "Say plainly.", "--type", "revision", "--as", "Tom", cwd=q).stdout.split()[0]
    by_hand = suggest(q, "--quote", "Every orbit", "--with", "Each orbit", "--answers", other)
    edit(q / LEMMA, "Every orbit", "Each orbit")
    assert ok("changes", "--keep", by_hand, cwd=q).stdout.startswith("kept 1 change")
    assert find(q, by_hand).status == "kept"  # type: ignore[union-attr]
    dropped = suggest(q, "--quote", "Each orbit", "--with", "Any orbit", "--answers", other)
    ok("changes", "--discard", dropped, cwd=q)
    assert find(q, dropped).status == "discarded"  # type: ignore[union-attr]


def test_an_agent_withdraws_only_its_own_and_the_viewers_undo_opens_one_again(tmp_path: Path) -> None:
    from loom.render.api import handle

    q = demo(tmp_path)
    mine = suggest(q, "--quote", "Every orbit", "--with", "Each orbit")
    theirs = suggest(q, "--quote", "one or two points", "--with", "two points", who="Referee Agent", env=AGENT)
    refused("suggest", "--withdraw", mine, "--as", "Referee Agent", cwd=q, env=AGENT, code=2, match="only your own")
    ok("suggest", "--withdraw", theirs, "--why", "wrong count", "--as", "Referee Agent", cwd=q, env=AGENT)
    assert (find(q, theirs).status, find(q, theirs).why) == ("discarded", "wrong count")  # type: ignore[union-attr]
    refused(
        "suggest", "--withdraw", theirs, "--as", "Referee Agent", cwd=q, env=AGENT, code=2, match="discarded already"
    )
    handle(q, "change-discard", {"changes": [theirs], "undo": True, "author": "Tom"})
    assert find(q, theirs).status == "open"  # type: ignore[union-attr]
    assert [e["event"] for e in log(q) if e["id"] == theirs] == ["created", "discarded", "reopened"]


def test_since_tells_an_agent_what_became_of_its_edits_once(tmp_path: Path) -> None:
    q = demo(tmp_path)
    who = "Referee Agent"
    a = suggest(q, "--quote", "one or two points", "--with", "at most two points", who=who, env=AGENT)
    b = suggest(q, "--quote", "Every orbit", "--with", "Each orbit", who=who, env=AGENT)
    json_of("since", "--as", who, "--json", cwd=q, env=AGENT)
    ok("changes", "--keep", a, cwd=q)
    ok("changes", "--discard", b, "--why", "no", cwd=q)
    got = json_of("since", "--as", who, "--json", cwd=q, env=AGENT)
    assert {(e["id"], e["act"], e["by"], e["why"]) for e in got["edits"]} == {
        (a, "kept", "Tom", ""),
        (b, "discarded", "Tom", "no"),
    }
    assert json_of("since", "--as", who, "--json", cwd=q, env=AGENT)["edits"] == []


def test_two_clones_merge_their_edits_each_with_an_id_of_its_own_and_a_bad_line_is_reported(tmp_path: Path) -> None:
    q = demo(tmp_path)
    one, two = copy(q, tmp_path / "one"), copy(q, tmp_path / "two")
    mine = suggest(one, "--quote", "Every orbit", "--with", "Each orbit")
    theirs = suggest(two, "--quote", "Every orbit", "--with", "Each orbit")
    assert mine != theirs
    with (one / ".loom/edits" / "log.jsonl").open("a", encoding="utf-8") as fh:
        fh.write((two / ".loom/edits" / "log.jsonl").read_text().splitlines()[-1] + "\n")
        fh.write("{not json\n")
        fh.write(json.dumps({"event": "kept", "id": "e-1999-01-01-ekn992"}) + "\n")
    edits, problems = replay(one)
    assert {mine, theirs} <= {e.id for e in edits}
    assert len(problems) == 2 and "Expecting property name" in problems[0]
    assert problems[1].endswith(": kept names unknown edit e-1999-01-01-ekn992")
    diags = json.loads(run("lint", "--json", cwd=one).stdout)["diagnostics"]
    assert any("not a valid suggested edit" in d["message"] for d in diags)
    assert not [d for d in diags if d["code"] == "loom:repeated-id"]
    # one id given twice is the merge conflict a reply or a link could not tell apart
    with (one / ".loom/edits" / "log.jsonl").open("a", encoding="utf-8") as fh:
        first = json.loads((one / ".loom/edits" / "log.jsonl").read_text().splitlines()[0])
        fh.write(json.dumps({**first, "with": "a second text"}) + "\n")
    diags = json.loads(run("lint", "--json", cwd=one).stdout)["diagnostics"]
    assert any(d["code"] == "loom:repeated-id" and ".loom/edits/log.jsonl" in d["message"] for d in diags)


def test_the_manifest_publishes_each_edit_as_its_record_and_an_open_one_as_a_change(tmp_path: Path) -> None:
    q = demo(tmp_path)
    ready = suggest(q, "--quote", "one or two points", "--with", "at most two points", "--comment", "Sharper *here*.")
    lost = suggest(q, "--quote", "the one-point orbits", "--with", "the fixed points")
    edit(q / LEMMA, "the one-point orbits", "the orbits of size one")
    ok("build", cwd=q)
    m = json.loads((q / ".loom/build" / "manifest.json").read_text())
    row = m["suggested_edits"][ready]
    assert (row["target"]["key"], row["quote"], row["with"], row["placement"], row["status"]) == (
        "dm-0002",
        "one or two points",
        "at most two points",
        "replace",
        "open",
    )
    # `with_html` is made by TeX, so it is checked in the tex suite (test_review_commands.py, the proposed theorem)
    assert "<em>here</em>" in row["comment_html"] and "change" not in row
    change = {c["id"]: c for c in m["changes"]}
    assert change[ready]["state"] == "ready" and change[ready]["block"]["fragment"].startswith("fragments/changes/")
    assert (q / ".loom/build" / change[ready]["diff"]).read_text().startswith(f"--- a/{LEMMA}")
    assert change[lost]["state"] == "unplaced" and change[lost]["block"] is None
    assert all("payload" not in a and "placement" not in a for a in m["annotations"].values())
    edit(q / LEMMA, "one or two points", "at most two points")
    ok("build", cwd=q)
    assert {c["id"]: c for c in json.loads((q / ".loom/build" / "manifest.json").read_text())["changes"]}[ready][
        "state"
    ] == "taken"
    ok("changes", "--keep", ready, cwd=q)
    ok("build", cwd=q)
    m = json.loads((q / ".loom/build" / "manifest.json").read_text())
    assert m["suggested_edits"][ready]["status"] == "kept" and ready not in {c["id"] for c in m["changes"]}


def test_keep_and_discard_over_the_api(tmp_path: Path) -> None:
    from loom.render.api import ApiError, handle

    q = demo(tmp_path)
    a = suggest(q, "--quote", "one or two points", "--with", "at most two points")
    lost = suggest(q, "--quote", "the one-point orbits", "--with", "the fixed points")
    theirs = suggest(q, "--quote", "Every orbit", "--with", "Each orbit", who="Referee Agent", env=AGENT)
    with pytest.raises(ApiError) as agent:
        handle(q, "change-keep", {"changes": [a], "author": "Claude Agent"})
    assert (agent.value.code, agent.value.status) == ("author-only", 403)
    with pytest.raises(ApiError) as missing:
        handle(q, "change-keep", {"changes": ["e-1999-01-01-ekn992"], "author": "Tom"})
    assert (missing.value.code, missing.value.status) == ("no-such-change", 404)
    edit(q / LEMMA, "the one-point orbits", "the orbits of size one")
    said = handle(q, "change-keep", {"changes": [lost, a], "author": "Tom"})
    assert said["done"] == [a] and [r["id"] for r in said["refused"]] == [lost]
    assert said["result"].startswith("kept 1 change; 1 could not be")
    with pytest.raises(ApiError) as again:
        handle(q, "change-keep", {"changes": [a], "author": "Tom"})
    assert again.value.code == "no-such-change"
    got = handle(q, "change-discard", {"changes": [theirs], "why": "no", "author": "Tom"})
    assert got["done"] == [theirs] and find(q, theirs).why == "no"  # type: ignore[union-attr]
    assert handle(q, "change-discard", {"changes": [theirs], "undo": True, "author": "Tom"})["done"] == [theirs]


def test_new_text_that_opens_a_section_is_kept_once_and_never_written_twice(tmp_path: Path) -> None:
    from loom.render.api import ApiError, handle

    q = demo(tmp_path)
    main = q / "drafting/main.tex"
    added = "\\section*{Preface}\nA word before the setup.\n\\begin{proof}[Answer]\n\\end{proof}"
    a = suggest(q, "--quote", "\\maketitle", "--with", added, "--after", key="drafting/main.tex")
    assert not is_taken(*placed(q, a))
    said = handle(q, "change-keep", {"changes": [a], "author": "Tom"})
    assert said["done"] == [a] and said["refused"] == []
    result, e = placed(q, a)
    # the section it opens is the master's child now, and the master still reads as it taken
    assert e.status == "kept" and is_taken(result, e)
    with pytest.raises(ApiError) as again:
        handle(q, "change-keep", {"changes": [a], "author": "Tom"})
    assert again.value.code == "no-such-change"
    assert main.read_text().count("A word before the setup.") == 1


def test_a_replacement_that_keeps_its_quote_and_opens_a_section_reads_as_taken(tmp_path: Path) -> None:
    q = demo(tmp_path)
    new = "\\maketitle\n\\section*{Note}\nRead the setup first."
    a = suggest(q, "--quote", "\\maketitle", "--with", new, key="drafting/main.tex")
    assert not is_taken(*placed(q, a))
    ok("changes", "--keep", a, cwd=q)
    result, e = placed(q, a)
    assert e.status == "kept" and is_taken(result, e)
    # the quote standing again outside the new text is the replacement undone
    edit(q / "drafting/main.tex", "\\begin{document}", "\\begin{document}\n\\maketitle")
    assert not is_taken(*placed(q, a))


def test_an_edit_on_an_empty_file_is_kept_as_the_whole_file(tmp_path: Path) -> None:
    from loom.render.api import handle

    q = demo(tmp_path)
    blank = q / "drafting/sheet.tex"
    blank.write_text("")
    whole = "\\documentclass{article}\n\\begin{document}\nOne problem.\n\\end{document}\n"
    a = suggest(q, "--with", whole, key="drafting/sheet.tex")
    assert place(*placed(q, a)).at == (0, 0)
    assert handle(q, "change-keep", {"changes": [a], "author": "Tom"})["done"] == [a]
    assert blank.read_text() == whole


def test_an_edit_on_an_agents_copy_is_not_kept_since_it_comes_in_with_the_copy(tmp_path: Path) -> None:
    import shutil

    from loom.render.api import handle
    from tests.unit._quilts import REPO

    q = tmp_path / "q"
    shutil.copytree(REPO / "tests" / "quilts" / "synthetic", q, ignore=shutil.ignore_patterns("build", ".git"))
    e = suggest(q, "--quote", "at most two points", "--with", "two points at most", key="sy-0002-ai")
    said = handle(q, "change-keep", {"changes": [e], "author": "Tom"})
    assert said["done"] == [] and said["refused"][0]["id"] == e and "aidoc.tex" in said["refused"][0]["why"]


def test_compile_with_an_edit_substitutes_its_text(tmp_path: Path) -> None:
    from loom.cli.build_cmds import substitution_for

    q = demo(tmp_path)
    a = suggest(q, "--quote", "one or two points", "--with", "at most two points")
    region = substitution_for(scan(load_quilt(q)), "dm-0002", a)
    assert "at most two points" in region and "one or two points" not in region


def test_keep_all_keeps_the_suggested_edits_where_edits_in_place_are_not_tracked(tmp_path: Path) -> None:
    """With no look and no tracking, Keep all has no look to take first: it keeps what waits."""
    from loom.render.api import handle
    from loom.scan.quilt import save_author

    save_author("Tom")
    q = demo(tmp_path)
    a = suggest(q, "--quote", "one or two points", "--with", "at most two points")
    said = handle(q, "change-keep", {"all": True, "author": "Tom"})
    assert a in said["done"] and "first look" not in said["result"]
    assert "at most two points" in (q / LEMMA).read_text()
