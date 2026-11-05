"""Shared CLI plumbing: exit codes, JSON output, and the two error classes every command raises.

Exit codes: 0 success, 1 a content problem the author can fix in the source, 2 a usage or environment problem.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from loom.paths import BUILD

EXIT_CONTENT = 1
EXIT_USAGE = 2


#: What click prints before a refusal's first line, which `fit` leaves room for.
ERROR_LEAD = len("Error: ")


def fit(text: str, lead: int = 0) -> str:
    """`text` within 100 columns line by line (T5), its first line `lead` shorter for a prefix printed before it.

    The refusals' and notes' one wrapper; an identifier or path longer than the width stands alone on its line, never cut.
    """
    from loom.cli.report import WIDTH, wrap

    return "\n".join(w for i, line in enumerate(text.split("\n")) for w in wrap(line, WIDTH - (lead if i == 0 else 0)))


class ContentError(click.ClickException):
    """A problem in the quilt's content (lint errors, failed identity test, refused write). Exit 1.

    The message is wrapped to fit; `verbatim` follows it as given, for text whose lines are its content, such as a diff.
    """

    exit_code = EXIT_CONTENT

    def __init__(self, message: str, verbatim: str = "") -> None:
        super().__init__(message)
        self.verbatim = verbatim

    def format_message(self) -> str:
        return fit(self.message, ERROR_LEAD) + self.verbatim


class EnvError(click.ClickException):
    """A usage or environment problem (bad arguments, missing tool, no author name). Exit 2.

    The message is wrapped to fit; `verbatim` follows it as given, for text whose lines are its content.
    """

    exit_code = EXIT_USAGE

    def __init__(self, message: str, verbatim: str = "") -> None:
        super().__init__(message)
        self.verbatim = verbatim

    def format_message(self) -> str:
        return fit(self.message, ERROR_LEAD) + self.verbatim


class NotFoundError(EnvError):
    """An argument names something that does not exist: a node, an annotation, a session, a cited work, a result. Exit 2, like any argument that names nothing; the write API answers it 404 `no-such-<what>`."""

    def __init__(self, what: str, message: str) -> None:
        super().__init__(message)
        self.what = what


def emit_json(obj: Any) -> None:
    """Print one JSON document to stdout and nothing else there; diagnostics go to stderr."""
    click.echo(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False))


def from_stdin(texts: dict[str, str | None]) -> list[str | None]:
    """The texts given, in order, with the one given as `-` read from standard input: how every command that takes a long text (LaTeX a shell would mangle) reads one.

    Standard input holds one text, so two given as `-` are refused by name.
    """
    dashed = [name for name, value in texts.items() if value == "-"]
    if len(dashed) > 1:
        raise EnvError(f"{' and '.join(dashed)} are both -, and standard input holds one text; give one of them inline")
    if not dashed:
        return list(texts.values())
    import sys

    read = sys.stdin.read()
    return [read if name == dashed[0] else value for name, value in texts.items()]


def note(message: str) -> None:
    """Progress or diagnostic text, always on stderr so --json stdout stays clean, wrapped to fit."""
    click.echo(fit(message), err=True)


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
    quilt: Any,
    path: str | Path,
    *,
    document: bool = False,
    source: bool = False,
    overwrite: bool = False,
) -> Path:
    """Where a command's `--to` writes, by the one rule every `--to` follows (K2).

    Parameters
    ----------
    quilt : Quilt
        The quilt the command runs against.
    path : str or Path
        What `--to` said; a relative path is the quilt root's, as every path loom takes is.
    document : bool, default False
        The command writes a working document: a `.tex` anywhere in the quilt the scan reads.
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
        A working document that is no `.tex`, lies outside the quilt or where the scan does not read; anything else among the quilt's sources, which loom never writes; a file that exists; or, under an agent, a path the quilt protects from agents (`refuse_protected`).
    """
    from loom.scan.scan import unread_dir

    root = Path(quilt.root).resolve()
    given = Path(path).expanduser()
    target = (given if given.is_absolute() else root / given).resolve()
    rel = target.relative_to(root).as_posix() if target.is_relative_to(root) else None
    if document:
        if rel is None:
            raise EnvError(f"{path} is outside the quilt; a working document goes inside it, e.g. --to {target.name}")
        if target.suffix != ".tex":
            raise EnvError(f"{path}: a working document is a .tex file")
        unread = unread_dir(quilt, rel)
        if unread is not None:
            raise EnvError(
                f"{path} is inside {unread}/, which loom never reads as a document; put it anywhere else in the quilt"
            )
    if (
        not document
        and not source
        and rel is not None
        and not rel.startswith(f"{BUILD}/")
        and target.suffix in SOURCE_SUFFIXES
    ):
        raise EnvError(
            f"{path} would be among the quilt's sources, which loom never writes; write it under {BUILD}/ or outside the quilt"
        )
    refuse_protected(quilt, target)
    if target.exists() and not overwrite:
        raise EnvError(f"{path} exists; loom does not overwrite it")
    return target


def refuse_protected(quilt: Any, target: Path) -> None:
    """Refuse an agent a file the quilt protects from agents, whichever command writes it and whatever client runs the agent (K5).

    Claude Code's permission file refuses the agent's own edits; this refuses the same paths when a loom command is the writer, which is the only refusal an agent in any other client meets. A person is never refused here.
    """
    if not agent_marker():
        return
    root = Path(quilt.root).resolve()
    resolved = target.resolve()
    if not resolved.is_relative_to(root):
        return
    from loom.agents import refusal

    why = refusal(quilt.config, resolved.relative_to(root).as_posix())
    if why is not None:
        raise EnvError(f"{resolved.relative_to(root).as_posix()}: {why}; write it elsewhere, or leave it to the author")


#: Environment variables an agent's shell carries. `AI_AGENT` is the generic one; the rest name a particular tool.
#: Loom reads them only to refuse what an agent may not do (the author's verbs, a protected path, a write signed with a name that does not say it is an agent's), never to change what any other command does.
AGENT_MARKERS = ("AI_AGENT", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CODEX_SANDBOX", "CURSOR_AGENT", "GEMINI_CLI")


def agent_marker() -> str | None:
    """The marker variable set in this environment, or None when no agent is running the shell."""
    import os

    return next((v for v in AGENT_MARKERS if os.environ.get(v)), None)


#: What to call an agent by the marker its app sets, the same name the app's MCP server gives it (`Client.agent`), the particular marker before the generic `AI_AGENT`, which apps set beside their own. A record that says "Claude Code Agent" is auditable; one that says the author's git name because the agent's shell inherited it is not, which is what DR-185 found.
AGENT_NAMES = {
    "CLAUDECODE": "Claude Code Agent",
    "CLAUDE_CODE_ENTRYPOINT": "Claude Code Agent",
    "CODEX_SANDBOX": "Codex Agent",
    "CURSOR_AGENT": "Cursor Agent",
    "GEMINI_CLI": "Gemini CLI Agent",
    "AI_AGENT": "agent",
}


def agent_name() -> str | None:
    """What the agent running this shell is called, or None when a person is."""
    import os

    return next((name for marker, name in AGENT_NAMES.items() if os.environ.get(marker)), None)


def name_yourself() -> str:
    """How a refusal tells the agent running this shell to sign: the name its app goes by where a marker says, else an example."""
    named = agent_name()
    example = named if named and named != AGENT_NAMES["AI_AGENT"] else "Referee Agent"
    return f'Name yourself with --as, including Agent or AI in the name, so the record says what wrote it: --as "{example}".'


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
    """(name, kind) for whoever is writing, from what they declared; under an agent marker the declaration must say it is an agent's (`signed`).

    Parameters
    ----------
    root : Path
        The quilt.
    declared : str, optional
        What `--as` said. An agent names itself, with `Agent` or `AI` in the name.

    Returns
    -------
    tuple of (str, str)
        The name, and `agent` or `person`.
    """
    said = signed(declared)
    if said:
        return said, "agent" if is_agent(said) else "person"
    return whoever(root), "person"


def signed(declared: str | None) -> str:
    """What `--as` said, stripped, or a refusal when an agent is running the shell and it names nobody or does not say it is an agent.

    A name cannot be checked, so under a marker it may only say what the marker already does: an agent that signs `Claude` or the author's name would otherwise be recorded as a person, and `loom since` would hand its words back as the person's. A shell with a marker is not the author's to sign in, here as for the author's acts (`refuse_under_agent`); the viewer and a terminal of their own are. Without a marker a declared name is taken at its word, since nothing says otherwise. Every command that records a declared name comes through here.
    """
    said = (declared or "").strip()
    marker = agent_marker()
    if marker and not said:
        raise EnvError(
            f"an agent is running this shell ({marker} is set) and has not said who it is.\n{name_yourself()}"
        )
    if marker and not is_agent(said):
        raise EnvError(
            f"an agent is running this shell ({marker} is set), and {said} does not say it is an agent.\n"
            f"{name_yourself()} A person writes in the viewer or a terminal of their own."
        )
    return said


def whoever(root: Path, author: str | None = None, *, sniff: bool = True) -> str:
    """Who is running this, for a record that wants provenance and must not refuse for want of it.

    Opening, retitling or closing a session is not an authored claim about anybody's mathematics, so an unconfigured author name costs the record a name and never the command; a name that is declared is held to `signed` like any other. The verbs that *are* claims -- `accept`, `library verify`, a comment -- keep asking. `sniff=False` is the write API's: a write over HTTP is somebody at a browser, and the shell `loom serve` was started in says nothing about them.
    """
    from loom.scan.quilt import NoAuthorError, resolve_author

    if (author or "").strip():
        return signed(author) if sniff else str(author).strip()
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
        named = f", whatever --as says ({declared})" if declared else ""
        raise EnvError(
            f"{verb} is the author's, and an agent is running this shell ({marker} is set){named}; run it in a terminal of your own.\n{how}"
        )
