"""Every path loom uses inside a quilt, relative to the quilt root, named once.

Quilt-relative POSIX strings, so each works both as `root / X` and in a string comparison. A path set in `config.toml` (`[quilt] history`, `research_state`) is read from the config; `HISTORY` here is only that setting's default. `loom/tests/unit/test_paths.py` refuses a quilt path spelled out anywhere else.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import PurePosixPath

#: Loom's own directory: everything loom writes in a quilt, records and derived output alike, lives under it.
LOOM = ".loom"
#: Everything loom can rebuild; deletable at any moment.
BUILD = f"{LOOM}/build"
#: Digests of cited works, their results and proposals, and the bibliography.
DIGESTS = f"{LOOM}/digests"
#: Loom's store of other people's documents, keyed by the work's identifier.
STORAGE = f"{DIGESTS}/storage"
#: The address the viewer reaches the store at, under its root, fixed wherever `STORAGE` sits: the server answers it and the manifest's `artifacts.dir` is written in it.
STORE_ADDRESS = "digests/storage"
#: The annotation log's directory.
ANNOTATIONS = f"{LOOM}/annotations"
#: What an agent is given: orientation, rules, formatting, modes.
AI = f"{LOOM}/ai"
#: Where `atomize --retire` sets a converted source aside.
RETIRED = f"{LOOM}/retired"
SESSIONS = f"{LOOM}/sessions"
#: Agent copies of documents, made by `loom draft DOC --ai NAME` and read by the scan on purpose.
COPIES = f"{LOOM}/copies"
#: Where each agent last looked, which `loom since` reads.
SINCE = f"{LOOM}/since"
#: Annotations a person deleted, one line each for the agent that wrote it, until that agent's `loom since` has reported it; machine-local, like the markers beside it.
DELETED = f"{SINCE}/deleted.jsonl"
#: Each person's last look at the open files, which Review's Your Changes reads.
LOOKED = f"{LOOM}/looked"
#: The default of `[quilt] history`; code reads the setting, never this.
HISTORY = f"{LOOM}/history"

#: What a command locks while it draws a node id (`loom.locks`), since those are read from the whole quilt and no one file holds them. It holds nothing, so it stays with what loom can rebuild.
ID_LOCK = f"{BUILD}/ids.lock"

#: Where `loom new`, atomize and fork write node files, relative to the document they serve.
NODES = "nodes"

#: The acceptance ledger, written only by `loom accept`.
LEDGER = f"{LOOM}/state.toml"
ANNOTATION_LOG = f"{ANNOTATIONS}/log.jsonl"
#: The quilt's annotation types: presets a person picks from and an agent reads, written by `loom init` with the defaults.
ANNOTATION_TYPES = f"{LOOM}/annotation-types.toml"
#: Notes, a quote among them: their own log beside the annotations'.
NOTE_LOG = f"{ANNOTATIONS}/notes.jsonl"
#: The running server's address and token.
SERVE_JSON = f"{LOOM}/serve.json"
REVIEW_DECISIONS = f"{LOOM}/review-decisions.json"
REVIEW_ORIGINS = f"{LOOM}/review-origins.json"
REVIEW_OBSERVATIONS = f"{LOOM}/review-observations.json"
ADOPTION_DECISIONS = f"{LOOM}/adoption-decisions.json"
SOURCE_SYNC = f"{LOOM}/source-sync.json"
#: Loom's cache of the last text it saw for every key, in `.loom/` wherever `[quilt] history` puts the history.
LAST_SEEN = f"{LOOM}/last-seen.json"
#: Loom's ignore file, saying which of its files stay on one machine.
LOOM_GITIGNORE = f"{LOOM}/.gitignore"
#: The quilt's bibliography, gathered from the landmarks.
BIBLIOGRAPHY = f"{DIGESTS}/bibliography.bib"
UNREADABLE = f"{DIGESTS}/unreadable.json"
LINKS = f"{DIGESTS}/links.jsonl"
LINKS_REMOVED = f"{DIGESTS}/links-removed.jsonl"
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


def document_dir(path: str) -> str:
    """The quilt-relative directory a file sits in, '' at the root: the base a document's names resolve against."""
    parent = PurePosixPath(path).parent.as_posix()
    return "" if parent == "." else parent


def under(base: str, name: str) -> str:
    """`name` read against the quilt-relative directory `base`, as a quilt-relative path; `name` itself at the root."""
    return (PurePosixPath(base) / name).as_posix() if base else PurePosixPath(name).as_posix()


def document_build(path: str) -> str:
    """Where a document compiles to, `.loom/build/<name>`; latexmk names what it writes there by the file's own stem."""
    return f"{BUILD}/{document_name(path)}"
