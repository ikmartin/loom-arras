"""The AI layer (book 11): layout and vendor files, upgrade, orientation, runs and their logs, promotion, the outside-writes check, and threads in the manifest."""

from __future__ import annotations

import json
import os
import re
import stat
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
    assert run("init", str(tmp_path / "q"), "--demo", "--no-git", cwd=tmp_path).exit_code == 0
    q = tmp_path / "q"
    for p in list((q / "ai").glob("**/*")) if (q / "ai").exists() else []:
        pass
    if (q / "ai").exists():  # the shipped demo carries its layer; start these tests from a bare quilt
        import shutil

        shutil.rmtree(q / "ai")
        for rel in ("CLAUDE.md", "AGENTS.md"):
            (q / rel).unlink(missing_ok=True)
        shutil.rmtree(q / ".claude", ignore_errors=True)
        gi = q / ".gitignore"
        gi.write_text("\n".join(ln for ln in gi.read_text().splitlines() if "bundle-" not in ln) + "\n")
    r = run("ai", "init", *flags, cwd=q)
    assert r.exit_code == 0, r.output
    return q


def test_ai_init_layout_and_vendor_files(tmp_path: Path) -> None:
    q = demo(tmp_path)
    for rel in ("ai/README.md", "ai/orientation.md", "ai/.loom-modes-version", "CLAUDE.md", "AGENTS.md"):
        assert (q / rel).is_file(), rel
    assert (q / "ai" / "runs").is_dir()
    assert {p.stem for p in (q / "ai" / "modes").glob("*.md")} == set(MODES)
    root_text = (q / "CLAUDE.md").read_text()
    assert root_text == (q / "AGENTS.md").read_text() and "loom ai orient" in root_text and "ai/runs/" in root_text
    assert "# Orientation: working in a quilt" in (q / "ai" / "orientation.md").read_text()
    assert not (q / ".claude").exists()
    again = run("ai", "init", cwd=q)
    assert again.exit_code == 2 and "loom upgrade" in again.output


def test_ai_init_gitignore_line(tmp_path: Path) -> None:
    q = demo(tmp_path)
    lines = (q / ".gitignore").read_text().splitlines()
    assert lines.count("ai/runs/*/bundle-*.tex") == 1
    assert run("upgrade", cwd=q).exit_code == 0
    assert (q / ".gitignore").read_text().splitlines().count("ai/runs/*/bundle-*.tex") == 1


def test_ai_init_permissions_generated(tmp_path: Path) -> None:
    q = demo(tmp_path, "--permissions")
    data = json.loads((q / ".claude" / "settings.json").read_text())
    deny = data["permissions"]["deny"]
    allow = data["permissions"]["allow"]
    for d in ("nodes", "drafts", "refs", "comments", ".loom", "ai/modes"):
        assert f"Edit(/{d}/**)" in deny and f"Write(/{d}/**)" in deny, d
    assert "Edit(/ai/runs/**)" in allow and "Write(/build/**)" in allow
    assert any(rule.startswith("Bash(loom accept") for rule in deny) and any("promote" in rule for rule in deny)


def test_ai_init_skills_generated_pointer_only(tmp_path: Path) -> None:
    q = demo(tmp_path, "--skills")
    blocks = (q / "ai" / "modes" / "blocks.md").read_text()
    block_names = re.findall(r"^- \[([a-z-]+)\]", blocks, re.M)
    assert len(block_names) > 20
    for mode in MODES:
        if mode == "blocks":
            continue
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


def test_modes_templates_present_and_contracts_listed(tmp_path: Path) -> None:
    q = demo(tmp_path)
    for mode in MODES:
        text = (q / "ai" / "modes" / f"{mode}.md").read_text()
        if mode == "blocks":
            assert text.startswith("# Blocks and standing rules") and "## Never" in text
            continue
        assert text.startswith(f"# Mode: {mode}\n\n## Before you begin\n")
        assert "$LOOM_RUN" in text and "## Checklist" in text
        assert re.search(r"^- \[ \] Nothing was written outside `\$LOOM_RUN`\.", text, re.M)
        if mode not in ("quick",):
            assert "## Output" in text and "thread.md" in text


