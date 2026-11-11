"""Whose a diagnostic is to fix: the person's, an agent's copy's, or a cited work's, whose digest loom wrote.

One reading for every reader: the manifest stamps it on each diagnostic (`render.build`), `loom lint --json` carries it, and the report groups split by it, so the viewer and the command line never disagree about whose a problem is.
"""

from __future__ import annotations

from loom.scan.model import Diagnostic
from loom.scan.scan import ScanResult

#: Whose a diagnostic is in the report groups: the author's, a cited work's, or a work's nothing cites.
AUTHOR, CITED, UNCITED = "author", "cited", "uncited"
#: Whose a diagnostic is to fix, as the manifest says it: the person's, an agent's copy's, or a cited work's digest's.
PERSON, COPY, WORK = "person", "copy", "work"
#: A digest's diagnostics that digesting it again does not mend: about the work or its rendering, or faithful to the paper (a cycle among its proofs).
NOT_MENDED = frozenset(
    {
        "loom:snippet-failed",
        "loom:dependency-cycle",
        "loom:missing-package",
        "loom:unverified-locators",
        "loom:version-mismatch",
        "loom:digest-without-bib",
        "loom:no-readable-copy",
    }
)


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
        self.copies: frozenset[str] = frozenset()
        if result is None:
            return
        self.cited = cited_works(result)
        self.copies = result.agent_documents
        asm = result.assembly
        # what the person's own text reaches in a digest; an agent's copy reaching it makes it no more the person's
        for e in result.edges.edges:
            src, to = asm.nodes.get(e.src), asm.nodes.get(e.to)
            if (
                src is not None
                and to is not None
                and src.file not in asm.digest_files
                and src.file not in self.copies
                and to.file in asm.digest_files
            ):
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

    def digests(self, d: Diagnostic) -> set[str]:
        """The works whose digests hold `d` (its every location in one, or its every key one's result), whatever reaches them; empty otherwise."""
        if self.result is None:
            return set()
        digests = self.result.assembly.digest_files
        nodes = self.result.nodes
        if d.locations:
            return (
                {digests[loc.file] for loc in d.locations} if all(loc.file in digests for loc in d.locations) else set()
            )
        if d.keys and all(k in nodes and nodes[k].digest for k in d.keys):
            return {nodes[k].digest for k in d.keys}
        return set()

    def _copy_key(self, key: str) -> bool:
        node = self.result.nodes.get(key) if self.result else None
        return node is not None and (
            bool(node.derived_of) or (bool(node.reached_by) and set(node.reached_by) <= self.copies)
        )

    def owner(self, d: Diagnostic) -> str:
        """`WORK` for one in a digest, `COPY` for one wholly in an agent's copy (its every location in a copy, or its every key a copy's result), else `PERSON`; a diagnostic naming both the person's and a copy's is the person's.

        A digest's problem is the work's even where the person's text reaches it, since only digesting the work again mends it; a bibliography entry's is the person's, whose file it is.
        """
        if self.digests(d):
            return WORK
        if d.locations:
            return COPY if all(loc.file in self.copies for loc in d.locations) else PERSON
        if d.keys and all(self._copy_key(k) for k in d.keys):
            return COPY
        return PERSON

    def split(self, diags: list[Diagnostic]) -> dict[str, list[Diagnostic]]:
        """`diags` by owner, in their order; every owner present."""
        out: dict[str, list[Diagnostic]] = {AUTHOR: [], CITED: [], UNCITED: []}
        for d in diags:
            out[self.of(d)].append(d)
        return out


def stamped(result: ScanResult, diags: list[Diagnostic]) -> list[Diagnostic]:
    """Each diagnostic with its `owner`, a digest's problem given the fix that digests its work again.

    A digest is loom's own writing, so what is wrong in one is mended by digesting its work again: the fix runs the extraction step alone, which a viewer offers as a button through `library-update`. One that digesting again does not mend (`NOT_MENDED`) gets no such fix.
    """
    from dataclasses import replace

    from loom.scan.model import Fix

    owners = Owners(result)
    out: list[Diagnostic] = []
    for d in diags:
        whose = owners.owner(d)
        fixes = list(d.fixes)
        if whose == WORK and d.code not in NOT_MENDED:
            fixes += [
                Fix(
                    f"digest {ck} again",
                    f"loom library update {ck} --only extract --redo",
                    {"endpoint": "library-update", "body": {"works": [ck], "redo": True, "steps": ["extract"]}},
                )
                for ck in sorted(owners.digests(d))
            ]
        out.append(replace(d, owner=whose, fixes=fixes))
    return out
