"""The AI layer (book 11): layout and vendor files, upgrade, orientation, runs and their logs, promotion, the outside-writes check, and threads in the manifest."""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from pathlib import Path

import pytest

from loom.ai.layout import MODES, TARGET_MODES
from tests.helpers import exits, ok, refused
from tests.unit._quilts import demo

FIXED = {"LOOM_FIXED_TIME": "2026-09-16T14:02:00Z"}


def bare(tmp_path: Path, *flags: str) -> Path:
    """The demo without its AI layer, annotations or sessions, then `loom ai init FLAGS`: the layer these tests read is the one they made, and the sessions they count are their own."""
    q = demo(tmp_path)
    shutil.rmtree(q / "ai")
    for rel in ("CLAUDE.md", "AGENTS.md"):
        (q / rel).unlink(missing_ok=True)
    shutil.rmtree(q / ".claude", ignore_errors=True)
    shutil.rmtree(q / "annotations", ignore_errors=True)  # the log lives at the quilt root, not under ai/
    shutil.rmtree(q / ".loom" / "sessions", ignore_errors=True)
    ok("ai", "init", *flags, cwd=q)
    return q


def test_ai_init_layout_and_vendor_files(tmp_path: Path) -> None:
    q = bare(tmp_path)
    for rel in ("ai/README.md", "ai/orientation.md", "ai/.loom-modes-version", "CLAUDE.md", "AGENTS.md"):
        assert (q / rel).is_file(), rel
    assert {p.stem for p in (q / "ai" / "modes").glob("*.md")} == set(MODES)
    root_text = (q / "CLAUDE.md").read_text()
    assert (
        root_text == (q / "AGENTS.md").read_text() and "loom ai orient" in root_text and ".loom/sessions/" in root_text
    )
    assert "# Orientation: working in a quilt" in (q / "ai" / "orientation.md").read_text()
    # what agents may run is written for every tool, whichever the person uses (DR-283)
    assert (q / ".claude" / "settings.json").is_file() and (q / ".codex" / "rules" / "loom.rules").is_file()
    refused("ai", "init", cwd=q, code=2, match="loom upgrade")


def test_root_files_carry_one_line_and_keep_the_authors(tmp_path: Path) -> None:
    """CLAUDE.md is the author's file with one line of loom's in it; an upgrade must not take it over (DR-151)."""
    from loom.ai.layout import CLAUDE_LINE

    q = bare(tmp_path)
    for name in ("CLAUDE.md", "AGENTS.md"):
        assert (q / name).read_text().splitlines().count(CLAUDE_LINE) == 1
    mine = "\n## This project\n\nNever touch canon/ without asking.\n"
    (q / "CLAUDE.md").write_text((q / "CLAUDE.md").read_text() + mine)
    ok("upgrade", cwd=q)
    after = (q / "CLAUDE.md").read_text()
    assert after.count(CLAUDE_LINE) == 1 and "Never touch canon/ without asking." in after

    # an earlier version of loom's line is replaced where it stands, not appended beside
    (q / "AGENTS.md").write_text("This directory is a quilt managed by loom. Old wording.\n\nMine.\n")
    ok("upgrade", cwd=q)
    agents = (q / "AGENTS.md").read_text()
    assert agents.count(CLAUDE_LINE) == 1 and "Old wording" not in agents and "Mine." in agents


def test_ai_init_permissions_generated(tmp_path: Path) -> None:
    """The generated settings let the agent edit its session and `build/`, in `Edit` rules only; what it is denied is test_the_allow_list_and_the_permission_file_cannot_disagree."""
    q = bare(tmp_path)
    data = json.loads((q / ".claude" / "settings.json").read_text())
    deny = data["permissions"]["deny"]
    allow = data["permissions"]["allow"]
    # `.loom` is not denied wholesale: the session an agent writes in lives under it (plan 0.13 §5)
    assert "Edit(/.loom/sessions/**)" in allow and "Edit(/build/**)" in allow
    # Claude Code matches only `Edit` rules against paths; a `Write` rule is ignored and says so on every start
    assert not any(r.startswith("Write(") for r in allow + deny)


