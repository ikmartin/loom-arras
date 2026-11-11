"""Writers in separate processes at the same moment: each draws an id of its own, and nothing anyone wrote is lost.

Real processes, since that is what an in-process lock cannot cover: two shells, two `loom mcp` servers, a server beside a shell. Every process has loom imported before any is released, and `HOLD` widens the gap between reading what is taken and writing what is new, so that a writer without a lock fails every time rather than now and then.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from collections.abc import Iterable, Sequence
from pathlib import Path

import pytest

from loom.cli._common import EnvError
from loom.history.ledger import append_entry, load_history
from loom.history.steps import FreezePlan, refuse_interrupted, write_step
from loom.locks import locked
from loom.paths import ANNOTATION_LOG, NOTE_LOG
from loom.sessions import INDEX, set_active
from tests.helpers import ok
from tests.unit._quilts import demo, new_session

AGENT = "X Agent"
N = 6
#: Seconds each write waits after its reads; a writer without a lock would overlap every other one.
HOLD = 0.2

#: Holds every write open, imports what the command will need, says it is ready, and waits for the others.
RACER = """
import pathlib, sys, time
real = pathlib.Path.open
def held(self, mode="r", *args, **kwargs):
    if set(mode) & set("awx"):
        time.sleep({hold})
    return real(self, mode, *args, **kwargs)
pathlib.Path.open = held
{prepare}
gate, ready = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
ready.write_text("")
while not gate.exists():
    time.sleep(0.002)
{run}
"""
AS_LOOM = """from loom.cli import main""", """main(sys.argv[3:], prog_name="loom")"""


def racing(
    q: Path, argvs: Iterable[Sequence[str]], code: tuple[str, str] = AS_LOOM
) -> list[subprocess.CompletedProcess[str]]:
    """Run each of `argvs` in a process of its own in `q`, released together once all have started; by default each is a `loom` command line."""
    gate = q.parent / "gate"
    readies, procs = [], []
    source = RACER.format(hold=HOLD, prepare=code[0], run=code[1])
    for i, argv in enumerate(argvs):
        ready = q.parent / f"ready-{i}"
        readies.append(ready)
        procs.append(
            subprocess.Popen(
                [sys.executable, "-c", source, str(gate), str(ready), *argv],
                cwd=q,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        )
    try:
        while not all(r.exists() for r in readies):
            time.sleep(0.01)
            assert all(p.poll() is None for p in procs), [p.communicate() for p in procs if p.poll() is not None]
        gate.write_text("")
        done = [(p.communicate(timeout=300), p.returncode) for p in procs]
    finally:
        gate.unlink(missing_ok=True)
        for r in readies:
            r.unlink(missing_ok=True)
    return [subprocess.CompletedProcess(p.args, rc, out, err) for p, ((out, err), rc) in zip(procs, done, strict=True)]


def all_ok(results: Sequence[subprocess.CompletedProcess[str]]) -> None:
    said = [(r.returncode, r.stdout[-300:], r.stderr[-600:]) for r in results if r.returncode != 0]
    assert not said, said


def events(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_parallel_new_each_make_a_file_of_their_own_or_refuse_cleanly(tmp_path: Path) -> None:
    """Measured before the lock: two calls both reported success in ten trials of twelve, and one file existed."""
    q = demo(tmp_path)
    nodes = q / "drafting" / "nodes"
    before = {p.name for p in nodes.glob("*.tex")}
    results = racing(q, (["new", "definition", f"Race {i}", "--as", AGENT, "--json"] for i in range(N)))
    made: dict[str, int] = {}
    for i, r in enumerate(results):
        if r.returncode:
            # a refusal is allowed, a crash and a lost node are not
            assert r.returncode == 2 and "already exists" in r.stderr and "Traceback" not in r.stderr, r.stderr
            continue
        report = json.loads(r.stdout)
        text = (q / report["file"]).read_text(encoding="utf-8")
        assert f"[Race {i}]" in text and f"\\label{{{report['id']}}}" in text, (report, text)
        made[report["file"]] = i
    assert sum(r.returncode == 0 for r in results) == len(made), "two calls reported the same file"
    assert {p.name for p in nodes.glob("*.tex")} - before == {Path(f).name for f in made}
    # and with the lock nobody needs refusing at all
    assert len(made) == N, [r.stderr for r in results]


def test_a_new_node_never_overwrites_a_file_that_arrived_after_the_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The last line of defence, for a filesystem with no locks or a person saving at that moment: the file is created exclusively."""
    from tests.helpers import refused

    q = demo(tmp_path)
    arrived = q / "drafting" / "nodes" / "dm-0012.tex"
    real = Path.exists

    def appears(self: Path) -> bool:
        # the check says the path is free, and then a person saves a file there
        if self == arrived:
            answer = real(self)
            self.write_text("mine\n", encoding="utf-8")
            return answer
        return real(self)

    monkeypatch.setattr(Path, "exists", appears)
    refused("new", "definition", "T", "--as", AGENT, cwd=q, code=2, match="already exists")
    monkeypatch.undo()
    assert arrived.read_text(encoding="utf-8") == "mine\n"


