from pathlib import Path

from loom.scan.hashing import hash_text
from tests.unit.scan.helpers import PREAMBLE, SINGLE_FILE, make_quilt


def test_example_single_file_paper(tmp_path: Path) -> None:
    r = make_quilt(tmp_path, {"drafts/main.tex": SINGLE_FILE})
    nodes = r.nodes
    assert r.masters == ["drafts/main.tex"] and r.default_master == "drafts/main.tex"
    sections = {k: n for k, n in nodes.items() if n.kind == "section"}
    assert set(sections) == {"ab-0010", "ab-0011"}
    assert [n.title for n in sections.values()] == ["Setup", "Results"]
    envs = {k: n for k, n in nodes.items() if n.kind == "environment"}
    assert set(envs) == {"ab-0001", "ab-0002", "ab-0003"}
    assert envs["ab-0002"].aliases == ["lem:involution-fixed"]
    assert envs["ab-0001"].taxon == "Definition" and envs["ab-0001"].style == "definition"
    assert envs["ab-0003"].title == "Main"
    proofs = {k: n for k, n in nodes.items() if n.kind == "proof"}
    assert set(proofs) == {"ab-0002/proof", "ab-0003/proof"}
    assert proofs["ab-0002/proof"].attach_via == "adjacent"
    assert proofs["ab-0003/proof"].attach_via == "ref" and proofs["ab-0003/proof"].of == "ab-0003"
    assert nodes["ab-0003"].proofs == ["ab-0003/proof"]
    master = nodes["drafts/main.tex"]
    assert master.kind == "master"
    src = r.files["drafts/main.tex"]
    own = "".join(src.clean[a:b] for a, b in master.own)
    assert "\\documentclass" in own and "\\begin{definition}" not in own and "Closedness" not in own
    results_own = "".join(src.clean[a:b] for a, b in nodes["ab-0011"].own)
    assert (
        "Closedness is" in results_own and "Take the orbit" not in results_own and "\\end{document}" not in results_own
    )
    assert r.assembly.labels["lem:involution-fixed"] == "ab-0002"
    assert not [d for d in r.diagnostics if d.severity == "error"], [d.message for d in r.diagnostics]


def test_env_node_without_id_qualified_key_and_regions(tmp_path: Path) -> None:
    r = make_quilt(
        tmp_path,
        {
            "drafts/main.tex": PREAMBLE
            + r"""\begin{document}
\section{Intro}
\begin{lemma}\label{lem:human}
With equation
\begin{equation}\label{eq:main} x = y \end{equation}
\end{lemma}
\begin{lemma}
Second, unlabelled.
\end{lemma}
\end{document}
"""
        },
    )
    nodes = r.nodes
    assert "drafts/main.tex#lemma:1" in nodes and "drafts/main.tex#lemma:2" in nodes
    assert nodes["drafts/main.tex#lemma:1"].aliases == ["lem:human"]
    assert "drafts/main.tex#section:1" in nodes
    assert r.assembly.regions["drafts/main.tex#lemma:1#eq:main"].where == "statement"
    assert r.assembly.labels["eq:main"] == "drafts/main.tex#lemma:1#eq:main"
    infos = [d for d in r.diagnostics if d.code == "loom:unlabelled-node"]
    assert len(infos) == 2


def test_example_two_proofs_and_positional_keys(tmp_path: Path) -> None:
    r = make_quilt(
        tmp_path,
        {
            "drafts/main.tex": PREAMBLE
            + r"""\begin{document}
\begin{theorem}\label{ab-0040}
T
\end{theorem}
\begin{proof}[First proof]\label{ab-0041}
\uses{ab-0004, ab-0012}
A
\end{proof}
\begin{proof}[Second proof]\label{ab-0042}
B
\end{proof}
\begin{theorem}\label{ab-0050}
U
\end{theorem}
\begin{proof}
one
\end{proof}
\begin{proof}
two
\end{proof}
\end{document}
"""
        },
    )
    nodes = r.nodes
    assert nodes["ab-0040"].proofs == ["ab-0041", "ab-0042"]
    assert (
        nodes["ab-0041"].kind == "proof"
        and nodes["ab-0041"].id == "ab-0041"
        and nodes["ab-0041"].title == "First proof"
    )
    assert nodes["ab-0050"].proofs == ["ab-0050/proof", "ab-0050/proof/2"]
    codes = [d.code for d in r.diagnostics]
    assert codes.count("loom:positional-proof-key") == 1


def test_statement_nested_in_proof_and_enclosure_keys(tmp_path: Path) -> None:
    r = make_quilt(
        tmp_path,
        {
            "drafts/main.tex": PREAMBLE
            + r"""\begin{document}
\begin{theorem}\label{ab-0001}
M
\end{theorem}
\begin{proof}
Outer.
\begin{lemma}\label{ab-0002}
I
\end{lemma}
\begin{proof}
Inner.
\end{proof}
More.
\end{proof}
\begin{example}\label{ab-0003}
Prose \incomplete{finish this}.
\begin{proof}
Of the example.
\end{proof}
\end{example}
\end{document}
"""
        },
    )
    nodes = r.nodes
    assert nodes["ab-0002/proof"].of == "ab-0002" and nodes["ab-0001/proof"].of == "ab-0001"
    assert nodes["ab-0003/proof"].attach_via == "enclosure"
    src = r.files["drafts/main.tex"]
    outer_own = "".join(src.clean[a:b] for a, b in nodes["ab-0001/proof"].own)
    assert (
        "Outer." in outer_own
        and "More." in outer_own
        and "Inner." not in outer_own
        and "\\label{ab-0002}" not in outer_own
    )
    assert nodes["ab-0003"].incomplete == ["finish this"]
    assert not [d for d in r.diagnostics if d.severity == "error"]


