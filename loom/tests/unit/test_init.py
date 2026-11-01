"""`loom init`: the layout, the refusals, the ignore file and README, the author and AI questions, `--from` a paper, and what `--demo` writes."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.helpers import json_of, ok, refused, said
from tests.unit._quilts import demo


def test_init_writes_a_config_a_readme_and_loom_s_directory_and_nothing_else(tmp_path: Path) -> None:
    """A quilt comes nearly empty: the person lays it out, and everything loom writes later goes under `.loom/`."""
    ok("init", str(tmp_path / "q"), "--prefix", "zz", "--ai", "none", "--yes")
    q = tmp_path / "q"
    assert sorted(p.name for p in q.iterdir()) == [".loom", "README.md", "config.toml"]
    assert sorted(p.relative_to(q).as_posix() for p in (q / ".loom").rglob("*")) == [
        ".loom/.gitignore",
        ".loom/history",
        ".loom/history/ledger.jsonl",
    ]
    config = (q / "config.toml").read_text()
    assert 'prefix = "zz"' in config and "drafting" not in config and "\nmain =" not in config
    ok("lint", cwd=q)


def test_init_refuses_in_quilt_and_nonempty(tmp_path: Path) -> None:
    ok("init", str(tmp_path / "q"), "--prefix", "a", "--yes")
    refused("init", str(tmp_path / "q" / "inner"), "--yes", code=2, match="is already inside a quilt")
    (tmp_path / "full").mkdir()
    (tmp_path / "full" / "x.txt").write_text("x")
    refused("init", str(tmp_path / "full"), "--yes", code=2, match="is not empty")


def test_a_nonempty_directory_says_what_is_actually_wrong(tmp_path: Path) -> None:
    """The two refusals are different and the advice differs. Told to pass `--from` when one was already passed, a reader looks for the mistake everywhere but where it is."""
    full = tmp_path / "full"
    full.mkdir()
    (full / "x.txt").write_text("x")
    outside = tmp_path / "paper.tex"
    outside.write_text("\\documentclass{article}\n\\begin{document}\\end{document}\n")

    # no paper at all: passing one is the advice
    plain = refused("init", str(full), "--yes", code=2, match="is not empty")
    assert said("--from FILE with a file inside it", plain.output)

    # a paper outside the directory: where it sits is the fault, and the message names it
    apart = refused("init", str(full), "--from", str(outside), "--yes", code=2, match="lies outside it")
    assert str(outside) in apart.output

    # and the current directory is named as such, since the path was never typed
    refused("init", "--yes", cwd=full, code=2, match="the current directory")


def test_init_writes_loom_s_ignore_file_always_and_a_repository_only_when_asked(tmp_path: Path) -> None:
    """A quilt is files, and loom reads no history: it makes a repository only when `--git` asks for one, and says so when it does. Loom's ignore file is written either way, since it costs nothing and is right the day the quilt becomes a repository; the root `.gitignore` is the person's, and gets only the agent client files' lines, when the agent layer writes them."""
    ok("init", str(tmp_path / "n"), "--prefix", "a", "--ai", "none", "--yes")
    assert not (tmp_path / "n" / ".git").exists() and not (tmp_path / "n" / ".gitignore").exists()

    asked = ok("init", str(tmp_path / "g"), "--prefix", "a", "--ai", "claude", "--yes", "--git")
    assert (tmp_path / "g" / ".git").is_dir()
    assert "git init" in asked.output  # never a silent side effect
    assert (tmp_path / "g" / ".gitignore").read_text().splitlines()[1:] == [
        ".mcp.json",
        ".codex/config.toml",
        ".gemini/settings.json",
        ".cursor/mcp.json",
    ]

    # nothing a node is made of is ignored: only what loom rebuilds, its runtime state and its copies of other people's documents
    ignored = [
        ln for ln in (tmp_path / "n" / ".loom" / ".gitignore").read_text().splitlines() if ln and not ln.startswith("#")
    ]
    assert "build/" in ignored and "serve.json" in ignored and "last-seen.json" in ignored
    # the artifacts are ignored and the page text is not: an anchor stays re-checkable by a coauthor with no PDF
    assert "digests/storage/**/paper.pdf" in ignored and "digests/storage/**/src/" in ignored
    assert not any(ln.endswith(".tex") or ln in ("digests/", "annotations/", "history/", "sessions/") for ln in ignored)


def test_the_starter_preamble_declares_candidate_taxa() -> None:
    """A document loom starts with no document to take a preamble from is usable for planning from the first minute: `conjecture` owes a proof and shows as a gap, `question` owes nothing (plan 0.2 §4)."""
    from loom.cli.quilt import ASSETS

    main = (ASSETS / "init" / "main.tex").read_text(encoding="utf-8")
    assert "\\newtheorem{conjecture}[theorem]{Conjecture}" in main
    assert "\\newtheorem{question}[theorem]{Question}" in main

    # a conjecture is plain, because it owes a proof; a question is a remark, because it owes nothing
    def style_of(name: str) -> str:
        return main[: main.index("{" + name + "}[theorem]")].rsplit("\\theoremstyle{", 1)[1].split("}")[0]

    assert style_of("conjecture") == "plain"
    assert style_of("question") == "remark"


