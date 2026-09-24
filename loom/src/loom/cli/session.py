"""`loom session new | use | list | rename | close | delete` (plan 0.13 §5, book 11).

A session is where work belongs; the author is who did it. These commands say which session is current, and the record says the rest.
"""

from __future__ import annotations

import click

from loom.cli._common import ContentError, EnvError, note
from loom.cli._quilt import open_quilt, quilt_option
from loom.sessions import (
    active,
    close,
    create,
    delete,
    index_path,
    rename,
    resolve,
    resume,
    sessions,
    set_active,
)


@click.group(name="session")
def session() -> None:
    """Sessions: the stretch of work an annotation belongs to, and which one is current.

    A session has a stable id (`s-2026-09-20-0001`) that never changes and is what records and URLs use, and a title you may change whenever you like. One is active at a time, for you and for any agent working in this quilt, so that a person and an agent at the same job land in the same place.
    """


def _who(quilt_path: str | None, author: str | None) -> tuple[object, str]:
    from loom.cli._common import whoever

    quilt = open_quilt(quilt_path)
    return quilt, whoever(quilt.root, author)


@session.command(name="new")
@click.argument("title", required=False)
@click.option("--author", default=None, help="Who opened it, when the user config and git do not say.")
@click.option("--no-use", is_flag=True, help="Create it without making it the active session.")
@quilt_option
def new_command(title: str | None, author: str | None, no_use: bool, quilt_path: str | None) -> None:
    """Open a session and make it the active one. With no TITLE, one named after today."""
    quilt, who = _who(quilt_path, author)
    root = quilt.root  # type: ignore[attr-defined]
    s = create(root, (title or "").strip() or "untitled", who)
    if not no_use:
        set_active(root, s.id)
    click.echo(f"{s.id}  {s.title}" + ("" if no_use else "  (active)"))


@session.command(name="use")
@click.argument("which")
@click.option("--author", default=None, help="Who resumed it, when the user config and git do not say.")
@quilt_option
def use_command(which: str, author: str | None, quilt_path: str | None) -> None:
    """Make WHICH the active session, resuming it when it was closed. WHICH is an id, a title, or a unique id suffix."""
    quilt, who = _who(quilt_path, author)
    root = quilt.root  # type: ignore[attr-defined]
    s = resolve(root, which)
    if s is None:
        raise ContentError(f"no session matches {which!r}; loom session list shows them")
    if s.state == "deleted":
        raise ContentError(f"{s.id} was deleted; nothing new can be written to it")
    if s.state == "closed":
        resume(root, s.id, who)
        note(f"resumed {s.id}; what changes from here is this round")
    set_active(root, s.id)
    click.echo(f"{s.id}  {s.title}  (active)")


@session.command(name="list")
@click.option("--all", "show_all", is_flag=True, help="Include closed and deleted sessions.")
@click.option("--json", "as_json", is_flag=True, help="Print as JSON.")
@quilt_option
def list_command(show_all: bool, as_json: bool, quilt_path: str | None) -> None:
    """What sessions this quilt has, newest last, with the active one marked."""
    import json as _json

    quilt = open_quilt(quilt_path)
    root = quilt.root
    here = active(root)
    standing = [s for s in sessions(root, deleted=show_all).values() if show_all or s.state == "open"]
    if as_json:
        click.echo(
            _json.dumps(
                [
                    {
                        "id": s.id,
                        "title": s.title,
                        "state": s.state,
                        "created": s.created,
                        "rounds": len(s.rounds),
                        "active": s.id == here,
                    }
                    for s in standing
                ],
                indent=2,
            )
        )
        return
    if not standing:
        click.echo("no sessions yet; loom session new opens one, and annotating opens one for you")
        return
    for s in standing:
        mark = "*" if s.id == here else " "
        state = "" if s.state == "open" else f"  [{s.state}]"
        click.echo(f"{mark} {s.id}  {s.title}{state}")


@session.command(name="rename")
@click.argument("which")
@click.argument("title")
@click.option("--author", default=None, help="Who renamed it, when the user config and git do not say.")
@quilt_option
def rename_command(which: str, title: str, author: str | None, quilt_path: str | None) -> None:
    """Change a session's title. Nothing moves: the id is the address and does not change."""
    quilt, who = _who(quilt_path, author)
    root = quilt.root  # type: ignore[attr-defined]
    s = resolve(root, which)
    if s is None:
        raise ContentError(f"no session matches {which!r}; loom session list shows them")
    rename(root, s.id, title, who)
    click.echo(f"{s.id}  {title}")


