"""`loom since`: what people did since this agent last looked, and the marker moved past it."""

from __future__ import annotations

from typing import Any

import click

from loom.cli._common import writer
from loom.cli._quilt import open_scan, quilt_option
from loom.cli.report import Report, counted


@click.command(name="since")
@click.option("--as", "declared", default=None, help="Who is looking. An agent names itself, including Agent or AI.")
@click.option("--dry-run", is_flag=True, help="Report, and leave your marker where it was.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def since_command(declared: str | None, dry_run: bool, as_json: bool, quilt_path: str | None) -> None:
    """Report what people did since you last looked, and move your marker past it.

    People's annotations and replies, whole, with the words they are on and what they propose; what they resolved, applied, discarded or reopened; what they accepted, and every accepted key gone stale, with why; their edits to the research state, as a diff; and what they said in a session's transcript. Your first look reports what happened since the active session was last opened. The marker is yours alone, one per name, and kept on this machine only.
    """
    from loom.since import since, write_marker

    result = open_scan(quilt_path)
    root = result.quilt.root
    name, _kind = writer(root, declared)
    got = since(result, name)
    if not dry_run and got.marker is not None:
        write_marker(root, name, got.marker)
    Report(_verdict(got), lines=_lines(got), dry_run=dry_run, data=got.to_json()).emit(as_json)


def _at(when: str | None) -> str:
    return (when or "")[:16].replace("T", " ")


def _verdict(got: Any) -> str:
    if got.first:
        window = f"your first look as {got.name}" + (
            f", since the session opened ({_at(got.start)})" if got.start else ""
        )
    else:
        window = f"since you last looked ({_at(got.start)})"
    if got.empty:
        return f"{window}: nothing"
    said = [
        counted(len(got.annotations), "annotation") if got.annotations else "",
        counted(len(got.acts), "annotation settled", "annotations settled") if got.acts else "",
        counted(len(got.accepted), "acceptance") if got.accepted else "",
        counted(len(got.stale), "key gone stale", "keys gone stale") if got.stale else "",
        "the research state changed" if got.state else "",
        counted(len(got.said), "message") if got.said else "",
    ]
    return f"{window}: " + ", ".join(s for s in said if s)


def _lines(got: Any) -> list[str]:
    """The report's detail, one block per kind of record, each under its heading and count."""
    from loom.mailbox import render_changes

    out: list[str] = []

    def block(heading: str, n: int, lines: list[str]) -> None:
        if n:
            out.extend(["", f"{heading} ({n})", *lines])

    block("annotations and replies", len(got.annotations), render_changes(got.annotations).splitlines())
    acts = []
    for a in got.acts:
        whose = "yours" if a.get("yours") else f"{a['of']}'s"
        acts.append(f"  {a['id']}  {a['kind']} · {a['target']} · {whose} · {a['act']} by {a['by']} at {_at(a['when'])}")
        if a.get("body"):
            acts.append(f'      "{a["body"]}"')
    block("annotations settled", len(got.acts), acts)
    block(
        "accepted",
        len(got.accepted),
        [f"  {r['key']}  {r['name']} · by {r['by']} at {_at(r['when'])}" for r in got.accepted],
    )
    block("gone stale", len(got.stale), [f"  {r['key']}  {r['name']} · {'; '.join(r['why'])}" for r in got.stale])
    state = []
    for s in got.state:
        state.append(f"  {s['act']} by {s['by']} at {_at(s['when'])}" if s["by"] else f"  {s['act']} by hand")
        state += ["    " + ln for ln in s["diff"].splitlines()]
    block("research state", len(got.state), state)
    said = []
    for m in got.said:
        carried = f" (with {counted(m['carried'], 'annotation')})" if m["carried"] else ""
        said.append(f"  {m['session']} #{m['seq']}  {m['by']} at {_at(m['when'])}{carried}")
        if m["body"]:
            said.append(f'      "{m["body"]}"')
    block("said", len(got.said), said)
    return out
