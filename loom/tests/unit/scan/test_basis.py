"""A block's support basis is semantic source metadata, not its LaTeX presentation style."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from loom.cli import main
from loom.cli.review import write_acceptance
from loom.records.store import Records
from loom.reshape.atomize import plan_atomize
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan
from tests.unit.scan.helpers import PREAMBLE, make_quilt


def test_drafting_scan_classifies_five_bases_and_flags_uncertainty(tmp_path: Path) -> None:
    result = make_quilt(
        tmp_path,
        {
            "drafting/main.tex": PREAMBLE
            + r"""
% !LOOM basis: local-proof
\newtheorem{hypothesis}{Hypothesis}
\newtheorem{conjecture}{Conjecture}
\begin{document}
\begin{definition}\label{ab-0001}A widget is a set.\end{definition}
\begin{lemma}\label{ab-0002}Every widget is a set.\end{lemma}
\begin{proof}By definition.\end{proof}
\begin{hypothesis}\label{ab-0003}Assume every widget is finite.\end{hypothesis}
\begin{conjecture}\label{ab-0004}All widgets are finite.\end{conjecture}
\begin{theorem}[{\cite[Theorem 2.1]{Paper}}]\label{ab-0005}Quoted.\end{theorem}
\begin{theorem}[{\cite{Paper}}]\label{ab-0006}Unlocated.\end{theorem}
\begin{remark}\label{ab-0007}Ambiguous remark.\end{remark}
\begin{remark}\label{ab-0008}
% !LOOM basis: expository
Terminology only.\end{remark}
\begin{theorem}\label{ab-0009}
% !LOOM basis: cited-result
This is quoted later in the block from \cite[Theorem 3]{Paper}.\end{theorem}
\end{document}
""",
            "digests/bibliography.bib": "@article{Paper, title={A paper}}\n",
        },
    )
    assert {k: result.nodes[k].basis for k in [f"ab-000{i}" for i in range(1, 10)]} == {
        "ab-0001": "expository",
        "ab-0002": "local-proof",
        "ab-0003": "assumption",
        "ab-0004": "open-claim",
        "ab-0005": "cited-result",
        "ab-0006": "unclassified",
        "ab-0007": "expository",
        "ab-0008": "expository",
        "ab-0009": "cited-result",
    }
    assert result.nodes["ab-0005"].external
    assert not result.nodes["ab-0006"].external
    assert {d.keys[0] for d in result.lint if d.code == "loom:needs-classification"} == {"ab-0006"}
    assert any(d.code == "loom:misplaced-basis" for d in result.lint)
    bulk = CliRunner().invoke(
        main, ["accept", "--all-live", "--yes", "--force", "--author", "Test author", "--quilt", str(result.quilt.root)]
    )
    assert bulk.exit_code != 0 and "live unclassified keys" in bulk.output
    assert not (result.quilt.root / ".loom" / "state.toml").exists()
    for key, phrase in (("ab-0004", "open claim"), ("ab-0005", "quotes someone else's result")):
        attempt = CliRunner().invoke(
            main, ["accept", key, "--force", "--author", "Test author", "--quilt", str(result.quilt.root)]
        )
        assert attempt.exit_code != 0 and phrase in attempt.output


def test_basis_controls_settlement_not_theorem_style(tmp_path: Path) -> None:
    result = make_quilt(
        tmp_path,
        {
            "drafting/main.tex": PREAMBLE
            + r"""
\newtheorem{hypothesis}{Hypothesis}
\newtheorem{conjecture}{Conjecture}
\begin{document}
\begin{definition}\label{ab-0001}A widget is a set.\end{definition}
\begin{hypothesis}\label{ab-0002}Assume widgets are finite.\end{hypothesis}
\begin{conjecture}\label{ab-0003}Widgets are finite.\end{conjecture}
\begin{lemma}\label{ab-0004}Finite widgets exist.\end{lemma}
\begin{proof}By example.\end{proof}
\begin{remark}\label{ab-0005}
% !LOOM basis: local-proof
Every widget is finite by the preceding construction.\end{remark}
\end{document}
""",
        },
    )
    keys = ["ab-0001", "ab-0002", "ab-0003", "ab-0004", "ab-0004/proof", "ab-0005"]
    write_acceptance(result, keys, "Test author")
    records = Records(result.quilt.root, result.quilt.history_dir)
    derived = records.derived(result, records.key_states(result))
    assert derived["ab-0001"]["settled"]
    assert derived["ab-0002"]["settled"]  # relative to an explicit assumption
    assert not derived["ab-0003"]["settled"]  # an accepted conjecture remains open
    assert derived["ab-0004"]["settled"]
    assert derived["ab-0005"]["settled"]  # the explicit inline argument is accepted with the remark

    master = result.quilt.root / "drafting" / "main.tex"
    master.write_text(master.read_text().replace("% !LOOM basis: local-proof", "% !LOOM basis: expository"))
    rescanned = scan(load_quilt(result.quilt.root))
    changed = Records(result.quilt.root, result.quilt.history_dir).key_states(rescanned)["ab-0005"]
    assert not changed.fresh
    assert "basis-changed" in {cause.kind for cause in changed.causes}


def test_accept_all_live_refuses_to_establish_an_open_claim(tmp_path: Path) -> None:
    result = make_quilt(
        tmp_path,
        {
            "drafting/main.tex": PREAMBLE
            + r"""
