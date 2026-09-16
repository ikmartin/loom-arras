"""`loom import` (book 6.2): copy a paper's closure into the quilt, insert `\\usepackage{loom}` and ids into the copies, show the diff, confirm, lint, and run the identity test.

Nothing is written until the diff is confirmed: the closure is staged in a temporary mirror of the quilt, scanned there, and only the patched copies are copied in.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from loom.refs.identity import declared
from loom.reshape.anchoring import Violation, anchoring_violations, fix_anchoring
from loom.reshape.ids import Insertion, apply_insertions, plan_insertions, unified_diff
from loom.scan.alloc import visible_locals
from loom.scan.labels import next_local
from loom.scan.quilt import Quilt, load_quilt
from loom.scan.scan import ScanResult, scan
from loom.scan.source import blank_comments
from loom.scan.tokenize import read_args, tokenize

GRAPHIC_EXTS = (".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg")


@dataclass
class ImportPlan:
    paper_dir: Path
    master_rel: str  # relative to paper dir
    files: dict[str, str] = field(default_factory=dict)  # quilt-relative path -> source absolute path
    outside: list[str] = field(default_factory=list)
    patched: dict[str, str] = field(default_factory=dict)  # quilt-relative path -> new text
    insertions: list[Insertion] = field(default_factory=list)
    violations: list[Violation] = field(default_factory=list)
    spans: list[str] = field(default_factory=list)
    diff: str = ""
    master_quilt_rel: str = ""


def _read(path: Path) -> str:
    from loom.scan.source import decode

    text, _ = decode(path.read_bytes())
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _resolve(paper_dir: Path, name: str, exts: tuple[str, ...]) -> Path | None:
    name = name.strip()
    if not name:
        return None
    for ext in ("", *exts):
        cand = name if (ext == "" or name.endswith(ext)) else name + ext
        p = paper_dir / cand
        if p.is_file():
            return p
    return None


def closure_of(paper_dir: Path, master: Path) -> tuple[dict[str, Path], list[str]]:
    """Every file the master reaches, keyed by paper-relative posix path, plus names outside the paper directory."""
    found: dict[str, Path] = {}
    outside: list[str] = []
    queue = [master]
    while queue:
        p = queue.pop()
        try:
            rel = p.resolve().relative_to(paper_dir.resolve()).as_posix()
        except ValueError:
            outside.append(str(p))
            continue
        if rel in found:
            continue
        found[rel] = p
        if p.suffix.lower() in GRAPHIC_EXTS or p.suffix.lower() in (".bst", ".bbl"):
            continue
        text = blank_comments(_read(p))
        for t in tokenize(text):
            if t.kind != "cmd":
                continue
            if t.value in ("input", "include", "nest"):
                (arg,), _, _ = read_args(text, t.end, "m")
                if arg is None:
                    continue
                arg = arg.strip()
                if not arg:
                    m = re.match(r"\s*([^\s{}\\]+)", text[t.end :])
                    arg = m.group(1) if m else ""
                target = _resolve(paper_dir, arg, (".tex",))
                if target:
                    queue.append(target)
            elif t.value in ("usepackage", "RequirePackage"):
                (_, names), _, _ = read_args(text, t.end, "om")
                for n in (names or "").split(","):
                    target = _resolve(paper_dir, n, (".sty",))
                    if target:
                        queue.append(target)
            elif t.value in ("documentclass", "LoadClass"):
                (_, name), _, _ = read_args(text, t.end, "om")
                target = _resolve(paper_dir, name or "", (".cls",))
                if target:
                    queue.append(target)
            elif t.value in ("bibliography", "addbibresource"):
                (_, name), _, _ = read_args(text, t.end, "om")
                for n in (name or "").split(","):
                    target = _resolve(paper_dir, n, (".bib",))
                    if target:
                        queue.append(target)
            elif t.value == "bibliographystyle":
                (name,), _, _ = read_args(text, t.end, "m")
                target = _resolve(paper_dir, name or "", (".bst",))
                if target:
                    queue.append(target)
            elif t.value == "includegraphics":
                (_, name), _, _ = read_args(text, t.end, "om")
                target = _resolve(paper_dir, name or "", GRAPHIC_EXTS)
                if target:
                    queue.append(target)
    return found, outside


_LOADS_LOOM = re.compile(r"\\(usepackage|RequirePackage)\s*(\[[^\]]*\])?\s*\{[^}]*\bloom\b[^}]*\}")


def _insert_usepackage(text: str, closure_texts: list[str] | None = None) -> str:
    if _LOADS_LOOM.search(blank_comments(text)) or any(
        _LOADS_LOOM.search(blank_comments(t)) for t in closure_texts or []
    ):
        return text  # the master or a file its preamble loads already has it
    m = re.search(r"\\documentclass\s*(\[[^\]]*\])?\s*\{[^}]*\}", blank_comments(text))  # not a commented-out one
    if not m:
        return text
    end = m.end()
    nl = text.find("\n", end)
    nl = len(text) if nl < 0 else nl
    return text[:nl] + "\n\\usepackage{loom}" + text[nl:]


def plan_import(quilt: Quilt, paper_file: Path, fix_anchors: bool = False, prefix: str | None = None) -> ImportPlan:
    paper_file = paper_file.resolve()
    paper_dir = paper_file.parent
    plan = ImportPlan(paper_dir=paper_dir, master_rel=paper_file.name)
    files, outside = closure_of(paper_dir, paper_file)
    plan.outside = outside
    drafts = quilt.config.drafts.strip("/")
    in_place = (
        paper_file.is_relative_to(quilt.root.resolve())
        and paper_file.parent.resolve() == (quilt.root / drafts).resolve()
    )
    for rel, src in files.items():
        if rel == plan.master_rel:
            dest = rel if in_place else f"{drafts}/{Path(rel).name}"
        else:
            dest = rel
        plan.files[dest] = str(src)
    plan.master_quilt_rel = plan.master_rel if in_place else f"{drafts}/{Path(plan.master_rel).name}"
    with tempfile.TemporaryDirectory(prefix="loom-import-") as tmp:
        stage = Path(tmp) / "quilt"
        _mirror_quilt(quilt, stage)
        texts: dict[str, str] = {}
        for dest, source in plan.files.items():
            if dest.endswith(".tex") or dest.endswith(".sty") or dest.endswith(".cls"):
                texts[dest] = _read(Path(source))
        others = [t for d, t in texts.items() if d != plan.master_quilt_rel]
        # violations are reported at the author's line numbers, and the master is about to gain a \usepackage line that shifts every line below it
        authored = dict(texts)
        if plan.master_quilt_rel in texts:
            texts[plan.master_quilt_rel] = _insert_usepackage(texts[plan.master_quilt_rel], others)
        for dest, source in plan.files.items():
            staged = stage / dest
            staged.parent.mkdir(parents=True, exist_ok=True)
            if dest in texts:
                staged.write_text(texts[dest], encoding="utf-8")
            else:
                shutil.copy(source, staged)
        result = scan(load_quilt(stage))
        theorem_names = set(result.taxa)
        for dest, text in list(texts.items()):
            if not dest.endswith(".tex"):
                continue
            v = anchoring_violations(authored[dest], theorem_names)
            if v and fix_anchors:
                texts[dest] = fix_anchoring(text, theorem_names)
                (stage / dest).write_text(texts[dest], encoding="utf-8")
            elif v:
                plan.violations.extend(
                    v if dest == plan.master_quilt_rel else [Violation(x.line, f"{dest}:{x.env}", x.kind) for x in v]
                )
        if fix_anchors:
            result = scan(load_quilt(stage))
        for d in result.lint:
            if d.code == "loom:environment-spans-files":
                plan.spans.append(
                    f"{d.locations[0].file}:{d.locations[0].line} {d.message}" if d.locations else d.message
                )
        if plan.violations or plan.spans:
            return plan
        order = [plan.master_quilt_rel]
        exp = result.expansions.get(plan.master_quilt_rel)
        if exp:
            order += [f for f in exp.reached if f != plan.master_quilt_rel and f in texts]
        order += [f for f in texts if f.endswith(".tex") and f not in order]
        pre = prefix or quilt.config.prefix
        first = next_local(visible_locals(result, pre))
        plan.insertions = plan_insertions(result, [f for f in order if f in result.files], pre, first)
        by_file: dict[str, list[Insertion]] = {}
        for ins in plan.insertions:
            by_file.setdefault(ins.file, []).append(ins)
        diffs = []
        for dest, text in texts.items():
            new = apply_insertions(text, by_file.get(dest, []))
            plan.patched[dest] = new
            original = _read(Path(plan.files[dest]))
            if new != original:
                diffs.append(unified_diff(original, new, dest))
        plan.diff = "".join(diffs)
    return plan


def _mirror_quilt(quilt: Quilt, stage: Path) -> None:
    """A temporary copy of the quilt's scanned files and config, so the staged paper is scanned in context (existing ids, taxa of other masters)."""
    stage.mkdir(parents=True)
    for p in quilt.root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(quilt.root)
        if rel.parts[0] in ("build", ".git", ".loom", "node_modules") or p.suffix not in (
            ".tex",
            ".sty",
            ".cls",
            ".bib",
            ".toml",
        ):
            continue
        target = stage / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(p, target)


