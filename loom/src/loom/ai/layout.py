"""`loom ai init` and `loom upgrade`: the `ai/` directory, the vendor files, and their refresh.

Mode files are the author's once written: `.loom-modes-version` records the shipped hash of each, so upgrade overwrites only files still equal to what it shipped and writes `<mode>.md.new` beside an edited one. The record holds `loom.sty`'s too, which upgrade always replaces, keeping an edited one as `loom.sty.old` (`refresh_sty`).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

from loom.scan.quilt import QuiltConfig

#: The modes loom ships, in the order the index lists them. Each file's `When it fits:` line is the index's entry for it, the one copy; a file in a quilt's `ai/modes/` whose name is not here is not a mode, so one loom no longer ships is inert.
MODES = ["quick", "question", "audit", "referee", "review", "simplify", "flow", "draft", "ingest"]
RULES = "rules.md"  # `ai/rules.md`: not a mode, and no longer filed among them
# The one list: every loom command an agent may run, by its full path in the command tree. Everything else loom offers is the author's, so a command added later is denied until it is named here -- which an enumeration of forbidden commands could never promise, and did not: twelve mutating commands were missing from it (DR-173).
AGENT_COMMANDS = frozenset(
    {
        "annotate", "build", "check", "compile", "deps", "doctor", "draft", "history", "id", "link", "lint",
        "new", "search", "serve", "source", "status", "downstream", "history show", "history verify", "suggestion", "write",
        "ai annotations", "ai drafts", "ai refresh", "ai orient", "ai mode",
        # the agent opens and names the session it works in, and parks, reads and answers in it; closing, resuming and deleting a session stay the author's, because they are decisions about the work rather than part of it
        "session new", "session rename", "session list", "session next", "session say", "session watch",
        # the library's readers and an agent's tools; filing a document (`library add`, `import`) and every decision are the author's
        "library", "library update", "library review", "library read", "library search", "library why",
        "library propose", "library locate", "library relate", "library check",
        # the MCP server an agent's app starts, often from a shell that already marks an agent
        "mcp",
    }
)  # fmt: skip
#: What each agent command does to the quilt, which is what an MCP tool's hints say (`loom.mcp.tools.hints`): `read` changes nothing but loom's own command log; `derive` rewrites what `build/` derives; `write` adds to a record, a session, a document of the agent's or the library; `replace` puts new text in place of a page's. Every command in `AGENT_COMMANDS` is here, and nothing else.
ACTS: dict[str, str] = {
    **dict.fromkeys(
        (
            "deps", "doctor", "downstream", "history", "history show", "history verify", "link", "lint", "search",
            "source", "status", "suggestion", "ai annotations", "ai drafts", "ai mode", "ai orient", "session list",
            "library", "library check", "library locate", "library read", "library review", "library search",
            "library why",
        ),
        "read",
    ),
    **dict.fromkeys(("build", "check", "compile", "id", "serve"), "derive"),
    **dict.fromkeys(
        (
            "annotate", "draft", "new", "ai refresh", "session new", "session rename", "session say", "session next",
            "session watch", "library propose", "library relate", "library update", "mcp",
        ),
        "write",
    ),
    "write": "replace",
}  # fmt: skip
#: Agent commands that are no MCP tool: the server itself, `serve`, which runs until stopped, and the inbox's waiting, which the bridge replaces (plan 0.21.8).
NOT_TOOLS = frozenset({"mcp", "serve", "session next", "session watch"})
#: The one agent command that may reach the network, when the quilt's config allows it.
NETWORK = frozenset({"library update"})
AGENT_WRITES = (
    ".loom/sessions",
    "build",
)  # the only places an agent may write, besides the quilt's `[quilt] drafting_ai`
# `.loom` is not read-only wholesale any more: a session's own directory is under it and is where an agent writes its
# journal and its notes, so the parts that are the record -- the history and the acceptance ledger -- are named instead.
# The person's drafting directory is read-only too, under the name the quilt gives it (`agent_dirs`).
AGENT_READONLY = ("nodes", "retired", "digests", "refs", "annotations", ".loom/history", "ai")
AGENT_READONLY_FILES = (
    "ai/orientation.md",
    "ai/rules.md",
    "ai/formatting.md",
    "config.toml",
    "reference-notes.jsonl",
    ".loom/state.toml",
    ".loom/sessions/index.jsonl",
)

#: The style file at every quilt's root: loom's, so always replaced by upgrade, and its shipped hash recorded with the mode files'.
STY = "loom.sty"

#: The line loom puts in each agent's root file, one per variant: an agent attached over MCP starts from the server's tool, and one working through a shell from the command.
MCP_LINE = "This directory is a quilt managed by loom. Before doing anything, call `loom_ai_orient`, the tool of the loom MCP server, and follow it; if you have no loom tools, ask the author to run `loom ai init` and approve the loom server. Write only under your session's directory in `.loom/sessions/`, and in the documents `loom_ai_orient` names as yours to edit."
SHELL_LINE = "This directory is a quilt managed by loom. Before doing anything, run `loom ai orient` and follow it. Write only under your session's directory in `.loom/sessions/`, and in the documents `loom ai orient` names as yours to edit."
#: The two ways an agent reaches loom: through the MCP server's tools, the default, or by typing `loom` in a shell, for an agent with no MCP.
MCP, SHELL = "mcp", "shell"
VERSION_FILE = ".loom-modes-version"


def _asset(*parts: str) -> str:
    return resources.files("loom").joinpath("assets", "ai", *parts).read_text(encoding="utf-8")


def shipped_sty() -> str:
    """The `loom.sty` this loom ships."""
    return resources.files("loom").joinpath("assets", STY).read_text(encoding="utf-8")


def record_version(root: Path, name: str, text: str) -> None:
    """Set one file's shipped hash in `ai/.loom-modes-version`, leaving the others; nothing without an `ai/`."""
    if not (root / "ai").is_dir():
        return
    versions = {**read_versions(root), name: sha(text)}
    (root / "ai" / VERSION_FILE).write_text(
        "\n".join(f"{k} {v}" for k, v in sorted(versions.items())) + "\n", encoding="utf-8"
    )


