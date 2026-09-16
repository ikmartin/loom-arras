"""`loom ai promote PATH` (book 11.7): copy a draft node or a digest from a run into the quilt, allocating or checking its id; never touch the run's file."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from loom.scan.alloc import visible_locals
from loom.scan.bib import citekey_slug
from loom.scan.envtree import labels_in, scan_environments
from loom.scan.labels import is_id_shaped, next_local, split_id
from loom.scan.model import SourceFile
from loom.scan.scan import ScanResult
from loom.scan.source import blank_comments, line_starts

_DIGEST = re.compile(r"^%\s*!LOOM\s+digest:\s*(\S+)", re.M)


@dataclass
class Promotion:
    kind: str  # node | digest
    target: str  # quilt-relative
    text: str
    node_id: str | None = None
    allocated: bool = False
    replaced_skeleton: bool = False


def _source(rel: str, path: Path, text: str) -> SourceFile:
    return SourceFile(
        path=rel,
        abspath=path,
        text=text,
        clean=blank_comments(text),
        encoding="utf-8",
        ignored=False,
        line_starts=line_starts(text),
    )


def plan_promotion(result: ScanResult, path: Path, prefix: str | None) -> Promotion:
    root = result.quilt.root
    text = path.read_text(encoding="utf-8")
    m = _DIGEST.search(text)
    if m or path.name.startswith("ingest-"):
        if not m:
            raise ValueError(f"{path.name} has no `% !LOOM digest:` header")
        return Promotion("digest", f"digests/{m.group(1)}.tex", text)
    rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else path.name
    src = _source(rel, path, text)
    fe = scan_environments(src, set(result.taxa))
    envs = [e for e in fe.theorem_envs if e.parent is None or not e.parent.theorem_like]
    if len(envs) != 1:
        raise ValueError(f"{path.name} must contain exactly one node; found {len(envs)} theorem-like environments")
    env = envs[0]
    slugs = {citekey_slug(k) for k in result.bib}
    labels = [lab for lab, _ in labels_in(src.clean, env.own_ranges())]
    ids = [lab for lab in labels if is_id_shaped(lab, slugs)]
    pfx = prefix or result.quilt.config.prefix
    if ids:
        node_id = ids[0]
        parts = split_id(node_id)
        if parts is None:
            raise ValueError(f"{node_id} is not an id")
        existing = result.nodes.get(node_id)
        skeleton = root / "nodes" / f"{node_id}.tex"
        if existing is not None and not _is_skeleton(existing.file, root, node_id):
            raise ValueError(f"{node_id} is already allocated to {existing.file}")
        if existing is None and node_id[len(parts[0]) + 1 :] in visible_locals(result, parts[0]):
            raise ValueError(f"{node_id} is referenced in the quilt's records or dangling links; choose another id")
        return Promotion("node", f"nodes/{node_id}.tex", text, node_id, False, skeleton.is_file())
    local = next_local(visible_locals(result, pfx))
    node_id = f"{pfx}-{local}"
    insert_at = env.body_start
    # directly after \begin{ENV}[title], before any newline
    head_end = text.find("\n", env.start)
    at = min(insert_at, head_end if head_end >= 0 else insert_at)
    patched = text[:at] + f"\\label{{{node_id}}}" + text[at:]
    return Promotion("node", f"nodes/{node_id}.tex", patched, node_id, True, False)


def _is_skeleton(file: str, root: Path, node_id: str) -> bool:
    """A loose skeleton the author created with `loom new` for this id: the node file whose statement is still empty."""
    if file != f"nodes/{node_id}.tex":
        return False
    text = (root / file).read_text(encoding="utf-8")
    body = re.sub(r"%.*", "", text)
    body = re.sub(r"\\(begin|end)\{[^}]*\}(\[[^\]]*\])?", "", body)
    body = re.sub(r"\\label\{[^}]*\}|\\uses\{[^}]*\}|\\incomplete\{[^}]*\}", "", body)
    return body.strip() == ""


def write_promotion(root: Path, plan: Promotion, replace: bool) -> Path:
    dest = root / plan.target
    if dest.exists() and not (replace or plan.replaced_skeleton):
        raise FileExistsError(str(dest))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(plan.text, encoding="utf-8")
    return dest