\newtheorem{conjecture}{Conjecture}
\begin{document}
\begin{conjecture}\label{ab-0001}Every widget is finite.\end{conjecture}
\end{document}
""",
        },
    )
    attempt = CliRunner().invoke(
        main, ["accept", "--all-live", "--yes", "--force", "--author", "Test author", "--quilt", str(result.quilt.root)]
    )
    assert attempt.exit_code != 0 and "open claims cannot be accepted" in attempt.output
    assert not (result.quilt.root / ".loom" / "state.toml").exists()


def test_zk_proof_after_explanatory_remark_belongs_to_proposition(tmp_path: Path) -> None:
    fixture = (Path(__file__).parent / "fixtures" / "zk_proof_after_remark.tex").read_text()
    result = make_quilt(
        tmp_path, {"drafting/main.tex": PREAMBLE + "\\begin{document}\n" + fixture + "\\end{document}\n"}
    )
    assert result.nodes["zk-000P"].basis == "local-proof"
    assert result.nodes["zk-000Q"].basis == "expository"
    assert result.nodes["zk-000P"].proofs == ["zk-000P/proof"]
    assert result.nodes["zk-000Q"].proofs == []
    assert result.nodes["zk-000P/proof"].of == "zk-000P"
    assert "zk-000P" in result.graph.direct("zk-000Q")
    assert not any(d.code == "loom:missing-proof" and "zk-000P" in d.keys for d in result.lint)
    assert not any(d.code == "loom:needs-classification" and "zk-000Q" in d.keys for d in result.lint)
    plan = plan_atomize(result, "drafting/main.tex", "drafting/spine.tex", keys=["zk-000P"])
    assert any("add an explicit \\ref" in refusal for refusal in plan.refusals)

    records = Records(result.quilt.root, result.quilt.history_dir)
    before = records.derived(result, records.key_states(result))
    assert not before["zk-000P"]["proved"] and not before["zk-000Q"]["settled"]
    write_acceptance(result, ["zk-000P", "zk-000P/proof", "zk-000Q"], "Test author")
    after = Records(result.quilt.root, result.quilt.history_dir)
    derived = after.derived(result, after.key_states(result))
    assert derived["zk-000P"] == {"proved": True, "settled": True}
    assert derived["zk-000Q"] == {"proved": True, "settled": True}


def test_inline_argument_in_remark_is_one_local_proof_acceptance(tmp_path: Path) -> None:
    result = make_quilt(
        tmp_path,
        {
            "drafting/main.tex": PREAMBLE
            + r"""\begin{document}
\begin{definition}\label{ab-0001}A widget is a set.\end{definition}
\begin{remark}\label{ab-0002}
% !LOOM basis: local-proof
The comparison holds by Definition \ref{ab-0001}: both sides describe the same set.
\end{remark}
\end{document}
"""
        },
    )
    assert result.nodes["ab-0002"].basis == "local-proof"
    assert result.nodes["ab-0002"].inline_proof
    assert result.nodes["ab-0002"].proofs == []
    assert "ab-0001" in result.graph.direct("ab-0002")
    assert not any(d.code == "loom:missing-proof" and "ab-0002" in d.keys for d in result.lint)
    write_acceptance(result, ["ab-0002"], "Test author")
    records = Records(result.quilt.root, result.quilt.history_dir)
    derived = records.derived(result, records.key_states(result))
    assert derived["ab-0002"] == {"proved": True, "settled": False}
    write_acceptance(result, ["ab-0001"], "Test author")
    records = Records(result.quilt.root, result.quilt.history_dir)
    assert records.derived(result, records.key_states(result))["ab-0002"]["settled"]


def test_proof_after_remark_needs_a_preceding_claim_or_explicit_reference(tmp_path: Path) -> None:
    result = make_quilt(
        tmp_path,
        {
            "drafting/main.tex": PREAMBLE
            + r"""\begin{document}
\begin{remark}\label{ab-0001}An explanation.\end{remark}
\begin{proof}This proof has no preceding claim.\end{proof}
\begin{remark}\label{ab-0002}A separate claim.\end{remark}
\begin{proof}[Proof of Remark~\ref{ab-0002}]Its explicit target wins.\end{proof}
\end{document}
"""
        },
    )
    assert not result.nodes["ab-0001"].proofs
    assert result.nodes["ab-0002"].proofs == ["ab-0002/proof"]
    assert any(d.code == "loom:unattached-proof" for d in result.diagnostics)


def test_legacy_definition_directive_maps_to_expository(tmp_path: Path) -> None:
    result = make_quilt(
        tmp_path,
        {
            "drafting/main.tex": PREAMBLE
            + r"""\begin{document}
\begin{remark}\label{ab-0001}
% !LOOM basis: definition
This only fixes terminology.
\end{remark}
\end{document}
"""
        },
    )
    assert result.nodes["ab-0001"].basis == "expository"
    assert "legacy" in result.nodes["ab-0001"].basis_reason
