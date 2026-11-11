"""The AI layer: layout and vendor files, upgrade, orientation, runs and their logs, promotion, the outside-writes check, and threads in the manifest."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from loom.ai.layout import MODES
from tests.helpers import exits, flat, json_of, ok, refused
from tests.unit._quilts import demo

FIXED = {"LOOM_FIXED_TIME": "2026-09-16T14:02:00Z"}


def bare(tmp_path: Path, *flags: str) -> Path:
    """The demo without its AI layer, annotations or sessions, then `loom ai init FLAGS`: the layer these tests read is the one they made, and the sessions they count are their own."""
    from loom.ai.clients import PROJECT_FILES
    from loom.ai.layout import ROOT_FILES

    q = demo(tmp_path)
    shutil.rmtree(q / ".loom/ai")
    for rel in (*ROOT_FILES, *PROJECT_FILES):
        (q / rel).unlink(missing_ok=True)
    shutil.rmtree(q / ".claude", ignore_errors=True)
    shutil.rmtree(q / ".codex", ignore_errors=True)
    shutil.rmtree(q / ".loom/annotations", ignore_errors=True)  # the log lives at the quilt root, not under .loom/ai/
    shutil.rmtree(q / ".loom" / "sessions", ignore_errors=True)
    ok("ai", "init", *flags, cwd=q)
    return q


def test_ai_init_layout_and_vendor_files(tmp_path: Path) -> None:
    q = bare(tmp_path)
    for rel in (
        ".loom/ai/README.md",
        ".loom/ai/orientation.md",
        ".loom/ai/.loom-modes-version",
        "CLAUDE.md",
        "AGENTS.md",
        "GEMINI.md",
    ):
        assert (q / rel).is_file(), rel
    assert {p.stem for p in (q / ".loom/ai" / "modes").glob("*.md")} == set(MODES)
    root_text = (q / "CLAUDE.md").read_text()
    assert root_text == (q / "AGENTS.md").read_text() == (q / "GEMINI.md").read_text()
    assert "`loom_ai_orient`" in root_text and "names as protected" in root_text and "loom doctor" in root_text
    assert "# Orientation: working in a quilt" in (q / ".loom/ai" / "orientation.md").read_text()
    # what agents may run is written for every tool, whichever the person uses (DR-283)
    assert (q / ".claude" / "settings.json").is_file() and (q / ".codex" / "rules" / "loom.rules").is_file()
    # loom starts no agent, so nothing names a command to start one (plan 0.20.1)
    assert not (q / ".loom/ai" / "ai-config.toml").exists()


def test_ai_init_refreshes_an_existing_layer_as_upgrade_would(tmp_path: Path) -> None:
    """`ai init` where `.loom/ai/` exists writes what is missing or stale, and keeps an edited mode file with the new one beside it."""
    q = bare(tmp_path)
    (q / ".loom/ai" / "orientation.md").unlink()
    mode = q / ".loom/ai" / "modes" / "audit.md"
    mode.write_text(mode.read_text() + "\nMy own rule.\n")
    before = {p: p.read_bytes() for p in q.rglob("*") if p.is_file()}
    dry = ok("ai", "init", "--dry-run", cwd=q)
    assert (
        dry.stdout.startswith("dry run: would write")
        and {p: p.read_bytes() for p in q.rglob("*") if p.is_file()} == before
    )
    r = ok("ai", "init", cwd=q)
    assert r.stdout.startswith("refreshed the agent layer") and (q / ".loom/ai" / "orientation.md").is_file()
    assert mode.read_text().endswith("My own rule.\n") and (q / ".loom/ai" / "modes" / "audit.md.new").is_file()
    assert ok("ai", "init", cwd=q).stdout.startswith("refreshed the agent layer: 0 files written, 1 edited file kept")


def test_ai_annotations_refuses_a_filter_value_it_does_not_know(tmp_path: Path) -> None:
    q = bare(tmp_path)
    sid = ok("session", "new", "--name", "x", cwd=q).stdout.split()[0]
    for flag, value in (("--kind", "objecton"), ("--severity", "huge"), ("--status", "discarded")):
        refused("ai", "annotations", "--session", sid, flag, value, cwd=q, code=2, match=f"Invalid value for '{flag}'")


def test_root_files_carry_one_line_and_keep_the_authors(tmp_path: Path) -> None:
    """CLAUDE.md is the author's file with one line of loom's in it; an upgrade must not take it over (DR-151), and a change of variant swaps the line where it stands."""
    from loom.ai.layout import MCP_LINE, ROOT_FILES, SHELL_LINE

    q = bare(tmp_path)
    for name in ROOT_FILES:
        assert (q / name).read_text().splitlines().count(MCP_LINE) == 1
    mine = "\n## This project\n\nNever touch canon/ without asking.\n"
    (q / "CLAUDE.md").write_text("# Mine\n\n" + (q / "CLAUDE.md").read_text() + mine)
    ok("upgrade", cwd=q)
    after = (q / "CLAUDE.md").read_text()
    assert after.count(MCP_LINE) == 1 and "Never touch canon/ without asking." in after
    ok("ai", "init", "--shell", cwd=q)
    lines = (q / "CLAUDE.md").read_text().splitlines()
    assert lines[:3] == ["# Mine", "", SHELL_LINE] and MCP_LINE not in lines and lines[-1].startswith("Never touch")
    ok("ai", "init", "--mcp", cwd=q)
    assert (q / "CLAUDE.md").read_text().splitlines()[:3] == ["# Mine", "", MCP_LINE]


def test_ai_init_permissions_generated(tmp_path: Path) -> None:
    """The generated settings let the agent edit its session, `.loom/build/` and its copies, in `Edit` rules only; what it is denied is test_the_allow_list_and_the_permission_file_cannot_disagree."""
    q = bare(tmp_path)
    data = json.loads((q / ".claude" / "settings.json").read_text())
    deny = data["permissions"]["deny"]
    allow = data["permissions"]["allow"]
    # `.loom` is not denied wholesale: the session an agent writes in lives under it (plan 0.13 §5)
    assert allow[:3] == ["Edit(.loom/sessions/**)", "Edit(.loom/build/**)", "Edit(.loom/copies/**)"]
    # over MCP the server's tools are allowed, with the agent's own commands in a shell beside them, and the author's turned away
    assert "mcp__loom__*" in allow and "Bash(loom status*)" in allow and "Bash(loom *)" not in deny
    assert "Bash(loom accept*)" in deny and "Bash(rm *)" in deny and "Edit(/config.toml)" in deny
    # a fresh quilt protects only loom's records, the config and the research state: the person's files are open
    assert not [
        r
        for r in deny
        if r.startswith("Edit(")
        and not r.startswith(("Edit(/.loom/", "Edit(/config.toml)", "Edit(/research-state.md)"))
    ]
    # relative to the working directory: passed with --settings, `/x` would be `.claude/x` and match nothing (DR-343-ikmartin)
    assert not any(r.startswith("Edit(/") for r in allow)
    # Claude Code matches only `Edit` rules against paths; a `Write` rule is ignored and says so on every start
    assert not any(r.startswith("Write(") for r in allow + deny)


def test_an_agent_is_never_allowed_to_delete(tmp_path: Path) -> None:
    """Nothing is deleted from a session's directory, since an annotation or a note may point at a file there; a shell permission cannot be confined to one directory, so `rm` is denied outright and intermediates go under `.loom/build/SESSION/` (DR-315-ikmartin)."""
    q = bare(tmp_path)
    data = json.loads((q / ".claude" / "settings.json").read_text())
    assert "Bash(rm *)" in data["permissions"]["deny"]
    assert not any(r.startswith("Bash(rm") for r in data["permissions"]["allow"])


