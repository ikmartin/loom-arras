"""Shared CLI plumbing: exit codes, JSON output, and the two error classes every command raises.

Exit codes follow the book's 12.1: 0 success, 1 a content problem the author can fix in the source, 2 a usage or environment problem.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

EXIT_OK = 0
EXIT_CONTENT = 1
EXIT_USAGE = 2


class ContentError(click.ClickException):
    """A problem in the quilt's content (lint errors, failed identity test, refused write). Exit 1."""

    exit_code = EXIT_CONTENT

    def format_message(self) -> str:
        return self.message


class EnvError(click.ClickException):
    """A usage or environment problem (bad arguments, missing tool, no author name). Exit 2."""

    exit_code = EXIT_USAGE

    def format_message(self) -> str:
        return self.message


class NotFoundError(EnvError):
    """An argument names something that does not exist: a node, an annotation, a session, a cited work, a result. Exit 2, like any argument that names nothing; the write API answers it 404 `no-such-<what>`."""

    def __init__(self, what: str, message: str) -> None:
        super().__init__(message)
        self.what = what


def emit_json(obj: Any) -> None:
    """Print one JSON document to stdout and nothing else there; diagnostics go to stderr."""
    click.echo(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False))


def note(message: str) -> None:
    """Progress or diagnostic text, always on stderr so --json stdout stays clean."""
    click.echo(message, err=True)


def find_session(root: Path, which: str | None, *, deleted: bool = False):  # type: ignore[no-untyped-def]
    """The session `which` names (`sessions.resolve`), or with nothing the active one; refused by name rather than guessed.

    A name that matches nothing is `NotFoundError`, one that matches several an `EnvError` naming them. Refusing rather than creating matters: a value that matched nothing used to be made as a directory at the quilt root, and that directory then satisfied every later lookup. Deleted sessions are found only with `deleted`, so nothing is written into a tombstone by accident.
    """
    from loom.sessions import SessionNotFound, active, resolve, sessions

    if not which:
        here = active(root)
        standing = sessions(root)
        if here and here in standing:
            return standing[here]
        raise EnvError('no session is active; loom session new --name "a name" opens one')
    try:
        return resolve(root, which, deleted=deleted)
    except SessionNotFound as exc:
        if exc.matches:
            raise EnvError(str(exc)) from None
        if not deleted:
            try:
                gone = resolve(root, which, deleted=True)
            except SessionNotFound:
                gone = None
            if gone is not None:
                raise ContentError(f"{gone.id} was deleted; nothing new can be written to it") from None
        raise NotFoundError("session", str(exc)) from None


#: What a file the scan reads ends in: a path loom writes with one of these, inside the quilt, would become source.
SOURCE_SUFFIXES = (".tex", ".sty", ".cls", ".bib")


def destination(
    quilt: Any, path: str | Path, *, drafting: bool = False, source: bool = False, overwrite: bool = False
) -> Path:
    """Where a command's `--to` writes, by the one rule every `--to` follows (book 12.1, K2).

    Parameters
    ----------
    quilt : Quilt
        The quilt the command runs against.
    path : str or Path
        What `--to` said; a relative path is the quilt root's, as every path loom takes is.
    drafting : bool, default False
        The command writes a working document, which belongs directly in the drafting directory (or, for an agent document, in `drafting-ai/`).
    source : bool, default False
        The command writes a source file that takes another's place (`atomize`), so it may go wherever a source may.
    overwrite : bool, default False
        The command replaces what is there by design; otherwise an existing file is refused.

    Returns
    -------
    Path
        The absolute path to write.

    Raises
    ------
    EnvError
        A working document outside the drafting directories; anything else among the quilt's sources or in a drafting directory, which loom never writes; or a file that exists.
    """
    root = Path(quilt.root).resolve()
    given = Path(path).expanduser()
    target = (given if given.is_absolute() else root / given).resolve()
    rel = target.relative_to(root).as_posix() if target.is_relative_to(root) else None
    homes = {quilt.config.drafting, getattr(quilt.config, "drafting_ai", "drafting-ai")}
    in_drafting = rel is not None and Path(rel).parent.as_posix() in homes
    if drafting and not in_drafting:
        raise EnvError(
            f"{path}: a working document goes directly in {quilt.config.drafting}/, e.g. --to {quilt.config.drafting}/{target.name}"
        )
    if (
        not drafting
        and not source
        and rel is not None
        and not rel.startswith("build/")
        and (in_drafting or target.suffix in SOURCE_SUFFIXES)
    ):
        raise EnvError(
            f"{path} would be among the quilt's sources, which loom never writes; write it under build/ or outside the quilt"
        )
    if target.exists() and not overwrite:
        raise EnvError(f"{path} exists; loom does not overwrite it")
    return target


