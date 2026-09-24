"""The AI layer (book 11): layout and vendor files, upgrade, orientation, runs and their logs, promotion, the outside-writes check, and threads in the manifest."""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from click.testing import CliRunner

from loom.ai.layout import MODES, TARGET_MODES
from loom.cli import main

FIXED = {"LOOM_FIXED_TIME": "2026-09-16T14:02:00Z"}


def run(*args: str, cwd: Path, env: dict[str, str] | None = None, stdin: str | None = None):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args), env=env, input=stdin)
    finally:
        os.chdir(old)


def demo(tmp_path: Path, *flags: str) -> Path:
    assert run("init", str(tmp_path / "q"), "--demo", cwd=tmp_path).exit_code == 0
    q = tmp_path / "q"
    if (q / "ai").exists():  # the shipped demo carries its layer; start these tests from a bare quilt
        import shutil

        shutil.rmtree(q / "ai")
        for rel in ("CLAUDE.md", "AGENTS.md"):
            (q / rel).unlink(missing_ok=True)
        shutil.rmtree(q / ".claude", ignore_errors=True)
        # the annotation log lives at the quilt root, not under ai/, and the demo now ships sessions of its own: a
        # test that starts from a bare quilt must clear both, or it counts the demo's sittings as its own
        shutil.rmtree(q / "annotations", ignore_errors=True)
        shutil.rmtree(q / ".loom" / "sessions", ignore_errors=True)
    r = run("ai", "init", *flags, cwd=q)
    assert r.exit_code == 0, r.output
    return q


def test_ai_init_layout_and_vendor_files(tmp_path: Path) -> None:
    q = demo(tmp_path)
    for rel in ("ai/README.md", "ai/orientation.md", "ai/.loom-modes-version", "CLAUDE.md", "AGENTS.md"):
        assert (q / rel).is_file(), rel
    assert {p.stem for p in (q / "ai" / "modes").glob("*.md")} == set(MODES)
    root_text = (q / "CLAUDE.md").read_text()
    assert (
        root_text == (q / "AGENTS.md").read_text() and "loom ai orient" in root_text and ".loom/sessions/" in root_text
    )
    assert "# Orientation: working in a quilt" in (q / "ai" / "orientation.md").read_text()
    assert not (q / ".claude").exists()
    again = run("ai", "init", cwd=q)
    assert again.exit_code == 2 and "loom upgrade" in again.output


def test_root_files_carry_one_line_and_keep_the_authors(tmp_path: Path) -> None:
    """CLAUDE.md is the author's file with one line of loom's in it; an upgrade must not take it over (DR-151)."""
    from loom.ai.layout import CLAUDE_LINE

    q = demo(tmp_path)
    for name in ("CLAUDE.md", "AGENTS.md"):
        assert (q / name).read_text().splitlines().count(CLAUDE_LINE) == 1
    mine = "\n## This project\n\nNever touch canon/ without asking.\n"
    (q / "CLAUDE.md").write_text((q / "CLAUDE.md").read_text() + mine)
    assert run("upgrade", cwd=q).exit_code == 0
    after = (q / "CLAUDE.md").read_text()
    assert after.count(CLAUDE_LINE) == 1 and "Never touch canon/ without asking." in after

    # an earlier version of loom's line is replaced where it stands, not appended beside
    (q / "AGENTS.md").write_text("This directory is a quilt managed by loom. Old wording.\n\nMine.\n")
    assert run("upgrade", cwd=q).exit_code == 0
    agents = (q / "AGENTS.md").read_text()
    assert agents.count(CLAUDE_LINE) == 1 and "Old wording" not in agents and "Mine." in agents


def test_ai_init_permissions_generated(tmp_path: Path) -> None:
    q = demo(tmp_path, "--permissions")
    data = json.loads((q / ".claude" / "settings.json").read_text())
    deny = data["permissions"]["deny"]
    allow = data["permissions"]["allow"]
    # `.loom` is no longer denied wholesale: the session an agent writes in lives under it, so the record's own
    # parts are named instead (plan 0.13 §5).
    for d in ("nodes", "drafting", "digests", "refs", "annotations", ".loom/history", "ai"):
        assert f"Edit(/{d}/**)" in deny, d
    assert "Edit(/.loom/sessions/**)" in allow and "Edit(/build/**)" in allow
    # Claude Code matches only `Edit` rules against paths; a `Write` rule is ignored and says so on every start
    assert not any(r.startswith("Write(") for r in allow + deny)
    assert any(rule.startswith("Bash(loom accept") for rule in deny) and any("upgrade" in rule for rule in deny)


