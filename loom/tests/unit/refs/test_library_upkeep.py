"""`loom library review` and `loom library check` (plan 0.18.5): what waits for the person, and what has gone wrong in the library."""

from __future__ import annotations

import json
from pathlib import Path

from tests.helpers import exits, json_of, ok
from tests.unit._quilts import demo, mapped, propose, work_home

AS = ("--as", "A. Author")
FIXED = {"LOOM_FIXED_TIME": "2026-01-02T00:00:00Z"}


def test_review_lists_every_proposal_and_open_suggestion_with_its_id_last(tmp_path: Path) -> None:
    """The queue a person works through: one line per thing, its id last, and the two commands that clear it."""
    q, ck = mapped(tmp_path)
    assert ok("library", "review", cwd=q).stdout.startswith("nothing waits for review")
    propose(q, ck, "thm-4.1", 12, "Every widget is a gadget", "G")
    ok(
        "annotate", "dm-0002", "Cite Kreck.", "--kind", "citation", "--payload", "M. Kreck, Surgery and duality",
        "--as", "Referee Agent", cwd=q, env=FIXED,
    )  # fmt: skip
    r = ok("library", "review", cwd=q)
    assert r.stdout.startswith("waiting for review: 1 proposed result and 1 citation suggestion"), r.output
    assert f"{ck}  theorem 4.1  p.12  {ck}-thm-4.1" in r.stdout
    assert "on dm-0002: M. Kreck, Surgery and duality  a-2026-01-02-0001" in r.stdout
    assert "next: loom library verify ID, or loom library discard ID --why" in r.stdout
    # with a work, only that work's proposals
    only = json_of("library", "review", ck, "--json", cwd=q)
    assert [p["id"] for p in only["proposed"]] == [f"{ck}-thm-4.1"] and only["citations"] == []
    # and once decided, nothing waits
    ok("library", "discard", f"{ck}-thm-4.1", "a-2026-01-02-0001", "--why", "not needed", *AS, cwd=q)
    assert ok("library", "review", cwd=q).stdout.startswith("nothing waits for review")


def test_check_finds_a_wrong_document_an_empty_digest_a_guessed_map_and_shared_documents(tmp_path: Path) -> None:
    """Each problem under its own heading with its fix, and exit 1; a check writes nothing."""
    q, ck = mapped(tmp_path)
    home = work_home(q, ck)
    (home / "paper.pdf").write_bytes(b"%PDF-1.4\n")
    # the first page carries Calloway14's title and not its own: the wrong PDF filed against the right entry
    (home / "pages" / "0001.txt").write_text("Fixed loci of involutions on separated spaces\nI. Calloway\n")
    (home / "sections.json").write_text(json.dumps({"sha256": "0" * 64, "pages": 300, "chars": 1, "sections": []}))
    (q / "digests" / f"{ck}.tex").write_text("% !LOOM digest: Vir12\n")
    with (q / "digests" / "bibliography.bib").open("a") as fh:
        fh.write("\n@misc{DupA, title={One}, loom-file={file/abc}}\n@misc{DupB, title={Two}, loom-file={file/abc}}\n")
    before = sorted((p, p.stat().st_mtime_ns) for p in q.rglob("*") if p.is_file())
    r = exits(1, "library", "check", cwd=q)
    assert sorted((p, p.stat().st_mtime_ns) for p in q.rglob("*") if p.is_file()) == before
    out = r.stdout
    assert f"documents that are another work's (1)\n  its PDF's first page carries Calloway14's title  {ck}" in out
    assert "fix: loom library add FILE --for WORK" in out
    assert f"digests with no results recorded (1)\n  its digest records no results  {ck}" in out
    assert f"section maps that are a guess (1)\n  0 sections found in 300 pages  {ck}" in out
    assert "entries that name one document (1)\n  2 entries name one document  DupA, DupB" in out
    # narrowed to one work, the others' problems are not reported
    narrowed = json_of("library", "check", "DupA", "--json", code=1, cwd=q)
    assert [p["problem"] for p in narrowed["problems"]] == ["duplicate-document"]


def test_check_names_a_pdf_whose_first_page_carries_no_title_of_its_own(tmp_path: Path) -> None:
    """A PDF filed on weak signals carries neither its own entry's title nor another's, and was reported by nothing."""
    q, ck = mapped(tmp_path)
    home = work_home(q, ck)
    (home / "paper.pdf").write_bytes(b"%PDF-1.4\n")
    (home / "pages" / "0001.txt").write_text("Handbook of something else entirely\nA. Editor\n")
    out = exits(1, "library", "check", ck, cwd=q).stdout
    assert f"documents that may not be their work (1)\n  its PDF's first page does not carry its title  {ck}" in out
    assert "documents that are another work's" not in out


def test_a_verify_dry_run_names_what_it_would_record_and_writes_nothing(tmp_path: Path) -> None:
    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-4.1", 12, "Every widget is a gadget", "G")
    before = (q / "digests" / f"{ck}.results.json").read_text()
    r = ok("library", "verify", f"{ck}-thm-4.1", "--dry-run", *AS, cwd=q)
    assert r.stdout.startswith("dry run: would verify 1 result") and f"{ck}-thm-4.1" in r.stdout
    assert (q / "digests" / f"{ck}.results.json").read_text() == before
    assert not (q / "digests" / f"{ck}.tex").exists()


def test_import_takes_its_citekey_from_name(tmp_path: Path) -> None:
    """`--name` files the digest under another citekey; the dry run writes nothing and names where it would."""
    q = demo(tmp_path)
    src = tmp_path / "elsewhere.tex"
    src.write_text((q / "digests" / "Calloway14.tex").read_text())
    dry = ok("library", "import", str(src), "--name", "Other20", "--dry-run", cwd=q)
    assert (
        dry.stdout.startswith("dry run: would write digests/Other20.tex")
        and not (q / "digests" / "Other20.tex").exists()
    )
    ok("library", "import", str(src), "--name", "Other20", cwd=q)
    assert (q / "digests" / "Other20.tex").read_text().startswith("% !LOOM digest: Other20\n")
