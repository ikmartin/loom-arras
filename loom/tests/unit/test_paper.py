"""Chapter 6 on the shim: id, import (with the closure, the diff, anchoring, in-place), init --from, atomize, inline, and the identity test."""

from __future__ import annotations

import json
import os
from pathlib import Path

from click.testing import CliRunner

from loom.cli import main
from loom.reshape.anchoring import anchoring_violations, fix_anchoring
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan

PAPER = r"""\documentclass{amsart}
\usepackage{amsthm}
\input{preamble}
\newtheorem{theorem}{Theorem}[section]
\newtheorem{lemma}[theorem]{Lemma}
\theoremstyle{definition}
\newtheorem{definition}[theorem]{Definition}
\begin{document}
\section{Setup}
\begin{definition}[Widget]\label{def:widget}
A widget is a pair.
\end{definition}
\input{sections/results}
\includegraphics{figures/fig.pdf}
\bibliography{refs}
\end{document}
"""
RESULTS = r"""\section{Results}\label{sec:results}
\begin{lemma}\label{lem:a}
Alpha, see Definition~\ref{def:widget}.
\end{lemma}
\begin{proof}
Obvious.
\end{proof}

Prose between, compare~\ref{thm:missing}.

\begin{theorem}[Main]\label{thm:main}
Beta uses Lemma~\ref{lem:a}.
\end{theorem}
\begin{proof}[Proof of Theorem~\ref{thm:main}]
Later.
\end{proof}
"""


def run(*args: str, cwd: Path, stdin: str | None = None):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args), input=stdin)
    finally:
        os.chdir(old)


def paper_dir(tmp_path: Path, results: str = RESULTS) -> Path:
    p = tmp_path / "paper"
    (p / "sections").mkdir(parents=True)
    (p / "figures").mkdir()
    (p / "main.tex").write_text(PAPER)
    (p / "preamble.tex").write_text("\\usepackage{amsmath}\n")
    (p / "sections" / "results.tex").write_text(results)
    (p / "figures" / "fig.pdf").write_bytes(b"%PDF-1.4\n%fake\n")
    (p / "refs.bib").write_text("@misc{x, title={X}}\n")
    (tmp_path / "elsewhere.tex").write_text("outside\n")
    return p


def imported(tmp_path: Path, results: str = RESULTS) -> Path:
    p = paper_dir(tmp_path, results)
    r = run("init", str(tmp_path / "q"), "--from", str(p / "main.tex"), "--prefix", "pp", "--yes", cwd=tmp_path)
    assert r.exit_code == 0, r.output
    return tmp_path / "q"


def drafted(tmp_path: Path, *flags: str) -> Path:
    q = imported(tmp_path)
    r = run("draft", "canon/main.tex", "--yes", *flags, cwd=q)
    assert r.exit_code == 0, r.output
    return q


def test_import_writes_one_flat_canon_document(tmp_path: Path) -> None:
    """A landmark is the paper as it arrived: one self-contained file, nothing inserted, the assets beside it, and step 0001."""
    p = paper_dir(tmp_path)
    r = run("init", str(tmp_path / "q"), "--from", str(p / "main.tex"), "--prefix", "pp", "--yes", cwd=tmp_path)
    assert r.exit_code == 0, r.output
    q = tmp_path / "q"
    for rel in ("canon/main.tex", "figures/fig.pdf", "refs.bib", "loom.sty", "config.toml"):
        assert (q / rel).exists(), rel
    canon = (q / "canon" / "main.tex").read_text()
    assert "\\input{sections/results}" not in canon and "\\input{preamble}" not in canon
    assert "\\usepackage{amsmath}" in canon and "Beta uses Lemma" in canon  # both inlined in place
    assert "\\usepackage{loom}" not in canon and "\\label{pp-" not in canon
    assert not (q / "sections").exists() and not (q / "preamble.tex").exists()  # inlined, so not copied
    assert not any((q / "drafting").iterdir())
    assert (p / "main.tex").read_text() == PAPER  # the original is untouched
    assert "Identity test: pass" in r.output

    ledger = [json.loads(line) for line in (q / ".loom" / "history" / "ledger.jsonl").read_text().splitlines()]
    assert len(ledger) == 1
    (step,) = ledger
    assert step["action"] == "import" and step["step"] == 1 and step["dir"] == "0001-main"
    assert step["to"]["path"] == "canon/main.tex" and step["froze"] == {}
    assert (q / ".loom" / "history" / "0001-main" / "main.tex").read_text() == canon


