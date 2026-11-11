"""`loom library verify | discard | ignore` (plan 0.18.5): the author's decisions about what the library holds.

`verify` and `discard` take result ids and citation suggestions' annotation ids alike, the id's shape saying which. All three are the author's and refuse an agent.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import click

from loom.cli._common import ContentError, EnvError, NotFoundError, refuse_under_agent
from loom.cli._quilt import open_scan, quilt_option
from loom.cli.library import _works
from loom.cli.report import Group, Item, Report, counted
from loom.scan.scan import ScanResult

_AS = "Who is deciding, when the user config and git do not say."
_DRY = "Check everything and say what would be recorded; write nothing."
_JSON = "Print the report as one JSON object."


def _who(root: Path, declared: str | None) -> str:
    """The author's name, `--as` first; no name to record is a usage problem, exit 2."""
    from loom.scan.quilt import NoAuthorError, resolve_author

    try:
        return resolve_author(declared, root)[0]
    except NoAuthorError as exc:
        raise EnvError(str(exc)) from exc


def _targets(result: ScanResult, ids: tuple[str, ...], decision: str) -> list[tuple[str, str, Any]]:
    """Each ID as (`result`, its id, the citekey), all resolved before anything is written; a result id that names nothing exits 2.

    An annotation id is refused: a work worth citing is a suggestion on the text, resolved or deleted where it stands, and nothing about it is the library's to decide.
    """
    out: list[tuple[str, str, Any]] = []
    for target in dict.fromkeys(ids):
        if _works.is_suggestion(target):
            raise EnvError(
                f"{target} is an annotation, not a result: a work worth citing is a suggestion on the text, resolved where it stands with `loom annotate --resolve {target}`"
            )
        ck, rid, _results = _works.find_result(result, target)
        out.append(("result", rid, ck))
    return out


def _show_both_texts(result: ScanResult, citekey: str, rid: str, statement: str | None) -> None:
    """The page (or source) and the rendering, on stderr, which is where the question about them goes (§5.3)."""
    from loom.refs.proposals import load_results, page_context

    r = load_results(result.quilt.root, citekey)[rid]
    context, found = page_context(result.quilt.root, r)
    if r.anchor.kind == "pdf":
        shown = [f"{rid}   p.{r.anchor.page} of {citekey}"]
        shown.append(
            f"\n--- the page {'(around the quoted span)' if found else '(quoted span not located; whole page)'} ---"
        )
    else:
        # a result quoted from, or extracted out of, the paper's own LaTeX has no page
        shown = [f"{rid}   from {r.anchor.path or citekey + ' (its source)'}", "\n--- the source ---"]
    shown += [context, "\n--- rendered as ---", (statement or r.statement).strip()]
    click.echo("\n".join(shown), err=True)


