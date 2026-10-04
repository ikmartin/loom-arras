"""Diagnostics as report groups (plan 0.18.3): one group per code with its count, the author's before the cited works', which are summarised under a heading of their own.

Every command that reports diagnostics (`lint`, `build`, `check`, `library update`, `history verify`) builds its groups here, so a diagnostic reads the same wherever it is printed: its location, its message, the keys it names, and the commands that would resolve it as `fix:` lines.
"""

from __future__ import annotations

from loom.cli.report import Group, Item, counted
from loom.scan.model import Diagnostic
from loom.scan.scan import ScanResult

SEVERITY = {"error": 0, "warning": 1, "info": 2}


def in_cited_work(d: Diagnostic, result: ScanResult | None) -> bool:
    """Whether `d` is about a cited paper's digest rather than the author's own documents: every location in a digest file, or every key an external one."""
    if result is None:
        return False
    digests = result.assembly.digest_files
    if d.locations:
        return all(loc.file in digests for loc in d.locations)
    nodes = result.nodes
    return bool(d.keys) and all(k in nodes and nodes[k].external for k in d.keys)


def item(d: Diagnostic) -> Item:
    """One diagnostic as an item: its location first, then its message, the keys it names last, its fixes beneath."""
    where = ", ".join(f"{loc.file}:{loc.line}" for loc in d.locations)
    text = f"{where}  {d.message}" if where else d.message
    return Item(
        text,
        key=" ".join(d.keys) or None,
        fixes=[f.command for f in d.fixes],
        data={"diagnostic": d.to_dict()},
    )


def groups(diags: list[Diagnostic], result: ScanResult | None, cited_next: str = "loom lint --json") -> list[Group]:
    """The author's diagnostics as one group per code, most severe first; a cited work's summarised in one group, a line per code with its count.

    A cited paper's digest can carry hundreds of diagnostics the author did not write and need not read one by one, which drowned the author's own (CLI study C3); they are counted, and `cited_next` names the command that lists every one.
    """
    own = [d for d in diags if not in_cited_work(d, result)]
    cited = [d for d in diags if in_cited_work(d, result)]
    out: list[Group] = []
    by_code: dict[tuple[int, str, str], list[Diagnostic]] = {}
    for d in own:
        by_code.setdefault((SEVERITY.get(d.severity, 3), d.code, d.severity), []).append(d)
    for (_, code, severity), ds in sorted(by_code.items()):
        ds.sort(key=lambda d: (d.locations[0].file, d.locations[0].line) if d.locations else ("", 0))
        out.append(Group(f"{severity} {code}", [item(d) for d in ds], problem=severity == "error", limit=20))
    if cited:
        tally: dict[tuple[int, str, str], int] = {}
        for d in cited:
            k = (SEVERITY.get(d.severity, 3), d.code, d.severity)
            tally[k] = tally.get(k, 0) + 1
        out.append(
            Group(
                "in cited works",
                [
                    Item(f"{counted(n, severity)}  {code}", data={"code": code, "severity": severity, "count": n})
                    for (_, code, severity), n in sorted(tally.items())
                ],
                count=len(cited),
                limit=None,
                next=cited_next,
            )
        )
    return out


def tally(diags: list[Diagnostic], result: ScanResult | None) -> str:
    """`2 errors, 1 warning in your documents; 88 errors in cited works`, or `no problems`: the count a verdict carries."""
    own = [d for d in diags if not in_cited_work(d, result)]
    cited = [d for d in diags if in_cited_work(d, result)]

    def counts(ds: list[Diagnostic]) -> str:
        parts = [
            counted(sum(1 for d in ds if d.severity == s), s)
            for s in ("error", "warning", "info")
            if any(d.severity == s for d in ds)
        ]
        return ", ".join(parts)

    parts = []
    if own:
        parts.append(f"{counts(own)} in your documents")
    if cited:
        parts.append(f"{counts(cited)} in cited works")
    return "; ".join(parts) or "no problems"


def has_errors(diags: list[Diagnostic], result: ScanResult | None, *, cited_count: bool = True) -> bool:
    """Whether any diagnostic is an error; `cited_count=False` counts only the author's own."""
    return any(d.severity == "error" and (cited_count or not in_cited_work(d, result)) for d in diags)