def refresh_sty(root: Path, write: bool = True) -> tuple[str, str]:
    """Make the quilt's `loom.sty` the shipped one; (outcome, where the one replaced is kept, or '').

    The outcome is `unchanged`, `written` (missing, or as loom wrote it), `edited` (kept first), or `unknown` (different, and no record says loom wrote it: kept first too). The old one goes to `loom.sty.old`, or `loom.sty.old.N` when an earlier one with other text is there. With `write` false nothing is written and the result is what upgrade would do.
    """
    shipped = shipped_sty()
    p = root / STY
    current = p.read_text(encoding="utf-8") if p.is_file() else None
    recorded = read_versions(root).get(STY)
    if current == shipped:
        outcome = "unchanged"
    elif current is None or recorded == sha(current):
        outcome = "written"
    else:
        outcome = "edited" if recorded else "unknown"
    old = ""
    if current is not None and outcome in ("edited", "unknown"):
        n, spare = 0, p.with_name(STY + ".old")
        while spare.is_file() and spare.read_text(encoding="utf-8") != current:
            n += 1
            spare = p.with_name(f"{STY}.old.{n}")
        old = spare.name
        if write:
            spare.write_text(current, encoding="utf-8")
    if write:
        if outcome != "unchanged":
            p.write_text(shipped, encoding="utf-8")
        if recorded != sha(shipped):
            record_version(root, STY, shipped)
    return outcome, old


def command_tree() -> list[str]:
    """Every leaf command loom offers, as the path a person types: `accept`, `ai orient`, `library verify`."""
    import click

    from loom.cli import main

    out: list[str] = []

    def walk(cmd: object, prefix: str = "") -> None:
        for name, sub in sorted(getattr(cmd, "commands", {}).items()):
            path = f"{prefix} {name}".strip()
            if isinstance(sub, click.Group):
                # a group that runs on its own (`history`, `history KEY`) is a command as well as a group
                if sub.invoke_without_command:
                    out.append(path)
                walk(sub, path)
            else:
                out.append(path)

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


def agent_dirs(config: QuiltConfig) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(where an agent may write, what it may not) for a quilt: the fixed tables with the quilt's own drafting and `drafting_ai` names in them."""
    return AGENT_WRITES + (config.drafting_ai,), (config.drafting,) + AGENT_READONLY


def quilt_config(root: Path) -> QuiltConfig:
    """The config of the quilt at `root`, or the defaults where there is none yet: the names the permission file is written with."""
    from loom.scan.quilt import NoQuiltError, load_quilt

    try:
        return load_quilt(root).config
    except NoQuiltError:
        return QuiltConfig()


