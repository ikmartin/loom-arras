"""`loom library update` and `loom library add` (plan 0.18.5): the commands that fill the store, and the defects their landing fixed."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from loom.scan.bib import parse_bib
from tests.helpers import edit, json_of, ok, refused
from tests.unit._quilts import demo, propose, work_home

BIB = "digests/bibliography.bib"
HANDBOOK = "Logarithmic geometry and moduli\nDan Abramovich, Qile Chen, Danny Gillam, Yuhao Huang, Martin Olsson, Matthew Satriano, and Shenghao Sun\n"
OLSSON = "Logarithmic geometry and algebraic stacks\nMartin C. Olsson\nAnn. Sci. Ecole Norm. Sup.\n"


def _fake_pdf(path: Path, text: str) -> Path:
    """A PDF in the shape the fake toolchain's pdftotext reads (tests/fake_latex)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(f"%PDF-1.4\n%FAKE-LOOM\n%%Pages: 1\n{text}\n".encode())
    return path


def _olsson(q: Path, *, handbook_entry: bool = False) -> None:
    """Olsson's 2003 paper in the bibliography, and the handbook a fifth-author byline and half its title once filed as it."""
    with (q / BIB).open("a", encoding="utf-8") as fh:
        fh.write(
            "\n@article{olsson03, author={Olsson, Martin C.}, title={Logarithmic geometry and algebraic stacks}, year={2003}}\n"
        )
        if handbook_entry:
            fh.write(
                "\n@incollection{abramovich16, author={Abramovich, Dan and Chen, Qile and Olsson, Martin}, "
                "title={Logarithmic geometry and moduli}, year={2016}}\n"
            )


def _source_in_store(q: Path, ck: str = "Calloway14") -> None:
    """The work's source in the store, which a checkout's demo does not carry."""
    src = work_home(q, ck) / "src"
    shutil.rmtree(src, ignore_errors=True)
    src.mkdir(parents=True)
    (src / "paper.tex").write_text("\\documentclass{article}\n\\begin{document}\nCalloway.\n\\end{document}\n")


