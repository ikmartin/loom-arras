"""The compiles `loom serve` runs in the background: each document whose files changed, the one being read first, as many at once as there are workers.

A document asked for while it compiles runs once more afterwards, however often it was asked; one asked for while it waits keeps its place and waits `delay` again, so a burst of saves is one run. How each stands is what the stream and `loom status` report.
"""

from __future__ import annotations

import functools
import re
import threading
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loom.tex.runner import CompileResult, stop_run

#: Where a server keeps how its compiles stand, under the build output, for `loom status` to read; it goes when the server stops.
COMPILES_JSON = "compiles.json"

#: The line of the log that says where TeX was when it stopped: `l.12 \hlind{...}`.
_AT = re.compile(r"^l\.\d+ .*$", re.M)


@dataclass
class Last:
    """How a document's last compile ended: `ok`; `errors`, a PDF made though LaTeX reported errors; or `failed`, no PDF, so the last good one stays."""

    result: str
    ended: str
    error: str | None = None
    at: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {"result": self.result, "ended": self.ended, "error": self.error, "at": self.at}


def last_of(res: CompileResult, ended: str) -> Last:
    """What a compile's result says to a reader: whether it made a PDF, and the first error with the line TeX stopped at."""
    if res.pdf is not None and not res.errors:
        return Last("ok", ended)
    at = None
    if res.log is not None and res.errors:
        text = res.log.read_text(encoding="utf-8", errors="replace")
        cut = text.find(res.errors[0])
        found = _AT.search(text, cut if cut >= 0 else 0)
        at = found.group(0).strip()[:200] if found else None
    return Last("errors" if res.pdf is not None else "failed", ended, res.first_error[:300], at)


class Compiles:
    """A queue of document compiles served by a fixed number of worker threads, started on first use.

    Parameters
    ----------
    run : callable
        `run(doc, started)` compiles one document and returns its `CompileResult`; `started` is handed latexmk's process so `stop` can end it.
    workers : int, default 2
    delay : float, default 0.4
        Seconds a document waits after the last ask before it compiles.
    first : callable, optional
        The document the reader has open, or None; it is taken before any other that is due.
    told : callable, optional
        Called, outside the lock, after any change to how a compile stands.
    made : callable, optional
        Called with a document whose run made a PDF, from the worker that ran it.
    """

    def __init__(
        self,
        run: Callable[[str, Callable[[Any], None]], CompileResult],
        *,
        workers: int = 2,
        delay: float = 0.4,
        first: Callable[[], str | None] = lambda: None,
        told: Callable[[], None] = lambda: None,
        made: Callable[[str], None] = lambda doc: None,
    ) -> None:
        self._run = run
        self._workers = workers
        self.delay = delay
        self._first = first
        self._told = told
        self._made = made
        self._cond = threading.Condition()
        self._due: dict[str, float] = {}  # waiting, by when it may start
        self._running: dict[str, Any] = {}  # compiling, with latexmk's process once it has one
        self._again: set[str] = set()
        self._last: dict[str, Last] = {}
        self._threads: list[threading.Thread] = []
        self._stopped = False
        self.runs = 0

    def want(self, docs: Iterable[str]) -> None:
        """Ask for each of `docs` to be compiled: queued, its wait restarted, or marked to run again after the run under way."""
        changed = False
        with self._cond:
            if self._stopped:
                return
            for doc in docs:
                if doc in self._running:
                    changed |= doc not in self._again
                    self._again.add(doc)
                else:
                    changed |= doc not in self._due
                    self._due[doc] = time.monotonic() + self.delay
            while len(self._threads) < self._workers:
                t = threading.Thread(target=self._work, name=f"loom-compile-{len(self._threads)}", daemon=True)
                self._threads.append(t)
                t.start()
            self._cond.notify_all()
        if changed:
            self._told()

    def state(self) -> dict[str, Any]:
        """Each document this server has compiled or will: `state` (`queued`, `compiling` or `idle`) and its `last` run, None before one ends."""
        with self._cond:
            docs = set(self._due) | set(self._running) | set(self._last)
            out: dict[str, Any] = {}
            for doc in sorted(docs):
                state = "compiling" if doc in self._running else "queued" if doc in self._due else "idle"
                last = self._last.get(doc)
                out[doc] = {"state": state, "again": doc in self._again, "last": last.to_json() if last else None}
            return out

    def idle(self, timeout: float) -> bool:
        """Wait until nothing is queued or compiling, at most `timeout` seconds; whether it got there."""
        with self._cond:
            return self._cond.wait_for(lambda: not self._due and not self._running, timeout)

    def stop(self) -> None:
        """Take nothing more, and end every compile under way with its whole process group."""
        with self._cond:
            self._stopped = True
            self._due.clear()
            self._again.clear()
            running = [p for p in self._running.values() if p is not None]
            self._cond.notify_all()
        for proc in running:
            stop_run(proc)

    def _next(self) -> tuple[str | None, float | None]:
        """The due document to compile now, the open one before the rest, else how long until one is due."""
        now = time.monotonic()
        due = [d for d, t in self._due.items() if t <= now]
        if not due:
            return None, (min(self._due.values()) - now if self._due else None)
        try:
            first = self._first()
        except Exception:  # noqa: BLE001 -- where the reader is only orders the queue
            first = None
        return (first if first in due else min(due, key=self._due.__getitem__)), None

    def _hold(self, doc: str, proc: Any) -> None:
        with self._cond:
            stopped = self._stopped
            if not stopped:
                self._running[doc] = proc
        if stopped:
            stop_run(proc)

    def _work(self) -> None:
        from loom.clock import stamp

        while True:
            with self._cond:
                while True:
                    if self._stopped:
                        return
                    doc, wait = self._next()
                    if doc is not None:
                        break
                    self._cond.wait(wait)
                del self._due[doc]
                self._running[doc] = None
                self.runs += 1
            self._told()
            res: CompileResult | None
            held = functools.partial(self._hold, doc)
            try:
                res = self._run(doc, held)
                last = last_of(res, stamp())
            except Exception as exc:  # noqa: BLE001 -- one document's compile must not end the server's
                res = None
                last = Last("failed", stamp(), f"{type(exc).__name__}: {exc}"[:300])
            with self._cond:
                del self._running[doc]
                self._last[doc] = last
                if doc in self._again and not self._stopped:
                    self._again.discard(doc)
                    self._due[doc] = time.monotonic() + self.delay
                self._cond.notify_all()
            self._told()
            if res is not None and res.pdf is not None:
                self._made(doc)


