"""Library runs the viewer starts: one at a time, in order, each step followed as it moves, a failure kept with its message."""

from __future__ import annotations

import threading
import time
from typing import Any

from loom.jobs import Job, Jobs, Step
from loom.refs.build import STEPS, WORK_STEPS


def _settle(jobs: Jobs, timeout: float = 5.0) -> list[dict[str, Any]]:
    """The jobs once none is queued or running."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        now = jobs.recent()
        if all(j["state"] in ("done", "failed") for j in now):
            return now
        time.sleep(0.01)
    raise AssertionError(f"jobs did not settle: {jobs.recent()}")


def test_told_moves_each_step_and_says_which_before_it_ran() -> None:
    job = Job("job-1", ["Kre99"], [Step(s) for s in WORK_STEPS])
    job.begin()
    job.told("fetch", "Kre99", 1, 1)
    # look-up never said it ran (offline, or nothing to look up): skipped, not done
    assert [s.state for s in job.steps] == ["skipped", "running", "waiting", "waiting"]
    assert (job.steps[1].n, job.steps[1].total, job.steps[1].item) == (1, 1, "Kre99")
    job.told("map", "Kre99", 1, 1)
    assert [s.state for s in job.steps] == ["skipped", "done", "skipped", "running"]
    # a stage the run does not take is ignored
    job.told("gather", "", 1, 1)
    assert [s.state for s in job.steps] == ["skipped", "done", "skipped", "running"]
    job.end({"verdict": "ok"})
    assert [s.state for s in job.steps] == ["skipped", "done", "skipped", "done"] and job.state == "done"


def test_gathering_runs_from_the_start_of_a_run_on_every_work() -> None:
    job = Job("job-1", [], [Step(s) for s in STEPS])
    job.begin()
    assert job.steps[0].state == "running" and job.state == "running"


def test_runs_go_one_at_a_time_in_order_and_each_is_followed() -> None:
    seen: list[str] = []
    running = threading.Lock()

    def run(job: Job, told: Any) -> dict[str, Any]:
        # two runs at once would find the lock held
        assert running.acquire(blocking=False), "two runs overlapped"
        try:
            seen.append(job.id)
            for name in WORK_STEPS:
                told(name, job.works[0] if job.works else "", 1, 1)
                time.sleep(0.005)
            return {"verdict": f"ran {job.id}"}
        finally:
            running.release()

    jobs = Jobs(run)
    first = jobs.submit(["Kre99"], WORK_STEPS, who="A. Author")
    second = jobs.submit([], STEPS, online=True)
    done = _settle(jobs)
    assert seen == [first.id, second.id]
    # newest first, each finished with every step done and its report
    assert [j["id"] for j in done] == [second.id, first.id]
    assert all(j["state"] == "done" for j in done)
    assert all(s["state"] == "done" for s in done[1]["steps"])
    assert done[1]["report"] == {"verdict": f"ran {first.id}"} and done[1]["who"] == "A. Author"
    assert done[0]["online"] is True and done[0]["works"] == []


def test_a_run_that_raises_is_failed_with_its_message_and_the_next_still_runs() -> None:
    def run(job: Job, _told: Any) -> dict[str, Any]:
        if job.works == ["bad"]:
            raise RuntimeError("the paper would not compile")
        return {"verdict": "ok"}

    jobs = Jobs(run)
    jobs.submit(["bad"], WORK_STEPS)
    jobs.submit(["good"], WORK_STEPS)
    good, bad = _settle(jobs)
    assert bad["state"] == "failed" and bad["error"] == "the paper would not compile"
    assert good["state"] == "done"


def test_touching_holds_while_a_run_waits_or_runs_and_every_work_counts_for_a_run_on_all() -> None:
    release = threading.Event()

    def run(job: Job, _told: Any) -> dict[str, Any]:
        release.wait(5)
        return {}

    jobs = Jobs(run)
    jobs.submit(["Kre99"], WORK_STEPS)
    jobs.submit([], STEPS)
    assert jobs.touching("Kre99") and jobs.touching("Man12")
    release.set()
    _settle(jobs)
    assert not jobs.touching("Kre99") and not jobs.touching("Man12")


def test_finished_jobs_past_the_keep_are_forgotten() -> None:
    jobs = Jobs(lambda job, told: {}, keep=2)
    for n in range(4):
        jobs.submit([f"W{n}"], WORK_STEPS)
        _settle(jobs)
    # the oldest finished one goes when the next is submitted; the newest is kept even before it runs
    assert [j["works"] for j in jobs.recent()] == [["W3"], ["W2"], ["W1"]]


def test_update_reports_each_step_as_it_moves(tmp_path: Any) -> None:
    """What a run follows: `refs.update.update` tells its progress per step and per work, as `build_refs` does, and says what it made."""
    from loom.refs.update import update
    from loom.scan.quilt import load_quilt
    from tests.unit._quilts import demo

    q = demo(tmp_path)
    told: list[tuple[str, str]] = []
    built = update(
        load_quilt(q), ("Calloway14",), steps=WORK_STEPS, progress=lambda s, item, n, total: told.append((s, item))
    )
    # offline, as the demo is, look-up and fetch act on nothing and say nothing; extraction and mapping each say so
    stages = [s for s, _ in told]
    assert stages == [s for s in WORK_STEPS if s in stages] and {"extract", "map"} <= set(stages)
    assert {item for _, item in told} == {"Calloway14"}
    assert built.report().to_json()["verdict"]