def test_ai_init_skills_generated_pointer_only(tmp_path: Path) -> None:
    q = bare(tmp_path, "--skills")
    blocks = (q / "ai" / "rules.md").read_text()
    block_names = re.findall(r"^- \[([a-z-]+)\]", blocks, re.M)
    assert len(block_names) > 20
    for mode in MODES:
        stub = q / ".claude" / "skills" / f"loom-{mode}" / "SKILL.md"
        text = stub.read_text()
        assert text.startswith("---\n") and f"name: loom-{mode}\n" in text and "description: " in text
        assert f"ai/modes/{mode}.md" in text and "loom ai orient" in text
        assert len(text.splitlines()) < 12
        for name in block_names:
            assert f"[{name}]" not in text, (mode, name)  # a stub points at the mode file; it never duplicates it
        assert ("$ARGUMENTS" in text) == (mode in TARGET_MODES)
    for mode in TARGET_MODES:
        cmd = (q / ".claude" / "commands" / f"{mode}.md").read_text()
        assert "$ARGUMENTS" in cmd and f"ai/modes/{mode}.md" in cmd and "argument-hint" in cmd
    assert not (q / ".claude" / "commands" / "question.md").exists()
    # brainstorm takes no single target, so it gets a skill and no slash command (plan 0.2 §3.4)
    assert (q / ".claude" / "skills" / "loom-brainstorm" / "SKILL.md").exists()
    assert not (q / ".claude" / "commands" / "brainstorm.md").exists()
    for name in ("candidates", "dead-ends", "known-results", "open-questions"):
        assert f"- [{name}]" in blocks


def test_modes_templates_present_and_contracts_listed(tmp_path: Path) -> None:
    q = bare(tmp_path)
    assert len(MODES) == 9  # rules.md is not a mode
    assert not (q / "ai" / "modes" / "blocks.md").exists()
    rules = (q / "ai" / "rules.md").read_text()
    assert rules.startswith("# Standing rules, contracts, and blocks") and "## Never" in rules
    for mode in MODES:
        text = (q / "ai" / "modes" / f"{mode}.md").read_text()
        assert text.startswith(f"# Mode: {mode}\n\n## Before you begin\n")
        assert "## Checklist" in text
        # the write policy is stated in every template, so a mode read without the orientation still carries it; it names the session's directory, not $LOOM_SESSION, which is set only for a turn `loom serve` launches
        assert re.search(r"^- \[ \] Nothing was written outside your session's directory\.", text, re.M)
        assert "$LOOM_SESSION" not in text
        if mode not in ("quick",):
            # the account of the work goes in the chat, the one transcript
            assert "## Output" in text and "loom session say" in text


def test_upgrade_preserves_edited_modes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    q = bare(tmp_path)
    referee = q / "ai" / "modes" / "referee.md"
    referee.write_text(referee.read_text() + "\n## House rule\nAlways check the dimension count.\n")
    audit = q / "ai" / "modes" / "audit.md"
    original_audit = audit.read_text()
    orientation = q / "ai" / "orientation.md"
    orientation.write_text("stale orientation\n")
    r = ok("upgrade", cwd=q)
    assert "kept ai/modes/referee.md (edited)" in r.output
    assert "House rule" in referee.read_text()  # untouched
    assert audit.read_text() == original_audit
    # the orientation is the first file an author tailors, so an edited one is kept like a mode file (DR-170)
    assert "kept ai/orientation.md (edited)" in r.output
    assert orientation.read_text() == "stale orientation\n"
    assert "# Orientation: working in a quilt" in (q / "ai" / "orientation.md.new").read_text()
    versions = (q / "ai" / ".loom-modes-version").read_text()
    assert "referee.md" in versions and "audit.md" in versions
    # the shipped text has not changed in this test, so no .new is written; simulate a changed shipped version
    import loom.ai.layout as layout

    shipped = layout.tracked_docs()
    shipped["ai/modes/referee.md"] = shipped["ai/modes/referee.md"] + "\n## New shipped section\n"
    monkeypatch.setattr(layout, "tracked_docs", lambda: shipped)
    r2 = ok("upgrade", cwd=q)
    assert "referee.md.new" in r2.output
    assert (
        "House rule" in referee.read_text()
        and "New shipped section" in (q / "ai" / "modes" / "referee.md.new").read_text()
    )