def test_modes_templates_present_and_contracts_listed(tmp_path: Path) -> None:
    """Every mode says in one line when it fits, names its report's blocks from the catalogue, and carries none of the ceremony the contract cut removed (plan 0.21.1)."""
    q = bare(tmp_path)
    assert len(MODES) == 9 and "flow" in MODES and "brainstorm" not in MODES  # rules.md is not a mode
    assert not (q / ".loom/ai" / "modes" / "blocks.md").exists()
    rules = (q / ".loom/ai" / "rules.md").read_text()
    assert rules.startswith("# Standing rules, contracts, and blocks") and "## Never" in rules
    catalogue = set(re.findall(r"^- \[([a-z-]+)\]", rules, re.M))
    assert {
        "summary",
        "intuition",
        "structure-map",
        "flow-edits",
        "rubric",
        "fresh-reader",
        "could-not-do",
    } <= catalogue
    assert not {"candidates", "dead-ends"} & catalogue  # brainstorm's, gone with it; a dead end is a note
    for mode in MODES:
        text = (q / ".loom/ai" / "modes" / f"{mode}.md").read_text()
        assert text.startswith(f"# Mode: {mode}\n\nWhen it fits: "), mode
        assert "## Report" in text, mode
        report = text.split("## Report", 1)[1].split("\n## ", 1)[0]
        named = set(re.findall(r"\[([a-z-]+)\]", report))
        assert named and named <= catalogue, (mode, named - catalogue)
        for gone in ("## Before you begin", "## Checklist", ".notes.md", ".check.py", "proposal-"):
            assert gone not in text, (mode, gone)


