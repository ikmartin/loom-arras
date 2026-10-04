"""Diagnostic codes on the demo (book 5.14): lint's exit code, one test per warning, and the codes `check` and `atomize` report."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from tests.helpers import edit, exits, json_of, ok, refused, the
from tests.unit._quilts import demo


def test_lint_exit_codes(tmp_path: Path) -> None:
    q = demo(tmp_path)
    (q / "nodes" / "bad.tex").write_text("\\begin{lemma}\\label{dm-0001}\ndup\n\\end{lemma}\n")
    r = exits(1, "lint", cwd=q)
    assert "duplicate-id" in r.output and r.output.splitlines()[0].startswith("1 error")


def _stray_documentclass(q: Path) -> None:
    (q / "sections").mkdir()
    (q / "sections" / "stray.tex").write_text("\\documentclass{article}\n\\begin{document}\nx\n\\end{document}\n")


def _unreadable_log_line(q: Path) -> None:
    with (q / "annotations" / "log.jsonl").open("a", encoding="utf-8") as fh:
        fh.write("{not json\n")


def _missing_main(q: Path) -> None:
    edit(q / "config.toml", 'main = "drafting/main.tex"', 'main = "drafting/missing.tex"')


def _unknown_table(q: Path) -> None:
    with (q / "config.toml").open("a", encoding="utf-8") as fh:
        fh.write("\n[colour]\nscheme = 1\n")


def _mac_roman_node(q: Path) -> None:
    (q / "nodes" / "old.tex").write_bytes(b"\\begin{remark}\\label{dm-0099}\nSee pages 989\xd01004.\n\\end{remark}\n")


#: code -> (what provokes it on the demo, what its line must name)
WARNINGS: dict[str, tuple[Callable[[Path], None], str]] = {
    "loom:documentclass-outside-drafts": (_stray_documentclass, "sections/stray.tex"),
    "loom:foreign-annotations": (_unreadable_log_line, "annotations/log.jsonl"),
    "loom:main-not-found": (_missing_main, "drafting/missing.tex"),
    "loom:unknown-config-key": (_unknown_table, "[colour]"),
    "loom:non-utf8-source": (_mac_roman_node, "nodes/old.tex"),
}


@pytest.mark.parametrize("code", sorted(WARNINGS))
def test_a_warning_is_reported_on_one_line_naming_where(tmp_path: Path, code: str) -> None:
    q = demo(tmp_path)
    provoke, where = WARNINGS[code]
    provoke(q)
    lint = ok("lint", cwd=q).output.splitlines()  # warnings and infos only: lint exits 0
    heading = the(lint, lambda ln: code in ln.split(), f"{code} group")
    assert heading.endswith("(1)"), heading  # one diagnostic, on the one line under its heading
    line = lint[lint.index(heading) + 1]
    assert where in line, line


def test_check_reports_a_closure_that_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    q = demo(tmp_path)
    monkeypatch.setenv("FAKE_TEX_FAIL_MATCH", "closures/")  # the master compiles; every closure fails
    r = exits(1, "check", "--closures", "all", cwd=q)
    # the verdict leads stdout; a run slow enough to show progress puts it on stderr, never before the verdict
    assert r.stdout.startswith("check failed:")
    assert "loom:closure-failed" in r.stdout and "compiles  drafting/main.tex" in r.stdout


def test_atomize_refuses_a_target_file_that_exists(tmp_path: Path) -> None:
    q = demo(tmp_path)
    (q / "nodes" / "dm-0004.tex").write_text("% a file already sits where the inline node dm-0004 would move\n")
    refused(
        "atomize", "drafting/main.tex", "--to", "drafting/spine.tex", cwd=q, code=1, match="loom:atomize-target-exists"
    )


# Lint by citation (plan 0.18.5b §3): a digest's diagnostic is the author's when their text reaches the result it is on, a cited work's when the bibliography's work is cited, and otherwise a work nothing cites, which counts toward nothing.

_DANGLING = "\\ref{nowhere-at-all}"


def _uncited_digest(q: Path) -> None:
    """A digest of `Har77`, which the demo's bibliography holds and nothing cites, with one dangling reference (an error)."""
    (q / "digests" / "Har77.tex").write_text(
        "% !LOOM digest: Har77\n% !LOOM prefix: Har77\n\n"
        "\\begin{theorem}[{\\cite[Theorem 1.1]{Har77}}]\\label{Har77-thm-1.1}\n"
        f"Every scheme is a scheme, as in {_DANGLING}.\n\\end{{theorem}}\n",
        encoding="utf-8",
    )


def _dangle_in(q: Path, label: str) -> None:
    """A dangling reference inside the Calloway14 result labelled `label`."""
    path = q / "digests" / "Calloway14.tex"
    text = path.read_text(encoding="utf-8")
    start = text.index(f"\\label{{{label}}}")
    end = text.index("\\end{", start)
    path.write_text(text[:end] + f"See {_DANGLING}.\n" + text[end:], encoding="utf-8")


def test_an_uncited_digest_counts_toward_nothing_and_library_check_lists_it(tmp_path: Path) -> None:
    q = demo(tmp_path)
    before = ok("lint", cwd=q).output.splitlines()[0]
    _uncited_digest(q)
    r = ok("lint", cwd=q)  # its error is no error of the author's
    assert r.output.splitlines()[0] == before
    line = the(r.output.splitlines(), lambda ln: "in works nothing cites" in ln, "the uncited line")
    assert line.endswith("in works nothing cites; loom library check lists them"), line
    assert "dangling-link" not in r.output and "Har77" not in r.output  # nor its missing copy and identifier
    data = json_of("lint", "--json", cwd=q)
    group = the(data["groups"], lambda g: "works nothing cites" in g["heading"], "the uncited group")
    assert "dangling-link" in [i["diagnostic"]["code"] for i in group["items"]]
    assert group["count"] == len(group["items"]) == int(line.split()[0])
    from loom.refs.proposals import record_extracted
    from loom.scan.quilt import load_quilt
    from loom.scan.scan import scan

    record_extracted(scan(load_quilt(q)), "Har77")  # so the work's only finding is lint's
    out = ok("library", "check", "Har77", cwd=q).output.splitlines()  # listed, and not a failure
    assert out[0].endswith("; 1 work nothing cites with lint diagnostics"), out[0]
    heading = the(out, lambda ln: ln.startswith("works nothing cites that lint finds wrong"), "check's group")
    assert out[out.index(heading) + 1].strip().startswith("lint finds 1 error, ")
    assert out[out.index(heading) + 1].strip().endswith("Har77")


def test_a_cited_digest_keeps_the_cited_works_heading(tmp_path: Path) -> None:
    q = demo(tmp_path)
    _dangle_in(q, "Calloway14-prop-3.3")  # no postnote names Proposition 3.3
    r = exits(1, "lint", cwd=q)
    assert "1 error in cited works" in r.output.splitlines()[0]
    assert "in cited works (1)" in r.output.splitlines()
    assert "works nothing cites" not in r.output


def test_a_diagnostic_on_a_result_the_author_reaches_is_the_authors(tmp_path: Path) -> None:
    q = demo(tmp_path)
    _dangle_in(q, "Calloway14-prop-3.2")  # dm-0003 cites [Proposition 3.2]{Calloway14}
    r = exits(1, "lint", cwd=q)
    assert r.output.splitlines()[0].startswith("1 error, ")  # the demo's own warning and infos follow it
    assert "error dangling-link (1)" in r.output.splitlines()
    assert "in cited works" not in r.output
