"""`loom new`, `loom search`, `loom delete` (book 12.3)."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import click

from loom.cli._common import EXIT_CONTENT, EnvError, emit_json, note
from loom.cli._quilt import open_scan, quilt_option
from loom.clock import today
from loom.scan.labels import LOOMLOCAL, next_local
from loom.scan.quilt import NoAuthorError, resolve_author
from loom.scan.scan import ScanResult


def visible_locals(result: ScanResult, prefix: str) -> set[str]:
    """Every local part under `prefix` that anything can point at: ids in source, ledger keys, annotation targets, references anywhere (dangling included), and git history."""
    pat = re.compile(r"\b" + re.escape(prefix) + r"-([0-9A-Z]{4})\b")
    found: set[str] = set()
    for src in result.files.values():
        found.update(pat.findall(src.text))
    root = result.quilt.root
    ledger = root / ".loom" / "state.toml"
    if ledger.is_file():
        found.update(pat.findall(ledger.read_text(encoding="utf-8", errors="replace")))
    for rec in list(root.glob("comments/*/*.json")) + list(root.glob("ai/runs/*/annotations.json")):
        found.update(pat.findall(rec.read_text(encoding="utf-8", errors="replace")))
    try:
        revs = subprocess.run(
            ["git", "-C", str(root), "rev-list", "--all", "--max-count=500"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if revs.returncode == 0 and revs.stdout.strip():
            out = subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "grep",
                    "-h",
                    "-o",
                    "-E",
                    rf"\b{re.escape(prefix)}-[0-9A-Z]{{4}}\b",
                    *revs.stdout.split(),
                ],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            found.update(pat.findall(out.stdout))
    except (OSError, subprocess.SubprocessError):
        pass
    return {x for x in found if LOOMLOCAL.match(x)}


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
@quilt_option
def new(taxon: str, title: str | None, prefix: str | None, print_only: bool, quilt_path: str | None) -> None:
    """Allocate an id and write nodes/<id>.tex with a skeleton for TAXON."""
    result = open_scan(quilt_path)
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


@click.command()
@click.argument("query")
@click.option("--kind", type=click.Choice(["node", "digest", "master", "thread"]), default=None)
@click.option("--json", "as_json", is_flag=True)
@quilt_option
def search(query: str, kind: str | None, as_json: bool, quilt_path: str | None) -> None:
    """Find ids by id, alias, title, taxon, tag, or citekey; exact matches first."""
    result = open_scan(quilt_path)
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
