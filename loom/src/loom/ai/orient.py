"""`loom ai orient [--run RUN]`: the static orientation followed by what only the moment knows."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from loom.records.store import Records
from loom.render.threads import SESSION_FILES
from loom.scan.scan import ScanResult

STATIC = ("orientation.md", "rules.md", "formatting.md")
#: How much of a session's chat `orient --session` prints: enough to pick the conversation up, not its history.
TAIL = 20


def static_text(root: Path) -> str:
    """The standing documents, the quilt's own copies where it has them: where an agent is, how it works, and how to write what the author reads.

    Printed together because the alternative is a two-part instruction — run a command, then read a file — whose second half fails silently. A command either ran or it did not.
    """
    from loom.ai.layout import tracked_docs

    shipped = tracked_docs()  # as `ai init` writes them: the rules with their list of allowed commands filled in
    out: list[str] = []
    for name in STATIC:
        p = root / "ai" / name
        text = p.read_text(encoding="utf-8") if p.is_file() else shipped[f"ai/{name}"]
        out.append(text.rstrip("\n"))
    return "\n\n---\n\n".join(out) + "\n"


def mode_text(root: Path, name: str) -> str:
    """Mode `name`'s file, the quilt's own copy where it has one, else the shipped one; `name` is one of `MODES`."""
    p = root / "ai" / "modes" / f"{name}.md"
    if p.is_file():
        return p.read_text(encoding="utf-8")
    return resources.files("loom").joinpath("assets", "ai", "modes", f"{name}.md").read_text(encoding="utf-8")


def mode_index(root: Path) -> str:
    """The modes, one line each, from each file's `When it fits:` line: what `loom ai orient` prints after the documents, and the server's instructions after it.

    Drawn from `MODES` rather than the directory, so a file loom no longer ships is not offered; a quilt copy edited to drop the line shows the mode with no description rather than none.
    """
    from loom.ai.layout import MODES

    lines = ["", "---", "", "# Modes", "", "`loom ai mode NAME` prints one in full.", ""]
    for name in MODES:
        fits = next(
            (
                ln.removeprefix("When it fits:").strip()
                for ln in mode_text(root, name).splitlines()
                if ln.startswith("When it fits:")
            ),
            "",
        )
        lines.append(f"- **{name}**: {fits}" if fits else f"- **{name}**")
    return "\n".join(lines) + "\n"


def instructions(root: Path, name: str) -> str:
    """What `loom mcp` tells a client when it attaches: who the agent is, to call `loom_ai_orient` first, how tools map to commands, then the mode index.

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
    return opening + "\n" + mode_index(root).replace("`loom ai mode NAME`", "`loom_ai_mode`")


def _research_state(result: ScanResult) -> list[str]:
    """The research state as `ai orient` prints it: its path and hash, who last wrote it, and the page itself; or how to start one."""
    from loom.pages import read, state_page, text_hash, writes

    root = result.quilt.root
    page = state_page(result.quilt.config)
    text = read(root, page)
    if text is None:
        return [f'- research state: none yet, at `{page.path}`; `loom write state - --as "…"` writes one']
    done = writes(root, result.quilt.history_dir, page)
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
    lines += _research_state(result)
    if run is not None:
        rel = run.relative_to(root).as_posix() if run.is_absolute() else run.as_posix()
        lines += ["", f"# Your session: `{rel}`", ""]
        lines.append("Writing lands in the active session; `--session` names another one where a command takes it.")
        if session_id is not None:
            from loom.mailbox import read_events, render

            events = read_events(root, session_id)
            lines += ["", "## the chat", ""]
            if len(events) > TAIL:
                lines.append(
                    f"(the last {TAIL} of {len(events)} messages; `loom session next --since 0 --wait 0 --json` prints them all)"
                )
            lines.append(render(events[-TAIL:]) if events else "(nothing said yet)")
        log = run / "run.log"
        lines += ["", "## the command log", ""]
        lines.append(log.read_text(encoding="utf-8").rstrip("\n") if log.is_file() else "(empty)")
        outputs = sorted(p.name for p in run.iterdir() if p.is_file() and p.name not in SESSION_FILES)
        lines += ["", "## files in the session", ""]
        lines.append(", ".join(outputs) if outputs else "(none)")
    return "\n".join(lines) + "\n"