@session.command(name="close")
@click.argument("which", required=False)
@click.option("--author", default=None, help="Who closed it, when the user config and git do not say.")
@quilt_option
def close_command(which: str | None, author: str | None, quilt_path: str | None) -> None:
    """End a session's current round. With no WHICH, the active one, which then stops being active."""
    quilt, who = _who(quilt_path, author)
    root = quilt.root  # type: ignore[attr-defined]
    here = active(root)
    s = resolve(root, which) if which else (sessions(root).get(here or ""))
    if s is None:
        raise ContentError(f"no session matches {which!r}" if which else "no session is active")
    close(root, s.id, who)
    if s.id == here:
        set_active(root, None)
    click.echo(f"closed {s.id}  {s.title}")


@session.command(name="delete")
@click.argument("which")
@click.option("--purge", is_flag=True, help="Really erase it, annotations and all. This cannot be undone.")
@click.option("--why", default=None, help="Why it was deleted; kept on the tombstone.")
@click.option("--author", default=None, help="Who deleted it, when the user config and git do not say.")
@click.option("--yes", "-y", is_flag=True, help="Skip the question --purge asks.")
@quilt_option
def delete_command(
    which: str, purge: bool, why: str | None, author: str | None, yes: bool, quilt_path: str | None
) -> None:
    """Remove a session from view, or with --purge erase it and everything written in it.

    A plain delete is a tombstone: the session stops being shown and every annotation made in it stays in the log, which is the rule the log has always had. `--purge` is the other thing, and is deliberately only here and never in the viewer: it rewrites the annotation log, and what it removes is gone.
    """
    import sys

    from loom.records.log import LOG, log_path

    quilt, who = _who(quilt_path, author)
    root = quilt.root  # type: ignore[attr-defined]
    s = resolve(root, which)
    if s is None:
        raise ContentError(f"no session matches {which!r}; loom session list shows them")
    if purge:
        kept, dropped = _without(root, s.id)
        if not yes:
            if not sys.stdin.isatty():
                raise EnvError(
                    f"--purge erases {dropped} annotation(s) and cannot be undone; pass --yes when you mean it"
                )
            click.echo(f"--purge erases {s.id} and the {dropped} annotation(s) written in it. This cannot be undone.")
            click.confirm("erase it?", abort=True)
        log_path(root).write_text("".join(kept), encoding="utf-8")
        _purge_index(root, s.id)
        if s.directory(root).is_dir():
            import shutil

            shutil.rmtree(s.directory(root))
        if active(root) == s.id:
            set_active(root, None)
        click.echo(f"erased {s.id} and {dropped} annotation(s) from {LOG}")
        return
    delete(root, s.id, who, why or "")
    if active(root) == s.id:
        set_active(root, None)
    click.echo(f"deleted {s.id}  {s.title}; its annotations stay in the log, and the viewer stops showing them")


def _without(root, sid: str) -> tuple[list[str], int]:  # type: ignore[no-untyped-def]
    """The annotation log's lines with one session's events removed, and how many were removed."""
    import json

    from loom.records.log import log_path

    p = log_path(root)
    if not p.is_file():
        return [], 0
    kept, dropped = [], 0
    for line in p.read_text(encoding="utf-8").splitlines(keepends=True):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            kept.append(line)
            continue
        if isinstance(event, dict) and str(event.get("session", "")) == sid:
            dropped += 1
            continue
        kept.append(line)
    return kept, dropped


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
    """(root, session, name, kind) for a dispatch command: the session it is about and who is at the keyboard."""
    from loom.cli._common import find_session, writer

    quilt = open_quilt(quilt_path)
    found = find_session(quilt.root, which)
    name, kind = writer(quilt.root, declared)
    return quilt.root, found, name, kind


@session.command(name="send")
@click.argument("text", required=False, default="")
@click.option("--session", "which", default=None, envvar="LOOM_SESSION", help="The session to post into.")
@click.option("--as", "declared", default=None, help="Who is speaking. An agent names itself, including Agent or AI.")
@quilt_option
def send_command(text: str, which: str | None, declared: str | None, quilt_path: str | None) -> None:
    """Post TEXT into a session, from the terminal, with what you marked since the last message; with no TEXT, what you marked alone.

    The symmetric verb to the composer in the viewer: both append to the same inbox, and a message lands whether or not anybody is listening. Loom is a mailbox: a parked reader wakes because a file grew, and where the quilt lets it, `loom serve` starts the configured agent for a turn.
    """
    from loom.mailbox import attached, pending, post, waiting_on

    root, found, name, kind = _mail(quilt_path, which, declared)
    # The same packet the viewer's input sends: a post says what changed, not only what was typed, and a message sent
    # from the terminal is not a lesser message.
    packet = pending(root, found, name)
    if not text.strip() and not packet:
        raise EnvError("nothing to send: no words, and nothing marked since the last message")
    post(root, found.id, text.strip(), name, kind="message", changed=packet)
    here = [r for r in attached(root, found.id) if r.get("who") != name]
    click.echo(f"posted to {found.id}")
    if here:
        click.echo("listening: " + ", ".join(f"{r.get('who')} ({r.get('kind')})" for r in here))
    else:
        note(waiting_on(root, found.id, name))


