"""`loom fork` (book 17.10): a copy of a node under a new id, for the document that needs its own version, printed as a patch the editor applies.

The text comes from the head or from a recorded version; the new id is allocated as `loom new` allocates; references inside the document are rewritten; nothing outside the document is touched.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from loom.history.ledger import History
from loom.history.versions import materialize, read_version
from loom.reshape.atomize import _single_node_file, node_region
from loom.reshape.ids import unified_diff
from loom.scan.alloc import visible_locals
from loom.scan.labels import is_id_shaped, next_local, split_id
from loom.scan.nodes import NodeRec
from loom.scan.scan import ScanResult

_REF = re.compile(r"(\\(?:ref|eqref|cref|Cref|autoref|pageref|vref|Vref|uses)\*?\s*\{)([^}]*)(\})")
_INPUT = re.compile(r"^([ \t]*)\\(input|nest)\{([^}]*)\}[ \t]*$", re.M)


@dataclass
class ForkPlan:
    node_id: str
    new_id: str
    doc: str
    mode: str = "inline"  # inline | atomic
    source_file: str = ""  # where the copied text came from
    node_file: str | None = None  # atomic: the new nodes/<id>.tex
    node_text: str = ""
    patched: str = ""  # the document's new text
    diff: str = ""
    step: int | None = None  # --from
    hash: str = ""
    elsewhere: dict[str, int] = field(default_factory=dict)  # other reached files still referring to the old id
    refusal: str | None = None


def _defining(result: ScanResult, node_id: str, doc: str) -> tuple[NodeRec | None, str]:
    """(record, mode): the definition of `node_id` the document holds inline, or the single-node file it includes; (None, why) when neither."""
    nodes = result.nodes
    n = nodes.get(node_id)
    candidates = [n] if n is not None and n.kind != "conflict" else []
    candidates += [d for d in nodes.values() if d.conflict_of == node_id]
    for c in candidates:
        if c.file == doc:
            return c, "inline"
    exp = result.expansions.get(doc)
    reached = set(exp.reached) if exp else set()
    for c in candidates:
        if c.file in reached:
            if not _single_node_file(result, c.file):
                return (
                    None,
                    f"{c.file} holds more than {node_id}; move the node out first with loom atomize --key {node_id}",
                )
            return c, "atomic"
    return None, f"{doc} neither defines {node_id} nor includes a file that does"


def _rewrite_refs(text: str, names: set[str], new_id: str) -> str:
    def repl(m: re.Match[str]) -> str:
        items = [x.strip() for x in m.group(2).split(",")]
        out = [new_id if x in names else x for x in items]
        return m.group(1) + ", ".join(out) + m.group(3) if "," in m.group(2) else m.group(1) + out[0] + m.group(3)

    return _REF.sub(repl, text)


def _relabel(text: str, node: NodeRec, node_id: str, new_id: str) -> str:
    """`\\label{ID}` becomes `\\label{NEW}`; every other heading label (an alias) is dropped, since a label defined twice is a fault."""
    out = re.sub(r"\\label\s*\{\s*" + re.escape(node_id) + r"\s*\}", f"\\\\label{{{new_id}}}", text, count=1)
    for alias in list(node.label_offsets) + list(node.aliases):
        if alias != node_id:
            out = re.sub(r"[ \t]*\\label\s*\{\s*" + re.escape(alias) + r"\s*\}", "", out)
    return out


def plan_fork(
    result: ScanResult,
    history: History,
    node_id: str,
    doc: str,
    at: str | None = None,
    as_id: str | None = None,
) -> ForkPlan:
    prefix = (split_id(node_id) or (result.quilt.config.prefix, ""))[0]
    if as_id is not None:
        if not is_id_shaped(as_id, result.assembly.citeslugs):
            return ForkPlan(node_id, as_id, doc, refusal=f"{as_id} is not an id")
        parts = split_id(as_id)
        if parts is None or parts[0] != prefix:
            return ForkPlan(node_id, as_id, doc, refusal=f"{as_id} is not under the prefix {prefix}")
        if as_id in result.nodes or parts[1] in visible_locals(result, prefix):
            return ForkPlan(node_id, as_id, doc, refusal=f"{as_id} is taken or has been referenced; choose another")
        new_id = as_id
    else:
        new_id = f"{prefix}-{next_local(visible_locals(result, prefix))}"
    plan = ForkPlan(node_id, new_id, doc)
    if doc not in result.files:
        plan.refusal = f"{doc} is not a scanned file of this quilt"
        return plan
    node, mode = _defining(result, node_id, doc)
    if node is None:
        plan.refusal = mode
        return plan
    plan.mode = mode
    plan.source_file = node.file
    names = {node_id, *node.aliases, *node.label_offsets}
    if at is not None:
        try:
            v, text = read_version(history, node_id, at)
            body = materialize(text, result)
            for pk in (f"{node_id}/proof", f"{node_id}/proof/2", f"{node_id}/proof/3"):
                try:
                    _, ptext = read_version(history, pk, at)
                except LookupError:
                    break
                body = body.rstrip("\n") + "\n" + materialize(ptext, result)
        except LookupError as exc:
            plan.refusal = str(exc)
            return plan
        plan.step, plan.hash = v.step, v.hash
        region_text = body.rstrip("\n") + "\n"
    else:
        region = node_region(result, node)
        region_text = region.text
        from loom.render.manifest import key_hash

        plan.hash = key_hash(result, node.key)
    forked = _rewrite_refs(_relabel(region_text, node, node_id, new_id), names, new_id)
    src_text = result.files[doc].text
    if mode == "inline":
        region = node_region(result, node)
        patched = src_text[: region.start] + forked + src_text[region.end :].lstrip("\n").rjust(0)
        patched = src_text[: region.start] + forked + src_text[region.end :]
        plan.patched = _rewrite_refs(patched, names, new_id)
    else:
        plan.node_file = f"nodes/{new_id}.tex"
        plan.node_text = forked
        stem = node.file[: -len(".tex")]

        def repl(m: re.Match[str]) -> str:
            name = m.group(3).strip()
            if name in (stem, node.file):
                return f"{m.group(1)}\\{m.group(2)}{{nodes/{new_id}}}"
            return m.group(0)

        plan.patched = _rewrite_refs(_INPUT.sub(repl, src_text), names, new_id)
    plan.diff = unified_diff(src_text, plan.patched, doc)
    exp = result.expansions.get(doc)
    for f in exp.reached if exp else []:
        if f == doc or f == node.file:
            continue
        count = sum(
            1 for m in _REF.finditer(result.files[f].text) if any(x.strip() in names for x in m.group(2).split(","))
        )
        if count:
            plan.elsewhere[f] = count
    return plan