def test_parallel_annotate_gives_every_annotation_its_own_id(tmp_path: Path) -> None:
    """Measured before the lock: duplicate ids in ten trials of twelve, and a reply to such an id cannot say which it means."""
    q = demo(tmp_path)
    sid = new_session(q)
    all_ok(racing(q, (["annotate", "dm-0002", f"race {i}", "--type", "question", "--as", AGENT] for i in range(N))))
    made = {str(e["id"]): str(e["body"]) for e in events(q / ANNOTATION_LOG) if "race " in str(e.get("body"))}
    assert sorted(made.values()) == [f"race {i}" for i in range(N)], made
    listed = json.loads(ok("ai", "annotations", "--session", sid, "--json", cwd=q).stdout)["annotations"]
    assert sorted(a["id"] for a in listed if "race " in str(a["message"])) == sorted(made)


def test_parallel_replies_and_new_annotations_draw_from_one_counter(tmp_path: Path) -> None:
    q = demo(tmp_path)
    new_session(q)
    parent = ok("annotate", "dm-0002", "the question", "--type", "question", "--as", AGENT, cwd=q).stdout.split()[0]
    calls = [["annotate", "dm-0002", f"race {i}", "--type", "note", "--as", AGENT] for i in range(2)]
    calls += [["annotate", "--reply", parent, f"race {i}", "--as", AGENT] for i in range(2, 4)]
    all_ok(racing(q, calls))
    ids = [str(e["id"]) for e in events(q / ANNOTATION_LOG) if "race " in str(e.get("body"))]
    assert len(ids) == 4 == len(set(ids)), ids


def test_parallel_note_gives_every_note_its_own_id(tmp_path: Path) -> None:
    q = demo(tmp_path)
    new_session(q)
    all_ok(racing(q, (["note", f"race {i}", "--on", "dm-0002", "--as", AGENT] for i in range(N))))
    made = {str(e["id"]): str(e["body"]) for e in events(q / NOTE_LOG) if e.get("event") == "noted"}
    assert sorted(made.values()) == [f"race {i}" for i in range(N)], made


def test_parallel_session_new_gives_every_session_its_own_id(tmp_path: Path) -> None:
    q = demo(tmp_path)
    all_ok(racing(q, (["session", "new", "--name", f"race {i}", "--no-use", "--as", AGENT] for i in range(N))))
    made = {str(e["id"]): str(e["title"]) for e in events(q / INDEX) if "race" in str(e.get("title"))}
    assert sorted(made.values()) == [f"race {i}" for i in range(N)], made


def test_writers_with_nothing_active_all_land_in_the_one_session_the_first_opens(tmp_path: Path) -> None:
    q = demo(tmp_path)
    set_active(q, None)
    before = len(events(q / INDEX))
    all_ok(racing(q, (["annotate", "dm-0002", f"race {i}", "--type", "note", "--as", AGENT] for i in range(N))))
    opened = [e for e in events(q / INDEX)[before:] if e["event"] == "created"]
    wrote = [e for e in events(q / ANNOTATION_LOG) if "race " in str(e.get("body"))]
    assert len(opened) == 1 and {e["session"] for e in wrote} == {opened[0]["id"]}, (opened, wrote)


def test_parallel_links_each_get_an_id_and_none_is_lost(tmp_path: Path) -> None:
    """A link is the one record rewritten whole, so a writer that read before another wrote would drop that link outright."""
    from loom.refs.links import read_links

    q = demo(tmp_path)
    code = (
        "from loom.refs.links import add_link",
        "add_link(pathlib.Path(sys.argv[3]), sys.argv[4], 'b', 'depends-on', 'because', 'X Agent')",
    )
    all_ok(racing(q, ([str(q), f"a{i}"] for i in range(N)), code))
    links = read_links(q)
    assert sorted(x.frm for x in links) == [f"a{i}" for i in range(N)]
    assert len({x.id for x in links}) == N, [x.id for x in links]


