"""Node assembly: theorem-like environments, proofs, sections, and containers become keyed records with ids, aliases, ownership, and regions (book 5.2-5.4, 5.6, 5.8, 5.9.3).

Ownership is a partition of each file: every character belongs to the innermost claimant (a theorem-like environment, a proof, a section's per-file span, or the file itself, the master owning its preamble and top-level prose). Hierarchy for sections is per master, from the expansion; ownership is per file, so hashes never depend on which master reached a file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from loom.scan.bib import citekey_slug
from loom.scan.directives import HEAD_LINES, file_level, list_value, parse_directives, within
from loom.scan.envtree import FileEnvs, labels_in, scan_environments
from loom.scan.expand import Expansion, Segment
from loom.scan.labels import is_id_shaped
from loom.scan.model import Diagnostic, Directive, Env, Location, SourceFile, Taxon
from loom.scan.preamble import PreambleClosure, document_start
from loom.scan.sections import LEVEL_NAMES, SectionUnit, find_sections

_INCOMPLETE = re.compile(r"\\incomplete\s*\{")
_CITE = re.compile(r"\\cite[a-zA-Z*]*\s*(?:\[([^]]+)\])?\s*\{[^}]+\}")
_BASIS_NAMES = {
    "expository": {
        "definition",
        "defn",
        "def",
        "notation",
        "construction",
        "convention",
        "remark",
        "rmk",
        "rem",
        "comment",
        "example",
        "examples",
        "exmp",
        "caveat",
        "warning",
        "note",
        "recall",
        "terminology",
    },
    "local-proof": {"theorem", "thm", "lemma", "lem", "proposition", "prop", "corollary", "cor", "claim", "fact"},
    "assumption": {"assumption", "axiom", "postulate", "hypothesis"},
    "open-claim": {"conjecture", "conj", "question", "problem"},
}
_BASES = frozenset((*_BASIS_NAMES, "cited-result"))
#: What a `[basis]` table may map a name to: `cited-result` needs a locator in each block, so no name can imply it.
NAMED_BASES = tuple(_BASIS_NAMES)


@dataclass
class NodeRec:
    key: str
    kind: str  # environment | section | proof | master | file
    file: str
    start: int
    end: int
    own: list[tuple[int, int]] = field(default_factory=list)
    id: str | None = None
    env: str | None = None
    taxon: str | None = None
    style: str | None = None
    level: int | None = None
    title: str | None = None
    labels: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    parent: dict[str, str | None] = field(default_factory=dict)
    children: dict[str, list[str]] = field(default_factory=dict)
    proofs: list[str] = field(default_factory=list)
    external: bool = False
    basis: str = "unclassified"
    basis_reason: str = ""
    digest: str | None = None
    incomplete: list[str] = field(default_factory=list)
    directives: dict[str, str] = field(default_factory=dict)
    reached_by: list[str] = field(default_factory=list)
    of: str | None = None  # proofs: the statement key
    attach_via: str | None = None
    ordinal: int = 0
    exp_ranges: dict[str, tuple[int, int]] = field(default_factory=dict)
    label_offsets: dict[str, int] = field(default_factory=dict)  # label -> its \label offset in the file, for editors
    order: float = 0.0  # document order in the default master, else file order
    body_start: int = 0  # masters: offset of \\begin{document}; edges and regions are read from here on
    claimants: list[str] = field(
        default_factory=list
    )  # direct child claimants (nodes, proofs, sections) in offset order
    conflict: list[str] = field(
        default_factory=list
    )  # kind "conflict": the files that each define this id (book 5.3.5)
    conflict_of: str | None = None  # a demoted definition: the id it claimed, which a placeholder now holds

    @property
    def inline_proof(self) -> bool:
        """An explicitly classified remark/comment contains its own argument instead of a proof environment."""
        return (
            self.kind == "environment"
            and self.basis == "local-proof"
            and self.directives.get("basis", "").strip().lower() == "local-proof"
            and any(
                name in {"remark", "rmk", "rem", "comment"}
                for name in ((self.env or "").lower(), (self.taxon or "").lower())
            )
            and not self.proofs
        )


@dataclass
class RegionRec:
    key: str
    container: str
    label: str
    file: str
    offset: int
    where: str  # statement | proof:<key> | prose


@dataclass
class Assembly:
    nodes: dict[str, NodeRec] = field(default_factory=dict)
    regions: dict[str, RegionRec] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)  # label -> key (ids, aliases, section labels, region keys)
    envs: dict[str, FileEnvs] = field(default_factory=dict)
    sections: dict[str, list[SectionUnit]] = field(default_factory=dict)  # per master
    diagnostics: list[Diagnostic] = field(default_factory=list)
    directives: dict[str, list[Directive]] = field(default_factory=dict)
    digest_files: dict[str, str] = field(default_factory=dict)  # file -> citekey
    digest_prefixes: dict[str, str] = field(default_factory=dict)  # file -> the prefix its node ids carry
    citeslugs: set[str] = field(default_factory=set)  # slugs of the bibliography's citekeys, for the id grammar

    def prefix_of(self, citekey: str) -> str:
        """The id prefix a citekey's digest nodes carry: declared in its header, or the citekey's slug when it declares none."""
        from loom.scan.bib import citekey_slug

        for f, ck in self.digest_files.items():
            if ck == citekey:
                return self.digest_prefixes.get(f, citekey_slug(citekey))
        return citekey_slug(citekey)

    def statement_keys(self) -> list[str]:
        return [k for k, n in self.nodes.items() if n.kind in ("environment", "section")]

    def key_of_env(self, file: str, env: Env) -> str | None:
        return self._env_keys.get((file, env.start))

    _env_keys: dict[tuple[str, int], str] = field(default_factory=dict, repr=False)


def assemble(
    files: dict[str, SourceFile],
    closures: dict[str, PreambleClosure],
    expansions: dict[str, Expansion],
    taxa: dict[str, Taxon],
    citekeys: set[str],
    default_master: str | None,
    basis_names: dict[str, str] | None = None,
) -> Assembly:
    """Every node of the quilt from its scanned files; `basis_names` is the quilt's `[basis]` table, which extends and overrides the built-in names."""
    asm = Assembly()
    masters = list(closures)
    theorem_names = set(taxa)
    slugs = {citekey_slug(k) for k in citekeys}
    asm.citeslugs = slugs
    for path, src in files.items():
        if src.ignored:
            continue
        asm.directives[path] = parse_directives(src)
        head = {d.key: d.value for d in asm.directives[path] if d.form == "kv" and d.line <= HEAD_LINES}
        if "digest" in head:
            asm.digest_files[path] = head["digest"]
            # the prefix is declared so that it survives a citekey rename and stays typeable in \uses; the slug is only the default (DR-109)
            prefix = head.get("prefix", "").strip() or citekey_slug(head["digest"])
            asm.digest_prefixes[path] = prefix
            slugs.add(prefix)
    for path, src in files.items():
        if src.ignored:
            continue
        body = document_start(src) if path in closures else None
        asm.envs[path] = scan_environments(src, theorem_names, body or 0)
    for master, exp in expansions.items():
        asm.sections[master] = find_sections(exp, files)
    reached_any = {f for exp in expansions.values() for f in exp.reached}
    for path, src in files.items():
        if src.ignored or path in expansions or path in reached_any or not path.endswith(".tex"):
            continue
        # a file no master reaches is sectioned on its own (book 5.9.2.3); the file path stands in for the master
        solo = Expansion(master=path, text=src.clean, segments=[Segment(path, 0, len(src.clean), 0, 0)])
        asm.sections[path] = find_sections(solo, files)
    conflicted = _conflicted_ids(asm, files, slugs)
    _statement_nodes(asm, files, taxa, slugs, masters, conflicted)
    _section_nodes(asm, files, slugs, masters, default_master, conflicted)
    _placeholders(asm, files, conflicted)
    _container_nodes(asm, files, masters)
    _proof_nodes(asm, files, slugs, expansions, default_master)
    _partition(asm, files)
    _regions_and_details(asm, files, expansions, default_master, basis_names or {})
    return asm


