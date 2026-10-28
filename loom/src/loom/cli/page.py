"""`loom write TARGET TEXT`: write a page, the quilt's research state or a cited work's overview (plan 0.21.3)."""

from __future__ import annotations

import click

from loom.cli._common import ContentError, EnvError, find_session, from_stdin, writer
from loom.cli._quilt import open_scan, quilt_option
from loom.cli.build_cmds import log_run
from loom.cli.report import Report, counted


@click.command(name="write")
@click.argument("target")
@click.argument("text")
@click.option(
    "--base", default=None, metavar="HASH", help="The page's hash as you read it; required once the page exists."
)
@click.option("--as", "declared", default=None, help="Who is writing. An agent names itself, including Agent or AI.")
@click.option("--session", "which", default=None, envvar="LOOM_SESSION", help="Log this call to the session.")
@click.option("--dry-run", is_flag=True, help="Check everything and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def write(
    target: str,
    text: str,
    base: str | None,
    declared: str | None,
    which: str | None,
    dry_run: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Write a page: TARGET `state`, the quilt's research state, or a WORK, that work's overview; `-` reads TEXT from stdin.

    A page is a reading the person edits directly and an agent writes here, never by hand; it says who wrote it, and it is never a source. Once the page exists, --base must be the hash it had when you read it -- `loom ai orient` prints the research state's, `loom library read WORK` an overview's -- so an edit you have not seen is never overwritten: a stale base is refused, with that edit shown. A link that names nothing the viewer shows is refused, as in a message. Every write is recorded in the history, with who made it.
    """
    from loom.links import refuse_bad_links
    from loom.pages import STATE, overview_page, read, state_page, text_hash
    from loom.pages import write as write_page

    (given,) = from_stdin({"TEXT": text})
    body = given or ""
    if not body.strip():
        raise EnvError("nothing to write: a page needs words")
    if not body.endswith("\n"):
        body += "\n"
    result = open_scan(quilt_path)
    root = result.quilt.root
    if target == STATE:
        page = state_page(result.quilt.config)
    else:
        from loom.cli.library._works import one_work

        page = overview_page(root, result.bib, one_work(result, target))
    current = read(root, page)
    if current is None and base is not None:
        raise EnvError(f"{page.name} does not exist yet; write it without --base")
    if current is not None and base is None:
        where = "loom ai orient" if page.kind == STATE else f"loom library read {page.work}"
        raise EnvError(
            f"{page.name} exists; read it first (`{where}` prints it with its hash) and pass that hash as --base"
        )
    if current is not None and base != text_hash(current):
        from loom.records.snapshots import read_raw
        from loom.reshape.ids import unified_diff

        seen = read_raw(root, base or "", result.quilt.history_dir)
        changed = unified_diff(seen, current, page.path) if seen is not None else ""
        raise ContentError(
            f"{page.name} has changed since you read it; it is now {text_hash(current)}. Read it again, and write over what is there now"
            + (":" if changed else "."),
            verbatim=f"\n{changed}" if changed else "",
        )
    refuse_bad_links(result, root, body)
    name, _kind = writer(root, declared)
    found = find_session(root, which) if which else None
    from loom.pages import linked

    links = linked(result, root, body)
    new = text_hash(body)
    data = {"page": page.kind, "path": page.path, "hash": new, "work": page.work or None, "links": len(links)}
    linking = f", linking {counted(len(links), 'thing')}" if links else ""
    if dry_run:
        Report(f"would write {page.name}{linking}", dry_run=True, data=data).emit(as_json)
        return
    if current == body:
        Report(f"{page.name} already reads so; nothing written", data=data).emit(as_json)
        return
    write_page(result, page, body, actor=name, session=found.id if found else None)
    log_run(found.id if found else None, f"loom write {target}", root)
    Report(f"wrote {page.name}{linking}", data=data).emit(as_json)
