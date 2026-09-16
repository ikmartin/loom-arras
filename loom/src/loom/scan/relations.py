"""Relations declared with `% !LOOM see:` (book 5.11.3): a link between two nodes that a viewer shows and the mathematics never sees.

A relation is not a dependency. It enters no closure, no bundle, no acceptance row, and no staleness computation, and it is stored beside `edges` rather than inside them so that nothing which walks the graph can reach it by accident. `\\uses` remains the only way to declare a dependency the text does not name.

Scope follows `tags:` (5.11.2): inside a node's own text the directive applies to that node; in a file's first twenty lines before any node it applies to every node the file defines.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from loom.scan.directives import file_level, list_value, within
from loom.scan.model import Diagnostic, Location, SourceFile
from loom.scan.nodes import Assembly


@dataclass(frozen=True)
class RelationRec:
    """One declared relation. `from_key` is the node that declared it, so the declaring side is known even though display is symmetric."""

    from_key: str
    to_key: str
    kind: str
    file: str
    line: int


@dataclass
class RelationResult:
    relations: list[RelationRec] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


def _first_node_offset(asm: Assembly, path: str) -> int | None:
    fe = asm.envs.get(path)
    starts = [e.start for e in (fe.theorem_envs + fe.proofs)] if fe else []
    starts += [n.start for n in asm.nodes.values() if n.file == path and n.kind == "section"]
    return min(starts, default=None)


def find_relations(asm: Assembly, files: dict[str, SourceFile]) -> RelationResult:
    """Resolve every `see:` item to a node key, after ids and aliases are known.

    An item resolves like a reference: an id, an alias, or a digest node id. A target inside a node (a labelled equation) resolves to the node that contains it, as a reference does. Unresolved items are `dangling-link`; a self-relation or a duplicate is `loom:see-redundant`.
    """
    res = RelationResult()
    seen: set[tuple[str, str, str]] = set()

    def declare(from_key: str, value: str, path: str, line: int) -> None:
        for item in list_value(value):
            target = asm.labels.get(item)
            if target is None:
                res.diagnostics.append(
                    Diagnostic(
                        "error",
                        "dangling-link",
                        f"% !LOOM see: {item} refers to no node or label",
                        [Location(path, line)],
                        [from_key],
                    )
                )
                continue
            region = asm.regions.get(target)
            to_key = region.container if region is not None else target
            if to_key == from_key:
                res.diagnostics.append(
                    Diagnostic(
                        "info",
                        "loom:see-redundant",
                        f"% !LOOM see: {item} names the node it is written in",
                        [Location(path, line)],
                        [from_key],
                    )
                )
                continue
            token = (from_key, to_key, "see")
            if token in seen:
                res.diagnostics.append(
                    Diagnostic(
                        "info",
                        "loom:see-redundant",
                        f"% !LOOM see: {item} is already declared on {from_key}",
                        [Location(path, line)],
                        [from_key],
                    )
                )
                continue
            seen.add(token)
            res.relations.append(RelationRec(from_key, to_key, "see", path, line))

    for path in sorted(files):
        src = files[path]
        if src.ignored or path not in asm.directives:
            continue
        directives = asm.directives[path]
        nodes = [n for n in asm.nodes.values() if n.file == path and n.kind in ("environment", "proof", "section")]
        for n in sorted(nodes, key=lambda x: x.start):
            for d in within(directives, n.own):
                if d.form == "kv" and d.key == "see":
                    declare(n.key, d.value, path, d.line)
        for d in file_level(directives, _first_node_offset(asm, path)):
            if d.form == "kv" and d.key == "see":
                for n in sorted(nodes, key=lambda x: x.start):
                    declare(n.key, d.value, path, d.line)
    res.relations.sort(key=lambda r: (r.from_key, r.to_key, r.kind))
    return res