@session.command(name="say")
@click.argument("text")
@click.option("--session", "which", default=None, envvar="LOOM_SESSION", help="The session to speak in.")
@click.option("--as", "declared", default=None, help="Who is speaking: your name, including Agent or AI.")
@quilt_option
def say_command(text: str, which: str | None, declared: str | None, quilt_path: str | None) -> None:
    """Say TEXT in a session's chat, as the agent; `-` reads it from stdin.

    The agent's half of the transcript, as `send` is the person's: the message goes into the session's inbox as written and carries no annotations. A `quilt:` or `cited:` link that names nothing the viewer shows is refused; `loom link` prints a correct one. Your own cursor moves past it when you had read everything before it, so `next` does not hand you your own words, and never past a message you have not read.
    """
    import sys

    from loom.mailbox import cursor, post, set_cursor

    root, found, name, kind = _mail(quilt_path, which, declared)
    if kind != "agent":
        raise EnvError("say is the agent's; a person uses loom session send")
    body = (sys.stdin.read() if text == "-" else text).strip()
    if not body:
        raise EnvError("a message with no text says nothing")
    from loom.links import LINK, refuse_bad_links

    if LINK.search(body):
        from loom.scan.scan import scan

        refuse_bad_links(scan(open_quilt(quilt_path)), root, body)
    e = post(root, found.id, body, name, kind="message")
    if cursor(root, found.id, name) == e.seq - 1:
        set_cursor(root, found.id, name, e.seq)
    click.echo(f"said in {found.id}")


@session.command(name="next")
@click.option("--session", "which", default=None, envvar="LOOM_SESSION", help="The session to park on.")
@click.option("--wait", default=120, show_default=True, help="Seconds to park before returning empty-handed.")
@click.option("--json", "as_json", is_flag=True, help="Print as JSON, with the same text under `text`.")
@click.option("--as", "declared", default=None, help="Who is parking. An agent names itself, including Agent or AI.")
@click.option("--since", type=int, default=None, help="Start after this sequence number instead of your own cursor.")
@quilt_option
def next_command(
    which: str | None, wait: int, as_json: bool, declared: str | None, since: int | None, quilt_path: str | None
) -> None:
    """Park until something lands in a session, print it, and exit. One call is one turn.

    For an agent. It returns the moment a message arrives rather than on a poll interval, so latency is an append and a wakeup; with nothing waiting it returns empty-handed when `--wait` runs out, and the agent parks again. Keep `--wait` under whatever timeout your harness puts on a tool call.

    The inbox is read and never consumed: your cursor moves, the message stays, and a second reader sees it too. Nothing here assigns you anything -- it is a broadcast, and what to do about a message is your judgement.
    """
    import json as _json
    import time

    from loom.mailbox import attach, cursor, read_events, render, set_cursor

    root, found, name, kind = _mail(quilt_path, which, declared)
    at = since if since is not None else cursor(root, found.id, name)
    attach(root, found.id, name, kind)
    deadline = time.monotonic() + max(0, wait)
    events = read_events(root, found.id, at)
    while not events and time.monotonic() < deadline:
        time.sleep(0.25)
        attach(root, found.id, name, kind)  # the heartbeat is what makes the composer's answer honest
        events = read_events(root, found.id, at)
    if events:
        set_cursor(root, found.id, name, events[-1].seq)
    text = render(events)
    if as_json:
        click.echo(
            _json.dumps(
                {
                    "session": found.id,
                    "title": found.title,
                    "from": at,
                    "to": events[-1].seq if events else at,
                    "events": [e.to_json() for e in events],
                    "text": text,
                },
                indent=2,
            )
        )
        return
    click.echo(text if events else "nothing yet")


@session.command(name="watch")
@click.argument("which", required=False)
@click.option("--as", "declared", default=None, help="Who is watching. An agent names itself, including Agent or AI.")
@quilt_option
def watch_command(which: str | None, declared: str | None, quilt_path: str | None) -> None:
    """Tail a session: print what lands, until you stop it.

    For a person. It delivers nothing and assigns nothing -- it blocks on the log, prints, and keeps a heartbeat so the composer can say honestly whether anybody is listening.
    """
    import time

    from loom.mailbox import attach, detach, last_seq, read_events, render

    root, found, name, kind = _mail(quilt_path, which, declared)
    at = last_seq(root, found.id)
    note(f"watching {found.id} ({found.title}) as {name}; Ctrl-C to stop")
    attach(root, found.id, name, kind)
    try:
        while True:
            events = read_events(root, found.id, at)
            if events:
                at = events[-1].seq
                click.echo(render(events))
            attach(root, found.id, name, kind)
            time.sleep(0.5)
    except KeyboardInterrupt:
        click.echo("")
    finally:
        detach(root, found.id, name)