def served(root: Path) -> dict[str, Any] | None:
    """How the compiles of the server running on `root` stand, as the stream says it; None when no server runs or its record cannot be read."""
    import json

    from loom.paths import BUILD, SERVE_JSON

    if not (root / SERVE_JSON).exists():
        return None
    try:
        state = json.loads((root / BUILD / COMPILES_JSON).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return state if isinstance(state, dict) else None


def needs_compiling(
    result: Any, changed: Iterable[Path] | None, built: Callable[[str], Path], *, pages: bool = False
) -> list[str]:
    """The documents a change reaches, or with `changed` None every document whose PDF is missing or older than what it reads, and with `pages` every document with no page beside its PDF.

    A document reaches its master, the files it inputs and its preamble's local styles; any other file it may read sits in its own directory or below (P12), so a changed file there of a kind TeX reads counts too. `built` names a document's compiled PDF; its page is `html/<stem>.html` beside it, which a server asks for when TeX4ht is installed to make one.
    """
    root = result.quilt.root
    reads = {m: _reads(result, m) for m in result.masters}
    if changed is None:
        out = []
        for m, files in reads.items():
            pdf = built(m)
            if not pdf.exists() or (pages and not (pdf.parent / "html" / f"{Path(m).stem}.html").is_file()):
                out.append(m)
                continue
            made = pdf.stat().st_mtime
            if any((root / f).exists() and (root / f).stat().st_mtime > made for f in files):
                out.append(m)
        return out
    rel = [p.relative_to(root).as_posix() for p in changed if p.is_relative_to(root)]
    out = []
    for m, files in reads.items():
        base = result.base_of(m)
        under = [r for r in rel if Path(r).suffix.lower() in TEX_READS and (not base or r.startswith(base + "/"))]
        if any(r in files for r in rel) or under:
            out.append(m)
    return out


#: Kinds of file a document may read without the scan knowing: its bibliography, figures and data. `.tex`, `.sty` and `.cls` are not among them, since the scan knows which documents read a local one.
TEX_READS = frozenset(
    (
        ".bib",
        ".bst",
        ".bbx",
        ".cbx",
        ".def",
        ".cfg",
        ".png",
        ".jpg",
        ".jpeg",
        ".pdf",
        ".eps",
        ".svg",
        ".tikz",
        ".dat",
        ".csv",
        ".txt",
    )
)


def _reads(result: Any, m: str) -> set[str]:
    exp = result.expansions.get(m)
    closure = result.closures.get(m)
    return {m, *(exp.reached if exp else ()), *(closure.files if closure else ())}
