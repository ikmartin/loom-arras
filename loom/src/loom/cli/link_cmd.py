"""`loom link THING` (plan 0.14 phase 3): print a link the viewer can follow, so an agent never composes one by hand."""

from __future__ import annotations

import click

from loom.cli._common import ContentError, EnvError
from loom.cli._quilt import open_scan, quilt_option


@click.command(name="link")
@click.argument("thing")
@click.option("--at", "at", default=None, help="A key inside the document or node: link to that place in it.")
@click.option("--page", type=int, default=None, help="A page of a cited work, from 1.")
@click.option("--quote", default=None, help="Text on that page to find.")
@quilt_option
def link_command(thing: str, at: str | None, page: int | None, quote: str | None, quilt_path: str | None) -> None:
    """Print a markdown link to THING that the viewer can follow.

    THING is a node or any key in it, a document's path, an annotation id, a session id, or a cited work's citekey or identifier. The link's text is empty: the viewer names the thing itself, as `Theorem 3.1`, and keeps the name right when the document is renumbered; write your own words between the brackets to show those instead. A thing the viewer does not show is refused, with why.
    """
    from loom.cli.review import _work_target
    from loom.links import LinkError, cited_link, quilt_link, resolve

    result = open_scan(quilt_path)
    root = result.quilt.root
    work = _work_target(result, thing)
    if work is not None or page is not None or quote is not None:
        if work is None:
            raise EnvError(f"--page and --quote are for a cited work, and {thing} names none: give its citekey")
        if at is not None:
            raise EnvError("--at is for a place in a document or a node; a work takes --page and --quote")
        _citekey, wid = work
        link = cited_link(wid.scheme, wid.value, page, quote)
    else:
        link = quilt_link(thing, at or "")
    href = link[len("[](") : -1]
    try:
        target = resolve(result, root, href)
    except LinkError as exc:
        raise ContentError(str(exc)) from None
    if target.kind in ("node", "document") and target.key != thing:
        link = quilt_link(target.key, at or "")
    click.echo(link)
