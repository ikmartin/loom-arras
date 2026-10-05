"""`loom new`, `loom search` (book 12.3)."""

from __future__ import annotations

import re
import shlex
from pathlib import Path

import click

from loom.cli._common import EnvError, NotFoundError, find_session, whoever, writer
from loom.cli._quilt import open_scan, quilt_option
from loom.cli.build_cmds import log_run
from loom.cli.graph import keyed, natural
from loom.cli.report import Group, Report, counted
from loom.clock import today
from loom.scan.alloc import visible_locals
from loom.scan.labels import PREFIX, next_local
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
    """The environment `name` means, by environment or by printed name; refused with what each document declares."""
    if name in result.taxa:
        return name
    for env, t in result.taxa.items():
        if t.name.lower() == name.lower():
            return env
    raise NotFoundError("taxon", f"unknown taxon {name!r}; " + _declared(result))


def _declared(result: ScanResult) -> str:
    """Which document declares which environments: the default master's in full, then each other document's that it lacks."""
    first = result.default_master
    seen = set(result.closures[first].taxa) if first in result.closures else set()
    parts = [f"{first} declares {', '.join(sorted(seen)) or 'none'}"] if first in result.closures else []
    for m in sorted(result.closures):
        extra = sorted(set(result.closures[m].taxa) - seen)
        if m != first and extra:
            parts.append(f"{m} also {', '.join(extra)}")
            seen |= set(extra)
    return "; ".join(parts) or f"no document declares any: {', '.join(sorted(result.taxa)) or 'none'}"


