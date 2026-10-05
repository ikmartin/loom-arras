"""A result's state as read (plan 0.18.5b item 1): `extracted` by loom, `verified` only by a person, derived on read with no file rewritten."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from loom.refs.proposals import EXTRACTED, PROPOSED, VERIFIED, Result, state_of
from tests.helpers import json_of, ok, refused
from tests.unit._quilts import demo, propose, work_home

CK = "Calloway14"
RID = "Calloway14-prop-3.2"
SPLIT = (
    "% !LOOM digest: Split\n% !LOOM prefix: Split\n% !LOOM extracted-from: arXiv:2001.00002v1\n"
    "% !LOOM published-as: doi:10.1090/S1\n% !LOOM method: extract\n"
    "\\section*{Overview}\nO.\n"
    "\\begin{theorem}[{\\cite[Theorem 1]{Split}}]\\label{Split-thm-1}\nEvery widget splits.\n\\end{theorem}\n"
)


def _results_bytes(q: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in sorted((q / "digests").glob("*.results.json"))}


def test_state_of_reads_a_mechanical_result_as_extracted_until_a_person_verifies_it() -> None:
    mechanical = Result(id="X-thm-1", local="thm-1", cls="mechanical", state=VERIFIED, origin=[{"act": "extracted"}])
    assert state_of(mechanical) == EXTRACTED
    assert state_of(Result(id="X-thm-1", local="thm-1", cls="mechanical", state=EXTRACTED)) == EXTRACTED
    for act in ("verified", "edited"):
        mechanical.origin.append({"act": act, "by": "A. Author"})
        assert state_of(mechanical) == VERIFIED
        mechanical.origin.pop()
    assert state_of(Result(id="X-thm-2", local="thm-2", cls="anchored", state=VERIFIED)) == VERIFIED
    assert state_of(Result(id="X-thm-3", local="thm-3", cls="anchored", state=PROPOSED)) == PROPOSED


def test_a_mechanical_result_reads_extracted_everywhere_and_no_file_is_written(tmp_path: Path) -> None:
    """Results recorded before 0.18.5b say `verified` with no person's act, as the author's quilt's 3,140 do; every reader says `extracted`, and the stored files stay byte for byte."""
    q = demo(tmp_path)
    stored = q / "digests" / f"{CK}.results.json"
    stored.write_text(stored.read_text().replace('"state": "extracted"', '"state": "verified"'))
    before = _results_bytes(q)
    assert {r["state"] for r in json.loads(stored.read_text())["results"]} == {"verified"}

    why = ok("library", "why", RID, cwd=q).stdout
    assert why.startswith(f"{RID}, extracted by loom, from {CK}") and "verified" not in why.split("\n")[0]
    assert json_of("library", "why", RID, "--json", cwd=q)["state"] == "extracted"
    hits = json_of("library", "search", "involution", "--json", cwd=q)["hits"]
    assert hits and {h["state"] for h in hits} == {"extracted"}
    assert "extracted by loom, best match first" in ok("library", "search", "involution", cwd=q).stdout
    row = next(w for w in json_of("library", "--json", cwd=q)["works"] if w["citekey"] == CK)
    assert (row["extracted"], row["verified"], row["waiting"]) == (5, 0, 0)
    ok("build", cwd=q)
    results = json.loads((q / "build" / "manifest.json").read_text())["references"][CK]["results"]
    assert {r["state"] for r in results.values()} == {"extracted"}
    assert _results_bytes(q) == before


def test_a_fresh_extraction_records_extracted(tmp_path: Path) -> None:
    from loom.refs.proposals import record_extracted, results_path
    from loom.scan.quilt import load_quilt
    from loom.scan.scan import scan

    q = demo(tmp_path)
    results_path(q, CK).unlink()
    assert record_extracted(scan(load_quilt(q)), CK) == 5
    stored = json.loads(results_path(q, CK).read_text())["results"]
    assert {r["state"] for r in stored} == {"extracted"} and {r["class"] for r in stored} == {"mechanical"}


