"""A digest's results are results whether or not a document declares their environments: a reading project with no document still has them."""

from __future__ import annotations

from pathlib import Path

from tests.unit.scan.helpers import PREAMBLE, make_quilt

DIGEST = r"""% !LOOM digest: Vir12
% !LOOM prefix: Vir12

\section{Pullbacks}\label{Vir12-sec-4}

\begin{thm}[{\cite[Theorem 4.1, p.~12]{Vir12}}]\label{Vir12-thm-4.1}
Every widget is a gadget.
\end{thm}

\begin{defn}[{\cite[Definition 4.2, p.~13]{Vir12}}]\label{Vir12-def-4.2}
A gadget is a widget with a perfect obstruction theory.
\end{defn}

\begin{theorem}[{\cite[Standing assumptions]{Vir12}}]\label{Vir12-setup}
All stacks are algebraic.
\end{theorem}
"""


def test_a_quilt_with_only_a_digest_sees_its_results(tmp_path: Path) -> None:
    r = make_quilt(tmp_path, {"digests/Vir12.tex": DIGEST})
    assert {k for k, n in r.nodes.items() if n.kind == "environment"} == {
        "Vir12-thm-4.1",
        "Vir12-def-4.2",
        "Vir12-setup",
    }
    assert (r.nodes["Vir12-thm-4.1"].taxon, r.nodes["Vir12-thm-4.1"].style) == ("Theorem", "plain")
    assert (r.nodes["Vir12-def-4.2"].taxon, r.nodes["Vir12-def-4.2"].style) == ("Definition", "definition")
    assert r.nodes["Vir12-setup"].taxon == "Theorem", (
        "a locator that names no kind of result leaves the environment's name"
    )
    assert not [d for d in r.lint if d.code == "loom:unknown-environment"]


def test_a_document_s_declaration_wins(tmp_path: Path) -> None:
    preamble = PREAMBLE + "\\newtheorem{thm}[theorem]{Satz}\n"
    r = make_quilt(
        tmp_path,
        {
            "drafting/main.tex": preamble + "\\begin{document}\nHello.\n\\end{document}\n",
            "digests/Vir12.tex": DIGEST,
        },
    )
    assert r.nodes["Vir12-thm-4.1"].taxon == "Satz"
    assert r.nodes["Vir12-def-4.2"].taxon == "Definition", "an environment no document declares still declares itself"


def test_an_author_s_own_undeclared_environment_is_still_not_a_node(tmp_path: Path) -> None:
    """Only a digest's results declare themselves; an author's file still needs a document's declaration."""
    r = make_quilt(
        tmp_path,
        {
            "nodes/x.tex": "\\begin{thm}[{\\cite[Theorem 1]{Vir12}}]\\label{ab-0001}\nA.\n\\end{thm}\n",
            "digests/Vir12.tex": DIGEST,
        },
    )
    assert "ab-0001" not in r.nodes
