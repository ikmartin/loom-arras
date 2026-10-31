"""Every path loom uses inside a quilt, relative to the quilt root, named once.

Quilt-relative POSIX strings, so each works both as `root / X` and in a string comparison. A path set in `config.toml` (`[quilt] drafting`, `drafting_ai`, `history`, `research_state`) is read from the config; `HISTORY` here is only that setting's default. `loom/tests/unit/test_paths.py` refuses a quilt path spelled out anywhere else.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import PurePosixPath

#: Loom's own directory: its records, sessions and history.
LOOM = ".loom"
#: Everything loom can rebuild; deletable at any moment.
BUILD = "build"
#: Digests of cited works, their results and proposals, and the bibliography.
DIGESTS = "digests"
#: Loom's store of other people's documents, keyed by the work's identifier.
STORAGE = f"{DIGESTS}/storage"
#: The annotation log's directory.
ANNOTATIONS = "annotations"
#: What an agent is given: orientation, rules, formatting, modes.
AI = "ai"
#: Where `atomize --retire` sets a converted source aside.
RETIRED = "retired"
SESSIONS = f"{LOOM}/sessions"
#: Where each agent last looked, which `loom since` reads.
SINCE = f"{LOOM}/since"
#: The default of `[quilt] history`; code reads the setting, never this.
HISTORY = f"{LOOM}/history"

#: Where `loom new`, atomize and fork write node files.
NODES = "nodes"
#: The author's seed space for PDFs and `.bib` files, which loom reads and never writes.
REFS = "refs"
#: The author's own reference material, which loom never scans.
NOTES_DIR = "notes"

#: The acceptance ledger, written only by `loom accept`.
LEDGER = f"{LOOM}/state.toml"
ANNOTATION_LOG = f"{ANNOTATIONS}/log.jsonl"
#: Works an agent proposed citing and the author accepted.
REFERENCE_NOTES = "reference-notes.jsonl"
#: The running server's address and token.
SERVE_JSON = f"{LOOM}/serve.json"
REVIEW_DECISIONS = f"{LOOM}/review-decisions.json"
REVIEW_ORIGINS = f"{LOOM}/review-origins.json"
REVIEW_OBSERVATIONS = f"{LOOM}/review-observations.json"
ADOPTION_DECISIONS = f"{LOOM}/adoption-decisions.json"
SOURCE_SYNC = f"{LOOM}/source-sync.json"
#: Loom's cache of the last text it saw for every key, a file beside the history directory, wherever that is.
LAST_SEEN = "last-seen.json"
#: The quilt's bibliography, gathered from the landmarks.
BIBLIOGRAPHY = f"{DIGESTS}/bibliography.bib"
UNREADABLE = f"{DIGESTS}/unreadable.json"
LINKS = f"{DIGESTS}/links.jsonl"
LINKS_REMOVED = f"{DIGESTS}/links-removed.jsonl"
#: The three macros, at the root where documents compile.
STY = "loom.sty"
MANIFEST = f"{BUILD}/manifest.json"
CLOSURES = f"{BUILD}/closures"


def document_name(path: str) -> str:
    """A document's name: its quilt-relative path without `.tex`, kept as a path (`paper/main.tex` is `paper/main`).

    The key of its build output, its fragment and its address in the viewer; two documents' names never collide, as their stems may.
    """
    return path.removesuffix(".tex")


def documents_named(word: str, pool: Iterable[str]) -> list[str]:
    """The documents among `pool` that `word` names: the one whose path or name it is, else every one whose file name or stem it is.

    Callers take a single match and refuse several, naming them: stems repeat across directories, so a stem is a name only while one document has it.
    """
    docs = list(pool)
    exact = [d for d in docs if word in (d, document_name(d))]
    return exact or [d for d in docs if word in (PurePosixPath(d).name, PurePosixPath(d).stem)]


def document_build(path: str) -> str:
    """Where a document compiles to, `build/<name>`; latexmk names what it writes there by the file's own stem."""
    return f"{BUILD}/{document_name(path)}"
