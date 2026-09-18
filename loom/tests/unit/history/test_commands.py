"""The workbench commands on the shim (book chapter 17): canonize, stamp, fork, revert, history, and what each records."""

from __future__ import annotations

import json
import os
from pathlib import Path

from click.testing import CliRunner

from loom.cli import main

PAPER = r"""\documentclass{article}
\usepackage{amsthm}
\newtheorem{theorem}{Theorem}
\newtheorem{lemma}[theorem]{Lemma}
\begin{document}
\section{Setup}
\begin{lemma}\label{lem:a}
Alpha.
\end{lemma}
\begin{proof}
Obvious.
\end{proof}
\begin{theorem}[Main]\label{thm:main}
Beta uses Lemma~\ref{lem:a}.
\end{theorem}
\begin{proof}
Later.
\end{proof}
\end{document}
"""


def run(*args: str, cwd: Path, env: dict[str, str] | None = None):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args), env=env)
    finally:
        os.chdir(old)


def quilt(tmp_path: Path) -> Path:
    paper = tmp_path / "paper"
    paper.mkdir()
    (paper / "main.tex").write_text(PAPER, encoding="utf-8")
    q = tmp_path / "q"
    assert (
        run("init", str(q), "--from", str(paper / "main.tex"), "--prefix", "pp", "--yes", cwd=tmp_path).exit_code == 0
    )
    assert run("draft", "canon/main.tex", "--yes", cwd=q).exit_code == 0
    return q


def ledger(q: Path) -> list[dict]:
    return [json.loads(x) for x in (q / ".loom" / "history" / "ledger.jsonl").read_text().splitlines()]


