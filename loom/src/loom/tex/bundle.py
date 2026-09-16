"""Bundles: a standalone document for one key containing exactly the statements it depends on (book 3.4, 9.7, DR-37).

Layout: the master's preamble closure verbatim (with \\usepackage{loom} guaranteed), a heading, the statements of the closure in dependency order, then the key's own region (the statement, or statement and proof). `--with` substitutes a proposed diff or file for the key's text and `--draft` bundles a node file not yet in the quilt; neither touches the quilt.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path

from loom.scan.envtree import scan_environments
from loom.scan.model import SourceFile
from loom.scan.nodes import NodeRec
from loom.scan.scan import ScanResult
from loom.scan.source import blank_comments, line_starts

HEADER = "% Bundle written by loom. Statements of the closure precede the key; ids are shown as comments before each environment.\n"


@dataclass
class Bundle:
    key: str
    text: str
    closure: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


def bundle_filename(key: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", key) + ".tex"


def _preamble(result: ScanResult, master: str) -> str:
    src = result.files[master]
    m = re.search(r"\\begin\s*\{document\}", src.clean)
    pre = src.text[: m.start()] if m else src.text
    closure = result.closures.get(master)
    if closure is not None and not closure.loads_loom:
        pre = re.sub(r"(\\documentclass(?:\[[^\]]*\])?\{[^}]*\})", r"\1\n\\usepackage{loom}", pre, count=1)
    return pre.rstrip() + "\n"


def region_text(result: ScanResult, key: str, override: str | None = None) -> str:
    """The key's whole region (an environment with its labels; for a section its per-file span) from the raw text."""
    if override is not None:
        return override
    n = result.nodes[key]
    src = result.files[n.file]
    return src.text[n.start : n.end]


def statement_block(result: ScanResult, key: str, override: str | None = None) -> str:
    n = result.nodes[key]
    text = region_text(result, key, override)
    if n.digest:
        block = _macro_block(result, n.file)
        if block:
            return f"% id: {key} (digest {n.digest})\n\\begingroup\n{block}\n{text}\n\\endgroup\n"
    return f"% id: {key}\n{text}\n"


def _macro_block(result: ScanResult, file: str) -> str:
    src = result.files[file]
    m = re.search(r"^\s*%\s*!LOOM\s+begin\s+macros\s*$(.*?)^\s*%\s*!LOOM\s+end\s+macros\s*$", src.text, re.M | re.S)
    return m.group(1).strip("\n") if m else ""


def build_bundle(result: ScanResult, key: str, master: str | None = None, override_text: str | None = None) -> Bundle:
    assert result.graph is not None
    master = master or result.default_master or (result.masters[0] if result.masters else None)
    if master is None:
        raise ValueError("the quilt has no master to take a preamble from")
    n = result.nodes[key]
    stmt_key = n.of if n.kind == "proof" and n.of else key
    closure = [k for k in result.graph.closure(key) if k != stmt_key]
    parts = [HEADER, _preamble(result, master), "\\begin{document}\n", f"\\section*{{Bundle for {key}}}\n\n"]
    missing: list[str] = []
    for dep in closure:
        if dep in result.nodes and result.nodes[dep].kind in ("environment", "section"):
            parts.append(statement_block(result, dep) + "\n")
        else:
            missing.append(dep)
    if n.kind == "proof":
        parts.append(statement_block(result, stmt_key) + "\n")
        parts.append(f"% proof: {key}\n{region_text(result, key, override_text)}\n")
    else:
        parts.append(statement_block(result, key, override_text) + "\n")
        for pk in n.proofs:
            parts.append(f"% proof: {pk}\n{region_text(result, pk)}\n")
    parts.append("\n\\end{document}\n")
    return Bundle(key, "".join(parts), closure, missing)


