"""`loom note`: a note beside something the viewer shows, a quote among them, or keeping one so it never fades."""

from __future__ import annotations

import click

from loom.cli._common import EnvError
from loom.cli._quilt import open_scan, quilt_option
from loom.cli.report import Report


@click.command(name="note")
@click.argument("text", required=False, default="")
@click.option(
    "--on",
    "on",
    default=None,
    metavar="THING",
    help="What it is on: a key, a document, a cited work's citekey (with --page), a file the viewer shows by its path, a message as SESSION#SEQ, or a session.",
)
@click.option("--quote", default=None, help="The words it quotes there.")
@click.option("--page", type=int, default=None, help="The page, on a cited work or a PDF file, from 1.")
@click.option(
    "--box", default=None, metavar="X,Y,W,H", help="A region of the page or image, in points from its top left."
)
@click.option("--keep", "keep_id", default=None, metavar="ID", help="Keep note ID, so it never fades.")
@click.option(
    "--session",
    default=None,
    help="Write into this session: an id, a title, or a unique id suffix. Default the active one.",
)
@click.option("--as", "declared", default=None, help="Who is writing. An agent names itself, including Agent or AI.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def note_command(
    text: str,
    on: str | None,
    quote: str | None,
    page: int | None,
    box: str | None,
    keep_id: str | None,
    session: str | None,
    declared: str | None,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Write a note on THING, quoting words there or naming a region, or keep one.

    A note has no kind, severity or resolution: it says what someone wants kept beside a thing, and a quote is a note with the words it quotes. It fades from view after 14 days unless it is kept or something durable links to it -- an annotation, a message, the research state, a kept note -- and is never deleted. An agent reads a person's notes with `loom since`.
    """
    from loom.cli.review import _writer
    from loom.notes import NoteRefused, keep, write

    result = open_scan(quilt_path)
    root = result.quilt.root
    try:
        if keep_id:
            name = _writer(root, session, declared, dry_run=True)[2]
            note = keep(root, keep_id, name)
            Report(f"kept {note.id}: it will not fade", data={"note": note.to_dict()}).emit(as_json)
            return
        if not on:
            raise click.UsageError("say what the note is on: --on THING")
        rects = None
        if box:
            try:
                rects = [[float(v) for v in box.split(",")]]
            except ValueError:
                raise click.UsageError("--box is X,Y,W,H in points") from None
            if len(rects[0]) != 4:
                raise click.UsageError("--box is X,Y,W,H in points")
        sid, kind, name = _writer(root, session, declared)
        note = write(
            result,
            on,
            author=name,
            author_kind="agent" if kind == "agent" else "person",
            session=sid,
            body=text,
            quote=quote,
            page=page,
            rects=rects,
        )
    except NoteRefused as exc:
        raise EnvError(exc.message) from None
    Report(f"noted {note.id} on {on}: [](quilt:{note.id})", data={"note": note.to_dict()}).emit(as_json)
