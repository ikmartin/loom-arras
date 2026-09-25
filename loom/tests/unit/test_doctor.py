"""`loom doctor` (book 12.2, DR-288-ikmartin): every item in each of its states, the bundle from each source, the JSON's shape, and the exit codes.

Each case runs on a clean PATH holding only the fake toolchain, a fake git and whatever the case writes, so nothing depends on what `/usr/bin` holds; the author comes from a user config and the bundle from LOOM_ARRAS_BUNDLE unless the case is about them.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import types
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from loom.version import INTERFACE_VERSION
from tests.helpers import edit, exits, json_of, ok, run, the

FAKE_GIT = """import sys
if "--version" in sys.argv:
    print("git version 2.0 (fake)")
sys.exit(0 if "--version" in sys.argv else 1)
"""
HANG = "import time\ntime.sleep(60)\n"
XPDF = """import sys
if "-v" in sys.argv:
    sys.stderr.write("pdftotext version 4.05\\n")
    sys.exit(0)
if "-bbox-layout" in sys.argv:
    sys.stderr.write("Usage: pdftotext [options] <PDF-file> [<text-file>]\\n")
    sys.exit(99)
"""
REAL_GIT = shutil.which("git")


def stamp(commit: str = "abc1234", interface: int = INTERFACE_VERSION) -> str:
    return f"arras {commit} interface {interface} vendored 2026-09-24T00:00:00Z\n"


def bundle(d: Path, version: str | None = None) -> Path:
    """A bundle directory: an index.html, and a VERSION when given."""
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text("<!doctype html>", encoding="utf-8")
    if version is not None:
        (d / "VERSION").write_text(version, encoding="utf-8")
    return d


@dataclass
class Box:
    """The machine a case runs on: a clean PATH, a user config, a bundle, a directory outside any quilt."""

    tmp: Path
    bin: Path
    mp: pytest.MonkeyPatch

    def script(self, name: str, body: str) -> Path:
        p = self.bin / name
        p.unlink(missing_ok=True)
        p.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
        p.chmod(0o755)
        return p

    def drop(self, *names: str) -> None:
        for n in names:
            (self.bin / n).unlink()

    def empty(self) -> None:
        for p in self.bin.iterdir():
            p.unlink()

    def author(self, text: str | None) -> None:
        p = Path(os.environ["XDG_CONFIG_HOME"]) / "loom" / "config.toml"
        if text is None:
            p.unlink(missing_ok=True)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")

    def real_git(self) -> None:
        if REAL_GIT is None:
            pytest.skip("no git")
        self.bin.joinpath("git").unlink(missing_ok=True)
        self.bin.joinpath("git").symlink_to(REAL_GIT)


@pytest.fixture
def box(tmp_path: Path, fake_bin: Path, monkeypatch: pytest.MonkeyPatch) -> Box:
    b = Box(tmp_path, tmp_path / "bin", monkeypatch)
    b.bin.mkdir()
    for tool in os.listdir(fake_bin):
        (b.bin / tool).symlink_to(fake_bin / tool)
    b.script("git", FAKE_GIT)
    monkeypatch.setenv("PATH", str(b.bin))
    b.author('[author]\nname = "Ada"\n')
    monkeypatch.setenv("LOOM_ARRAS_BUNDLE", str(bundle(tmp_path / "arras-build", stamp())))
    (tmp_path / "away").mkdir()
    return b


def doctor(box: Box, *args: str, code: int | None = None, cwd: Path | None = None) -> dict[str, Any]:
    """`loom doctor --json ARGS` from `cwd` (default outside any quilt); asserts the exit code the items imply unless one is given."""
    r = run("doctor", "--json", *args, cwd=cwd or box.tmp / "away")
    import json

    data: dict[str, Any] = json.loads(r.stdout)
    want = code if code is not None else (2 if data["failing"] or ("--strict" in args and data["warnings"]) else 0)
    problems = [(i["name"], i["detail"]) for i in data["items"] if i["status"] != "ok"]
    assert r.exit_code == want, f"exit {r.exit_code}, expected {want}: {problems}"
    return data


def item(data: dict[str, Any], name: str) -> dict[str, Any]:
    found: dict[str, Any] = the(data["items"], lambda i: i["name"] == name, f"item {name}")
    return found


def quilt(box: Box) -> Path:
    """The demo quilt, which starts with every quilt item ok."""
    ok("init", str(box.tmp / "q"), "--demo", cwd=box.tmp)
    return box.tmp / "q"


# ---- machine: the tools


REQUIRED = ["latexmk", "pdflatex", "dvisvgm"]
OPTIONAL = ["latex", "xelatex", "lualatex", "bibtex", "biber", "kpsewhich", "pdftotext", "pdfinfo", "pdftocairo", "git"]


def test_every_tool_found_on_the_shim_is_ok(box: Box) -> None:
    data = doctor(box, code=0)
    for name in REQUIRED + OPTIONAL:
        got = item(data, name)
        assert (got["status"], got["path"]) == ("ok", str(box.bin / name)), got
        assert "fake" in got["detail"], got
    assert data["ok"] is True and data["failing"] == [] and data["warnings"] == []


@pytest.mark.parametrize(
    "name,status", [(n, "fail") for n in REQUIRED] + [(n, "warn") for n in OPTIONAL], ids=REQUIRED + OPTIONAL
)
def test_a_missing_tool_fails_when_required_and_warns_when_optional(box: Box, name: str, status: str) -> None:
    box.drop(name)
    got = item(doctor(box), name)
    assert (got["status"], got["path"]) == (status, None)
    assert got["detail"].startswith("not found: ")
    assert got["remedy"], got


def test_a_hung_tool_is_reported_not_waited_on(box: Box, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("loom.doctor.PROBE_TIMEOUT", 1.0)
    box.empty()  # nothing else to probe, so a slow machine cannot time out an honest tool
    box.script("latexmk", HANG)
    began = time.monotonic()
    got = item(doctor(box, code=2), "latexmk")
    assert time.monotonic() - began < 8
    assert got["status"] == "fail" and got["detail"].startswith("hung: -v did not answer in 1 s"), got
    assert "take" in got["remedy"] and str(box.bin / "latexmk") in got["remedy"]


def test_a_tool_that_cannot_start_fails(box: Box) -> None:
    p = box.bin / "dvisvgm"
    p.unlink()
    p.write_text("#!/nonexistent/interpreter\n", encoding="utf-8")
    p.chmod(0o755)
    got = item(doctor(box, code=2), "dvisvgm")
    assert got["status"] == "fail" and got["detail"].startswith("cannot run: "), got


def test_a_pdftotext_without_bbox_layout_fails(box: Box) -> None:
    box.script("pdftotext", XPDF)
    got = item(doctor(box, code=2), "pdftotext")
    assert got["status"] == "fail", got
    assert got["detail"].startswith("pdftotext version 4.05: no -bbox-layout"), got
    assert "poppler" in got["remedy"]


def biblatex(box: Box, version: str) -> None:
    """A biblatex.sty of `version` where a fake kpsewhich finds it."""
    sty = box.tmp / "texmf" / "biblatex.sty"
    sty.parent.mkdir(exist_ok=True)
    sty.write_text(f"\\def\\abx@date{{2024/03/21}}\n\\def\\abx@version{{{version}}}\n", encoding="utf-8")
    box.script(
        "kpsewhich",
        f"import sys\nif '--version' in sys.argv: print('kpathsea version 6.4.0')\nelse: print({str(sty)!r})\n",
    )


@pytest.mark.parametrize(
    "biber,biblatex_version,status,detail",
    [
        ("2.20", "3.20", "ok", "biber 2.20, biblatex 3.20"),
        ("2.19", "3.20", "warn", "biber 2.19, biblatex 3.20: by their version numbers they do not pair"),
        ("2.14", "3.18", "warn", "biber 2.14, biblatex 3.18: by their version numbers they do not pair"),
        ("2.13", "3.12", "ok", "biber 2.13, biblatex 3.12 (pairs this old are not compared)"),
    ],
)
def test_biber_is_compared_with_the_biblatex_kpsewhich_finds(
    box: Box, biber: str, biblatex_version: str, status: str, detail: str
) -> None:
    box.script("biber", f"print('biber version: {biber}')\n")
    biblatex(box, biblatex_version)
    got = item(doctor(box), "biber")
    assert got["status"] == status and got["detail"].startswith(detail), got
    assert ("tlmgr" in got["remedy"]) == (status == "warn")


def test_biber_without_a_readable_biblatex_is_only_run(box: Box) -> None:
    box.script("biber", "print('biber version: 2.20')\n")  # the shim's kpsewhich names a biblatex.sty that is not there
    got = item(doctor(box, code=0), "biber")
    assert (got["status"], got["detail"]) == ("ok", "biber version: 2.20")


# ---- machine: the agent commands


def test_agent_commands_are_looked_for_only_with_agents_or_a_configured_agent(box: Box) -> None:
    names = {i["name"] for i in doctor(box)["items"]}
    assert not {"claude", "codex"} & names
    box.script("claude", "print('2.1 (Claude Code)')\n")
    data = doctor(box, "--agents")
    assert item(data, "claude")["status"] == "ok" and item(data, "claude")["path"] == str(box.bin / "claude")
    codex = item(data, "codex")
    assert (codex["status"], codex["path"]) == ("warn", None) and "codex" in codex["remedy"]


def test_a_configured_agents_command_is_looked_for(box: Box) -> None:
    q = quilt(box)
    (q / "ai" / "ai-config.toml").write_text('name = "Claude Agent"\nstart = ["claude", "-p", "{prompt}"]\n')
    got = item(doctor(box, cwd=q), "claude")
    assert got["status"] == "warn" and "ai/ai-config.toml" in got["remedy"]
    box.script("claude", "raise SystemExit('never run')\n")  # found, not run: it is a command the person wrote
    assert item(doctor(box, cwd=q), "claude")["status"] == "ok"


# ---- machine: the author


def test_the_author(box: Box) -> None:
    got = item(doctor(box), "author")
    assert (got["status"], got["detail"]) == (
        "ok",
        f"Ada (from {Path(os.environ['XDG_CONFIG_HOME']) / 'loom' / 'config.toml'})",
    )
    box.author(None)
    got = item(doctor(box, code=0), "author")
    assert got["status"] == "warn" and got["detail"] == "none: accept and annotate refuse without one"
    assert 'name = "Your Name" under [author]' in got["remedy"] and "git config --global user.name" in got["remedy"]


def test_an_empty_author_in_the_quilt_names_the_quilts_config(box: Box) -> None:
    q = quilt(box)
    with (q / "config.toml").open("a", encoding="utf-8") as fh:
        fh.write('\n[author]\nname = ""\n')
    got = item(doctor(box, cwd=q), "author")
    assert got["status"] == "warn" and got["remedy"] == f'set name = "Your Name" under [author] in {q / "config.toml"}'


# ---- machine: the bundle, from each source


def vendored_at(box: Box, d: Path | None) -> None:
    """Point the vendored lookup at `d` and clear LOOM_ARRAS_BUNDLE."""
    box.mp.delenv("LOOM_ARRAS_BUNDLE")
    box.mp.setattr("loom.arras_bundle.vendored_path", lambda: d or box.tmp / "no-bundle")


def checkout(box: Box, version: str) -> Path:
    """A loom-arras checkout whose vendored bundle carries `version`; returns its root."""
    root = box.tmp / "ws"
    (root / ".git").mkdir(parents=True)
    (root / "arras" / "src").mkdir(parents=True)
    (root / "arras" / "package.json").write_text("{}")
    vendored_at(box, bundle(root / "loom" / "src" / "loom" / "assets" / "arras", version))
    return root


Case = Callable[[Box], None]


def env_valid(box: Box) -> None:
    return None


def env_invalid(box: Box) -> None:
    vendored_at(box, bundle(box.tmp / "vendored", stamp()))
    (box.tmp / "empty").mkdir()
    box.mp.setenv("LOOM_ARRAS_BUNDLE", str(box.tmp / "empty"))


def env_invalid_alone(box: Box) -> None:
    vendored_at(box, None)
    box.mp.setenv("LOOM_ARRAS_BUNDLE", str(box.tmp / "nowhere"))


def env_unversioned(box: Box) -> None:
    box.mp.setenv("LOOM_ARRAS_BUNDLE", str(bundle(box.tmp / "dev-build")))


def env_other_interface(box: Box) -> None:
    box.mp.setenv("LOOM_ARRAS_BUNDLE", str(bundle(box.tmp / "old", stamp(interface=INTERFACE_VERSION + 1))))


def package(box: Box) -> None:
    box.mp.delenv("LOOM_ARRAS_BUNDLE")
    p = bundle(box.tmp / "site" / "arras" / "build", stamp())
    box.mp.setitem(sys.modules, "arras", types.SimpleNamespace(bundle_path=lambda: p))


def vendored(box: Box) -> None:
    vendored_at(box, bundle(box.tmp / "site-packages" / "loom" / "assets" / "arras", stamp()))


def none(box: Box) -> None:
    vendored_at(box, None)


def dirty_checkout(box: Box) -> None:
    checkout(box, stamp("abc1234-dirty"))


BUNDLES: list[tuple[str, Case, str, str | None, str, str]] = [
    # id, setup, status, source, detail starts with, remedy contains
    ("env", env_valid, "ok", "LOOM_ARRAS_BUNDLE", "LOOM_ARRAS_BUNDLE, arras abc1234", ""),
    ("env-invalid", env_invalid, "fail", None, "LOOM_ARRAS_BUNDLE=", "unset it"),
    ("env-invalid-alone", env_invalid_alone, "fail", None, "LOOM_ARRAS_BUNDLE=", "unset it"),
    (
        "unversioned",
        env_unversioned,
        "warn",
        "LOOM_ARRAS_BUNDLE",
        "LOOM_ARRAS_BUNDLE, unversioned: its interface",
        "vendor_arras.py",
    ),
    (
        "interface",
        env_other_interface,
        "fail",
        "LOOM_ARRAS_BUNDLE",
        f"LOOM_ARRAS_BUNDLE, interface {INTERFACE_VERSION + 1}",
        "one release",
    ),
    ("package", package, "ok", "arras package", "arras package, arras abc1234", ""),
    ("vendored", vendored, "ok", "vendored", "vendored, arras abc1234", ""),
    ("none", none, "fail", None, "not found: loom serve refuses", "reinstall loom"),
    ("dirty-checkout", dirty_checkout, "warn", "vendored", "vendored, stamped abc1234-dirty", "commit arras, then"),
]


@pytest.mark.parametrize("setup,status,source,detail,remedy", [c[1:] for c in BUNDLES], ids=[c[0] for c in BUNDLES])
def test_the_bundle_from_each_source(
    box: Box, setup: Case, status: str, source: str | None, detail: str, remedy: str
) -> None:
    setup(box)
    got = item(doctor(box), "arras bundle")
    assert (got["status"], got["source"]) == (status, source), got
    assert got["detail"].startswith(detail), got
    assert remedy in got["remedy"], got
    if source is None:
        assert got["path"] is None and got["interface"] is None
    if status == "ok":
        assert got["interface"] == INTERFACE_VERSION


def test_an_invalid_loom_arras_bundle_is_a_refusal_not_a_fallback(box: Box) -> None:
    env_invalid(box)
    got = item(doctor(box), "arras bundle")
    assert got["detail"] == f"LOOM_ARRAS_BUNDLE={box.tmp / 'empty'} has no index.html; loom serve refuses"
    assert got["status"] == "fail" and got["source"] is None


def test_a_vendored_bundle_behind_the_checkouts_arras_warns(box: Box) -> None:
    box.real_git()
    root = box.tmp / "ws"
    (root / "arras" / "src").mkdir(parents=True)
    (root / "arras" / "package.json").write_text("{}")

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    git("init", "-q")
    (root / "arras" / "src" / "app.ts").write_text("1")
    git("add", ".")
    git("commit", "-qm", "one")
    built = git("rev-parse", "--short", "HEAD")
    vendored_at(box, bundle(root / "loom" / "src" / "loom" / "assets" / "arras", stamp(built)))
    assert item(doctor(box), "arras bundle")["status"] == "ok"
    (root / "arras" / "src" / "app.ts").write_text("2")
    git("commit", "-qam", "two")
    got = item(doctor(box), "arras bundle")
    assert got["status"] == "warn" and f"built from {built}, but arras's sources changed in " in got["detail"], got
    assert got["remedy"].endswith("scripts/vendor_arras.py ../arras/build") and "commit arras" not in got["remedy"]


# ---- the quilt section


def test_no_quilt_section_outside_a_quilt(box: Box) -> None:
    data = doctor(box, code=0)
    assert data["quilt"] is None and not [i for i in data["items"] if i["severity"] == "quilt"]


def test_the_demo_is_ok_in_every_quilt_item(box: Box) -> None:
    q = quilt(box)
    data = doctor(box, cwd=q / "drafting", code=0)
    assert data["quilt"] == str(q.resolve())
    got = {i["name"]: (i["status"], i["detail"]) for i in data["items"] if i["severity"] == "quilt"}
    assert got == {
        "engine": ("ok", "pdflatex"),
        "agent": ("ok", "none configured, launch off"),
        "permissions": ("ok", ".claude/settings.json, .codex/rules/loom.rules"),
        "ai files": ("ok", "current"),
        "loom.sty": ("ok", "current"),
        ".gitignore": ("ok", "has loom's lines"),
        "config": ("ok", "config.toml read cleanly"),
    }


def test_quilt_option_names_the_quilt(box: Box) -> None:
    q = quilt(box)
    assert doctor(box, "--quilt", str(q))["quilt"] == str(q.resolve())
    got = item(doctor(box, "--quilt", str(box.tmp / "away"), code=2), "quilt")
    assert got["status"] == "fail" and got["detail"].startswith("not inside a quilt")


def test_an_unreadable_config_fails(box: Box) -> None:
    q = quilt(box)
    (q / "config.toml").write_text("[quilt\n")
    got = item(doctor(box, cwd=q, code=2), "quilt")
    assert "is not valid TOML" in got["detail"] and "fix config.toml" in got["remedy"]


def test_the_engine(box: Box) -> None:
    q = quilt(box)
    edit(q / "config.toml", 'engine = "pdflatex"', 'engine = "xelatex"')
    got = item(doctor(box, cwd=q), "engine")
    assert (got["status"], got["detail"], got["path"]) == ("ok", "xelatex", str(box.bin / "xelatex"))
    box.drop("xelatex")
    data = doctor(box, cwd=q, code=2)
    assert item(data, "xelatex")["status"] == "warn"  # optional on the machine; this quilt needs it
    got = item(data, "engine")
    assert (got["status"], got["detail"]) == ("fail", "xelatex: not found, so every compile here fails")
    edit(q / "config.toml", 'engine = "xelatex"', 'engine = "xetex"')
    got = item(doctor(box, cwd=q), "engine")
    assert got["status"] == "warn" and got["detail"].startswith("engine = 'xetex' is not one of")


def launch(q: Path, on: bool) -> None:
    with (q / "config.toml").open("a", encoding="utf-8") as fh:
        fh.write(f"\n[ai]\nlaunch = {'true' if on else 'false'}\n")


CLAUDE = """name = "Claude Agent"
start = ["claude", "-p", "{prompt}"]
"""


@pytest.mark.parametrize(
    "config,on,claude,status,detail",
    [
        (None, True, False, "fail", "launch is on and no agent is configured"),
        (CLAUDE, False, False, "warn", "claude is not on PATH; launch off"),
        (CLAUDE, True, False, "fail", "claude is not on PATH; launch on"),
        (CLAUDE, True, True, "ok", "Claude Agent, launch on"),
        ('name = "Bob"\nstart = ["claude"]\n', False, True, "warn", "name 'Bob' must include Agent or AI"),
    ],
    ids=["unconfigured-on", "missing-off", "missing-on", "sound-on", "incomplete-off"],
)
def test_the_agent(box: Box, config: str | None, on: bool, claude: bool, status: str, detail: str) -> None:
    q = quilt(box)
    if config:
        (q / "ai" / "ai-config.toml").write_text(config)
    launch(q, on)
    if claude:
        box.script("claude", "print('2.1')\n")
    got = item(doctor(box, cwd=q), "agent")
    assert got["status"] == status and got["detail"].startswith(detail), got
    if status != "ok":
        assert "loom agent check" in got["remedy"]


def test_a_tracked_agent_config_is_a_fault(box: Box) -> None:
    box.real_git()
    q = quilt(box)
    (q / "ai" / "ai-config.toml").write_text(CLAUDE)
    box.script("claude", "print('2.1')\n")
    subprocess.run(["git", "init", "-q"], cwd=q, check=True)
    subprocess.run(["git", "add", "-f", "ai/ai-config.toml"], cwd=q, check=True)
    got = item(doctor(box, cwd=q), "agent")
    assert got["status"] == "warn" and got["detail"].startswith("git tracks ai/ai-config.toml"), got


def test_the_permission_files(box: Box) -> None:
    q = quilt(box)
    edit(q / ".claude" / "settings.json", '"Bash(rm *)"', '"Bash(rm -rf *)"')
    got = item(doctor(box, cwd=q), "permissions")
    assert (got["status"], got["remedy"]) == ("warn", "loom upgrade")
    assert got["detail"] == ".claude/settings.json: not what this loom lets agents run"
    shutil.rmtree(q / "ai")
    assert item(doctor(box, cwd=q), "permissions")["remedy"] == "loom ai init"
    (q / ".claude" / "settings.json").unlink()
    (q / ".codex" / "rules" / "loom.rules").unlink()
    got = item(doctor(box, cwd=q), "permissions")
    assert got["status"] == "ok" and got["detail"].startswith("no ai/")
    # beside an ai/ both are due, so a missing one warns and `loom upgrade` writes it
    ok("ai", "init", cwd=q)
    (q / ".codex" / "rules" / "loom.rules").unlink()
    got = item(doctor(box, cwd=q), "permissions")
    assert (got["status"], got["remedy"]) == ("warn", "loom upgrade")
    assert got["detail"] == ".codex/rules/loom.rules missing: an agent here runs without loom's table"
    ok("upgrade", cwd=q)
    assert item(doctor(box, cwd=q), "permissions")["status"] == "ok"


def tree(q: Path) -> dict[str, bytes]:
    return {str(p.relative_to(q)): p.read_bytes() for p in sorted(q.rglob("*")) if p.is_file()}


def test_the_ai_files_by_upgrades_dry_run(box: Box) -> None:
    from loom.ai.layout import VERSION_FILE, sha

    q = quilt(box)
    versions = q / "ai" / VERSION_FILE
    mode = q / "ai" / "modes" / "quick.md"
    # shipped by an older loom and never edited: the record holds its hash
    older = "an older quick mode\n"
    mode.write_text(older)
    record = next(ln for ln in versions.read_text().splitlines() if ln.startswith("quick.md "))
    edit(versions, record, f"quick.md {sha(older)}")
    before = tree(q)
    got = item(doctor(box, cwd=q), "ai files")
    assert tree(q) == before, "doctor wrote into the quilt"
    assert (got["status"], got["detail"], got["remedy"]) == (
        "warn",
        "older than this loom: ai/modes/quick.md",
        "loom upgrade (an edited file gets the new version beside it)",
    )
    # edited by the author against what is shipped now: theirs, nothing newer to offer
    ok("upgrade", cwd=q)
    mode.write_text(mode.read_text() + "my own rule\n")
    assert item(doctor(box, cwd=q), "ai files")["detail"] == "current, 1 edited"
    # edited, and a newer version ships: warned until upgrade puts it beside the file
    record = next(ln for ln in versions.read_text().splitlines() if ln.startswith("quick.md "))
    edit(versions, record, "quick.md 0000")
    got = item(doctor(box, cwd=q), "ai files")
    assert (got["status"], got["detail"]) == ("warn", "edited, with a newer version shipped: ai/modes/quick.md")
    ok("upgrade", cwd=q)
    assert item(doctor(box, cwd=q), "ai files")["detail"] == "current, 1 edited"


def test_loom_sty(box: Box) -> None:
    q = quilt(box)
    (q / "loom.sty").write_text("% an older loom.sty\n")
    got = item(doctor(box, cwd=q), "loom.sty")
    assert (got["status"], got["detail"], got["remedy"]) == ("warn", "not the one this loom ships", "loom upgrade")
    (q / "loom.sty").unlink()
    assert item(doctor(box, cwd=q), "loom.sty")["detail"].startswith("missing")
    ok("upgrade", cwd=q)
    assert item(doctor(box, cwd=q), "loom.sty")["status"] == "ok"


def test_the_gitignore_lines(box: Box) -> None:
    q = quilt(box)
    edit(q / ".gitignore", "\nlast-seen.json\n", "\n")
    edit(q / ".gitignore", "\nai/ai-config.toml\n", "\n")
    got = item(doctor(box, cwd=q), ".gitignore")
    assert (got["status"], got["detail"], got["remedy"]) == (
        "warn",
        "lacks last-seen.json, ai/ai-config.toml",
        "loom upgrade",
    )
    ok("upgrade", cwd=q)
    assert item(doctor(box, cwd=q), ".gitignore")["status"] == "ok"


def test_config_warnings_point_to_lint(box: Box) -> None:
    q = quilt(box)
    edit(q / "config.toml", "[lint]\n", "[lint]\nshout = true\n")
    got = item(doctor(box, cwd=q), "config")
    assert (got["status"], got["detail"], got["remedy"]) == (
        "warn",
        "config.toml: unknown key lint.shout; ignored",
        "loom lint",
    )


# ---- the report as a whole


def everything_wrong(box: Box) -> None:
    box.drop("latexmk", "biber")
    box.author(None)
    none(box)


@pytest.mark.parametrize("setup", [lambda b: None, everything_wrong], ids=["clean", "broken"])
@pytest.mark.parametrize("inside", [False, True], ids=["outside", "inside"])
def test_the_json_schema(box: Box, setup: Case, inside: bool) -> None:
    setup(box)
    data = doctor(box, "--agents", cwd=quilt(box) if inside else None)
    assert set(data) == {"python", "loom", "interface_version", "quilt", "ok", "failing", "warnings", "items"}
    names = [i["name"] for i in data["items"]]
    assert len(names) == len(set(names)), names
    for i in data["items"]:
        assert {"name", "status", "severity", "detail", "remedy"} <= set(i), i
        assert all(isinstance(i[k], str) for k in ("name", "status", "severity", "detail", "remedy")), i
        assert i["status"] in ("ok", "warn", "fail") and i["severity"] in ("required", "optional", "quilt"), i
        assert bool(i["remedy"]) == (i["status"] != "ok"), i
        assert i["detail"], i
    assert data["failing"] == [i["name"] for i in data["items"] if i["status"] == "fail"]
    assert data["warnings"] == [i["name"] for i in data["items"] if i["status"] == "warn"]
    assert data["ok"] == (not data["failing"])
    assert (data["quilt"] is not None) == inside == any(i["severity"] == "quilt" for i in data["items"])


def test_exit_codes_and_the_summary(box: Box) -> None:
    assert ok("doctor", cwd=box.tmp / "away").stdout.splitlines()[-1] == "ok"
    assert ok("doctor", "--strict", cwd=box.tmp / "away").stdout.splitlines()[-1] == "ok"
    box.author(None)
    box.drop("pdfinfo")
    assert ok("doctor", cwd=box.tmp / "away").stdout.splitlines()[-1] == "ok (2 warnings)"
    r = exits(2, "doctor", "--strict", cwd=box.tmp / "away")
    assert r.stdout.splitlines()[-1] == "warnings: pdfinfo, author"
    assert json_of("doctor", "--json", "--strict", cwd=box.tmp / "away", code=2)["ok"] is False
    box.drop("latexmk", "dvisvgm")
    r = exits(2, "doctor", cwd=box.tmp / "away")
    assert r.stdout.splitlines()[-1] == "failing: latexmk, dvisvgm (2 warnings)"
    r = exits(2, "doctor", "--strict", cwd=box.tmp / "away")
    assert r.stdout.splitlines()[-1] == "failing: latexmk, dvisvgm; warnings: pdfinfo, author"


def test_the_text_report_lines_up(box: Box) -> None:
    box.drop("pdfinfo")
    lines = ok("doctor", cwd=quilt(box)).stdout.splitlines()
    tools = [ln for ln in lines if ln.startswith("  ok    ") and str(box.bin) in ln]
    assert len(tools) == 13  # twelve tools and the engine
    assert len({ln.index(str(box.bin)) for ln in tools}) == 1, "the paths do not start in one column"
    at = lines.index(next(ln for ln in lines if ln.startswith("  warn  pdfinfo")))
    assert lines[at + 1].strip() == f"fix: {item(doctor(box), 'pdfinfo')['remedy']}"
    assert lines[at + 1].index("fix:") == lines[at].index("not found")
    assert "machine" in lines and any(ln.startswith("quilt ") for ln in lines)
