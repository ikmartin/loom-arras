"""Diagnostics as report groups (plan 0.18.3): one group per code with its count, the author's before the cited works', which are summarised under a heading of their own, and a single line for the works nothing cites.

Every command that reports diagnostics (`lint`, `build`, `check`, `library update`, `history verify`) builds its groups here, so a diagnostic reads the same wherever it is printed: its location, its message, the keys it names, and the commands that would resolve it as `fix:` lines.
"""

from __future__ import annotations

from loom.cli.report import Group, Item, counted
from loom.scan.model import Diagnostic
from loom.scan.scan import ScanResult

SEVERITY = {"error": 0, "warning": 1, "info": 2}


#: Whose a diagnostic is: the author's, a cited work's, or a work's nothing cites.
AUTHOR, CITED, UNCITED = "author", "cited", "uncited"


def cited_works(result: ScanResult) -> set[str]:
    """The citekeys the author's text cites (`refs.build.cited_counts`), with each version of one, since a version is cited when its primary is."""
    from loom.refs.build import cited_counts
    from loom.refs.scan import versions_of

    cited = set(cited_counts(result))
    return cited | {v for top, vs in versions_of(result.bib).items() if top in cited for v in vs}


class Owners:
    """Whose each diagnostic of one scan is, by what the author's text cites and reaches.

    A digest's diagnostic is the author's when it is on a result an edge from the author's text reaches (by key, or by a location inside the result's own text), a cited work's when its work is cited, and otherwise a work's nothing cites. A diagnostic naming only bibliography entries is the author's unless none of them is cited. Without a scan, every diagnostic is the author's.
    """

    def __init__(self, result: ScanResult | None) -> None:
        self.result = result
        self.cited: set[str] = set()
        self.reached: set[str] = set()
        self.spans: dict[str, list[tuple[int, int]]] = {}
        if result is None:
            return
        self.cited = cited_works(result)
        asm = result.assembly
        for e in result.edges.edges:
            src, to = asm.nodes.get(e.src), asm.nodes.get(e.to)
            if src is not None and to is not None and src.file not in asm.digest_files and to.file in asm.digest_files:
                self.reached.add(e.to)
        for k in self.reached:
            n = asm.nodes[k]
            f = result.files[n.file]
            self.spans.setdefault(n.file, []).extend(
                (f.line_of(a), f.line_of(max(a, b - 1))) for a, b in (n.own or [(n.start, n.end)]) if b > a
            )

    def works(self, d: Diagnostic) -> set[str]:
        """The works whose digests `d` is about; empty when it is the author's."""
        if self.result is None:
            return set()
        digests = self.result.assembly.digest_files
        nodes = self.result.nodes
        if any(k in self.reached for k in d.keys):
            return set()
        if d.locations:
            if not all(loc.file in digests for loc in d.locations):
                return set()
            if any(a <= loc.line <= b for loc in d.locations for a, b in self.spans.get(loc.file, ())):
                return set()
            return {digests[loc.file] for loc in d.locations}
        if d.keys and all(k in nodes and nodes[k].digest for k in d.keys):
            return {nodes[k].digest for k in d.keys}
        # a bibliography entry's own diagnostic is the author's while it is cited, and the work's while nothing cites it
        if d.keys and all(k in self.result.bib and k not in nodes for k in d.keys) and not set(d.keys) & self.cited:
            return set(d.keys)
        return set()

    def of(self, d: Diagnostic) -> str:
        """`AUTHOR`, `CITED` or `UNCITED`."""
        works = self.works(d)
        if not works:
            return AUTHOR
        return CITED if works & self.cited else UNCITED

    def split(self, diags: list[Diagnostic]) -> dict[str, list[Diagnostic]]:
        """`diags` by owner, in their order; every owner present."""
        out: dict[str, list[Diagnostic]] = {AUTHOR: [], CITED: [], UNCITED: []}
        for d in diags:
            out[self.of(d)].append(d)
        return out


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
    """The author's diagnostics as one group per code, most severe first; a cited work's summarised in one group, a line per code with its count; a work's nothing cites in one line.

    A cited paper's digest can carry hundreds of diagnostics the author did not write and need not read one by one, which drowned the author's own (CLI study C3); they are counted, and `cited_next` names the command that lists every one. The uncited works' line carries every one of its diagnostics in the JSON.
    """
    split = Owners(result).split(diags)
    own, cited, uncited = split[AUTHOR], split[CITED], split[UNCITED]
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
    if uncited:
        out.append(
            Group(
                f"{len(uncited)} in works nothing cites; loom library check lists them",
                [item(d) for d in uncited],
                limit=0,
                counted=False,
            )
        )
    return out


def tally(diags: list[Diagnostic], result: ScanResult | None) -> str:
    """`2 errors, 1 warning in your documents; 88 errors in cited works`, or `no problems`: the count a verdict carries; a work's nothing cites counts toward neither."""
    split = Owners(result).split(diags)
    own, cited = split[AUTHOR], split[CITED]

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


def has_errors(diags: list[Diagnostic], result: ScanResult | None) -> bool:
    """Whether any diagnostic is an error, the author's or a cited work's; a work nothing cites never counts."""
    owners = Owners(result)
    return any(d.severity == "error" and owners.of(d) in (AUTHOR, CITED) for d in diags)