def apply_import(quilt: Quilt, plan: ImportPlan) -> list[str]:
    """Copy the closure in, with patched text for the .tex/.sty/.cls files; returns the quilt-relative paths written."""
    written: list[str] = []
    for dest, src in plan.files.items():
        target = quilt.root / dest
        if (
            target.exists()
            and dest in plan.patched
            and target.read_text(encoding="utf-8", errors="replace") == plan.patched[dest]
        ):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if dest in plan.patched:
            target.write_text(plan.patched[dest], encoding="utf-8")
        else:
            if Path(src).resolve() != target.resolve():
                shutil.copy(src, target)
        written.append(dest)
    return written


def set_main(quilt: Quilt, master_rel: str) -> bool:
    """Set [quilt] main to master_rel when main is unset or names no existing file; returns whether config.toml changed."""
    cfg = quilt.root / "config.toml"
    text = cfg.read_text(encoding="utf-8")
    current = quilt.config.main
    if current and (quilt.root / current).is_file() and current != master_rel:
        return False
    if re.search(r'^main\s*=\s*"[^"]*"', text, re.M):
        new = re.sub(r'^main\s*=\s*"[^"]*"', f'main = "{master_rel}"', text, count=1, flags=re.M)
    else:
        new = text.replace("[quilt]", f'[quilt]\nmain = "{master_rel}"', 1)
    if new != text:
        cfg.write_text(new, encoding="utf-8")
        return True
    return False


