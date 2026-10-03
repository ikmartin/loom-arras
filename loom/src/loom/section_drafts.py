"""Section scopes and immutable context for AI copies; author source is read only."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from loom.history.ledger import History, load_history
from loom.scan.expand import Expansion, Segment
from loom.scan.labels import LABEL_DEF, derived_of, is_id_shaped, plain_key
from loom.scan.model import SourceFile
from loom.scan.scan import ScanResult
from loom.scan.sections import SectionUnit, body_range, find_sections
from loom.scan.source import blank_comments
from loom.sync import SyncError


def sections(text: str) -> tuple[Expansion, list[SectionUnit]]:
    """Parse section boundaries in an already flattened document, retaining raw offsets."""
    clean = blank_comments(text)
    file = "section-snapshot.tex"
    exp = Expansion(file, clean, [Segment(file, 0, len(clean), 0, 0)])
    src = SourceFile(file, Path(file), text, clean, "utf-8", False)
    return exp, find_sections(exp, {file: src})


def section(text: str, key: str) -> SectionUnit:
    """Find one stable section identity; numeric/title selectors are only creation conveniences."""
    _, units = sections(text)
    found = [u for u in units if key in [plain_key(k) for k in u.labels]]
    if len(found) != 1:
        raise SyncError(f"Section {key} is missing or ambiguous; restore its unique label before continuing")
    return found[0]


def resolve_section(result: ScanResult, source: str, text: str, selector: str) -> dict[str, Any]:
    """Resolve a creation selector and describe its stable subtree."""
    _, units = sections(text)
    found = [u for u in units if selector in u.labels or selector == u.title]
    if not found and selector.isdigit():
        top = [u for u in units if u.name == "section"]
        at = int(selector) - 1
        found = top[at : at + 1] if at >= 0 else []
    if len(found) != 1:
        raise SyncError(f"Section {selector!r} is missing or ambiguous in {source}; name its unique section ID")
    unit = found[0]
    key = next((k for k in unit.labels if is_id_shaped(k) and not derived_of(k)), None)
    if key is None:
        from loom.scan.sections import find_sections as expanded_sections

        matches = [u for u in expanded_sections(result.expansions[source], result.files) if u.title == unit.title]
        location = source
        if len(matches) == 1:
            u = matches[0]
            location = f"{u.file}:{result.files[u.file].line_of(u.offset)}"
        raise SyncError(
            f"{location}: section {unit.title!r} needs a stable Loom ID. `loom id {source}` prints a label patch; inspect and apply the relevant section label, then retry with its ID. The copy command does not edit author source."
        )
    labels = [m[2] for m in LABEL_DEF.finditer(text[unit.exp_start : unit.exp_end])]
    return {"version": 1, "kind": "section", "key": key, "level": unit.level, "title": unit.title, "keys": labels}


def extract(text: str, scope: dict[str, Any], *, proposal: bool = False) -> str:
    """Return the selected section wrapped in its preamble, refusing escaped proposal contents."""
    unit = section(text, scope["key"])
    exp, _ = sections(text)
    start, end = body_range(exp)
    if unit.level != scope["level"]:
        raise SyncError("The draft's root section level changed; restore its level before incorporating")
    if proposal and (text[start : unit.exp_start].strip() or text[unit.exp_end : end].strip()):
        raise SyncError("The AI draft contains material outside its section; keep edits inside the root section")
    return text[:start] + "\n" + text[unit.exp_start : unit.exp_end] + "\\end{document}\n"


def replace_section(document: str, replacement: str, scope: dict[str, Any]) -> str:
    """Substitute a scoped skeleton, preserving all surrounding document bytes."""
    old = section(document, scope["key"])
    new = section(replacement, scope["key"])
    return document[: old.exp_start] + replacement[new.exp_start : new.exp_end] + document[old.exp_end :]


def split_preamble(text: str) -> tuple[str, str]:
    """Split immediately before the document opener; the body retains its exact bytes."""
    m = re.search(r"\\begin\s*\{document\}", blank_comments(text))
    return (text[: m.start()], text[m.start() :]) if m else ("", text)


def metadata(result: ScanResult, copy: str) -> dict[str, Any]:
    """Copy metadata followed through recorded moves, with the latest synchronized context."""
    history = load_history(result.quilt.history_dir)
    found: dict[str, Any] = {}
    for entry in history.entries:
        path = str(entry.get("to" if entry.action == "copy" else "copy", ""))
        if (history.current_document(path, result.masters) or path) != copy:
            continue
        if entry.action == "copy":
            found = {
                "scope": entry.get("scope") or {"kind": "document"},
                "suffix": entry.get("suffix") or "-ai",
                "context": entry.get("context"),
                "source": entry.get("from"),
            }
        elif entry.action == "refresh" and entry.get("context"):
            found["context"] = entry.get("context")
    return found


def check_overlap(result: ScanResult, source: str, scope: dict[str, Any], *, exclude: str = "") -> None:
    """Refuse active structural overlaps, naming the existing draft and how to close it."""
    from loom.reshape.linearize import flatten

    text = flatten(result.quilt.root, source).text
    target = section(text, scope["key"]) if scope.get("kind") == "section" else None
    history = load_history(result.quilt.history_dir)
    for copy, origin in history.copies(result.masters).items():
        if origin != source or copy == exclude:
            continue
        other = metadata(result, copy).get("scope", {})
        unit = section(text, other["key"]) if other.get("kind") == "section" else None
        if target is None or unit is None or max(target.exp_start, unit.exp_start) < min(target.exp_end, unit.exp_end):
            raise SyncError(
                f"This scope overlaps {copy}; close that draft with `loom ai close {copy}` before continuing"
            )


def next_suffix(history: History) -> str:
    """Allocate a namespace never reused by any copy in this quilt's history."""
    from loom.scan.labels import base36_decode, base36_encode

    used = [str(e.get("suffix", "")) for e in history.entries if e.action == "copy"]
    indexes = [base36_decode(s[4:]) for s in used if re.fullmatch(r"-ai-[0-9A-Z]+", s)]
    return "-ai-" + base36_encode(max(indexes, default=0) + 1, 2)


