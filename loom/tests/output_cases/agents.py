"""Output cases for the agents commands -- `session`, `ai`, `doctor --agents`, `digest` and `sync`; see `tests/output_cases/__init__.py`."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from tests.output_cases import core
from tests.output_cases.base import Case, ai_copy, author

S1, S2 = "s-2026-09-16-0001", "s-2026-09-16-0002"
AGENT = ("--as", "Probe Agent")

KIND: dict[str, str] = {
    "session new": "report",
    "session use": "report",
    "session list": "report",
    "session rename": "report",
    "session close": "report",
    "session delete": "report",
    "session say": "report",
    "session next": "raw",
    "session watch": "running",
    "ai discard": "report",
    "ai init": "report",
    "ai orient": "raw",
    "ai drafts": "report",
    "ai annotations": "report",
    "ai refresh": "report",
    "digest extract": "report",
    "digest import": "report",
    "sync init": "report",
    "sync fetch": "report",
    "sync status": "report",
    "sync documents": "report",
    "sync incorporate": "report",
    "sync publish": "report",
}


REF = (
    "\\documentclass{article}\n\\newtheorem{thm}{Theorem}[section]\n\\begin{document}\n\\section{Introduction}\n"
    "We study widgets.\n\\section{Results}\n\\begin{thm}\\label{main}\nWidgets are gadgets.\n\\end{thm}\n\\end{document}\n"
)


def filed_source(q: Path) -> None:
    """A cited work, Ref20, whose source loom holds, which is what `digest extract` reads."""
    from tests.helpers import ok

    with (q / "digests" / "bibliography.bib").open("a", encoding="utf-8") as fh:
        fh.write("\n@misc{Ref20, title={Widgets}, author={Ref, A.}, year={2020}}\n")
    paper = q.parent / "paper" / "ref.tex"
    paper.parent.mkdir()
    paper.write_text(REF, encoding="utf-8")
    ok("refs", "add", "Ref20", str(paper), cwd=q)


def no_ai(q: Path) -> None:
    """A quilt without the agent layer, which `ai init` writes."""
    shutil.rmtree(q / "ai")


def marked(q: Path) -> None:
    """A person's annotation in the session, not yet carried by a message: what `session say` with no words carries."""
    from tests.helpers import ok

    author(q)
    ok("annotate", "dm-0003", "Is this right?", "--kind", "question", "--session", S1, cwd=q)


def launching(q: Path) -> None:
    """Launching on, with no agent configured: what `loom serve` cannot honour."""
    with (q / "config.toml").open("a", encoding="utf-8") as fh:
        fh.write("\n[ai]\nlaunch = true\n")


def configured(q: Path) -> None:
    """Claude configured as the agent, with the author named, so `doctor --agents` prints its commands and prompt."""
    from loom.agent import CONFIG, config_text

    author(q)
    (q / CONFIG).write_text(config_text("claude"), encoding="utf-8")


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def workspace(q: Path) -> None:
    """A bare repository beside the quilt standing in for an Overleaf project, at `../overleaf.git`."""
    bare, seed = q.parent / "overleaf.git", q.parent / "seed"
    _git(q.parent, "init", "-q", "--bare", "-b", "master", str(bare))
    _git(q.parent, "clone", "-q", str(bare), str(seed))
    _git(seed, "config", "user.name", "Overleaf")
    _git(seed, "config", "user.email", "overleaf@example.org")
    (seed / "main.tex").write_text("\\documentclass{article}\n\\begin{document}\n\\end{document}\n", encoding="utf-8")
    _git(seed, "add", ".")
    _git(seed, "commit", "-q", "-m", "new project")
    _git(seed, "push", "-q", "origin", "HEAD:master")


def paired(q: Path) -> None:
    """The quilt paired with that workspace, its main published there as `main.tex`, with an author to stamp as."""
    from loom.scan.quilt import load_quilt
    from loom.sync import configure

    author(q)
    workspace(q)
    configure(load_quilt(q), "../overleaf.git", "main.tex")