def test_upgrade_preserves_edited_modes(tmp_path: Path) -> None:
    q = demo(tmp_path)
    referee = q / "ai" / "modes" / "referee.md"
    referee.write_text(referee.read_text() + "\n## House rule\nAlways check the dimension count.\n")
    audit = q / "ai" / "modes" / "audit.md"
    original_audit = audit.read_text()
    (q / "ai" / "orientation.md").write_text("stale orientation\n")
    r = run("upgrade", cwd=q)
    assert r.exit_code == 0, r.output
    assert "kept ai/modes/referee.md (edited)" in r.output and "wrote ai/orientation.md" in r.output
    assert "House rule" in referee.read_text()  # untouched
    assert audit.read_text() == original_audit
    assert "# Orientation: working in a quilt" in (q / "ai" / "orientation.md").read_text()
    versions = (q / "ai" / ".loom-modes-version").read_text()
    assert "referee.md" in versions and "audit.md" in versions
    # the shipped text has not changed in this test, so no .new is written; simulate a changed shipped version
    import loom.ai.layout as layout

    shipped = layout.shipped_modes()
    shipped["referee.md" and "referee"] = shipped["referee"] + "\n## New shipped section\n"
    original = layout.shipped_modes
    layout.shipped_modes = lambda: shipped  # type: ignore[assignment]
    try:
        r2 = run("upgrade", cwd=q)
    finally:
        layout.shipped_modes = original  # type: ignore[assignment]
    assert r2.exit_code == 0 and "referee.md.new" in r2.output
    assert (
        "House rule" in referee.read_text()
        and "New shipped section" in (q / "ai" / "modes" / "referee.md.new").read_text()
    )


def test_orient_static_plus_live(tmp_path: Path) -> None:
    q = demo(tmp_path)
    r = run("ai", "orient", cwd=q)
    assert r.exit_code == 0, r.output
    assert r.output.startswith("# Orientation: working in a quilt")
    assert "# Live state" in r.output and "- status: " in r.output and "prefix `dm`" in r.output
    assert "- undigested citekeys: " in r.output and "- open runs: none" in r.output


def test_run_start_creates_dir_and_toml_and_orient_run(tmp_path: Path) -> None:
    q = demo(tmp_path)
    r = run("ai", "start", "referee-dm-0003", cwd=q, env=FIXED)
    assert r.exit_code == 0, r.output
    rel = r.output.strip().splitlines()[0]
    assert rel == "ai/runs/2026-09-16T14-02-referee-dm-0003"
    toml = (q / rel / "run.toml").read_text()
    assert toml == 'created = 2026-09-16T14:02:00Z\nslug = "referee-dm-0003"\ndiscarded = false\n'
    (q / rel / "thread.md").write_text(
        "# Thread: referee dm-0003\n\n## 2026-09-16 14:10 first pass\n\nAsked: referee. Did: read the bundle.\n"
    )
    assert run("bundle", "dm-0003", "--run", rel, cwd=q).exit_code == 0
    log = (q / rel / "run.log").read_text()
    assert "loom bundle dm-0003" in log and (q / rel / "bundle-dm-0003.tex").is_file()
    o = run("ai", "orient", "--run", rel, cwd=q)
    assert o.exit_code == 0, o.output
    assert f"# Your run: `{rel}`" in o.output and "first pass" in o.output and "loom bundle dm-0003" in o.output
    assert "bundle-dm-0003.tex" in o.output
    assert "loom ai orient" in (q / rel / "run.log").read_text()
    second = run("ai", "start", "referee-dm-0003", cwd=q, env=FIXED).output.strip()
    assert second == rel + "-2"  # a run started in the same minute with the same slug gets a suffix


def test_run_log_appended_by_run_flag(tmp_path: Path) -> None:
    q = demo(tmp_path)
    rel = run("ai", "start", cwd=q, env=FIXED).output.strip()
    assert rel.endswith("-run")
    for args in (("search", "orbit"), ("deps", "dm-0003"), ("unravel", "dm-0001"), ("lint",), ("status",)):
        r = run(*args, "--run", rel, cwd=q)
        assert r.exit_code in (0, 1), (args, r.output)
    env = dict(FIXED, LOOM_RUN=rel)
    assert run("search", "gadget", cwd=q, env=env).exit_code == 0  # LOOM_RUN is the default for --run
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


