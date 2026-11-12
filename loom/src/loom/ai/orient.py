"""`loom ai orient [--run RUN]`: the static orientation followed by what only the moment knows."""

from __future__ import annotations

import re
from importlib import resources
from pathlib import Path

from loom.paths import AI, ANNOTATION_TYPES
from loom.records.store import Records
from loom.records.types import Types, load_types
from loom.render.threads import SESSION_FILES
from loom.scan.quilt import Quilt
from loom.scan.scan import ScanResult

STATIC = ("orientation.md", "rules.md", "formatting.md")
#: A type named in the standing documents and the modes: `{type:revision}`, filled with the type's name when it is printed, so a rename reaches every mode. An article before it and the word `annotation` after it are part of the match, so a type the quilt no longer lists reads as an untyped annotation.
PLACEHOLDER = re.compile(r"(?:\b([Aa])n? )?\{type:([a-z][a-z0-9-]*)\}( annotations?\b)?")
#: How much of a session's chat `orient --session` prints: enough to pick the conversation up, not its history.
TAIL = 20


def static_text(root: Path) -> str:
    """The standing documents, the quilt's own copies where it has them: where an agent is, how it works, and how to write what the author reads.

    Printed together because the alternative is a two-part instruction — run a command, then read a file — whose second half fails silently. A command either ran or it did not. The whole is longer than a client's shell shows at once (Claude Code's Bash tool keeps the first 2,000 bytes of anything over 30,000 and saves the rest to a file), which is why `orientation.md` opens with what must not be missed and says to read the rest.
    """
    from loom.ai.layout import tracked_docs

    shipped = tracked_docs()  # as `ai init` writes them: the rules with their list of allowed commands filled in
    types = load_types(root)
    out: list[str] = []
    for name in STATIC:
        p = root / AI / name
        text = p.read_text(encoding="utf-8") if p.is_file() else shipped[f"{AI}/{name}"]
        out.append(expand_types(text, types).rstrip("\n"))
        if name == "rules.md":
            out.append(types_text(types).rstrip("\n"))
    return "\n\n---\n\n".join(out) + "\n"


def expand_types(text: str, types: Types) -> str:
    """`text` with each `{type:ID}` filled with that type's name, and an article before it agreeing; a type the quilt no longer lists reads as an untyped annotation."""

    def fill(m: re.Match[str]) -> str:
        article, tid, noun = m.group(1), m.group(2), m.group(3) or ""
        t = types.get(tid)
        if t is None:
            said = "untyped annotation" + ("s" if noun.endswith("s") else "")
            return f"{'A' if article == 'A' else 'a'}n {said}" if article else said
        if not article:
            return t.name + noun
        an = "n" if t.name[:1].lower() in "aeiou" else ""
        return f"{article}{an} {t.name}{noun}"

    return PLACEHOLDER.sub(fill, text)


def types_line(types: Types) -> str:
    """The quilt's annotation types in one line, for the MCP server's instructions, which a client cuts short: each name, its id, and whether it stays open."""
    return "; ".join(
        f"{t.name} (`{t.id}`, {'stays open until resolved' if t.open else 'only informs'})" for t in types.types
    )


def types_text(types: Types) -> str:
    """The quilt's annotation types as the orientation prints them, after the rules: each with its id for `--type`, whether it stays open, and its instructions."""
    lines = [
        "# Annotation types",
        "",
        f"This quilt's types, from `{types.source or ANNOTATION_TYPES + ' (the defaults: the file is missing)'}`. Pass a type's id as `--type`; leave an annotation untyped when no type's instructions fit.",
    ]
    for t in types.types:
        stays = "stays open until resolved" if t.open else "only informs"
        listed = ", listed in Notes" if t.notes else ""
        lines += ["", f"## {t.name} (`--type {t.id}`): {stays}{listed}", ""]
        lines.append(t.instructions or "No instructions: use it when the person asks for it.")
    return "\n".join(lines) + "\n"


