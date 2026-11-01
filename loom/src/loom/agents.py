"""Where an agent may write in a quilt: its own places, what is always protected, and the person's `[agents] deny` list.

One boundary, read two ways: `denied_by` is the predicate loom's own commands ask for every agent, and `claude_allows`/`claude_denies` render it into Claude Code's permission file, the one client whose file can refuse an edit by path. Inside `.loom/` loom's table alone decides; the list governs the rest of the quilt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from loom.paths import (
    ADOPTION_DECISIONS,
    AI,
    ANNOTATIONS,
    BUILD,
    COPIES,
    DIGESTS,
    LAST_SEEN,
    LEDGER,
    LOOM,
    LOOM_GITIGNORE,
    REFERENCE_NOTES,
    RETIRED,
    REVIEW_DECISIONS,
    REVIEW_OBSERVATIONS,
    REVIEW_ORIGINS,
    SERVE_JSON,
    SESSIONS,
    SINCE,
    SOURCE_SYNC,
)

if TYPE_CHECKING:
    from loom.scan.quilt import QuiltConfig

CONFIG = "config.toml"
#: Where an agent always writes, whatever the list says: its session's directory, the build output and its copies.
AGENT_PLACES = (SESSIONS, BUILD, COPIES)
#: The session index, a record inside an agent's place that only loom writes.
SESSION_INDEX = f"{SESSIONS}/index.jsonl"
#: Loom's record directories under `.loom/`, each named, since a Claude Code deny of `.loom/` would beat the places' allows; the history is the quilt's `[quilt] history` beside them.
LOOM_DIRS = (DIGESTS, ANNOTATIONS, AI, RETIRED, SINCE)
#: Loom's record files under `.loom/`, each named for the same reason.
LOOM_FILES = (
    LEDGER,
    REFERENCE_NOTES,
    SERVE_JSON,
    REVIEW_DECISIONS,
    REVIEW_ORIGINS,
    REVIEW_OBSERVATIONS,
    ADOPTION_DECISIONS,
    SOURCE_SYNC,
    LAST_SEEN,
    LOOM_GITIGNORE,
    SESSION_INDEX,
)


@dataclass(frozen=True)
class Pattern:
    """One `[agents] deny` entry: the text as written, and how it matches a quilt-relative path."""

    text: str
    body: str  # without the anchoring `/` and the trailing `/`
    anchored: bool  # matches from the root only
    directory: bool  # matches a directory, and so everything under it
    regex: re.Pattern[str]

    def matches(self, rel: str) -> bool:
        """Whether this entry denies the quilt-relative file `rel`: the file itself, or a directory it sits in."""
        return self.regex.match(rel) is not None


def _glob(body: str) -> str:
    """A gitignore glob as a regex: `*` and `?` stop at `/`, `**` crosses directories, `[...]` is a class."""
    out, i = [], 0
    while i < len(body):
        c = body[i]
        if body.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif body.startswith("**", i):
            out.append(".*")
            i += 2
        elif c == "*":
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        elif c == "[" and (end := body.find("]", i + 2)) != -1:
            inner = body[i + 1 : end]
            out.append("[" + ("^" + inner[1:] if inner.startswith("!") else inner).replace("\\", "\\\\") + "]")
            i = end + 1
        else:
            out.append(re.escape(c))
            i += 1
    return "".join(out)


def compile_pattern(text: str) -> Pattern | str:
    """`text` as a `Pattern`, or why it is refused: negation (a Claude Code allow cannot undo a deny), `..`, an absolute path, or nothing to match."""
    raw = text.strip()
    if raw.startswith("!"):
        return f"{text!r} negates, which a deny list cannot: an agent's client lets a deny beat any allow"
    if raw.startswith(("//", "~")) or re.match(r"^[A-Za-z]:", raw):
        return f"{text!r} is not a path in the quilt"
    body = raw.strip("/")
    if not body:
        return f"{text!r} names nothing"
    if ".." in PurePosixPath(body).parts:
        return f"{text!r} leaves the quilt"
    directory = raw.endswith("/")
    anchored = raw.startswith("/") or "/" in body
    rest = r"/.+" if directory else r"(?:/.+)?"
    regex = re.compile(("^" if anchored else "^(?:.*/)?") + _glob(body) + rest + "$")
    return Pattern(raw, body, anchored, directory, regex)


def deny_list(entries: list[str]) -> tuple[list[Pattern], list[str]]:
    """(the patterns, the refusals) for `[agents] deny`'s entries, in order."""
    patterns: list[Pattern] = []
    refused: list[str] = []
    for entry in entries:
        got = compile_pattern(entry)
        if isinstance(got, Pattern):
            patterns.append(got)
        else:
            refused.append(got)
    return patterns, refused