def test_import_refuses_an_existing_canon_document(tmp_path: Path) -> None:
    q = imported(tmp_path)
    p = tmp_path / "paper"
    again = run("import", str(p / "main.tex"), "--yes", cwd=q)
    assert again.exit_code == 1 and "canon/main.tex exists" in again.output
    assert len((q / ".loom" / "history" / "ledger.jsonl").read_text().splitlines()) == 1


def test_import_asks_before_writing(tmp_path: Path) -> None:
    p = paper_dir(tmp_path)
    assert run("init", str(tmp_path / "q"), "--prefix", "pp", "--yes", cwd=tmp_path).exit_code == 0
    q = tmp_path / "q"
    r = run("import", str(p / "main.tex"), cwd=q)
    assert r.exit_code == 2 and "needs confirmation" in r.output
    assert not (q / "canon" / "main.tex").exists()
    r2 = run("import", str(p / "main.tex"), "--yes", cwd=q)
    assert r2.exit_code == 0, r2.output
    assert "-> canon/main.tex (linearized, 2 files inlined)" in r2.output


def test_draft_labels_the_copy_sets_main_and_records_it(tmp_path: Path) -> None:
    """A working document is loom's own file: the package line and an id on every node, inserted in the copy and never in the landmark."""
    q = imported(tmp_path)
    before = (q / "canon" / "main.tex").read_text()
    r = run("draft", "canon/main.tex", "--yes", cwd=q)
    assert r.exit_code == 0, r.output
    main = (q / "drafting" / "main.tex").read_text()
    assert main.splitlines()[1] == "\\usepackage{loom}"
    assert "\\section{Setup}\\label{pp-0001}" in main  # ids follow document order
    assert "\\begin{definition}[Widget]\\label{pp-0002}\\label{def:widget}" in main
    assert "\\section{Results}\\label{pp-0003}" in main and "\\begin{lemma}\\label{pp-0004}" in main
    assert "\\label{lem:a}" in main  # the author's labels stay, as aliases
    assert (q / "canon" / "main.tex").read_text() == before  # the landmark is untouched
    assert 'main = "drafting/main.tex"' in (q / "config.toml").read_text()
    assert "Identity test: pass" in r.output and "Nodes:" in r.output and "Proofs:" in r.output

    line = json.loads((q / ".loom" / "history" / "ledger.jsonl").read_text().splitlines()[-1])
    assert line["action"] == "draft" and line["from"]["path"] == "canon/main.tex" and line["from"]["step"] == 1
    assert line["to"]["path"] == "drafting/main.tex" and line["ids"] == 5
    assert "dangling-link" in run("lint", cwd=q).output  # thm:missing was never defined in the paper


def test_draft_refuses_a_second_copy_and_a_path_outside_drafting(tmp_path: Path) -> None:
    q = drafted(tmp_path)
    again = run("draft", "canon/main.tex", "--yes", cwd=q)
    assert again.exit_code == 2 and "exists; draft never overwrites" in again.output
    out = run("draft", "canon/main.tex", "--to", "nodes/main.tex", "--yes", cwd=q)
    assert out.exit_code == 2 and "goes directly under drafting/" in out.output
    not_canon = run("draft", "drafting/main.tex", "--to", "drafting/other.tex", "--yes", cwd=q)
    assert not_canon.exit_code == 2 and "is not a canon document" in not_canon.output