def test_upgrade_preserves_edited_modes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    q = bare(tmp_path)
    referee = q / ".loom/ai" / "modes" / "referee.md"
    referee.write_text(referee.read_text() + "\n## House rule\nAlways check the dimension count.\n")
    audit = q / ".loom/ai" / "modes" / "audit.md"
    original_audit = audit.read_text()
    orientation = q / ".loom/ai" / "orientation.md"
    orientation.write_text("stale orientation\n")
    r = json_of("upgrade", "--json", cwd=q)
    assert ".loom/ai/modes/referee.md" in r["kept"]
    assert "House rule" in referee.read_text()  # untouched
    assert audit.read_text() == original_audit
    # the orientation is the first file an author tailors, so an edited one is kept like a mode file (DR-170)
    assert ".loom/ai/orientation.md" in r["kept"]
    assert orientation.read_text() == "stale orientation\n"
    assert "# Orientation: working in a quilt" in (q / ".loom/ai" / "orientation.md.new").read_text()
    versions = (q / ".loom/ai" / ".loom-modes-version").read_text()
    assert "referee.md" in versions and "audit.md" in versions
    # the shipped text has not changed in this test, so no .new is written; simulate a changed shipped version
    import loom.ai.layout as layout

    shipped = layout.tracked_docs()
    shipped[".loom/ai/modes/referee.md"] = shipped[".loom/ai/modes/referee.md"] + "\n## New shipped section\n"
    monkeypatch.setattr(layout, "tracked_docs", lambda: shipped)
    r2 = ok("upgrade", cwd=q)
    assert "referee.md.new" in r2.output and r2.output.startswith("upgraded:")
    assert (
        "House rule" in referee.read_text()
        and "New shipped section" in (q / ".loom/ai" / "modes" / "referee.md.new").read_text()
    )
    assert (
        "merge .loom/ai/modes/referee.md.new into .loom/ai/modes/referee.md, then delete .loom/ai/modes/referee.md.new"
        in flat(r2.output)
    )
    # a merge in progress in the .new is the author's, never written over
    new = q / ".loom/ai" / "modes" / "referee.md.new"
    new.write_text(new.read_text() + "half merged\n")
    ok("upgrade", cwd=q)
    assert new.read_text().endswith("half merged\n")
    # merged and deleted, it is not written again until loom ships another version (the re-grade: "on every run")
    new.unlink()
    assert not ok("upgrade", cwd=q).output.count("referee.md.new") and not new.exists()
    shipped[".loom/ai/modes/referee.md"] += "\n## Another shipped section\n"
    ok("upgrade", cwd=q)
    assert "Another shipped section" in new.read_text()


def test_upgrade_counts_one_kept_file_once(tmp_path: Path) -> None:
    """T5: "kept 1 edited file, 1 with a new version beside it to merge" was one file."""
    q = bare(tmp_path)
    (q / ".loom/ai" / "orientation.md").write_text("stale orientation\n")
    r = ok("upgrade", cwd=q).stdout.splitlines()[0]
    assert r == "upgraded: kept 1 edited file, its new version beside it to merge", r