def _order(exp: Expansion | None, file: str, offset: int, files: dict[str, SourceFile]) -> float:
    if exp is not None:
        e = exp.exp_offset(file, offset)
        if e is not None:
            return float(e)
    idx = list(files).index(file)
    return 1e12 + idx * 1e9 + offset


def _conflicted_ids(asm: Assembly, files: dict[str, SourceFile], slugs: set[str]) -> dict[str, list[str]]:
    """Ids defined by more than one file -> the files, in path order. A node is defined once and included many times (book 5.3.5); a second definition of an id leaves it with no text rather than a winner, so the decision is made here before any record exists."""
    defs: dict[str, dict[str, int]] = {}
    for path, fe in asm.envs.items():
        src = files[path]
        for env in fe.theorem_envs:
            found = labels_in(src.clean, env.own_ranges())
            first = found[0][0] if found else None
            if first and is_id_shaped(first, slugs):
                defs.setdefault(first, {}).setdefault(path, env.start)
    for units in asm.sections.values():
        for u in units:
            first = u.labels[0] if u.labels else None
            if first and is_id_shaped(first, slugs):
                defs.setdefault(first, {}).setdefault(u.file, u.offset)
    return {i: sorted(fs) for i, fs in defs.items() if len(fs) > 1}


def _placeholders(asm: Assembly, files: dict[str, SourceFile], conflicted: dict[str, list[str]]) -> None:
    """One record of kind `conflict` per doubly-defined id, holding the id and every alias its definitions carry, with no text of its own; and one `duplicate-id` per id naming every file."""
    from loom.scan.model import Fix

    for node_id, paths in sorted(conflicted.items()):
        demoted = [n for n in asm.nodes.values() if n.conflict_of == node_id]
        first: NodeRec | None = next((n for n in demoted if n.file == paths[0]), demoted[0] if demoted else None)
        aliases: list[str] = []
        for n in demoted:
            for lab in n.label_offsets:
                if lab != node_id and lab not in aliases:
                    aliases.append(lab)
        rec = NodeRec(
            key=node_id,
            kind="conflict",
            file=paths[0],
            start=first.start if first else 0,
            end=first.start if first else 0,
            id=node_id,
            env=first.env if first else None,
            taxon=first.taxon if first else None,
            style=first.style if first else None,
            level=first.level if first else None,
            title=first.title if first else None,
            labels=[node_id, *aliases],
            aliases=aliases,
            conflict=list(paths),
        )
        asm.nodes[node_id] = rec
        locations = []
        for path in paths:
            at = next((d.start for d in demoted if d.file == path), None)
            locations.append(Location(path, files[path].line_of(at) if at is not None else 1))
        fixes = [Fix(f"fork the copy in {path}", f"loom fork {node_id} --in {path}") for path in paths]
        fixes.append(Fix("give one copy a fresh id by hand", "loom id --next"))
        asm.diagnostics.append(
            Diagnostic(
                "error",
                "duplicate-id",
                f"{node_id} is defined by {' and '.join(paths)}; it has no text until one definition remains",
                locations,
                [node_id],
                fixes=fixes,
            )
        )


