"""`loom init` (book 4.2, 4.7): the layout, the refusals, the ignore file and README, the author and AI questions, `--from` a paper, and what `--demo` writes."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.helpers import json_of, ok, refused
from tests.unit._quilts import demo


def test_init_creates_layout(tmp_path: Path) -> None:
    ok("init", str(tmp_path / "q"), "--prefix", "zz", "--yes")
    q = tmp_path / "q"
    for rel in (
        "config.toml",
        "loom.sty",
        "drafting/main.tex",
        "nodes",
        "digests",
        "refs",
        ".gitignore",
        "README.md",
    ):
        assert (q / rel).exists(), rel
    assert not (q / "comments").exists()  # annotations live in annotations/log.jsonl; there is no comments/
    assert 'prefix = "zz"' in (q / "config.toml").read_text()
    assert "\\usepackage{loom}" in (q / "drafting/main.tex").read_text()
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
    assert "--from FILE with a file inside it" in plain.output

    # a paper outside the directory: where it sits is the fault, and the message names it
    apart = refused("init", str(full), "--from", str(outside), "--yes", code=2, match="lies outside it")
    assert str(outside) in apart.output

    # and the current directory is named as such, since the path was never typed
    refused("init", "--yes", cwd=full, code=2, match="the current directory")


def test_init_writes_gitignore_always_and_a_repository_only_when_asked(tmp_path: Path) -> None:
    """A quilt is files, and loom reads no history: it makes a repository only when `--git` asks for one, and says so when it does. The ignore file is written either way, since it costs nothing and is right the day the quilt becomes a repository."""
    plain = ok("init", str(tmp_path / "n"), "--prefix", "a", "--yes")
    assert not (tmp_path / "n" / ".git").exists()
    assert (tmp_path / "n" / ".gitignore").is_file()
    assert "wrote .gitignore" in plain.output and "build/" in plain.output

    asked = ok("init", str(tmp_path / "g"), "--prefix", "a", "--yes", "--git")
    assert (tmp_path / "g" / ".git").is_dir()
    assert "git init" in asked.output  # never a silent side effect

    # nothing a node is made of is ignored: only derived directories and LaTeX's own leavings
    ignored = [ln for ln in (tmp_path / "n" / ".gitignore").read_text().splitlines() if ln and not ln.startswith("#")]
    assert "build/" in ignored
    # the artifacts are ignored and the page text is not: an anchor stays re-checkable by a coauthor with no PDF
    assert "digests/storage/**/paper.pdf" in ignored and "digests/storage/**/src/" in ignored
    assert "refs/" in ignored  # the seed space is the author's pile of other people's PDFs
    assert not any(ln.endswith(".tex") or ln in ("nodes/", "drafting/", "digests/", "comments/") for ln in ignored)


def test_init_minimal_master_declares_candidate_taxa(tmp_path: Path) -> None:
    """A quilt is usable for planning from the first minute: `conjecture` owes a proof and shows as a gap, `question` owes nothing (plan 0.2 §4)."""
    ok("init", str(tmp_path / "q"), "--yes")
    main = (tmp_path / "q" / "drafting" / "main.tex").read_text()
    assert "\\newtheorem{conjecture}[theorem]{Conjecture}" in main
    assert "\\newtheorem{question}[theorem]{Question}" in main

    # a conjecture is plain, because it owes a proof; a question is a remark, because it owes nothing
    def style_of(name: str) -> str:
        return main[: main.index("{" + name + "}[theorem]")].rsplit("\\theoremstyle{", 1)[1].split("}")[0]

    assert style_of("conjecture") == "plain"
    assert style_of("question") == "remark"


def test_init_readme_orients_the_author_in_this_quilts_own_names(tmp_path: Path, home: Path) -> None:
    """The README init writes is an orientation for the author: what each directory holds, the promise that a canon file is only ever copied, the draft-canonize loop with a worked example, and the contract page as its last section. Its paths and ids are this quilt's own, so a quilt that renamed its directories reads its own names back and nothing in the example has to be translated."""
    cfg = home / ".config" / "loom"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "config.toml").write_text('[quilt]\ndrafting = "work"\ncanon = "fixed"\n', encoding="utf-8")
    ok("init", str(tmp_path / "q"), "--prefix", "ab", "--yes")
    text = (tmp_path / "q" / "README.md").read_text()

    for heading in ("**`work/`**", "**`fixed/`**", "**`nodes/`**", "**`refs/`**"):
        assert heading in text, heading
    assert "at the quilt root" in text and "Created empty" in text  # refs/ is the author's seed space, not canon/refs/
    assert "is never touched" in text and "only ever read and copied somewhere else" in text
    assert "$ loom draft fixed/paper.tex --to work/main.tex" in text
    assert '$ loom canonize work/main.tex --to fixed/paper-v2.tex -m "Referee revisions"' in text
    assert "## The contract" in text
    assert "\\label{ab-0004}" in text  # the example id carries this quilt's prefix, not one to be copied blindly
    assert "drafting/" not in text and "canon/" not in text and "q-0" not in text


