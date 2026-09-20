"""`loom import` and `loom draft` (book 6.1-6.3): a paper arrives as one flat canon document, and a canon document becomes a working draft with the two things a landmark must not carry, `\\usepackage{loom}` and ids.

Nothing is written until a plan is confirmed; the draft is staged in a temporary mirror of the quilt and scanned there, exactly as import once staged a whole closure.
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from loom.history.ledger import Entry, History
from loom.history.steps import file_hash, text_hash
from loom.reshape.anchoring import Violation, anchoring_violations, fix_anchoring
from loom.reshape.ids import Insertion, apply_insertions, plan_insertions, unified_diff
from loom.reshape.importer import _insert_usepackage, _mirror_quilt, _read, closure_of, inline_bbl
from loom.reshape.linearize import flatten, from_canon
from loom.scan.alloc import visible_locals
from loom.scan.labels import next_local
from loom.scan.quilt import Quilt, load_quilt
from loom.scan.scan import ScanResult, scan


@dataclass
class ImportPlan:
    paper_dir: Path
    master_rel: str  # relative to the paper directory
    canon_rel: str  # quilt-relative path of the flat copy
    text: str = ""  # the flat document
    inlined: list[str] = field(default_factory=list)
    assets: dict[str, str] = field(default_factory=dict)  # quilt-relative path -> absolute source, the non-.tex closure
    outside: list[str] = field(default_factory=list)
    exists: bool = False  # the canon path is taken


def plan_import(quilt: Quilt, paper_file: Path) -> ImportPlan:
    """Linearize the paper's master into `canon/<stem>.tex` and list its assets for copying to the root at their paper-relative paths."""
    paper_file = paper_file.resolve()
    paper_dir = paper_file.parent
    canon_rel = f"{quilt.config.canon}/{paper_file.name}"
    plan = ImportPlan(paper_dir=paper_dir, master_rel=paper_file.name, canon_rel=canon_rel)
    files, outside = closure_of(paper_dir, paper_file)
    plan.outside = outside
    flat = flatten(paper_dir, plan.master_rel)
    plan.text, bbl = inline_bbl(paper_dir, plan.master_rel, flat.text)
    plan.inlined = [*flat.inlined, *([bbl] if bbl else [])]
    for rel, src in files.items():
        if rel == plan.master_rel or rel in flat.inlined:
            continue
        plan.assets[rel] = str(src)
    plan.exists = (quilt.root / canon_rel).exists()
    return plan


def apply_import(quilt: Quilt, plan: ImportPlan) -> list[str]:
    """Write the flat copy and copy the assets in; returns the quilt-relative paths written. A file already at its place with the same bytes is left alone (the in-place case)."""
    written: list[str] = []
    target = quilt.root / plan.canon_rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(plan.text, encoding="utf-8")
    written.append(plan.canon_rel)
    for dest, src in plan.assets.items():
        t = quilt.root / dest
        if Path(src).resolve() == t.resolve():
            continue
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, t)
        written.append(dest)
    return written


@dataclass
class DraftPlan:
    canon_rel: str
    dest_rel: str
    authored: str = ""  # the canon text as read
    text: str = ""  # what will be written
    insertions: list[Insertion] = field(default_factory=list)
    violations: list[Violation] = field(default_factory=list)
    spans: list[str] = field(default_factory=list)
    diff: str = ""
    step: Entry | None = None  # the step that wrote the canon file, when the history knows it
    moved: bool = False  # the canon file no longer hashes to what its step recorded
    swapped_block: bool = False


def plan_draft(
    result: ScanResult,
    history: History,
    canon_rel: str,
    dest_rel: str,
    ids: bool = True,
    fix_anchors: bool = False,
    prefix: str | None = None,
) -> DraftPlan:
    """The draft `dest_rel` would be: the canon text with the package line, ids in document order, and anchoring repaired on request; violations refuse unless repaired."""
    quilt = result.quilt
    plan = DraftPlan(canon_rel=canon_rel, dest_rel=dest_rel)
    plan.authored = _read(quilt.root / canon_rel)
    plan.step = history.step_for_path(canon_rel)
    if plan.step is not None:
        to = plan.step.get("to") or {}
        recorded = to.get("hash") if isinstance(to, dict) else None
        plan.moved = bool(recorded) and file_hash(quilt.root / canon_rel) != recorded
    text, plan.swapped_block = from_canon(plan.authored)
    if not plan.swapped_block:
        text = _insert_usepackage(text)
    with tempfile.TemporaryDirectory(prefix="loom-draft-") as tmp:
        stage = Path(tmp) / "quilt"
        _mirror_quilt(quilt, stage)
        staged = stage / dest_rel
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_text(text, encoding="utf-8")
        staged_result = scan(load_quilt(stage))
        theorem_names = set(staged_result.taxa)
        v = anchoring_violations(plan.authored, theorem_names)
        if v and fix_anchors:
            text = fix_anchoring(text, theorem_names)
            staged.write_text(text, encoding="utf-8")
            staged_result = scan(load_quilt(stage))
        elif v:
            plan.violations = v
        for d in staged_result.lint:
            if d.code == "loom:environment-spans-files" and d.locations and d.locations[0].file == dest_rel:
                plan.spans.append(f"{d.locations[0].file}:{d.locations[0].line} {d.message}")
        if plan.violations or plan.spans:
            plan.text = text
            return plan
        if ids and dest_rel in staged_result.files:
            pre = prefix or quilt.config.prefix
            first = next_local(visible_locals(result, pre) | visible_locals(staged_result, pre))
            plan.insertions = plan_insertions(staged_result, [dest_rel], pre, first)
            text = apply_insertions(text, plan.insertions)
    plan.text = text
    plan.diff = unified_diff(plan.authored, text, dest_rel)
    return plan


def draft_entry(quilt: Quilt, plan: DraftPlan) -> dict[str, object]:
    """The ledger line's fields for a draft that was written."""
    return {
        "from": {
            "path": plan.canon_rel,
            "hash": text_hash(plan.authored),
            "step": plan.step.step if plan.step is not None else None,
        },
        "to": {"path": plan.dest_rel, "hash": text_hash(plan.text)},
        "ids": len(plan.insertions),
        "moved": plan.moved,
    }
