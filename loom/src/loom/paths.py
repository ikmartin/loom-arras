"""Every path loom uses inside a quilt, relative to the quilt root, named once.

Quilt-relative POSIX strings, so each works both as `root / X` and in a string comparison. A path set in `config.toml` (`[quilt] drafting`, `drafting_ai`, `history`, `research_state`) is read from the config; `HISTORY` here is only that setting's default. `loom/tests/unit/test_paths.py` refuses a quilt path spelled out anywhere else.
"""

from __future__ import annotations

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
#: Loom's clone of the document workspace (an Overleaf project).
WORKSPACE = f"{LOOM}/workspace"
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