def permissions_json(config: QuiltConfig, *, shell: bool = False) -> str:
    """`.claude/settings.json` for a quilt, generated from the one table rather than written by hand.

    Over MCP, the default, the agent's commands are the loom server's tools, allowed as `mcp__loom__*`, and the author's are not tools at all; `loom` typed in a shell is denied, which steers an agent to the tools and is not the boundary -- loom's own refusal under an agent (K5) is. With `shell`, for an agent that has no MCP, the file enumerates what is refused -- the complement of `AGENT_COMMANDS`, since Claude Code's deny rules beat its allow rules and an allow-only whitelist cannot be expressed (DR-71) -- and allows `AGENT_COMMANDS` themselves outright, so the person is never asked to approve an agent's own reads and annotations. The directories are the quilt's own names (`agent_dirs`), so a quilt that renames `drafting` keeps it read-only.

    The file is read twice and its two path forms are for different readings (DR-343-ikmartin): as the project's settings, `/x` is the quilt root, but an untrusted folder's allow rules are dropped there; passed with `--settings`, every rule holds but `/x` is under `.claude/`. So the allows are relative to the working directory, the quilt root an agent is started in, and the denies keep `/`, which anchors `/*.tex` to the root where a relative `*.tex` would refuse the agent's own drafts.
    """
    import json

    writes, readonly = agent_dirs(config)
    # `Edit` rules govern every file-editing tool; Claude Code does not match `Write` rules against paths at all
    allow = [f"Edit({d}/**)" for d in writes]
    # the agent's own commands, allowed outright: approving each of them is friction with nothing to decide
    allow += [f"Bash(loom {c}*)" for c in sorted(AGENT_COMMANDS)] if shell else ["mcp__loom__*"]
    deny = [f"Edit(/{d}/**)" for d in readonly]
    deny += [f"Edit(/{f})" for f in AGENT_READONLY_FILES]
    # the research state is a page: an agent writes it through `loom write`, which records the write, never by hand
    deny.append(f"Edit(/{config.research_state})")
    deny += [f"Edit(/*.{ext})" for ext in ("tex", "sty", "bib")]
    deny += [f"Bash(loom {c}*)" for c in author_commands()] if shell else ["Bash(loom *)"]
    deny.append("Bash(rm *)")
    return json.dumps({"permissions": {"allow": allow, "deny": deny}}, indent=2) + "\n"


#: Where each agent tool reads the quilt's rules for its agents: one policy, loom's own, rendered per tool (DR-283-ikmartin).
CLAUDE_SETTINGS = ".claude/settings.json"
CODEX_RULES = ".codex/rules/loom.rules"


def codex_rules(*, shell: bool = False) -> str:
    """`.codex/rules/loom.rules`: the same policy as `permissions_json`, as Codex's command-prefix rules; over MCP, `loom` in a shell is forbidden and the tools are the way in.

    Codex matches commands, not paths, so the path rules have no counterpart here; the author's own verbs are refused by loom itself for an agent's name whatever the tool (DR-185). Codex reads a project's rules only once the project is trusted. Unverified: Codex was not installed where this was written.
    """
    import json

    head = [
        "# Written by loom from its table of what an agent may run; `loom upgrade` rewrites it, and a quilt does not change it.",
        "# Rules of your own go in another file in this directory, which loom never touches.",
    ]

    def rule(words: list[str], decision: str) -> str:
        return f"prefix_rule(pattern = [{', '.join(json.dumps(w) for w in words)}], decision = {json.dumps(decision)})"

    if shell:
        body = [rule(["loom", *c.split()], "allow") for c in sorted(AGENT_COMMANDS)]
        body += [rule(["loom", *c.split()], "forbidden") for c in author_commands()]
    else:
        body = [rule(["loom"], "forbidden")]
    body.append(rule(["rm"], "forbidden"))
    return "\n".join(head + body) + "\n"


def vendor_files(config: QuiltConfig, *, shell: bool = False) -> dict[str, str]:
    """Quilt-relative path -> text for the permission files loom owns whole in a quilt with `config`, in one variant; the agent root files are not among them (see `ensure_root_line`), nor the untracked MCP client files (`ai.clients`)."""
    return {CLAUDE_SETTINGS: permissions_json(config, shell=shell), CODEX_RULES: codex_rules(shell=shell)}


def variant(root: Path) -> str | None:
    """Which way the quilt's agents reach loom, read off its permission file: `MCP` when it allows the loom server's tools, `SHELL` when it allows `loom` commands, None with no file. Never recorded anywhere else, so it cannot disagree with what the file says."""
    p = root / CLAUDE_SETTINGS
    try:
        allow = json.loads(p.read_text(encoding="utf-8"))["permissions"]["allow"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if "mcp__loom__*" in allow:
        return MCP
    return SHELL if any(str(r).startswith("Bash(loom ") for r in allow) else None


@dataclass
class LayerReport:
    written: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)  # edited mode files left alone
    new_beside: list[str] = field(default_factory=list)  # <mode>.md.new written
    unchanged: list[str] = field(default_factory=list)


ROOT_FILES = ("CLAUDE.md", "AGENTS.md", "GEMINI.md")