def _statement_nodes(
    asm: Assembly,
    files: dict[str, SourceFile],
    taxa: dict[str, Taxon],
    slugs: set[str],
    masters: list[str],
    conflicted: dict[str, list[str]],
) -> None:
    for path, fe in asm.envs.items():
        src = files[path]
        counts: dict[str, int] = {}
        for env in fe.theorem_envs:
            counts[env.name] = counts.get(env.name, 0) + 1
            own = env.own_ranges()
            found = labels_in(src.clean, own)
            labels = [lab for lab, _ in found]
            first = labels[0] if labels else None
            node_id = first if first and is_id_shaped(first, slugs) else None
            conflict_of = node_id if node_id in conflicted else None
            if conflict_of:
                node_id = None  # demoted: the placeholder holds the id and claims every label; this record claims none
            key = node_id or f"{path}#{env.name}:{counts[env.name]}"
            taxon = taxa.get(env.name)
            rec = NodeRec(
                key=key,
                kind="environment",
                file=path,
                start=env.start,
                end=env.end,
                id=node_id,
                env=env.name,
                taxon=taxon.name if taxon else env.name.capitalize(),
                style=taxon.style if taxon else "plain",
                title=env.optarg.strip() if env.optarg else None,
                labels=[] if conflict_of else labels,
                label_offsets={lab: off for lab, off in found},
                aliases=[] if conflict_of else [lab for lab in labels if lab != node_id],
                conflict_of=conflict_of,
            )
            asm.nodes[key] = rec
            asm._env_keys[(path, env.start)] = key
            if node_id is None and conflict_of is None:
                asm.diagnostics.append(
                    Diagnostic(
                        "info",
                        "loom:unlabelled-node",
                        f"{env.name} without an id",
                        [Location(path, src.line_of(env.start))],
                        [key],
                    )
                )


