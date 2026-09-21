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


def emit_json(obj: Any) -> None:
    """Print one JSON document to stdout and nothing else there; diagnostics go to stderr."""
    click.echo(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False))


def note(message: str) -> None:
    """Progress or diagnostic text, always on stderr so --json stdout stays clean."""
    click.echo(message, err=True)


def resolve_run(root: Path, run_dir: str | None) -> Path | None:
    """A `--run` directory as a path: absolute as given, otherwise relative to the quilt root (never to the shell's cwd), so `--run ai/runs/x` means the quilt's run from any directory.

    See Also
    --------
    find_session : a session by id, title or unique suffix.
    """
    if not run_dir:
        return None
    p = Path(run_dir).expanduser()
    return p if p.is_absolute() else root / p


def under_runs(root: Path, p: Path) -> bool:
    """Whether a resolved `--run` path is inside `ai/runs/`, which is the only place an agent may write."""
    try:
        return p.resolve().is_relative_to((root / "ai" / "runs").resolve())
    except (OSError, ValueError):
        return False


def find_session(root: Path, which: str | None):  # type: ignore[no-untyped-def]
    """Locate a session by id, by title, or by a unique id suffix; with nothing, the active one (plan 0.13 §5).

    Refuses rather than guessing, and refuses rather than creating: a value that matched nothing used to be made as a directory at the quilt root, and that directory then satisfied every later lookup, so a whole sitting's annotations were filed under a run that did not exist.
    """
    from loom.sessions import active, sessions

    if not which:
        here = active(root)
        standing = sessions(root)
        if here and here in standing:
            return standing[here]
        raise EnvError('no session is active; loom session new "a name" opens one')
    standing = sessions(root, deleted=True)
    if which in standing:
        return standing[which]
    want = which.strip().lower()
    # The title is what a person remembers, so it is what this accepts -- exactly, then as part of one. An id suffix
    # is here for the same reason: nobody types a date they can see in a listing.
    for pick in (
        lambda x: x.title.lower() == want,
        lambda x: x.id.endswith(want),
        lambda x: want in x.title.lower(),
    ):
        hits = [x for x in standing.values() if pick(x)]
        if len(hits) == 1:
            return hits[0]
        if hits:
            # naming the matches rather than guessing, as `refs resolve` does with candidates
            named = ", ".join(f"{x.id} ({x.title})" for x in hits[:4])
            raise EnvError(f"{which!r} matches {len(hits)} sessions: {named}")
    raise EnvError(f"no session matches {which!r}; loom session list shows them")


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
    """Whether a declared identity is an agent's, by the word it was asked to include in its own name."""
    return any(w in name.lower().split() or w in name.lower().replace("-", " ").split() for w in AGENT_WORDS)


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


def whoever(root: Path, author: str | None = None) -> str:
    """Who is running this, for a record that wants provenance and must not refuse for want of it.

    Opening, retitling or closing a session is not an authored claim about anybody's mathematics, so an unconfigured author name costs the record a name and never the command. The verbs that *are* claims -- `accept`, `refs verify`, a comment -- keep asking.
    """
    from loom.scan.quilt import NoAuthorError, resolve_author

    if (author or "").strip():
        return str(author).strip()
    robot = agent_name()
    if robot:
        return robot
    try:
        return resolve_author(None, root)[0]
    except NoAuthorError:
        return ""


def refuse_under_agent(verb: str, how: str, declared: str | None = None) -> None:
    """Refuse one of the author's verbs when an agent is the writer.

    The claim these verbs make -- *I checked this*, *I accept this mathematics* -- is the author's, and a record that credits the author with a check nobody made is worse than no record. An agent verified its own proposal in the first study run and loom recorded the author as the verifier, because the author's name comes from git, which an agent's shell shares.

    **The guard is on the identity, not the door** (plan 0.13 §8). A session is now shared by a person and an agent, and the write API is no longer only the author's own click, so neither the session nor the environment says who is writing. A declared name that calls itself an agent is refused whichever surface it came through; a marker with no declared identity is refused too, because it will not guess.
    """
    if declared and is_agent(declared):
        raise EnvError(f"{verb} is the author's, and {declared} is an agent.\n{how}")
    if declared:
        return  # an explicit identity wins: a person who named themselves is a person, whatever shell they are in
    marker = agent_marker()
    if marker:
        raise EnvError(f"{verb} is the author's, and an agent is running this shell ({marker} is set).\n{how}")
