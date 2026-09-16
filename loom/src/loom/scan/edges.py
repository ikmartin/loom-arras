"""Edges from references, \\uses, citations with postnotes, and nesting (book 5.7, 5.8.3).

An edge runs from a region (a statement, a proof, or prose) to a node; its kind is that of the region it occurs in. A reference to a labelled region inside a node targets the node that owns the region, which is the proof key when the region lies in a proof.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from loom.scan.envtree import norm_label
from loom.scan.model import Diagnostic, Location, SourceFile
from loom.scan.nodes import Assembly
from loom.scan.tokenize import read_args

REF_CMDS = {"ref", "eqref", "cref", "Cref", "autoref", "pageref", "vref", "Vref"}
LIST_CMDS = {"cref", "Cref", "uses"}
CITE_CMDS = {
    "cite",
    "parencite",
    "textcite",
    "autocite",
    "citep",
    "citet",
    "Cite",
    "Parencite",
    "Textcite",
    "cites",
    "footcite",
    "citeauthor",
    "citeyear",
}
_CMD = re.compile(
    r"\\(ref|eqref|cref|Cref|autoref|pageref|vref|Vref|uses|cite|parencite|textcite|autocite|citep|citet|Cite|Parencite|Textcite|cites|footcite)\*?(?![A-Za-z@])"
)


@dataclass
class EdgeRec:
    src: str
    to: str
    kind: str  # statement | proof | prose
    via: str
    file: str
    line: int
    label: str = ""


@dataclass
class CiteRec:
    src: str
    citekey: str
    postnote: str | None
    file: str
    line: int
    offset: int


@dataclass
class EdgeResult:
    edges: list[EdgeRec] = field(default_factory=list)
    cites: list[CiteRec] = field(default_factory=list)
    refs_in: dict[str, list[str]] = field(default_factory=dict)  # key -> labels referenced by \ref family
    uses_in: dict[str, list[str]] = field(default_factory=dict)  # key -> labels listed in \uses
    diagnostics: list[Diagnostic] = field(default_factory=list)


def _kind_of(kind: str) -> str:
    return {"environment": "statement", "proof": "proof"}.get(kind, "prose")


def find_edges(asm: Assembly, files: dict[str, SourceFile]) -> EdgeResult:
    res = EdgeResult()
    for key, n in asm.nodes.items():
        src = files[n.file]
        text = src.clean
        kind = _kind_of(n.kind)
        for a, b in n.own:
            a = max(a, n.body_start)
            if a >= b:
                continue
            for m in _CMD.finditer(text, a, b):
                cmd = m.group(1)
                line = src.line_of(m.start())
                if cmd == "uses":
                    (arg,), _, _ = read_args(text, m.end(), "m")
                    for lab in _labels(arg, True):
                        res.uses_in.setdefault(key, []).append(lab)
                        _resolve(res, asm, key, lab, kind, "uses", n.file, line)
                elif cmd in REF_CMDS:
                    (arg,), _, _ = read_args(text, m.end(), "m")
                    for lab in _labels(arg, cmd in LIST_CMDS):
                        res.refs_in.setdefault(key, []).append(lab)
                        _resolve(res, asm, key, lab, kind, cmd, n.file, line)
                else:
                    (o1, o2, keys), _, _ = read_args(text, m.end(), "oom")
                    postnote = o2 if o2 is not None else o1
                    for ck in (keys or "").split(","):
                        ck = re.sub(r"\s+", " ", ck).strip()
                        if ck:
                            res.cites.append(
                                CiteRec(key, ck, postnote.strip() if postnote else None, n.file, line, m.start())
                            )
    for path, fe in asm.envs.items():
        src = files[path]
        for env in fe.theorem_envs:
            if env.parent is not None and env.parent.is_proof:
                pkey = asm.key_of_env(path, env.parent)
                skey = asm.key_of_env(path, env)
                if pkey and skey:
                    res.edges.append(EdgeRec(pkey, skey, "proof", "nested", path, src.line_of(env.start)))
    return res


def _labels(arg: str | None, split: bool) -> list[str]:
    if not arg:
        return []
    parts = arg.split(",") if split else [arg]
    return [norm_label(p) for p in parts if norm_label(p)]


def _resolve(
    res: EdgeResult, asm: Assembly, from_key: str, label: str, kind: str, via: str, file: str, line: int
) -> None:
    target = asm.labels.get(label)
    if target is None:
        res.diagnostics.append(
            Diagnostic(
                "error",
                "dangling-link",
                f"\\{via}{{{label}}} refers to no node or label",
                [Location(file, line)],
                [from_key],
            )
        )
        return
    region = asm.regions.get(target)
    to = region.container if region is not None else target
    if to == from_key:
        return
    src_node = asm.nodes.get(from_key)
    if src_node is not None and src_node.kind == "proof" and src_node.of == to:
        return
    res.edges.append(EdgeRec(from_key, to, kind, "postnote" if via == "cite" else via, file, line, label))