def test_upgrade_refreshes_an_unedited_mode_the_first_time(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """What `ai init` records is what `upgrade` looks up, so a mode nobody edited is refreshed rather than kept with a `.new` beside it."""
    import loom.ai.layout as layout

    q = bare(tmp_path)
    shipped = layout.tracked_docs()
    assert layout.read_versions(q) == {Path(rel).name: layout.sha(text) for rel, text in shipped.items()}
    shipped[".loom/ai/modes/audit.md"] += "\n## New shipped section\n"
    monkeypatch.setattr(layout, "tracked_docs", lambda: shipped)
    r = json_of("upgrade", "--json", cwd=q)
    assert ".loom/ai/modes/audit.md" in r["written"] and r["kept"] == [] and "kept" not in r["verdict"]
    assert (q / ".loom/ai" / "modes" / "audit.md").read_text() == shipped[".loom/ai/modes/audit.md"]
    assert not (q / ".loom/ai" / "modes" / "audit.md.new").exists()


def test_review_mode_grades_every_finding_and_writes_no_pdf(tmp_path: Path) -> None:
    """Mode 7 of the author's own rules: it supersedes the compiled red-marked pair rather than producing one."""
    q = bare(tmp_path)
    text = (q / ".loom/ai" / "modes" / "review.md").read_text()
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
    assert "There is no compiled LaTeX or PDF pair" in text

    blocks = (q / ".loom/ai" / "rules.md").read_text()
    assert "a reply is for talking to the author" in blocks  # the edit-not-reply rule
    assert "`citation` for a work" in blocks


def test_ai_mode_prints_the_quilts_copy_and_refuses_what_loom_does_not_ship(tmp_path: Path) -> None:
    """`loom ai mode NAME` is how an agent reads a mode, so an author's edit holds; a mode loom no longer ships is refused even where its old file was left behind."""
    q = bare(tmp_path)
    flow = q / ".loom/ai" / "modes" / "flow.md"
    assert ok("ai", "mode", "flow", cwd=q).stdout == flow.read_text()
    flow.write_text(flow.read_text().replace("When it fits: ", "When it fits: (house) ", 1))
    assert "(house)" in ok("ai", "mode", "flow", cwd=q).stdout
    (q / ".loom/ai" / "modes" / "brainstorm.md").write_text("# Mode: brainstorm\n\nWhen it fits: never.\n")
    refused("ai", "mode", "brainstorm", cwd=q, code=2, match="no mode 'brainstorm'")
    shutil.rmtree(q / ".loom/ai")
    assert ok("ai", "mode", "flow", cwd=q).stdout.startswith("# Mode: flow\n\nWhen it fits: reading order")


def test_orient_ends_with_the_index_of_the_modes(tmp_path: Path) -> None:
    """Each mode's `When it fits:` line is its entry, read from the quilt's copy; a file loom does not ship is not offered."""
    q = bare(tmp_path)
    quick = q / ".loom/ai" / "modes" / "quick.md"
    quick.write_text(quick.read_text().replace("When it fits: ", "When it fits: (house) ", 1))
    (q / ".loom/ai" / "modes" / "brainstorm.md").write_text("# Mode: brainstorm\n\nWhen it fits: never.\n")
    out = ok("ai", "orient", cwd=q).stdout
    index = out.split("# Modes", 1)[1].split("# Live state", 1)[0]
    assert [ln.split("**")[1] for ln in index.splitlines() if ln.startswith("- **")] == MODES
    assert "- **quick**: (house) " in index and "brainstorm" not in index


def test_orient_static_plus_live(tmp_path: Path) -> None:
    q = bare(tmp_path)
    r = ok("ai", "orient", cwd=q)
    assert r.output.startswith("# Orientation: working in a quilt")
    assert "# Live state" in r.output and "- status: " in r.output and "prefix `dm`" in r.output
    assert "- undigested citekeys: " in r.output and "- open sessions: none" in r.output


def test_the_orientation_opens_with_what_must_not_be_missed(tmp_path: Path) -> None:
    """Claude Code's Bash tool saves anything over 30,000 bytes to a file and shows the whole lines of its first 2,000 (measured on 2.1.312), and `loom ai orient` is longer than that, so agents searched the file and missed the rules. So the opening fits inside what survives, and says to read the rest whole."""
    q = bare(tmp_path)
    said = ok("ai", "orient", cwd=q).stdout
    assert len(said.encode()) > 30_000, "the orientation now fits a shell's reply: this opening may be unnecessary"
    kept = said.encode()[:2_000].decode(errors="ignore").rsplit("\n", 1)[0]
    opening = kept[: kept.index("You are working in a **quilt**")]
    for rule in ("read that file whole", '--as "Claude Code Agent"', "`loom accept`", "`loom session say`", "`loom annotate`", "`config.toml`"):  # fmt: skip
        assert rule in opening, rule
    assert "server signs for you" in opening


def test_session_new_opens_a_session_and_orient_prints_its_chat(tmp_path: Path) -> None:
    q = bare(tmp_path)
    r = ok("session", "new", "--name", "Referee of dm-0003", cwd=q, env=FIXED)
    sid = r.stdout.split()[0]
    assert sid == "s-2026-09-16-p9z37z"  # the id is minted, never slugified from the title
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
    second = ok("session", "new", "--name", "Referee of dm-0003", cwd=q, env=FIXED).stdout.split()[0]
    assert second == "s-2026-09-16-cd0j88"  # two sessions may share a title; the id is what distinguishes them


def test_sessions_listed_by_title_and_addressed_by_part_of_one(tmp_path: Path) -> None:
    """A session is addressed by what the author called it; remembering the minute it opened is not a workflow."""
    q = bare(tmp_path)
    assert ok("session", "list", cwd=q).output.startswith("no sessions yet")
    ref = ok("session", "new", "--name", "Referee of the parity theorem", cwd=q, env=FIXED).stdout.split()[0]
    other = ok("session", "new", "--name", "Ingest of Hartshorne", cwd=q, env=FIXED).stdout.split()[0]
    assert ref != other
    listing = ok("session", "list", cwd=q).output
    assert f"{ref}  Referee of the parity theorem" in listing
    assert f"{other}  Ingest of Hartshorne" in listing

    # "Referee **of**…" and "Ingest **of**…": named, not guessed
    refused("ai", "annotations", "--session", "of", cwd=q, code=2, match="matches 2 sessions")

    ok("session", "rename", "parity", "--name", "Parity, revisited", cwd=q)
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
        "--as",
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
    sid = ok("session", "new", cwd=q, env=FIXED).stdout.split()[0]
    rel = f".loom/sessions/{sid}"
    for code, args in (
        (0, ("search", "orbit")),
        (0, ("deps", "dm-0003")),
        (0, ("downstream", "dm-0001")),
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
        "loom downstream dm-0001",
        "loom lint",
        "loom status",
    ]
    assert commands[-1] == "loom search gadget"


def test_threads_from_sessions_in_manifest_and_sessions_not_scanned(tmp_path: Path) -> None:
    q = bare(tmp_path)
    sid = ok("session", "new", "--name", "referee dm-0003", cwd=q, env=FIXED).stdout.split()[0]
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
        "--as",
        "An Agent",
        cwd=q,
        env=dict(FIXED, AI_AGENT="1"),
    )
    ok("session", "say", "Refereed dm-0003; one objection.", "--session", sid, "--as", "Referee Agent", cwd=q)
    (q / rel / "orbit-counts.py").write_text("print(2)\n# 2\n")  # a script a report cites, kept in the session
    ok("build", cwd=q)
    m = json.loads((q / ".loom/build" / "manifest.json").read_text())
    t = m["threads"][sid]
    assert t["kind"] == "session" and t["created"] == "2026-09-16T14:02:00Z"
    assert t["targets"] == ["dm-0003/proof"] and t["discarded"] is False
    # the conversation is not in the manifest, which every viewer polls; the build pages it beside it
    assert "messages" not in t
    page = json.loads((q / ".loom/build" / "transcripts" / sid / "1.json").read_text())
    assert [(e["who"], e["body_html"]) for e in page["events"]] == [
        ("Referee Agent", "<p>Refereed dm-0003; one objection.</p>")
    ]
    kinds = {a["name"]: a["kind"] for a in t["attachments"]}
    assert kinds == {"annotations": "annotations", "orbit-counts.py": "file"}  # reading leaves no file
    assert "pipeline" not in t  # a report is a transcript message, not a file the build indexes
    assert [entry["command"] for entry in t["log"]][:2] == [
        "loom source dm-0003 --closure",
        "loom annotate dm-0003/proof --quote --kind objection",
    ]
    assert any(s["kind"] == "thread" and s["key"] == t["id"] for s in m["search"])
    # a person writing in the same session is a participant in the same thread, which is the point of the split
    ok("annotate", "dm-0002", "Mine.", "--as", "Tom", "--session", sid, cwd=q, env=FIXED)
    ok("build", cwd=q)
    m2 = json.loads((q / ".loom/build" / "manifest.json").read_text())
    again = m2["threads"][sid]
    assert {"kind": "person", "id": "Tom"} in again["participants"]
    assert {"kind": "agent", "id": "An Agent"} in again["participants"]
    # a .tex file in a session is not scanned: an id it repeats is no duplicate (test_lint_exit_codes is the control)
    (q / rel / "scratch.tex").write_text("\\begin{lemma}\\label{dm-0001}\ndup\n\\end{lemma}\n")
    assert "duplicate-id" not in ok("lint", cwd=q).output


