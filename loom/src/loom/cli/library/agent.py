"""`loom library propose` and `locate` (plan 0.18.5): the agent's two tools, each checking a quotation against the page it claims to come from."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import click

from loom.cli._common import EXIT_CONTENT, ContentError, EnvError
from loom.cli._quilt import open_scan, quilt_option
from loom.cli.library._works import home, logged, one_work, present
from loom.cli.library.read import no_pages, page_range
from loom.cli.report import Group, Item, Report
from loom.clock import stamp

#: A statement that brings its own environment or label: loom writes those itself.
WRAPPER = re.compile(
    r"\\(begin|end)\s*\{(theorem|lemma|proposition|corollary|definition|remark|example|construction|conjecture|claim|notation)\*?\}|\\label\s*\{"
)


@click.command(name="propose")
@click.argument("work")
@click.option(
    "--local", required=True, help="The paper's own name for the result: thm-4.1, cor-2.3.1, eq-1, thm-star-2."
)
@click.option("--page", "page_spec", default=None, help="The page the statement is on, or 353-354 if it runs over.")
@click.option(
    "--source-file",
    default=None,
    metavar="FILE",
    help="Quote the work's LaTeX source instead of a page: a file under the directory `loom library read WORK --where src` prints.",
)
@click.option("--source-text", required=True, help="The paper's own words, verbatim; checked against the page or file.")
@click.option(
    "--statement", required=True, help="The same result as LaTeX, in the paper's words only; the author verifies it."
)
@click.option("--taxon", default=None, help="theorem, lemma, definition, equation, …; read off --local when omitted.")
@click.option("--number", default="", help="The paper's numbers when it states several results together: '3.2, 3.3'.")
@click.option("--level", type=click.Choice(["1", "3"]), default="3", show_default=True, help="1 is a main result.")
@click.option("--supersedes", default=None, metavar="ID", help="Re-propose something discarded, recording the chain.")
@click.option(
    "--session", "run_dir", default=None, envvar="LOOM_SESSION", metavar="SESSION", help="The session proposing this."
)
@click.option("--dry-run", is_flag=True, help="Check the quotation and say what would be proposed, storing nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the stored record as JSON.")
@quilt_option
def propose_command(
    work: str,
    local: str,
    page_spec: str | None,
    source_file: str | None,
    source_text: str,
    statement: str,
    taxon: str | None,
    number: str,
    level: str,
    supersedes: str | None,
    run_dir: str | None,
    dry_run: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """An agent's tool: propose one result of WORK, its quotation checked against the page or source file it claims to come from.

    The only write an agent makes to the library's results. SOURCE-TEXT must appear on PAGE — whitespace, hyphenation across lines and ligatures are normalised, nothing else is — and on failure nothing is stored and the page's text is printed so the quotation can be corrected in the same turn. For a work with a LaTeX source, quote the source with --source-file instead: the mathematics is there, and in a PDF's text layer it is often control bytes. A proposal lands in `digests/CITEKEY.proposed.tex`, which no bundle inputs, and waits there for the author to verify or discard it.
    """
    from loom.cli._common import agent_marker
    from loom.refs.pages import read_map, read_pages
    from loom.refs.proposals import (
        DISCARDED,
        PROPOSED,
        Anchor,
        Result,
        append_event,
        check_local,
        discarded_locals,
        load_results,
        numbers_of,
        quilt_env,
        save_results,
        state_of,
        write_proposed_tex,
    )
    from loom.refs.search import find_in_page, words_not_on_page

    if (page_spec is None) == (source_file is None):
        raise EnvError("give --page for a page of the PDF, or --source-file for the work's LaTeX source: one of them")
    try:
        taxon, local_number = check_local(local, taxon)
    except ValueError as exc:
        raise ContentError(str(exc)) from exc
    result = open_scan(quilt_path)
    root = result.quilt.root
    citekey = one_work(result, work)
    where_home = home(result, citekey)
    if run_dir:
        # "ai/runs/2026-...-fixed-stacks" and "2026-...-fixed-stacks" are one run; provenance showed both spellings
        run_dir = Path(run_dir).name

    # a discard the agent cannot see is a discard it will make again (§5.5)
    gone = discarded_locals(root, citekey)
    if local in gone and not supersedes:
        raise ContentError(
            f"{citekey} {local} was discarded: {gone[local]}\nIf this proposal answers that, pass --supersedes to record the chain."
        )

    if source_file is not None:
        placed = _source_anchor(root, where_home, citekey, source_file, source_text)
        if isinstance(placed, Report):
            placed.emit(as_json)
            return
        anchor, where = placed
        page_no = 0
    else:
        assert page_spec is not None
        m = read_map(where_home)
        if m is None:
            raise ContentError(f"{citekey} has no page text; {no_pages(where_home, citekey)}")
        page_no, last = page_range(page_spec)
        if last - page_no > 3:
            raise EnvError(f"{page_spec} spans {last - page_no + 1} pages; a statement is anchored to at most four")
        page_text = read_pages(where_home, page_no, last)
        if page_text is None:
            raise ContentError(f"{citekey} has {m.pages} pages; {page_spec} runs past the end")
        where = f"p.{page_no}" if last == page_no else f"pp.{page_no}-{last}"
        if not find_in_page(page_text, source_text):
            # the page itself, so the quotation can be corrected in the same turn
            Report(
                f"that text is not on {citekey} {where}, so nothing was stored; quote from the page below and propose again",
                ok=False,
                exit=EXIT_CONTENT,
                lines=["", *page_text.rstrip("\n").split("\n")],
                data={"stored": False, "citekey": citekey, "where": where, "page_text": page_text},
            ).emit(as_json)
            return
        anchor = Anchor(kind="pdf", sha256=m.sha256, page=page_no, last=last if last > page_no else 0)

    wrapper = WRAPPER.search(statement)
    if wrapper:
        # Thirteen of thirteen first attempts by two agents wrapped the statement in its own environment, and loom wrapped it again: a nested environment, the label doubled. A note does not stop it, because a result written as LaTeX looks like an environment. Refusing does.
        raise ContentError(
            f"--statement contains {wrapper.group(0)!r}. The statement is the body only: loom writes the "
            f"\\begin{{{taxon}}}, the locator and the \\label itself. Pass the text between them."
        )
    results = load_results(root, citekey)
    if level != "1" and not any(r.level == 1 and state_of(r) != DISCARDED for r in results.values()):
        raise ContentError(
            f"{citekey} has no level-1 result yet. Read the abstract and introduction and propose the main results "
            f"first (--level 1); everything deeper is cheaper once they are there."
        )

    prefix = result.assembly.prefix_of(citekey)
    rid = f"{prefix}-{local}" if not local.startswith(prefix) else local
    withdrawn = False
    if rid in results:
        prior = results[rid]
        mine = (
            bool(run_dir)
            and state_of(prior) == PROPOSED
            and any(o.get("act") == "proposed" and Path(str(o.get("by", ""))).name == run_dir for o in prior.origin)
        )
        if supersedes and supersedes == rid and mine:
            # A run correcting its own proposal before anyone has looked at it, which touches nothing the author has decided: the record is still `proposed`. Without it a mistake could only be re-proposed under a new id, and eleven results became twenty-two to review.
            results.pop(rid)
            withdrawn = True
        elif supersedes and supersedes == rid and state_of(prior) == DISCARDED:
            # The chain lives in the log, which `discarded_locals` replays and `loom library why` prints; an id is how a locator finds a result (contract §6.2), so it may not carry the history of how it was arrived at.
            results.pop(rid)
        else:
            raise ContentError(f"{rid} is already recorded ({state_of(prior)}); loom library why {rid}")
    number = number or local_number
    nums = numbers_of(number)
    if len(nums) > 1:
        # the id is the first number's; the others ride as aliases, so a citation to either finds it
        local = f"{local.split('-')[0]}-{nums[0]}"
        rid = f"{prefix}-{local}"
        if rid in results:
            raise ContentError(f"{rid} is already recorded ({state_of(results[rid])}); loom library why {rid}")
    r = Result(
        id=rid,
        local=local,
        taxon=taxon,
        number=number,
        statement=statement,
        source_text=source_text,
        anchor=anchor,
        env=quilt_env(result, taxon),
        level=int(level),
        cls="anchored",
        state=PROPOSED,
        origin=[{"act": "proposed", "by": run_dir or "", "when": stamp()}],
        supersedes=supersedes or "",
    )
    if not dry_run:
        if withdrawn:
            append_event(root, citekey, {"event": "withdrawn", "id": rid, "local": local, "run": run_dir or ""})
        results[rid] = r
        save_results(root, citekey, results)
        write_proposed_tex(root, citekey, prefix, results)
        append_event(
            root,
            citekey,
            {
                "event": "proposed",
                "id": rid,
                "local": local,
                "page": page_no,
                "run": run_dir or "",
                "supersedes": supersedes or "",
            },
        )
    notes = []
    added = words_not_on_page(statement, source_text)
    if added:
        # a gloss is the commonest correction an author makes, and a line in the orientation did not stop it
        notes.append(
            f"not in the quoted {'page' if page_no else 'source'} text: {', '.join(added)}. A statement is the "
            f"paper's words only; if these are yours, correct it now with --supersedes {rid}, and put the gloss in "
            "your notes file."
        )
    if dry_run:
        lines = [f"would be written to digests/{citekey}.proposed.tex"]
    elif agent_marker():
        # the author's verb is not the agent's next step, and "verified" is the author's word (plan 0.12 §5.6)
        lines = [f"in digests/{citekey}.proposed.tex, waiting for the author, who verifies or discards it"]
    else:
        lines = [
            f"in digests/{citekey}.proposed.tex, which nothing inputs until you verify it",
            f"next: loom library verify {rid}, or loom library discard {rid} --why '…'",
        ]
    Report(
        f"{'would propose' if dry_run else 'proposed'} {rid}, its source text checked against {where}"
        + ("; its statement has words the quotation lacks" if added else ""),
        ok=not added,
        dry_run=dry_run,
        lines=lines,
        notes=notes,
        data={"stored": not dry_run, "work": citekey, **r.to_json()},
    ).emit(as_json)


def _source_anchor(
    root: Path, home: Path, citekey: str, source_file: str, source_text: str
) -> tuple[Any, str] | Report:
    """A LaTeX anchor for a quotation of the work's source (contract §9.3) and its path, or the refusal that shows what is there.

    The refusal is a report rather than an error because it carries the file's nearby lines, so the quotation can be corrected in the same turn.
    """
    import hashlib

    from loom.anchors import Anchor
    from loom.refs.proposals import locate_quote

    src = home / "src"
    given = Path(source_file)
    f = (given if given.is_absolute() else (src / given if (src / given).is_file() else home / given)).resolve()
    if not f.is_file() or not f.is_relative_to(home.resolve()):
        tex = sorted(p.relative_to(src).as_posix() for p in src.rglob("*.tex")) if src.is_dir() else []
        raise ContentError(
            f"{source_file} is not a file of {citekey}'s source; "
            + (
                f"it has {', '.join(tex[:12])}"
                if tex
                else f"{citekey} has no source (loom library update {citekey} --online fetches one, or loom library add FILE --for {citekey})"
            )
        )
    data = f.read_bytes()
    # surrogateescape round-trips any byte, so the offsets below are the file's own even in a Latin-1 source
    text = data.decode("utf-8", "surrogateescape")
    rel = f.relative_to(root.resolve()).as_posix()
    span = locate_quote(text, source_text)
    if span is None:
        head = " ".join(source_text.split()[:3])
        near = [row for row in text.splitlines() if head and head in " ".join(row.split())][:5]
        return Report(
            f"that text is not in {rel}, so nothing was stored; quote the file exactly, only whitespace may differ",
            ok=False,
            exit=EXIT_CONTENT,
            groups=present(Group("lines that begin the same way", [Item(row) for row in near], limit=None)),
            data={"stored": False, "citekey": citekey, "where": rel, "near": near},
        )
    a, b = (len(text[:i].encode("utf-8", "surrogateescape")) for i in span)
    anchor = Anchor(kind="tex", sha256=hashlib.sha256(data).hexdigest(), path=rel, bytes=[a, b])
    return anchor, rel


@click.command(name="locate")
@click.argument("work")
@click.argument("text")
@click.option("--page", "page_no", type=click.IntRange(min=1), required=True, help="The page the text is on.")
@click.option("--json", "as_json", is_flag=True, help="Print the anchor as JSON.")
@quilt_option
@logged("locate")
def locate_command(work: str, text: str, page_no: int, as_json: bool, quilt_path: str | None) -> None:
    """An agent's tool: print the region of WORK's page PAGE that TEXT occupies, so an anchor need not compute geometry.

    Token geometry is thirty times the size of plain page text, so it is produced for the one page asked about and kept there; nothing writes it in bulk. Where `loom serve` is running, an `open:` line follows with a link into the viewer **at the place** -- `?page=4&span=812-871` -- so that following it lights the quotation rather than leaving it to be found by eye.
    """
    from loom.refs.anchoring import anchor_on_page
    from loom.refs.pages import read_map

    result = open_scan(quilt_path)
    citekey = one_work(result, work)
    where = home(result, citekey)
    if read_map(where) is None or not (where / "paper.pdf").is_file():
        raise ContentError(f"{citekey} has no mapped PDF; {no_pages(where, citekey)}")
    # The mapping the viewer previews with and `loom annotate` records, so the three cannot spell one place differently.
    placed = anchor_on_page(where, page_no, text)
    if not placed.found:
        Report(
            f"not found on {citekey} p.{page_no}",
            ok=False,
            exit=EXIT_CONTENT,
            data={"found": False, "citekey": citekey, "page": page_no},
        ).emit(as_json)
        return
    anchor = placed.anchor
    quads = anchor.quads or []
    if as_json:
        Report(f"found on {citekey} p.{page_no}", data=anchor.to_dict()).emit(True)
        return
    xs = [q[0] for q in quads] or [0.0]
    ys = [q[1] for q in quads] or [0.0]
    x1s = [q[2] for q in quads] or [0.0]
    y1s = [q[3] for q in quads] or [0.0]
    lines = f"{len(quads)} line{'s' if len(quads) != 1 else ''}"
    words = len(placed.selector.exact.split())
    click.echo(
        f"{citekey} p.{page_no}  {anchor.basis}  {min(xs):.1f} {min(ys):.1f} {max(x1s):.1f} {max(y1s):.1f}  ({words} words, {lines})"
    )
    # A quad is four numbers; what anyone wants next is to see the place on the page. The line is printed only when a server is actually listening, because a dead link is worse than none.
    from loom.render.serve import open_url

    # offsets where the committed page text holds the quotation, else the rectangle that was matched
    locator = (
        f"span={anchor.start}-{anchor.end}"
        if anchor.basis == "text"
        else "box=" + ",".join(f"{v:.1f}" for v in (quads[0] if quads else []))
    )
    link = open_url(result.quilt.root, f"library/{citekey}?page={page_no}&{locator}")
    if link:
        click.echo(f"open: {link}")


#: The commands this module adds to `loom library`.
COMMANDS: list[click.Command] = [propose_command, locate_command]