def test_a_person_verifying_an_extracted_result_makes_it_verified_through_a_redo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verified by the author, a mechanical result reads `verified by NAME`, and a fresh extraction that no longer states it puts it back."""
    q = demo(tmp_path)
    digest = q / "digests" / f"{CK}.tex"
    text = digest.read_text()
    start = text.index("\\begin{proposition}[{\\cite[Proposition 3.2")
    end = text.index("\\end{proposition}", start) + len("\\end{proposition}\n")
    without = text[:start] + text[end:]
    monkeypatch.setattr("loom.digest.extract.extract_digest", lambda *_a, **_k: (without, None))
    src = work_home(q, CK) / "src"
    shutil.rmtree(src, ignore_errors=True)
    src.mkdir(parents=True)
    (src / "paper.tex").write_text("\\documentclass{article}\n\\begin{document}\nCalloway.\n\\end{document}\n")

    ok("library", "verify", RID, "--as", "A. Author", "--yes", cwd=q)
    assert ok("library", "why", RID, cwd=q).stdout.startswith(f"{RID}, verified by A. Author, from {CK}")
    # an extracted result beside it is untouched by the verify
    assert json_of("library", "why", "Calloway14-prop-3.3", "--json", cwd=q)["state"] == "extracted"

    r = ok("library", "update", CK, "--redo", "--only", "extract", cwd=q)
    after = digest.read_text()
    assert after.count(f"\\label{{{RID}}}") == 1 and "Then $\\operatorname{Fix}(\\sigma)$ is closed in $X$." in after
    assert "\\cite[{\\cite" not in after, "the node is put back as extracted, not re-wrapped"
    assert f"verified results kept through the new extraction (1)\n  {RID}  {CK}" in r.output, r.output
    assert json_of("library", "why", RID, "--json", cwd=q)["state"] == "verified"


def test_discard_refuses_an_extracted_result_and_names_the_redo(tmp_path: Path) -> None:
    q = demo(tmp_path)
    before = _results_bytes(q)
    r = refused("library", "discard", RID, "--why", "r", "--as", "A. Author", code=1, match="extracted", cwd=q)
    assert f"loom library update {CK} --redo" in r.output
    assert _results_bytes(q) == before


def test_a_result_read_off_a_preprint_carries_the_version(tmp_path: Path) -> None:
    """A digest extracted from a preprint while the bibliography cites the published article: each of its results says so, in the manifest, `why` and search."""
    from loom.refs.proposals import record_extracted
    from loom.scan.quilt import load_quilt
    from loom.scan.scan import scan

    q = demo(tmp_path)
    with (q / "digests" / "bibliography.bib").open("a") as fh:
        fh.write("\n@article{Split, title={S}, doi={10.1090/S1}, eprint={2001.00002v1}}\n")
    (q / "digests" / "Split.tex").write_text(SPLIT, encoding="utf-8")
    assert record_extracted(scan(load_quilt(q)), "Split") == 1

    said = "read from arXiv:2001.00002v1; the bibliography cites doi:10.1090/S1"
    assert said in ok("library", "why", "Split-thm-1", cwd=q).stdout
    data = json_of("library", "why", "Split-thm-1", "--json", cwd=q)
    assert data["version"] == {"extracted_from": "arXiv:2001.00002v1", "cited": "doi:10.1090/S1"}
    assert said in ok("library", "search", "widget splits", cwd=q).stderr
    assert "the bibliography cites" not in ok("library", "why", RID, cwd=q).stdout
    ok("build", cwd=q)
    refs = json.loads((q / "build" / "manifest.json").read_text())["references"]
    assert refs["Split"]["results"]["Split-thm-1"]["version"] == {
        "extracted_from": "arXiv:2001.00002v1",
        "cited": "doi:10.1090/S1",
    }
    assert all("version" not in r for r in refs[CK]["results"].values()), "a digest cited as it was read says nothing"


def test_a_proposal_waits_and_drop_proposed_leaves_extracted_results(tmp_path: Path) -> None:
    q = demo(tmp_path)
    propose(q, CK, "rem-9.1", 1, "An involution of a topological space fixes a subspace", "S")
    assert json_of("library", "why", f"{CK}-rem-9.1", "--json", cwd=q)["state"] == "proposed"
    ok("library", "drop", "--proposed", "--yes", cwd=q)
    from loom.refs.proposals import load_results

    left = load_results(q, CK)
    assert f"{CK}-rem-9.1" not in left and len(left) == 5