def report_counts(result: ScanResult) -> str:
    from collections import Counter

    taxa = Counter(n.taxon for n in result.nodes.values() if n.kind == "environment")
    sections = Counter(n.taxon for n in result.nodes.values() if n.kind == "section")
    proofs = Counter(n.attach_via for n in result.nodes.values() if n.kind == "proof")
    dangling = sum(1 for d in result.lint if d.code == "dangling-link")
    unmatched = sum(1 for d in result.lint if d.code in ("loom:unmatched-postnote", "loom:undigested-citekey"))
    unknown = sum(1 for d in result.lint if d.code == "loom:unknown-environment")
    resolved = sum(1 for e in result.bib.values() if declared(e))
    refs_line = f"References: {dangling} dangling; {unmatched} citations with locators but no digest"
    if result.bib:
        refs_line += f"; {resolved} of {len(result.bib)} works carry an identifier"
    lines = [
        "Nodes: "
        + ", ".join(f"{n} {t}" for t, n in sorted(taxa.items(), key=lambda x: -x[1]))
        + ("; " + ", ".join(f"{n} {t.lower()}s" for t, n in sorted(sections.items())) if sections else ""),
        f"Proofs: {proofs.get('adjacent', 0)} adjacent, {proofs.get('ref', 0)} by reference, {proofs.get('enclosure', 0)} by enclosure, {proofs.get('none', 0)} unattached",
        refs_line,
    ]
    if unknown:
        lines.append(f"Unknown environments: {unknown} (add % !LOOM environment: lines to the master)")
    return "\n".join(lines)


def env_paths_for_identity(plan: ImportPlan) -> tuple[Path, str]:
    return plan.paper_dir, plan.master_rel


def has_tty() -> bool:
    return os.isatty(0)