#: Environment variables an agent's shell carries. `AI_AGENT` is the generic one; the rest name a particular tool.
#: Loom reads them only to refuse the author's verbs, never to change what any other command does.
AGENT_MARKERS = ("AI_AGENT", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CODEX_SANDBOX", "CURSOR_AGENT", "GEMINI_CLI")


def agent_marker() -> str | None:
    """The marker variable set in this environment, or None when no agent is running the shell."""
    import os

    return next((v for v in AGENT_MARKERS if os.environ.get(v)), None)


#: What to call an agent that has not named itself. A record that says "claude-code" is auditable; one that says the
#: author's git name because the agent's shell inherited it is not, which is what DR-185 found.
AGENT_NAMES = {
    "AI_AGENT": "agent",
    "CLAUDECODE": "claude-code",
    "CLAUDE_CODE_ENTRYPOINT": "claude-code",
    "CODEX_SANDBOX": "codex",
    "CURSOR_AGENT": "cursor",
    "GEMINI_CLI": "gemini",
}


def agent_name() -> str | None:
    """What the agent running this shell is called, or None when a person is."""
    marker = agent_marker()
    return AGENT_NAMES.get(marker, "agent") if marker else None


#: What makes a declared name an agent's. An agent is instructed to include one when it names itself, so that a record
#: says what wrote it without loom having to guess from the environment it happened to run in.
AGENT_WORDS = ("agent", "ai", "bot", "assistant")


def is_agent(name: str) -> bool:
    """Whether a declared identity is an agent's, by the word it was asked to include in its own name.

    The words are matched however they are punctuated, because the form loom's own documents ask for is `Referee (Agent)` and the showcase writes exactly that. Splitting on whitespace and hyphens made `(agent)` a different word from `agent`, so the name the orientation teaches was read as a person's: the session picker showed a parked agent as `⟨person⟩`, and `refuse_under_agent` let that name run `loom accept` and `loom library verify`. Found by the reading study, 2026-09-21.
    """
    import re

    return any(w in re.findall(r"[a-z0-9]+", name.lower()) for w in AGENT_WORDS)


def writer(root: Path, declared: str | None) -> tuple[str, str]:
    """(name, kind) for whoever is writing, from what they declared rather than from the shell they are in.

    **An explicit identity wins, and a marker with no explicit identity refuses rather than guesses.** The markers distinguish well today -- the author's own shell carries no `CLAUDECODE` -- but an author may ask an agent to run a command, and a marker can be unset. Sniffing was always a proxy for the question actually being asked, which is *who is making this claim*; now it is asked.

    Parameters
    ----------
    root : Path
        The quilt.
    declared : str, optional
        What `--as` or `--author` said. An agent names itself and is asked to include `Agent` or `AI` in the name.

    Returns
    -------
    tuple of (str, str)
        The name, and `agent` or `person`.
    """
    said = (declared or "").strip()
    if said:
        return said, "agent" if is_agent(said) else "person"
    marker = agent_marker()
    if marker:
        raise EnvError(
            f"an agent is running this shell ({marker} is set) and has not said who it is.\n"
            "Name yourself with --as, including Agent or AI in the name, so the record says what wrote it: "
            '--as "Referee Agent".'
        )
    return whoever(root), "person"


def whoever(root: Path, author: str | None = None, *, sniff: bool = True) -> str:
    """Who is running this, for a record that wants provenance and must not refuse for want of it.

    Opening, retitling or closing a session is not an authored claim about anybody's mathematics, so an unconfigured author name costs the record a name and never the command. The verbs that *are* claims -- `accept`, `library verify`, a comment -- keep asking. `sniff=False` is the write API's: a write over HTTP is somebody at a browser, and the shell `loom serve` was started in says nothing about them.
    """
    from loom.scan.quilt import NoAuthorError, resolve_author

    if (author or "").strip():
        return str(author).strip()
    robot = agent_name() if sniff else None
    if robot:
        return robot
    try:
        return resolve_author(None, root)[0]
    except NoAuthorError:
        return ""


def refuse_under_agent(verb: str, how: str, declared: str | None = None) -> None:
    """Refuse one of the author's acts when an agent could be the one performing it.

    The claim these acts make -- *I checked this*, *I accept this mathematics*, *erase this* -- is the author's, and a record that credits the author with a check nobody made is worse than no record. A declared name that calls itself an agent is refused wherever it came from; and under an agent marker the act is refused **whatever name is declared**, because a name cannot be checked and an agent that types the author's name is exactly the case to stop (DR-325-ikmartin). The author runs these in a shell of their own.
    """
    if declared and is_agent(declared):
        raise EnvError(f"{verb} is the author's, and {declared} is an agent.\n{how}")
    marker = agent_marker()
    if marker:
        named = f", whatever --author or --as says ({declared})" if declared else ""
        raise EnvError(
            f"{verb} is the author's, and an agent is running this shell ({marker} is set){named}; run it in a terminal of your own.\n{how}"
        )
