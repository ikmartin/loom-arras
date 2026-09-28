"""Mathematical dependency targets, separate from source ownership and navigation."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from loom.scan.edges import _CMD, LIST_CMDS, REF_CMDS
from loom.scan.envtree import norm_label
from loom.scan.hashing import hash_text
from loom.scan.source import blank_comments
from loom.scan.tokenize import EnvNode, env_tree, read_args

if TYPE_CHECKING:
    from loom.scan.scan import ScanResult

DISPLAYS = {"equation", "align", "alignat", "flalign", "gather", "multline", "eqnarray", "displaymath"}


def display_span(text: str, offset: int) -> tuple[int, int] | None:
    """The complete display enclosing a label, including nested split/aligned environments."""
    roots, _ = env_tree(blank_comments(text))

    def walk(nodes: list[EnvNode]) -> tuple[int, int] | None:
        for node in nodes:
            if node.start <= offset < node.end:
                if node.name.rstrip("*") in DISPLAYS:
                    return node.start, node.end
                found = walk(node.children)
                if found:
                    return found
        return None

    return walk(roots)


def historical_display(text: str, label: str) -> str | None:
    clean = blank_comments(text)
    matches = list(re.finditer(r"\\label\s*\{\s*" + re.escape(label) + r"\s*\}", clean))
    if len(matches) != 1:
        return None
    span = display_span(text, matches[0].start())
    return text[slice(*span)] if span else None


class Dependencies:
    """Revision-local mathematical targets; equations have no acceptance state of their own."""

    def __init__(self, result: ScanResult) -> None:
        from loom.render.manifest import own_text

        self.result = result
        self.regions: dict[str, str] = {}
        self.references: dict[str, set[str]] = {}
        self.texts: dict[str, str | None] = {}
        self.owners: dict[str, str] = {}
        spans: dict[str, tuple[str, int, int]] = {}
        equation_refs = {e.label for e in result.edges.edges if e.via == "eqref"}
        for region in result.assembly.regions.values():
            source = result.files[region.file].text
            span = display_span(source, region.offset)
            if span is None and region.label not in equation_refs:
                continue
            key = "equation:" + region.label
            self.regions[region.key] = key
            self.owners[key] = region.container
            self.texts[key] = source[slice(*span)] if span else None
            if span:
                spans[key] = (region.file, *span)
        for key, node in result.nodes.items():
            if node.kind in ("environment", "proof"):
                self.texts[key] = own_text(result, node)
                self.owners[key] = key
        self.out: dict[str, list[str]] = {}
        for key in self.texts:
            targets: list[str] = []
            if key.startswith("equation:"):
                text = blank_comments(self.texts[key] or "")
                for match in _CMD.finditer(text):
                    cmd = match.group(1)
                    if cmd not in REF_CMDS | {"uses"}:
                        continue
                    (arg,), _, _ = read_args(text, match.end(), "m")
                    for label in (arg or "").split(",") if cmd in LIST_CMDS else [arg or ""]:
                        label = norm_label(label)
                        self.references.setdefault(key, set()).add(label)
                        target = self.resolve_label(label)
                        if target:
                            targets.append(target)
                if key in spans:
                    file, start, end = spans[key]
                    targets.extend(
                        edge.to
                        for edge in result.edges.edges
                        if edge.via == "postnote" and edge.file == file and start <= edge.offset < end
                    )
            else:
                for edge in result.edges.edges:
                    if edge.src == key:
                        target = (
                            self.node_target(edge.to)
                            if edge.via in ("nested", "postnote")
                            else self.resolve_label(edge.label)
                        )
                        if target:
                            targets.append(target)
                node = result.nodes[key]
                if node.kind == "proof" and node.of:
                    targets.append(node.of)
            self.out[key] = list(dict.fromkeys(t for t in targets if t != key))

    def node_target(self, key: str) -> str | None:
        node = self.result.nodes.get(key)
        if node is None or node.kind == "section":
            return None
        return node.of if node.kind == "proof" and node.of else key

    def resolve_label(self, label: str) -> str | None:
        target = self.result.assembly.labels.get(label)
        if target in self.regions:
            return self.regions[target]
        region = self.result.assembly.regions.get(target or "")
        return self.node_target(region.container if region else target or "")

    def direct(self, key: str) -> list[str]:
        return self.out.get(key, [])

    def review_targets(self, key: str) -> list[str]:
        """Nearest reviewable dependencies, passing through displays without acceptance rows."""
        targets: list[str] = []
        seen = {key}

        def visit(target: str) -> None:
            if target in seen:
                return
            seen.add(target)
            if target.startswith("equation:"):
                for dep in self.direct(target):
                    visit(dep)
            else:
                targets.append(target)

        for dep in self.direct(key):
            visit(dep)
        return targets

    def closure(self, key: str) -> list[str]:
        visited: set[str] = set()
        order: list[str] = []

        def visit(target: str) -> None:
            if target in visited:
                return
            visited.add(target)
            for dep in self.direct(target):
                visit(dep)
            order.append(target)

        visit(key)
        return order

    def hashes(self, key: str) -> dict[str, str]:
        return {
            dep: hash_text(text)
            for dep in self.closure(key)
            if dep != key and (text := self.texts.get(dep)) is not None
        }