def test_directives_file_and_node_level(tmp_path: Path) -> None:
    r = make_quilt(
        tmp_path,
        {
            "drafts/main.tex": PREAMBLE + "\\begin{document}\n\\input{nodes/ab-0004}\n\\end{document}\n",
            "nodes/ab-0004.tex": "% !LOOM author: Markas Hecht\n% !LOOM created: 2026-09-15\n% !LOOM tags: localization, residue\n\n\\begin{lemma}[Residue]\\label{ab-0004}\n% !LOOM tags: only-this\nL\n\\end{lemma}\n\\begin{proof}\nP\n\\end{proof}\n",
        },
    )
    n = r.nodes["ab-0004"]
    assert n.directives == {"author": "Markas Hecht", "created": "2026-09-15", "tags": "only-this"}
    assert r.nodes["ab-0004/proof"].directives["author"] == "Markas Hecht"
    assert n.reached_by == ["drafts/main.tex"]
    assert hash_text("".join(r.files["nodes/ab-0004.tex"].text[a:b] for a, b in n.own)).startswith("sha256:")


def test_duplicate_id_and_label_errors(tmp_path: Path) -> None:
    r = make_quilt(
        tmp_path,
        {
            "drafts/main.tex": PREAMBLE
            + "\\begin{document}\n\\begin{lemma}\\label{ab-0001}\nA\n\\end{lemma}\n\\input{nodes/dup}\n\\begin{lemma}\\label{ab-0002}\n\\begin{equation}\\label{eq:x} 1 \\end{equation}\n\\end{lemma}\n\\begin{lemma}\\label{ab-0003}\n\\begin{equation}\\label{eq:x} 2 \\end{equation}\n\\end{lemma}\n% \\begin{lemma}\\label{ab-0001}\n\\end{document}\n",
            "nodes/dup.tex": "\\begin{lemma}\\label{ab-0001}\nB\n\\end{lemma}\n",
        },
    )
    codes = sorted(d.code for d in r.diagnostics if d.severity == "error")
    assert codes == ["duplicate-id", "loom:duplicate-label"]
    dup = next(d for d in r.diagnostics if d.code == "duplicate-id")
    assert {loc.file for loc in dup.locations} == {"drafts/main.tex", "nodes/dup.tex"}


def test_external_node_and_digest_file(tmp_path: Path) -> None:
    r = make_quilt(
        tmp_path,
        {
            "drafts/main.tex": PREAMBLE
            + "\\begin{document}\n\\begin{theorem}[{\\cite[Theorem 2]{K}}]\\label{ab-0001}\nT\n\\end{theorem}\n\\begin{definition}\\cite[Def 1]{K}\n\\label{ab-0002}\nD\n\\end{definition}\n\\end{document}\n",
            "digests/Man12.tex": "% !LOOM digest: Man12\n% !LOOM source: arXiv:0805.2065v2\n% !LOOM method: extract\n\\section*{Overview}\n\\section{Preliminaries}\\label{Man12-sec-2}\n\\begin{theorem}[{\\cite[Theorem 4.1, p.~12]{Man12}}]\\label{Man12-thm-4.1}\nStatement.\n\\end{theorem}\n",
            "refs.bib": "@article{Man12, title={Virtual pull-backs}}\n@misc{K, title={K}}\n",
        },
    )
    nodes = r.nodes
    assert (
        nodes["ab-0001"].external and not nodes["ab-0002"].external
    )  # definition style never owes a proof, so not external
    assert nodes["Man12-thm-4.1"].external and nodes["Man12-thm-4.1"].digest == "Man12"
    assert nodes["Man12-thm-4.1"].reached_by == []
    assert "Man12" in r.bib


def test_declared_prefix_carries_the_id_grammar(tmp_path: Path) -> None:
    """A digest declares the prefix its node ids carry, so `\\uses` stays typeable and the ids survive a citekey rename.

    Without the declaration the prefix would be the citekey's slug, and a Zotero key makes that 29 characters. The prefix is what `is_id_shaped` matches on, so declaring one is what makes `Man12-thm-4.1` an id at all rather than a human alias (plan 0.5, DR-109).
    """
    long_key = "manolache_VirtualPullbacks2012"
    r = make_quilt(
        tmp_path,
        {
            "drafts/main.tex": PREAMBLE
            + "\\begin{document}\n\\begin{lemma}\\label{ab-0001}\n\\uses{Man12-thm-4.1}\nL\n\\end{lemma}\n\\end{document}\n",
            "digests/paper.tex": f"% !LOOM digest: {long_key}\n% !LOOM prefix: Man12\n"
            "% !LOOM extracted-from: arXiv:0805.2065v2\n% !LOOM method: extract\n"
            "\\section*{Overview}\n"
            f"\\begin{{theorem}}[{{\\cite[Theorem 4.1]{{{long_key}}}}}]\\label{{Man12-thm-4.1}}\nS.\n\\end{{theorem}}\n",
            "refs.bib": f"@article{{{long_key}, title={{Virtual pull-backs}}, doi={{10.1090/S1}}}}\n",
        },
    )
    # the short prefix is an id, not an alias: the node exists under it and carries its digest's citekey
    assert r.nodes["Man12-thm-4.1"].external and r.nodes["Man12-thm-4.1"].digest == long_key
    assert not any(k.startswith("manolacheVirtual") for k in r.nodes)
    # and the edge from the quilt's own lemma resolves to it
    assert ("ab-0001", "Man12-thm-4.1", "uses") in {(e.src, e.to, e.via) for e in r.edges.edges}
