"""Diagnostics as report groups (plan 0.18.3): one group per code with its count, the author's before the cited works', which are summarised under a heading of their own, and a single line for the works nothing cites.

Every command that reports diagnostics (`lint`, `build`, `check`, `library update`, `history verify`) builds its groups here, so a diagnostic reads the same wherever it is printed: its location, its message, the keys it names, and the commands that would resolve it as `fix:` lines.
"""

from __future__ import annotations

import re

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


def item(d: Diagnostic, said: str | None = None) -> Item:
    """One diagnostic as an item: its location first, then its message (or `said`, the part of it its heading does not already say), the keys it names last unless the text names them, its fixes beneath; the JSON carries the diagnostic whole."""
    where = ", ".join(f"{loc.file}:{loc.line}" for loc in d.locations)
    message = d.message if said is None else said
    text = f"{where}  {message}" if where else message
    named = set(re.findall(r"[^\s,;:()]+", message))
    return Item(
        text,
        key=" ".join(k for k in d.keys if k not in named) or None,
        fixes=[f.command for f in d.fixes],
        data={"diagnostic": d.to_dict()},
    )


#: A sentence its diagnostics share is said once in their heading when it has at least `SHARED` words and each says no more than `VARIES` of its own: one sentence about different things, not different sentences that begin alike.
SHARED, VARIES = 4, 4


def _shared(messages: list[str]) -> tuple[int, int]:
    """How many leading and trailing words every message shares, word-aligned and never overlapping; (0, 0) when the messages are not one sentence (`SHARED`, `VARIES`)."""
    words = [m.split() for m in messages]
    shortest = min(len(w) for w in words)
    head = 0
    while head < shortest and len({w[head] for w in words}) == 1:
        head += 1
    tail = 0
    while tail < shortest - head and len({w[-1 - tail] for w in words}) == 1:
        tail += 1
    own = [len(w) - head - tail for w in words]
    return (head, tail) if head + tail >= SHARED and all(0 < n <= VARIES for n in own) else (0, 0)


def _code_group(severity: str, code: str, ds: list[Diagnostic]) -> Group:
    """One code's diagnostics: when they all say one sentence about different things, the sentence is the heading's, once, and each line says only what varies (T2)."""
    head, tail = _shared([d.message for d in ds]) if len(ds) > 1 else (0, 0)
    if not head and not tail:
        return Group(f"{severity} {code}", [item(d) for d in ds], problem=severity == "error", limit=20)
    first = ds[0].message.split()
    gist = " ".join([*first[:head], "…", *(first[len(first) - tail :] if tail else [])])
    # what varies, without the comma that joined it to the shared words
    items = [item(d, " ".join(d.message.split()[head : len(d.message.split()) - tail]).rstrip(",;:")) for d in ds]
    return Group(f"{severity} {code}: {gist}", items, problem=severity == "error", limit=20)


def groups(diags: list[Diagnostic], result: ScanResult | None, cited_next: str = "loom lint --json") -> list[Group]:
    """The author's diagnostics as one group per code, most severe first; a cited work's summarised in one group, a line per code with its count; a work's nothing cites in one line.

    A cited paper's digest can carry hundreds of diagnostics the author did not write and need not read one by one, which drowned the author's own (CLI study C3); they are counted, and `cited_next` names the command that lists every one. The uncited works' line carries every one of its diagnostics in the JSON.
    """
    owners = Owners(result)
    split = owners.split(_once(diags))
    own, cited, uncited = split[AUTHOR], split[CITED], split[UNCITED]
    out: list[Group] = []
    by_code: dict[tuple[int, str, str], list[Diagnostic]] = {}
    for d in own:
        by_code.setdefault((SEVERITY.get(d.severity, 3), d.code, d.severity), []).append(d)
    for (_, code, severity), ds in sorted(by_code.items()):
        ds.sort(key=lambda d: (d.locations[0].file, d.locations[0].line) if d.locations else ("", 0))
        out.append(_code_group(severity, code, ds))
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
        works = set().union(*(owners.works(d) for d in uncited))
        out.append(
            Group(
                f"{counted(len(uncited), 'diagnostic')} in {counted(len(works), 'work')} nothing cites; loom library check lists them",
                [item(d) for d in uncited],
                limit=0,
                counted=False,
            )
        )
    return out


def _once(diags: list[Diagnostic]) -> list[Diagnostic]:
    """`diags` with each one said once: two passes can report the same diagnostic at the same place."""
    seen: set[tuple[str, str, str, tuple[tuple[str, int], ...], tuple[str, ...]]] = set()
    out = []
    for d in diags:
        mark = (d.severity, d.code, d.message, tuple((loc.file, loc.line) for loc in d.locations), tuple(d.keys))
        if mark not in seen:
            seen.add(mark)
            out.append(d)
    return out


def tally(diags: list[Diagnostic], result: ScanResult | None) -> str:
    """`2 errors, 1 warning in your documents; 88 errors in cited works`, or `no problems`: the count a verdict carries; a work's nothing cites counts toward neither."""
    split = Owners(result).split(_once(diags))
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