def modes_using(root: Path) -> dict[str, list[str]]:
    """Which modes name each type, by type id, read from the placeholders in the quilt's mode files (else the shipped ones)."""
    from loom.ai.layout import MODES

    out: dict[str, list[str]] = {}
    for name in MODES:
        p = root / AI / "modes" / f"{name}.md"
        text = (
            p.read_text(encoding="utf-8")
            if p.is_file()
            else resources.files("loom").joinpath("assets", "ai", "modes", f"{name}.md").read_text(encoding="utf-8")
        )
        for tid in dict.fromkeys(m.group(2) for m in PLACEHOLDER.finditer(text)):
            out.setdefault(tid, []).append(name)
    return out


def mode_text(root: Path, name: str) -> str:
    """Mode `name`'s file, the quilt's own copy where it has one, else the shipped one, with its types named as the quilt names them; `name` is one of `MODES`."""
    p = root / AI / "modes" / f"{name}.md"
    if p.is_file():
        text = p.read_text(encoding="utf-8")
    else:
        text = resources.files("loom").joinpath("assets", "ai", "modes", f"{name}.md").read_text(encoding="utf-8")
    return expand_types(text, load_types(root))


def fits(root: Path, name: str) -> str:
    """Mode `name`'s `When it fits:` line, without its label: the index's entry and the MCP prompt's description; '' when the quilt's copy dropped it."""
    return next(
        (
            ln.removeprefix("When it fits:").strip()
            for ln in mode_text(root, name).splitlines()
            if ln.startswith("When it fits:")
        ),
        "",
    )


def mode_index(root: Path) -> str:
    """The modes, one line each, from each file's `When it fits:` line: what `loom ai orient` prints after the documents, and the server's instructions after it.

    Drawn from `MODES` rather than the directory, so a file loom no longer ships is not offered; a quilt copy edited to drop the line shows the mode with no description rather than none.
    """
    from loom.ai.layout import MODES

    lines = ["", "---", "", "# Modes", "", "`loom ai mode NAME` prints one in full.", ""]
    for name in MODES:
        line = fits(root, name)
        lines.append(f"- **{name}**: {line}" if line else f"- **{name}**")
    return "\n".join(lines) + "\n"


def instructions(root: Path, name: str) -> str:
    """What `loom mcp` tells a client when it attaches: who the agent is, to call `loom_ai_orient` first, how tools map to commands, the bridge, then the mode index.

    Short by design: Claude Code keeps the first 4,096 characters of a server's instructions and Codex reads the first 512 as a summary, so the opening stands alone and the orientation, the rules and the quilt's state are a tool call away rather than cut off.
    """
    from loom.scan.quilt import load_quilt

    quilt = load_quilt(root)
    opening = (
        f"This is loom, serving the quilt {quilt.name}: a research project, usually mathematical, kept as LaTeX. "
        f"You are attached as {name}. Before anything else, and again whenever your context has been compacted, "
        "call loom_ai_orient: it is your orientation, the rules, the modes and the quilt's state. Each tool is the "
        "loom command of the same name (loom_status is `loom status`), with its options as arguments; the author's "
        "commands are not tools."
    )
    bridge = (
        "When the person points at something without naming it, loom_here says what they are looking at in the "
        "viewer; loom_since says what they did since you last looked, so call it when a conversation starts. "
        "An annotation on a PDF page comes with a crop of the page as an image: TeX you read off a crop is your own "
        "reading, while a `source` span is the work's own text. "
        f"The quilt's annotation types, by the id `type` takes: {types_line(load_types(root))}; when to use each is in loom_ai_orient."
    )
    return opening + "\n" + bridge + "\n" + mode_index(root).replace("`loom ai mode NAME`", "`loom_ai_mode`")


