"""`loom deloom`: a flat document with loom's marks taken out and every other line as written; a referenced id-only result and an `\\incomplete` block it unless kept."""

from __future__ import annotations

import json
from pathlib import Path

from loom.reshape.deloom import INCOMPLETE_DEF, deloom
from tests.helpers import ok, run

IDS = {"zk-0001", "zk-0002", "zk-0003", "zk-0003-ai"}

PAPER = r"""\documentclass{article}
\usepackage{amsmath,loom,amsthm}
% !LOOM name: the paper
\newtheorem{lemma}{Lemma}
\begin{document}
\begin{lemma}\label{zk-0001}\label{lem:first}
First, see Lemma~\ref{zk-0002} % \label{zk-0001} in a comment stays
\end{lemma}
\begin{lemma}\label{zk-0002}
  \label{lem:second}
Second uses \cref{zk-0001, lem:second}.
\end{lemma}
\begin{proof}
  \uses{zk-0001}
By Lemma~\ref{zk-0001}.
\end{proof}
\begin{verbatim}
\label{zk-0001}
\end{verbatim}
\end{document}
"""


def test_every_loom_mark_goes_and_references_move_to_the_authors_labels() -> None:
    done = deloom(PAPER, IDS)
    assert not done.blocked
    text = done.text
    assert "\\usepackage{amsmath,amsthm}" in text
    assert "!LOOM" not in text and "\\uses" not in text
    assert "\\begin{lemma}\\label{lem:first}" in text
    assert "\\begin{lemma}\n  \\label{lem:second}" in text  # the line that held only the id is gone
    assert (
        "Lemma~\\ref{lem:second}" in text
        and "\\cref{lem:first, lem:second}" in text
        and "By Lemma~\\ref{lem:first}." in text
    )
    assert "% \\label{zk-0001} in a comment stays" in text
    assert "\\begin{verbatim}\n\\label{zk-0001}\n\\end{verbatim}" in text
    assert sorted(done.removed) == ["zk-0001", "zk-0002"]
    assert done.moved == 3 and done.uses == 1 and done.directives == 1
    # nothing else moved: the rest of the document is line for line the source
    assert text.count("\n") == PAPER.count("\n") - 2


def test_a_referenced_result_labelled_only_by_its_id_blocks_until_kept() -> None:
    paper = PAPER.replace(
        "\\end{document}", "\\begin{lemma}\\label{zk-0003}\nThird.\n\\end{lemma}\nSee \\ref{zk-0003}.\n\\end{document}"
    )
    blocked = deloom(paper, IDS)
    assert blocked.blocked and blocked.blocked_ids == {"zk-0003": 1} and not blocked.text
    kept = deloom(paper, IDS, keep_ids=True)
    assert not kept.blocked
    assert "\\label{zk-0003}" in kept.text and "See \\ref{zk-0003}." in kept.text
    line = kept.text.splitlines()[kept.kept_ids["zk-0003"] - 1]
    assert line == "\\begin{lemma}\\label{zk-0003}"
    # an unreferenced id-only label is simply removed
    quiet = deloom(paper.replace("See \\ref{zk-0003}.", ""), IDS)
    assert not quiet.blocked and "zk-0003" not in quiet.text


def test_an_incomplete_blocks_until_kept_and_is_then_defined_where_loom_was() -> None:
    paper = PAPER.replace("First, see", "First, \\incomplete{the case \\(n = {2}\\)} see")
    blocked = deloom(paper, IDS)
    assert blocked.blocked and blocked.blocked_incomplete == [7]
    kept = deloom(paper, IDS, keep_incomplete=True)
    assert not kept.blocked
    assert "\\incomplete{the case \\(n = {2}\\)}" in kept.text
    assert INCOMPLETE_DEF in kept.text and kept.text.index(INCOMPLETE_DEF) < kept.text.index("\\begin{document}")
    assert kept.text.splitlines()[kept.kept_incomplete[0] - 1].startswith("First, \\incomplete{")


def test_the_macro_block_plain_writes_goes_with_it() -> None:
    from loom.reshape.linearize import to_canon

    done = deloom(to_canon(PAPER.replace("\\usepackage{amsmath,loom,amsthm}", "\\usepackage{loom}")), IDS)
    assert (
        "!LOOM" not in done.text
        and "\\providecommand{\\nest}" not in done.text
        and "\\usepackage{loom}" not in done.text
    )


def test_the_command_refuses_naming_each_blocker_and_its_flag(tmp_path: Path) -> None:
    ok("init", str(tmp_path / "demo"), "--demo", cwd=tmp_path)
    d = tmp_path / "demo"
    main = d / "drafting/main.tex"
    text = main.read_text()
    main.write_text(text.replace("\\end{document}", "\\incomplete{Later.}\n\\end{document}"))
    refused = run("deloom", "main.tex", "--to", "build/plain.tex", cwd=d)
    assert refused.exit_code == 1
    assert "\\incomplete" in refused.output and "--keep-incomplete" in refused.output
    assert not (d / "build/plain.tex").exists()
    done = ok(
        "deloom", "main", "--to", "build/plain.tex", "--keep-incomplete", "--keep-referenced-ids", "--json", cwd=d
    )
    answer = json.loads(done.stdout)
    assert answer["source"] == "drafting/main.tex" and answer["kept_incomplete"]
    plain = (d / "build/plain.tex").read_text()
    assert "\\uses" not in plain and "\\usepackage{loom}" not in plain
    assert not [i for i in answer["removed"] if i in plain]


def test_the_target_is_never_a_live_document_or_a_source(tmp_path: Path) -> None:
    ok("init", str(tmp_path / "demo"), "--demo", cwd=tmp_path)
    d = tmp_path / "demo"
    into_drafting = run(
        "deloom", "main.tex", "--to", "drafting/plain.tex", "--keep-incomplete", "--keep-referenced-ids", cwd=d
    )
    assert into_drafting.exit_code == 2 and "drafting directory" in into_drafting.output
    onto_source = run(
        "deloom", "main.tex", "--to", "nodes/dm-0001.tex", "--keep-incomplete", "--keep-referenced-ids", cwd=d
    )
    assert onto_source.exit_code == 2 and "sources" in onto_source.output