def test_init_readme_teaches_loom_and_lays_out_nothing(tmp_path: Path) -> None:
    """The README init writes is a tutorial, safe to delete: what a document, a node and a cited paper are to loom, the loop of stamping a landmark and restoring from one with a worked example, and the contract page as its last section. It names no directory the person must use, and its ids carry this quilt's prefix."""
    ok("init", str(tmp_path / "q"), "--prefix", "ab", "--yes")
    text = (tmp_path / "q" / "README.md").read_text()
    assert "safe to delete" in text and "`.loom/`" in text and "loom library add FILE" in text
    assert '$ loom stamp paper/main.tex -m "referee revisions"' in text
    assert "$ loom history show referee-revisions --plain" in text
    assert "## The contract" in text
    assert "\\label{ab-0004}" in text  # the example id carries this quilt's prefix, not one to be copied blindly
    assert "drafting/" not in text and "drafting-ai/" not in text and "refs/" not in text and "q-0" not in text


def test_init_asks_only_which_ai_and_writes_no_author(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The reviewer comes from local Settings or git, never from the quilt: init writes no `[author]` table and has no `--author`, and with a terminal attached the one question is which AI. An agent or a script sees no question."""
    from loom.cli import quilt as quilt_cli

    refused(
        "init", str(tmp_path / "given"), "--prefix", "ab", "--author", "Markas Hecht", "--yes", code=2, match="--author"
    )
    assert not (tmp_path / "given").exists()

    # no terminal under the runner: nothing is asked
    ok("init", str(tmp_path / "quiet"), "--prefix", "ab")
    assert "[author]" not in (tmp_path / "quiet" / "config.toml").read_text()

    asked: list[str] = []

    def prompt(text: str, **kwargs: object) -> str:
        asked.append(text)
        return "4"

    monkeypatch.setattr(quilt_cli, "sys", SimpleNamespace(stdin=SimpleNamespace(isatty=lambda: True)))
    monkeypatch.setattr(quilt_cli.click, "prompt", prompt)
    ok("init", str(tmp_path / "asked"), "--prefix", "ab")
    assert asked == ["Enter 1, 2, 3 or 4"]
    assert "[author]" not in (tmp_path / "asked" / "config.toml").read_text()


def test_init_asks_which_ai_and_writes_the_agent_layer_for_any(tmp_path: Path) -> None:
    """Any AI gets the agent layer, Claude, Codex or another; none gets nothing. Loom starts no agent, so nothing names a command to start one (plan 0.20.1)."""
    r = ok("init", str(tmp_path / "c"), "--ai", "claude", cwd=tmp_path)
    c = tmp_path / "c"
    assert not (c / ".loom/ai" / "ai-config.toml").exists() and "[ai]" not in (c / "config.toml").read_text()
    perms = json.loads((c / ".claude" / "settings.json").read_text())["permissions"]
    assert "mcp__loom__*" in perms["allow"] and "Bash(loom *)" in perms["deny"]
    assert (c / ".mcp.json").is_file() and "approve the loom server" in r.output
    assert "AI: Claude (Claude Code). Run it in this quilt" in r.output and "launch" not in r.output
    o = ok("init", str(tmp_path / "o"), "--ai", "other", cwd=tmp_path)
    assert (tmp_path / "o" / ".loom/ai" / "orientation.md").is_file() and "AI: another agent" in o.output
    # no terminal, no flag: no AI, and no layer
    n = ok("init", str(tmp_path / "n"), cwd=tmp_path)
    assert "AI: none" in n.output
    assert not (tmp_path / "n" / ".claude").exists() and not (tmp_path / "n" / ".loom/ai").exists()


def test_init_from_leaves_the_authors_preamble_alone(tmp_path: Path) -> None:
    """`--from` keeps the paper as it is for its first landmark, verbatim, and drafts the working document from it: the package line and ids are added there, and nothing else is added to the author's preamble."""
    src = tmp_path / "paper.tex"
    src.write_text(
        "\\documentclass{article}\n\\newtheorem{thm}{Theorem}\n\\begin{document}\nHello.\n\\end{document}\n",
        encoding="utf-8",
    )
    r = ok("init", str(tmp_path / "q"), "--from", str(src), "--yes")
    q = tmp_path / "q"
    landmark = q / ".loom" / "history" / "0001-paper" / "paper.tex"
    assert landmark.read_text() == src.read_text()  # verbatim: the paper has nothing to inline
    drafted = (q / "paper" / "paper.tex").read_text()  # a directory of its own, named for the paper
    assert "% !LOOM begin loom-macros" in drafted and "conjecture" not in drafted
    assert "the paper as received is landmark paper" in r.output


def test_init_from_leaves_nothing_behind_when_the_import_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed import is not half a quilt. The instinct after a refusal is to fix the paper and re-run the same command, and a surviving skeleton refuses that as "already inside a quilt"."""
    src = tmp_path / "paper.tex"
    src.write_text(
        "\\documentclass{article}\n\\newtheorem{thm}{Theorem}\n\\begin{document}\nHello.\n\\end{document}\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("FAKE_TEX_FAIL", "1")
    bad = refused(
        "init",
        str(tmp_path / "q"),
        "--from",
        str(src),
        "--prefix",
        "pp",
        "--yes",
        code=1,
        match="does not compile from a clean copy",
    )
    assert not (tmp_path / "q").exists()
    assert "created quilt" not in bad.output  # nothing is announced that does not outlive the command

    monkeypatch.delenv("FAKE_TEX_FAIL")
    again = ok("init", str(tmp_path / "q"), "--from", str(src), "--prefix", "pp", "--yes")
    assert (tmp_path / "q" / "paper" / "paper.tex").is_file() and "created quilt" in again.output


def test_init_from_inside_a_paper_directory_keeps_the_paper_when_the_import_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Undoing the skeleton removes what init wrote and nothing else: the author's own directory is not init's to delete."""
    paper = tmp_path / "paper"
    paper.mkdir()
    (paper / "main.tex").write_text(
        "\\documentclass{article}\n\\newtheorem{thm}{Theorem}\n\\begin{document}\nHello.\n\\end{document}\n",
        encoding="utf-8",
    )
    (paper / "notes.txt").write_text("mine\n", encoding="utf-8")

    monkeypatch.setenv("FAKE_TEX_FAIL", "1")
    refused(
        "init",
        str(paper),
        "--from",
        str(paper / "main.tex"),
        "--prefix",
        "pp",
        "--yes",
        code=1,
        match="does not compile",
    )
    assert sorted(x.name for x in paper.iterdir()) == ["main.tex", "notes.txt"]


def test_demo_has_outline_master(tmp_path: Path) -> None:
    """The demo shows the outline pattern: a second master reaching one conjecture and one question, so a candidate is reached rather than loose while it is being considered (plan 0.2 §1.2)."""
    q = demo(tmp_path)
    assert (q / "drafting" / "outline.tex").exists()
    keys = json_of("status", "--master", "drafting/outline.tex", "--json", cwd=q)["keys"]
    reached = {k for k, v in keys.items() if "drafting/outline.tex" in v["reached_by"]}
    assert {"dm-0006", "dm-0007"} <= reached  # the candidates are reached, not loose, while they are being considered
    taxa = {n["key"]: n.get("taxon") for n in json_of("search", "dm-000", "--json", cwd=q)["matches"]}
    assert taxa.get("dm-0006") == "Conjecture" and taxa.get("dm-0007") == "Question"
    # the conjecture owes a proof and is a gap until it is proved or refuted; the question owes nothing
    assert keys["dm-0006/proof"]["state"] == "incomplete"
    assert "dm-0007/proof" not in keys


def test_upgrade_rewrites_loom_s_ignore_lines_and_keeps_the_person_s(tmp_path: Path) -> None:
    """One list each (`loom.gitignore`): `upgrade` rewrites `.loom/.gitignore` above its own-lines marker and keeps what the person wrote below it, and gives the root `.gitignore` the client lines it lacks, touching nothing else there."""
    from loom.gitignore import CLIENT_LINES, LOOM_IGNORE, OWN, missing

    ok("init", tmp_path / "q", "--prefix", "zz", "--ai", "claude", "--yes")
    q = tmp_path / "q"
    assert missing(q) == [] and (q / ".loom" / ".gitignore").read_text() == LOOM_IGNORE
    (q / ".loom" / ".gitignore").write_text(f"build/\n{OWN}\n!digests/storage/**/paper.pdf\n")
    (q / ".gitignore").write_text("# mine\nscratch/\n")
    said = ok("upgrade", cwd=q).output
    assert ".loom/.gitignore" in said
    assert (q / ".loom" / ".gitignore").read_text() == LOOM_IGNORE + "!digests/storage/**/paper.pdf\n"
    lines = (q / ".gitignore").read_text().splitlines()
    assert lines[:2] == ["# mine", "scratch/"] and missing(q) == [] and all(line in lines for line in CLIENT_LINES)


def test_init_inside_a_quilt_names_import(tmp_path: Path) -> None:
    """T3: "is already inside a quilt" named no `loom import`, which is what brings a paper into one."""
    ok("init", str(tmp_path / "q"), "--prefix", "a", "--yes")
    refused(
        "init",
        str(tmp_path / "q" / "inner"),
        "--prefix",
        "a",
        "--yes",
        code=2,
        match="loom import FILE brings a paper into it",
    )
