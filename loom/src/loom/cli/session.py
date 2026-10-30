"""`loom session new | use | list | rename | close | delete | say`.

A session is where work belongs; the author is who did it. These commands say which session is current and write its transcript, and the record says the rest.
"""

from __future__ import annotations

import click

from loom.cli._common import ContentError, EnvError, find_session, from_stdin
from loom.cli._quilt import open_quilt, quilt_option
from loom.cli.help import CommandGroup
from loom.cli.report import Group, Item, Report, counted
from loom.sessions import (
    active,
    close,
    create,
    delete,
    index_path,
    rename,
    resume,
    sessions,
    set_active,
)


@click.group(name="session", cls=CommandGroup)
def session() -> None:
    """Open, name and write in sessions: the stretch of work an annotation belongs to, and which one is current.

    A session has a stable id (`s-2026-09-20-0001`) that never changes and is what records and URLs use, and a title you may change whenever you like. One is active at a time, for you and for any agent working in this quilt, so that a person and an agent at the same job land in the same place.
    """


def _who(quilt_path: str | None, declared: str | None) -> tuple[object, str]:
    """(quilt, name) for a session writer: `--as` when given, else the configured author; an agent unnamed is refused (`writer`)."""
    from loom.cli._common import writer

    quilt = open_quilt(quilt_path)
    return quilt, writer(quilt.root, declared)[0]


AS_OPTION = click.option(
    "--as", "declared", default=None, metavar="NAME", help="Who acts; an agent names itself, including Agent or AI."
)
DRY_RUN = click.option("--dry-run", is_flag=True, help="Say what would change and write nothing.")


@session.command(name="new")
@click.option("--name", "title", default=None, metavar="TITLE", help="What to call it; default untitled.")
@AS_OPTION
@click.option("--no-use", is_flag=True, help="Create it without making it the active session.")
@DRY_RUN
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def new_command(
    title: str | None, declared: str | None, no_use: bool, dry_run: bool, as_json: bool, quilt_path: str | None
) -> None:
    """Open a session and make it the active one."""
    from loom.clock import stamp
    from loom.sessions import next_id

    quilt, who = _who(quilt_path, declared)
    root = quilt.root  # type: ignore[attr-defined]
    name = (title or "").strip() or "untitled"
    tail = ", not made active" if no_use else ", now the active session"
    if dry_run:
        sid = next_id(root, stamp()[:10])
        Report(
            f'would open {sid} "{name}"' + ("" if no_use else " and make it the active session"),
            dry_run=True,
            data={"session": sid, "title": name, "active": not no_use},
        ).emit(as_json)
        return
    s = create(root, name, who)
    if not no_use:
        set_active(root, s.id)
    Report(
        f'{s.id}  opened "{s.title}"' + tail,
        data={"session": s.id, "title": s.title, "active": not no_use},
    ).emit(as_json)


@session.command(name="use")
@click.argument("which")
@AS_OPTION
@DRY_RUN
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def use_command(which: str, declared: str | None, dry_run: bool, as_json: bool, quilt_path: str | None) -> None:
    """Make WHICH the active session, resuming it when it was closed. WHICH is an id, a title, or a unique id suffix."""
    quilt, who = _who(quilt_path, declared)
    root = quilt.root  # type: ignore[attr-defined]
    s = find_session(root, which, deleted=True)
    if s.state == "deleted":
        raise ContentError(f"{s.id} was deleted; nothing new can be written to it")
    resumed = s.state == "closed"
    data = {"session": s.id, "title": s.title, "resumed": resumed}
    if dry_run:
        Report(
            f'{s.id}  "{s.title}" would be the active session' + ("; it would be resumed" if resumed else ""),
            dry_run=True,
            data=data,
        ).emit(as_json)
        return
    if resumed:
        resume(root, s.id, who)
    set_active(root, s.id)
    Report(
        f'{s.id}  "{s.title}" is the active session'
        + ("; resumed, and what changes from here is a new round" if resumed else ""),
        data=data,
    ).emit(as_json)


