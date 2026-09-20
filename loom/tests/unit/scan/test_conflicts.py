"""A node is defined once and included many times (book 5.3.5): a second live definition leaves the id conflicted -- no text, no winner -- and one `duplicate-id` naming both files."""

from __future__ import annotations

from pathlib import Path

from tests.unit.scan.helpers import PREAMBLE, make_quilt

LEMMA = "\\begin{lemma}\\label{ab-0001}\nAlpha.\n\\end{lemma}\n"


def _diag(result, code):  # type: ignore[no-untyped-def]
    return [d for d in result.lint if d.code == code]


def test_two_files_defining_one_id_leave_it_conflicted(tmp_path: Path) -> None:
    r = make_quilt(
        tmp_path,
        {
            "drafting/main.tex": PREAMBLE + "\\begin{document}\n" + LEMMA + "\\end{document}\n",
            "drafting/talk.tex": PREAMBLE + "\\begin{document}\n" + LEMMA + "\\end{document}\n",
        },
    )
    n = r.nodes["ab-0001"]
    assert n.kind == "conflict" and n.conflict == ["drafting/main.tex", "drafting/talk.tex"]
    assert n.own == [] and n.taxon == "Lemma"  # it has no text; the taxon is the first definition's, for display
    demoted = [x for x in r.nodes.values() if x.conflict_of == "ab-0001"]
    assert len(demoted) == 2 and all(x.id is None and x.labels == [] for x in demoted)
    assert [x.key for x in demoted] == ["drafting/main.tex#lemma:1", "drafting/talk.tex#lemma:1"]

    (d,) = _diag(r, "duplicate-id")
    assert "defined by drafting/main.tex and drafting/talk.tex" in d.message and "no text" in d.message
    assert [loc.file for loc in d.locations] == ["drafting/main.tex", "drafting/talk.tex"]
    assert [f.command for f in d.fixes] == [
        "loom fork ab-0001 --in drafting/main.tex",
        "loom fork ab-0001 --in drafting/talk.tex",
        "loom id --next",
    ]
    assert not _diag(r, "loom:unlabelled-node")  # a demoted definition is not an unlabelled node
    assert not _diag(r, "loom:duplicate-label")  # the id's collision is said once, as duplicate-id


def test_a_node_file_and_an_inline_copy_conflict(tmp_path: Path) -> None:
    r = make_quilt(
        tmp_path,
        {
            "drafting/main.tex": PREAMBLE + "\\begin{document}\n\\input{nodes/ab-0001}\n" + LEMMA + "\\end{document}\n",
            "nodes/ab-0001.tex": LEMMA,
        },
    )
    assert r.nodes["ab-0001"].kind == "conflict"
    assert r.nodes["ab-0001"].conflict == ["drafting/main.tex", "nodes/ab-0001.tex"]
    assert len(_diag(r, "duplicate-id")) == 1


def test_two_masters_sharing_one_node_file_is_not_a_conflict(tmp_path: Path) -> None:
    r = make_quilt(
        tmp_path,
        {
            "drafting/main.tex": PREAMBLE + "\\begin{document}\n\\input{nodes/ab-0001}\n\\end{document}\n",
            "drafting/talk.tex": PREAMBLE + "\\begin{document}\n\\input{nodes/ab-0001}\n\\end{document}\n",
            "nodes/ab-0001.tex": LEMMA,
        },
    )
    assert r.nodes["ab-0001"].kind == "environment"  # defined once, included twice: exactly the intended shape
    assert set(r.nodes["ab-0001"].reached_by) == {"drafting/main.tex", "drafting/talk.tex"}
    assert not _diag(r, "duplicate-id")


def test_a_proof_attaches_to_its_own_file_s_copy(tmp_path: Path) -> None:
    body = LEMMA + "\\begin{proof}\nBy inspection.\n\\end{proof}\n"
    r = make_quilt(
        tmp_path,
        {
            "drafting/main.tex": PREAMBLE + "\\begin{document}\n" + body + "\\end{document}\n",
            "drafting/talk.tex": PREAMBLE + "\\begin{document}\n" + LEMMA + "\\end{document}\n",
        },
    )
    proofs = [x for x in r.nodes.values() if x.kind == "proof"]
    assert len(proofs) == 1
    (p,) = proofs
    assert p.file == "drafting/main.tex" and p.of == "drafting/main.tex#lemma:1"  # never the other file's copy
    assert r.nodes["ab-0001"].proofs == []


def test_a_conflicted_id_is_still_a_reference_target(tmp_path: Path) -> None:
    r = make_quilt(
        tmp_path,
        {
            "drafting/main.tex": PREAMBLE
            + "\\begin{document}\n"
            + LEMMA
            + "\\begin{theorem}\\label{ab-0002}\nBy Lemma~\\ref{ab-0001}.\n\\end{theorem}\n\\end{document}\n",
            "drafting/talk.tex": PREAMBLE + "\\begin{document}\n" + LEMMA + "\\end{document}\n",
        },
    )
    assert not _diag(r, "dangling-link")  # the graph still shows it; what it has no text
    assert [e.to for e in r.edges.edges if e.src == "ab-0002"] == ["ab-0001"]


def test_two_copies_in_one_file_keep_todays_message(tmp_path: Path) -> None:
    r = make_quilt(
        tmp_path,
        {"drafting/main.tex": PREAMBLE + "\\begin{document}\n" + LEMMA + LEMMA + "\\end{document}\n"},
    )
    (d,) = _diag(r, "duplicate-id")
    assert d.message == "label ab-0001 is defined twice" and not d.fixes
    assert "ab-0001" in r.nodes and r.nodes["ab-0001"].kind == "environment"  # one file is the author's to fix
