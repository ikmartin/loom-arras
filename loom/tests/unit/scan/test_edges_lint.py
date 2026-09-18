from pathlib import Path

from tests.unit.scan.helpers import PREAMBLE, SINGLE_FILE, make_quilt


def codes(r):  # type: ignore[no-untyped-def]
    return sorted(d.code for d in r.lint)


def test_edge_family_alias_classification_closure(tmp_path: Path) -> None:
    r = make_quilt(tmp_path, {"drafting/main.tex": SINGLE_FILE, "refs.bib": "@article{Man12, title={x}}\n"})
    edges = {(e.src, e.to, e.kind, e.via) for e in r.edges.edges}
    assert ("ab-0003/proof", "ab-0001", "proof", "uses") in edges
    assert ("ab-0003/proof", "ab-0002", "proof", "ref") in edges
    assert r.graph.direct("ab-0003/proof") == ["ab-0001", "ab-0002"]
    assert r.graph.closure("ab-0003/proof") == ["ab-0001", "ab-0002", "ab-0003"]
    assert r.graph.closure("ab-0003") == ["ab-0003"]
    assert r.graph.downstream("ab-0002") == ["ab-0003/proof"]
    cites = [(c.src, c.citekey, c.postnote) for c in r.edges.cites]
    assert cites == [("ab-0011", "Man12", "Theorem 4.1")]
    assert codes(r) == ["loom:undigested-citekey", "loom:unresolved-work", "loom:uses-missing", "loom:uses-unused"]


def test_edge_dangling_loose_and_uses_lints(tmp_path: Path) -> None:
    r = make_quilt(
        tmp_path,
        {
            "drafting/main.tex": PREAMBLE
            + "\\begin{document}\n\\begin{lemma}\\label{ab-0001}\nSee \\ref{ab-0099}, \\ref{ab-0002} and \\eqref{eq:in-proof}.\n\\end{lemma}\n\\begin{proof}\n\\uses{ab-0003}\nBy \\cref{ab-0002}.\n\\end{proof}\n\\begin{lemma}\\label{ab-0003}\nX\n\\end{lemma}\n\\begin{proof}\n\\begin{equation}\\label{eq:in-proof} 1 \\end{equation}\n\\end{proof}\n\\end{document}\n",
            "nodes/loose.tex": "\\begin{lemma}\\label{ab-0002}\nL\n\\end{lemma}\n\\begin{proof}\nP\n\\end{proof}\n",
        },
    )
    c = codes(r)
    assert "dangling-link" in c
    assert c.count("loom:reference-to-loose") == 2
    assert "unreachable" in c
    assert "loom:uses-missing" in c and "loom:uses-unused" in c
    assert "loom:equation-in-proof-referenced" in c
    eq = next(e for e in r.edges.edges if e.label == "eq:in-proof")
    assert eq.to == "ab-0003/proof" and eq.kind == "statement"


def test_missing_proof_external_unexpected_unknown_env(tmp_path: Path) -> None:
    r = make_quilt(
        tmp_path,
        {
            "drafting/main.tex": PREAMBLE
            + "\\begin{document}\n\\begin{theorem}\\label{ab-0001}\nNo proof.\n\\end{theorem}\n\\begin{theorem}[{\\cite[Thm 1]{K}}]\\label{ab-0002}\nExternal.\n\\end{theorem}\n\\begin{theorem}\\label{ab-0003}\n\\incomplete{later}\n\\end{theorem}\n\\begin{definition}\\label{ab-0004}\nD\n\\end{definition}\n\\begin{proof}\nWhy.\n\\end{proof}\n\\begin{conjecture}\\label{ab-0005}\nC\n\\end{conjecture}\n\\end{document}\n"
        },
    )
    c = codes(r)
    assert c.count("loom:missing-proof") == 1
    assert "loom:unexpected-proof" in c
    assert "loom:unknown-environment" in c
    assert r.nodes["ab-0002"].external


def test_directives_macros_prefix_disable(tmp_path: Path) -> None:
    cfg = '[quilt]\nmain = "drafting/main.tex"\nprefix = "Man12"\n[lint]\ndisable = ["loom:unlabelled-node"]\n'
    r = make_quilt(
        tmp_path,
        {
            "drafting/main.tex": "\\documentclass{amsart}\n\\newtheorem{lemma}{Lemma}\n\\newcommand{\\uses}[1]{}\n% !LOOM bogus: 1\n\\begin{document}\n\\begin{lemma}\nA \\uses{x}\n\\end{lemma}\n\\begin{proof}\nP\n\\end{proof}\n\\end{document}\n",
            "refs.bib": "@misc{Man12, title={t}}\n",
        },
        config=cfg,
    )
    c = codes(r)
    assert "loom:macros-unloaded" in c and "loom:macro-shadowed" in c
    assert "loom:unknown-directive" in c and "loom:prefix-is-citekey" in c
    assert "loom:unlabelled-node" not in c
    assert "dangling-link" in c


def test_dependency_cycle_and_slug_collision(tmp_path: Path) -> None:
    r = make_quilt(
        tmp_path,
        {
            "drafting/main.tex": PREAMBLE
            + "\\begin{document}\n\\begin{lemma}\\label{ab-0001}\nUses \\ref{ab-0002}.\n\\end{lemma}\n\\begin{proof}P\\end{proof}\n\\begin{lemma}\\label{ab-0002}\nUses \\ref{ab-0001}.\n\\end{lemma}\n\\begin{proof}P\\end{proof}\n\\end{document}\n",
            "refs.bib": "@misc{stacks-project, title={s}}\n@misc{stacksproject, title={s2}}\n",
        },
    )
    c = codes(r)
    assert "loom:dependency-cycle" in c and "loom:citekey-slug-collision" in c


def test_labels_with_spaces_commas_and_wrapped_refs(tmp_path: Path) -> None:
    r = make_quilt(
        tmp_path,
        {
            "drafting/main.tex": PREAMBLE
            + "\\newcommand\\refpart[2]{(\\ref{#1;#2})}\n\\begin{document}\n\\begin{lemma}\n\\label{Prop: Index of the image}\nSee \\eqref{Eqn: M(G,bg)->M} and \\ref{Prop: Index of\nthe image} and \\cref{ab-0002,ab-0003}.\n\\begin{equation}\\label{Eqn: M(G,bg)->M} 1 \\end{equation}\n\\end{lemma}\n\\begin{lemma}\\label{ab-0002}\nA\n\\end{lemma}\n\\begin{lemma}\\label{ab-0003}\nB\n\\end{lemma}\n\\end{document}\n",
        },
    )
    assert not [d for d in r.lint if d.code == "dangling-link"], [d.message for d in r.lint]
    assert "Prop: Index of the image" in r.assembly.labels
    assert "#1" not in " ".join(r.assembly.labels)
    targets = {e.to for e in r.edges.edges if e.src == "drafting/main.tex#lemma:1"}
    assert targets == {"ab-0002", "ab-0003"}
