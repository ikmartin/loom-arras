"""Dependency closure and downstream sets over the edge list (book 3.4, 5.7.2, 7.9)."""

from __future__ import annotations

from collections import defaultdict

from loom.scan.edges import EdgeRec
from loom.scan.nodes import Assembly


class Graph:
    def __init__(self, asm: Assembly, edges: list[EdgeRec]) -> None:
        self.asm = asm
        self.edges = edges
        self.out: dict[str, list[EdgeRec]] = defaultdict(list)
        self.inc: dict[str, list[EdgeRec]] = defaultdict(list)
        for e in edges:
            self.out[e.src].append(e)
            self.inc[e.to].append(e)

    def statement_key(self, key: str) -> str:
        n = self.asm.nodes.get(key)
        return n.of if n is not None and n.kind == "proof" and n.of else key

    def direct(self, key: str) -> list[str]:
        seen: list[str] = []
        for e in self.out.get(key, []):
            t = self.statement_key(e.to)
            if t not in seen and t != key:
                seen.append(t)
        return seen

    def closure(self, key: str) -> list[str]:
        """Transitive statement dependencies in dependency order (dependencies first), then the key's own statement last. For a proof key, its direct proof-edges' statements and their closures are included."""
        stmt = self.statement_key(key)
        order: list[str] = []
        visiting: set[str] = set()

        def visit(k: str) -> None:
            if k in order or k in visiting:
                return
            visiting.add(k)
            for e in self.out.get(k, []):
                if e.kind == "statement" or e.via == "nested":
                    visit(self.statement_key(e.to))
            visiting.discard(k)
            order.append(k)

        if key != stmt:
            for e in self.out.get(key, []):
                visit(self.statement_key(e.to))
        visit(stmt)
        return order

    def downstream(self, key: str) -> list[str]:
        """Every key that depends on `key` transitively (statements and proofs)."""
        targets = {key}
        n = self.asm.nodes.get(key)
        if n is not None:
            targets.update(n.proofs)
        out: list[str] = []
        stack = list(targets)
        seen: set[str] = set()
        while stack:
            k = stack.pop()
            for e in self.inc.get(k, []):
                if e.src not in seen and e.src not in targets:
                    seen.add(e.src)
                    out.append(e.src)
                    src_node = self.asm.nodes.get(e.src)
                    stack.append(e.src)
                    if src_node is not None:
                        stack.extend(p for p in src_node.proofs if p not in seen)
        return out

    def cycles(self) -> list[list[str]]:
        """Simple cycles among statement-edges (each reported once)."""
        adj: dict[str, list[str]] = defaultdict(list)
        for e in self.edges:
            if e.kind == "statement":
                adj[e.src].append(self.statement_key(e.to))
        found: list[list[str]] = []
        state: dict[str, int] = {}
        path: list[str] = []

        def dfs(u: str) -> None:
            state[u] = 1
            path.append(u)
            for v in adj.get(u, []):
                if state.get(v, 0) == 0:
                    dfs(v)
                elif state.get(v) == 1:
                    cyc = path[path.index(v) :]
                    if sorted(cyc) not in [sorted(c) for c in found]:
                        found.append(list(cyc))
            path.pop()
            state[u] = 2

        for u in list(adj):
            if state.get(u, 0) == 0:
                dfs(u)
        return found