@click.command(name="verify")
@click.argument("ids", nargs=-1, required=True, metavar="ID...")
@click.option("--statement", default=None, help="Your own rendering, replacing the proposed one; one ID only.")
@click.option(
    "--local", default=None, help="The paper's own name for it, correcting the proposal's (cor-3.2.1); one ID only."
)
@click.option("--taxon", default=None, help="The environment, when --local does not imply it; one ID only.")
@click.option("--as", "as_name", default=None, metavar="NAME", help=_AS)
@click.option("--yes", is_flag=True, help="Skip the question; you have read both texts.")
@click.option("--dry-run", is_flag=True, help=_DRY)
@click.option("--json", "as_json", is_flag=True, help=_JSON)
@quilt_option
def verify(
    ids: tuple[str, ...],
    statement: str | None,
    local: str | None,
    taxon: str | None,
    as_name: str | None,
    yes: bool,
    dry_run: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Record that a result's transcription is faithful.

    A result id promotes a proposal into the digest, or re-verifies one already there: the claim is that this copy is faithful to the paper, never that its mathematics holds, which is `loom accept`. --statement edits the rendering, never the quotation, so the anchor stays re-checkable and both parties are recorded.
    """
    from loom.refs.proposals import PROPOSAL_ABBREV, verify_result

    refuse_under_agent(
        "loom library verify",
        "Verify in the digest view, where the page and the rendering are side by side, or in your own terminal. "
        "An agent proposes; it does not vouch for its own reading.",
        as_name,
    )
    if len(ids) > 1 and (statement or local or taxon):
        raise EnvError("--statement, --local and --taxon correct one result; give one ID with them")
    if taxon and taxon not in PROPOSAL_ABBREV:
        raise EnvError(f"--taxon {taxon} is not one of: {', '.join(sorted(PROPOSAL_ABBREV))}")
    result = open_scan(quilt_path)
    root = result.quilt.root
    targets = _targets(result, ids, "accept")
    who = _who(root, as_name)
    if dry_run:
        # the dry run is where both texts can be read without answering for them
        for kind, tid, what in targets:
            if kind == "result":
                _show_both_texts(result, what, tid, statement)
        items = [Item(f"{what}: its transcription", key=tid) for _kind, tid, what in targets]
        Report(
            f"would verify {_counted(targets)}; nothing written",
            dry_run=True,
            groups=[Group("would verify", items, limit=None)],
            data={"verified": [{"kind": k, "id": t} for k, t, _ in targets], "author": who},
        ).emit(as_json)
        return
    if any(k == "result" for k, _, _ in targets) and not yes and not sys.stdin.isatty():
        raise EnvError(
            "verifying needs you to have read both texts; --dry-run shows them, and --yes verifies once you have"
        )
    lines: list[str] = []
    done: list[dict[str, Any]] = []
    items = []
    declined: list[str] = []
    for kind, tid, what in targets:
        _show_both_texts(result, what, tid, statement)
        if not yes and not click.confirm(f"\nis the rendering of {tid} faithful to the page?", err=True):
            declined.append(tid)  # a "no" is an answer, not a failure: nothing is recorded for it
            continue
        try:
            said = verify_result(result, tid, statement, who, local=local, taxon=taxon)
        except LookupError as exc:
            raise ContentError(str(exc)) from exc
        done.append({"kind": kind, "id": tid, "work": what})
        items.append(Item(said[0]))
        lines += said[1:]
    if not items:
        Report(
            f"not verified: {', '.join(declined)}; nothing recorded",
            groups=[
                Group(
                    "to set a proposal aside, with the reason the next proposer is told",
                    [Item("", key=t, fixes=[f"loom library discard {t} --why '…'"]) for t in declined],
                    counted=False,
                )
            ],
            data={"verified": [], "declined": declined, "author": who},
        ).emit(as_json)
        return
    one = len(items) == 1 and not declined
    if one:
        verdict = items[0].text
    elif declined:
        verdict = f"verified {len(items)} of {len(targets)}; not {', '.join(declined)}, as you answered"
    else:
        verdict = f"verified {_counted(targets)}"
    Report(
        verdict,
        lines=lines if one else [],
        groups=[] if one else [Group("verified", items, limit=None)],
        data={"verified": done, "declined": declined, "author": who},
    ).emit(as_json)


@click.command(name="discard")
@click.argument("ids", nargs=-1, required=True, metavar="ID...")
@click.option("--why", required=True, help="Why it should not stand; whatever proposes it again is shown this.")
@click.option("--as", "as_name", default=None, metavar="NAME", help=_AS)
@click.option("--dry-run", is_flag=True, help=_DRY)
@click.option("--json", "as_json", is_flag=True, help=_JSON)
@quilt_option
def discard(
    ids: tuple[str, ...], why: str, as_name: str | None, dry_run: bool, as_json: bool, quilt_path: str | None
) -> None:
    """Discard a proposed result, with a reason.

    `loom library propose` refuses a discarded result and returns the reason, so the agent that proposed it learns why in the turn it fails. Nothing is deleted: the log keeps it and `loom library why` reports it.
    """
    from loom.refs.proposals import DISCARDED, discard_refusal, discard_result, discarded_locals, load_results, state_of

    refuse_under_agent("loom library discard", "Discard in the digest view or in your own terminal.", as_name)
    result = open_scan(quilt_path)
    root = result.quilt.root
    targets = _targets(result, ids, "reject")
    for kind, tid, ck in targets:
        refusal = discard_refusal(load_results(root, ck)[tid], ck) if kind == "result" else ""
        if refusal:
            raise ContentError(refusal)
    # one discarded already keeps the reason the next proposer is told; discarding it again would replace it (T7)
    already: dict[str, str] = {}
    for kind, tid, ck in targets:
        r = load_results(root, ck)[tid] if kind == "result" else None
        if r is not None and state_of(r) == DISCARDED:
            already[tid] = discarded_locals(root, ck).get(r.local, "no reason given")
    targets = [t for t in targets if t[1] not in already]
    if not targets:
        Report(
            "already discarded: " + "; ".join(f"{t}, {why}" for t, why in already.items()) + "; nothing written",
            dry_run=dry_run,
            data={"discarded": [], "already": already, "why": why},
        ).emit(as_json)
        return
    who = _who(root, as_name)
    items = [
        Item(
            (f"{what}: " if kind == "result" else "") + ("would discard" if dry_run else "discarded"),
            key=tid,
        )
        for kind, tid, what in targets
    ]
    if not dry_run:
        for _kind, tid, _what in targets:
            try:
                discard_result(result, tid, why, who)
            except LookupError as exc:
                raise ContentError(str(exc)) from exc
    one = len(targets) == 1
    verb = "would discard" if dry_run else "discarded"
    Report(
        f"{verb} {targets[0][1] if one else _counted(targets)}: {why}",
        dry_run=dry_run,
        lines=["the reason is returned to whatever proposes it again"] if not dry_run else [],
        groups=[] if one else [Group(verb, items, limit=None)],
        data={"discarded": [{"kind": k, "id": t} for k, t, _ in targets], "why": why, "author": who},
    ).emit(as_json)


@click.command(name="ignore")
@click.argument("work", metavar="WORK")
@click.option("--why", required=True, help="Why loom should stop asking for it; with --undo, why that was wrong.")
@click.option("--undo", is_flag=True, help="Withdraw what stands, so the work is asked for or offered again.")
@click.option("--as", "as_name", default=None, metavar="NAME", help=_AS)
@click.option("--dry-run", is_flag=True, help=_DRY)
@click.option("--json", "as_json", is_flag=True, help=_JSON)
@quilt_option
def ignore(
    work: str, why: str, undo: bool, as_name: str | None, dry_run: bool, as_json: bool, quilt_path: str | None
) -> None:
    """Stop loom asking for a work's document, or offering a stored document an entry.

    A work with no document is declared unreadable -- the Stacks Project is a living work with no fixed version -- so the lint stops asking for a PDF that does not exist. A work whose store holds a document is set aside: once your bibliography no longer names it, the store stops offering it an entry on every scan. WORK may also be a prefix of a stored document's hash, for one no entry names. Both are recorded in loom's own file, never in your .bib, and --undo withdraws whichever stands.
    """
    from loom.refs.unreadable import NotIgnorable
    from loom.refs.unreadable import ignore as declare_ignored

    refuse_under_agent(
        "loom library ignore",
        "Whether a work can be obtained, or a document is wanted, is the author's claim about the world, not "
        "something to infer from a failed fetch. Report what you could not find, and let the author decide.",
        as_name,
    )
    result = open_scan(quilt_path)
    root = result.quilt.root
    key = _ignore_key(result, work)
    who = _who(root, as_name)
    try:
        kind, said = declare_ignored(result, key, why, who, undo=undo, dry_run=dry_run)
    except NotIgnorable as exc:
        raise ContentError(exc.message) from None
    from loom.refs.build import cited_counts

    cited = cited_counts(result).get(key, 0) if not undo else 0
    Report(
        ("would record: " if dry_run else "") + said,
        dry_run=dry_run,
        # setting aside a work the paper cites is allowed, and worth knowing before it is done
        lines=[f"{key} is cited by {counted(cited, 'key')} of yours"] if cited else [],
        data={"key": key, "declaration": kind, "why": why, "undo": undo, "author": who, "cited": cited},
    ).emit(as_json)


def _ignore_key(result: ScanResult, work: str) -> str:
    """The key a declaration is filed under: a WORK through `_works.one_work`; failing that, `sha256:<hash>` for a prefix of a hash in the copy ledger, a stored document no entry names."""
    from loom.refs.scan import load_ledger

    try:
        ck = _works.one_work(result, work)
    except NotFoundError:
        want = work.removeprefix("sha256:").lower()
        if not re.fullmatch(r"[0-9a-f]{6,64}", want):
            raise NotFoundError(
                "work", f"{work!r} names no work: no citekey, result id, author, title or stored document's hash"
            ) from None
        hits = [sha for sha in load_ledger(result.quilt.root) if sha.startswith(want)]
        if len(hits) > 1:
            raise EnvError(f"{work} names {len(hits)} documents in the copy ledger; give more of the hash") from None
        if not hits:
            raise NotFoundError("work", f"{work} is neither a work nor a hash in the copy ledger") from None
        return f"sha256:{hits[0]}"
    return ck


def _short(text: str | None, width: int = 60) -> str:
    """A suggestion's work, cut at a word for a one-line item; the JSON keeps it whole."""
    text = " ".join((text or "").split())
    return text if len(text) <= width else text[:width].rsplit(" ", 1)[0] + "…"


def _counted(targets: list[tuple[str, str, Any]]) -> str:
    """`2 results and 1 citation suggestion`, from resolved targets."""
    results = sum(1 for k, _, _ in targets if k == "result")
    citations = len(targets) - results
    parts = [counted(results, "result")] if results else []
    parts += [counted(citations, "citation suggestion")] if citations else []
    return " and ".join(parts)


#: The commands this module adds to `loom library`.
COMMANDS: list[click.Command] = [verify, discard, ignore]