@session.command(name="list")
@click.option("--all", "show_all", is_flag=True, help="Include closed and deleted sessions.")
@click.option("--json", "as_json", is_flag=True, help="Print as JSON.")
@quilt_option
def list_command(show_all: bool, as_json: bool, quilt_path: str | None) -> None:
    """List this quilt's sessions, newest last, with the active one marked."""
    quilt = open_quilt(quilt_path)
    root = quilt.root
    here = active(root)
    every = sessions(root, deleted=show_all)
    standing = sorted((s for s in every.values() if show_all or s.state == "open"), key=lambda s: s.id)
    rows = [
        {
            "id": s.id,
            "title": s.title,
            "state": s.state,
            "created": s.created,
            "rounds": len(s.rounds),
            "active": s.id == here,
        }
        for s in standing
    ]
    if not standing:
        verdict = (
            "no open sessions; loom session list --all shows the closed ones"
            if every
            else "no sessions yet; loom session new opens one, and annotating opens one for you"
        )
    else:
        closed = 0 if show_all else sum(1 for s in every.values() if s.state != "open")
        verdict = (
            counted(len(standing), "session" if show_all else "open session")
            + (f"; {here} is active (*)" if any(s.id == here for s in standing) else "; none is active")
            # what is left out is said, with the flag that shows it (T2)
            + (f"; {closed} closed: --all lists them" if closed else "")
        )
    items = [
        Item(f"{'*' if s.id == here else ' '} {s.id}  {s.title}" + ("" if s.state == "open" else f"  [{s.state}]"))
        for s in standing
    ]
    Report(
        verdict,
        groups=[Group("sessions" if show_all else "open sessions", items, limit=None)] if items else [],
        data={"sessions": rows},
    ).emit(as_json)


@session.command(name="rename")
@click.argument("which")
@click.option("--name", "title", required=True, metavar="TITLE", help="The new title.")
@AS_OPTION
@DRY_RUN
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def rename_command(
    which: str, title: str, declared: str | None, dry_run: bool, as_json: bool, quilt_path: str | None
) -> None:
    """Change a session's title. Nothing moves: the id is the address and does not change."""
    quilt, who = _who(quilt_path, declared)
    root = quilt.root  # type: ignore[attr-defined]
    s = find_session(root, which)
    data = {"session": s.id, "title": title}
    if dry_run:
        Report(f'would rename {s.id} to "{title}"', dry_run=True, data=data).emit(as_json)
        return
    rename(root, s.id, title, who)
    Report(f'renamed {s.id} to "{title}"', data=data).emit(as_json)


@session.command(name="close")
@click.argument("which", required=False)
@AS_OPTION
@DRY_RUN
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def close_command(
    which: str | None, declared: str | None, dry_run: bool, as_json: bool, quilt_path: str | None
) -> None:
    """End a session's current round. With no WHICH, the active one, which then stops being active."""
    quilt, who = _who(quilt_path, declared)
    root = quilt.root  # type: ignore[attr-defined]
    here = active(root)
    s = find_session(root, which)
    data = {"session": s.id, "title": s.title, "was_active": s.id == here}
    if s.state == "closed":
        Report(f'{s.id} is already closed: "{s.title}"; nothing recorded', data={**data, "closed": False}).emit(as_json)
        return
    data["closed"] = not dry_run
    if dry_run:
        Report(
            f'would close {s.id} "{s.title}"' + ("; no session would be active" if s.id == here else ""),
            dry_run=True,
            data=data,
        ).emit(as_json)
        return
    close(root, s.id, who)
    if s.id == here:
        set_active(root, None)
    Report(
        f'closed {s.id} "{s.title}"' + ("; no session is active now" if s.id == here else ""),
        data=data,
    ).emit(as_json)