def test_draft_refuses_line_anchoring_and_fix_anchoring(tmp_path: Path) -> None:
    bad = RESULTS.replace("\\begin{lemma}\\label{lem:a}\nAlpha", "\\begin{lemma}\\label{lem:a} Alpha").replace(
        "Obvious.\n\\end{proof}", "Obvious. \\end{proof}"
    )
    q = imported(tmp_path, bad)  # import takes the paper as it is; anchoring only matters once ids are inserted
    r = run("draft", "canon/main.tex", "--yes", cwd=q)
    assert r.exit_code == 1 and "line-anchoring" in r.output and not (q / "drafting" / "main.tex").exists()
    r2 = run("draft", "canon/main.tex", "--yes", "--fix-anchoring", cwd=q)
    assert r2.exit_code == 0, r2.output
    fixed = (q / "drafting" / "main.tex").read_text()
    assert "\\begin{lemma}\\label{pp-" in fixed and "\nAlpha" in fixed and "Obvious.\n\\end{proof}" in fixed
    assert anchoring_violations(fixed, {"lemma", "theorem", "definition"}) == []


def test_anchoring_violation_reports_the_authors_line(tmp_path: Path) -> None:
    """The draft gains \\usepackage{loom} in loom's staged copy; the lines it reports are the canon document's, which that insertion must not shift."""
    p = paper_dir(tmp_path)
    bad = PAPER.replace(
        "\\begin{definition}[Widget]\\label{def:widget}\nA widget",
        "\\begin{definition}[Widget]\\label{def:widget} A widget",
    )
    (p / "main.tex").write_text(bad)
    assert (
        run(
            "init", str(tmp_path / "q"), "--from", str(p / "main.tex"), "--prefix", "pp", "--yes", cwd=tmp_path
        ).exit_code
        == 0
    )
    q = tmp_path / "q"
    canon = (q / "canon" / "main.tex").read_text()
    expected = next(i for i, line in enumerate(canon.splitlines(), 1) if "\\begin{definition}" in line)
    r = run("draft", "canon/main.tex", "--yes", cwd=q)
    assert r.exit_code == 1, r.output
    assert f"line {expected}: \\begin{{definition}}" in r.output, r.output


def test_fix_anchoring_unit() -> None:
    text = (
        "Text \\begin{lemma}\\label{x} body\nmore \\end{lemma} tail\n\\begin{setting}\\label{y}one line\\end{setting}\n"
    )
    out = fix_anchoring(text, {"lemma", "setting"})
    assert (
        out
        == "Text\n\\begin{lemma}\\label{x}\nbody\nmore\n\\end{lemma}\ntail\n\\begin{setting}\\label{y}\none line\n\\end{setting}\n"
    )
    assert anchoring_violations(out, {"lemma", "setting"}) == []
    assert [v.line for v in anchoring_violations(text, {"lemma", "setting"})] == [1, 2, 3, 3]


def test_import_outside_tree_warning_and_in_place(tmp_path: Path) -> None:
    p = paper_dir(tmp_path)
    (p / "main.tex").write_text(PAPER.replace("\\input{preamble}", "\\input{preamble}\n\\input{../elsewhere}"))
    r = run("init", str(p), "--from", str(p / "main.tex"), "--prefix", "pp", "--yes", cwd=tmp_path)
    assert r.exit_code in (0, 1), r.output
    assert "loom:import-outside-tree" in r.output
    assert (p / "config.toml").exists() and (p / "canon" / "main.tex").is_file()
    assert (p / "main.tex").read_text().startswith("\\documentclass")  # the original still there, unmodified
    assert "\\input{../elsewhere}" in (p / "canon" / "main.tex").read_text()  # left as written; loom copied nothing