def _section_nodes(
    asm: Assembly,
    files: dict[str, SourceFile],
    slugs: set[str],
    masters: list[str],
    default_master: str | None,
    conflicted: dict[str, list[str]],
) -> None:
    ordered = ([default_master] if default_master in asm.sections else []) + [
        m for m in asm.sections if m != default_master
    ]
    for master in ordered:
        units = asm.sections[master]
        keys: dict[int, str] = {}
        for u in units:
            first = u.labels[0] if u.labels else None
            node_id = first if first and is_id_shaped(first, slugs) else None
            conflict_of = node_id if node_id in conflicted else None
            if conflict_of:
                node_id = None
            if node_id:
                key = node_id
            elif first:
                key = f"{u.file}#{first}"
            else:
                key = f"{u.file}#{u.name}:{u.ordinal}"
            keys[id(u)] = key
            rec = asm.nodes.get(key)
            if rec is None or rec.kind != "section":
                rec = NodeRec(
                    key=key,
                    kind="section",
                    file=u.file,
                    start=u.offset,
                    end=u.file_end,
                    id=node_id,
                    env=u.name,
                    taxon=LEVEL_NAMES.get(u.level, u.name).capitalize(),
                    level=u.level,
                    title=u.title,
                    labels=[] if conflict_of else list(u.labels),
                    # a section's definition site is its sectioning command, not the \label beside it, so every label points there
                    label_offsets=dict.fromkeys(u.labels, u.offset),
                    aliases=[] if conflict_of else [lab for lab in u.labels if lab != node_id],
                    conflict_of=conflict_of,
                )
                asm.nodes[key] = rec
            rec.exp_ranges[master] = (u.exp_start, u.exp_end)
            rec.parent[master] = keys[id(u.parent)] if u.parent is not None else None
            rec.children.setdefault(master, [])
        for u in units:
            if u.parent is not None:
                asm.nodes[keys[id(u.parent)]].children[master].append(keys[id(u)])
        asm.sections[master] = units


def _container_nodes(asm: Assembly, files: dict[str, SourceFile], masters: list[str]) -> None:
    for path, src in files.items():
        if src.ignored:
            continue
        kind = "master" if path in masters else "file"
        body = document_start(src) if kind == "master" else None
        asm.nodes[path] = NodeRec(
            key=path, kind=kind, file=path, start=0, end=len(src.clean), title=path, body_start=body or 0
        )


