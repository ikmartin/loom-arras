"""A suggestion's payload in place (plan 0.20.7): `replace` covers exactly the quoted words, `after` and `before` go beside them, no quote means the key's body; the patch, compiling as if taken, the published change, and resolving as applied."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from loom.records.annotations import find_annotation, load_records
from loom.records.suggestions import Unplaced, body_span, is_taken, patch, place
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan
from tests.helpers import edit, exits, json_of, ok, refused
from tests.unit._quilts import demo

LEMMA = "drafting/nodes/dm-0002.tex"


def suggest(q: Path, *args: str) -> str:
    """Write a suggestion on dm-0002, returning its id."""
    out = ok("annotate", "dm-0002", "Tighten it", "--type", "suggestion", *args, "--as", "Tom", cwd=q).stdout
    return out.split()[0]


def placed(q: Path, ann_id: str):  # type: ignore[no-untyped-def]
    result = scan(load_quilt(q))
    records, _ = load_records(q)
    found = find_annotation(records, ann_id)
    assert found is not None
    return result, found[1]


def test_replace_takes_exactly_the_quoted_words(tmp_path: Path) -> None:
    q = demo(tmp_path)
    a = suggest(q, "--quote", "one or two points", "--payload", "at most two points", "--placement", "replace")
    result, ann = placed(q, a)
    p = place(result, ann)
    assert p.taken.count("at most two points") == 1 and "one or two points" not in p.taken
    assert p.own.replace("one or two points", "at most two points") == p.taken
    assert not p.moved
    diff = patch(result, p)
    assert diff.startswith(f"--- a/{LEMMA}") and "-Every orbit of a widget has one or two points" in diff


def test_after_and_before_go_right_beside_the_quote_joined_by_a_space(tmp_path: Path) -> None:
    q = demo(tmp_path)
    after = suggest(q, "--quote", "one or two points", "--payload", "(and never more)", "--placement", "after")
    before = suggest(q, "--quote", "Every orbit", "--payload", "Plainly,", "--placement", "before")
    result, ann = placed(q, after)
    assert "has one or two points (and never more), and" in place(result, ann).taken
    result, ann = placed(q, before)
    assert "Plainly, Every orbit of a widget" in place(result, ann).taken


def test_with_no_quote_the_anchor_is_the_body(tmp_path: Path) -> None:
    q = demo(tmp_path)
    whole = suggest(q, "--payload", "Each orbit has one or two points.", "--placement", "replace")
    tail = suggest(q, "--payload", "Hence orbits are small.", "--placement", "after")
    result, ann = placed(q, whole)
    p = place(result, ann)
    # the head and the end stay: the label is the key's identity, and the body is all it replaces
    assert p.taken.startswith(
        "\\begin{lemma}[Orbits]\\label{dm-0002}\\label{lem:orbits}\nEach orbit has one or two points."
    )
    assert p.taken.rstrip().endswith("\\end{lemma}") and "Every orbit" not in p.taken
    result, ann = placed(q, tail)
    assert "union of the one-point orbits.\nHence orbits are small.\n\\end{lemma}" in place(result, ann).taken


def test_the_body_skips_the_head_its_label_and_its_uses() -> None:
    own = "\\begin{proof}\n\\uses{dm-0002}\nBy Lemma~\\ref{lem:orbits} it holds.\n\\end{proof}"
    a, b = body_span(own)
    assert own[a:b] == "By Lemma~\\ref{lem:orbits} it holds."
    titled = "\\begin{theorem}[{\\cite[Theorem 2.1]{Kre99}}]\\label{x}\nStatement.\n\\end{theorem}"
    a, b = body_span(titled)
    assert titled[a:b] == "Statement."


def test_an_empty_payload_deletes_the_quote(tmp_path: Path) -> None:
    q = demo(tmp_path)
    a = suggest(
        q,
        "--quote",
        ", and $\\Fix(\\sigma)$ is the union of the one-point orbits",
        "--payload",
        "",
        "--placement",
        "replace",
    )
    result, ann = placed(q, a)
    assert "has one or two points.\n" in place(result, ann).taken
    refused(
        "annotate", "dm-0002", "x", "--type", "suggestion", "--quote", "Every orbit", "--payload", "", "--placement", "after", "--as", "Tom",
        cwd=q, code=2, match="empty --payload deletes the quoted words",
    )  # fmt: skip


def test_a_suggestions_payload_needs_a_placement(tmp_path: Path) -> None:
    q = demo(tmp_path)
    refused(
        "annotate", "dm-0002", "x", "--type", "suggestion", "--quote", "Every orbit", "--payload", "Each orbit", "--as", "Tom",
        cwd=q, code=2, match="needs --placement",
    )  # fmt: skip


def test_a_quote_that_no_longer_stands_once_is_refused_and_a_moved_text_whose_quote_stands_is_said(
    tmp_path: Path,
) -> None:
    q = demo(tmp_path)
    a = suggest(q, "--quote", "one or two points", "--payload", "at most two points", "--placement", "replace")
    # the text changed elsewhere: the quote still stands, so the payload is placed and the move is said
    edit(q / LEMMA, "the union of the one-point orbits", "the union of the orbits of size one")
    result, ann = placed(q, a)
    assert place(result, ann).moved
    # the quoted words gone
    edit(q / LEMMA, "one or two points", "one point or two")
    result, ann = placed(q, a)
    try:
        place(result, ann)
        raise AssertionError("placed a quote that no longer stands")
    except Unplaced as exc:
        assert "no longer stands" in str(exc)
    # standing twice
    edit(q / LEMMA, "one point or two", "one or two points, one or two points")
    result, ann = placed(q, a)
    try:
        place(result, ann)
        raise AssertionError("placed a quote that stands twice")
    except Unplaced as exc:
        assert "2 times" in str(exc)


def test_the_cli_prints_the_patch_and_says_when_it_is_taken(tmp_path: Path) -> None:
    q = demo(tmp_path)
    a = suggest(q, "--quote", "one or two points", "--payload", "at most two points", "--placement", "replace")
    out = ok("suggestion", a, cwd=q).stdout
    assert out.startswith(f"--- a/{LEMMA}") and "+Every orbit of a widget has at most two points" in out
    data = json_of("suggestion", a, "--json", cwd=q)
    assert data["file"] == LEMMA and data["moved"] is False and data["diff"] == out
    edit(q / LEMMA, "one or two points", "at most two points")
    assert "already reads as" in ok("suggestion", a, cwd=q).stdout
    # whatever its type, an annotation carrying text is a change to the text, and one carrying none is not
    untyped = ok(
        "annotate", "dm-0002", "See", "--quote", "Every orbit", "--payload", "Each orbit", "--placement", "replace",
        "--as", "Tom", cwd=q,
    ).stdout.split()[0]  # fmt: skip
    assert "+Each orbit of a widget" in ok("suggestion", untyped, cwd=q).stdout
    note = ok("annotate", "dm-0002", "See", "--quote", "Every orbit", "--as", "Tom", cwd=q).stdout.split()[0]
    exits(1, "suggestion", note, cwd=q, match="carries no payload")


def test_is_taken_for_each_placement(tmp_path: Path) -> None:
    q = demo(tmp_path)
    rep = suggest(q, "--quote", "one or two points", "--payload", "at most two points", "--placement", "replace")
    ins = suggest(q, "--quote", "Every orbit", "--payload", "Plainly,", "--placement", "before")
    gone = suggest(q, "--quote", " of a widget", "--payload", "", "--placement", "replace")
    for a in (rep, ins, gone):
        assert not is_taken(*placed(q, a))
    edit(q / LEMMA, "Every orbit of a widget has one or two points", "Plainly, Every orbit has at most two points")
    for a in (rep, ins, gone):
        assert is_taken(*placed(q, a)), a


def test_resolving_as_applied_waits_for_the_text_and_records_its_hash(tmp_path: Path) -> None:
    from loom.render.manifest import key_hash

    q = demo(tmp_path)
    a = suggest(q, "--quote", "one or two points", "--payload", "at most two points", "--placement", "replace")
    exits(1, "annotate", "--resolve", a, "Taken", "--applied", "--as", "Tom", cwd=q, match="does not yet read as")
    edit(q / LEMMA, "one or two points", "at most two points")
    ok("annotate", "--resolve", a, "Taken as written", "--applied", "--as", "Tom", cwd=q)
    result, ann = placed(q, a)
    assert ann.status == "resolved" and ann.applied == {"hash": key_hash(result, "dm-0002")}
    assert ann.resolved_why == "Taken as written"
    refused("annotate", "--resolve", a, "--applied", "--undo", "--as", "Tom", cwd=q, code=2, match="not --undo")
    # an undo takes the application back with the resolution
    ok("annotate", "--resolve", a, "--undo", "--as", "Tom", cwd=q)
    assert placed(q, a)[1].applied is None


def test_the_manifest_carries_each_open_suggestions_change(tmp_path: Path) -> None:
    q = demo(tmp_path)
    ready = suggest(q, "--quote", "one or two points", "--payload", "at most two points", "--placement", "replace")
    lost = suggest(q, "--quote", "the one-point orbits", "--payload", "the fixed points", "--placement", "replace")
    edit(q / LEMMA, "the one-point orbits", "the orbits of size one")
    ok("build", cwd=q)
    m = json.loads((q / ".loom/build" / "manifest.json").read_text())
    change = m["annotations"][ready]["change"]
    assert change["state"] == "ready" and change["moved"] is True
    fragment = (q / ".loom/build" / change["fragment"]).read_text()
    assert "review-changed" in fragment and "most" in fragment
    assert (q / ".loom/build" / change["diff"]).read_text().startswith(f"--- a/{LEMMA}")
    assert m["annotations"][lost]["change"] == {"state": "unplaced", "why": m["annotations"][lost]["change"]["why"]}
    assert "no longer stands" in m["annotations"][lost]["change"]["why"]
    # taken, then resolved as applied: the change gives way to what was recorded
    edit(q / LEMMA, "one or two points", "at most two points")
    ok("build", cwd=q)
    assert json.loads((q / ".loom/build" / "manifest.json").read_text())["annotations"][ready]["change"] == {
        "state": "taken"
    }
    ok("annotate", "--resolve", ready, "--applied", "--as", "Tom", cwd=q)
    ok("build", cwd=q)
    entry = json.loads((q / ".loom/build" / "manifest.json").read_text())["annotations"][ready]
    assert "change" not in entry and entry["applied"]["hash"]


def _session(q: Path) -> str:
    from loom.sessions import active

    s = active(q)
    assert s
    return s


def test_apply_writes_it_in_keeping_a_version_first_and_resolves_it_as_applied(tmp_path: Path) -> None:
    from loom.history.acts import APPLY
    from loom.history.ledger import load_history
    from loom.render.manifest import key_hash

    q = demo(tmp_path)
    a = suggest(q, "--quote", "one or two points", "--payload", "at most two points", "--placement", "replace")
    out = ok("suggestion", "apply", a, "--as", "Tom", cwd=q).stdout
    assert "applied" in out and "a version of" in out
    assert "at most two points" in (q / LEMMA).read_text() and "one or two points" not in (q / LEMMA).read_text()
    result, ann = placed(q, a)
    assert ann.status == "resolved" and ann.applied == {"hash": key_hash(result, "dm-0002")}
    history = load_history(result.quilt.history_dir)
    kept = [e for e in history.landmarks() if e.get("kept_for") == APPLY]
    assert kept and kept[-1].message == "Before applying a suggestion"
    assert "one or two points" in history.landmark_path(kept[-1]).read_text()  # the text it replaced
    line = [e for e in history.entries if e.action == APPLY][-1]
    assert (line.get("annotation"), line.get("key"), line.get("path")) == (a, "dm-0002", LEMMA)


def test_apply_over_the_api_is_the_authors_and_says_why_it_cannot(tmp_path: Path) -> None:
    from loom.render.api import ApiError, handle

    q = demo(tmp_path)
    a = suggest(q, "--quote", "one or two points", "--payload", "at most two points", "--placement", "replace")
    prose = suggest(q, "--quote", "Every orbit")
    lost = suggest(q, "--quote", "the one-point orbits", "--payload", "the fixed points", "--placement", "replace")
    session = _session(q)
    body = {"session": session, "author": "Tom"}
    with pytest.raises(ApiError) as agent:
        handle(q, "suggestion-apply", {**body, "annotation": a, "author": "Claude Agent"})
    assert (agent.value.code, agent.value.status) == ("author-only", 403)
    with pytest.raises(ApiError) as no_text:
        handle(q, "suggestion-apply", {**body, "annotation": prose})
    assert no_text.value.code == "not-a-suggestion" and "carries no text" in no_text.value.message
    edit(q / LEMMA, "the one-point orbits", "the orbits of size one")
    with pytest.raises(ApiError) as unplaced:
        handle(q, "suggestion-apply", {**body, "annotation": lost})
    assert unplaced.value.code == "unplaced"
    said = handle(q, "suggestion-apply", {**body, "annotation": a})["result"]
    assert said.startswith("applied the suggestion in main.tex") and "a version of main.tex" in said
    with pytest.raises(ApiError) as again:
        handle(q, "suggestion-apply", {**body, "annotation": a})
    assert again.value.code == "not-open"
    # nothing was written for the refused ones
    assert "the orbits of size one" in (q / LEMMA).read_text()


def test_a_suggestion_on_an_agents_copy_is_not_applied_since_it_comes_in_with_the_copy(tmp_path: Path) -> None:
    import shutil

    from loom.render.api import ApiError, handle
    from tests.unit._quilts import REPO

    q = tmp_path / "q"
    shutil.copytree(REPO / "tests" / "quilts" / "synthetic", q, ignore=shutil.ignore_patterns("build", ".git"))
    out = ok(
        "annotate",
        "sy-0002-ai",
        "Shorter",
        "--type",
        "suggestion",
        "--quote",
        "at most two points",
        "--payload",
        "two points at most",
        "--placement",
        "replace",
        "--as",
        "Tom",
        cwd=q,
    ).stdout
    with pytest.raises(ApiError) as copy:
        handle(q, "suggestion-apply", {"annotation": out.split()[0], "session": _session(q), "author": "Tom"})
    assert copy.value.code == "on-a-copy" and "aidoc.tex" in copy.value.message
