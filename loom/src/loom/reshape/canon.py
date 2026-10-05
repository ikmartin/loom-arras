"""`loom import` and `loom history restore` (book 6.1-6.3, 17.9): a paper arrives as one flat text, kept as a landmark, and a landmark's text becomes a working document with the two things a working document needs, `\\usepackage{loom}` and ids.

Nothing is written until a plan is confirmed; the draft is staged in a temporary mirror of the quilt and scanned there, exactly as import once staged a whole closure.
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from loom.reshape.anchoring import Violation, anchoring_violations, fix_anchoring
from loom.reshape.ids import Insertion, apply_insertions, plan_insertions, unified_diff
from loom.reshape.importer import _insert_usepackage, _mirror_quilt, closure_of, inline_bbl
from loom.reshape.linearize import flatten, from_canon
from loom.scan.alloc import visible_locals
from loom.scan.labels import next_local
from loom.scan.quilt import Quilt, load_quilt
from loom.scan.scan import ScanResult, scan


@dataclass
class ImportPlan:
    paper_dir: Path
    master_rel: str  # relative to the paper directory
    dest_rel: str  # quilt-relative path of the drafted document
    text: str = ""  # the flat paper as received, which the import step keeps as a landmark
    inlined: list[str] = field(default_factory=list)
    assets: dict[str, str] = field(default_factory=dict)  # quilt-relative path -> absolute source, the non-.tex closure
    outside: list[str] = field(default_factory=list)
    exists: bool = False  # the drafted document's path is taken


def plan_import(quilt: Quilt, paper_file: Path, dest_rel: str | None = None) -> ImportPlan:
    """Linearize the paper's master into one flat text and list its assets for copying to the root at their paper-relative paths; the draft goes to `dest_rel`, by default `<drafting>/<name>`."""
    paper_file = paper_file.resolve()
    paper_dir = paper_file.parent
    dest_rel = dest_rel or f"{quilt.config.drafting}/{paper_file.name}"
    plan = ImportPlan(paper_dir=paper_dir, master_rel=paper_file.name, dest_rel=dest_rel)
    files, outside = closure_of(paper_dir, paper_file)
    plan.outside = outside
    flat = flatten(paper_dir, plan.master_rel)
    plan.text, bbl = inline_bbl(paper_dir, plan.master_rel, flat.text)
    plan.inlined = [*flat.inlined, *([bbl] if bbl else [])]
    for rel, src in files.items():
        if rel == plan.master_rel or rel in flat.inlined:
            continue
        plan.assets[rel] = str(src)
    plan.exists = (quilt.root / dest_rel).exists()
    return plan


def apply_import(quilt: Quilt, plan: ImportPlan) -> list[str]:
    """Copy the paper's assets in; returns the quilt-relative paths written. A file already at its place with the same bytes is left alone (the in-place case)."""
    written: list[str] = []
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
    dest_rel: str
    authored: str = ""  # the text drafted from: a landmark's, or a paper's as received
    text: str = ""  # what will be written
    insertions: list[Insertion] = field(default_factory=list)
    violations: list[Violation] = field(default_factory=list)
    spans: list[str] = field(default_factory=list)
    diff: str = ""
    swapped_block: bool = False


def plan_draft(
    result: ScanResult,
    authored: str,
    dest_rel: str,
    ids: bool = True,
    fix_anchors: bool = False,
    prefix: str | None = None,
    assets: dict[str, str] | None = None,
) -> DraftPlan:
    """The document `dest_rel` would be, drafted from `authored`: the package line in place of the macro block or added, ids in document order on every node that has none, and anchoring repaired on request; violations refuse unless repaired.

    `assets` (quilt-relative path -> absolute source) are staged beside the draft before it is scanned: an import's style files declare the theorem environments that get ids, and are not in the quilt until the import is confirmed.
    """
    quilt = result.quilt
    plan = DraftPlan(dest_rel=dest_rel, authored=authored)
    text, plan.swapped_block = from_canon(authored)
    if not plan.swapped_block and "\\usepackage{loom}" not in text:
        text = _insert_usepackage(text)
    with tempfile.TemporaryDirectory(prefix="loom-draft-") as tmp:
        stage = Path(tmp) / "quilt"
        _mirror_quilt(quilt, stage)
        for rel, source in (assets or {}).items():
            (stage / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(source, stage / rel)
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