def apply_unified_diff(original: str, diff_text: str) -> str:
    """Apply a unified diff (one file) to `original`; raises ValueError when a hunk does not match."""
    lines = original.splitlines(keepends=True)
    out: list[str] = []
    pos = 0
    hunks = re.finditer(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@.*$", diff_text, re.M)
    diff_lines = diff_text.splitlines(keepends=True)
    line_index = {i: ln for i, ln in enumerate(diff_lines)}
    hunk_starts = [i for i, ln in line_index.items() if ln.startswith("@@")]
    for hi, start in enumerate(hunk_starts):
        header = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", diff_lines[start])
        if not header:
            raise ValueError("malformed hunk header")
        old_start = int(header.group(1)) - 1
        end = hunk_starts[hi + 1] if hi + 1 < len(hunk_starts) else len(diff_lines)
        body = diff_lines[start + 1 : end]
        out.extend(lines[pos:old_start])
        pos = old_start
        for ln in body:
            if ln.startswith("\\"):
                continue
            tag, content = ln[0], ln[1:]
            if tag == " ":
                if pos >= len(lines) or lines[pos] != content:
                    raise ValueError(f"context mismatch at line {pos + 1}")
                out.append(lines[pos])
                pos += 1
            elif tag == "-":
                if pos >= len(lines) or lines[pos] != content:
                    raise ValueError(f"removed line does not match at line {pos + 1}")
                pos += 1
            elif tag == "+":
                out.append(content)
            else:
                raise ValueError(f"unexpected diff line: {ln!r}")
    out.extend(lines[pos:])
    _ = hunks
    return "".join(out)


def substituted_region(result: ScanResult, key: str, with_file: Path) -> str:
    """The key's region text after applying `with_file` (a unified diff against the node's file, or a .tex replacement)."""
    n = result.nodes[key]
    src = result.files[n.file]
    raw = with_file.read_text(encoding="utf-8")
    if with_file.suffix in (".diff", ".patch") or raw.lstrip().startswith(("---", "@@", "diff ")):
        patched = apply_unified_diff(src.text, raw)
    else:
        patched = raw
    return _region_from_text(result, key, patched, n)


def _region_from_text(result: ScanResult, key: str, text: str, n: NodeRec) -> str:
    fake = SourceFile(
        n.file, result.files[n.file].abspath, text, blank_comments(text), "utf-8", False, line_starts(text)
    )
    fe = scan_environments(fake, set(result.taxa))
    wanted = n.labels[0] if n.labels else None
    candidates = fe.theorem_envs if n.kind == "environment" else fe.proofs
    for env in candidates:
        body = fake.clean[env.start : env.end]
        if wanted is None or re.search(r"\\label\s*\{\s*" + re.escape(wanted) + r"\s*\}", body):
            return text[env.start : env.end]
    raise ValueError(f"could not find {key} in the substituted text")


def draft_bundle(result: ScanResult, draft: Path) -> Bundle:
    """A bundle for a node file not yet in the quilt: its \\ref and \\uses targets determine the closure."""
    assert result.graph is not None
    text = draft.read_text(encoding="utf-8")
    labels = re.findall(r"\\(?:ref|eqref|cref|Cref|autoref|uses)\s*\{([^}]*)\}", blank_comments(text))
    deps: list[str] = []
    unknown: list[str] = []
    for group in labels:
        for lab in group.split(","):
            lab = re.sub(r"\s+", " ", lab).strip()
            if not lab:
                continue
            target = result.assembly.labels.get(lab)
            if target is None:
                unknown.append(lab)
                continue
            region = result.assembly.regions.get(target)
            target = region.container if region else target
            target = result.graph.statement_key(target)
            if target not in deps:
                deps.append(target)
    order: list[str] = []
    for d in deps:
        for k in result.graph.closure(d):
            if k not in order:
                order.append(k)
    master = result.default_master or result.masters[0]
    parts = [
        HEADER,
        _preamble(result, master),
        "\\begin{document}\n",
        f"\\section*{{Bundle for draft {draft.name}}}\n\n",
    ]
    for dep in order:
        if dep in result.nodes and result.nodes[dep].kind in ("environment", "section"):
            parts.append(statement_block(result, dep) + "\n")
    parts.append(f"% draft: {draft.name}\n{text}\n\n\\end{{document}}\n")
    return Bundle(f"draft-{draft.stem}", "".join(parts), order, unknown)


def unified_diff(a: str, b: str, path: str) -> str:
    return "".join(
        difflib.unified_diff(
            a.splitlines(keepends=True), b.splitlines(keepends=True), fromfile=f"a/{path}", tofile=f"b/{path}"
        )
    )