def capture_context(result: ScanResult, source: str) -> dict[str, Any]:
    """Freeze local context bytes in a content-addressed history directory."""
    from loom.clock import stamp
    from loom.reshape.linearize import flatten

    root = result.quilt.root
    files: dict[str, bytes] = {}
    # Local assets may be read through author macros; preserve quilt-local inputs conservatively.
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if any(
            p
            in {"build", ".git", ".loom", "node_modules", ".venv", "notes", "retired", result.quilt.config.drafting_ai}
            for p in rel.parts
        ):
            continue
        if (
            path.is_relative_to(root / result.quilt.config.drafting_ai)
            or path.is_symlink()
            or not path.is_file()
            or path.is_relative_to(result.quilt.history_dir)
        ):
            continue
        if path.suffix.lower() in {
            ".tex",
            ".sty",
            ".cls",
            ".bib",
            ".bst",
            ".png",
            ".jpg",
            ".jpeg",
            ".pdf",
            ".eps",
            ".svg",
            ".def",
            ".clo",
            ".cfg",
        }:
            files[rel.as_posix()] = path.read_bytes()
    hashes = {p: hashlib.sha256(b).hexdigest() for p, b in files.items()}
    digest = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    home = result.quilt.history_dir / "draft-context" / digest
    for name, content in files.items():
        dest = home / name
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
    return {
        "path": str(home.relative_to(root)),
        "hashes": hashes,
        "document": flatten(root, source).text,
        "source": source,
        "when": stamp(),
    }


def context_changed(result: ScanResult, context: dict[str, Any]) -> bool:
    """Whether any recorded context input changed or disappeared."""
    for rel, digest in context.get("hashes", {}).items():
        path = result.quilt.root / rel
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            return True
    return False


def pinned_inputs(result: ScanResult, copy: str) -> ScanResult:
    """Reuse scan metadata while resolving shape-parser support files from saved inputs."""
    from dataclasses import replace

    from loom.scan.quilt import Quilt

    context = metadata(result, copy).get("context")
    return replace(result, quilt=Quilt(result.quilt.root / context["path"], result.quilt.config)) if context else result


def pinned_scan(result: ScanResult, copy: str) -> ScanResult:
    """Scan the draft against its saved local inputs without making that context live."""
    from loom.scan.quilt import Quilt
    from loom.scan.scan import scan

    context = metadata(result, copy).get("context")
    if not context:
        return result
    root = result.quilt.root / context["path"]
    return scan(Quilt(root, result.quilt.config), {copy: (result.quilt.root / copy).read_text()})


