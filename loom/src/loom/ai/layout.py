"""`loom ai init` and `loom upgrade` (book 11.2, 11.3, 11.8, 11.12): the `ai/` directory, the vendor files, and their refresh.

Mode files are the author's once written: `.loom-modes-version` records the shipped hash of each, so upgrade overwrites only files still equal to what it shipped and writes `<mode>.md.new` beside an edited one.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

MODES = ["audit", "referee", "review", "simplify", "question", "quick", "draft", "ingest", "brainstorm"]
RULES = "rules.md"  # `ai/rules.md`: not a mode, and no longer filed among them
TARGET_MODES = ["audit", "referee", "review", "simplify", "draft", "ingest"]
TRIGGERS = {
    "audit": "when the user asks to audit a key of this quilt: its hypotheses, citations, uses, or self-containedness",
    "review": "a referee reading to improve the source: citations, hypotheses, errors, wording, each finding graded by severity; the author reaches for this most",
    "referee": "when the user asks to referee, review, or find gaps or errors in a node of this quilt",
    "simplify": "when the user asks to shorten, tighten, or simplify a node's text without changing its mathematics",
    "question": "when the user asks a thorough question about a key or about the quilt",
    "quick": "when the user wants a brief answer about a key or the quilt",
    "draft": "when the user asks to write a node from a plan they supply",
    "ingest": "when the user asks to digest a cited paper into digests/",
    "brainstorm": "when the user wants to explore, brainstorm, or plan a topic before proving anything",
}
# The one list: every loom command an agent may run, by its full path in the command tree. Everything else loom
# offers is the author's, so a command added later is denied until it is named here -- which an enumeration of
# forbidden commands could never promise, and did not: twelve mutating commands were missing from it (DR-173).
AGENT_COMMANDS = frozenset(
    {
        "annotate", "build", "check", "compile", "deps", "doctor", "history", "id", "link", "lint",
        "new", "search", "serve", "source", "status", "unravel", "downstream", "pop", "reach",
        "ai annotations", "ai check", "ai discard", "ai name", "ai orient", "ai start",
        # dispatch is the agent's half of the mailbox: park, read, answer. Opening, closing, retitling and deleting a
        # session stay the author's, because they are decisions about the work rather than participation in it.
        "session list", "session next", "session say", "session send", "session watch",
        "digest extract",
        "refs build", "refs coverage", "refs fetch", "refs grep", "refs link", "refs links", "refs locate",
        "refs find", "refs ingest", "refs map", "refs match", "refs overview", "refs page", "refs path", "refs propose",
        "refs recheck",
        "refs resolve", "refs unlink", "refs why",
    }
)  # fmt: skip
AGENT_WRITES = (".loom/sessions", "build")  # the only places an agent may write
# `.loom` is not read-only wholesale any more: a session's own directory is under it and is where an agent writes its
# journal and its notes, so the parts that are the record -- the history and the acceptance ledger -- are named instead.
AGENT_READONLY = ("nodes", "drafting", "canon", "retired", "digests", "refs", "annotations", ".loom/history", "ai")
AGENT_READONLY_FILES = (
    "ai/orientation.md",
    "ai/rules.md",
    "ai/formatting.md",
    "config.toml",
    "reference-notes.jsonl",
    ".loom/state.toml",
    ".loom/sessions/index.jsonl",
)

CLAUDE_LINE = "This directory is a quilt managed by loom. Before doing anything, run `loom ai orient` and follow it. Write only under your session's directory in `.loom/sessions/`."
VERSION_FILE = ".loom-modes-version"


def _asset(*parts: str) -> str:
    return resources.files("loom").joinpath("assets", "ai", *parts).read_text(encoding="utf-8")


def command_tree() -> list[str]:
    """Every leaf command loom offers, as the path a person types: `accept`, `ai promote`, `refs cite`."""
    import click

    from loom.cli import main

    out: list[str] = []

    def walk(cmd: object, prefix: str = "") -> None:
        for name, sub in sorted(getattr(cmd, "commands", {}).items()):
            path = f"{prefix} {name}".strip()
            walk(sub, path) if isinstance(sub, click.Group) else out.append(path)

    walk(main)
    return out


def author_commands() -> list[str]:
    """Every command that is not an agent's, derived rather than listed, so a new one is the author's until it is admitted."""
    return [c for c in command_tree() if c not in AGENT_COMMANDS]


def tracked_docs() -> dict[str, str]:
    """Quilt-relative path -> shipped text for every file whose edits `loom upgrade` preserves.

    The orientation is here because it is the first thing an author tailors -- a standing rule about this quilt, a mode the agent should not reach for -- and `loom upgrade` overwrote it without a word until it was.
    """
    allowed = "\n".join(f"  - `loom {c}`" for c in sorted(AGENT_COMMANDS))
    out = {
        f"ai/{RULES}": _asset(RULES).replace("{allowed_commands}", allowed),
        "ai/orientation.md": _asset("orientation.md"),
        "ai/formatting.md": _asset("formatting.md"),
    }
    out.update({f"ai/modes/{m}.md": _asset("modes", f"{m}.md") for m in MODES})
    return out


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
    """Record the shipped hash of each of `texts` (quilt-relative path -> text) under its file name, which is how `upgrade_layer` looks it up."""
    lines = [f"{Path(rel).name} {sha(t)}" for rel, t in sorted(texts.items(), key=lambda kv: Path(kv[0]).name)]
    (root / "ai" / VERSION_FILE).write_text("\n".join(lines) + "\n", encoding="utf-8")


def permissions_json() -> str:
    """`.claude/settings.json`, generated from the one table rather than written by hand.

    Claude Code's deny rules beat its allow rules and an allow-only whitelist cannot be expressed (DR-71), so the file enumerates what is refused -- the complement of `AGENT_COMMANDS`, rather than a list somebody remembered to extend -- and allows `AGENT_COMMANDS` themselves outright, because an agent `loom serve` starts for one turn cannot answer a permission prompt (plan 0.14). The hand-written one had drifted by seven commands, `loom upgrade` and both spellings of `loom canonize` among them, so `loom canonise` walked through the deny on `loom canonize`.
    """
    import json

    # `Edit` rules govern every file-editing tool; Claude Code does not match `Write` rules against paths at all
    allow = [f"Edit(/{d}/**)" for d in AGENT_WRITES]
    # the agent's own commands, allowed outright: an agent `loom serve` starts for a turn cannot answer a prompt
    allow += [f"Bash(loom {c}*)" for c in sorted(AGENT_COMMANDS)]
    deny = [f"Edit(/{d}/**)" for d in AGENT_READONLY]
    deny += [f"Edit(/{f})" for f in AGENT_READONLY_FILES]
    deny += [f"Edit(/*.{ext})" for ext in ("tex", "sty", "bib")]
    deny += [f"Bash(loom {c}*)" for c in author_commands()]
    deny.append("Bash(rm *)")
    return json.dumps({"permissions": {"allow": allow, "deny": deny}}, indent=2) + "\n"


#: Where each agent tool reads the quilt's rules for its agents: one policy, loom's own, rendered per tool (DR-283-ikmartin).
CLAUDE_SETTINGS = ".claude/settings.json"
CODEX_RULES = ".codex/rules/loom.rules"


def codex_rules() -> str:
    """`.codex/rules/loom.rules`: the same table as `permissions_json`, as Codex's command-prefix rules.

    Codex matches commands, not paths, so the path rules have no counterpart here; the author's own verbs are refused by loom itself for an agent's name whatever the tool (DR-185). Codex reads a project's rules only once the project is trusted. Unverified: Codex was not installed where this was written.
    """
    import json

    head = [
        "# Written by loom from its table of what an agent may run; `loom upgrade` rewrites it, and a quilt does not change it.",
        "# Rules of your own go in another file in this directory, which loom never touches.",
    ]

    def rule(words: list[str], decision: str) -> str:
        return f"prefix_rule(pattern = [{', '.join(json.dumps(w) for w in words)}], decision = {json.dumps(decision)})"

    body = [rule(["loom", *c.split()], "allow") for c in sorted(AGENT_COMMANDS)]
    body += [rule(["loom", *c.split()], "forbidden") for c in author_commands()]
    body.append(rule(["rm"], "forbidden"))
    return "\n".join(head + body) + "\n"


def vendor_files(permissions: bool, skills: bool, codex: bool = False) -> dict[str, str]:
    """Quilt-relative path -> text for the files loom owns whole; the agent root files are not among them (see `ensure_root_line`)."""
    out: dict[str, str] = {}
    if permissions:
        out[CLAUDE_SETTINGS] = permissions_json()
    if codex:
        out[CODEX_RULES] = codex_rules()
    if skills:
        skill = _asset("vendor", "claude", "SKILL.md")
        command = _asset("vendor", "claude", "command.md")
        for m in MODES:
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


ROOT_FILES = ("CLAUDE.md", "AGENTS.md")


def ensure_root_line(root: Path, write: bool = True) -> list[str]:
    """Put loom's one line into CLAUDE.md and AGENTS.md without taking the files over; returns what was written, or with `write` false what would be.

    These are the files an agent reads before anything else, and they are also where an author writes what is true of *their* project — so loom contributes a line and owns nothing else. An earlier version of the line is replaced in place; everything around it is left exactly as the author left it. Loom writing the whole file is what clobbered hand-written instructions on every upgrade (DR-151).
    """
    written: list[str] = []
    for name in ROOT_FILES:
        p = root / name
        existing = p.read_text(encoding="utf-8") if p.is_file() else ""
        lines = existing.splitlines()
        if CLAUDE_LINE in lines:
            continue
        written.append(name)
        if not write:
            continue
        stale = [i for i, ln in enumerate(lines) if ln.startswith("This directory is a quilt managed by loom.")]
        if stale:
            lines[stale[0]] = CLAUDE_LINE
            for i in reversed(stale[1:]):
                del lines[i]
            p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        else:
            p.write_text(
                existing.rstrip("\n") + ("\n\n" if existing.strip() else "") + CLAUDE_LINE + "\n", encoding="utf-8"
            )
    return written


def init_layer(root: Path, skills: bool = False) -> LayerReport:
    """Write `ai/` and the vendor files into a quilt that has no `ai/` yet, the permission files for every tool among them: what agents may run is loom's, and the same whichever tool runs them (DR-283)."""
    ai = root / "ai"
    if ai.exists():
        raise FileExistsError(str(ai))
    rep = LayerReport()
    (ai / "modes").mkdir(parents=True)
    texts = tracked_docs()
    for rel, text in texts.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        rep.written.append(rel)
    for name in ("README.md",):
        (ai / name).write_text(_asset(name), encoding="utf-8")
        rep.written.append(f"ai/{name}")
    write_versions(root, texts)
    rep.written.append(f"ai/{VERSION_FILE}")
    for rel, text in vendor_files(True, skills, True).items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        rep.written.append(rel)
    rep.written.extend(ensure_root_line(root))
    return rep