def test_ai_init_skills_generated_pointer_only(tmp_path: Path) -> None:
    q = demo(tmp_path, "--skills")
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


def test_every_command_that_writes_outside_a_run_is_denied_to_the_agent(tmp_path: Path) -> None:
    """The deny list is now the complement of one allow-list, so a command added later is the author's until it is admitted.

    A habit fails the first time a command lands at 2am; this does not. The allow list gives an agent its session directory and
    `build/`, so every command that writes anywhere else is the author's and must appear here by name. It held: the
    hand-written list this replaced was missing seven, `upgrade` and both spellings of `canonize` among them, so
    `loom canonise` walked straight through the deny on `loom canonize` (DR-173).
    """
    from loom.ai.layout import settings_deny_paths

    denied = settings_deny_paths()
    commands = {d.removeprefix("Bash(loom ").removesuffix("*)") for d in denied if d.startswith("Bash(loom ")}

    # every loom command that writes into the quilt outside its session and build/
    writes_outside_a_run = {
        "accept",
        "atomize",
        "inline",
        "import",
        "draft",
        "canonize",
        "stamp",
        "fork",
        "revert",
        "live",
        "linearize",
        "refs note",
        "upgrade",
        "canonise",
        "canonicalize",
        "refs add",
        "digest import",
        "ai init",
    }
    missing = sorted(writes_outside_a_run - commands)
    assert not missing, f"agent-writable commands missing from the deny list: {missing}"

    # and the files those commands own, which a direct Write would otherwise reach
    for path in (
        "/nodes/**",
        "/drafting/**",
        "/canon/**",
        "/digests/**",
        "/.loom/history/**",
        "/reference-notes.jsonl",
    ):
        assert f"Edit({path})" in denied, path


def test_modes_templates_present_and_contracts_listed(tmp_path: Path) -> None:
    q = demo(tmp_path)
    assert len(MODES) == 9  # rules.md is not among them: it is not a mode and no longer filed as one
    assert not (q / "ai" / "modes" / "blocks.md").exists()
    rules = (q / "ai" / "rules.md").read_text()
    assert rules.startswith("# Standing rules, contracts, and blocks") and "## Never" in rules
    for mode in MODES:
        text = (q / "ai" / "modes" / f"{mode}.md").read_text()
        assert text.startswith(f"# Mode: {mode}\n\n## Before you begin\n")
        assert "## Checklist" in text
        # the write policy is stated in every template, so a mode read without the orientation still carries it.
        # It says "your run directory" rather than $LOOM_SESSION: nothing sets that variable since the launcher went.
        assert re.search(r"^- \[ \] Nothing was written outside your session's directory\.", text, re.M)
        assert "$LOOM_SESSION" not in text  # nothing sets it; ai/rules.md is the one file that explains that
        if mode not in ("quick",):
            # the account of the work goes in the chat, the one transcript; no journal file
            assert "## Output" in text and "loom session say" in text and "thread.md" not in text


def test_upgrade_preserves_edited_modes(tmp_path: Path) -> None:
    q = demo(tmp_path)
    referee = q / "ai" / "modes" / "referee.md"
    referee.write_text(referee.read_text() + "\n## House rule\nAlways check the dimension count.\n")
    audit = q / "ai" / "modes" / "audit.md"
    original_audit = audit.read_text()
    orientation = q / "ai" / "orientation.md"
    orientation.write_text("stale orientation\n")
    r = run("upgrade", cwd=q)
    assert r.exit_code == 0, r.output
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
    original = layout.tracked_docs
    layout.tracked_docs = lambda: shipped  # type: ignore[assignment]
    try:
        r2 = run("upgrade", cwd=q)
    finally:
        layout.tracked_docs = original  # type: ignore[assignment]
    assert r2.exit_code == 0 and "referee.md.new" in r2.output
    assert (
        "House rule" in referee.read_text()
        and "New shipped section" in (q / "ai" / "modes" / "referee.md.new").read_text()
    )