def _proof_nodes(
    asm: Assembly,
    files: dict[str, SourceFile],
    slugs: set[str],
    expansions: dict[str, Expansion],
    default_master: str | None,
) -> None:
    exp = expansions.get(default_master) if default_master else None
    label_map: dict[str, str] = {}
    for key, n in asm.nodes.items():
        for lab in n.labels:
            label_map.setdefault(lab, key)
    pending: list[tuple[str, Env, str | None, str, list[str]]] = []
    for path, fe in asm.envs.items():
        for proof in fe.proofs:
            att = fe.attachments[proof.start]
            stmt_key: str | None = None
            if att.statement is not None:
                stmt_key = asm.key_of_env(path, att.statement)
            elif att.via == "ref":
                stmt_key = next((label_map[lab] for lab in att.ref_labels if lab in label_map), None)
                fallback_stmt = att.fallback.statement if att.fallback is not None else None
                if stmt_key is None and fallback_stmt is not None and att.fallback is not None:
                    # every named label is unknown (reported as a dangling link); the proof sits beside a statement, so position decides
                    att = att.fallback
                    stmt_key = asm.key_of_env(path, fallback_stmt)
                elif len(att.ref_labels) > 1:
                    asm.diagnostics.append(
                        Diagnostic(
                            "warning",
                            "loom:multi-target-proof",
                            f"proof names several results ({', '.join(att.ref_labels)}); attached to the first",
                            [Location(path, files[path].line_of(proof.start))],
                        )
                    )
            pending.append((path, proof, stmt_key, att.via, att.ref_labels))
    per_statement: dict[str, list[tuple[float, str, Env, str]]] = {}
    for path, proof, stmt_key, via, ref_labels in pending:
        src = files[path]
        if stmt_key is None:
            asm.diagnostics.append(
                Diagnostic(
                    "error",
                    "loom:unattached-proof",
                    "proof is neither adjacent to a statement nor names one with \\ref"
                    + (f" (unknown label {ref_labels[0]})" if ref_labels else ""),
                    [Location(path, src.line_of(proof.start))],
                )
            )
            key = f"{path}#proof:{proof.start}"
            asm.nodes[key] = NodeRec(
                key=key, kind="proof", file=path, start=proof.start, end=proof.end, env="proof", attach_via="none"
            )
            asm._env_keys[(path, proof.start)] = key
            continue
        per_statement.setdefault(stmt_key, []).append((_order(exp, path, proof.start, files), path, proof, via))
    for stmt_key, items in per_statement.items():
        items.sort(key=lambda x: x[0])
        count = 0
        for order, path, proof, via in items:
            src = files[path]
            own = proof.own_ranges()
            found = labels_in(src.clean, own)
            labels = [lab for lab, _ in found]
            first = labels[0] if labels else None
            if first and is_id_shaped(first, slugs):
                key, pid = first, first
            else:
                count += 1
                key, pid = (f"{stmt_key}/proof" if count == 1 else f"{stmt_key}/proof/{count}"), None
            rec = NodeRec(
                key=key,
                kind="proof",
                file=path,
                start=proof.start,
                end=proof.end,
                id=pid,
                env="proof",
                taxon="Proof",
                title=proof.optarg.strip() if proof.optarg else None,
                labels=labels,
                label_offsets={lab: off for lab, off in found},
                aliases=[lab for lab in labels if lab != pid],
                of=stmt_key,
                attach_via=via,
                ordinal=count,
                order=order,
            )
            asm.nodes[key] = rec
            asm._env_keys[(path, proof.start)] = key
            asm.nodes[stmt_key].proofs.append(key)
        if count > 1:
            asm.diagnostics.append(
                Diagnostic(
                    "info",
                    "loom:positional-proof-key",
                    f"{stmt_key} has {count} unlabelled proofs; consider labelling them",
                    [],
                    [stmt_key],
                )
            )