def test_the_session_flag_works_from_a_subdirectory(tmp_path: Path) -> None:
    q = bare(tmp_path)
    sid = ok("session", "new", "--name", "sub", cwd=q, env=FIXED).stdout.split()[0]
    rel = f".loom/sessions/{sid}"
    ok("search", "gadget", "--session", sid, cwd=q / "drafting" / "nodes")  # from a subdirectory
    ok("source", "dm-0003", "--session", sid, cwd=q / "drafting" / "nodes")
    ok(
        "annotate",
        "dm-0003",
        "Fine.",
        "--kind",
        "note",
        "--session",
        sid,
        "--as",
        "A. Author",
        cwd=q / "drafting" / "nodes",
        env=FIXED,
    )
    log = (q / rel / "run.log").read_text()
    assert "loom search gadget" in log and "loom source dm-0003" in log and "loom annotate dm-0003" in log
    assert (q / ".loom/annotations" / "log.jsonl").is_file()  # the record lands in the quilt's one log
    assert not (q / "drafting" / "nodes" / ".loom/ai").exists()  # nothing landed relative to the shell's directory


def test_the_allow_list_and_the_permission_file_cannot_disagree(tmp_path: Path) -> None:
    """One table, `AGENT_COMMANDS`, decides what an agent may run: the deny list is its complement, so a command added later is the author's until it is admitted, and the settings file and the prose in rules.md are rendered from it (DR-173)."""
    from loom.ai.layout import (
        AGENT_COMMANDS,
        author_commands,
        command_tree,
        help_commands,
        permissions_json,
        settings_deny_paths,
    )
    from loom.scan.quilt import QuiltConfig

    every = set(command_tree())
    assert AGENT_COMMANDS < every, "the allow-list names commands loom does not have"
    assert set(author_commands()) == every - AGENT_COMMANDS  # derived, never listed

    # the deny list is the complement, and the two variants differ only by the server's tools
    denied_paths = settings_deny_paths(QuiltConfig(), shell=True)
    denied = {d.removeprefix("Bash(loom ").removesuffix("*)") for d in denied_paths if d.startswith("Bash(loom ")}
    assert denied == every - AGENT_COMMANDS
    shell = json.loads(permissions_json(QuiltConfig(), shell=True))["permissions"]
    assert {r.removeprefix("Bash(loom ").removesuffix("*)") for r in shell["allow"] if r.startswith("Bash(")} == (
        AGENT_COMMANDS | set(help_commands())
    )
    over_mcp = json.loads(permissions_json(QuiltConfig()))["permissions"]
    assert over_mcp["deny"] == shell["deny"] and set(over_mcp["allow"]) - set(shell["allow"]) == {"mcp__loom__*"}

    # what the table must not admit: every command that writes into the quilt outside the session and .loom/build/, the history's restore among them, so `loom canonise` cannot walk past a deny on `loom canonize`
    writes_outside_a_session = {
        "accept", "atomize", "import", "stamp", "fork",
        "revert", "live", "mv", "linearize", "upgrade", "ai init",
        "library add", "library verify", "library discard", "library ignore", "library import", "library drop",
    }  # fmt: skip
    missing = sorted(writes_outside_a_session - denied)
    assert not missing, f"agent-writable commands missing from the deny list: {missing}"
    # and the files those commands own, which a direct edit would otherwise reach
    for d in (".loom/digests", ".loom/annotations", ".loom/history", ".loom/ai", ".loom/retired", ".loom/since"):
        assert f"Edit(/{d}/**)" in denied_paths, d
    assert "Edit(/.loom/reference-notes.jsonl)" in denied_paths

    q = bare(tmp_path)
    assert (q / ".claude" / "settings.json").read_text() == permissions_json(QuiltConfig())
    rules = (q / ".loom/ai" / "rules.md").read_text()
    for c in sorted(AGENT_COMMANDS):
        assert f"`loom {c}`" in rules, c  # the prose is the same table
    assert "{allowed_commands}" not in rules