def incoming(q: Path) -> None:
    """Paired and published, then a collaborator's edit to the main document fetched and waiting for review."""
    import loom.sync as sync
    from loom.scan.quilt import load_quilt

    paired(q)
    quilt = load_quilt(q)
    state = sync.SyncState.read(q)
    with mock.patch.object(sync, "compile_tex", lambda *_a, **_k: SimpleNamespace(ok=True)):
        publication = sync.publish(quilt, state)
    sync.push_publication(quilt, state, publication.commit)
    clone = q.parent / "collaborator"
    _git(q.parent, "clone", "-q", str(q.parent / "overleaf.git"), str(clone))
    _git(clone, "config", "user.name", "Colleague")
    _git(clone, "config", "user.email", "colleague@example.org")
    main = clone / "main.tex"
    main.write_text(
        main.read_text(encoding="utf-8").replace("\\end{document}", "A colleague's sentence.\n\\end{document}")
    )
    _git(clone, "commit", "-q", "-am", "a colleague's edit")
    _git(clone, "push", "-q", "origin", "HEAD:master")
    sync.fetch(quilt, sync.SyncState.read(q))


def patch_file(q: Path) -> None:
    incoming(q)
    (q / "pull.patch").write_text("already here\n", encoding="utf-8")


NOWHERE = ("--session", "no-such-session")

