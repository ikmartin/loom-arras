"""Library runs a person starts in the viewer: `loom serve` keeps them and runs them one at a time, beside the requests that started them.

A run can take minutes (a compile is allowed ten), and a write over the API is answered only after it is done, holding the lock every rebuild takes. So a run is a job: the request that starts it answers at once with the job, a worker thread takes the jobs in turn, and the viewer asks `GET /_api/jobs` how each is going. Jobs live in memory; a restarted server forgets them.
"""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from loom.clock import stamp
from loom.refs.build import OnProgress


@dataclass
class Step:
    """One step of a run: `waiting`, `running`, `done`, or `skipped` when it acted on nothing (offline, or nothing in it to do), with how far through the works it is and the one it is on."""

    name: str
    state: str = "waiting"
    n: int = 0
    total: int = 0
    item: str = ""


@dataclass
class Job:
    """One library run: the works it acts on (none is every work), its steps, and where it stands.

    `state` is `queued`, `running`, `done` or `failed`; `report` is what `loom library update` would print, as its JSON envelope.
    """

    id: str
    works: list[str]
    steps: list[Step]
    who: str = ""
    online: bool = False
    redo: bool = False
    kind: str = "library-update"
    state: str = "queued"
    submitted: str = field(default_factory=stamp)
    started: str = ""
    finished: str = ""
    error: str = ""
    report: dict[str, Any] | None = None

    def acts_on(self, citekey: str) -> bool:
        """Whether this run, while it waits or runs, acts on the work `citekey`."""
        return self.state in ("queued", "running") and (not self.works or citekey in self.works)

    def told(self, stage: str, item: str, n: int, total: int) -> None:
        """Follow `build_refs`' `(stage, item, n, total)`: the step named runs, and every one before it is over, done if it ran and skipped if it never did."""
        names = [s.name for s in self.steps]
        if stage not in names:
            return
        at = names.index(stage)
        for s in self.steps[:at]:
            s.state = _over(s)
        step = self.steps[at]
        step.state, step.n, step.total, step.item = "running", n, total, item

    def begin(self) -> None:
        """The run starts: gathering, which says nothing as it goes, runs from the first moment; a work step runs when it first says so."""
        self.state, self.started = "running", stamp()
        if self.steps and self.steps[0].name == "gather":
            self.steps[0].state = "running"

    def end(self, report: dict[str, Any]) -> None:
        for s in self.steps:
            s.state = _over(s)
        self.state, self.finished, self.report = "done", stamp(), report

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "works": list(self.works),
            "steps": [vars(s).copy() for s in self.steps],
            "state": self.state,
            "who": self.who,
            "online": self.online,
            "redo": self.redo,
            "submitted": self.submitted,
        }
        for name in ("started", "finished", "error"):
            if getattr(self, name):
                out[name] = getattr(self, name)
        if self.report is not None:
            out["report"] = self.report
        return out


def _over(step: Step) -> str:
    """A step's state once the run is past it: done if it ran, skipped if it never did."""
    return "done" if step.state in ("running", "done") else "skipped"


#: How a run is made: given its job and the progress callback that records into it, it returns the run's report.
Run = Callable[[Job, OnProgress], dict[str, Any]]


class Jobs:
    """The runs one server keeps, run in turn by one worker thread, started with the first.

    Parameters
    ----------
    run : callable
        Makes one run and returns its report; what it raises fails the job with its message.
    keep : int, default 20
        How many finished jobs are remembered.
    """

    def __init__(self, run: Run, keep: int = 20) -> None:
        self._run = run
        self._keep = keep
        self._lock = threading.Lock()
        self._jobs: list[Job] = []
        self._queue: queue.Queue[Job] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._count = 0

    def submit(
        self, works: list[str], steps: tuple[str, ...], *, who: str = "", online: bool = False, redo: bool = False
    ) -> Job:
        """Queue a run of `steps` over `works` (none is every work) and return its job, which the worker takes in turn."""
        with self._lock:
            self._count += 1
            job = Job(f"job-{self._count}", list(works), [Step(s) for s in steps], who=who, online=online, redo=redo)
            self._jobs.append(job)
            finished = [j for j in self._jobs if j.state in ("done", "failed")]
            for old in finished[: max(0, len(finished) - self._keep)]:
                self._jobs.remove(old)
            if self._worker is None:
                self._worker = threading.Thread(target=self._work, name="loom-jobs", daemon=True)
                self._worker.start()
        self._queue.put(job)
        return job

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        """The latest jobs, newest first, each as its JSON."""
        with self._lock:
            return [j.to_json() for j in reversed(self._jobs[-limit:])]

    def touching(self, citekey: str) -> bool:
        """Whether a queued or running job acts on the work `citekey`."""
        with self._lock:
            return any(j.acts_on(citekey) for j in self._jobs)

    def _told(self, job: Job) -> OnProgress:
        def told(stage: str, item: str, n: int, total: int) -> None:
            with self._lock:
                job.told(stage, item, n, total)

        return told

    def _work(self) -> None:
        while True:
            job = self._queue.get()
            with self._lock:
                job.begin()
            try:
                report = self._run(job, self._told(job))
            except Exception as exc:  # noqa: BLE001
                # a run that fails is the person's to read, not a dead worker: the next job still runs
                with self._lock:
                    job.state, job.finished, job.error = "failed", stamp(), str(exc) or type(exc).__name__
                continue
            with self._lock:
                job.end(report)