def test_an_agent_in_a_shell_may_ask_loom_what_it_offers(tmp_path: Path) -> None:
    """The orientation sends a shell agent to `loom --help`, which was refused again and again because the rules named only commands; a rule for `session new` does not reach `loom session --help` either. The help is admitted in both clients' files, is no rule's to deny, and loom answers it under a marker with the commands an agent may run marked."""
    from loom.ai.layout import codex_rules, help_commands, permissions_json
    from loom.scan.quilt import QuiltConfig

    assert help_commands() == ["--help", "-h", "ai --help", "ai -h", "session --help", "session -h"]
    rules = json.loads(permissions_json(QuiltConfig(), shell=True))["permissions"]
    codex = codex_rules()
    for typed in help_commands():
        assert f"Bash(loom {typed}*)" in rules["allow"], typed
        assert f"Bash(loom {typed}*)" in json.loads(permissions_json(QuiltConfig()))["permissions"]["allow"], typed
        assert not [d for d in rules["deny"] if typed.startswith(d.removeprefix("Bash(loom ").removesuffix("*)"))], (
            typed
        )
        pattern = ", ".join(json.dumps(w) for w in ["loom", *typed.split()])
        assert f'prefix_rule(pattern = [{pattern}], decision = "allow")' in codex, typed
    q = bare(tmp_path)
    for typed in help_commands():
        said = ok(*typed.split(), cwd=q, env={"CLAUDECODE": "1"}).stdout
        assert said.startswith("Usage: "), typed
    assert "status*" in ok("--help", cwd=q, env={"CLAUDECODE": "1"}).stdout


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
    assert 'prefix_rule(pattern = ["loom"], decision = "forbidden")' not in rules
    assert 'prefix_rule(pattern = ["rm"], decision = "forbidden")' in rules
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

    options = dict(walk(main))
    # who acts is `--as` everywhere (K2); `--author` names nothing an agent may pass
    assert not [c for c in AGENT_COMMANDS if "--author" in options.get(c, set())]
    writers = {"annotate", "session say", "session new", "library relate", "library propose"}
    assert writers <= AGENT_COMMANDS
    assert not [c for c in sorted(writers) if "--as" not in options[c] and c != "library propose"]


