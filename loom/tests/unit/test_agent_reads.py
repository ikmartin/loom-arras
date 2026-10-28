"""The reads the modes name (plan 0.21.1): the proofs that cite a key, a key's text at a version and what changed since, a document's keys in order, and a section printed whole."""

from __future__ import annotations

from pathlib import Path

from tests.helpers import edit, json_of, ok, refused
from tests.unit._quilts import demo, showcase

LEMMA = "nodes/dm-0002.tex"


def test_downstream_proofs_lists_the_proofs_that_cite_a_key_with_what_each_proves(tmp_path: Path) -> None:
    q = showcase(tmp_path)
    data = json_of("downstream", "sh-0009", "--proofs", "--json", cwd=q)
    assert data["proofs"] == [
        {"key": "sh-000A/proof", "statement": "sh-000A", "via": "uses"},
        {"key": "sh-000C/proof", "statement": "sh-000C", "via": "uses"},
    ]
    # a proof with a label of its own proves the statement it names, which no string operation on its key recovers
    assert {"key": "sh-0009/proof", "statement": "sh-0009", "via": "uses"} in json_of(
        "downstream", "sh-0007", "--proofs", "--json", cwd=q
    )["proofs"]


def test_source_at_an_annotation_prints_the_text_it_was_written_against_and_diffs_it(tmp_path: Path) -> None:
    q = demo(tmp_path)
    ann = ok(
        "annotate",
        "dm-0002",
        "Is this right?",
        "--kind",
        "question",
        "--quote",
        "one or two points",
        "--as",
        "Tom",
        cwd=q,
    ).stdout.split()[0]
    assert "nothing has changed since" in ok("source", "dm-0002", "--at", ann, "--diff", cwd=q).stdout
    edit(q / LEMMA, "one or two points", "at most two points")
    then = ok("source", "dm-0002", "--at", ann, cwd=q)
    assert "one or two points" in then.stdout and "written against" in then.stderr
    diff = ok("source", "dm-0002", "--at", ann, "--diff", cwd=q).stdout
    assert diff.startswith(f"--- dm-0002@{ann}\n+++ dm-0002\n")
    assert (
        "-Every orbit of a widget has one or two points" in diff
        and "+Every orbit of a widget has at most two points" in diff
    )
    refused("source", "dm-0003", "--at", ann, cwd=q, code=2, match="is on dm-0002, not dm-0003")


def test_source_at_accepted_and_at_a_step(tmp_path: Path) -> None:
    q = demo(tmp_path)
    edit(q / LEMMA, "one or two points", "at most two points")
    accepted = ok("source", "dm-0002", "--at", "accepted:The loom demo", "--diff", cwd=q)
    assert "-Every orbit of a widget has one or two points" in accepted.stdout and "accepted it on" in accepted.stderr
    refused("source", "dm-0002", "--at", "accepted:Nobody", cwd=q, code=2, match="never accepted by Nobody")
    assert (
        "+Every orbit of a widget has at most two points"
        in ok("source", "dm-0002", "--at", "1", "--diff", cwd=q).stdout
    )
    refused("source", "dm-0002", "--at", "99", cwd=q, code=2, match="no step 99")
    refused("source", "dm-0002", "--diff", cwd=q, code=2, match="--diff compares with --at")
    refused("source", "dm-0002", "--at", "1", "--closure", cwd=q, code=2, match="--closure does not apply")


def test_source_of_a_section_prints_everything_in_it_and_stops_before_the_bibliography(tmp_path: Path) -> None:
    q = demo(tmp_path)
    setup = ok("source", "dm-0010", cwd=q).stdout
    assert setup.startswith("\\section{Setup}\\label{dm-0010}")
    assert "\\input{" not in setup and "\\begin{lemma}[Orbits]\\label{dm-0002}" in setup  # inclusions expanded
    assert "\\section{Results}" not in setup  # stops at the next section
    results = ok("source", "dm-0011", cwd=q).stdout
    assert "\\bibliography" not in results and results.rstrip().endswith("\\end{proof}")


def test_status_in_order_lists_a_documents_keys_as_it_prints_them(tmp_path: Path) -> None:
    q = showcase(tmp_path)
    rows = json_of("status", "--master", "drafting/main-atomic.tex", "--in-order", "--json", cwd=q)["in_order"]
    keys = [r["key"] for r in rows]
    assert keys.index("sh-0100") < keys.index("sh-0001") < keys.index("sh-0200")  # sections among them, in place
    assert keys.index("sh-0007") < keys.index("sh-0007/proof") < keys.index("sh-0010") < keys.index("sh-0008")
    assert next(r for r in rows if r["key"] == "sh-0001")["state"] == "draft"
    refused("status", "--in-order", cwd=q, code=2, match="name it with --master")