def ensure_root_line(root: Path, write: bool = True, *, shell: bool = False) -> list[str]:
    """Put loom's one line, the variant's, into each agent's root file without taking the files over; returns what was written, or with `write` false what would be.

    These are the files an agent reads before anything else, and they are also where an author writes what is true of *their* project — so loom contributes a line and owns nothing else. The other variant's line is replaced where it stands; everything around it is left exactly as the author left it. Loom writing the whole file is what clobbered hand-written instructions on every upgrade (DR-151).
    """
    line, other = (SHELL_LINE, MCP_LINE) if shell else (MCP_LINE, SHELL_LINE)
    written: list[str] = []
    for name in ROOT_FILES:
        p = root / name
        existing = p.read_text(encoding="utf-8") if p.is_file() else ""
        lines = existing.splitlines()
        if line in lines:
            continue
        written.append(name)
        if not write:
            continue
        if other in lines:
            p.write_text("\n".join(line if x == other else x for x in lines) + "\n", encoding="utf-8")
            continue
        p.write_text(existing.rstrip("\n") + ("\n\n" if existing.strip() else "") + line + "\n", encoding="utf-8")
    return written


def init_layer(root: Path, *, shell: bool = False) -> LayerReport:
    """Write `ai/` and the vendor files into a quilt that has no `ai/` yet, the permission files for every tool among them in one variant: what agents may run is loom's, and the same whichever tool runs them (DR-283)."""
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
    sty = root / STY
    write_versions(
        root,
        {**texts, STY: shipped_sty()} if sty.is_file() and sty.read_text(encoding="utf-8") == shipped_sty() else texts,
    )
    rep.written.append(f"ai/{VERSION_FILE}")
    for rel, text in vendor_files(quilt_config(root), shell=shell).items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        rep.written.append(rel)
    rep.written.extend(ensure_root_line(root, shell=shell))
    return rep


def upgrade_layer(root: Path, write: bool = True, *, shell: bool | None = None) -> LayerReport:
    """Refresh the generated files of an existing `ai/`; keep edited mode files and write `.new` beside them.

    The permission files keep the variant they are in (`variant`) unless `shell` says which; with none, MCP. With `write` false nothing is written and the report says what would be: `loom doctor`'s dry run, byte for byte what `loom upgrade` compares.
    """
    if shell is None:
        shell = variant(root) == SHELL
    ai = root / "ai"
    rep = LayerReport()
    if not ai.is_dir():
        return rep
    recorded = read_versions(root)
    texts = tracked_docs()
    wrote_beside: dict[
        str, str
    ] = {}  # each .new as loom wrote it, so a later upgrade can tell the author's merge from it
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
            beside = p.with_name(name + ".new")
            there = beside.read_text(encoding="utf-8") if beside.is_file() else None
            last = recorded.get(name + ".new")
            rep.kept.append(rel)
            if there is None and last == sha(shipped):
                # merged and deleted: the author has this version, and nothing goes beside it until loom ships another
                wrote_beside[name + ".new"] = last
                continue
            # a .new as loom wrote it is brought up to date; one the author has begun merging into is theirs (K4)
            if there is None or (sha(there) == last and there != shipped):
                if write:
                    beside.write_text(shipped, encoding="utf-8")
                wrote_beside[name + ".new"] = sha(shipped)
            elif last:
                wrote_beside[name + ".new"] = last
            rep.new_beside.append(rel + ".new")
    names = {Path(rel).name for rel in texts} | {STY}
    new_versions = {name: h for name, h in recorded.items() if name in names} | wrote_beside
    for rel, shipped in texts.items():
        if rel in rep.kept:
            continue  # the record keeps the hash of what was shipped last time, so a later upgrade still sees the edit
        new_versions[Path(rel).name] = sha(shipped)
    sty = root / STY
    if STY not in new_versions and sty.is_file() and sty.read_text(encoding="utf-8") == shipped_sty():
        new_versions[STY] = sha(shipped_sty())  # loom's own, so an edit from here on is known as one
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
    for rel, text in vendor_files(quilt_config(root), shell=shell).items():
        p = root / rel
        if p.is_file() and p.read_text(encoding="utf-8") == text:
            rep.unchanged.append(rel)
            continue
        if write:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        rep.written.append(rel)
    rep.written.extend(ensure_root_line(root, write, shell=shell))
    return rep


def settings_deny_paths(config: QuiltConfig, *, shell: bool = False) -> list[str]:
    """The Edit/Write patterns and commands the generated settings deny for a quilt with `config`, for tests."""
    data = json.loads(permissions_json(config, shell=shell))
    return [str(r) for r in data["permissions"]["deny"]]