def test_run_launch_agent_if_configured(tmp_path: Path) -> None:
    q = demo(tmp_path)
    fake = tmp_path / "fakeagent"
    fake.write_text('#!/bin/sh\nprintf \'%s\\n\' "$LOOM_RUN" "$#" "$1" > "$LOOM_RUN/launched.txt"\n')
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    cfg = q / "config.toml"
    assert 'agent = ""' in cfg.read_text()
    cfg.write_text(cfg.read_text().replace('agent = ""', f'agent = "{fake}"', 1))
    r = run("ai", "start", "quick", cwd=q, env=FIXED)
    assert r.exit_code == 0, r.output
    rel = r.output.strip().splitlines()[0]
    assert "(launching:" in r.output
    launched = (q / rel / "launched.txt").read_text().splitlines()
    assert launched[0] == rel and launched[1] == "1" and f"loom ai orient --run {rel}" in launched[2]
    cfg.write_text(cfg.read_text().replace(f'agent = "{fake}"', 'agent = "no-such-agent-binary"'))
    r2 = run("ai", "start", "quick", cwd=q, env=FIXED)
    assert r2.exit_code == 2 and "not on PATH" in r2.output and "ai/runs/" in r2.output  # refused, path printed


def test_promote_draft_allocates_or_checks_id(tmp_path: Path) -> None:
    q = demo(tmp_path)
    rel = run("ai", "start", "draft", cwd=q, env=FIXED).output.strip()
    draft = q / rel / "draft-lemma.tex"
    draft.write_text(
        "% !LOOM author: agent\n\\begin{lemma}[Drafted]\n\\uses{dm-0001}\nEvery gadget is a widget.\n\\end{lemma}\n\\begin{proof}\nBy definition.\n\\end{proof}\n"
    )
    before = draft.read_text()
    r = run("ai", "promote", str(draft), cwd=q)
    assert r.exit_code == 0, r.output
    m = re.search(r"promoted draft-lemma.tex -> nodes/(dm-[0-9A-Z]{4}).tex \(allocated (dm-[0-9A-Z]{4})\)", r.output)
    assert m and m.group(1) == m.group(2), r.output
    nid = m.group(1)
    node = (q / "nodes" / f"{nid}.tex").read_text()
    assert f"\\begin{{lemma}}[Drafted]\\label{{{nid}}}\n" in node
    assert draft.read_text() == before  # the run's file is never modified
    # a draft carrying an id that is already allocated is refused
    taken = q / rel / "draft-dm-0001.tex"
    taken.write_text("\\begin{definition}\\label{dm-0001}\nClash.\n\\end{definition}\n")
    r2 = run("ai", "promote", str(taken), cwd=q)
    assert r2.exit_code == 1 and "already allocated" in r2.output
    # a draft carrying the id of a skeleton the author created with loom new replaces the skeleton
    assert run("new", "lemma", "Planned", cwd=q).exit_code == 0
    skel = next(p for p in (q / "nodes").glob("dm-*.tex") if "Planned" in p.read_text())
    sid = skel.stem
    planned = q / rel / f"draft-{sid}.tex"
    planned.write_text(f"\\begin{{lemma}}[Planned]\\label{{{sid}}}\nNow written.\n\\end{{lemma}}\n")
    r3 = run("ai", "promote", str(planned), cwd=q)
    assert r3.exit_code == 0, r3.output
    assert "replaced the author's skeleton" in r3.output and "Now written." in skel.read_text()


def test_promote_digest_refuses_existing(tmp_path: Path) -> None:
    q = demo(tmp_path)
    rel = run("ai", "start", "ingest", cwd=q, env=FIXED).output.strip()
    ingest = q / rel / "ingest-Man12.tex"
    ingest.write_text((q / "refs" / "Man12.tex").read_text().replace("method: manual", "method: ingest"))
    r = run("ai", "promote", str(ingest), cwd=q)
    assert r.exit_code == 1 and "refs/Man12.tex exists" in r.output and "--replace" in r.output
    r2 = run("ai", "promote", str(ingest), "--replace", cwd=q)
    assert r2.exit_code == 0, r2.output
    assert "-% !LOOM method: manual" in r2.output and "+% !LOOM method: ingest" in r2.output  # the diff was shown
    assert "method: ingest" in (q / "refs" / "Man12.tex").read_text()
    new = q / rel / "ingest-Har77.tex"
    new.write_text(
        "% !LOOM digest: Har77\n% !LOOM source: manual\n% !LOOM method: ingest\n\\section*{Overview}\nHartshorne.\n"
    )
    r3 = run("ai", "promote", str(new), cwd=q)
    assert r3.exit_code == 0 and (q / "refs" / "Har77.tex").is_file()