@click.command()
@click.argument("taxon")
@click.argument("title", required=False, default=None)
@click.option("--prefix", default=None, help="Allocate under this prefix instead of [quilt] prefix.")
@click.option(
    "--print", "print_only", is_flag=True, help="Print the skeleton without allocating an id or writing a file."
)
@click.option("--dry-run", is_flag=True, help="Say which id and file would be written, and write nothing.")
@click.option(
    "--session", "run_dir", default=None, metavar="SESSION", envvar="LOOM_SESSION", help="Log this call to the session."
)
@click.option(
    "--as",
    "declared",
    default=None,
    metavar="NAME",
    help="Who writes the node; an agent names itself, including Agent or AI.",
)
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def new(
    taxon: str,
    title: str | None,
    prefix: str | None,
    print_only: bool,
    dry_run: bool,
    run_dir: str | None,
    declared: str | None,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Allocate an id and write nodes/<id>.tex with a skeleton for TAXON; with --print, print the skeleton instead.

    The node's `% !LOOM author:` line is whoever writes it: `--as`, else the configured author; an agent that has not named itself is refused.
    """
    result = open_scan(quilt_path)
    env = resolve_taxon(result, taxon)
    if prefix is not None and not PREFIX.match(prefix):
        raise EnvError(f"--prefix {prefix}: a prefix is letters and digits, without a hyphen")
    if prefix is not None and prefix in result.assembly.citeslugs:
        raise EnvError(f"--prefix {prefix} is a cited work's slug, whose ids are that paper's own")
    root = result.quilt.root
    author = (whoever(root, declared) if print_only else writer(root, declared)[0]) or None
    if dry_run and run_dir:
        find_session(result.quilt.root, run_dir)
    elif not dry_run:
        log_run(run_dir, f"loom new {taxon}" + (f" {title!r}" if title else ""), result.quilt.root)
    if print_only:
        click.echo(skeleton(result, None, env, title, author), nl=False)
        return
    pre = prefix or result.quilt.config.prefix
    node_id = f"{pre}-{next_local(visible_locals(result, pre))}"
    path = result.quilt.root / "nodes" / f"{node_id}.tex"
    if path.exists():
        raise EnvError(f"{path} already exists")
    rel = path.relative_to(result.quilt.root).as_posix()
    name = result.taxa[env].name if env in result.taxa else env
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(skeleton(result, node_id, env, title, author), encoding="utf-8")
    home = result.default_master or result.quilt.config.main
    line = f"\\input{{nodes/{node_id}}}"
    Report(
        f"{node_id}  {'would write' if dry_run else 'wrote'} {rel}, a new {name.lower()}; no document reaches it yet",
        dry_run=dry_run,
        lines=[f"to place it, add {line} to a document, e.g. {home}"],
        data={"id": node_id, "file": rel, "taxon": env, "author": author, "input": line},
    ).emit(as_json)


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
                    "name": cited_name(result, n.digest, title) if n.digest else title,
                    "aliases": list(n.aliases),
                    "tags": tags,
                    "file": n.file,
                    "line": src.line_of(n.start),
                    "number": None,
                    "url": f"/node/{key}" if entry_kind != "master" else f"/master/{Path(key).stem}",
                },
            )
        )
    out.sort(key=lambda x: (x[0], natural(x[1])))
    return [e for _, _, e in out]


def cited_name(result: ScanResult, citekey: str, title: str) -> str:
    """A cited work's result as a reader names it: its locator without the page, then the work's authors (`Corollary 2.16 of Edidin et al.`); the title as written when it carries no locator."""
    from loom.refs.resolve import query_for
    from loom.scan.postnote import locator_of

    loc = locator_of(title)
    if not loc:
        return title
    loc = re.sub(r",\s*p+\.\s*~?\s*[\d-]+$", "", loc).replace("~", " ").strip()
    entry = result.bib.get(citekey)
    names = list(query_for(entry).surnames) if entry is not None else []
    more = entry is not None and bool(re.search(r"\band\s+others\b", entry.fields.get("author", "")))
    if not names:
        return f"{loc} of {citekey}"
    return f"{loc} of " + (f"{names[0]} et al." if len(names) > 2 or more else " and ".join(names))


#: A result named as a reader sees it: `Theorem 3.4`, `Lemma 4.1`, `3.4`, or an equation's `(3)`.
NUMBERED = re.compile(r"^\s*(?:(?P<taxon>[^\W\d_][\w-]*)\.?\s+)?(?P<open>\()?(?P<number>\d+(?:\.\d+)*[a-z]?)\)?\s*$")


def document_named(result: ScanResult, name: str) -> str:
    """The drafting document `name` means: its path, or a stem only one document has."""
    if name in result.masters:
        return name
    stem = [m for m in result.masters if Path(m).stem == Path(name).stem]
    if len(stem) == 1:
        return stem[0]
    raise NotFoundError("document", f"{name} names no document; they are: {', '.join(result.masters) or 'none'}")


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
@click.option(
    "--kind", type=click.Choice(["node", "digest", "master", "thread"]), default=None, help="Only matches of this kind."
)
@click.option(
    "--in", "within", default=None, metavar="DOC", help="Resolve a number like `Theorem 3.4` in this document only."
)
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
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
    only = document_named(result, within) if within else None
    log_run(run_dir, f"loom search {query}" + (f" --in {within}" if within else ""), result.quilt.root)
    found = numbered_entries(result, query, only)
    asked = query.strip()
    # a bare number that numbers nothing may still be words to look for, as `2026` in a title is
    bare = found == [] and not only and bool(re.fullmatch(r"\s*[\d.]+\s*", query))
    if found is not None and not bare:
        if not found:
            where = only or "any drafting document"
            Report(
                f"nothing is numbered {asked} in {where}",
                lines=["a document numbers only what its last compile saw: loom compile DOCUMENT refreshes it"],
                data={"matches": []},
            ).emit(as_json)
            return
        rows = [
            (
                (
                    f"{str(e['taxon']).capitalize()} {e['number']}",
                    str(e["document"]),
                    "default" if e["default"] else "",
                ),
                str(e["key"]),
            )
            for e in found
        ]
        Report(
            f"{counted(len(found), 'result')} numbered {asked}",
            groups=[Group("", keyed(rows), limit=None)],
            data={"matches": found},
        ).emit(as_json)
        return
    if only:
        raise EnvError("--in names a document to resolve a number in, such as `Theorem 3.4`")
    entries = search_entries(result, query, kind)
    more = f"loom search {shlex.quote(query)} --json"
    groups = []
    for heading, part in (
        ("in your documents", [e for e in entries if e["kind"] != "digest"]),
        ("in cited works", [e for e in entries if e["kind"] == "digest"]),
    ):
        rows = [
            (
                (str(e["taxon"] or e["kind"]), f'"{e["name"]}"' if e["name"] else "", f"{e['file']}:{e['line']}"),
                str(e["key"]),
            )
            for e in part
        ]
        if rows:
            groups.append(Group(heading, keyed(rows), limit=20, next=more if len(rows) > 20 else None))
    Report(
        f"{counted(len(entries), 'match', 'matches')} for {asked!r}" if entries else f"nothing matches {asked!r}",
        groups=groups,
        data={"matches": entries},
    ).emit(as_json)