def test_id_prints_patch_and_to_writes_copy(tmp_path: Path) -> None:
    q = drafted(tmp_path)
    (q / "nodes" / "extra.tex").write_text(
        "\\begin{lemma}\\label{lem:extra}\nE\n\\end{lemma}\n\\subsection{Sub}\n\\paragraph{Par}\n"
    )
    r = run("id", "nodes/extra.tex", cwd=q)
    assert r.exit_code == 0, r.output
    assert (
        "+\\begin{lemma}\\label{pp-" in r.output
        and "+\\subsection{Sub}\\label{pp-" in r.output
        and "\\paragraph{Par}\\label" not in r.output
    )
    r2 = run("id", "nodes/extra.tex", "--all-levels", "--no-sections", cwd=q)
    assert "\\subsection{Sub}\\label" not in r2.output
    r3 = run("id", "nodes/extra.tex", "--to", str(tmp_path / "extra-labelled.tex"), cwd=q)
    assert r3.exit_code == 0 and "\\label{pp-" in (tmp_path / "extra-labelled.tex").read_text()
    assert "\\label{pp-" not in (q / "nodes" / "extra.tex").read_text()
    assert run("id", "nodes/extra.tex", "--to", str(tmp_path / "extra-labelled.tex"), cwd=q).exit_code == 2


def test_atomize_requires_dest_moves_nodes_and_identity(tmp_path: Path) -> None:
    q = drafted(tmp_path)
    r = run("atomize", "drafting/main.tex", cwd=q)
    assert r.exit_code == 2 and "specify a destination file after the source, or with --to" in r.output
    r2 = run("atomize", "drafting/main.tex", "drafting/spine.tex", cwd=q)
    assert r2.exit_code == 0, r2.output
    spine = (q / "drafting" / "spine.tex").read_text()
    assert "\\input{nodes/pp-" in spine and "\\begin{definition}" not in spine
    node_files = sorted(f for f in (q / "nodes").glob("pp-*.tex") if ".proof" not in f.name)
    assert len(node_files) == 3  # the definition, the lemma with its adjacent proof, the theorem
    assert any("\\begin{definition}[Widget]" in f.read_text() for f in node_files)
    assert "Identity test: pass" in r2.output
    assert (q / "drafting" / "main.tex").read_text().count("\\begin{definition}") == 1  # SRC untouched on disk
    lemma = next(f for f in node_files if "Alpha" in f.read_text())
    assert "\\begin{proof}\nObvious." in lemma.read_text()  # adjacent proof travels with its statement
    files = {f.name for f in (q / "nodes").glob("*.tex")}
    assert any(f.endswith(".proof.tex") for f in files), files  # the deferred proof of the theorem

    # the source is superseded, not edited: it defines nothing, and no id is defined twice
    line = json.loads((q / ".loom" / "history" / "ledger.jsonl").read_text().splitlines()[-1])
    assert line["action"] == "atomize" and line["superseded"] == ["drafting/main.tex"]
    lint = run("lint", cwd=q)
    assert "duplicate-id" not in lint.output and "loom:superseded-file" in lint.output
    assert 'main = "drafting/spine.tex"' in (q / "config.toml").read_text()  # the default master moved with the spine

    assert run("atomize", "drafting/main.tex", "drafting/again.tex", cwd=q).exit_code == 1  # superseded


def test_live_makes_a_superseded_document_define_again(tmp_path: Path) -> None:
    q = drafted(tmp_path)
    assert run("atomize", "drafting/main.tex", "drafting/spine.tex", cwd=q).exit_code == 0
    assert "duplicate-id" not in run("lint", cwd=q).output
    r = run("live", "drafting/main.tex", cwd=q)
    assert r.exit_code == 0 and "is live" in r.output
    lint = run("lint", cwd=q)
    assert "duplicate-id" in lint.output  # both define every node now, and neither wins
    assert "loom:superseded-file" not in lint.output
    assert run("live", "drafting/main.tex", cwd=q).exit_code == 2  # not superseded any more


def test_atomize_retire_moves_the_source(tmp_path: Path) -> None:
    q = drafted(tmp_path)
    r = run("atomize", "drafting/main.tex", "drafting/spine.tex", "--retire", cwd=q)
    assert r.exit_code == 0, r.output
    assert not (q / "drafting" / "main.tex").exists()
    assert (q / "retired" / "drafting" / "main.tex").read_text().count("\\begin{definition}") == 1
    line = json.loads((q / ".loom" / "history" / "ledger.jsonl").read_text().splitlines()[-1])
    assert line["retired"] == ["retired/drafting/main.tex"] and line["superseded"] == []
    assert "duplicate-id" not in run("lint", cwd=q).output  # retired/ is not scanned


