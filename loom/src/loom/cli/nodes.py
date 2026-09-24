"""`loom new`, `loom search`, `loom delete` (book 12.3)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import click

from loom.cli._common import EXIT_CONTENT, EnvError, emit_json, note
from loom.cli._quilt import open_scan, quilt_option
from loom.cli.build_cmds import log_run
from loom.clock import today
from loom.scan.alloc import visible_locals
from loom.scan.labels import next_local
from loom.scan.quilt import NoAuthorError, resolve_author
from loom.scan.scan import ScanResult


def skeleton(result: ScanResult, node_id: str | None, env: str, title: str | None, author: str | None) -> str:
    taxon = result.taxa.get(env)
    lines = []
    if author:
        lines.append(f"% !LOOM author: {author}")
    lines.append(f"% !LOOM created: {today()}")
    lines.append("% !LOOM tags: ")
    lines.append("")
    opt = f"[{title}]" if title else ""
    label = f"\\label{{{node_id}}}" if node_id else ""
    lines.append(f"\\begin{{{env}}}{opt}{label}")
    lines.append("")
    lines.append(f"\\end{{{env}}}")
    if taxon is None or taxon.style == "plain":
        lines.append("\\begin{proof}")
        lines.append("\\uses{}")
        lines.append("")
        lines.append("\\end{proof}")
    return "\n".join(lines) + "\n"


def resolve_taxon(result: ScanResult, name: str) -> str:
    if name in result.taxa:
        return name
    for env, t in result.taxa.items():
        if t.name.lower() == name.lower():
            return env
    raise EnvError(f"unknown taxon {name!r}; the default master declares: {', '.join(sorted(result.taxa))}")


@click.command()
@click.argument("taxon")
@click.argument("title", required=False, default=None)
@click.option("--prefix", default=None, help="Allocate under this prefix instead of [quilt] prefix.")
@click.option(
    "--print", "print_only", is_flag=True, help="Print the skeleton without allocating an id or writing a file."
)
@click.option(
    "--session", "run_dir", default=None, metavar="SESSION", envvar="LOOM_SESSION", help="Log this call to the session."
)
@quilt_option
def new(
    taxon: str, title: str | None, prefix: str | None, print_only: bool, run_dir: str | None, quilt_path: str | None
) -> None:
    """Allocate an id and write nodes/<id>.tex with a skeleton for TAXON."""
    from loom.cli.build_cmds import log_run

    result = open_scan(quilt_path)
    log_run(run_dir, f"loom new {taxon}" + (f" {title!r}" if title else ""), result.quilt.root)
    env = resolve_taxon(result, taxon)
    try:
        author, _ = resolve_author(None, result.quilt.root)
    except NoAuthorError:
        author = None
    if print_only:
        click.echo(skeleton(result, None, env, title, author), nl=False)
        return
    pre = prefix or result.quilt.config.prefix
    node_id = f"{pre}-{next_local(visible_locals(result, pre))}"
    path = result.quilt.root / "nodes" / f"{node_id}.tex"
    if path.exists():
        raise EnvError(f"{path} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(skeleton(result, node_id, env, title, author), encoding="utf-8")
    click.echo(f"{node_id}  {path.relative_to(result.quilt.root)}")


def search_entries(result: ScanResult, query: str, kind: str | None) -> list[dict[str, object]]:
    q = query.lower()
    out: list[tuple[int, str, dict[str, object]]] = []
    for key, n in result.assembly.nodes.items():
        entry_kind = (
            "master"
            if n.kind == "master"
            else ("digest" if n.digest else ("node" if n.kind in ("environment", "section", "proof") else "file"))
        )
        if kind and entry_kind != kind:
            continue
        if n.kind == "file":
            continue
        tags = [t.strip() for t in n.directives.get("tags", "").split(",") if t.strip()]
        title = n.title or ""
        rank = None
        if q == key.lower() or any(q == a.lower() for a in n.aliases):
            rank = 0
        elif title.lower().startswith(q):
            rank = 1
        elif (
            q in title.lower()
            or q in key.lower()
            or any(q in a.lower() for a in n.aliases)
            or any(q == t.lower() for t in tags)
            or (n.taxon or "").lower() == q
            or (n.digest or "").lower() == q
        ):
            rank = 2
        if rank is None:
            continue
        src = result.files[n.file]
        out.append(
            (
                rank,
                key,
                {
                    "key": key,
                    "kind": entry_kind,
                    "taxon": n.taxon,
                    "title": title,
                    "aliases": list(n.aliases),
                    "tags": tags,
                    "file": n.file,
                    "line": src.line_of(n.start),
                    "number": None,
                    "url": f"/node/{key}" if entry_kind != "master" else f"/master/{Path(key).stem}",
                },
            )
        )
    out.sort(key=lambda x: (x[0], x[1]))
    return [e for _, _, e in out]


#: A result named as a reader sees it: `Theorem 3.4`, `Lemma 4.1`, `3.4`, or an equation's `(3)`.
NUMBERED = re.compile(r"^\s*(?:(?P<taxon>[^\W\d_][\w-]*)\.?\s+)?(?P<open>\()?(?P<number>\d+(?:\.\d+)*[a-z]?)\)?\s*$")


def document_named(result: ScanResult, name: str) -> str:
    """The drafting document `name` means: its path, or a stem only one document has."""
    if name in result.masters:
        return name
    stem = [m for m in result.masters if Path(m).stem == Path(name).stem]
    if len(stem) == 1:
        return stem[0]
    raise EnvError(f"{name} names no drafting document; they are: {', '.join(result.masters) or 'none'}")


def numbered_entries(result: ScanResult, query: str, only: str | None = None) -> list[dict[str, object]] | None:
    """Every key the drafting documents number as `query` (`Theorem 3.4`, `(3)`), or None when `query` is not a number.

    Numbers come from each document's last compile, as the viewer's do, so a document never compiled numbers nothing. A reader names a result by what the default document prints, so that document's match is flagged; the others are listed because another arrangement may print the same number for a different result.
    """
    from loom.tex.aux import read_numbers

    m = NUMBERED.match(query)
    if not m:
        return None
    taxon = (m.group("taxon") or "").lower()
    number = m.group("number")
    equation = bool(m.group("open")) or taxon in ("equation", "eq")
    asm = result.assembly
    out: list[dict[str, object]] = []
    for doc in [only] if only else result.masters:
        table = read_numbers(result.quilt.root, doc)
        default = doc == result.default_master
        if equation:
            for qkey, r in asm.regions.items():
                container = asm.nodes.get(r.container)
                if container and doc in container.reached_by and r.label in table and table[r.label].number == number:
                    out.append(
                        {"key": qkey, "taxon": "equation", "number": f"({number})", "document": doc, "default": default}
                    )
            continue
        for key, n in asm.nodes.items():
            if n.kind not in ("environment", "section") or doc not in n.reached_by:
                continue
            if taxon and (n.taxon or n.kind).lower() != taxon:
                continue
            lab = next((x for x in [n.id, *n.labels] if x and x in table), None)
            if lab is not None and table[lab].number == number:
                out.append(
                    {"key": key, "taxon": n.taxon or n.kind, "number": number, "document": doc, "default": default}
                )
    out.sort(key=lambda e: (not e["default"], str(e["document"]), str(e["key"])))
    return out


@click.command()
@click.argument("query")
@click.option("--kind", type=click.Choice(["node", "digest", "master", "thread"]), default=None)
@click.option(
    "--in", "within", default=None, metavar="DOC", help="Resolve a number like `Theorem 3.4` in this document only."
)
@click.option("--json", "as_json", is_flag=True)
@click.option(
    "--session", "run_dir", default=None, metavar="SESSION", envvar="LOOM_SESSION", help="Log this call to the session."
)
@quilt_option
def search(
    query: str, kind: str | None, within: str | None, as_json: bool, run_dir: str | None, quilt_path: str | None
) -> None:
    """Find ids by id, alias, title, taxon, tag, or citekey; exact matches first.

    A number as a reader sees it -- `Theorem 3.4`, `3.4`, `(3)` -- finds what each drafting document numbers so, the default document's first and marked; `--in DOC` asks one document only.
    """
    result = open_scan(quilt_path)
    log_run(run_dir, f"loom search {query}" + (f" --in {within}" if within else ""), result.quilt.root)
    only = document_named(result, within) if within else None
    found = numbered_entries(result, query, only)
    # a bare number that numbers nothing may still be words to look for, as `2026` in a title is
    bare = found == [] and not only and bool(re.fullmatch(r"\s*[\d.]+\s*", query))
    if found is not None and not bare:
        if as_json:
            emit_json(found)
            return
        for e in found:
            mark = "  (default document)" if e["default"] else ""
            click.echo(f"{e['key']}  {str(e['taxon']).capitalize()} {e['number']}  {e['document']}{mark}")
        if not found:
            where = only or "any drafting document"
            note(f"nothing is numbered {query.strip()} in {where}; a document numbers only what its last compile saw")
        return
    if only:
        raise EnvError("--in names a document to resolve a number in, such as `Theorem 3.4`")
    entries = search_entries(result, query, kind)
    if as_json:
        emit_json(entries)
        return
    for e in entries:
        title = f'  "{e["title"]}"' if e["title"] else ""
        click.echo(f"{e['key']}  {e['taxon'] or e['kind']}{title}  {e['file']}:{e['line']}")
    if not entries:
        note("no matches")


@click.command(name="delete")
@click.argument("args", nargs=-1)
@click.pass_context
def delete(ctx: click.Context, args: tuple[str, ...]) -> None:
    """Refuse: loom never deletes your notes."""
    click.echo(
        "loom will not delete your notes; do this yourself with rm. Run loom unravel <ID> to see the consequences first.",
        err=True,
    )
    ctx.exit(EXIT_CONTENT)


def _json_dump(obj: object) -> str:
    return json.dumps(obj, indent=2, sort_keys=True)
