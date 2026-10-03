"""Poll file mtimes every second and rebuild when something the build depends on changed (book 9.8), the skeleton of the site generator's watcher with the roots parameterised.

Watched: every .tex, .sty, .cls, .bib under the quilt root outside build/, config.toml, the ledger and snapshots, the annotation log, the reference notes, and session files other than the inbox. Build-written observation caches are excluded to avoid an extra rebuild. The callback runs in the watcher thread; a blanket except keeps the thread alive and reports.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path

from loom.mailbox import INBOX
from loom.records.lastseen import CACHE

SKIP = {"build", ".git", "node_modules", ".svelte-kit"}
SUFFIXES = {".tex", ".sty", ".cls", ".bib", ".toml", ".json", ".jsonl", ".md", ".log"}
#: What a change to records alone touches; see `records_only`.
RECORDS = ("annotations/", "comments/", ".loom/sessions/")
RECORD_FILES = ("reference-notes.jsonl", ".loom/review-decisions.json", ".loom/review-origins.json")


def _files(root: Path) -> Iterator[Path]:
    """Every file under `root` outside the directories `SKIP` names, which are pruned rather than walked: a quilt's `build/` holds thousands of files and is polled every second."""
    for here, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP]
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
        if p.suffix not in SUFFIXES or p.name in (CACHE, "review-observations.json", INBOX):
            continue
        rel = p.relative_to(root)
        # Review decisions publish only queue metadata through the API; Finish review rebuilds the view.
        if rel.as_posix() in (".loom/review-decisions.json", ".loom/adoption-decisions.json"):
            continue
        # `annotations/log.jsonl` is where every comment, reply and finding lands, and `reference-notes.jsonl` is
        # where an accepted citation does. Neither was watched -- the directory list still said `comments/`, the name
        # the log replaced in 0.10, and `.jsonl` was not a watched suffix -- so a write through `loom serve`'s own API
        # appended to the log and the page it came from never changed (DR-174).
        if (
            rel.parts[0] in ("ai", "annotations", "comments", ".loom")
            or p.suffix in (".tex", ".sty", ".cls", ".bib")
            or rel.as_posix() in ("config.toml", "reference-notes.jsonl")
        ):
            try:
                seen[p] = p.stat().st_mtime
            except OSError:
                continue
    return seen


class Watcher:
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
        while not self._stop.is_set():
            time.sleep(self.interval)
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
