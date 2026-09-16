from pathlib import Path

from loom.scan.envtree import first_body_token_is_cite, labels_in, scan_environments
from loom.scan.source import read_source

THEOREMS = {"lemma", "theorem", "example", "definition"}


def _fe(tmp_path: Path, text: str, body_start: int = 0):
    (tmp_path / "f.tex").write_text(text, encoding="utf-8")
    src = read_source(tmp_path, "f.tex")
    return src, scan_environments(src, THEOREMS, body_start)


def test_proof_adjacent_and_second_adjacent(tmp_path: Path) -> None:
    src, fe = _fe(
        tmp_path,
        "\\begin{lemma}\\label{a}\nA\n\\end{lemma}\n% comment\n% !LOOM tags: x\n\\begin{proof}\nP1\n\\end{proof}\n\n\\begin{proof}\nP2\n\\end{proof}\n",
    )
    assert len(fe.theorem_envs) == 1 and len(fe.proofs) == 2
    a1 = fe.attachments[fe.proofs[0].start]
    a2 = fe.attachments[fe.proofs[1].start]
    assert a1.via == "adjacent" and a1.statement is fe.theorem_envs[0]
    assert a2.via == "adjacent" and a2.statement is fe.theorem_envs[0]


def test_proof_by_reference_anywhere(tmp_path: Path) -> None:
    src, fe = _fe(
        tmp_path,
        "\\begin{theorem}\\label{t}\nT\n\\end{theorem}\nProse.\n\\begin{proof}[Proof of Theorem~\\ref{t} and \\cref{u}]\nP\n\\end{proof}\n",
    )
    a = fe.attachments[fe.proofs[0].start]
    assert a.via == "ref" and a.ref_labels == ["t", "u"] and a.statement is None


def test_proof_unattached_after_prose(tmp_path: Path) -> None:
    src, fe = _fe(tmp_path, "\\begin{lemma}\nL\n\\end{lemma}\n\\red{not done}\n\\begin{proof}\nP\n\\end{proof}\n")
    assert fe.attachments[fe.proofs[0].start].via == "none"


def test_proof_by_enclosure(tmp_path: Path) -> None:
    src, fe = _fe(tmp_path, "\\begin{example}\nSome prose.\n\\begin{proof}\nP\n\\end{proof}\n\\end{example}\n")
    a = fe.attachments[fe.proofs[0].start]
    assert a.via == "enclosure" and a.statement is fe.theorem_envs[0]


def test_statement_nested_in_proof(tmp_path: Path) -> None:
    text = "\\begin{theorem}\\label{main}\nM\n\\end{theorem}\n\\begin{proof}\nOuter.\n\\begin{lemma}\\label{inner}\nI\n\\end{lemma}\n\\begin{proof}\nInner proof.\n\\end{proof}\nMore outer.\n\\end{proof}\n"
    src, fe = _fe(tmp_path, text)
    outer, inner = fe.proofs
    assert fe.attachments[outer.start].via == "adjacent"
    assert fe.attachments[inner.start].via == "adjacent"
    assert fe.attachments[inner.start].statement.parent is outer
    own = "".join(src.clean[a:b] for a, b in outer.own_ranges())
    assert "Outer." in own and "More outer." in own and "Inner proof." not in own and "I\n" not in own


def test_env_body_on_begin_line_and_one_line_env(tmp_path: Path) -> None:
    text = "\\begin{definition} An $A$-invariant thing \\end{definition}\n\\begin{lemma}\\label{x}Body on the same line.\n\\end{lemma}\n"
    src, fe = _fe(tmp_path, text)
    assert [e.name for e in fe.theorem_envs] == ["definition", "lemma"]
    assert labels_in(src.clean, fe.theorem_envs[1].own_ranges()) == [("x", text.index("\\label{x}"))]


def test_env_spans_files_problem(tmp_path: Path) -> None:
    src, fe = _fe(tmp_path, "\\begin{lemma}\nno end here\n")
    assert fe.problems == [("unclosed", 0, "lemma")]


def test_external_node_by_leading_cite(tmp_path: Path) -> None:
    src, fe = _fe(
        tmp_path,
        "\\begin{definition}\\cite[Def.~B.2]{GS}\n\\label{d}\nD\n\\end{definition}\n\\begin{lemma}[{\\cite[Thm 1]{K}}]\nL\n\\end{lemma}\n",
    )
    assert first_body_token_is_cite(src.clean, fe.theorem_envs[0])
    assert not first_body_token_is_cite(src.clean, fe.theorem_envs[1])
    assert fe.theorem_envs[1].optarg == "{\\cite[Thm 1]{K}}"


def test_body_start_skips_preamble_definitions(tmp_path: Path) -> None:
    text = "\\newenvironment{named}[1]{\\begin{theorem}}{\\end{theorem}}\n\\begin{document}\n\\begin{theorem}\nT\n\\end{theorem}\n\\end{document}\n"
    src, fe = _fe(tmp_path, text, body_start=text.index("\\begin{document}"))
    assert len(fe.theorem_envs) == 1 and fe.theorem_envs[0].start > text.index("\\begin{document}")