@session.command(name="delete")
@click.argument("which")
@click.option("--purge", is_flag=True, help="Really erase it, annotations and all. This cannot be undone.")
@click.option("--why", default=None, help="Why it was deleted; kept on the tombstone.")
@AS_OPTION
@click.option("--yes", "-y", is_flag=True, help="Skip the question --purge asks.")
@DRY_RUN
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def delete_command(
    which: str,
    purge: bool,
    why: str | None,
    declared: str | None,
    yes: bool,
    dry_run: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Remove a session from view, or with --purge erase it and everything written in it.

    A plain delete is a tombstone: the session stops being shown and every annotation made in it stays in the log. `--purge` is deliberately only here and never in the viewer: it rewrites the annotation log, and what it removes is gone.
    """
    import sys

    from loom.records.log import LOG, log_path

    quilt, who = _who(quilt_path, declared)
    root = quilt.root  # type: ignore[attr-defined]
    # a deleted session is found, so deleting it again is answered rather than refused (T7)
    s = find_session(root, which, deleted=True)
    if s.state == "deleted" and not purge:
        Report(f'{s.id} "{s.title}" is already deleted; nothing written', data={"session": s.id, "purged": False}).emit(
            as_json
        )
        return
    if purge:
        from loom.cli._common import refuse_under_agent

        refuse_under_agent(
            "loom session delete --purge",
            "Erasing a session is the author's; an agent removes one from view with loom session delete, without --purge.",
            declared,
        )
        kept, dropped = _without(root, s.id)
        data = {"session": s.id, "title": s.title, "purged": True, "annotations": dropped}
        if dry_run:
            Report(f"would erase {s.id} and {counted(dropped, 'annotation')} from {LOG}", dry_run=True, data=data).emit(
                as_json
            )
            return
        if not yes:
            if not sys.stdin.isatty():
                raise EnvError(
                    f"--purge erases {counted(dropped, 'annotation')} and cannot be undone; pass --yes when you mean it"
                )
            click.echo(
                f"--purge erases {s.id} and the {counted(dropped, 'annotation')} written in it or answering them. This cannot be undone.",
                err=True,
            )
            click.confirm("erase it?", abort=True, err=True)
        log_path(root).write_text("".join(kept), encoding="utf-8")
        _purge_index(root, s.id)
        if s.directory(root).is_dir():
            import shutil

            shutil.rmtree(s.directory(root))
        if active(root) == s.id:
            set_active(root, None)
        Report(f"erased {s.id} and {counted(dropped, 'annotation')} from {LOG}", data=data).emit(as_json)
        return
    data = {"session": s.id, "title": s.title, "purged": False}
    if dry_run:
        Report(f'would delete {s.id} "{s.title}"; its annotations would stay in the log', dry_run=True, data=data).emit(
            as_json
        )
        return
    delete(root, s.id, who, why or "")
    if active(root) == s.id:
        set_active(root, None)
    Report(
        f'deleted {s.id} "{s.title}"; its annotations stay in the log, and the viewer stops showing them',
        data=data,
    ).emit(as_json)


def _without(root, sid: str) -> tuple[list[str], int]:  # type: ignore[no-untyped-def]
    """The annotation log's lines with one session's events removed, and how many annotations went with them.

    Also removes any other session's event that names an erased annotation -- a reply to it, and so on down, or an edit, resolve or discard of it -- which would otherwise be left naming nothing and be reported as `loom:foreign-annotations` for good. A line that is not JSON is kept as it stands.
    """
    import json

    from loom.records.log import log_path

    p = log_path(root)
    if not p.is_file():
        return [], 0
    kept: list[str] = []
    erased: set[str] = set()
    for line in p.read_text(encoding="utf-8").splitlines(keepends=True):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            kept.append(line)
            continue
        if isinstance(event, dict) and (
            str(event.get("session", "")) == sid
            or str(event.get("reply_to") or "-") in erased
            or (event.get("event") not in ("created", "replied") and str(event.get("id") or "-") in erased)
        ):
            if event.get("event") in ("created", "replied") and event.get("id"):
                erased.add(str(event["id"]))
            continue
        kept.append(line)
    return kept, len(erased)


def _purge_index(root, sid: str) -> None:  # type: ignore[no-untyped-def]
    """Drop one session's events from the index; the only place loom rewrites a log rather than appending to it."""
    import json

    p = index_path(root)
    if not p.is_file():
        return
    kept = []
    for line in p.read_text(encoding="utf-8").splitlines(keepends=True):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            kept.append(line)
            continue
        if isinstance(event, dict) and str(event.get("id", "")) == sid:
            continue
        kept.append(line)
    p.write_text("".join(kept), encoding="utf-8")


def _mail(quilt_path: str | None, which: str | None, declared: str | None):  # type: ignore[no-untyped-def]
    """(root, session, name, kind) for `say`: the session it is about and who is at the keyboard."""
    from loom.cli._common import find_session, writer

    quilt = open_quilt(quilt_path)
    found = find_session(quilt.root, which)
    name, kind = writer(quilt.root, declared)
    return quilt.root, found, name, kind


@session.command(name="say")
@click.argument("text", required=False, default="")
@click.option("--session", "which", default=None, envvar="LOOM_SESSION", help="The session to speak in.")
@click.option("--as", "declared", default=None, help="Who is speaking. An agent names itself, including Agent or AI.")
@DRY_RUN
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def say_command(
    text: str, which: str | None, declared: str | None, dry_run: bool, as_json: bool, quilt_path: str | None
) -> None:
    """Say TEXT in a session's transcript, with what you marked since your last message; `-` reads TEXT from stdin.

    The transcript is what the author reads afterwards. A person's message carries the annotations they made in the session since their last one, and with no TEXT it carries them alone. A `quilt:` or `cited:` link that names nothing the viewer shows is refused; `loom link` prints a correct one.
    """
    from loom.mailbox import pending, post

    root, found, name, _kind = _mail(quilt_path, which, declared)
    (said,) = from_stdin({"TEXT": text})
    body = (said or "").strip()
    packet = pending(root, found, name)
    if not body and not packet:
        raise EnvError("nothing to say: no words, and nothing marked since your last message")
    from loom.links import LINK, refuse_bad_links

    if LINK.search(body):
        from loom.scan.scan import scan

        refuse_bad_links(scan(open_quilt(quilt_path)), root, body)
    carried = f" with {counted(len(packet), 'annotation')} you marked" if packet else ""
    data: dict[str, object] = {"session": found.id, "carried": len(packet)}
    if dry_run:
        Report(f"would say in {found.id}{carried}", dry_run=True, data={**data, "seq": None}).emit(as_json)
        return
    e = post(root, found.id, body, name, kind="message", changed=packet)
    Report(f"said in {found.id}{carried}", data={**data, "seq": e.seq}).emit(as_json)