def test_ai_check_reports_outside_writes(tmp_path: Path) -> None:
    q = demo(tmp_path)
    r = run("ai", "start", "audit", cwd=q)  # the real clock: the check compares mtimes with the run's created time
    rel = r.output.strip()
    started = time.time()
    (q / rel / "audit-dm-0003.notes.md").write_text("## [summary]\nfine\n")
    ok = run("ai", "check", rel, cwd=q)
    assert ok.exit_code == 0 and "ok" in ok.output
    node = q / "nodes" / "dm-0002.tex"
    node.write_text(node.read_text() + "% touched by an agent\n")
    os.utime(node, (started + 5, started + 5))
    bad = run("ai", "check", rel, cwd=q)
    assert bad.exit_code == 1 and "loom:agent-wrote-outside-run" in bad.output and "nodes/dm-0002.tex" in bad.output
    assert node.read_text().endswith("% touched by an agent\n")  # reported, never reverted
    node.write_text(node.read_text().replace("% touched by an agent\n", ""))
    os.utime(node, (started - 100, started - 100))
    draft = q / rel / "draft-x.tex"
    draft.write_text("\\begin{lemma}[Promoted]\nP.\n\\end{lemma}\n")
    p = run("ai", "promote", str(draft), cwd=q)
    assert p.exit_code == 0, p.output
    assert "loom ai promote draft-x.tex -> nodes/" in (q / rel / "run.log").read_text()
    assert run("ai", "check", rel, cwd=q).exit_code == 0  # the promoted node is the author's move, not an agent write


def test_threads_from_runs_in_manifest_and_runs_not_scanned(tmp_path: Path) -> None:
    q = demo(tmp_path)
    rel = run("ai", "start", "referee-dm-0003", cwd=q, env=FIXED).output.strip()
    assert run("bundle", "dm-0003", "--run", rel, cwd=q).exit_code == 0
    r = run(
        "comment",
        "dm-0003/proof",
        "Closedness is asserted.",
        "--quote",
        "diagonal is closed",
        "--kind",
        "objection",
        "--run",
        rel,
        cwd=q,
        env=FIXED,
    )
    assert r.exit_code == 0, r.output
    (q / rel / "thread.md").write_text(
        "# Thread: referee dm-0003\n\nOpening note.\n\n## 2026-09-16 14:31 referee\n\nRefereed dm-0003; one objection.\n"
    )
    (q / rel / "referee-dm-0003.notes.md").write_text("## [summary]\nOne objection.\n")
    assert run("build", cwd=q).exit_code == 0
    m = json.loads((q / "build" / "manifest.json").read_text())
    t = m["threads"]["2026-09-16T14-02-referee-dm-0003"]
    assert t["kind"] == "run" and t["title"] == "referee dm-0003" and t["created"] == "2026-09-16T14:02:00Z"
    assert t["targets"] == ["dm-0003/proof"] and t["discarded"] is False
    assert [msg["body_html"] for msg in t["messages"]][0] == "<p>Opening note.</p>"
    assert t["messages"][1]["time"] == "2026-09-16T14:31:00Z" and "one objection" in t["messages"][1]["body_html"]
    kinds = {a["name"]: a["kind"] for a in t["attachments"]}
    assert kinds == {
        "annotations.json": "annotations",
        "bundle-dm-0003.tex": "bundle",
        "referee-dm-0003.notes.md": "notes",
    }
    assert [entry["command"] for entry in t["log"]][:2] == [
        "loom bundle dm-0003",
        "loom comment dm-0003/proof --quote --kind objection",
    ]
    assert any(s["kind"] == "thread" and s["key"] == t["id"] for s in m["search"])
    assert "comments/the-loom-demo/2026-09-16" in m["threads"]
    # the bundle copied into the run is not a master and none of its ids are duplicates
    lint = run("lint", cwd=q).output
    assert "duplicate-id" not in lint and f"{rel}/bundle-dm-0003.tex" not in lint
