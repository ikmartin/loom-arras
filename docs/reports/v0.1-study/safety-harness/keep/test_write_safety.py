"""Writes to the person's files hold up over sequences of acts: seeded runs of suggest, hand edits, Keep, Keep all, Discard and their undo, a tick and a setting, through the write API's handler on a copy of the synthetic quilt, each act checked against the invariants loom promises.

The invariants, checked after every act loom performs: only the files the act names change; the same request sent again changes nothing; every suggested edit's text (each carries a unique word) stands at most once, and a ready one is never already in its file; text the person typed is in a file or in a kept text; and the bytes a write replaced are kept in the history first. The `KNOWN` tests pin damage found by the v0.1 safety study and are expected to fail until it is fixed.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import shutil
from pathlib import Path
from typing import Any

import pytest

import loom

QUILTS = Path(loom.__file__).resolve().parents[2] / "tests" / "quilts"
AGENT = "Agent Smith"
WORDS = "orbit group action finite widget lemma bound measure compact dense closed map kernel image quotient series limit converges uniformly hence suppose every exists integral norm space basis linear operator".split()


# ---- the quilt and the person -----------------------------------------------------------------------------------


@pytest.fixture
def q(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A copy of the synthetic quilt, edits tracked, with a Markdown task list; the person is `Pat`, and no agent marker is set."""
    for m in ("AI_AGENT", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CODEX_SANDBOX", "CURSOR_AGENT", "GEMINI_CLI"):
        monkeypatch.delenv(m, raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    from loom.scan.quilt import save_author

    save_author("Pat")
    root = tmp_path / "q"
    shutil.copytree(QUILTS / "synthetic", root, ignore=shutil.ignore_patterns("build", ".git"))
    (root / "tasks.md").write_text("# Tasks\n\n- [ ] read the first proof again\n- [x] write the second answer\n", encoding="utf-8")
    from loom.config_edit import set_values
    from loom.scan.quilt import load_quilt

    try:
        set_values(load_quilt(root), {"review.track_edits": True})
    except Exception:  # noqa: BLE001 -- a loom from before edit tracking refuses the table
        pass
    call(root, "change-keep", {"all": True})  # the first look
    return root


def call(root: Path, endpoint: str, body: dict[str, Any]) -> dict[str, Any]:
    from loom.render.api import ApiError, handle

    try:
        return handle(root, endpoint, dict(body))
    except ApiError as exc:
        return {"error": exc.code}


def suggest(root: Path, key: str, new: str, *more: str) -> str | None:
    from click.testing import CliRunner

    from loom.cli import main

    res = CliRunner().invoke(main, ["suggest", key, "--with", new, *more, "--as", AGENT, "--json", "--quilt", str(root)], env={"AI_AGENT": "1"})
    return str(json.loads(res.stdout)["edit"]) if res.exit_code == 0 else None


def files(root: Path) -> dict[str, bytes]:
    """Every file outside `.loom/`, as bytes."""
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file() and ".loom" not in p.relative_to(root).parts}


def scan(root: Path) -> Any:
    from loom.scan.quilt import load_quilt
    from loom.scan.scan import scan as scan_

    return scan_(load_quilt(root))


def waiting(root: Path, result: Any = None) -> list[Any]:
    from loom.pending import pending

    return pending(result or scan(root), "Pat")


def kept_in_history(root: Path, data: bytes) -> bool:
    text = data.decode("utf-8")
    p = root / ".loom/history/texts" / f"{hashlib.sha256(text.encode()).hexdigest()}.md"
    return p.is_file() and p.read_bytes() == data


# ---- the invariants ---------------------------------------------------------------------------------------------


class Run:
    """One sequence: what the harness filed, typed and expects."""

    def __init__(self, root: Path, seed: int) -> None:
        self.root = root
        self.rng = random.Random(seed)
        self.markers: dict[str, str] = {}  # edit id -> its unique word
        self.typed: set[str] = set()
        self.n = 0
        self.problems: list[str] = []
        self.trail: list[str] = []  # what was done, for the failure message

    def word(self, kind: str) -> str:
        self.n += 1
        return f"{kind}{''.join(chr(97 + (self.n * 7 + i * 3) % 26) for i in range(3))}{self.n:03d}x"

    def check(self, act: str, before: dict[str, bytes], allowed: set[str]) -> dict[str, bytes]:
        from loom.records.edits import replay

        after = files(self.root)
        changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
        if not changed <= allowed:
            self.problems.append(f"{act}: changed {sorted(changed - allowed)}, which it does not name")
        for k in changed & set(before):
            if k == "config.toml":
                continue  # no version is kept of the config (SAFE-10): test_saving_settings_keeps_the_config_first
            if before[k] and not kept_in_history(self.root, before[k]):
                self.problems.append(f"{act}: the text of {k} before the write is kept nowhere")
        blob = b"\n".join(after.values()).decode("utf-8", "replace")
        for mk in sorted(self.typed):
            if mk not in blob and not any(mk.encode() in p.read_bytes() for p in (self.root / ".loom/history").rglob("*.md")):
                self.problems.append(f"{act}: the person's {mk} is gone and kept nowhere")
        states = {p.id: p.state for p in waiting(self.root) if p.kind == "suggested"}
        status = {e.id: e.status for e in replay(self.root)[0]}
        for eid, mk in self.markers.items():
            n = blob.count(mk)
            if n > 1:
                self.problems.append(f"{act}: {eid}'s text stands {n} times")
            if status.get(eid) == "open" and states.get(eid) == "ready" and n:
                self.problems.append(f"{act}: {eid} is ready to keep while its text already stands")
        return after

    def press(self, endpoint: str, body: dict[str, Any], allowed: set[str]) -> None:
        """Send a request, check it, send it again and check that nothing more changed."""
        before = files(self.root)
        call(self.root, endpoint, body)
        after = self.check(endpoint, before, allowed)
        call(self.root, endpoint, body)
        if files(self.root) != after:
            self.problems.append(f"{endpoint} {body} sent twice changed the files again")


def sentence(rng: random.Random, n: int, mark: str) -> str:
    ws = [rng.choice(WORDS) for _ in range(n)]
    ws.insert(rng.randrange(n + 1), mark)
    return " ".join(ws)


def blocks(root: Path, result: Any) -> list[Any]:
    return [n for n in result.nodes.values() if n.kind in ("environment", "proof") and not n.file.startswith(".loom/") and any(result.document_role(d) == "person" for d in n.reached_by or [])]


def quote_in(result: Any, node: Any, rng: random.Random) -> str | None:
    """A run of two to four words standing once in the block's own text, inside it (never its `\\begin` or `\\end`)."""
    from loom.records.edits import body_span
    from loom.records.selectors import find_quote
    from loom.records.store import Records

    own = Records.own_pieces(result, node)[0]
    a, b = body_span(own)
    toks = [m for m in re.finditer(r"\S+", own) if a <= m.start() and m.end() <= b and "\\" not in m.group() and "%" not in m.group()]
    for _ in range(20):
        if len(toks) < 3:
            return None
        i = rng.randrange(len(toks) - 1)
        quote = own[toks[i].start() : toks[min(len(toks) - 1, i + rng.randint(1, 3))].end()]
        if len(find_quote(own, quote)) == 1 and not quote.startswith("-"):
            return quote
    return None


def step(run: Run) -> None:
    """One act drawn from the run's generator."""
    rng, root = run.rng, run.root
    op = rng.choices(["suggest", "section", "type", "edit", "keep", "keep_all", "discard", "undo_discard", "tick", "setting"], [6, 2, 2, 4, 6, 2, 2, 1, 1, 1])[0]
    run.trail.append(op)
    if run.typed:  # what the person deleted in their own last act was theirs to delete; loom's acts are checked as they happen
        blob = b"\n".join(files(root).values())
        run.typed = {w for w in run.typed if w.encode() in blob}
    if op in ("suggest", "section"):
        if op == "section":  # the hwk1 shape: a problem and its answer after \maketitle
            mk = run.word("sm")
            new = f"\\section*{{Problem {mk}}}\n{sentence(rng, 24, 'and')}\n\\begin{{proof}}[Answer]\n{sentence(rng, 24, 'so')}\n\\end{{proof}}"
            eid = suggest(root, "drafting/main.tex", new, "--quote", "\\maketitle", "--after")
        else:
            result = scan(root)
            node = rng.choice(blocks(root, result))
            quote = quote_in(result, node, rng)
            mk = run.word("sg")
            new = sentence(rng, rng.choice([3, 6, 30]), mk)
            where = rng.choice(["--after", "--before", None]) if quote else rng.choice(["--after", "--before"])
            more = (["--quote", quote] if quote else []) + ([where] if where else [])
            eid = suggest(root, node.key, new, *more)
            run.trail[-1] += f" {node.key} {more} {new[:40]!r}"
        if eid:
            run.markers[eid] = mk
        run.check("suggest", files(root), set())
        return
    if op == "type":  # the person writes an open suggestion of twenty words or more in by hand, then works inside it
        from loom.records.edits import Placed, compose, find

        result = scan(root)
        opens = [e for eid in run.markers if (e := find(root, eid)) and e.status == "open" and len(e.with_text.split()) >= 20]
        placed = [(e, pl) for e, pl in compose(result, opens) if isinstance(pl, Placed)]
        if placed:
            e, pl = rng.choice(placed)
            text = result.files[pl.file].text
            mine = run.word("pt")
            typed = pl.text.replace(run.markers[e.id], f"{run.markers[e.id]} {mine}")
            (root / pl.file).write_text(text[: pl.at[0]] + typed + text[pl.at[1] :], encoding="utf-8")
            run.typed.add(mine)
            run.trail[-1] += f" {e.id} by hand into {pl.file}, with {mine} inside"
        return
    if op == "edit":  # the person's own words somewhere in a block
        node = rng.choice(blocks(root, scan(root)))
        text = (root / node.file).read_text(encoding="utf-8")
        at = text.find(" ", node.start + (node.end - node.start) // 2, node.end)
        if at > 0:
            mine = run.word("pt")
            (root / node.file).write_text(text[:at] + f" {mine}" + text[at:], encoding="utf-8")
            run.typed.add(mine)
            run.trail[-1] += f" {mine} into {node.key}"
        return
    pend = waiting(root)
    sug = [p for p in pend if p.kind == "suggested"]
    if op == "keep" and sug:
        p = rng.choice(sug)
        run.trail[-1] += f" {p.id} ({p.state})"
        run.press("change-keep", {"changes": [p.id]}, {p.path})
    elif op == "keep_all":
        run.press("change-keep", {"all": True}, {p.path for p in sug})
    elif op == "discard" and pend:
        p = rng.choice(pend)
        run.trail[-1] += f" {p.id} ({p.kind})"
        run.press("change-discard", {"changes": [p.id]}, {p.path} if p.kind == "edit" else set())
    elif op == "undo_discard":
        from loom.records.edits import replay

        gone = [e.id for e in replay(root)[0] if e.status == "discarded" and e.id in run.markers]
        if gone:
            before = files(root)
            call(root, "change-discard", {"changes": [rng.choice(gone)], "undo": True})
            run.check("undo of a discard", before, set())
    elif op == "tick":
        from loom.tasks import items

        t = items((root / "tasks.md").read_text(encoding="utf-8"))[0]
        before = files(root)
        call(root, "file-tick", {"path": "tasks.md", "task": t.id, "done": not t.done})
        run.check("tick", before, {"tasks.md"})
        t2 = items((root / "tasks.md").read_text(encoding="utf-8"))[0]
        call(root, "file-tick", {"path": "tasks.md", "task": t2.id, "done": t.done})
        if files(root)["tasks.md"] != before["tasks.md"]:
            run.problems.append("tick then untick did not give back tasks.md")
    elif op == "setting":
        before = files(root)
        call(root, "settings-save", {"changes": {"quilt.name": f"widgets {rng.randrange(99)}"}})
        run.check("settings", before, {"config.toml"})


# ---- the tests --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("seed", range(4))
def test_a_seeded_sequence_of_writes_keeps_the_persons_text(q: Path, seed: int) -> None:
    run = Run(q, seed)
    for _ in range(16):
        step(run)
        assert not run.problems, (run.problems, run.trail)


def test_a_kept_edit_that_opens_a_section_is_written_once_however_often_keep_is_pressed(q: Path) -> None:
    """1ac44c5e: a kept suggestion that opened a section read as not taken, and each press pasted it again."""
    run = Run(q, 0)
    new = "\\section*{Preface}\nThese notes collect what is known about widgets and gadgets.\n\\begin{proof}[Answer]\nNone yet.\n\\end{proof}"
    eid = suggest(q, "drafting/main.tex", new, "--quote", "\\maketitle", "--after")
    run.markers[eid] = "These notes collect"
    run.press("change-keep", {"changes": [eid]}, {"drafting/main.tex"})
    assert not run.problems, run.problems


def test_text_written_in_and_worked_inside_is_not_written_again(q: Path) -> None:
    """2e106a45: the person wrote a long suggestion in and worked inside it; Keep pasted it a second time."""
    run = Run(q, 0)
    new = "These notes collect what is known about widgets, what each lemma rests on, and which questions stay open for a reader to settle on a later pass."
    eid = suggest(q, "drafting/main.tex", new, "--quote", "\\maketitle", "--after")
    run.markers[eid] = "These notes collect"
    main = q / "drafting/main.tex"
    main.write_text(main.read_text().replace("\\maketitle", "\\maketitle\n" + new.replace("rests on,", "rests on, with a sketch,")), encoding="utf-8")
    run.press("change-keep", {"changes": [eid]}, {"drafting/main.tex"})
    assert not run.problems, run.problems


# Damage the v0.1 safety study found (docs/reports/v0.1-study/raw/safety.md); each test passes once its finding is fixed.


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="SAFE-1: text placed after a block's \\end is never read as taken")
def test_an_edit_placed_after_its_blocks_end_is_not_written_twice(q: Path) -> None:
    node = q / "drafting/nodes/sy-000A.tex"
    new = "A gadget with three points has one fixed point."
    eid = suggest(q, "sy-000A", new, "--quote", "\\end{remark}", "--after")
    node.write_text(node.read_text().replace("\\end{remark}", "\\end{remark} " + new), encoding="utf-8")  # written in by hand
    call(q, "change-keep", {"changes": [eid]})
    assert node.read_text().count(new) == 1


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="SAFE-1: a short text written in and touched is not read as taken")
def test_a_short_edit_written_in_and_touched_is_not_written_twice(q: Path) -> None:
    node = q / "drafting/nodes/sy-000A.tex"
    eid = suggest(q, "sy-000A", "Each swap fixes nothing.", "--quote", "with the swap.", "--after")
    node.write_text(node.read_text().replace("with the swap.", "with the swap. Each swap fixes no point."), encoding="utf-8")
    call(q, "change-keep", {"changes": [eid]})
    assert node.read_text().count("Each swap fixes") == 1


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="SAFE-2: Keep writes the file from its scan, so a save made meanwhile is lost")
def test_a_save_made_while_keep_runs_is_not_lost(q: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import loom.history.acts as acts

    node = q / "drafting/nodes/sy-000A.tex"
    eid = suggest(q, "sy-000A", "Each swap fixes nothing.", "--quote", "with the swap.", "--after")
    real = acts.keep_versions

    def and_a_save(*args: Any, **kw: Any) -> Any:
        out = real(*args, **kw)
        node.write_text(node.read_text() + "% a line the editor saved\n", encoding="utf-8")
        return out

    monkeypatch.setattr(acts, "keep_versions", and_a_save)
    call(q, "change-keep", {"changes": [eid]})
    assert "a line the editor saved" in node.read_text()


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="SAFE-4: an edit on a key named by place goes into another block when the blocks cannot be told apart")
def test_an_edit_on_a_block_named_by_place_stays_on_that_block(q: Path) -> None:
    main = q / "drafting/main.tex"
    text = main.read_text()
    empty = "\\begin{proof}[Answer]\n\\end{proof}\n"
    main.write_text(text.replace("\\end{document}", f"\\section*{{One}}\n{empty}\\section*{{Two}}\n{empty}\\end{{document}}"), encoding="utf-8")
    result = scan(q)
    keys = sorted((n.start, k) for k, n in result.nodes.items() if n.file == "drafting/main.tex" and k.startswith("drafting/main.tex#proof:"))
    last = keys[-1][1]  # the empty proof under Two
    a = suggest(q, last, "The answer to two. ANSWER-TWO")
    b = suggest(q, "drafting/main.tex", "\\section*{Zero}\n" + empty.strip(), "--quote", "\\maketitle", "--after")
    call(q, "change-keep", {"changes": [b]})
    call(q, "change-keep", {"changes": [a]})
    after = main.read_text()
    assert after.index("ANSWER-TWO") > after.index("\\section*{Two}")


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="SAFE-6: Keep rewrites the file from the scan's normalised text")
def test_keep_leaves_line_endings_alone(q: Path) -> None:
    node = q / "drafting/nodes/sy-000A.tex"
    node.write_bytes(node.read_bytes().replace(b"\n", b"\r\n"))
    call(q, "change-keep", {"all": True})
    eid = suggest(q, "sy-000A", "Each swap fixes nothing.", "--quote", "with the swap.", "--after")
    call(q, "change-keep", {"changes": [eid]})
    assert node.read_bytes().count(b"\r\n") == 3


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="SAFE-10: saving Settings keeps nothing of config.toml first, and leaves it mode 0600")
def test_saving_settings_keeps_the_config_first(q: Path) -> None:
    config = q / "config.toml"
    old = config.read_bytes()
    call(q, "settings-save", {"changes": {"quilt.name": "widgets"}})
    call(q, "settings-save", {"changes": {"quilt.name": "gadgets"}})
    assert kept_in_history(q, config.read_bytes().replace(b"gadgets", b"widgets")) and kept_in_history(q, old)
    assert config.stat().st_mode & 0o777 == 0o644


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="SAFE-5: restore overwrites a file the document no longer reaches without keeping it")
def test_restoring_a_version_keeps_every_file_it_overwrites(q: Path) -> None:
    results, node = q / "drafting/sections/results.tex", q / "drafting/nodes/sy-0006.tex"
    results.write_text(results.read_text().replace("\\input{nodes/sy-0006}", "% \\input{nodes/sy-0006}"), encoding="utf-8")
    node.write_text(node.read_text() + "% MY-NEW-PARAGRAPH\n", encoding="utf-8")
    kept = node.read_bytes()
    call(q, "history-restore", {"document": "drafting/main.tex", "version": "widgets-v1"})
    assert "MY-NEW-PARAGRAPH" in node.read_text() or kept_in_history(q, kept)


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="SAFE-7: discarding an in-place change in a CRLF file splices at offsets of another text")
def test_discarding_an_agents_edit_in_a_crlf_file_gives_back_its_bytes(q: Path) -> None:
    f = q / "drafting/sections/appendix.tex"
    f.write_bytes(f.read_bytes().replace(b"\n", b"\r\n"))
    call(q, "change-keep", {"all": True})
    original = f.read_bytes()
    text = original.decode()
    at = text.rfind("the")
    f.write_bytes((text[:at] + "AGENT-WORDS" + text[at + 3 :]).encode())
    ids = [c.id for c in waiting(q) if c.kind == "edit" and c.path == "drafting/sections/appendix.tex"]
    call(q, "change-discard", {"changes": ids})
    assert f.read_bytes() == original


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="SAFE-8: an insertion whose words stand elsewhere in its block reads as taken, and Keep writes nothing")
def test_keeping_an_insertion_writes_it_even_when_its_words_stand_elsewhere_in_the_block(q: Path) -> None:
    node = q / "drafting/nodes/sy-000A.tex"
    eid = suggest(q, "sy-000A", "\\cite[Theorem 2.1]{Kre99}", "--quote", "Gadgets exist:", "--after")
    call(q, "change-keep", {"changes": [eid]})
    assert node.read_text().count("\\cite[Theorem 2.1]{Kre99}") == 2