def test_review_mode_grades_every_finding_and_writes_no_pdf(tmp_path: Path) -> None:
    """Mode 7 of the author's own rules: it supersedes the compiled red-marked pair rather than producing one."""
    q = demo(tmp_path)
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
    q = demo(tmp_path)
    r = run("ai", "orient", cwd=q)
    assert r.exit_code == 0, r.output
    assert r.output.startswith("# Orientation: working in a quilt")
    assert "# Live state" in r.output and "- status: " in r.output and "prefix `dm`" in r.output
    assert "- undigested citekeys: " in r.output and "- open sessions: none" in r.output


def test_ai_start_opens_a_session_and_orient_prints_its_chat(tmp_path: Path) -> None:
    q = demo(tmp_path)
    r = run("ai", "start", "Referee of dm-0003", cwd=q, env=FIXED)
    assert r.exit_code == 0, r.output
    sid = r.output.strip().splitlines()[0]
    assert sid == "s-2026-09-16-0001"  # the id is minted, never slugified from the title
    index = (q / ".loom" / "sessions" / "index.jsonl").read_text()
    assert '"title": "Referee of dm-0003"' in index and '"event": "created"' in index
    rel = f".loom/sessions/{sid}"
    said = run(
        "session",
        "say",
        "First pass. Asked: referee. Did: read the source.",
        "--session",
        sid,
        "--as",
        "Referee Agent",
        cwd=q,
    )
    assert said.exit_code == 0, said.output
    assert run("source", "dm-0003", "--closure", "--session", sid, cwd=q).exit_code == 0
    log = (q / rel / "run.log").read_text()
    assert "loom source dm-0003 --closure" in log
    assert not list((q / rel).glob("*.tex"))  # reading writes nothing into the session
    o = run("ai", "orient", "--session", sid, cwd=q)
    assert o.exit_code == 0, o.output
    assert (
        f"# Your session: `{rel}`" in o.output and "## the chat" in o.output and "Referee Agent: First pass" in o.output
    )
    assert "thread.md" not in o.output
    assert "loom source dm-0003" in o.output
    assert "loom ai orient" in (q / rel / "run.log").read_text()
    second = run("ai", "start", "Referee of dm-0003", cwd=q, env=FIXED).output.strip()
    assert second == "s-2026-09-16-0002"  # two sessions may share a title; the id is what distinguishes them


