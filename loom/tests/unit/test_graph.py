"""The dependency graph from the command line (book 12): `search`, `deps`, `downstream`, and the refusal of `delete`."""

from __future__ import annotations

import shutil
from pathlib import Path

from tests.helpers import json_of, ok, refused
from tests.unit._quilts import demo

SYNTHETIC = Path(__file__).resolve().parents[1] / "quilts" / "synthetic"


def test_deps_prints_see_also(tmp_path: Path) -> None:
    """`deps` reports relations in a final section marked not-a-dependency, and `--json` carries them beside the closure (plan 0.2 §2.2)."""
    q = tmp_path / "syn"
    shutil.copytree(SYNTHETIC, q)
    r = ok("deps", "sy-0008", cwd=q)
    assert "see also, not a dependency (1)" in r.output
    assert "sy-0009" in r.output.split("see also, not a dependency (1)")[1]

    payload = json_of("deps", "sy-0009", "--json", cwd=q)
    assert payload["relations"] == [{"key": "sy-0008", "kind": "see"}]  # both directions are reported
    assert all(e["key"] != "sy-0008" for e in payload["closure"])  # and a relation is not in the closure


def test_search_deps_downstream_delete(tmp_path: Path) -> None:
    q = demo(tmp_path)
    entries = json_of("search", "orbits", "--json", cwd=q)["matches"]
    assert entries[0]["key"] == "dm-0002" and "lem:orbits" in entries[0]["aliases"]
    found = ok("search", "lem:orbits", cwd=q).output.splitlines()
    assert found[0] == "1 match for 'lem:orbits'" and found[2] == "in your documents (1)"
    assert found[3].split()[-1] == "dm-0002"  # the key last on its row
    payload = json_of("deps", "dm-0003", "--json", cwd=q)
    assert [e["key"] for e in payload["proof"]] == [
        "dm-0002",
        "Calloway14-prop-3.2",
    ]  # \cite[Proposition 3.2]{Calloway14} resolves to the digest node
    assert payload["closure"] == [{"key": "dm-0003"}]
    dp = ok("deps", "dm-0003/proof", "--closure", cwd=q)
    assert dp.output.splitlines()[2] == "closure, dependencies first (4)"
    assert {tuple(ln.split()) for ln in dp.output.splitlines()[3:]} == {
        ("Lemma", "dm-0002"),
        ("Theorem", "dm-0003"),
        ("Definition", "Calloway14-def-3.1"),
        ("Proposition", "Calloway14-prop-3.2"),
    }  # the closure includes the digest nodes the proof cites by postnote (book 8.11)
    up = json_of("downstream", "dm-0001", "--json", cwd=q)
    assert {x["key"] for x in up["dependents"]} == {"dm-0002/proof", "dm-0005/proof"}
    assert any(i["file"] == "drafting/main.tex" for i in up["inclusions"])
    assert "nothing was changed" in ok("downstream", "dm-0001", cwd=q).output.splitlines()[0]
    before = sorted(p.relative_to(q).as_posix() for p in q.rglob("*"))
    for name in ("delete", "rm", "remove"):
        r = refused(name, "dm-0001", cwd=q, code=2, match="loom will not delete your notes")
        assert "loom downstream dm-0001" in r.output
    assert sorted(p.relative_to(q).as_posix() for p in q.rglob("*")) == before
    refused("deps", "dm-9999", cwd=q, code=2, match="no such key: dm-9999")


def test_downstream_reports_the_ledger_and_the_annotations_it_heads(tmp_path: Path) -> None:
    """`downstream` lists a node's ledger rows and the annotations on it; `annotations: (none)` on a reviewed node would say it was never reviewed (F13)."""
    q = demo(tmp_path)
    ok("annotate", "dm-0002", "Which orbits?", "--as", "Tom", cwd=q)

    payload = json_of("downstream", "dm-0002", "--json", cwd=q)
    assert [r["key"] for r in payload["ledger"]] == ["dm-0002", "dm-0002/proof"]  # the statement and its proof
    (a,) = payload["annotations"]
    assert a["message"] == "Which orbits?" and a["target"] == "dm-0002" and a["status"] == "open"

    text = ok("downstream", "dm-0002", cwd=q).output
    assert "Which orbits?" in text
    assert "annotations:\n  (none)" not in text


def test_deps_closure_names_what_the_proof_adds_so_it_agrees_with_source(tmp_path: Path) -> None:
    """The re-grade: `deps dm-0003 --closure` said "depends on nothing" right after `deps dm-0003` listed two results, while `source dm-0003 --closure` printed four. The statement closure stays what `--closure` is; what the proofs add is listed apart, and the two together are what `source` prints."""
    from loom.scan.quilt import load_quilt
    from loom.scan.scan import scan
    from loom.tex.bundle import build_bundle

    q = demo(tmp_path)
    r = ok("deps", "dm-0003", "--closure", cwd=q)
    said = " ".join(r.stdout.split())
    assert "depends on nothing" not in said
    assert (
        "dm-0003's statement depends on no other statement; its proof adds 3, which loom source dm-0003 --closure prints with it"
        in said
    )
    payload = json_of("deps", "dm-0003", "--closure", "--json", cwd=q)
    listed = [e["key"] for e in payload["closure"] + payload["proof_closure"] if e["key"] != "dm-0003"]
    assert sorted(listed) == sorted(build_bundle(scan(load_quilt(q)), "dm-0003").closure)


def test_search_names_a_cited_result_by_its_locator_and_lists_the_authors_results_apart(tmp_path: Path) -> None:
    """The re-grade: digest titles printed as raw `{\\cite[Proposition 3.2, p.~1]{Calloway14}}`, in one list with the author's results."""
    q = demo(tmp_path)
    r = ok("search", "proposition", cwd=q)
    assert "\\cite" not in r.stdout
    yours, cited = r.stdout.split("in cited works (2)")
    assert "in your documents (1)" in yours and "dm-0005" in yours and "Calloway14" not in yours
    assert '"Proposition 3.2 of Calloway"' in cited and "Calloway14-prop-3.2" in cited
    payload = json_of("search", "proposition", "--json", cwd=q)
    assert [g["heading"] for g in payload["groups"]] == ["in your documents", "in cited works"]
    digest = next(m for m in payload["matches"] if m["key"] == "Calloway14-prop-3.2")
    assert digest["name"] == "Proposition 3.2 of Calloway" and digest["title"].startswith("{\\cite[")