def test_upgrade_refreshes_an_unedited_mode_the_first_time(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """What `ai init` records is what `upgrade` looks up, so a mode nobody edited is refreshed rather than kept with a `.new` beside it."""
    import loom.ai.layout as layout

    q = bare(tmp_path)
    shipped = layout.tracked_docs()
    assert layout.read_versions(q) == {Path(rel).name: layout.sha(text) for rel, text in shipped.items()}
    shipped["ai/modes/audit.md"] += "\n## New shipped section\n"
    monkeypatch.setattr(layout, "tracked_docs", lambda: shipped)
    r = ok("upgrade", cwd=q)
    assert "wrote ai/modes/audit.md" in r.output and "kept" not in r.output
    assert (q / "ai" / "modes" / "audit.md").read_text() == shipped["ai/modes/audit.md"]
    assert not (q / "ai" / "modes" / "audit.md.new").exists()


def test_review_mode_grades_every_finding_and_writes_no_pdf(tmp_path: Path) -> None:
    """Mode 7 of the author's own rules: it supersedes the compiled red-marked pair rather than producing one."""
    q = bare(tmp_path)
    text = (q / "ai" / "modes" / "review.md").read_text()
    for wanted in (
        "new citations",
        "bad citations",
        "unnecessary hypotheses",
        "merge-or-delete",
        "sharpenings",
        "self-containedness",
        "mathematical errors",
        "grammar and wording",
        "clarity",
    ):
        assert wanted in text, wanted
    assert "--severity" in text and "--payload" in text
    assert "[referee-review]" in text  # reused, not a new block: blocks are structures, modes are procedures
    assert "There is no compiled LaTeX or PDF pair." in text
    assert "review-KEY.2.notes.md" in text  # a re-check's report is a new numbered pass

    blocks = (q / "ai" / "rules.md").read_text()
    assert "a reply is for talking to the author" in blocks  # the edit-not-reply rule
    assert "`citation` for a work" in blocks


def test_orient_static_plus_live(tmp_path: Path) -> None:
    q = bare(tmp_path)
    r = ok("ai", "orient", cwd=q)
    assert r.output.startswith("# Orientation: working in a quilt")
    assert "# Live state" in r.output and "- status: " in r.output and "prefix `dm`" in r.output
    assert "- undigested citekeys: " in r.output and "- open sessions: none" in r.output


def test_ai_start_opens_a_session_and_orient_prints_its_chat(tmp_path: Path) -> None:
    q = bare(tmp_path)
    r = ok("ai", "start", "Referee of dm-0003", cwd=q, env=FIXED)
    sid = r.output.strip().splitlines()[0]
    assert sid == "s-2026-09-16-0001"  # the id is minted, never slugified from the title
    index = (q / ".loom" / "sessions" / "index.jsonl").read_text()
    assert '"title": "Referee of dm-0003"' in index and '"event": "created"' in index
    rel = f".loom/sessions/{sid}"
    ok(
        "session",
        "say",
        "First pass. Asked: referee. Did: read the source.",
        "--session",
        sid,
        "--as",
        "Referee Agent",
        cwd=q,
    )
    ok("source", "dm-0003", "--closure", "--session", sid, cwd=q)
    log = (q / rel / "run.log").read_text()
    assert "loom source dm-0003 --closure" in log
    assert not list((q / rel).glob("*.tex"))  # reading writes nothing into the session
    o = ok("ai", "orient", "--session", sid, cwd=q)
    assert (
        f"# Your session: `{rel}`" in o.output and "## the chat" in o.output and "Referee Agent: First pass" in o.output
    )
    assert "thread.md" not in o.output
    assert "loom source dm-0003" in o.output
    assert "loom ai orient" in (q / rel / "run.log").read_text()
    second = ok("ai", "start", "Referee of dm-0003", cwd=q, env=FIXED).output.strip()
    assert second == "s-2026-09-16-0002"  # two sessions may share a title; the id is what distinguishes them


def test_sessions_listed_by_title_and_addressed_by_part_of_one(tmp_path: Path) -> None:
    """A session is addressed by what the author called it; remembering the minute it opened is not a workflow."""
    q = bare(tmp_path)
    assert ok("session", "list", cwd=q).output.startswith("no sessions yet")
    ref = ok("ai", "start", "Referee of the parity theorem", cwd=q, env=FIXED).output.strip()
    other = ok("ai", "start", "Ingest of Hartshorne", cwd=q, env=FIXED).output.strip()
    assert ref != other
    listing = ok("session", "list", cwd=q).output
    assert f"{ref}  Referee of the parity theorem" in listing
    assert f"{other}  Ingest of Hartshorne" in listing

    # "Referee **of**…" and "Ingest **of**…": named, not guessed
    refused("ai", "annotations", "--session", "of", cwd=q, code=2, match="matches 2 sessions")

    ok("ai", "name", "Parity, revisited", "--session", "parity", cwd=q)
    assert "Parity, revisited" in ok("session", "list", cwd=q).output

    ok(
        "annotate",
        "dm-0003",
        "Say where finiteness is used.",
        "--quote",
        "with $X$ a finite set",
        "--kind",
        "suggestion",
        "--session",
        ref,
        "--author",
        "An Agent",
        cwd=q,
        env=FIXED,
    )
    # part of a title reaches the session, which is how a person addresses one
    ok("ai", "annotations", "--session", "revisited", cwd=q)

    f = ok("ai", "annotations", "--session", "parity", cwd=q)
    assert "dm-0003" in f.output and "suggestion" in f.output and "a finite set" in f.output

    ok("ai", "discard", ref, cwd=q)
    assert "Parity, revisited" not in ok("session", "list", cwd=q).output
    assert "Parity, revisited" in ok("session", "list", "--all", cwd=q).output
    refused("ai", "runs", cwd=q, code=2, match="No such command 'runs'")


def test_run_log_appended_by_run_flag(tmp_path: Path) -> None:
    q = bare(tmp_path)
    sid = ok("ai", "start", cwd=q, env=FIXED).output.strip()
    rel = f".loom/sessions/{sid}"
    for code, args in (
        (0, ("search", "orbit")),
        (0, ("deps", "dm-0003")),
        (0, ("unravel", "dm-0001")),
        (0, ("lint",)),
        (0, ("status",)),
    ):
        exits(code, *args, "--session", sid, cwd=q)
    env = dict(FIXED, LOOM_SESSION=sid)
    ok("search", "gadget", cwd=q, env=env)  # LOOM_SESSION is the default for --session
    log = (q / rel / "run.log").read_text().splitlines()
    commands = [ln.split("  ", 1)[1] for ln in log]
    assert commands[:5] == [
        "loom search orbit",
        "loom deps dm-0003",
        "loom unravel dm-0001",
        "loom lint",
        "loom status",
    ]
    assert commands[-1] == "loom search gadget"


def test_ai_check_reports_writes_outside_the_session(tmp_path: Path) -> None:
    """`ai check` names every file changed after the session opened outside its directory and reverts nothing; the annotation log `loom annotate` appends to is the agent's to write, and a digest is not (DR-173)."""
    q = bare(tmp_path)
    sid = ok("ai", "start", "audit", cwd=q).stdout.strip()  # the real clock: the check compares mtimes with it
    rel = f".loom/sessions/{sid}"
    started = time.time()
    # well past the session's first second, which the check allows, whatever the clock's resolution
    later = started + 60
    (q / rel).mkdir(parents=True, exist_ok=True)
    (q / rel / "audit-dm-0003.notes.md").write_text("## [summary]\nfine\n")
    assert ok("ai", "check", sid, cwd=q).stdout.strip() == "ok: nothing outside the session changed"

    # the annotations the agent was told to write; addressed by title, like every other session (DR-167)
    ok("annotate", "dm-0002", "A finding", "--session", sid, "--author", "A. Author", cwd=q)
    os.utime(q / "annotations" / "log.jsonl", (later, later))
    assert ok("ai", "check", "audit", cwd=q).stdout.strip() == "ok: nothing outside the session changed"

    node = q / "nodes" / "dm-0002.tex"
    node.write_text(node.read_text() + "% touched by an agent\n")
    os.utime(node, (later, later))
    bad = exits(1, "ai", "check", "audit", cwd=q)
    assert "loom:agent-wrote-outside-run" in bad.output and "nodes/dm-0002.tex" in bad.output, bad.output
    assert node.read_text().endswith("% touched by an agent\n")  # reported, never reverted
    node.write_text(node.read_text().replace("% touched by an agent\n", ""))
    os.utime(node, (started - 100, started - 100))
    ok("ai", "check", sid, cwd=q)

    # `loom digest extract` makes digests and `ingest` mode checks them, so a digest the agent wrote itself is a write outside the session like any other, and there is no command to copy one in
    refused("ai", "promote", "anything", cwd=q, code=2, match="No such command 'promote'")
    (q / "digests" / "Har77.tex").write_text("% !LOOM digest: Har77\n\\section*{Overview}\nHartshorne.\n")
    os.utime(q / "digests" / "Har77.tex", (later, later))
    caught = exits(1, "ai", "check", sid, cwd=q)
    assert "digests/Har77.tex" in caught.output


def test_threads_from_sessions_in_manifest_and_sessions_not_scanned(tmp_path: Path) -> None:
    q = bare(tmp_path)
    sid = ok("ai", "start", "referee dm-0003", cwd=q, env=FIXED).output.strip()
    rel = f".loom/sessions/{sid}"
    ok("source", "dm-0003", "--closure", "--session", sid, cwd=q)
    ok(
        "annotate",
        "dm-0003/proof",
        "Closedness is asserted.",
        "--quote",
        "diagonal is closed",
        "--kind",
        "objection",
        "--session",
        sid,
        "--author",
        "An Agent",
        cwd=q,
        env=dict(FIXED, AI_AGENT="1"),
    )
    ok("session", "say", "Refereed dm-0003; one objection.", "--session", sid, "--as", "Referee Agent", cwd=q)
    (q / rel / "referee-dm-0003.notes.md").write_text("## [summary]\nOne objection.\n")
    ok("build", cwd=q)
    m = json.loads((q / "build" / "manifest.json").read_text())
    t = m["threads"][sid]
    assert t["kind"] == "session" and t["created"] == "2026-09-16T14:02:00Z"
    assert t["targets"] == ["dm-0003/proof"] and t["discarded"] is False
    # the conversation is not in the manifest, which every viewer polls; the build pages it beside it
    assert "messages" not in t
    page = json.loads((q / "build" / "transcripts" / sid / "1.json").read_text())
    assert [(e["who"], e["body_html"]) for e in page["events"]] == [
        ("Referee Agent", "<p>Refereed dm-0003; one objection.</p>")
    ]
    kinds = {a["name"]: a["kind"] for a in t["attachments"]}
    assert kinds == {"annotations": "annotations", "referee-dm-0003.notes.md": "notes"}  # reading leaves no file
    assert [entry["command"] for entry in t["log"]][:2] == [
        "loom source dm-0003 --closure",
        "loom annotate dm-0003/proof --quote --kind objection",
    ]
    assert any(s["kind"] == "thread" and s["key"] == t["id"] for s in m["search"])
    # a person writing in the same session is a participant in the same thread, which is the point of the split
    ok("annotate", "dm-0002", "Mine.", "--author", "Tom", "--session", sid, cwd=q, env=FIXED)
    ok("build", cwd=q)
    m2 = json.loads((q / "build" / "manifest.json").read_text())
    again = m2["threads"][sid]
    assert {"kind": "person", "id": "Tom"} in again["participants"]
    assert {"kind": "agent", "id": "An Agent"} in again["participants"]
    # a .tex file in a session is not scanned: an id it repeats is no duplicate (test_lint_exit_codes is the control)
    (q / rel / "scratch.tex").write_text("\\begin{lemma}\\label{dm-0001}\ndup\n\\end{lemma}\n")
    assert "duplicate-id" not in ok("lint", cwd=q).output


def test_the_session_flag_works_from_a_subdirectory(tmp_path: Path) -> None:
    q = bare(tmp_path)
    sid = ok("ai", "start", "sub", cwd=q, env=FIXED).output.strip()
    rel = f".loom/sessions/{sid}"
    ok("search", "gadget", "--session", sid, cwd=q / "nodes")  # from a subdirectory
    ok("source", "dm-0003", "--session", sid, cwd=q / "nodes")
    ok(
        "annotate",
        "dm-0003",
        "Fine.",
        "--kind",
        "note",
        "--session",
        sid,
        "--author",
        "A. Author",
        cwd=q / "nodes",
        env=FIXED,
    )
    log = (q / rel / "run.log").read_text()
    assert "loom search gadget" in log and "loom source dm-0003" in log and "loom annotate dm-0003" in log
    assert (q / "annotations" / "log.jsonl").is_file()  # the record lands in the quilt's one log
    assert not (q / "nodes" / "ai").exists()  # nothing landed relative to the shell's directory


def test_the_allow_list_and_the_permission_file_cannot_disagree(tmp_path: Path) -> None:
    """One table, `AGENT_COMMANDS`, decides what an agent may run: the deny list is its complement, so a command added later is the author's until it is admitted, and the settings file and the prose in rules.md are rendered from it (DR-173)."""
    from loom.ai.layout import AGENT_COMMANDS, author_commands, command_tree, permissions_json, settings_deny_paths

    every = set(command_tree())
    assert AGENT_COMMANDS < every, "the allow-list names commands loom does not have"
    assert set(author_commands()) == every - AGENT_COMMANDS  # derived, never listed

    denied_paths = settings_deny_paths()
    denied = {d.removeprefix("Bash(loom ").removesuffix("*)") for d in denied_paths if d.startswith("Bash(loom ")}
    assert denied == every - AGENT_COMMANDS

    # what the table must not admit: every command that writes into the quilt outside the session and build/, both spellings of canonize among them, so `loom canonise` cannot walk past a deny on `loom canonize`
    writes_outside_a_session = {
        "accept", "atomize", "inline", "import", "draft", "canonize", "canonise", "canonicalize", "stamp", "fork",
        "revert", "live", "linearize", "refs cite", "refs add", "upgrade", "digest import", "ai init",
    }  # fmt: skip
    missing = sorted(writes_outside_a_session - denied)
    assert not missing, f"agent-writable commands missing from the deny list: {missing}"
    # and the files those commands own, which a direct edit would otherwise reach
    for d in ("nodes", "drafting", "canon", "digests", "refs", "annotations", ".loom/history", "ai"):
        assert f"Edit(/{d}/**)" in denied_paths, d
    assert "Edit(/reference-notes.jsonl)" in denied_paths

    q = bare(tmp_path)
    assert (q / ".claude" / "settings.json").read_text() == permissions_json()
    rules = (q / "ai" / "rules.md").read_text()
    for c in sorted(AGENT_COMMANDS):
        assert f"`loom {c}`" in rules, c  # the prose is the same table
    assert "{allowed_commands}" not in rules


def test_codex_is_given_the_same_policy_as_claude(tmp_path: Path) -> None:
    """One policy, loom's own, rendered per tool (DR-283-ikmartin); a quilt does not change it."""
    from loom.ai.layout import AGENT_COMMANDS, CODEX_RULES, author_commands, codex_rules

    rules = codex_rules()
    for c in AGENT_COMMANDS:
        assert (
            f'prefix_rule(pattern = [{", ".join(json.dumps(w) for w in ["loom", *c.split()])}], decision = "allow")'
            in rules
        )
    for c in author_commands():
        assert f'"{c.split()[-1]}"], decision = "forbidden")' in rules
    ok("init", str(tmp_path / "c"), "--ai", "codex", "--yes", cwd=tmp_path)
    assert (tmp_path / "c" / CODEX_RULES).read_text() == rules
    assert (tmp_path / "c" / ".claude" / "settings.json").is_file()  # the same table for the other tool, too


def test_every_command_an_agent_writes_with_takes_as() -> None:
    """The rules tell an agent to name itself with `--as`, so every agent command that records an author takes it (0.14 study F22)."""
    import click

    from loom.ai.layout import AGENT_COMMANDS
    from loom.cli import main

    def walk(cmd: click.Command, path: tuple[str, ...] = ()):  # type: ignore[no-untyped-def]
        if isinstance(cmd, click.Group):
            for n, c in cmd.commands.items():
                yield from walk(c, (*path, n))
        else:
            yield " ".join(path), {o for p in cmd.params for o in getattr(p, "opts", [])}

    # `ai discard --author` picks records to discard; it says nothing about who is discarding
    naming = {c: opts for c, opts in walk(main) if c in AGENT_COMMANDS and "--author" in opts and c != "ai discard"}
    assert naming, "no agent command takes an author"
    assert not [c for c, opts in naming.items() if "--as" not in opts]


def test_every_command_the_agent_is_told_to_run_is_allowed() -> None:
    """A command the shipped documents tell the agent to run is one it may run, unless they name it to be refused (0.14 study F18)."""
    from loom.ai.layout import AGENT_COMMANDS, author_commands

    assets = Path(__file__).parents[2] / "src" / "loom" / "assets" / "ai"
    docs = " ".join(p.read_text() for p in assets.rglob("*.md"))
    # the author's own verbs are named to be refused; `session use` is named beside `--session`, which the agent uses
    named_to_refuse = {
        "accept",
        "refs verify",
        "refs discard",
        "refs unreadable",
        "refs forget",
        "refs cite",
        "ai init",
        "upgrade",
        "session use",
    }
    told = {c for c in author_commands() if re.search(rf"`loom {re.escape(c)}\b", docs)}
    assert told <= named_to_refuse, sorted(told - named_to_refuse)
    assert "refs overview" in AGENT_COMMANDS


def test_findings_for_a_run_include_what_the_author_decided(tmp_path: Path) -> None:
    """`ai annotations` shows the author's decision on each of the session's proposals, so an agent that reattaches need not ask `refs why` id by id."""
    from tests.unit._quilts import mapped, propose

    q, ck = mapped(tmp_path)
    runname = ok("ai", "start", "r", cwd=q).stdout.strip()
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y", session=runname)
    ok("refs", "discard", f"{ck}-thm-1.1", "--reason", "wrong theorem", "--author", "i", cwd=q)
    out = ok("ai", "annotations", "--session", runname, cwd=q).output
    assert f"{ck}-thm-1.1" in out and "discarded -- wrong theorem" in out