def test_canonize_writes_a_flat_landmark_and_a_step(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    r = run("canonize", "drafting/main.tex", "-m", "First landmark", cwd=q)
    assert r.exit_code == 2 and "exists; canonize never overwrites" in r.output  # canon/main.tex came from the import
    r = run("canonize", "drafting/main.tex", "--to", "canon/main-v1.tex", "-m", "First landmark", cwd=q)
    assert r.exit_code == 0, r.output
    text = (q / "canon" / "main-v1.tex").read_text()
    assert "\\usepackage{loom}" not in text and "% !LOOM begin loom-macros" in text
    assert "\\providecommand{\\uses}" in text  # a landmark compiles without loom.sty, forever
    assert "\\label{pp-0002}" in text  # the ids stay: versions are per key
    assert "step 0002 froze" in r.output and "Identity test: pass" in r.output

    step = ledger(q)[-1]
    assert step["action"] == "canonize" and step["step"] == 2 and step["dir"] == "0002-main-v1"
    assert step["message"] == "First landmark" and step["document"] == "drafting/main.tex" and step["live"] is True
    # sections are never versioned: a section has no text of its own that a landmark could hold (17.5)
    assert set(step["froze"]) == {"pp-0002", "pp-0002/proof", "pp-0003", "pp-0003/proof"}
    assert step["of"]["pp-0002/proof"] == "pp-0002@2"  # a proof version records the statement version it stood against
    assert sorted(step["reaches"]) == sorted(step["froze"])
    assert step["parent"] == {"step": 1, "how": "declared"}  # the draft said which landmark it came from

    d = q / ".loom" / "history" / "0002-main-v1"
    assert (d / "main-v1.tex").read_text() == text
    assert (d / "preamble.tex").is_file() and (d / "pp-0002.tex").is_file() and (d / "pp-0002.proof.tex").is_file()
    assert "\\begin{lemma}" in (d / "pp-0002.tex").read_text()
    assert run("history", "verify", cwd=q).exit_code == 0


def test_canonize_requires_a_message_and_refuses_a_conflicted_key(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    assert run("canonize", "drafting/main.tex", "--to", "canon/x.tex", cwd=q).exit_code == 2
    node = q / "nodes" / "pp-0002.tex"
    node.parent.mkdir(exist_ok=True)
    node.write_text("\\begin{lemma}\\label{pp-0002}\nA second definition.\n\\end{lemma}\n", encoding="utf-8")
    main = q / "drafting" / "main.tex"
    main.write_text(main.read_text().replace("\\end{document}", "\\input{nodes/pp-0002}\n\\end{document}"))
    r = run("canonize", "drafting/main.tex", "--to", "canon/x.tex", "-m", "m", cwd=q)
    assert r.exit_code == 1 and "pp-0002" in r.output and "defined by two files" in r.output
    assert not (q / "canon" / "x.tex").exists()


def test_stamp_records_only_what_moved(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    assert run("canonize", "drafting/main.tex", "--to", "canon/v1.tex", "-m", "one", cwd=q).exit_code == 0
    nothing = run("stamp", "-m", "nothing changed", cwd=q)
    assert nothing.exit_code == 1 and "nothing to stamp" in nothing.output
    main = q / "drafting" / "main.tex"
    main.write_text(main.read_text().replace("Alpha.", "Alpha, revised."))
    r = run("stamp", "-m", "Referee points", cwd=q)
    assert r.exit_code == 0, r.output
    step = ledger(q)[-1]
    assert step["action"] == "stamp" and step["dir"] == "0003-stamp-referee-points"
    assert list(step["froze"]) == ["pp-0002"] and step["preamble"] is None
    d = q / ".loom" / "history" / "0003-stamp-referee-points"
    assert [p.name for p in sorted(d.iterdir())] == ["pp-0002.tex"]
    assert "Alpha, revised." in (d / "pp-0002.tex").read_text()


def test_history_lists_steps_and_a_key_s_versions(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    assert run("canonize", "drafting/main.tex", "--to", "canon/v1.tex", "-m", "one", cwd=q).exit_code == 0
    main = q / "drafting" / "main.tex"
    main.write_text(main.read_text().replace("Alpha.", "Alpha, revised."))
    assert run("stamp", "-m", "two", cwd=q).exit_code == 0
    r = run("history", cwd=q)
    assert r.exit_code == 0, r.output
    assert "0001  import" in r.output and "0002  canonize" in r.output and '"one"' in r.output
    assert "draft" in r.output and "0003  stamp" in r.output
    k = run("history", "pp-0002", cwd=q)
    assert "pp-0002@2" in k.output and "pp-0002@3" in k.output and "head: the text of @3" in k.output
    j = json.loads(run("history", "pp-0002", "--json", cwd=q).output)
    assert j["head_is"] == 3 and len(j["versions"]) == 2


def test_revert_prints_a_patch_and_records_it(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    assert run("canonize", "drafting/main.tex", "--to", "canon/v1.tex", "-m", "one", cwd=q).exit_code == 0
    main = q / "drafting" / "main.tex"
    before = main.read_text()
    main.write_text(before.replace("Alpha.", "Alpha, revised."))
    r = run("revert", "pp-0002@2", cwd=q)
    assert r.exit_code == 0, r.output
    assert "-Alpha, revised." in r.output and "+Alpha." in r.output
    assert main.read_text() != before  # loom prints the patch; applying it is the author's act
    assert ledger(q)[-1]["action"] == "revert" and ledger(q)[-1]["step"] == 2
    assert "the text of @2" in r.output
    missing = run("revert", "pp-0002@9", cwd=q)
    assert missing.exit_code == 1 and "no step 9" in missing.output


def test_fork_gives_a_document_its_own_copy(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    assert run("atomize", "drafting/main.tex", "drafting/spine.tex", cwd=q).exit_code == 0
    (q / "drafting" / "talk.tex").write_text(
        "\\documentclass{article}\n\\usepackage{amsthm}\n\\usepackage{loom}\n"
        "\\newtheorem{theorem}{Theorem}\n\\newtheorem{lemma}[theorem]{Lemma}\n"
        "\\begin{document}\n\\input{nodes/pp-0002}\nSee Lemma~\\ref{pp-0002}.\n\\end{document}\n",
        encoding="utf-8",
    )
    r = run("fork", "pp-0002", "--in", "drafting/talk.tex", cwd=q)
    assert r.exit_code == 0, r.output
    new_id = next(p.stem for p in (q / "nodes").glob("pp-*.tex") if p.stem not in ("pp-0001", "pp-0002", "pp-0003"))
    assert f"Wrote nodes/{new_id}.tex" in r.output
    assert f"\\label{{{new_id}}}" in (q / "nodes" / f"{new_id}.tex").read_text()
    assert f"+\\input{{nodes/{new_id}}}" in r.output and f"+See Lemma~\\ref{{{new_id}}}." in r.output
    assert "\\input{nodes/pp-0002}" in (q / "drafting" / "talk.tex").read_text()  # the patch is the author's to apply
    line = ledger(q)[-1]
    assert line["action"] == "fork" and line["new"] == new_id and line["from"]["id"] == "pp-0002"
    assert line["in"] == "drafting/talk.tex"


def test_fork_from_a_recorded_version(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    assert run("canonize", "drafting/main.tex", "--to", "canon/v1.tex", "-m", "one", cwd=q).exit_code == 0
    main = q / "drafting" / "main.tex"
    main.write_text(main.read_text().replace("Alpha.", "Alpha, revised."))
    r = run("fork", "pp-0002", "--in", "drafting/main.tex", "--from", "@2", "--as", "pp-0100", cwd=q)
    assert r.exit_code == 0, r.output
    assert "+Alpha." in r.output and "pp-0100" in r.output  # the older text, under the new id
    assert ledger(q)[-1]["from"]["step"] == 2
    taken = run("fork", "pp-0002", "--in", "drafting/main.tex", "--as", "pp-0001", cwd=q)
    assert taken.exit_code == 1 and "taken" in taken.output


def test_an_id_the_history_recorded_is_never_allocated_again(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    assert run("canonize", "drafting/main.tex", "--to", "canon/v1.tex", "-m", "one", cwd=q).exit_code == 0
    main = q / "drafting" / "main.tex"
    text = main.read_text()
    start = text.index("\\begin{theorem}")
    end = text.index("\\end{proof}", text.index("Later.")) + len("\\end{proof}\n")
    main.write_text(text[:start] + text[end:])
    assert run("stamp", "-m", "dropped the theorem", cwd=q).exit_code == 0
    assert ledger(q)[-1]["removed"] == ["pp-0003", "pp-0003/proof"]
    nxt = run("id", "--next", cwd=q).output.strip()
    assert nxt == "pp-0004", nxt  # pp-0003 is retired: the allocator consults the history


def test_a_retired_id_written_again_is_reuse_or_recovery(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    assert run("canonize", "drafting/main.tex", "--to", "canon/v1.tex", "-m", "one", cwd=q).exit_code == 0
    main = q / "drafting" / "main.tex"
    text = main.read_text()
    start = text.index("\\begin{theorem}")
    end = text.index("\\end{proof}", text.index("Later.")) + len("\\end{proof}\n")
    main.write_text(text[:start] + text[end:])
    assert run("stamp", "-m", "dropped", cwd=q).exit_code == 0

    main.write_text(text)  # the same text back under the same id
    lint = run("lint", cwd=q)
    assert "loom:node-recovered" in lint.output and "loom:id-reused" not in lint.output

    main.write_text(text.replace("Beta uses", "Gamma uses"))
    lint2 = run("lint", cwd=q)
    assert "loom:id-reused" in lint2.output and "an id names one node forever" in lint2.output
    assert lint2.exit_code == 1


def test_canon_edited_is_reported_with_its_fixes(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    canon = q / "canon" / "main.tex"
    canon.write_text(canon.read_text() + "% an edit after the fact\n")
    lint = run("lint", cwd=q)
    assert "loom:canon-edited" in lint.output and "0001-main" in lint.output
    nodes = run("lint", "--nodes", cwd=q)
    assert nodes.exit_code == 0  # a warning about the record is not a node's problem
    js = json.loads(run("lint", "--json", cwd=q).output)
    edited = next(d for d in js if d["code"] == "loom:canon-edited")
    assert edited["subject"] == "record" and any("loom draft" in f["command"] for f in edited["fixes"])


def test_history_verify_reports_an_edited_record(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    assert run("canonize", "drafting/main.tex", "--to", "canon/v1.tex", "-m", "one", cwd=q).exit_code == 0
    v = q / ".loom" / "history" / "0002-v1" / "pp-0002.tex"
    v.write_text(v.read_text() + "% edited by hand\n")
    r = run("history", "verify", cwd=q)
    assert r.exit_code == 1 and "loom:history-edited" in r.output and "pp-0002" in r.output
    v.unlink()
    r2 = run("history", "verify", cwd=q)
    assert r2.exit_code == 1 and "loom:history-missing" in r2.output


def test_canonize_aliases_print_one_line(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    r = run("canonicalize", "drafting/main.tex", "--to", "canon/v1.tex", "-m", "one", cwd=q)
    assert r.exit_code == 0, r.output
    assert "canonicalize \u2192 canonize" in r.output
