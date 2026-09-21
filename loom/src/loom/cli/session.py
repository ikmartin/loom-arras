"""`loom session new | use | list | rename | close | delete | migrate` (plan 0.13 §5, book 11).

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
                        "source": s.source,
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
                raise EnvError(f"--purge erases {dropped} annotation(s) and cannot be undone; pass --yes when you mean it")
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


@session.command(name="migrate")
@click.option("--author", default=None, help="Who ran the migration, when the user config and git do not say.")
@quilt_option
def migrate_command(author: str | None, quilt_path: str | None) -> None:
    """Give every existing run and every day's comments a session, so nothing written before sessions is orphaned.

    Nothing in the annotation log is rewritten: each session records the grouping its annotations already carry, and reading an annotation's session follows that. Running it twice adds nothing.
    """
    from loom.sessions import migrate

    quilt, who = _who(quilt_path, author)
    made = migrate(quilt.root, who)  # type: ignore[attr-defined]
    if not made:
        click.echo("nothing to migrate: every run and comment group already has a session")
        return
    for s in made:
        click.echo(f"{s.id}  {s.title}   <- {s.source}")
    click.echo(f"{len(made)} session(s) made")