def test_init_asks_for_an_author_name_and_writes_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`[author] name` comes from `--author`, or is asked for once when a terminal is attached and `--yes` is absent, or is written empty for the author to fill in (book 4.2, 4.3, 4.7). An agent or a script sees no question."""
    from loom.cli import quilt as quilt_cli

    ok("init", str(tmp_path / "given"), "--prefix", "ab", "--author", "Markas Hecht", "--yes")
    assert 'name = "Markas Hecht"' in (tmp_path / "given" / "config.toml").read_text()

    # no terminal under the runner: nothing is asked and the key waits, rather than naming the machine
    ok("init", str(tmp_path / "quiet"), "--prefix", "ab")
    assert 'name = ""' in (tmp_path / "quiet" / "config.toml").read_text()

    asked: list[str] = []

    def prompt(text: str, **kwargs: object) -> str:
        asked.append(text)
        return "  Markas Hecht  "

    monkeypatch.setattr(quilt_cli, "sys", SimpleNamespace(stdin=SimpleNamespace(isatty=lambda: True)))
    monkeypatch.setattr(quilt_cli.click, "prompt", prompt)
    ok("init", str(tmp_path / "asked"), "--prefix", "ab")
    # the author's name, then which AI they use, which is what decides what ai/ai-config.toml holds
    assert len(asked) == 2 and "Author name" in asked[0] and asked[1] == "Enter 1, 2, 3 or 4"
    assert 'name = "Markas Hecht"' in (tmp_path / "asked" / "config.toml").read_text()  # trimmed

    # the flag is an answer, an empty one included: a quilt told to have no name is not asked for one
    asked.clear()
    ok("init", str(tmp_path / "flagged"), "--prefix", "ab", "--author", "")
    assert (
        not any("Author name" in q for q in asked) and 'name = ""' in (tmp_path / "flagged" / "config.toml").read_text()
    )
    before = len(asked)
    assert quilt_cli.ask_author("", yes=True) == "" and len(asked) == before  # --yes never asks


def test_init_asks_which_ai_and_says_whether_it_will_be_started(tmp_path: Path) -> None:
    import tomllib

    r = ok("init", str(tmp_path / "c"), "--ai", "claude", "--launch-agents", "--author", "A. Author", cwd=tmp_path)
    c = tmp_path / "c"
    cfg = tomllib.loads((c / "ai" / "ai-config.toml").read_text())
    assert cfg["name"] == "Claude Agent" and cfg["start"][0] == "claude" and "{agent_session}" in cfg["resume"]
    assert tomllib.loads((c / "config.toml").read_text())["ai"]["launch"] is True
    perms = json.loads((c / ".claude" / "settings.json").read_text())["permissions"]
    assert "Bash(loom session say*)" in perms["allow"] and "Bash(loom accept*)" in perms["deny"]
    assert "ai/ai-config.toml" in (c / ".gitignore").read_text()
    assert "Agents will be launched by loom serve" in r.output
    # no terminal, no flag: no AI, and nothing will be started
    n = ok("init", str(tmp_path / "n"), "--author", "A. Author", cwd=tmp_path)
    assert "AI: none" in n.output and "Agents will not be launched" in n.output
    assert not (tmp_path / "n" / ".claude").exists()
    assert tomllib.loads((tmp_path / "n" / "ai" / "ai-config.toml").read_text()) == {}


def test_init_from_leaves_the_authors_preamble_alone(tmp_path: Path) -> None:
    """`--from` adopts a paper as it is: one flat canon document, no package line, no ids, nothing added to the author's preamble."""
    src = tmp_path / "paper.tex"
    src.write_text(
        "\\documentclass{article}\n\\newtheorem{thm}{Theorem}\n\\begin{document}\nHello.\n\\end{document}\n",
        encoding="utf-8",
    )
    r = ok("init", str(tmp_path / "q"), "--from", str(src), "--yes")
    q = tmp_path / "q"
    canon = q / "canon" / "paper.tex"
    assert canon.read_text() == src.read_text()  # verbatim: the paper has nothing to inline
    assert "conjecture" not in canon.read_text() and "usepackage{loom}" not in canon.read_text()
    assert not any((q / "drafting").iterdir())  # work begins with loom draft
    assert "next: loom draft canon/paper.tex" in r.output


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
    assert (tmp_path / "q" / "canon" / "paper.tex").is_file() and "created quilt" in again.output


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
    """The demo shows the outline pattern: a second master reaching one conjecture and one question, so a candidate is reached rather than loose while it is being considered (plan 0.2 §1.2, book 4.4)."""
    q = demo(tmp_path)
    assert (q / "drafting" / "outline.tex").exists()
    keys = json_of("status", "--master", "drafting/outline.tex", "--json", cwd=q)["keys"]
    reached = {k for k, v in keys.items() if "drafting/outline.tex" in v["reached_by"]}
    assert {"dm-0006", "dm-0007"} <= reached  # the candidates are reached, not loose, while they are being considered
    taxa = {n["key"]: n.get("taxon") for n in json_of("search", "dm-000", "--json", cwd=q)}
    assert taxa.get("dm-0006") == "Conjecture" and taxa.get("dm-0007") == "Question"
    # the conjecture owes a proof and is a gap until it is proved or refuted; the question owes nothing
    assert keys["dm-0006/proof"]["state"] == "incomplete"
    assert "dm-0007/proof" not in keys


def test_init_and_upgrade_keep_the_same_gitignore_lines(tmp_path: Path) -> None:
    """One list, `loom.gitignore.MANAGED`: the template `init` writes carries all of it, and `upgrade` gives an older quilt what it lacks and nothing else."""
    from loom.gitignore import MANAGED, missing

    ok("init", tmp_path / "q", "--prefix", "zz", "--yes")
    q = tmp_path / "q"
    assert missing(q) == []
    (q / ".gitignore").write_text("build/\n# mine\nnotes/\n")
    said = ok("upgrade", cwd=q).output
    assert ".loom/serve.json" in said
    lines = (q / ".gitignore").read_text().splitlines()
    assert lines[:3] == ["build/", "# mine", "notes/"] and missing(q) == []
    assert lines.count("build/") == 1 and all(line in lines for line in MANAGED)