def test_every_command_the_agent_is_told_to_run_is_allowed() -> None:
    """A command the shipped documents tell the agent to run is one it may run, unless they name it to be refused (0.14 study F18)."""
    from loom.ai.layout import AGENT_COMMANDS, author_commands

    assets = Path(__file__).parents[2] / "src" / "loom" / "assets" / "ai"
    docs = " ".join(p.read_text() for p in assets.rglob("*.md"))
    # the author's own verbs are named to be refused; `session use` is named beside `--session`, which the agent uses
    named_to_refuse = {
        "accept",
        "library add",
        "library verify",
        "library discard",
        "library ignore",
        "library drop",
        "library import",
        "session delete",
        "ai discard",
        "sync publish",
        "sync incorporate",
        "ai init",
        "upgrade",
        "session use",
        "adopt",  # the orientation names incorporation as author-only
        "history restore",
    }
    told = {c for c in author_commands() if re.search(rf"`loom {re.escape(c)}\b", docs)}
    assert told <= named_to_refuse, sorted(told - named_to_refuse)
    assert "library read" in AGENT_COMMANDS


def test_findings_for_a_run_include_what_the_author_decided(tmp_path: Path) -> None:
    """`ai annotations` shows the author's decision on each of the session's proposals, so an agent that reattaches need not ask `library why` id by id."""
    from tests.unit._quilts import mapped, propose

    q, ck = mapped(tmp_path)
    runname = ok("session", "new", "--name", "r", cwd=q).stdout.split()[0]
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "Y", session=runname)
    ok("library", "discard", f"{ck}-thm-1.1", "--why", "wrong theorem", "--as", "i", cwd=q)
    out = ok("ai", "annotations", "--session", runname, cwd=q).output
    assert f"{ck}-thm-1.1" in out and "discarded -- wrong theorem" in out


def test_upgrade_leaves_a_loom_sty_alone(tmp_path: Path) -> None:
    """A document carries loom's macro block, so upgrade writes no loom.sty; one a person keeps beside a document is theirs, and upgrade neither replaces nor records it."""
    import loom.ai.layout as layout

    q = bare(tmp_path)
    assert not (q / "loom.sty").exists() and "loom.sty" not in layout.read_versions(q)
    kept = q / "drafting" / "loom.sty"
    kept.write_text("% my own\n")
    r = json_of("upgrade", "--json", cwd=q)
    assert "loom.sty" not in r["written"] and kept.read_text() == "% my own\n" and not (q / "loom.sty").exists()


def test_ai_annotations_after_a_discard_says_how_many_are_withdrawn(tmp_path: Path) -> None:
    """T7: a session whose annotations were all withdrawn is not "no annotations yet"."""
    q = demo(tmp_path)
    sid = "s-2026-09-16-cd0j88"
    before = json_of("ai", "annotations", "--session", sid, "--json", cwd=q)["annotations"]
    assert before
    ok("ai", "discard", sid, cwd=q)
    said = ok("ai", "annotations", "--session", sid, cwd=q).stdout.splitlines()[0]
    assert "no annotations yet" not in said
    assert f"{len(before)} withdrawn" in said and "--all lists them" in said, said


def test_a_stale_or_conflicted_agent_document_names_a_command_that_runs_as_printed(tmp_path: Path) -> None:
    """T3: `ai drafts` and `ai refresh` quote a document's name, so a name with a space survives a paste."""
    import shlex

    from loom.scan.quilt import save_author
    from tests.helpers import run

    save_author("Tester")
    q = demo(tmp_path)
    ok("draft", "drafting/main.tex", "--ai", "Referee Agent.tex", cwd=q)
    copy = q / ".loom" / "copies" / "Referee Agent.tex"
    copy.write_text(copy.read_text().replace("restricts to a map", "restricts, by the agent, to a map"))
    main = q / "drafting" / "main.tex"
    main.write_text(main.read_text().replace("restricts to a map", "restricts, by the author, to a map"))
    fixes = [f for c in json_of("ai", "drafts", "--json", cwd=q)["groups"][0]["items"] for f in c.get("fixes", [])]
    assert fixes and all(shlex.split(f)[3:] == [".loom/copies/Referee Agent.tex"] for f in fixes), fixes
    refreshed = run("ai", "refresh", "Referee Agent.tex", cwd=q)
    assert refreshed.exit_code == 1, refreshed.output
    line = next(ln for ln in refreshed.stdout.splitlines() if "loom ai refresh" in ln)
    argv = shlex.split(line.split(": ", 1)[1])
    assert argv[:3] == ["loom", "ai", "refresh"] and len(argv) == 4, line
    assert run(*argv[1:], cwd=q).exit_code == 1  # the same conflict, not an unexpected argument


