"""The ignore lines loom relies on, each set from one list: `.loom/.gitignore`, loom's own file, which `loom init` writes and `loom upgrade` rewrites above the line `OWN`, keeping the person's lines below it; and the lines for the agent client files, which `loom ai init` and `loom upgrade` add to the quilt's root `.gitignore`, touching nothing else there. `loom doctor` checks both.

The root `.gitignore` is the person's: loom adds only what its client files need, since they name this machine's paths.
"""

from __future__ import annotations

from pathlib import Path

from loom.ai.clients import PROJECT_FILES
from loom.paths import BUILD, LAST_SEEN, LOOM, LOOM_GITIGNORE, SERVE_JSON, SESSIONS, SINCE, STORAGE


def _inside(path: str) -> str:
    """`path`, a quilt path under `.loom/`, as `.loom/.gitignore` names it."""
    return path.removeprefix(f"{LOOM}/")


#: What stays on one machine under `.loom/`, as `.loom/.gitignore` names it.
LOOM_LINES = (
    f"{_inside(BUILD)}/",
    _inside(SERVE_JSON),
    f"{_inside(SINCE)}/",
    _inside(LAST_SEEN),
    f"{_inside(SESSIONS)}/*/attached.json",
    f"{_inside(SESSIONS)}/*/cursors/",
    f"{_inside(STORAGE)}/**/paper.pdf",
    f"{_inside(STORAGE)}/**/src/",
    f"{_inside(STORAGE)}/cache/",
)

#: The line after which `.loom/.gitignore` is the person's: a line of their own there, such as `!digests/storage/**/paper.pdf` to commit the store's PDFs, outlives `loom upgrade`.
OWN = "# your own lines go below this one; loom upgrade keeps them"

LOOM_IGNORE = (
    "# loom's files that stay on this machine: what it rebuilds, its caches and runtime state, and its copies of other people's documents. "
    "Everything else here is committed: the history, the acceptance ledger, annotations, sessions, digests, and a stored document's page text, "
    "which lets a coauthor who holds no PDF re-check a transcription. `loom upgrade` rewrites the lines above the last.\n"
    + "\n".join(LOOM_LINES)
    + f"\n{OWN}\n"
)

#: The lines the root `.gitignore` needs once `loom ai init` has written the agent client files.
CLIENT_LINES = PROJECT_FILES
CLIENT_COMMENT = "# what starts loom's MCP server for each agent's app, written by `loom ai init`: it names this machine's loom and this quilt's path, so every machine writes its own\n"


def _wanted(root: Path) -> tuple[str, str]:
    """(what `.loom/.gitignore` holds, what this loom would make it): the person's own lines kept below `OWN`."""
    p = root / LOOM_GITIGNORE
    have = p.read_text(encoding="utf-8") if p.is_file() else ""
    own = have.split(f"{OWN}\n", 1)[1] if f"{OWN}\n" in have else ""
    return have, LOOM_IGNORE + own


def loom_ignore_current(root: Path) -> bool:
    """Whether `.loom/.gitignore` carries this loom's lines above the person's own."""
    have, want = _wanted(root)
    return have == want


def write_loom_ignore(root: Path, *, write: bool = True) -> bool:
    """Write `.loom/.gitignore` when it is absent or its lines are not this loom's, keeping the person's own; returns whether it was (or, with `write` False, would be) written."""
    have, want = _wanted(root)
    if have == want:
        return False
    if write:
        p = root / LOOM_GITIGNORE
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(want, encoding="utf-8")
    return True


def missing(root: Path) -> list[str]:
    """The client lines the quilt's root `.gitignore` lacks, in `CLIENT_LINES`'s order."""
    p = root / ".gitignore"
    have = set(p.read_text(encoding="utf-8").splitlines()) if p.is_file() else set()
    return [line for line in CLIENT_LINES if line not in have]


def ensure(root: Path) -> list[str]:
    """Append the missing client lines to the root `.gitignore` under one comment, making the file if needed and touching nothing else; returns what it added."""
    lines = missing(root)
    if not lines:
        return []
    p = root / ".gitignore"
    existing = p.read_text(encoding="utf-8") if p.is_file() else ""
    p.write_text(
        existing.rstrip("\n") + ("\n" if existing else "") + CLIENT_COMMENT + "\n".join(lines) + "\n", encoding="utf-8"
    )
    return lines