def test_atomize_proofs_separate_directives_sections_and_all(tmp_path: Path) -> None:
    q = imported(tmp_path)
    canon = q / "canon" / "main.tex"
    canon.write_text(canon.read_text().replace("\\begin{lemma}", "% !LOOM tags: moved-with-me\n\\begin{lemma}", 1))
    assert run("draft", "canon/main.tex", "--yes", cwd=q).exit_code == 0
    r = run("atomize", "drafting/main.tex", "drafting/spine.tex", "--proofs", "separate", cwd=q)
    assert r.exit_code == 0, r.output
    lemma = next(f for f in (q / "nodes").glob("pp-*.tex") if "Alpha" in f.read_text())
    assert lemma.read_text().startswith("% !LOOM tags: moved-with-me\n") and "\\begin{proof}" not in lemma.read_text()
    proof = next(f for f in (q / "nodes").glob("*.proof.tex") if "Obvious" in f.read_text())
    assert proof.exists()


def test_atomize_sections_and_inline_round_trip(tmp_path: Path) -> None:
    q = drafted(tmp_path)
    before = (q / "drafting" / "main.tex").read_text()
    r = run("atomize", "drafting/main.tex", "drafting/spine.tex", "--sections", cwd=q)
    assert r.exit_code == 0, r.output
    spine = (q / "drafting" / "spine.tex").read_text()
    assert "\\input{nodes/pp-" in spine and "\\section{Results}" not in spine
    section_file = next(f for f in (q / "nodes").glob("pp-*.tex") if "\\section{Results}" in f.read_text())
    assert "\\input{nodes/pp-" in section_file.read_text() and "Prose between" in section_file.read_text()
    r2 = run("inline", "drafting/spine.tex", "drafting/back.tex", "--all", cwd=q)
    assert r2.exit_code == 0, r2.output
    assert (q / "drafting" / "back.tex").read_text().split() == before.split()
    assert run("inline", "drafting/spine.tex", "drafting/back.tex", cwd=q).exit_code == 2


def test_inline_nest_shifts_and_identity_on_master(tmp_path: Path) -> None:
    q = drafted(tmp_path)
    (q / "sections").mkdir(exist_ok=True)
    (q / "sections" / "nested.tex").write_text("\\section{Nested}\\label{pp-0100}\nN\n")
    m = q / "drafting" / "main.tex"
    m.write_text(m.read_text().replace("\\end{document}", "\\nest{sections/nested}\n\\end{document}"))
    r = run("inline", "drafting/main.tex", "drafting/flat.tex", "--all", cwd=q)
    assert r.exit_code == 0, r.output
    flat = (q / "drafting" / "flat.tex").read_text()
    assert "\\subsection{Nested}" in flat and "\\nest{" not in flat
    assert "Identity test: pass" in r.output
    res = scan(load_quilt(q))
    assert "drafting/flat.tex" in res.masters


