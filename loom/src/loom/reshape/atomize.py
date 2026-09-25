"""`loom atomize` and `loom inline` (book 6.4, 6.5): move each node of a file into nodes/<id>.tex and write a spine, or the reverse; never in place."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from loom.reshape.anchoring import anchoring_violations
from loom.scan.directives import within
from loom.scan.model import Env
from loom.scan.nodes import NodeRec
from loom.scan.scan import ScanResult
from loom.tex.assemble import shift_sectioning


@dataclass
class Move:
    key: str
    target: str  # quilt-relative path of the new node file
    start: int
    end: int
    text: str


@dataclass
class AtomizePlan:
    src: str
    dest: str
    moves: list[Move] = field(default_factory=list)
    spine: str = ""
    refusals: list[str] = field(default_factory=list)
    unlabelled: list[str] = field(default_factory=list)


def _wanted(result: ScanResult, src_rel: str, keys: list[str], plan: AtomizePlan) -> set[str]:
    """The statement keys to move, with a refusal in `plan` for each key that cannot be one: unknown, elsewhere, unlabelled, or inside another chosen node."""
    asm = result.assembly
    out: set[str] = set()
    for key in keys:
        n = asm.nodes.get(key)
        if n is None:
            plan.refusals.append(f"{key} is not a key of this quilt")
            continue
        if n.kind == "proof" and n.of:  # a proof is moved by the statement that carries it
            n = asm.nodes.get(n.of, n)
        if n.file != src_rel:
            plan.refusals.append(f"{n.key} lives in {n.file}, not in {src_rel}")
            continue
        if not n.id:
            plan.refusals.append(
                f"loom:atomize-unlabelled: {n.key} has no id; give it one first (loom id --next, then \\label, "
                'or the editor\'s "Give this node an id")'
            )
            continue
        if n.kind == "section":
            plan.refusals.append(f"{n.key} is a section; one-node atomize moves theorem-like nodes and their proofs")
            continue
        if n.file == f"nodes/{n.id}.tex":
            plan.refusals.append(f"{n.key} already lives in {n.file}")
            continue
        out.add(n.key)
    for key in sorted(out):
        n = asm.nodes[key]
        if any(k != key and asm.nodes[k].start <= n.start and n.end <= asm.nodes[k].end for k in out):
            plan.refusals.append(f"{key} lies inside another node being moved")
    return out


def _line_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    """Widen [start, end) to whole lines; an end that already sits at a line start (a section's span ends where the next heading begins) does not pull that next line in.

    Indentation before the next heading counts as the line start: ` \\section{…}` would otherwise pull its heading into the section before it, the two moves overlap, and the rest of the document is lost from the spine.
    """
    ls = text.rfind("\n", 0, start) + 1
    end_ls = text.rfind("\n", 0, end) + 1
    if end > start and end_ls > ls and not text[end_ls:end].strip():
        return ls, end_ls - 1
    le = text.find("\n", end)
    le = len(text) if le < 0 else le
    return ls, le


def _directive_start(result: ScanResult, node: NodeRec, region_start: int) -> int:
    """Node-level directives immediately preceding the environment travel with it."""
    src = result.files[node.file]
    start = region_start
    while True:
        ls = src.text.rfind("\n", 0, start - 1) + 1 if start > 0 else 0
        line = src.text[ls:start].rstrip("\n")
        if re.match(r"^\s*%\s*!LOOM\s+", line) and ls < start:
            start = ls
            continue
        break
    return start


@dataclass
class Region:
    """A node's whole-line region in its file: directive lines above it, the environment, and the adjacent unlabelled proofs that travel with it."""

    start: int
    end: int
    text: str
    proofs: list[str] = field(default_factory=list)


def node_region(result: ScanResult, n: NodeRec, proofs: str = "attached") -> Region:
    src = result.files[n.file]
    text = src.text
    region_start = _directive_start(result, n, n.start)
    region_end = n.end
    claimed: list[str] = []
    if n.kind == "environment":
        attached = []
        for pk in n.proofs:
            p = result.assembly.nodes[pk]
            if p.file == n.file and p.attach_via == "adjacent" and p.start >= n.end and not p.id:
                if proofs == "attached" and text[n.end : p.start].strip() == "":
                    attached.append(p)
        for p in sorted(attached, key=lambda x: x.start):
            if text[region_end : p.start].strip() == "":
                region_end = p.end
                claimed.append(p.key)
    ls, le = _line_bounds(text, region_start, region_end)
    return Region(ls, le, text[ls:le].rstrip("\n") + "\n", claimed)


def plan_atomize(
    result: ScanResult,
    src_rel: str,
    dest_rel: str,
    proofs: str = "attached",
    sections: bool = False,
    keys: list[str] | None = None,
) -> AtomizePlan:
    """The moves and the spine for atomizing `src_rel`, or with `keys` only those nodes (a proof names its statement, which carries it)."""
    plan = AtomizePlan(src=src_rel, dest=dest_rel)
    wanted = _wanted(result, src_rel, keys, plan) if keys is not None else None
    if plan.refusals:
        return plan
    asm = result.assembly
    src = result.files[src_rel]
    text = src.text
    theorem_names = set(result.taxa)
    v = anchoring_violations(text, theorem_names)
    if v:
        plan.refusals.append(
            "line-anchoring violations at line(s) " + ", ".join(str(x.line) for x in v) + " (loom:line-anchoring)"
        )
    for d in result.lint:
        if d.code == "loom:environment-spans-files" and d.locations and d.locations[0].file == src_rel:
            plan.refusals.append(d.message)
    if plan.refusals:
        return plan
    nodes_here = sorted((n for n in asm.nodes.values() if n.file == src_rel), key=lambda n: n.start)
    claimed: set[str] = set()
    moves: list[Move] = []
    for n in nodes_here:
        if n.key in claimed:
            continue
        if wanted is not None and n.key not in wanted:
            continue
        if n.kind == "environment":
            if not n.id:
                plan.unlabelled.append(n.key)
                continue
            if _inside_moved(n, nodes_here, claimed):
                continue
            # what separates is a block the reader sees: a `%` line between them is not, as it is not to the scanner that attached the proof
            if any(
                (p := asm.nodes[pk]).file == src_rel
                and p.attach_via == "adjacent"
                and p.start >= n.end
                and src.clean[n.end : p.start].strip()
                for pk in n.proofs
            ):
                plan.refusals.append(
                    f"{n.key} has a positional proof separated from its statement; add an explicit \\ref to the proof title before atomizing"
                )
                continue
            region = node_region(result, n, proofs)
            claimed.update(region.proofs)
            ls, le = region.start, region.end
            if re.search(r"\\include\s*\{", src.clean[ls:le]):
                plan.refusals.append(
                    f"{n.key} contains \\include, which cannot move into a node file (\\include forces a page break and its own .aux)"
                )
                continue
            moves.append(Move(n.key, f"nodes/{n.id}.tex", ls, le, text[ls:le].rstrip("\n") + "\n"))
            claimed.add(n.key)
        elif n.kind == "proof" and n.key not in claimed:
            stmt = asm.nodes.get(n.of or "")
            if n.id:
                ls, le = _line_bounds(text, n.start, n.end)
                moves.append(Move(n.key, f"nodes/{n.id}.tex", ls, le, text[ls:le].rstrip("\n") + "\n"))
                claimed.add(n.key)
            elif (
                stmt is not None and stmt.id and (n.attach_via == "ref" or proofs == "separate" or stmt.file != src_rel)
            ):
                suffix = "" if n.ordinal <= 1 else f".{n.ordinal}"
                ls, le = _line_bounds(text, n.start, n.end)
                moves.append(Move(n.key, f"nodes/{stmt.id}.proof{suffix}.tex", ls, le, text[ls:le].rstrip("\n") + "\n"))
                claimed.add(n.key)
    if sections:
        for n in nodes_here:
            if n.kind == "section" and n.id and n.level is not None and n.level <= 2 and n.key not in claimed:
                plan.moves = moves
                plan.spine = _spine(text, moves)
                return _atomize_sections(result, plan, nodes_here, moves)
    plan.moves = moves
    plan.spine = _spine(text, moves)
    return plan


def _inside_moved(n: NodeRec, nodes_here: list[NodeRec], claimed: set[str]) -> bool:
    for other in nodes_here:
        if other.key in claimed and other.start <= n.start and n.end <= other.end and other.key != n.key:
            return True
    return False


def _spine(text: str, moves: list[Move]) -> str:
    out = text
    for m in sorted(moves, key=lambda x: x.start, reverse=True):
        stem = m.target[: -len(".tex")] if m.target.endswith(".tex") else m.target
        out = out[: m.start] + f"\\input{{{stem}}}" + out[m.end :]
    return out


def _atomize_sections(
    result: ScanResult, plan: AtomizePlan, nodes_here: list[NodeRec], moves: list[Move]
) -> AtomizePlan:
    """With --sections: each labelled section (levels 1 and 2) becomes nodes/<id>.tex holding its heading, prose, and the inclusion lines of its children, in the spine already rewritten for environments."""
    spine = plan.spine
    offset_map = _offset_mapper(result.files[plan.src].text, moves)
    section_moves: list[Move] = []
    for n in sorted(
        (n for n in nodes_here if n.kind == "section" and n.id and n.level is not None and n.level <= 2),
        key=lambda n: n.start,
    ):
        a = offset_map(n.start)
        b = offset_map(n.end)
        ls, le = _line_bounds(spine, a, b)
        body = spine[ls:le].rstrip("\n") + "\n"
        section_moves.append(Move(n.key, f"nodes/{n.id}.tex", ls, le, body))
    outer: list[Move] = []
    for m in sorted(section_moves, key=lambda x: x.start):
        if any(o.start <= m.start and m.end <= o.end for o in outer):
            continue
        outer.append(m)
    new_spine = spine
    for m in sorted(outer, key=lambda x: x.start, reverse=True):
        stem = m.target[: -len(".tex")]
        new_spine = new_spine[: m.start] + f"\\input{{{stem}}}" + new_spine[m.end :]
    inner_moves: list[Move] = []
    for m in outer:
        text = m.text
        for sub in sorted(
            (s for s in section_moves if s is not m and m.start <= s.start and s.end <= m.end),
            key=lambda s: s.start,
            reverse=True,
        ):
            rel_a, rel_b = sub.start - m.start, sub.end - m.start
            stem = sub.target[: -len(".tex")]
            text = text[:rel_a] + f"\\input{{{stem}}}" + text[rel_b:]
            inner_moves.append(sub)
        m.text = text
    plan.moves = moves + outer + inner_moves
    plan.spine = new_spine
    return plan


def _offset_mapper(original: str, moves: list[Move]):  # type: ignore[no-untyped-def]
    replacements = sorted(((m.start, m.end, len(f"\\input{{{m.target[:-4]}}}")) for m in moves), key=lambda x: x[0])

    def mapper(pos: int) -> int:
        delta = 0
        for a, b, n in replacements:
            if b <= pos:
                delta += n - (b - a)
            elif a <= pos < b:
                return a + delta
        return pos + delta

    return mapper


def write_atomize(result: ScanResult, plan: AtomizePlan, force: bool = False) -> list[str]:
    root = result.quilt.root
    dest = root / plan.dest
    if dest.exists():
        raise FileExistsError(str(plan.dest))
    for m in plan.moves:
        if (root / m.target).exists():
            raise FileExistsError(m.target)
    written: list[str] = []
    for m in plan.moves:
        p = root / m.target
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(m.text, encoding="utf-8")
        written.append(m.target)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(plan.spine, encoding="utf-8")
    written.append(plan.dest)
    return written


def write_moves(result: ScanResult, plan: AtomizePlan) -> list[str]:
    """Write a plan's node files, refusing before writing anything if one exists. The source file is the author's to change."""
    root = result.quilt.root
    for m in plan.moves:
        if (root / m.target).exists():
            raise FileExistsError(m.target)
    written: list[str] = []
    for m in plan.moves:
        path = root / m.target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(m.text, encoding="utf-8")
        written.append(m.target)
    return written


def verify_plan(result: ScanResult, plan: AtomizePlan) -> str | None:
    """None when the moves and the spine put back together are the source file byte for byte, else what differs.

    The moved text is the region with its trailing newlines normalised to one, and the spine carries an inclusion line in its place, so reversing the plan is exact and needs no LaTeX.
    """
    text = result.files[plan.src].text
    rebuilt = plan.spine
    for m in sorted(plan.moves, key=lambda x: x.start, reverse=True):
        stem = m.target[: -len(".tex")] if m.target.endswith(".tex") else m.target
        line = f"\\input{{{stem}}}"
        at = rebuilt.find(line)
        if at < 0:
            return f"the spine has no inclusion line for {m.key}"
        rebuilt = rebuilt[:at] + text[m.start : m.end] + rebuilt[at + len(line) :]
        if m.text != text[m.start : m.end].rstrip("\n") + "\n":
            return f"the text moved for {m.key} is not its region"
    return None if rebuilt == text else f"{plan.src} is not reproduced by the plan"


def plan_payload(result: ScanResult, plan: AtomizePlan) -> dict[str, object]:
    """The plan as data for an editor: the region to replace, what stands in its place, and the files to create."""
    src = result.files[plan.src]
    return {
        "src": plan.src,
        "keys": [m.key for m in plan.moves],
        "edits": [
            {
                "file": plan.src,
                "start": m.start,
                "end": m.end,
                "line": src.line_of(m.start),
                "text": f"\\input{{{m.target[: -len('.tex')]}}}",
            }
            for m in plan.moves
        ],
        "files": [{"path": m.target, "text": m.text} for m in plan.moves],
        "refusals": list(plan.refusals),
    }


def inline(result: ScanResult, src_rel: str, recursive: bool = False) -> str:
    """The text of `src_rel` with every `\\input{nodes/...}` (and `\\nest`) of a single-node file replaced by that file's contents."""
    root = result.quilt.root
    text = result.files[src_rel].text if src_rel in result.files else (root / src_rel).read_text(encoding="utf-8")
    pattern = re.compile(r"^([ \t]*)\\(input|nest)\{([^}]*)\}[ \t]*$", re.M)

    def repl(m: re.Match[str]) -> str:
        name = m.group(3).strip()
        cand = root / name
        if not cand.is_file():
            cand = root / (name + ".tex")
        if (
            not cand.is_file() or cand.suffix != ".tex"
        ):  # a non-.tex inclusion (a figure's .pspdftex, say) is opaque, as in the scanner
            return m.group(0)
        rel = cand.relative_to(root).as_posix()
        if not _single_node_file(result, rel) and not recursive:
            return m.group(0)
        body = inline(result, rel, recursive) if recursive else cand.read_text(encoding="utf-8")
        if m.group(2) == "nest":
            body = shift_sectioning(body, 1)
        return body.rstrip("\n")

    return pattern.sub(repl, text)


def _single_node_file(result: ScanResult, rel: str) -> bool:
    nodes = [n for n in result.nodes.values() if n.file == rel and n.kind in ("environment", "section")]
    proofs = [n for n in result.nodes.values() if n.file == rel and n.kind == "proof"]
    if len(nodes) == 1 and all(p.of == nodes[0].key or p.attach_via == "adjacent" for p in proofs):
        return True
    return len(nodes) == 0 and len(proofs) == 1


def directive_lines(result: ScanResult, node: NodeRec) -> list[str]:
    return [d.key for d in within(result.assembly.directives.get(node.file, []), node.own)]


def env_of(result: ScanResult, node: NodeRec) -> Env | None:
    fe = result.assembly.envs.get(node.file)
    if not fe:
        return None
    for e in fe.all_envs():
        if e.start == node.start:
            return e
    return None