def test_parallel_steps_each_draw_a_number_of_their_own(tmp_path: Path) -> None:
    """A step's number and a copy's label suffix are drawn from the history, as an annotation's id is from its log."""
    q = demo(tmp_path)
    doc = "drafting/main.tex"
    calls = [["draft", doc, "--ai", f"copy{key}", "--section", key, "--as", AGENT] for key in ("dm-0010", "dm-0011")]
    calls += [["stamp", doc, "-m", f"landmark {i}"] for i in range(2)]
    all_ok(racing(q, calls))
    history = load_history(q / ".loom" / "history")
    steps = [e.step for e in history.steps()]
    assert steps == list(range(1, len(steps) + 1)), steps
    assert len(steps) >= 4 and not history.unrecorded_dirs()
    copies = [e for e in history.entries if e.action == "copy"]
    assert sorted(str(e.get("to")) for e in copies) == [".loom/copies/copydm-0010.tex", ".loom/copies/copydm-0011.tex"]
    assert len({e.get("suffix") for e in copies}) == 2
    ok("history", "verify", cwd=q)


def test_parallel_drafts_of_one_scope_leave_one_copy_and_clean_refusals(tmp_path: Path) -> None:
    """An agent document is one per scope; without the lock each saw no other copy yet, and every one was written."""
    q = demo(tmp_path)
    results = racing(q, (["draft", "drafting/main.tex", "--ai", f"copy{i}", "--as", AGENT] for i in range(4)))
    won = [r for r in results if r.returncode == 0]
    lost = [r for r in results if r.returncode != 0]
    assert len(won) == 1 and all(r.returncode == 2 and "overlaps" in r.stderr for r in lost), results
    assert len(list((q / ".loom" / "copies").glob("copy*.tex"))) == 1


def test_parallel_new_and_fork_draw_from_one_counter(tmp_path: Path) -> None:
    """A fork writes a node file named by its new id, as `new` does, so the two take the same lock."""
    q = demo(tmp_path)
    calls = [["new", "definition", f"Race {i}", "--as", AGENT, "--json"] for i in range(2)]
    calls += [["fork", key, "--in", "drafting/main.tex", "--json"] for key in ("dm-0001", "dm-0002")]
    results = racing(q, calls)
    all_ok(results)
    drawn = [json.loads(r.stdout)["id"] for r in results[:2]] + [json.loads(r.stdout)["new"] for r in results[2:]]
    assert len(set(drawn)) == 4, drawn
    assert all((q / "drafting" / "nodes" / f"{d}.tex").is_file() for d in drawn), drawn


def test_a_step_planned_from_a_history_that_has_moved_on_is_refused_and_writes_nothing(tmp_path: Path) -> None:
    """The viewer's acts plan from a history read before any lock; its number is already in what they would record."""
    q = demo(tmp_path)
    hist = q / ".loom" / "history"
    planned = load_history(hist)
    write_step(load_history(hist), "stamp", "first", FreezePlan(), "someone")
    ledger = (hist / "ledger.jsonl").read_bytes()
    dirs = sorted(p.name for p in hist.iterdir())
    with pytest.raises(EnvError, match="run this again"):
        write_step(planned, "stamp", "second", FreezePlan(), "someone")
    assert (hist / "ledger.jsonl").read_bytes() == ledger and sorted(p.name for p in hist.iterdir()) == dirs


def test_a_step_being_written_is_not_taken_for_an_interrupted_one(tmp_path: Path) -> None:
    """Its directory exists before its line, and the refusal says to remove that directory: said of a live step, that would destroy it."""
    q = demo(tmp_path)
    hist = q / ".loom" / "history"
    stale = load_history(hist)
    n = stale.next_step()
    started = threading.Event()

    def writing() -> None:
        with locked(stale.ledger):
            (hist / f"{n:04d}-other").mkdir()
            started.set()
            time.sleep(0.2)
            append_entry(hist, "stamp", {"step": n, "dir": f"{n:04d}-other"}, "someone")

    t = threading.Thread(target=writing)
    t.start()
    assert started.wait(30)
    try:
        refuse_interrupted(stale)
    finally:
        t.join()