def test_linearize_refuses_shared_nodes_keeps_or_forks_them(tmp_path: Path) -> None:
    """A node is defined once and included many times: inlining a file two documents include would define it twice, so linearize refuses and names both continuations."""
    q = drafted(tmp_path)
    assert run("atomize", "drafting/main.tex", "drafting/spine.tex", cwd=q).exit_code == 0
    shared = next(f for f in sorted((q / "nodes").glob("pp-*.tex")) if "Alpha" in f.read_text())
    (q / "drafting" / "talk.tex").write_text(
        "\\documentclass{article}\n\\usepackage{amsthm}\n\\usepackage{loom}\n"
        "\\newtheorem{theorem}{Theorem}\n\\newtheorem{lemma}[theorem]{Lemma}\n"
        "\\begin{document}\n\\input{nodes/" + shared.stem + "}\n\\end{document}\n"
    )
    refused = run("linearize", "drafting/talk.tex", "--to", "drafting/talk-flat.tex", "--no-check", cwd=q)
    assert refused.exit_code == 1 and "also included by drafting/spine.tex" in refused.output
    assert not (q / "drafting" / "talk-flat.tex").exists()

    kept = run("linearize", "drafting/talk.tex", "--to", "drafting/talk-kept.tex", "--keep-shared", "--no-check", cwd=q)
    assert kept.exit_code == 0, kept.output
    text = (q / "drafting" / "talk-kept.tex").read_text()
    assert "% !LOOM shared:" in text and f"\\input{{nodes/{shared.stem}}}" in text
    assert run("live", "drafting/talk.tex", cwd=q).exit_code == 0

    forked = run("linearize", "drafting/talk.tex", "--to", "drafting/talk-fork.tex", "--fork", "--no-check", cwd=q)
    assert forked.exit_code == 0, forked.output
    flat = (q / "drafting" / "talk-fork.tex").read_text()
    assert "\\input{nodes/" not in flat and "Alpha" in flat
    new_id = flat.split("\\label{")[1].split("}")[0]
    assert new_id.startswith("pp-") and new_id != shared.stem
    assert "duplicate-id" not in run("lint", cwd=q).output


def test_selector_survives_atomize(tmp_path: Path) -> None:
    """A quote-anchored comment on a theorem stays attached after the theorem moves into nodes/<id>.tex: the key and the text are unchanged, only the file is."""
    q = drafted(tmp_path)
    r = run("comment", "pp-0005", "Which lemma?", "--quote", "Beta uses", "--kind", "question", "--author", "R", cwd=q)
    assert r.exit_code == 0, r.output
    before = run("status", "--explain", "pp-0005", cwd=q).output
    assert "1 open question" in before and "detached" not in before
    assert run("atomize", "drafting/main.tex", "drafting/spine.tex", cwd=q).exit_code == 0
    after = run("status", "--explain", "pp-0005", cwd=q).output
    assert "1 open question" in after and "detached" not in after, after
    assert "nodes/pp-0005.tex" in after
    assert "detached-annotation" not in run("lint", cwd=q).output


def _quilt_from_paper(tmp_path: Path) -> Path:
    return drafted(tmp_path)


def test_id_next_prints_a_free_id_and_inserts_nothing(tmp_path: Path) -> None:
    q = _quilt_from_paper(tmp_path)
    before = (q / "drafting" / "main.tex").read_text()
    r = run("id", "--next", cwd=q)
    assert r.exit_code == 0
    allocated = r.output.strip()
    assert allocated.startswith("pp-") and allocated not in (q / "drafting" / "main.tex").read_text()
    assert (q / "drafting" / "main.tex").read_text() == before
    assert json.loads(run("id", "--next", "--json", cwd=q).output) == {"id": allocated, "prefix": "pp"}
    assert run("id", cwd=q).exit_code == 2  # a file, or --next


def test_atomize_one_key_writes_the_node_and_leaves_the_source_to_the_author(tmp_path: Path) -> None:
    q = _quilt_from_paper(tmp_path)
    result = scan(load_quilt(q))
    key = next(k for k, n in result.assembly.nodes.items() if n.kind == "environment" and n.file == "drafting/main.tex")
    before = (q / "drafting" / "main.tex").read_text()
    states_before = sorted(run("status", cwd=q).output.splitlines())

    r = run("atomize", "--key", key, cwd=q)
    assert r.exit_code == 0, r.output
    node_file = q / "nodes" / f"{key}.tex"
    assert node_file.is_file() and key in node_file.read_text()
    assert (q / "drafting" / "main.tex").read_text() == before, "loom never edits the source"
    assert f"+\\input{{nodes/{key}}}" in r.output and f"-\\begin{{definition}}[Widget]\\label{{{key}}}" in r.output

    # applying the patch is the author's act; afterwards the quilt holds one definition and every state is where it was
    patched = before.replace(node_file.read_text().rstrip("\n"), f"\\input{{nodes/{key}}}")
    (q / "drafting" / "main.tex").write_text(patched)
    assert "duplicate-id" not in run("lint", cwd=q).output, "one definition of the node, once the patch is applied"
    assert sorted(run("status", cwd=q).output.splitlines()) == states_before, "moving a node into nodes/ moves no state"