def _partition(asm: Assembly, files: dict[str, SourceFile]) -> None:
    """Own ranges: each claimant's range minus its direct children's ranges, per file."""
    by_file: dict[str, list[NodeRec]] = {}
    for n in asm.nodes.values():
        if n.kind == "conflict":
            continue  # no text of its own, so it claims nothing
        by_file.setdefault(n.file, []).append(n)
    for recs in by_file.values():
        recs.sort(key=lambda r: (r.start, -r.end, 0 if r.kind in ("master", "file") else 1))
        stack: list[NodeRec] = []
        children: dict[str, list[NodeRec]] = {r.key: [] for r in recs}
        for r in recs:
            while stack and stack[-1].end <= r.start:
                stack.pop()
            if stack:
                children[stack[-1].key].append(r)
            stack.append(r)
        for r in recs:
            pieces: list[tuple[int, int]] = []
            pos = r.start
            kids = sorted(children[r.key], key=lambda x: x.start)
            r.claimants = [c.key for c in kids]
            for c in kids:
                if c.start > pos:
                    pieces.append((pos, c.start))
                pos = max(pos, min(c.end, r.end))
            if r.end > pos:
                pieces.append((pos, r.end))
            r.own = pieces


def _regions_and_details(
    asm: Assembly,
    files: dict[str, SourceFile],
    expansions: dict[str, Expansion],
    default_master: str | None,
    basis_names: dict[str, str],
) -> None:
    exp = expansions.get(default_master) if default_master else None
    reached: dict[str, list[str]] = {}
    for master, e in expansions.items():
        for path in e.reached:
            reached.setdefault(path, []).append(master)
    for n in asm.nodes.values():
        src = files[n.file]
        if n.kind == "conflict":
            n.reached_by = sorted({m for f in n.conflict for m in reached.get(f, [])})
            continue
        n.reached_by = reached.get(n.file, []) if n.kind != "master" else [n.file]
        if n.kind in ("environment", "proof") and not n.order:
            n.order = _order(exp, n.file, n.start, files)
        if n.kind == "section":
            n.order = _order(exp, n.file, n.start, files)
        n.incomplete = _incomplete_texts(src.clean, [(max(a, n.body_start), b) for a, b in n.own if b > n.body_start])
        node_dirs = within(asm.directives.get(n.file, []), n.own) if n.kind != "master" else []
        for d in node_dirs:
            if d.form == "kv":
                n.directives[d.key] = d.value
        if n.file in asm.digest_files and n.kind in ("environment", "section", "proof"):
            # Every node a digest defines is someone else's, sections included. Only statements used to be marked,
            # so the 226 section nodes of sixteen real digests reached the author's graph: `\cite[Section 3.6]{Kresch}`
            # resolves to one, and nothing that filters on `external` could tell it from the author's own work.
            n.digest = asm.digest_files[n.file]
            n.external = True
    for path, src in files.items():
        if src.ignored or path not in asm.envs:
            continue
        fe = asm.envs[path]
        first_node = min(
            [e.start for e in fe.theorem_envs + fe.proofs]
            + [s.start for s in asm.nodes.values() if s.file == path and s.kind == "section"],
            default=None,
        )
        file_dirs = {d.key: d.value for d in file_level(asm.directives.get(path, []), first_node) if d.form == "kv"}
        for n in asm.nodes.values():
            if n.file == path and n.kind in ("environment", "proof", "section"):
                for k, v in file_dirs.items():
                    # Names and support claims belong to one block, never every block in a file.
                    if k not in ("basis", "name"):
                        n.directives.setdefault(k, v)
    envs = {(path, env.start): env for path, fe in asm.envs.items() for env in fe.theorem_envs}
    for n in asm.nodes.values():
        if n.kind == "environment":
            n.basis, n.basis_reason = _classify_basis(n, files[n.file], envs.get((n.file, n.start)), basis_names)
            n.external = n.basis == "cited-result"
    _collect_labels(asm, files)