def research_state(quilt: Quilt) -> list[str]:
    """The research state as `ai orient` prints it: its path and hash, who last wrote it, and the page itself; or how to start one. Also what `loom mcp` serves as `quilt:state`."""
    from loom.pages import read, state_page, text_hash, writes

    root = quilt.root
    page = state_page(quilt.config)
    text = read(root, page)
    if text is None:
        return [f'- research state: none yet, at `{page.path}`; `loom write state - --as "…"` writes one']
    done = writes(root, quilt.history_dir, page)
    last = done[-1] if done else None
    by = f"; last written by {last.actor} on {last.when[:10]}" if last else ""
    edited = "; edited by hand since" if last is None or last.get("to") != text_hash(text) else ""
    return [
        "",
        "# Research state",
        "",
        f'`{page.path}`, {text_hash(text)}{by}{edited}. Write it with `loom write state - --base HASH --as "…"`.',
        "",
        text.rstrip("\n"),
    ]


def open_sessions(root: Path, include_closed: bool = False) -> list[tuple[str, str, str, bool]]:
    """(id, title, created, closed) for every session, oldest first; closed ones only when asked."""
    from loom.sessions import sessions

    out: list[tuple[str, str, str, bool]] = []
    for s in sessions(root).values():
        closed = s.state != "open"
        if closed and not include_closed:
            continue
        out.append((s.id, s.title, s.created, closed))
    return out


def live_text(result: ScanResult, records: Records, run: Path | None, session_id: str | None = None) -> str:
    from loom.cli.review import status_payload

    root = result.quilt.root
    cfg = result.quilt.config
    lines = ["", "---", "", "# Live state", ""]
    lines.append(
        f"- quilt: `{root.name}` at `{root}`; prefix `{cfg.prefix}`; main `{result.default_master or '(none)'}`"
    )
    lines.append(f"- masters: {', '.join(result.masters) if result.masters else '(none)'}")
    payload = status_payload(result, records)
    s = payload["summary"]
    lines.append(
        f"- status: {s['stale']} stale of {s['accepted'] + s['stale']} accepted; {s['draft']} draft; {s['incomplete']} incomplete; {s['loose']} loose; {s['proved']} proved, {s['settled']} settled"
    )
    from loom.cli.review import agent_line

    lines.append(f"- agent documents: {agent_line(payload) or 'none'}")
    from loom.agents import always_protected

    deny = ", ".join(f"`{p}`" for p in cfg.agents_deny) or "nothing more"
    lines.append(
        f"- protected, which no agent writes: {', '.join(f'`{p}`' for p in always_protected(cfg))}; and what `[agents] deny` names: {deny}"
    )
    from loom.cli.diagnostics import tally

    lines.append(f"- lint: {tally(result.lint, result)}; run `loom lint` for the list")
    und = payload["undigested"]
    lines.append("- undigested citekeys: " + (", ".join(und) if und else "none"))
    from loom.sessions import active

    here = active(root)
    open_ones = open_sessions(root)
    if open_ones:
        lines.append("- open sessions:")
        for sid, title, created, _ in open_ones:
            lines.append(f"  - `{sid}` ({title}, opened {created})" + ("  <- active" if sid == here else ""))
    else:
        lines.append("- open sessions: none")
    lines += research_state(result.quilt)
    if run is not None:
        rel = run.relative_to(root).as_posix() if run.is_absolute() else run.as_posix()
        lines += ["", f"# Your session: `{rel}`", ""]
        lines.append("Writing lands in the active session; `--session` names another one where a command takes it.")
        if session_id is not None:
            from loom.mailbox import read_events, render

            events = read_events(root, session_id)
            lines += ["", "## the chat", ""]
            if len(events) > TAIL:
                lines.append(f"(the last {TAIL} of {len(events)} messages)")
            lines.append(render(events[-TAIL:]) if events else "(nothing said yet)")
        log = run / "run.log"
        lines += ["", "## the command log", ""]
        lines.append(log.read_text(encoding="utf-8").rstrip("\n") if log.is_file() else "(empty)")
        outputs = (
            sorted(p.name for p in run.iterdir() if p.is_file() and p.name not in SESSION_FILES) if run.is_dir() else []
        )
        lines += ["", "## files in the session", ""]
        lines.append(", ".join(outputs) if outputs else "(none)")
    return "\n".join(lines) + "\n"
