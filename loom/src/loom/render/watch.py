"""Poll file mtimes every second and rebuild when something the build depends on changed (book 9.8), the skeleton of the site generator's watcher with the roots parameterised.

Watched: every .tex, .sty, .cls, .bib under the quilt root outside build/, config.toml, the ledger and snapshots, the annotation log, the reference notes, and run journals. The callback runs in the watcher thread; a blanket except keeps the thread alive and reports.
"""

from __future__ import annotations

import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

SKIP = {"build", ".git", "node_modules", ".svelte-kit"}
SUFFIXES = {".tex", ".sty", ".cls", ".bib", ".toml", ".json", ".jsonl", ".md", ".log"}


def snapshot(root: Path) -> dict[Path, float]:
    seen: dict[Path, float] = {}
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix not in SUFFIXES:
            continue
        rel = p.relative_to(root)
        if any(part in SKIP for part in rel.parts[:-1]):
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

    def rebaseline(self) -> None:
        self._seen = snapshot(self.root)

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