CASES: dict[str, list[Case]] = {
    "session new": [
        Case(("--name", "probe sitting")),
        Case(("--name", "probe sitting", "--no-use")),
        Case(("--name", "probe sitting", "--dry-run"), unchanged=True),
    ],
    "session use": [
        Case((S1,)),
        Case((S1, "--dry-run"), unchanged=True),
        Case(("no-such-session",), exit=2, why="names no session", unchanged=True),
    ],
    "session list": [Case(()), Case(("--all",))],
    "session rename": [
        Case((S1, "--name", "A new title")),
        Case((S1, "--name", "A new title", "--dry-run"), unchanged=True),
        Case(("no-such-session", "--name", "x"), exit=2, why="names no session", unchanged=True),
    ],
    "session close": [
        Case(()),
        Case((S1,)),
        Case((S1, "--dry-run"), unchanged=True),
        Case(("no-such-session",), exit=2, why="names no session", unchanged=True),
    ],
    "session delete": [
        Case((S1,)),
        Case((S1, "--dry-run"), unchanged=True),
        Case((S1, "--purge", "--yes", "--as", "A. Author")),
        Case((S1, "--purge", "--dry-run", "--as", "A. Author"), unchanged=True),
        Case(
            (S1, "--purge", "--as", "A. Author"),
            exit=2,
            why="--purge with nobody to ask and no --yes",
            unchanged=True,
        ),
        Case(("no-such-session",), exit=2, why="names no session", unchanged=True),
    ],
    "session say": [
        Case(("Read it; one objection.", *AGENT)),
        Case(("Have a look.", "--as", "A. Author")),
        Case(("--session", S1, "--as", "Tester"), setup=marked),
        Case(("Have a look.", "--as", "A. Author", "--dry-run"), unchanged=True),
        Case(("--as", "Somebody Else"), exit=2, why="no words and nothing marked", unchanged=True),
        Case(("hello", *NOWHERE, "--as", "A. Author"), exit=2, why="names no session", unchanged=True),
    ],
    "session next": [
        Case(("--wait", "0", *AGENT)),
        Case(("--wait", "0", *NOWHERE, *AGENT), exit=2, why="names no session", unchanged=True),
    ],
    "ai discard": [
        Case((S1,)),
        Case(("--before", "2000-01-01")),
        Case((S1, "--dry-run"), unchanged=True),
        Case(("--by", "Tester", "--dry-run"), unchanged=True),
        Case((), exit=2, why="names nothing to withdraw", unchanged=True),
        Case(("no-such-session",), exit=2, why="names no session", unchanged=True),
        Case(("--target", "dm-9999"), exit=2, why="names no key", unchanged=True),
    ],
    "ai init": [
        Case((), setup=no_ai),
        Case(("--skills", "--agent", "claude"), setup=no_ai),
        Case((), why="ai/ exists: refreshes it"),
        Case(("--dry-run",), setup=no_ai, unchanged=True),
        Case(("--dry-run", "--skills"), unchanged=True),
    ],
    "ai orient": [Case(()), Case(NOWHERE, exit=2, why="names no session")],
    "ai drafts": [Case(()), Case((), setup=ai_copy)],
    "ai annotations": [
        Case(("--session", S2)),
        Case(("--session", S2, "--kind", "objection", "--severity", "major", "--status", "open")),
        Case(NOWHERE, exit=2, why="names no session"),
    ],
    "ai refresh": [
        Case(("contribution.tex",), setup=ai_copy),
        Case(("contribution.tex", "--dry-run"), setup=ai_copy, unchanged=True),
        Case(("no-such-copy.tex",), exit=2, why="names no agent document", unchanged=True),
    ],
    # core.py holds doctor's own cases; these add the agent report `doctor --agents` prints, merged after them
    "doctor": [
        *core.CASES["doctor"],
        Case(("--agents",), setup=author),
        Case(("--agents",), setup=configured, why="an agent configured: its start, resume and prompt lines"),
        Case(("--agents",), setup=launching, exit=2, why="launching on with no agent configured: a fault and its fix"),
    ],
    "digest extract": [
        Case(("Ref20",), setup=filed_source),
        Case(("Ref20", "--no-compile", "--to", "elsewhere.tex"), setup=filed_source),
        Case(("Calloway14",), exit=2, why="loom holds no source for it"),
    ],
    "digest import": [
        Case(("digests/Calloway14.tex", "--as", "Other14")),
        Case(("digests/Calloway14.tex",), exit=2, why="the digest exists; import never overwrites"),
    ],
    "sync init": [
        Case(("../overleaf.git", "--publish-main", "main.tex"), setup=workspace),
        Case(("../overleaf.git", "--dry-run"), setup=workspace, unchanged=True),
        Case(("../nowhere.git",), exit=2, why="no workspace there to clone", unchanged=True),
        Case(("../nowhere.git", "--dry-run"), exit=2, why="no workspace there to ask", unchanged=True),
    ],
    "sync fetch": [Case((), setup=paired), Case((), exit=2, why="not paired")],
    "sync status": [
        Case((), setup=paired),
        Case((), setup=incoming),
        Case(("--patch",), setup=incoming),
        Case(("--patch",), setup=paired, why="nothing incoming"),
        Case(("--patch", "--to", "build/pull.patch"), setup=incoming),
        Case(("--patch", "--to", "pull.patch"), setup=patch_file, exit=2, why="the file exists", unchanged=True),
        Case(("--to", "pull.patch"), setup=incoming, exit=2, why="--to without --patch", unchanged=True),
        Case((), exit=2, why="not paired"),
    ],
    "sync documents": [
        Case((), setup=paired),
        Case(("add", "drafting/outline.tex", "--dry-run"), setup=paired, unchanged=True),
        Case(("add",), setup=paired, exit=2, why="add names no document", unchanged=True),
        Case(("add", "drafting/nowhere.tex"), setup=paired, exit=2, why="names no document", unchanged=True),
        Case((), exit=2, why="not paired"),
    ],
    "sync incorporate": [
        Case((), setup=incoming),
        Case(("--dry-run",), setup=incoming, unchanged=True),
        Case((), setup=paired, exit=2, why="nothing incoming to incorporate", unchanged=True),
    ],
    "sync publish": [
        Case((), setup=paired),
        Case(("--dry-run",), setup=paired, unchanged=True),
        Case((), exit=2, why="not paired", unchanged=True),
    ],
}