def test_redo_keeps_a_verified_result_byte_identical(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`--redo` rewrites a digest from the paper's source; a result the author verified keeps its record and its text in the digest byte for byte (CLI study, defect 3)."""
    from loom.refs.proposals import results_path

    q = demo(tmp_path)
    ck = "Calloway14"
    extracted = (q / "digests" / f"{ck}.tex").read_text()
    monkeypatch.setattr("loom.digest.extract.extract_digest", lambda *_a, **_k: (extracted, None))
    _source_in_store(q)
    propose(q, ck, "rem-4.1", 2, "Let X = {a, b} carry the indiscrete topology", "The indiscrete pair stands.")
    rid = f"{ck}-rem-4.1"
    ok("library", "verify", rid, "--as", "A. Author", "--yes", cwd=q)
    digest = q / "digests" / f"{ck}.tex"

    def node(text: str) -> str:
        start = text.index(f"\\label{{{rid}}}")
        return text[text.rindex("\\begin{", 0, start) : text.index("\\end{", start)]

    def record() -> dict[str, object]:
        return next(r for r in json.loads(results_path(q, ck).read_text())["results"] if r["id"] == rid)

    kept, before = record(), node(digest.read_text())
    r = ok("library", "update", ck, "--redo", "--only", "extract", cwd=q)
    assert digest.read_text() != extracted, "the extraction ran and the verified node was put back"
    assert node(digest.read_text()) == before
    assert record() == kept
    assert f"verified results kept through the new extraction (1)\n  {rid}  {ck}" in r.output, r.output


def test_online_is_refused_under_an_agent_without_standing_consent(tmp_path: Path) -> None:
    """An agent may not grant itself the network: `--online` under an agent marker needs `[library] online = true`, and is refused before anything is written."""
    q = demo(tmp_path)
    bib = (q / BIB).read_bytes()
    r = refused(
        "library", "update", "--online", code=2, match="--online is the author's", cwd=q, env={"CLAUDECODE": "1"}
    )
    assert "online = true under [library]" in r.output
    assert (q / BIB).read_bytes() == bib
    # standing consent is the author's, so under it the agent's run goes ahead; offline here, it asks nothing
    edit(q / "config.toml", "online = false", "online = true")
    ok("library", "update", "--online", "--only", "map", cwd=q, env={"CLAUDECODE": "1"})
    # and the author's own shell needs no consent but the flag
    edit(q / "config.toml", "online = true", "online = false")
    ok("library", "update", "--online", "--only", "map", cwd=q)


def test_a_config_with_the_retired_consent_keys_is_refused_by_name(tmp_path: Path) -> None:
    """`[refs] fetch` and `resolve` merged into `[library] online`; a config still carrying them is refused, naming the new key and the edit, rather than read without its consent."""
    q = demo(tmp_path)
    edit(q / "config.toml", "[library]\nonline = false", '[refs]\nfetch = true\nresolve = false\ncontact = "a@b.c"')
    r = refused("library", "update", code=2, match="[refs] fetch is now online under [library]", cwd=q)
    assert "[refs] resolve is now online under [library]" in r.output and "contact under [library]" in r.output
    assert '[library]\nonline = true\ncontact = "a@b.c"' in r.output
    refused("status", code=2, match="[refs] fetch", cwd=q)


def test_a_dry_run_says_what_each_step_would_do_and_writes_nothing(tmp_path: Path) -> None:
    q = demo(tmp_path)
    _fake_pdf(q / "refs" / "Hartshorne - 1977 - Algebraic Geometry.pdf", "Algebraic Geometry\nRobin Hartshorne")
    data = json_of("library", "update", "--dry-run", "--json", cwd=q)
    assert data["dry_run"] and data["would"] == {"resolve": ["Har77"], "fetch": ["Man12"], "extract": [], "map": []}
    assert [a["key"] for a in data["scan"]["added"]] == [] and data["scan"]["copied"], "it says what it would file"
    assert not (q / "digests" / "storage" / "copied.json").read_text().count("Hartshorne")
    assert {w["citekey"] for w in data["works"]} == {"Calloway14", "Har77", "Man12"}


def test_a_work_argument_narrows_every_step_and_one_naming_nothing_is_refused(tmp_path: Path) -> None:
    q = demo(tmp_path)
    data = json_of("library", "update", "Hartshorne", "--json", cwd=q)  # a fragment of an author names the work
    assert [w["citekey"] for w in data["works"]] == ["Har77"] and data["scan"] is None
    refused("library", "update", "Nobody99", code=2, match="names no work", cwd=q)


def test_a_weak_match_is_skipped_with_its_reason(tmp_path: Path) -> None:
    """The handbook names Olsson fifth and shares half the title of his 2003 paper; two weak signals filed it as that paper, and then skipped the real one because the slot was taken (audit §4)."""
    q = demo(tmp_path)
    _olsson(q)
    pile = tmp_path / "pile"
    _fake_pdf(pile / "Handbook of Moduli.pdf", HANDBOOK)
    _fake_pdf(pile / "olsson.pdf", OLSSON)
    r = ok("library", "add", pile, cwd=q)
    assert r.stdout.startswith("2 documents: 1 filed, 1 skipped, 0 refused"), r.output
    said = " ".join(r.stdout.split())
    assert "Handbook of Moduli.pdf: olsson03 is the nearest entry" in said
    assert "its title is not olsson03's in full and Olsson does not lead its byline" in said
    assert "olsson.pdf as olsson03's PDF, with its page text" in said
    home = work_home(q, "olsson03")
    assert (home / "paper.pdf").read_bytes() == (pile / "olsson.pdf").read_bytes()
    rows = {Path(d["file"]).name: d for d in json_of("library", "add", pile, "--dry-run", "--json", cwd=q)["documents"]}
    assert rows["Handbook of Moduli.pdf"]["outcome"] == "skipped" and rows["olsson.pdf"]["outcome"] == "skipped"
    assert rows["olsson.pdf"]["reason"].startswith("already in loom's store")


def test_a_pdf_naming_another_work_is_refused_and_force_records_the_override(tmp_path: Path) -> None:
    """With `--for` the check still runs: a document that shows it is another entry's is refused, naming it, exit 2, and `--force` files it and records who overrode what."""
    q = demo(tmp_path)
    _olsson(q, handbook_entry=True)
    handbook = _fake_pdf(tmp_path / "Handbook of Moduli.pdf", HANDBOOK)
    r = refused("library", "add", handbook, "--for", "olsson03", code=2, match="it is abramovich16's", cwd=q)
    assert "pass --force with --for olsson03" in r.output and not (work_home(q, "olsson03") / "paper.pdf").exists()
    refused("library", "add", handbook, "--force", code=2, match="--force applies only with --for", cwd=q)
    ok("library", "add", handbook, "--for", "olsson03", "--force", "--as", "A. Author", cwd=q)
    assert (work_home(q, "olsson03") / "paper.pdf").is_file()
    ledger = json.loads((q / "digests" / "storage" / "copied.json").read_text())
    row = next(v for v in ledger.values() if v["from"] == "Handbook of Moduli.pdf")
    assert row["forced"].startswith("it is abramovich16's") and row["by"] == "A. Author"
    # without --for it is filed under the work it shows it is
    other = _fake_pdf(tmp_path / "again.pdf", HANDBOOK + "a second printing\n")
    assert "again.pdf as abramovich16's PDF" in " ".join(ok("library", "add", other, cwd=q).stdout.split())


def test_a_second_document_is_filed_beside_the_first_and_keeps_its_pdf(tmp_path: Path) -> None:
    """`add` never replaces (book 8.16): a second PDF for a work that has one is filed beside it under a sibling entry, which names its own home in `loom-file` so it shows its own PDF and not the first's (audit §3)."""
    from loom.refs.fetch import work_dir

    q = demo(tmp_path)
    _olsson(q)
    one = _fake_pdf(tmp_path / "one.pdf", OLSSON + "first copy")
    two = _fake_pdf(tmp_path / "two.pdf", OLSSON + "second copy")
    ok("library", "add", one, cwd=q)
    r = ok("library", "add", two, "--for", "olsson03", cwd=q)
    assert "two.pdf as olsson03's PDF, beside its first document as olsson03A" in " ".join(r.stdout.split())
    entries = parse_bib((q / BIB).read_text())
    sibling = entries["olsson03A"]
    assert sibling.fields["loom-copy-of"] == "olsson03" and sibling.fields["loom-file"].startswith("file/")
    assert b"first copy" in (work_dir(q, entries["olsson03"]) / "paper.pdf").read_bytes()
    assert b"second copy" in (work_dir(q, sibling) / "paper.pdf").read_bytes()
    again = ok("library", "add", two, "--for", "olsson03", cwd=q)
    assert again.stdout.startswith("1 document: 0 filed, 1 skipped"), again.output
    assert "olsson03B" not in (q / BIB).read_text()