def upgrade_layer(root: Path, write: bool = True) -> LayerReport:
    """Refresh the generated files of an existing `ai/`; keep edited mode files and write `.new` beside them.

    With `write` false nothing is written and the report says what would be: `loom doctor`'s dry run, byte for byte what `loom upgrade` compares.
    """
    ai = root / "ai"
    rep = LayerReport()
    if not ai.is_dir():
        return rep
    recorded = read_versions(root)
    texts = tracked_docs()
    for rel, shipped in texts.items():
        p = root / rel
        name = Path(rel).name
        if not p.is_file():
            if write:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(shipped, encoding="utf-8")
            rep.written.append(rel)
            continue
        current = p.read_text(encoding="utf-8")
        if sha(current) == sha(shipped):
            rep.unchanged.append(rel)
            continue
        if recorded.get(name) == sha(current):
            if write:
                p.write_text(shipped, encoding="utf-8")  # untouched since it was shipped: refresh
            rep.written.append(rel)
        else:
            if write:
                p.with_name(name + ".new").write_text(shipped, encoding="utf-8")
            rep.kept.append(rel)
            rep.new_beside.append(rel + ".new")
    names = {Path(rel).name for rel in texts}
    new_versions = {name: h for name, h in recorded.items() if name in names}
    for rel, shipped in texts.items():
        if rel in rep.kept:
            continue  # the record keeps the hash of what was shipped last time, so a later upgrade still sees the edit
        new_versions[Path(rel).name] = sha(shipped)
    if write:
        (ai / VERSION_FILE).write_text(
            "\n".join(f"{k} {v}" for k, v in sorted(new_versions.items())) + "\n", encoding="utf-8"
        )
    for name in ("README.md",):
        p = ai / name
        text = _asset(name)
        if not p.is_file() or p.read_text(encoding="utf-8") != text:
            if write:
                p.write_text(text, encoding="utf-8")
            rep.written.append(f"ai/{name}")
        else:
            rep.unchanged.append(f"ai/{name}")
    # a quilt with ai/ has both permission files, so a missing one is written like a stale one
    skills = (root / ".claude" / "skills").is_dir() or (root / ".claude" / "commands").is_dir()
    for rel, text in vendor_files(True, skills, True).items():
        p = root / rel
        if p.is_file() and p.read_text(encoding="utf-8") == text:
            rep.unchanged.append(rel)
            continue
        if write:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        rep.written.append(rel)
    rep.written.extend(ensure_root_line(root, write))
    return rep


def settings_deny_paths() -> list[str]:
    """The Edit/Write patterns and commands the generated settings deny, for tests."""
    data = json.loads(permissions_json())
    return [str(r) for r in data["permissions"]["deny"]]
