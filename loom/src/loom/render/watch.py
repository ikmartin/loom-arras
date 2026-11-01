"""Poll file mtimes, the tree every second and loom's own records five times a second, and rebuild when something the build depends on changed, the skeleton of the site generator's watcher with the roots parameterised.

Watched: every .tex, .sty, .cls, .bib under the quilt root outside loom's build output and store, config.toml, and loom's records under `.loom/` (the ledger and snapshots, the annotation log, the reference notes, the agents' files, session files other than the inbox). Build-written observation caches are excluded to avoid an extra rebuild. The callback runs in the watcher thread; a blanket except keeps the thread alive and reports.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path

from loom.mailbox import INBOX
from loom.paths import (
    ADOPTION_DECISIONS,
    ANNOTATION_LOG,
    ANNOTATIONS,
    BUILD,
    COPIES,
    DIGESTS,
    LOOM,
    REFERENCE_NOTES,
    RETIRED,
    REVIEW_DECISIONS,
    REVIEW_OBSERVATIONS,
    REVIEW_ORIGINS,
    SERVE_JSON,
    SESSIONS,
    SINCE,
    STORAGE,
)
from loom.records.lastseen import CACHE

SKIP = {".git", "node_modules", ".svelte-kit"}
#: Pruned by quilt-relative path: the build output, which a build writes and which holds thousands of files, and loom's store of other people's documents, which no build reads as source.
PRUNED = (BUILD, STORAGE)
#: The directories under `.loom/` watched for their sources alone, as any of the quilt's directories is; everything else there is a record.
SOURCES_ONLY = (f"{DIGESTS}/", f"{RETIRED}/", f"{COPIES}/")
SUFFIXES = {".tex", ".sty", ".cls", ".bib", ".toml", ".json", ".jsonl", ".md", ".log"}
#: What a change to records alone touches; see `records_only`.
RECORDS = (f"{ANNOTATIONS}/", f"{SESSIONS}/")
RECORD_FILES = (REFERENCE_NOTES, REVIEW_DECISIONS, REVIEW_ORIGINS)


def _files(root: Path) -> Iterator[Path]:
    """Every file under `root` outside the directories `SKIP` names, `PRUNED` and the sync directory, which are pruned rather than walked, since the tree is polled every second."""
    from loom.sync import skipped_directory

    synced = skipped_directory(root)
    pruned = {root / d for d in PRUNED} | ({root / synced} if synced else set())
    for here, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP and Path(here) / d not in pruned]
        for name in names:
            yield Path(here) / name


def records_only(root: Path, changed: list[Path]) -> bool:
    """Whether every path in `changed` is a record the scan never reads: the annotation log, the reference notes, a session's files, or the review decisions. A build after such a change may reuse the last scan."""
    for p in changed:
        rel = p.relative_to(root).as_posix() if p.is_absolute() else p.as_posix()
        if not (rel.startswith(RECORDS) or rel in RECORD_FILES):
            return False
    return True


def snapshot(root: Path) -> dict[Path, float]:
    seen: dict[Path, float] = {}
    for p in _files(root):
        # A session's inbox is read live through `/_api/events`; rebuilding the manifest per message would re-render what the reader has open.
        if p.suffix not in SUFFIXES or p.name in (Path(CACHE).name, Path(REVIEW_OBSERVATIONS).name, INBOX):
            continue
        rel = p.relative_to(root)
        # Review decisions publish only queue metadata through the API; Finish review rebuilds the view.
        # and `serve.json` is the server's own note of where it listens, which no build reads
        if rel.as_posix() in (REVIEW_DECISIONS, ADOPTION_DECISIONS, SERVE_JSON):
            continue
        # where each agent last looked (`loom since`), which no build reads either
        if rel.as_posix().startswith(f"{SINCE}/"):
            continue
        # loom's records under `.loom/` count whatever their suffix: a write through `loom serve`'s own API to the annotation log or the reference notes must redraw the page it came from (DR-174)
        posix = rel.as_posix()
        if (
            (posix.startswith(f"{LOOM}/") and not posix.startswith(SOURCES_ONLY))
            or p.suffix in (".tex", ".sty", ".cls", ".bib")
            or posix == "config.toml"
        ):
            try:
                seen[p] = p.stat().st_mtime
            except OSError:
                continue
    return seen


#: The records loom's own commands append to, looked at between full scans: an agent's annotation is drawn within a fraction of a second rather than on the next scan.
FAST = (ANNOTATION_LOG, REFERENCE_NOTES, f"{SESSIONS}/index.jsonl")
#: How often the fast lane looks.
FAST_INTERVAL = 0.2


def _fast(root: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    for rel in FAST:
        try:
            out[rel] = (root / rel).stat().st_mtime
        except OSError:
            continue
    return out


class Watcher:
    """Poll the quilt and call `on_change` with what changed: the whole tree every `interval`, and loom's own records (`FAST`) every `FAST_INTERVAL`, a change there starting a full look at once."""

    def __init__(self, root: Path, on_change: Callable[[list[Path]], None], interval: float = 1.0) -> None:
        self.root = root
        self.on_change = on_change
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._seen = snapshot(root)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="loom-watch", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.interval * 3)

    def rebaseline(self, seen: dict[Path, float] | None = None) -> None:
        """Take `seen` (default the files as they are now) as what has been handled, so the next poll reports only what changed since."""
        self._seen = snapshot(self.root) if seen is None else seen

    def _loop(self) -> None:
        fast = _fast(self.root)
        due = time.monotonic() + self.interval
        while not self._stop.is_set():
            time.sleep(min(FAST_INTERVAL, self.interval))
            now_fast = _fast(self.root)
            if now_fast == fast and time.monotonic() < due:
                continue
            fast = now_fast
            due = time.monotonic() + self.interval
            try:
                now = snapshot(self.root)
                changed = [p for p, m in now.items() if self._seen.get(p) != m] + [
                    p for p in self._seen if p not in now
                ]
                self._seen = now
                if changed:
                    self.on_change(changed)
            except Exception as exc:  # noqa: BLE001
                print(f"loom serve: watcher error: {exc}", file=sys.stderr)