def test_a_withdrawal_carries_its_reason_and_is_not_made_twice(tmp_path: Path) -> None:
    """K2: `ai discard` took no `--why`, so every withdrawal read "no reason given"; T7: run twice, it said "withdrew" twice and recorded it twice."""
    q = demo(tmp_path)
    sid = "s-2026-09-16-cd0j88"
    log = q / ".loom/annotations" / "log.jsonl"
    ok("ai", "discard", sid, "--why", "an early, mistaken pass", cwd=q)
    lines = log.read_text()
    again = ok("ai", "discard", sid, cwd=q)
    assert again.stdout.startswith(f"already withdrawn: {sid}; nothing written") and log.read_text() == lines
    listed = ok("ai", "annotations", "--session", sid, "--all", cwd=q).stdout
    assert "withdrawn: an early, mistaken pass" in listed and "no reason given" not in listed, listed


def test_ai_annotations_says_who_wrote_each_and_lines_its_columns_up(tmp_path: Path) -> None:
    """An agent answers the author's annotations and may edit its own, so it must tell them apart; T2: the columns did not line up."""
    q = demo(tmp_path)
    sid = "s-2026-09-16-cd0j88"
    rows = json_of("ai", "annotations", "--session", sid, "--json", cwd=q)["annotations"]
    assert rows and all(set(r["author"]) == {"kind", "id"} for r in rows), rows
    text = ok("ai", "annotations", "--session", sid, cwd=q).stdout
    lines = [ln for ln in text.splitlines() if ln.startswith("  a-")]
    assert lines and all(f"by {r['author']['id']}" in text for r in rows)
    assert len({ln.index(" by ") for ln in lines}) == 1, lines  # one column, whatever the row


def test_the_deny_list_is_rendered_into_the_permission_file_beside_what_is_always_protected() -> None:
    """`[agents] deny` adds to loom's own table and never replaces it: a directory pattern, a file pattern at any depth and an anchored one each become Edit denies; a negation is refused rather than rendered, since Claude Code lets a deny beat any allow."""
    from loom.ai.layout import permissions_json
    from loom.scan.quilt import QuiltConfig

    config = QuiltConfig.from_dict(
        {"quilt": {}, "agents": {"deny": ["paper/", "*.bib", "/notes/plan.md", "!paper/x.tex"]}}
    )
    assert config.agents_deny == ["paper/", "*.bib", "/notes/plan.md"]
    assert any("negates" in w for w in config.warnings)
    deny = json.loads(permissions_json(config))["permissions"]["deny"]
    for rule in (
        "Edit(/**/paper/**)",
        "Edit(/**/*.bib)",
        "Edit(/**/*.bib/**)",
        "Edit(/notes/plan.md)",
        "Edit(/notes/plan.md/**)",
    ):
        assert rule in deny, rule
    assert "Edit(/.loom/annotations/**)" in deny and "Edit(/config.toml)" in deny
    assert not any("paper/x.tex" in r for r in deny)


def test_an_old_instruction_line_is_replaced_where_it_stands(tmp_path: Path) -> None:
    """A root file an older loom wrote keeps one line, the current one, where the old one stood, and the person's text around it."""
    from loom.ai.layout import MCP_LINE, OLD_LINES, ensure_root_line

    (tmp_path / "CLAUDE.md").write_text(
        f"# Mine\n\n{OLD_LINES[0]}\n\nMore of mine.\n{OLD_LINES[1]}\n", encoding="utf-8"
    )
    assert "CLAUDE.md" in ensure_root_line(tmp_path)
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == f"# Mine\n\n{MCP_LINE}\n\nMore of mine.\n"
    assert "CLAUDE.md" not in ensure_root_line(tmp_path)
    for old in OLD_LINES[2:]:
        (tmp_path / "CLAUDE.md").write_text(f"{old}\n", encoding="utf-8")
        ensure_root_line(tmp_path)
        assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == f"{MCP_LINE}\n"