def test_sessions_listed_by_title_and_addressed_by_part_of_one(tmp_path: Path) -> None:
    """A session is addressed by what the author called it; remembering the minute it opened is not a workflow."""
    q = demo(tmp_path)
    assert run("ai", "runs", cwd=q).output.strip() == "no open sessions"
    ref = run("ai", "start", "Referee of the parity theorem", cwd=q, env=FIXED).output.strip()
    other = run("ai", "start", "Ingest of Hartshorne", cwd=q, env=FIXED).output.strip()
    assert ref != other
    listing = run("ai", "runs", cwd=q).output
    assert "2026-09-16: Referee of the parity theorem" in listing
    assert "2026-09-16: Ingest of Hartshorne" in listing

    ambiguous = run("ai", "findings", "--session", "of", cwd=q)  # "Referee **of**…" and "Ingest **of**…"
    assert ambiguous.exit_code == 2 and "matches 2 sessions" in ambiguous.output  # named, not guessed

    named = run("ai", "name", "Parity, revisited", "--session", "parity", cwd=q)
    assert named.exit_code == 0, named.output
    assert "Parity, revisited" in run("ai", "runs", cwd=q).output

    c = run(
        "comment",
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
    assert c.exit_code == 0, c.output
    # part of a title reaches the session, which is how a person addresses one
    by_part = run("ai", "findings", "--session", "revisited", cwd=q)
    assert by_part.exit_code == 0, by_part.output

    f = run("ai", "findings", "--session", "parity", cwd=q)
    assert f.exit_code == 0, f.output
    assert "dm-0003" in f.output and "suggestion" in f.output and "a finite set" in f.output

    assert run("ai", "discard", ref, cwd=q).exit_code == 0
    assert "Parity, revisited" not in run("ai", "runs", cwd=q).output
    assert "(closed)" in run("ai", "runs", "--all", cwd=q).output


def test_run_log_appended_by_run_flag(tmp_path: Path) -> None:
    q = demo(tmp_path)
    sid = run("ai", "start", cwd=q, env=FIXED).output.strip()
    rel = f".loom/sessions/{sid}"
    for args in (("search", "orbit"), ("deps", "dm-0003"), ("unravel", "dm-0001"), ("lint",), ("status",)):
        r = run(*args, "--session", sid, cwd=q)
        assert r.exit_code in (0, 1), (args, r.output)
    env = dict(FIXED, LOOM_SESSION=sid)
    assert run("search", "gadget", cwd=q, env=env).exit_code == 0  # LOOM_SESSION is the default for --session
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


def test_ai_check_reports_outside_writes(tmp_path: Path) -> None:
    q = demo(tmp_path)
    r = run("ai", "start", "audit", cwd=q)  # the real clock: the check compares mtimes with when the round opened
    sid = r.output.strip()
    rel = f".loom/sessions/{sid}"
    started = time.time()
    (q / rel).mkdir(parents=True, exist_ok=True)
    (q / rel / "audit-dm-0003.notes.md").write_text("## [summary]\nfine\n")
    ok = run("ai", "check", sid, cwd=q)
    assert ok.exit_code == 0 and "ok" in ok.output, ok.output
    node = q / "nodes" / "dm-0002.tex"
    node.write_text(node.read_text() + "% touched by an agent\n")
    os.utime(node, (started + 60, started + 60))  # well past the run's first second, whatever the clock's resolution
    bad = run("ai", "check", sid, cwd=q)
    assert bad.exit_code == 1 and "loom:agent-wrote-outside-run" in bad.output and "nodes/dm-0002.tex" in bad.output, (
        bad.output
    )
    assert node.read_text().endswith("% touched by an agent\n")  # reported, never reverted
    node.write_text(node.read_text().replace("% touched by an agent\n", ""))
    os.utime(node, (started - 100, started - 100))
    after = run("ai", "check", sid, cwd=q)
    assert after.exit_code == 0, after.output

    # a digest the agent wrote itself is a write outside the run like any other: `loom digest extract` makes digests
    # and `ingest` mode checks them, so nothing copies a typed one in (DR-173)
    assert run("ai", "promote", "anything", cwd=q).exit_code != 0
    (q / "digests" / "Har77.tex").write_text("% !LOOM digest: Har77\n\\section*{Overview}\nHartshorne.\n")
    os.utime(q / "digests" / "Har77.tex", (started + 60, started + 60))
    caught = run("ai", "check", sid, cwd=q)
    assert caught.exit_code == 1 and "digests/Har77.tex" in caught.output


def test_threads_from_sessions_in_manifest_and_sessions_not_scanned(tmp_path: Path) -> None:
    q = demo(tmp_path)
    sid = run("ai", "start", "referee dm-0003", cwd=q, env=FIXED).output.strip()
    rel = f".loom/sessions/{sid}"
    assert run("source", "dm-0003", "--closure", "--session", sid, cwd=q).exit_code == 0
    r = run(
        "comment",
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
    assert r.exit_code == 0, r.output
    said = run("session", "say", "Refereed dm-0003; one objection.", "--session", sid, "--as", "Referee Agent", cwd=q)
    assert said.exit_code == 0, said.output
    (q / rel / "referee-dm-0003.notes.md").write_text("## [summary]\nOne objection.\n")
    assert run("build", cwd=q).exit_code == 0
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
        "loom comment dm-0003/proof --quote --kind objection",
    ]
    assert any(s["kind"] == "thread" and s["key"] == t["id"] for s in m["search"])
    # a person writing in the same session is a participant in the same thread, which is the point of the split
    assert run("comment", "dm-0002", "Mine.", "--author", "Tom", "--session", sid, cwd=q, env=FIXED).exit_code == 0
    assert run("build", cwd=q).exit_code == 0
    m2 = json.loads((q / "build" / "manifest.json").read_text())
    again = m2["threads"][sid]
    assert {"kind": "person", "id": "Tom"} in again["participants"]
    assert {"kind": "agent", "id": "An Agent"} in again["participants"]
    # the bundle copied into the run is not a master and none of its ids are duplicates
    lint = run("lint", cwd=q).output
    assert "duplicate-id" not in lint and f"{rel}/bundle-dm-0003.tex" not in lint


def test_the_session_flag_works_from_a_subdirectory(tmp_path: Path) -> None:
    q = demo(tmp_path)
    sid = run("ai", "start", "sub", cwd=q, env=FIXED).output.strip()
    rel = f".loom/sessions/{sid}"
    assert run("search", "gadget", "--session", sid, cwd=q / "nodes").exit_code == 0  # from a subdirectory
    assert run("source", "dm-0003", "--session", sid, cwd=q / "nodes").exit_code == 0
    assert (
        run(
            "comment",
            "dm-0003",
            "Fine.",
            "--kind",
            "confirmation",
            "--session",
            sid,
            "--author",
            "A. Author",
            cwd=q / "nodes",
            env=FIXED,
        ).exit_code
        == 0
    )
    log = (q / rel / "run.log").read_text()
    assert "loom search gadget" in log and "loom source dm-0003" in log and "loom comment dm-0003" in log
    assert (q / "annotations" / "log.jsonl").is_file()  # the record lands in the quilt's one log
    assert not (q / "nodes" / "ai").exists()  # nothing landed relative to the shell's directory


def test_upgrade_keeps_an_edited_orientation(tmp_path: Path) -> None:
    """The orientation is the first file an author tailors and the only shipped document with no policy: `loom upgrade` overwrote it with no warning and no backup (A1)."""
    q = demo(tmp_path)
    orientation = q / "ai" / "orientation.md"
    mine = orientation.read_text() + "\n## Standing rule for this quilt\nNever touch drafting/appendix.tex.\n"
    orientation.write_text(mine)
    r = run("upgrade", cwd=q)
    assert r.exit_code == 0, r.output
    assert orientation.read_text() == mine
    assert "kept ai/orientation.md (edited)" in r.output
    assert (q / "ai" / "orientation.md.new").is_file()


def test_ai_check_does_not_flag_the_annotations_the_agent_was_told_to_write(tmp_path: Path) -> None:
    """`loom comment` appends to the log; the command that verifies an agent behaved reported that as a violation (H13's stale name)."""
    import os
    import time

    q = demo(tmp_path)
    sid = run("ai", "start", "Referee", cwd=q).output.strip()
    assert run("comment", "dm-0002", "A finding", "--session", sid, "--author", "A. Author", cwd=q).exit_code == 0
    later = time.time() + 60  # the index records whole seconds and the check allows the round's first one
    os.utime(q / "annotations" / "log.jsonl", (later, later))

    r = run("ai", "check", "Referee", cwd=q)  # by name, like every other run address (DR-167)
    assert r.exit_code == 0, r.output
    assert "ok: nothing outside the session changed" in r.output

    node = q / "nodes" / "dm-0002.tex"
    node.write_text(node.read_text() + "\n% edited\n")
    os.utime(node, (later, later))
    bad = run("ai", "check", "Referee", cwd=q)
    assert bad.exit_code == 1 and "nodes/dm-0002.tex" in bad.output  # a real write outside the run still reports


def test_the_allow_list_and_the_permission_file_cannot_disagree(tmp_path: Path) -> None:
    """Two hand-maintained lists of one fact drifted once already; both are now the same table (DR-173)."""
    from loom.ai.layout import AGENT_COMMANDS, author_commands, command_tree, permissions_json, settings_deny_paths

    every = set(command_tree())
    assert AGENT_COMMANDS < every, "the allow-list names commands loom does not have"
    assert set(author_commands()) == every - AGENT_COMMANDS  # derived, never listed

    denied = {
        d.removeprefix("Bash(loom ").removesuffix("*)") for d in settings_deny_paths() if d.startswith("Bash(loom ")
    }
    assert denied == every - AGENT_COMMANDS

    q = demo(tmp_path, "--permissions")
    assert (q / ".claude" / "settings.json").read_text() == permissions_json()
    rules = (q / "ai" / "rules.md").read_text()
    for c in sorted(AGENT_COMMANDS):
        assert f"`loom {c}`" in rules, c  # the prose is the same table
    assert "{allowed_commands}" not in rules


def test_every_command_an_agent_writes_with_takes_as() -> None:
    """F22 of the 0.14 study: the rules say "name yourself with `--as`", and `loom comment` knew only `--author`."""
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
    """F18 of the 0.14 study: the orientation sent the agent to `loom refs overview`, and the permission file refused it."""
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
        "refs note",
        "ai init",
        "upgrade",
        "session use",
    }
    told = {c for c in author_commands() if re.search(rf"`loom {re.escape(c)}\b", docs)}
    assert told <= named_to_refuse, sorted(told - named_to_refuse)
    assert "refs overview" in AGENT_COMMANDS