def _under(rel: str, dirs: tuple[str, ...]) -> bool:
    return any(rel == d or rel.startswith(f"{d}/") for d in dirs)


def always_protected(config: QuiltConfig) -> list[str]:
    """What no agent writes whatever the list says, as the orientation names it: loom's directory but for the agent's places, the history wherever it sits, the config and the research state."""
    out = [f"{LOOM}/ (but {', '.join(f'{p}/' for p in AGENT_PLACES)})"]
    if not _under(config.history, (LOOM,)):
        out.append(f"{config.history}/")
    return [*out, CONFIG, config.research_state]


def denied_by(config: QuiltConfig, rel: str) -> str | None:
    """What keeps an agent from writing the quilt-relative file `rel`: the protection or the list's entry, as the person reads it; None when the agent may write it."""
    rel = PurePosixPath(rel).as_posix()
    if rel == SESSION_INDEX:
        return rel
    if _under(rel, AGENT_PLACES):
        return None
    if _under(rel, (LOOM,)):
        return f"{LOOM}/"
    if _under(rel, (config.history,)):
        return f"{config.history}/"
    if rel in (CONFIG, config.research_state):
        return rel
    return next((p.text for p in deny_list(config.agents_deny)[0] if p.matches(rel)), None)


def refusal(config: QuiltConfig, rel: str) -> str | None:
    """Why an agent may not write the quilt-relative file `rel`, as a refusal says it; None when it may."""
    why = denied_by(config, rel)
    if why is None:
        return None
    if why == config.research_state:
        return f"an agent writes {why} only through `loom write`, which records the write"
    if why in (f"{LOOM}/", SESSION_INDEX, f"{config.history}/", CONFIG):
        places = ", ".join(f"{p}/" for p in AGENT_PLACES)
        return (
            f"{why} is loom's, and an agent writes only in {places} there"
            if why != CONFIG
            else f"{CONFIG} is the person's, and no agent writes it"
        )
    return f"the quilt protects it from agents ([agents] deny names {why} in {CONFIG})"


def claude_allows() -> list[str]:
    """The paths Claude Code lets an agent edit without asking: its places, relative to the quilt root it is started in (DR-343-ikmartin)."""
    return [f"{p}/**" for p in AGENT_PLACES]


def claude_denies(config: QuiltConfig) -> list[str]:
    """The paths Claude Code refuses an agent, anchored to the quilt root with `/`: loom's records named one by one, the history, the config, the research state, then the list."""
    dirs = [*LOOM_DIRS] + ([config.history] if config.history not in LOOM_DIRS else [])
    out = [f"/{d}/**" for d in dirs]
    out += [f"/{f}" for f in (*LOOM_FILES, CONFIG, config.research_state)]
    for p in deny_list(config.agents_deny)[0]:
        at = f"/{p.body}" if p.anchored else f"/**/{p.body}"
        # a pattern without a trailing `/` names a file or a directory, as in gitignore, so both are refused
        out += [f"{at}/**"] if p.directory else [at, f"{at}/**"]
    return out
