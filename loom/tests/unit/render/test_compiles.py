"""The compile queue `loom serve` runs (plan 0.29.1): a burst of saves is one run more, the document being read goes first, and only the documents a change reaches are asked for."""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from types import SimpleNamespace

from loom.render.compiles import Compiles, last_of, needs_compiling
from loom.tex.runner import CompileResult


def _made(doc: str) -> CompileResult:
    return CompileResult(True, "pdflatex", Path("."), 0, pdf=Path(f"{doc}.pdf"))


def _until(check, seconds: float = 5.0) -> None:  # type: ignore[no-untyped-def]
    end = time.monotonic() + seconds
    while not check():
        assert time.monotonic() < end, "timed out"
        time.sleep(0.01)


def test_ten_saves_during_a_compile_cause_at_most_two_runs() -> None:
    gate = threading.Event()
    runs: list[str] = []
    made: list[str] = []

    def run(doc: str, started) -> CompileResult:  # type: ignore[no-untyped-def]
        runs.append(doc)
        gate.wait(5)
        return _made(doc)

    c = Compiles(run, delay=0.02, made=made.append)
    try:
        c.want(["main.tex"])
        _until(lambda: c.state()["main.tex"]["state"] == "compiling")
        for _ in range(10):
            c.want(["main.tex"])
        assert c.state()["main.tex"]["again"] is True
        gate.set()
        assert c.idle(5)
        assert runs == ["main.tex", "main.tex"]
        assert made == ["main.tex", "main.tex"]
        last = c.state()["main.tex"]
        assert last["state"] == "idle" and last["last"]["result"] == "ok"
    finally:
        c.stop()


def test_a_burst_of_asks_before_a_compile_starts_is_one_run() -> None:
    runs: list[str] = []
    c = Compiles(lambda doc, started: runs.append(doc) or _made(doc), delay=0.1)
    try:
        for _ in range(10):
            c.want(["main.tex"])
            time.sleep(0.01)
        assert c.idle(5)
        assert runs == ["main.tex"]
    finally:
        c.stop()


def test_the_document_being_read_compiles_before_the_others() -> None:
    gate = threading.Event()
    runs: list[str] = []

    def run(doc: str, started) -> CompileResult:  # type: ignore[no-untyped-def]
        runs.append(doc)
        if doc == "x.tex":
            gate.wait(5)
        return _made(doc)

    c = Compiles(run, workers=1, delay=0.01, first=lambda: "b.tex")
    try:
        c.want(["x.tex"])
        _until(lambda: runs == ["x.tex"])
        c.want(["a.tex", "b.tex"])
        time.sleep(0.05)
        gate.set()
        assert c.idle(5)
        assert runs == ["x.tex", "b.tex", "a.tex"]
    finally:
        c.stop()


def test_a_compile_that_raises_is_a_failed_run_and_the_queue_goes_on() -> None:
    def run(doc: str, started) -> CompileResult:  # type: ignore[no-untyped-def]
        if doc == "bad.tex":
            raise OSError("no such engine")
        return _made(doc)

    c = Compiles(run, delay=0.01)
    try:
        c.want(["bad.tex", "good.tex"])
        assert c.idle(5)
        state = c.state()
        assert state["bad.tex"]["last"]["result"] == "failed" and "no such engine" in state["bad.tex"]["last"]["error"]
        assert state["good.tex"]["last"]["result"] == "ok"
    finally:
        c.stop()


def test_a_run_s_last_says_whether_it_made_a_pdf_and_where_tex_stopped(tmp_path: Path) -> None:
    log = tmp_path / "main.log"
    log.write_text(
        "This is pdfTeX\n! Undefined control sequence.\nl.12 \\hlind\n               {x}\n", encoding="utf-8"
    )
    errors = ["! Undefined control sequence."]
    made = last_of(
        CompileResult(False, "pdflatex", tmp_path, 12, errors=errors, pdf=tmp_path / "main.pdf", log=log), "now"
    )
    assert (made.result, made.error, made.at) == ("errors", "! Undefined control sequence.", "l.12 \\hlind")
    none = last_of(CompileResult(False, "pdflatex", tmp_path, 12, errors=errors, log=log), "now")
    assert none.result == "failed"
    assert last_of(_made("main"), "now").result == "ok"


def _scan(root: Path) -> SimpleNamespace:
    reached = {"paper/main.tex": {"paper/main.tex": 0, "paper/ch1.tex": 0}, "notes.tex": {"notes.tex": 0}}
    return SimpleNamespace(
        quilt=SimpleNamespace(root=root),
        masters=["paper/main.tex", "notes.tex"],
        expansions={m: SimpleNamespace(reached=r) for m, r in reached.items()},
        closures={"paper/main.tex": SimpleNamespace(files=["paper/main.tex", "paper/defs.sty"])},
        base_of=lambda m: "paper" if m.startswith("paper/") else "",
    )


def test_a_change_asks_only_for_the_documents_it_reaches(tmp_path: Path) -> None:
    result = _scan(tmp_path)
    built = lambda m: tmp_path / ".loom/build" / f"{m}.pdf"  # noqa: E731
    assert needs_compiling(result, [tmp_path / "paper/ch1.tex"], built) == ["paper/main.tex"]
    assert needs_compiling(result, [tmp_path / "paper/defs.sty"], built) == ["paper/main.tex"]
    # a figure or a bibliography is read from the document's own directory or below, so one under the root may be any document's
    assert needs_compiling(result, [tmp_path / "paper/figs/plot.png"], built) == ["paper/main.tex", "notes.tex"]
    assert needs_compiling(result, [tmp_path / "notes.tex"], built) == ["notes.tex"]
    assert needs_compiling(result, [tmp_path / "README.md"], built) == []


def test_on_starting_every_document_never_compiled_or_edited_since_is_asked_for(tmp_path: Path) -> None:
    result = _scan(tmp_path)
    for f in ("paper/main.tex", "paper/ch1.tex", "paper/defs.sty", "notes.tex"):
        (tmp_path / f).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / f).write_text("x", encoding="utf-8")
    built = lambda m: tmp_path / ".loom/build" / f"{m}.pdf"  # noqa: E731
    assert needs_compiling(result, None, built) == ["paper/main.tex", "notes.tex"]
    for m in result.masters:
        built(m).parent.mkdir(parents=True, exist_ok=True)
        built(m).write_bytes(b"%PDF")
    assert needs_compiling(result, None, built) == []
    later = time.time() + 5
    os.utime(tmp_path / "paper/ch1.tex", (later, later))
    assert needs_compiling(result, None, built) == ["paper/main.tex"]
