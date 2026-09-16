"""`loom ai init` and `loom upgrade` (book 11.2, 11.3, 11.8, 11.12): the `ai/` directory, the vendor files, and their refresh.

Mode files are the author's once written: `.loom-modes-version` records the shipped hash of each, so upgrade overwrites only files still equal to what it shipped and writes `<mode>.md.new` beside an edited one.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

MODES = ["blocks", "audit", "referee", "simplify", "question", "quick", "draft", "ingest", "brainstorm"]
TARGET_MODES = ["audit", "referee", "simplify", "draft", "ingest"]
TRIGGERS = {
    "blocks": "the block definitions and standing rules every loom mode refers to; read once per session before applying a mode",
    "audit": "when the user asks to audit a key of this quilt: its hypotheses, citations, uses, or self-containedness",
    "referee": "when the user asks to referee, review, or find gaps or errors in a node of this quilt",
    "simplify": "when the user asks to shorten, tighten, or simplify a node's text without changing its mathematics",
    "question": "when the user asks a thorough question about a key or about the quilt",
    "quick": "when the user wants a brief answer about a key or the quilt",
    "draft": "when the user asks to write a node from a plan they supply",
    "ingest": "when the user asks to digest a cited paper into refs/",
    "brainstorm": "when the user wants to explore, brainstorm, or plan a topic before proving anything",
}
GITIGNORE_LINE = "ai/runs/*/bundle-*.tex"
VERSION_FILE = ".loom-modes-version"


def _asset(*parts: str) -> str:
    return resources.files("loom").joinpath("assets", "ai", *parts).read_text(encoding="utf-8")


def shipped_modes() -> dict[str, str]:
    return {m: _asset("modes", f"{m}.md") for m in MODES}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_versions(root: Path) -> dict[str, str]:
    p = root / "ai" / VERSION_FILE
    out: dict[str, str] = {}
    if p.is_file():
        for line in p.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) == 2:
                out[parts[0]] = parts[1]
    return out


def write_versions(root: Path, texts: dict[str, str]) -> None:
    lines = [f"{m}.md {sha(t)}" for m, t in sorted(texts.items())]
    (root / "ai" / VERSION_FILE).write_text("\n".join(lines) + "\n", encoding="utf-8")


def vendor_files(permissions: bool, skills: bool) -> dict[str, str]:
    """Quilt-relative path -> text for the vendor files; the root files always, the rest on request."""
    root_text = _asset("vendor", "root.md")
    out = {"CLAUDE.md": root_text, "AGENTS.md": root_text}
    if permissions:
        out[".claude/settings.json"] = _asset("vendor", "claude", "settings.json")
    if skills:
        skill = _asset("vendor", "claude", "SKILL.md")
        command = _asset("vendor", "claude", "command.md")
        for m in MODES:
            if m == "blocks":
                continue
            target_line = " The target is `$ARGUMENTS`." if m in TARGET_MODES else ""
            out[f".claude/skills/loom-{m}/SKILL.md"] = (
                skill.replace("{mode}", m).replace("{trigger}", TRIGGERS[m]).replace("{target_line}", target_line)
            )
        for m in TARGET_MODES:
            out[f".claude/commands/{m}.md"] = command.replace("{mode}", m)
    return out


@dataclass
class LayerReport:
    written: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)  # edited mode files left alone
    new_beside: list[str] = field(default_factory=list)  # <mode>.md.new written
    unchanged: list[str] = field(default_factory=list)


def init_layer(root: Path, permissions: bool = False, skills: bool = False) -> LayerReport:
    """Write `ai/` and the vendor files into a quilt that has no `ai/` yet."""
    ai = root / "ai"
    if ai.exists():
        raise FileExistsError(str(ai))
    rep = LayerReport()
    (ai / "modes").mkdir(parents=True)
    (ai / "runs").mkdir()
    texts = shipped_modes()
    for m, t in texts.items():
        (ai / "modes" / f"{m}.md").write_text(t, encoding="utf-8")
        rep.written.append(f"ai/modes/{m}.md")
    for name in ("orientation.md", "README.md"):
        (ai / name).write_text(_asset(name), encoding="utf-8")
        rep.written.append(f"ai/{name}")
    write_versions(root, texts)
    rep.written.append(f"ai/{VERSION_FILE}")
    for rel, text in vendor_files(permissions, skills).items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        rep.written.append(rel)
    if ensure_gitignore_line(root):
        rep.written.append(".gitignore")
    return rep


def ensure_gitignore_line(root: Path) -> bool:
    p = root / ".gitignore"
    existing = p.read_text(encoding="utf-8") if p.is_file() else ""
    if GITIGNORE_LINE in existing.splitlines():
        return False
    p.write_text(existing.rstrip("\n") + ("\n" if existing else "") + GITIGNORE_LINE + "\n", encoding="utf-8")
    return True


def upgrade_layer(root: Path) -> LayerReport:
    """Refresh the generated files of an existing `ai/`; keep edited mode files and write `.new` beside them."""
    ai = root / "ai"
    rep = LayerReport()
    if not ai.is_dir():
        return rep
    recorded = read_versions(root)
    texts = shipped_modes()
    for m, shipped in texts.items():
        p = ai / "modes" / f"{m}.md"
        rel = f"ai/modes/{m}.md"
        if not p.is_file():
            p.write_text(shipped, encoding="utf-8")
            rep.written.append(rel)
            continue
        current = p.read_text(encoding="utf-8")
        if sha(current) == sha(shipped):
            rep.unchanged.append(rel)
            continue
        if recorded.get(f"{m}.md") == sha(current):
            p.write_text(shipped, encoding="utf-8")  # untouched since it was shipped: refresh
            rep.written.append(rel)
        else:
            (ai / "modes" / f"{m}.md.new").write_text(shipped, encoding="utf-8")
            rep.kept.append(rel)
            rep.new_beside.append(rel + ".new")
    new_versions = dict(recorded)
    for m, shipped in texts.items():
        rel = f"ai/modes/{m}.md"
        if rel in rep.kept:
            continue  # the record keeps the hash of what was shipped last time, so a later upgrade still sees the edit
        new_versions[f"{m}.md"] = sha(shipped)
    (ai / VERSION_FILE).write_text(
        "\n".join(f"{k} {v}" for k, v in sorted(new_versions.items())) + "\n", encoding="utf-8"
    )
    for name in ("orientation.md", "README.md"):
        p = ai / name
        text = _asset(name)
        if not p.is_file() or p.read_text(encoding="utf-8") != text:
            p.write_text(text, encoding="utf-8")
            rep.written.append(f"ai/{name}")
        else:
            rep.unchanged.append(f"ai/{name}")
    permissions = (root / ".claude" / "settings.json").is_file()
    skills = (root / ".claude" / "skills").is_dir() or (root / ".claude" / "commands").is_dir()
    for rel, text in vendor_files(permissions, skills).items():
        p = root / rel
        if p.is_file() and p.read_text(encoding="utf-8") == text:
            rep.unchanged.append(rel)
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        rep.written.append(rel)
    if ensure_gitignore_line(root):
        rep.written.append(".gitignore")
    return rep


def settings_deny_paths() -> list[str]:
    """The Edit/Write patterns the shipped settings deny, for tests and doctor."""
    data = json.loads(_asset("vendor", "claude", "settings.json"))
    return [str(r) for r in data["permissions"]["deny"]]