def preview_in_paper(result: ScanResult, copy: str) -> dict[str, Any]:
    """Compile the saved full paper with the bounded proposal substituted, leaving author files untouched."""
    import shutil
    import tempfile

    from loom.adopt import _resolve
    from loom.render.publish import write_atomic
    from loom.scan.labels import rename_labels
    from loom.tex.runner import compile_tex

    copy, _ = _resolve(result, copy)
    meta = metadata(result, copy)
    if meta["scope"].get("kind") != "section" or not meta.get("context"):
        raise SyncError("Preview in paper requires a section draft with saved paper context")
    proposal = rename_labels((result.quilt.root / copy).read_text(), plain=True)
    extract(proposal, meta["scope"], proposal=True)
    document = replace_section(meta["context"]["document"], proposal, meta["scope"])
    document = split_preamble(proposal)[0] + split_preamble(document)[1]
    digest = hashlib.sha256((document + meta["context"]["path"]).encode()).hexdigest()
    home = result.quilt.root / "build/draft-previews" / digest
    pdf = home / "paper.pdf"
    if not pdf.is_file():
        with tempfile.TemporaryDirectory(prefix="loom-section-paper-") as temporary:
            stage = Path(temporary)
            shutil.copytree(result.quilt.root / meta["context"]["path"], stage, dirs_exist_ok=True)
            (stage / "paper.tex").write_text(document)
            compiled = compile_tex(stage, "paper.tex", stage / "build", result.quilt.config.engine)
            if not compiled.pdf or not compiled.pdf.is_file() or compiled.errors:
                raise SyncError(
                    "Preview could not compile: " + (compiled.errors[0] if compiled.errors else compiled.first_error)
                )
            write_atomic(pdf, compiled.pdf.read_bytes())
    return {
        "pdf": str(pdf.relative_to(result.quilt.root / "build")),
        "message": "Preview uses the saved paper context and this draft's preamble and section.",
    }


def attach_context(result: ScanResult, manifest: dict[str, Any], files: dict[str, str | bytes]) -> None:
    """Render scoped copies and external references from the same pinned input set."""
    from loom.render.convert import slug
    from loom.render.fragments import FragmentRenderer, RenderPlan
    from loom.scan.macros import to_mathjax

    for master in list(manifest["masters"]):
        copy = master["path"]
        if master.get("scope", {}).get("kind") != "section" or master.get("closed"):
            continue
        meta = metadata(result, copy)
        snap = pinned_scan(result, copy)
        context_source = meta["context"].get("source", meta["source"])
        context_id = "context/paper-" + Path(meta["context"]["path"]).name + "-" + Path(meta["source"]).stem + ".tex"
        renderer = FragmentRenderer(
            RenderPlan(snap, {}, result.quilt.root / "build/cache/svg", result.quilt.root / "build/svg")
        )
        macro_name = "draft:" + copy
        manifest["macros"]["sets"][macro_name] = to_mathjax(snap.closures[copy].macros)
        master.update(macros=macro_name, context_document=context_id)
        local = {k for k, n in snap.nodes.items() if copy in n.reached_by}

        def pin(fragment: str, local: set[str] = local, context_id: str = context_id) -> str:
            def ref(match: re.Match[str]) -> str:
                key = match[1]
                if key in local:
                    return match[0]
                return f'data-context-document="{context_id}" data-context-anchor="{slug(key)}" ' + match[0]

            return re.sub(r'data-target="([^"]+)"', ref, fragment)

        # Preserve annotation marks placed by the ordinary renderer; only the underlying context differs.
        from loom.records.store import Records
        from loom.render.build import _marks_by_node
        from loom.render.marks import place_marks

        marks = _marks_by_node(result, Records(result.quilt.root, result.quilt.history_dir))
        files[master["fragment"]] = pin(
            place_marks(
                renderer.master_fragment(copy),
                [m for k, ms in marks.items() for m in ms if k in local and m.in_doc in (None, copy)],
            )
        )
        for key in local:
            node = manifest["nodes"].get(key)
            if node and key != copy:
                files[node["fragment"]] = pin(
                    place_marks(renderer.node_fragment(key), [m for m in marks.get(key, []) if m.in_doc is None])
                )
                node["draft_macros"] = macro_name
        if any(m["path"] == context_id for m in manifest["masters"]):
            continue
        fragment = "fragments/contexts/" + hashlib.sha256(context_id.encode()).hexdigest() + ".html"
        files[fragment] = renderer.master_fragment(context_source)
        context_macros = "context:" + context_id
        manifest["macros"]["sets"][context_macros] = to_mathjax(snap.closures[context_source].macros)
        manifest["masters"].append(
            {
                "path": context_id,
                "title": "Saved paper context",
                "default": False,
                "fragment": fragment,
                "context_only": True,
                "macros": context_macros,
            }
        )