def test_atomize_key_json_writes_nothing_and_carries_the_edit(tmp_path: Path) -> None:
    q = _quilt_from_paper(tmp_path)
    result = scan(load_quilt(q))
    key = next(k for k, n in result.assembly.nodes.items() if n.kind == "environment" and n.file == "drafting/main.tex")
    r = run("atomize", "--key", key, "--json", cwd=q)
    assert r.exit_code == 0, r.output
    plan = json.loads(r.output)
    assert plan["keys"] == [key] and plan["refusals"] == []
    (edit,) = plan["edits"]
    assert edit["file"] == "drafting/main.tex" and edit["text"] == f"\\input{{nodes/{key}}}"
    (made,) = plan["files"]
    assert made["path"] == f"nodes/{key}.tex" and made["text"].endswith("\n")
    text = (q / "drafting" / "main.tex").read_text()
    assert text[edit["start"] : edit["end"]] == made["text"].rstrip("\n"), "the region is what moves"
    assert not (q / "nodes" / f"{key}.tex").exists(), "--json writes nothing"


def test_atomize_key_refuses_what_it_cannot_move(tmp_path: Path) -> None:
    q = _quilt_from_paper(tmp_path)
    result = scan(load_quilt(q))
    key = next(k for k, n in result.assembly.nodes.items() if n.kind == "environment" and n.file == "drafting/main.tex")
    section = next(k for k, n in result.assembly.nodes.items() if n.kind == "section")

    assert run("atomize", "--key", key, cwd=q).exit_code == 0
    main = q / "drafting" / "main.tex"
    moved = (q / "nodes" / f"{key}.tex").read_text().rstrip("\n")
    main.write_text(main.read_text().replace(moved, f"\\input{{nodes/{key}}}"))
    already = run("atomize", "--key", key, cwd=q)
    assert already.exit_code == 1 and "already lives in" in already.output
    sec = run("atomize", "--key", section, cwd=q)
    assert sec.exit_code == 1 and "is a section" in sec.output
    unknown = run("atomize", "--key", "pp-ZZZZ", cwd=q)
    assert unknown.exit_code == 1 and "not a key of this quilt" in unknown.output, unknown.output

    main.write_text(
        main.read_text().replace("\\end{document}", "\\begin{lemma}\nNo id.\n\\end{lemma}\n\\end{document}")
    )
    unlabelled = next(k for k, n in scan(load_quilt(q)).assembly.nodes.items() if n.kind == "environment" and not n.id)
    r = run("atomize", "--key", unlabelled, cwd=q)
    assert r.exit_code == 1 and "loom:atomize-unlabelled" in r.output and "loom id --next" in r.output


def test_atomize_key_moves_an_attached_proof_with_its_statement(tmp_path: Path) -> None:
    q = _quilt_from_paper(tmp_path)
    main = q / "drafting" / "main.tex"
    result = scan(load_quilt(q))
    key = next(k for k, n in result.assembly.nodes.items() if n.kind == "environment" and n.file == "drafting/main.tex")
    node = result.assembly.nodes[key]
    text = main.read_text()
    main.write_text(text[: node.end] + "\n\\begin{proof}\nBy inspection.\n\\end{proof}" + text[node.end :])
    proof_key = next(k for k, n in scan(load_quilt(q)).assembly.nodes.items() if n.kind == "proof")

    r = run("atomize", "--key", proof_key, cwd=q)
    assert r.exit_code == 0, r.output
    moved = (q / "nodes" / f"{key}.tex").read_text()
    assert "\\begin{proof}" in moved and "\\begin{definition}" in moved, "the statement carries its proof"
