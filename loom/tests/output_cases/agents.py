"""Output cases for the agents commands -- `session`, `ai`, `agent check`, `digest` and `sync`; see `tests/output_cases/__init__.py`."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

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
    "session send": "report",
    "session say": "report",
    "session next": "raw",
    "session watch": "running",
    "agent check": "report",
    "ai discard": "report",
    "ai init": "report",
    "ai orient": "raw",
    "ai drafts": "report",
    "ai start": "report",
    "ai name": "report",
    "ai annotations": "report",
    "ai check": "report",
    "ai refresh": "report",
    "digest extract": "report",
    "digest import": "report",
    "sync init": "report",
    "sync fetch": "report",
    "sync status": "report",
    "sync documents": "report",
    "sync patch": "raw",
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
    """A quilt without the AI layer, which `ai init` writes and `ai start` needs."""
    shutil.rmtree(q / "ai")


def fresh_session(q: Path) -> None:
    """A session opened after every file in the quilt was written, so nothing has changed outside it."""
    from loom.sessions import create

    create(q, "probe sitting", "tester")


def launching(q: Path) -> None:
    """Launching on, with no agent configured: what `loom serve` cannot honour."""
    with (q / "config.toml").open("a", encoding="utf-8") as fh:
        fh.write("\n[ai]\nlaunch = true\n")


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
    "session new": [Case(("probe sitting",)), Case(("probe sitting", "--no-use"))],
    "session use": [Case((S1,)), Case(("no-such-session",), exit=2, why="names no session")],
    "session list": [Case(()), Case(("--all",))],
    "session rename": [Case((S1, "A new title")), Case(("no-such-session", "x"), exit=2, why="names no session")],
    "session close": [Case(()), Case((S1,)), Case(("no-such-session",), exit=2, why="names no session")],
    "session delete": [
        Case((S1,)),
        Case((S1, "--purge", "--yes", "--author", "A. Author")),
        Case((S1, "--purge", "--author", "A. Author"), exit=2, why="--purge with nobody to ask and no --yes"),
        Case(("no-such-session",), exit=2, why="names no session"),
    ],
    "session send": [
        Case(("Have a look.", "--as", "A. Author")),
        Case(("--as", "Somebody Else"), exit=2, why="no words and nothing marked"),
        Case(("hello", *NOWHERE, "--as", "A. Author"), exit=2, why="names no session"),
    ],
    "session say": [
        Case(("Read it; one objection.", *AGENT)),
        Case(("hello", "--as", "A. Author"), exit=2, why="say is the agent's"),
    ],
    "session next": [
        Case(("--wait", "0", *AGENT)),
        Case(("--wait", "0", *NOWHERE, *AGENT), exit=2, why="names no session"),
    ],
    "agent check": [
        Case(()),
        Case((), setup=launching, exit=2, why="launching on with no agent configured"),
    ],
    "ai discard": [
        Case((S1,)),
        Case(
            (
                "--before",
                "2000-01-01",
            )
        ),
        Case((), exit=2, why="names nothing to discard"),
    ],
    "ai init": [
        Case((), setup=no_ai),
        Case(("--skills",), setup=no_ai),
        Case((), exit=2, why="ai/ exists"),
    ],
    "ai orient": [Case(()), Case(NOWHERE, exit=2, why="names no session")],
    "ai drafts": [Case(()), Case((), setup=ai_copy)],
    "ai start": [Case(("Probe sitting",)), Case(("Probe sitting",), setup=no_ai, exit=2, why="no ai/")],
    "ai name": [Case(("A new title", "--session", S1)), Case(("x", *NOWHERE), exit=2, why="names no session")],
    "ai annotations": [Case(("--session", S2)), Case(NOWHERE, exit=2, why="names no session")],
    "ai check": [
        Case(("probe sitting",), setup=fresh_session),
        Case((S1,), exit=1, why="files changed after the session opened"),
        Case(("no-such-session",), exit=2, why="names no session"),
    ],
    "ai refresh": [
        Case(("contribution.tex",), setup=ai_copy),
        Case(("no-such-copy.tex",), exit=2, why="names no agent copy"),
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
        Case(("../nowhere.git",), exit=2, why="no workspace there to clone"),
    ],
    "sync fetch": [Case((), setup=paired), Case((), exit=2, why="not paired")],
    "sync status": [Case((), setup=paired), Case((), setup=incoming), Case((), exit=2, why="not paired")],
    "sync documents": [
        Case((), setup=paired),
        Case(("add",), setup=paired, exit=2, why="add names no document"),
        Case((), exit=2, why="not paired"),
    ],
    "sync patch": [
        Case((), setup=incoming),
        Case(("--to", "pull.patch"), setup=patch_file, exit=2, why="the file exists"),
        Case((), exit=2, why="not paired"),
    ],
    "sync incorporate": [
        Case((), setup=incoming),
        Case((), setup=paired, exit=2, why="nothing incoming to incorporate"),
    ],
    "sync publish": [Case((), setup=paired), Case((), exit=2, why="not paired")],
}
