"""`loom ai orient [--run RUN]` (book 11.3): the static orientation followed by what only the moment knows."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from loom.records.store import Records
from loom.scan.scan import ScanResult

STATIC = ("orientation.md", "rules.md")


def static_text(root: Path) -> str:
    """Both standing documents, the quilt's own copies where it has them: where an agent is, then how it works.

    Printed together because the alternative is a two-part instruction — run a command, then read a file — whose second half fails silently. A command either ran or it did not.
    """
    out: list[str] = []
    for name in STATIC:
        p = root / "ai" / name
        text = (
            p.read_text(encoding="utf-8")
            if p.is_file()
            else resources.files("loom").joinpath("assets", "ai", name).read_text(encoding="utf-8")
        )
        out.append(text.rstrip("\n"))
    return "\n\n---\n\n".join(out) + "\n"


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


def live_text(result: ScanResult, records: Records, run: Path | None) -> str:
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
    errors = sum(1 for d in result.lint if d.severity == "error")
    lines.append(f"- lint: {errors} error(s); run `loom lint` for the list")
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
    if run is not None:
        rel = run.relative_to(root).as_posix() if run.is_absolute() else run.as_posix()
        lines += ["", f"# Your session: `{rel}`", ""]
        lines.append("Writing lands in the active session; `--session` names another one where a command takes it.")
        thread = run / "thread.md"
        lines += ["", "## thread.md", ""]
        lines.append(
            thread.read_text(encoding="utf-8").rstrip("\n") if thread.is_file() else "(no thread.md yet; write one)"
        )
        log = run / "run.log"
        lines += ["", "## the command log", ""]
        lines.append(log.read_text(encoding="utf-8").rstrip("\n") if log.is_file() else "(empty)")
        outputs = sorted(
            p.name for p in run.iterdir() if p.is_file() and p.name not in ("run.toml", "run.log", "thread.md")
        )
        lines += ["", "## files in the session", ""]
        lines.append(", ".join(outputs) if outputs else "(none)")
    return "\n".join(lines) + "\n"