def _classify_basis(
    n: NodeRec, src: SourceFile, env: Env | None, configured: dict[str, str] | None = None
) -> tuple[str, str]:
    """A basis is a source-level claim about why this block may be relied on, never a TeX style.

    `configured` is the quilt's `[basis]` table, environment name to basis; a name it gives wins over the built-in table for that name only.
    """
    explicit = n.directives.get("basis", "").strip().lower()
    if explicit and explicit not in _BASES:
        return "unclassified", f"unknown basis {explicit!r}; choose {', '.join(sorted(_BASES))}"
    if n.digest:
        if explicit and explicit != "cited-result":
            return "unclassified", "a digest block must have basis cited-result"
        return "cited-result", "identified by the digest source"
    title_cites = list(_CITE.finditer(n.title or ""))
    body = src.clean[env.body_start : env.body_end] if env else ""
    first_body_cite = _CITE.match(body.lstrip())
    attributed = title_cites or first_body_cite is not None
    located = any(m.group(1) for m in title_cites) or bool(first_body_cite and first_body_cite.group(1))
    if explicit:
        if explicit == "cited-result" and not any(
            m.group(1) for a, b in n.own for m in _CITE.finditer(src.clean, a, b)
        ):
            return "unclassified", "cited-result needs a citation with a result locator in its block"
        return explicit, "classified by % !LOOM basis in the source"
    if attributed:
        if not located:
            return "unclassified", "attribution has no result locator; classify the block explicitly"
        if n.proofs:
            return "unclassified", "a cited result also has a local proof; classify the block explicitly"
        return "cited-result", "attributed to a cited result with a locator"
    names = {str(v).lower().replace(" ", "-") for v in (n.env, n.taxon) if v}
    configured = configured or {}
    matches = {configured[x] for x in names if x in configured} | {
        basis for basis, aliases in _BASIS_NAMES.items() if (names - configured.keys()) & aliases
    }
    if len(matches) != 1:
        return "unclassified", "environment name does not identify one basis; add % !LOOM basis: ... inside the block"
    basis = matches.pop()
    if n.proofs and basis != "local-proof":
        return (
            "unclassified",
            "this block has a proof but its environment suggests no local proof; classify it explicitly",
        )
    by = " by [basis] in config.toml" if names & configured.keys() else ""
    return basis, f"inferred from environment {n.taxon or n.env}{by}"


def _incomplete_texts(clean: str, own: list[tuple[int, int]]) -> list[str]:
    from loom.scan.tokenize import match_group

    out: list[str] = []
    for a, b in own:
        for m in _INCOMPLETE.finditer(clean, a, b):
            end = match_group(clean, m.end() - 1)
            if end > 0:
                out.append(re.sub(r"\s+", " ", clean[m.end() : end - 1]).strip())
    return out


def _collect_labels(asm: Assembly, files: dict[str, SourceFile]) -> None:
    seen: dict[str, tuple[str, str, int]] = {}
    for key, n in sorted(asm.nodes.items(), key=lambda kv: (kv[1].file, kv[1].start)):
        src = files[n.file]
        heading = set(n.labels) | set(
            n.label_offsets
        )  # a demoted definition's heading labels belong to the placeholder, not to a region
        for lab in n.labels:
            _claim(asm, files, seen, lab, key, n.file, n.start)
        where = "statement" if n.kind == "environment" else (f"proof:{key}" if n.kind == "proof" else "prose")
        for lab, off in labels_in(src.clean, [(max(a, n.body_start), b) for a, b in n.own if b > n.body_start]):
            if lab in heading:
                continue
            qkey = f"{key}#{lab}"
            asm.regions[qkey] = RegionRec(qkey, key, lab, n.file, off, where)
            _claim(asm, files, seen, lab, qkey, n.file, off)


def _claim(
    asm: Assembly,
    files: dict[str, SourceFile],
    seen: dict[str, tuple[str, str, int]],
    lab: str,
    key: str,
    file: str,
    off: int,
) -> None:
    if lab in seen:
        other_key, other_file, other_off = seen[lab]
        if other_key == key:
            return
        code = "duplicate-id" if is_id_shaped(lab, asm.citeslugs) else "loom:duplicate-label"
        asm.diagnostics.append(
            Diagnostic(
                "error",
                code,
                f"label {lab} is defined twice",
                [Location(other_file, files[other_file].line_of(other_off)), Location(file, files[file].line_of(off))],
                sorted({other_key, key}),
            )
        )
        return
    seen[lab] = (key, file, off)
    asm.labels[lab] = key


def tags_of(n: NodeRec) -> list[str]:
    return list_value(n.directives.get("tags", ""))
