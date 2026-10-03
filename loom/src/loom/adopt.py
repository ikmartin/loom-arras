"""Prepare, inspect and incorporate an AI contribution without accepting mathematics."""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from loom.history.ledger import History, append_entry, load_history
from loom.history.steps import plan_freeze, slug, stamp_document, text_hash, write_step
from loom.render.manifest import own_text
from loom.reshape.linearize import flatten
from loom.scan.hashing import pair_hash
from loom.scan.labels import next_local, plain_key, rename_labels
from loom.scan.quilt import Quilt, resolve_author
from loom.scan.scan import ScanResult, scan
from loom.sync import SyncError

_MARKER = re.compile(r"% !LOOM adopt-node: ([^\n]+)\n")
_INCLUDE = re.compile(r"\\(?:input|include|nest)\s*\{([^}]+)\}")


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _marker(key: str) -> str:
    return f"% !LOOM adopt-node: {key}\n"


def _mapped(key: str, mapping: dict[str, str]) -> str:
    head, separator, tail = key.partition("/")
    return mapping.get(key, mapping.get(head, head) + separator + tail)


def _rename(text: str, mapping: dict[str, str]) -> str:
    text = rename_labels(text, mapping)
    return _MARKER.sub(lambda match: _marker(_mapped(match[1], mapping)), text)


def _history(result: ScanResult) -> History:
    return load_history(result.quilt.history_dir)


def _shape(result: ScanResult, document: str) -> tuple[dict[str, str], dict[str, tuple[str, int, int]], dict[str, str]]:
    """Mask node bodies recursively, retaining independent statement and proof choices."""
    nodes = [n for n in result.nodes.values() if document in n.reached_by and n.kind in ("environment", "proof")]
    spans: dict[str, tuple[str, int, int]] = {}
    for n in nodes:
        text = result.files[n.file].text
        start = n.start
        # Node directives immediately before a statement belong to its proposal.
        while start > 0:
            at = text.rfind("\n", 0, start - 1) + 1
            if not re.fullmatch(r"\s*%\s*!LOOM[^\n]*\n?", text[at:start]):
                break
            start = at
        spans[plain_key(n.key)] = (n.file, start, n.end)
    bodies: dict[str, str] = {}
    skeletons: dict[str, str] = {}
    for file in result.expansions[document].reached:
        if file not in result.files:
            continue
        text = result.files[file].text
        entries = [(k, a, b) for k, (f, a, b) in spans.items() if f == file]

        def mask(
            a: int, b: int, owner: str | None, entries: list[tuple[str, int, int]] = entries, text: str = text
        ) -> str:
            children = [(k, lo, hi) for k, lo, hi in entries if k != owner and a <= lo and hi <= b]
            direct = [
                (k, lo, hi) for k, lo, hi in children if not any(j != k and x <= lo and hi <= y for j, x, y in children)
            ]
            value = text[a:b]
            for key, lo, hi in sorted(direct, key=lambda e: e[1], reverse=True):
                bodies[key] = rename_labels(mask(lo, hi, key), plain=True)
                value = value[: lo - a] + _marker(key) + value[hi - a :]
            return value

        skeletons[file] = rename_labels(mask(0, len(text), None), plain=True)
    return bodies, spans, skeletons


def _flat_shape(result: ScanResult, text: str) -> tuple[dict[str, str], str]:
    with tempfile.TemporaryDirectory(prefix="loom-adopt-shape-") as temporary:
        root = Path(temporary)
        doc = result.quilt.config.drafting + "/adoption-snapshot.tex"
        (root / doc).parent.mkdir(parents=True)
        (root / doc).write_text(rename_labels(text, plain=True))
        # Local theorem declarations must remain visible to the scanner: every file a preamble loads, read from disk, since the scan reads a local .sty on demand and never lists it in `files`.
        loaded = {f for c in result.closures.values() for f in c.files if f not in result.masters}
        for name in sorted(loaded | {n for n in result.files if n.endswith(".bib")}):
            source = result.quilt.root / name
            if source.is_file():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(source.read_text())
        snap = scan(Quilt(root, result.quilt.config))
        bodies, _, skeletons = _shape(snap, doc)
        return bodies, skeletons[doc]


def _baseline(result: ScanResult, copy: str) -> dict[str, Any]:
    history = _history(result)
    for entry in reversed(history.entries):
        path = str(entry.get("to" if entry.action == "copy" else "copy", ""))
        if history.current_document(path, result.masters) != copy:
            continue
        if entry.action in ("adopt", "refresh") and entry.get("adoption_base"):
            return dict(entry.get("adoption_base"))
        if entry.action == "copy":
            recorded = history.dir / (entry.dir or "") / Path(str(entry.get("from"))).name
            from loom.section_drafts import pinned_inputs

            bodies, skeleton = _flat_shape(pinned_inputs(result, copy), recorded.read_text())
            return {"nodes": bodies, "document": skeleton, "mapping": {}}
    raise SyncError("This AI draft has no recorded baseline; create it with loom draft DOC --ai NAME")


def _merge(base: str, ours: str, theirs: str) -> tuple[str, bool]:
    if ours == base or ours == theirs:
        return theirs, False
    if theirs == base:
        return ours, False
    with tempfile.TemporaryDirectory(prefix="loom-adopt-merge-") as temporary:
        paths = [Path(temporary) / name for name in ("working", "base", "proposal")]
        for path, text in zip(paths, (ours, base, theirs), strict=True):
            path.write_text(text)
        try:
            run = subprocess.run(["git", "merge-file", "-p", *map(str, paths)], capture_output=True)
        except FileNotFoundError:
            raise SyncError(
                "Merging the document's prose with your edits needs the git program, which is not installed; install git (loom doctor checks for it)"
            ) from None
        # git merge-file exits with the number of conflicts, capped at 127, and negative (255 to a shell) on error
        if not 0 <= run.returncode <= 127:
            raise SyncError(run.stderr.decode() or "Document merge failed")
        return run.stdout.decode(), run.returncode != 0


def _resolve(result: ScanResult, copy: str) -> tuple[str, str]:
    if copy not in result.masters:
        matches = [m for m in result.masters if Path(m).name == copy or Path(m).stem == copy]
        if len(matches) == 1:
            copy = matches[0]
    if result.document_role(copy) != "drafting-ai":
        raise SyncError("Adoption requires a live AI draft")
    source = _history(result).copy_of(copy, result.masters)
    if not source:
        # a document written straight into the directory has no copy step, so no source and no bases (loom:agent-document-not-a-copy)
        raise SyncError(
            f"{copy} is not a copy: no copy step made it, so it has no working document to be incorporated into or updated from; an AI draft starts as `loom draft DOC --ai NAME`"
        )
    if result.document_role(source) != "drafting":
        raise SyncError("The original working document is unavailable; restore it before incorporating")
    return copy, source


def comparison(result: ScanResult, copy: str) -> dict[str, Any]:
    """Describe a contribution without changing source or acceptance records.

    Parameters
    ----------
    result : ScanResult
        Current quilt scan.
    copy : str
        AI document path, filename or unique stem.

    Returns
    -------
    dict
        Normalized comparison, baseline and revision fingerprint.
    """
    copy, source = _resolve(result, copy)
    from loom.section_drafts import check_overlap, extract, metadata

    meta = metadata(result, copy)
    scope = meta.get("scope", {"kind": "document"})
    baseline = _baseline(result, copy)
    proposed_text = rename_labels(flatten(result.quilt.root, copy).text, plain=True)
    current_text = flatten(result.quilt.root, source).text
    if scope.get("kind") == "section":
        check_overlap(result, source, scope, exclude=copy)
        proposed_text = extract(proposed_text, scope, proposal=True)
        current_text = extract(current_text, scope)
    from loom.section_drafts import pinned_inputs

    proposed, proposal_document = _flat_shape(pinned_inputs(result, copy), proposed_text)
    current, current_document = _flat_shape(result, current_text)
    mapping = baseline.get("mapping", {})
    if mapping:
        proposed = {_mapped(k, mapping): _rename(v, mapping) for k, v in proposed.items()}
        proposal_document = _rename(proposal_document, mapping)
    changes = []
    for key in sorted(set(baseline["nodes"]) | set(proposed) | set(current)):
        base, ours, theirs = (baseline["nodes"].get(key), current.get(key), proposed.get(key))
        if ours == theirs:
            kind = "unchanged" if ours == base else "identical"
        elif theirs == base:
            kind = "author-only"
        elif ours == base:
            kind = "removed" if theirs is None else "new" if base is None else "proposal-only"
        else:
            kind = "conflict"
        outside = base is None and key in result.nodes and source not in result.nodes[key].reached_by
        if outside and theirs is not None:
            kind = "separate-result"
        node = result.nodes.get(key)
        changes.append(
            {
                "key": key,
                "class": kind,
                "current": ours or "",
                "proposed": theirs or "",
                "base": base or "",
                "name": (node.directives.get("name") or node.title) if node else key,
                "documents": node.reached_by if node else [],
                "offered": kind not in ("unchanged", "identical", "author-only"),
                "math_changed": pair_hash(ours or "") != pair_hash(theirs or ""),
            }
        )
    from loom.section_drafts import split_preamble

    base_pre, base_body = split_preamble(baseline["document"])
    current_pre, current_body = split_preamble(current_document)
    proposed_pre, proposed_body = split_preamble(proposal_document)
    merged_body, conflict = _merge(base_body, current_body, proposed_body)
    merged_pre, preamble_conflict = _merge(base_pre, current_pre, proposed_pre)
    merged = current_pre + merged_body
    data = {
        "scope": scope,
        "suffix": meta.get("suffix", "-ai"),
        "context": meta.get("context"),
        "preamble_changed": proposed_pre != base_pre and proposed_pre != current_pre,
        "preamble_conflict": preamble_conflict,
        "current_preamble": current_pre,
        "proposed_preamble": proposed_pre,
        "merged_preamble": merged_pre,
        "copy": copy,
        "source": source,
        "changes": changes,
        "document_changed": proposed_body != base_body and proposed_body != current_body,
        "document_conflict": conflict,
        "current_document": current_document,
        "proposed_document": proposal_document,
        "merged_document": merged,
        "baseline": baseline,
    }
    # Pin every scanned source, config and ledger: edits to dependencies or allocation inputs invalidate previews too.
    data["fingerprint"] = _digest(
        {
            "files": {k: v.text for k, v in result.files.items()},
            "config": (result.quilt.root / "config.toml").read_text(),
            "history": [e.to_dict() for e in _history(result).entries],
            "comparison": data,
            "preambles": {name: closure.raw_text() for name, closure in result.closures.items()},
            "context_inputs": {
                name: hashlib.sha256((result.quilt.root / name).read_bytes()).hexdigest()
                if (result.quilt.root / name).is_file()
                else None
                for name in (meta.get("context") or {}).get("hashes", {})
                if not name.endswith(".tex")
            },
        }
    )
    return data


def _expand(text: str, bodies: dict[str, str], stack: tuple[str, ...] = ()) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match[1]
        if key not in bodies:
            raise SyncError(f"{key} is missing: select its proposal or revise the document-level changes")
        if key in stack:
            raise SyncError(f"{key} has a cyclic node placement")
        return _expand(bodies[key], bodies, (*stack, key))

    return _MARKER.sub(replace, text)


def _project(result: ScanResult, source: str, bodies: dict[str, str], document: str) -> dict[str, str]:
    """Restore source inclusions; merge edits crossing file boundaries require explicit reconciliation."""
    old_bodies, _, skeletons = _shape(result, source)
    root = result.quilt.root
    atomic: dict[str, str] = {}
    for file, text in skeletons.items():
        matches = list(_MARKER.finditer(text))
        if file != source and matches and not _MARKER.sub("", text).strip():
            atomic[file] = text
    representations: dict[str, str] = {}

    # An atomic file can contain a statement and its proofs; preserve the original inclusion as a unit.
    def flatten_spine(
        file: str, stack: tuple[str, ...] = (), preserve_atomic: bool = False
    ) -> tuple[str, list[tuple[str, int]]]:
        text = skeletons[file]
        out = ""
        locations: list[tuple[str, int]] = []
        at = 0
        for match in _INCLUDE.finditer(text):
            child = match[1] if match[1].endswith(".tex") else match[1] + ".tex"
            if child not in skeletons or child in stack:
                continue
            out += text[at : match.start()]
            locations.extend((file, i) for i in range(at, match.start()))
            if child in atomic and preserve_atomic:
                part = match[0]
                out += part
                locations.extend((file, i) for i in range(match.start(), match.end()))
            elif child in atomic:
                part = atomic[child]
                representations[part] = match[0]
                out += part
                locations.extend((file, match.start()) for _ in part)
            else:
                part, locs = flatten_spine(child, (*stack, file), preserve_atomic)
                out += part
                locations.extend(locs)
            at = match.end()
        out += text[at:]
        locations.extend((file, i) for i in range(at, len(text)))
        return out, locations

    spine, locations = flatten_spine(source)
    # The scanner's flat form may contain harmless inclusion newlines. Match its whitespace using a three-way merge.
    flat_spine = flatten(root, source, overlay=skeletons).text
    target, conflict = _merge(flat_spine, spine, document)
    if conflict:
        raise SyncError(
            "Document structure conflicts with source inclusions; reconcile the working document and refresh the comparison"
        )
    for part, inclusion in sorted(representations.items(), key=lambda row: len(row[0]), reverse=True):
        if part in target:
            target = target.replace(part, inclusion)
    current_spine, locations = flatten_spine(source, preserve_atomic=True)
    edits: dict[str, list[tuple[int, int, str]]] = {}
    for kind, lo, hi, start, end in difflib.SequenceMatcher(None, current_spine, target, autojunk=False).get_opcodes():
        if kind == "equal":
            continue
        covered = locations[lo:hi]
        if covered:
            file, at = covered[0]
            if covered != [(file, at + i) for i in range(len(covered))]:
                raise SyncError(
                    "Prose changes cross an inclusion boundary; reconcile the working files and refresh Incoming"
                )
            stop = covered[-1][1] + 1
        elif lo < len(locations):
            file, at = locations[lo]
            stop = at
        else:
            file, at = locations[-1]
            at += 1
            stop = at
        edits.setdefault(file, []).append((at, stop, target[start:end]))
    for file, changes in edits.items():
        for lo, hi, text in sorted(changes, reverse=True):
            skeletons[file] = skeletons[file][:lo] + text + skeletons[file][hi:]
    overlay = {}
    for file, skeleton in skeletons.items():
        # Removing an inclusion never erases its reusable node file.
        local_bodies = {**old_bodies, **bodies} if file in atomic else bodies
        rendered = _expand(skeleton, local_bodies)
        if rendered != result.files[file].text:
            overlay[file] = rendered
    return overlay


def _not_offered(unknown: list[str], data: dict[str, Any], offered: dict[str, Any]) -> str:
    """The refusal of keys that name no change, with what the copy does offer and the command that lists it.

    A `.tex` name among the keys is a reader asking adoption to write a new document, which it never does, so that case says where the changes go instead.
    """
    copy, source = Path(data["copy"]).name, data["source"]
    lines = [f"{', '.join(unknown)}: not a result with a change in {copy}"]
    if any(k.endswith(".tex") for k in unknown):
        lines.append(
            f"Adoption revises {source}, the document {copy} was copied from; it never writes another document. Name results by key, or name none to take every change."
        )
    shown = sorted(offered)[:8]
    if shown:
        lines.append(
            f"Changed results: {', '.join(shown)}"
            + (f" and {len(offered) - len(shown)} more" if len(offered) > len(shown) else "")
        )
    lines.append(f"Run `loom adopt {copy}` to see every change.")
    return "\n".join(lines)


def prepare(
    result: ScanResult,
    copy: str,
    keys: list[str] | None = None,
    document: bool = False,
    reviewer: str | None = None,
    *,
    data: dict[str, Any] | None = None,
    preamble: bool | None = None,
) -> dict[str, Any]:
    """Pin the exact selected patch for inspection before any author-file write.

    Parameters
    ----------
    result : ScanResult
        Current quilt scan.
    copy : str
        AI document path or unique name.
    keys : list of str, optional
        Canonical node keys to use; None selects all offered nodes.
    document : bool, default False
        Include proposed prose, preamble and ordering.
    reviewer : str, optional
        Reviewer identity; defaults to the local author.

    Returns
    -------
    dict
        Immutable token, exact patch, paths, selection and baseline updates.
    """
    root = result.quilt.root
    who = resolve_author(reviewer, root)[0]
    data = data if data is not None else comparison(result, copy)
    from loom.section_drafts import replace_section, split_preamble

    if preamble is None:
        preamble = document and data["scope"].get("kind") != "section"
    offered = {row["key"]: row for row in data["changes"] if row["offered"]}
    selected = sorted(offered if keys is None else set(keys))
    unknown = sorted(set(selected) - offered.keys())
    if unknown:
        raise SyncError(_not_offered(unknown, data, offered))
    issues = [
        f"{key}: both versions changed; reconcile the two copies in your editor, run loom ai refresh, and refresh Incoming"
        for key in selected
        if offered[key]["class"] == "conflict"
    ]
    if document and data["document_conflict"]:
        issues.append("Document prose or ordering conflicts; reconcile in your editor and refresh Incoming")
    if preamble and data["preamble_conflict"]:
        issues.append("Preamble changes conflict; reconcile them before including this group")
    if issues:
        raise SyncError("\n".join(issues))
    bodies = {r["key"]: r["current"] for r in data["changes"] if r["current"]}
    new_mapping = dict(data["baseline"].get("mapping", {}))
    from loom.reshape.copy import derived_key
    from loom.reshape.fork import plan_fork
    from loom.scan.alloc import visible_locals

    reserved = visible_locals(result, result.quilt.config.prefix)
    fork_bodies: dict[str, str] = {}
    for key in selected:
        row = offered[key]
        head = key.split("/", 1)[0]
        if row["class"] == "separate-result" and head not in new_mapping:
            target = result.quilt.config.prefix + "-" + next_local(reserved)
            fork = plan_fork(
                result, _history(result), derived_key(head, data["suffix"]) or head, data["copy"], as_id=target
            )
            if fork.refusal:
                raise SyncError(fork.refusal)
            new_mapping[head] = fork.new_id
            reserved.add(target.split("-", 1)[1])
            fork_bodies.update(_flat_shape(result, fork.patched)[0])
        elif row["class"] == "new" and "/" not in key and head not in new_mapping:
            # An identity recorded in history belongs to that old result, even if it is currently absent.
            if head in _history(result).recorded_ids():
                target = result.quilt.config.prefix + "-" + next_local(reserved)
                new_mapping[head] = target
                reserved.add(target.split("-", 1)[1])
    for key in selected:
        row = offered[key]
        target = _mapped(key, new_mapping)
        if row["proposed"]:
            text = fork_bodies.get(target, row["proposed"])
            bodies[target] = _rename(text, new_mapping)
        else:
            bodies.pop(key, None)
    spine = _rename(data["merged_document"] if document else data["current_document"], new_mapping)
    _, chosen_body = split_preamble(spine)
    spine = (data["merged_preamble"] if preamble else data["current_preamble"]) + chosen_body
    for key in selected:
        row = offered[key]
        if not row["proposed"]:
            spine = spine.replace(_marker(key), "")
        elif row["class"] in ("new", "separate-result") and _marker(_mapped(key, new_mapping)) not in spine:
            raise SyncError(
                f"{key} is a new result, and placing it changes the document; run `loom adopt {Path(data['copy']).name} --document-changes`, with the keys you chose"
            )
    for row in data["changes"]:
        if row["key"] in selected and not row["proposed"]:
            bodies = {key: text.replace(_marker(row["key"]), "") for key, text in bodies.items()}
    final_text = _expand(spine, bodies)
    if not preamble and data["preamble_changed"]:
        from loom.scan.macros import parse_macros
        from loom.scan.source import blank_comments

        added = set(parse_macros(blank_comments(data["proposed_preamble"]))) - set(
            parse_macros(blank_comments(data["current_preamble"]))
        )
        used = set(re.findall(r"\\([A-Za-z@]+)", split_preamble(final_text)[1]))
        missing = sorted(added & used)
        if missing:
            raise SyncError(
                "Selected edits need proposed preamble definitions: "
                + ", ".join("\\" + name for name in missing)
                + ". Include Preamble changes or revise the edits."
            )
    final_bodies, _ = _flat_shape(result, final_text)
    for row in data["changes"]:
        if row["key"] not in selected and row["current"] and row["key"] not in final_bodies:
            raise SyncError(f"Document changes would remove kept result {row['key']}; revise the selection or document")
    for key in selected:
        target = _mapped(key, new_mapping)
        if offered[key]["proposed"] and target not in final_bodies:
            raise SyncError(f"{key} has no placement in the selected document")
    projection_bodies = bodies
    projection_spine = spine
    if data["scope"].get("kind") == "section":
        all_bodies, _, full_skeletons = _shape(result, data["source"])
        full_spine = flatten(root, data["source"], overlay=full_skeletons).text
        outside = {k: v for k, v in all_bodies.items() if k not in {r["key"] for r in data["changes"]}}
        projection_bodies = {**outside, **bodies}
        projection_spine = replace_section(full_spine, spine, data["scope"]) if document else full_spine
        _, full_body = split_preamble(projection_spine)
        projection_spine = split_preamble(spine)[0] + full_body
    overlay = _project(result, data["source"], projection_bodies, projection_spine)
    after = scan(result.quilt, overlay=overlay)
    before_errors = {(d.code, d.message) for d in result.diagnostics + result.lint if d.severity == "error"}
    errors = [
        d.message
        for d in after.diagnostics + after.lint
        if d.severity == "error" and (d.code, d.message) not in before_errors
    ]
    # References to an unselected new proposal are never satisfied by the AI workspace.
    for edge in after.edges.edges:
        if edge.file in overlay and edge.to not in after.nodes and edge.to not in after.assembly.regions:
            errors.append(f"Unresolved dependency {edge.label}; include its proposal or revise the selection")
    if errors:
        raise SyncError("\n".join(dict.fromkeys(errors)))
    paths = sorted(overlay)
    patch = "".join(
        "".join(
            difflib.unified_diff(
                result.files[path].text.splitlines(True),
                text.splitlines(True),
                fromfile="a/" + path,
                tofile="b/" + path,
            )
        )
        for path, text in sorted(overlay.items())
    )
    moved = json.loads(json.dumps(data["baseline"]))
    for row in data["changes"]:
        if row["key"] in selected or row["class"] == "identical":
            key = _mapped(row["key"], new_mapping)
            moved["nodes"].pop(row["key"], None)
            if row["proposed"]:
                moved["nodes"][key] = bodies[key]
    base_pre, base_body = split_preamble(moved["document"])
    proposed_pre, proposed_body = split_preamble(data["proposed_document"])
    moved["document"] = _rename(
        (proposed_pre if preamble else base_pre) + (proposed_body if document else base_body), new_mapping
    )
    moved["mapping"] = new_mapping
    prepared = {
        "copy": data["copy"],
        "source": data["source"],
        "fingerprint": data["fingerprint"],
        "proposal_hash": _digest((root / data["copy"]).read_text()),
        "reviewer": who,
        "keys": selected,
        "document": document,
        "preamble": preamble,
        "patch": patch,
        "paths": paths,
        "overlay": overlay,
        "adoption_base": moved,
    }
    prepared["decision"] = decisions(result, copy, who, data=data)
    prepared["token"] = _digest(prepared)
    home = root / "build/adoption"
    home.mkdir(parents=True, exist_ok=True)
    (home / (prepared["token"] + ".json")).write_text(json.dumps(prepared, indent=2) + "\n")
    return prepared


def incorporate(result: ScanResult, copy: str, token: str, reviewer: str | None = None) -> dict[str, Any]:
    """Apply a saved, current preview and record its source and provenance together.

    Parameters
    ----------
    result : ScanResult
        Current quilt scan.
    copy : str
        AI document path or unique name.
    token : str
        Immutable token from an inspected preview.
    reviewer : str, optional
        Reviewer identity; must match the preview.

    Returns
    -------
    dict
        Incorporated paths, the adopt step, and the landmark keeping the document as it was; or a no-change result.
    """
    if not re.fullmatch("[0-9a-f]{64}", token):
        raise SyncError("Invalid preview token")
    root = result.quilt.root
    path = root / "build/adoption" / (token + ".json")
    if not path.is_file():
        raise SyncError("Preview unavailable; inspect the contribution again")
    saved = json.loads(path.read_text())
    supplied = saved.pop("token")
    if supplied != token or _digest(saved) != token:
        raise SyncError("Preview changed; inspect the contribution again")
    data = comparison(result, copy)
    who = resolve_author(reviewer, root)[0]
    if data["copy"] != saved["copy"] or data["fingerprint"] != saved["fingerprint"] or who != saved["reviewer"]:
        if who != saved["reviewer"]:
            raise SyncError("Reviewer changed; refresh Incoming and preview again")
        if saved.get("proposal_hash") != _digest((root / data["copy"]).read_text()):
            raise SyncError("The AI draft changed; preview again")
        raise SyncError("The paper or its context changed since this preview; preview again")
    if saved.get("decision") != decisions(result, copy, who, data=data):
        raise SyncError("Selection changed; preview the selected changes again")
    checked = prepare(result, copy, saved["keys"], saved["document"], who, data=data, preamble=saved.get("preamble"))
    if checked["overlay"] != saved["overlay"] or checked["adoption_base"] != saved["adoption_base"]:
        raise SyncError("Result identities or dependencies changed; inspect a fresh preview")
    if not saved["patch"]:
        return {"paths": [], "message": "No changes to incorporate"}
    from loom.records.store import Records
    from loom.review_origins import read, write
    from loom.review_queue import fingerprint

    history = _history(result)
    for rel in saved["paths"]:
        if rel not in result.files and (root / rel).exists():
            raise SyncError(f"{rel} appeared after the preview; inspect the contribution again")
    # Everything incorporation may write, as it was: restored byte for byte if any step fails.
    touched_files = [
        root / ".loom/review-origins.json",
        history.dir / "ledger.jsonl",
        *(root / p for p in saved["paths"]),
    ]
    snapshots = {p: p.read_bytes() if p.exists() else None for p in touched_files}
    kept_entries = {p.name for p in history.dir.iterdir()} if history.dir.is_dir() else set()
    source_stem = Path(data["source"]).stem
    landmark = base = slug(f"{source_stem} before adopt {Path(data['copy']).stem}", limit=120)
    suffix = 2
    while history.landmark(landmark) is not None:
        landmark, suffix = f"{base}-{suffix}", suffix + 1

    def finish() -> dict[str, Any]:
        history = _history(result)  # re-read: the landmark's stamp step is now the latest
        after = scan(result.quilt)
        freeze = plan_freeze(after, history, document=data["source"], narrow_to=data["source"])
        freeze.removed = []
        touched = {
            key
            for key in freeze.current
            if key not in result.nodes or own_text(after, after.nodes[key]) != own_text(result, result.nodes[key])
        }
        # A changed proof must retain the exact statement version it proves,
        # including a prior author edit not yet captured in node history.
        touched.update(
            after.nodes[key].of
            for key in list(touched)
            if after.nodes[key].kind == "proof" and after.nodes[key].of in freeze.froze
        )
        freeze.froze = {key: value for key, value in freeze.froze.items() if key in touched}
        freeze.texts = {key: value for key, value in freeze.texts.items() if key in touched}
        freeze.restored = [key for key in freeze.restored if key in touched]
        freeze.of = {key: value for key, value in freeze.of.items() if key in freeze.froze}
        extra = {
            "copy": data["copy"],
            "taken": saved["keys"],
            "kept": [r["key"] for r in data["changes"] if r["offered"] and r["key"] not in saved["keys"]],
            "adoption_base": saved["adoption_base"],
            "preview": token,
            "proposal_fingerprint": data["fingerprint"],
            "proposal": {"path": "proposal.tex", "hash": text_hash(flatten(root, data["copy"]).text)},
        }
        from loom.reshape.copy import derived_key

        bases = {}
        mapping = saved["adoption_base"].get("mapping", {})
        inverse = {value: key for key, value in mapping.items()}
        for chosen in saved["keys"]:
            key = _mapped(chosen, mapping)
            if key not in freeze.current:
                continue
            original = _mapped(key, inverse)
            derived = derived_key(original, data["suffix"])
            if derived:
                latest = history.latest_versions().get(key)
                bases[derived] = {
                    "key": key,
                    "step": history.next_step()
                    if key in freeze.froze
                    else latest[0]
                    if latest
                    else history.next_step(),
                    "hash": freeze.current[key],
                }
        extra["bases"] = bases
        extra["forks"] = {
            key: target
            for key, target in saved["adoption_base"].get("mapping", {}).items()
            if data["baseline"].get("mapping", {}).get(key) != target
        }
        entry = write_step(
            history,
            "adopt",
            "adopt-" + Path(data["copy"]).stem,
            freeze,
            who,
            extra=extra,
            document_text=flatten(root, data["copy"]).text,
            document_name="proposal.tex",
        )
        for old, new in extra["forks"].items():
            if any(row["key"] == old and row["class"] == "separate-result" for row in data["changes"]):
                parent = history.latest_versions().get(old)
                append_entry(
                    history.dir,
                    "fork",
                    {
                        "from": {"id": old, **({"step": parent[0]} if parent else {})},
                        "new": new,
                        "in": data["source"],
                        "via": "adopt",
                    },
                    who,
                )
        origins = read(root)
        changed = {
            k
            for k in after.nodes
            if not after.nodes[k].derived_of
            and k in result.nodes
            and pair_hash(own_text(after, after.nodes[k])) != pair_hash(own_text(result, result.nodes[k]))
        }
        changed |= {
            k
            for k in after.nodes
            if not after.nodes[k].derived_of
            and k not in result.nodes
            and after.nodes[k].kind in ("environment", "proof")
        }
        for key, node in after.nodes.items():
            if node.kind not in ("environment", "proof") or node.derived_of:
                continue
            if (
                key in changed
                or set(Records.closure_hashes(after, key)) & changed
                or (key in result.nodes and fingerprint(after, key) != fingerprint(result, key))
            ):
                previous = origins.get(key, {})
                origins[key] = {
                    "source": f"adopt:{entry.step}",
                    "copy": data["copy"],
                    "label": f"Incoming from AI draft “{Path(data['copy']).stem}”",
                    "changed": key in changed,
                    "baseline": fingerprint(after, key),
                    "local_before": previous.get("local_before", False)
                    or bool(
                        previous.get("baseline")
                        and key in result.nodes
                        and previous["baseline"] != fingerprint(result, key)
                    ),
                }
        write(root, origins)
        return {
            "paths": saved["paths"],
            "step": entry.step,
            "landmark": landmark,
            "copy": data["copy"],
            "message": f"Changes incorporated; {source_stem} as it was is landmark {landmark}; mathematics remains to be reviewed",
        }

    try:
        stamp_document(
            result, history, data["source"], landmark, f"{data['source']} before adopting {data['copy']}", who
        )
        for rel, text in saved["overlay"].items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        return finish()
    except Exception as exc:
        import shutil

        for file, content in snapshots.items():
            if content is None:
                file.unlink(missing_ok=True)
            else:
                file.write_bytes(content)
        for made in (e for e in history.dir.iterdir() if e.name not in kept_entries and e.is_dir()):
            shutil.rmtree(made)
        if isinstance(exc, ValueError):
            raise SyncError(str(exc)) from exc
        raise


def refresh(result: ScanResult, copy: str) -> dict[str, Any]:
    """Update only an AI copy from its working source, retaining unresolved proposals.

    Parameters
    ----------
    result : ScanResult
        Current quilt scan.
    copy : str
        AI document path or unique name.

    Returns
    -------
    dict
        Updated keys, unresolved conflicts and a readable result.
    """
    from loom.reshape.copy import derive_labels

    data = comparison(result, copy)
    bodies = {r["key"]: r["proposed"] for r in data["changes"] if r["proposed"]}
    baseline = json.loads(json.dumps(data["baseline"]))
    conflicts = []
    updated = []
    for row in data["changes"]:
        key = row["key"]
        if row["class"] in ("author-only", "identical"):
            if row["current"]:
                bodies[key] = row["current"]
                baseline["nodes"][key] = row["current"]
            else:
                bodies.pop(key, None)
                baseline["nodes"].pop(key, None)
            updated.append(key)
        elif row["class"] == "conflict":
            conflicts.append(key)
    spine, document_conflict = _merge(data["baseline"]["document"], data["proposed_document"], data["current_document"])
    if document_conflict:
        conflicts.append("document prose or ordering")
        spine = data["proposed_document"]
    else:
        baseline["document"] = data["current_document"]
    for row in data["changes"]:
        if row["class"] == "author-only" and not row["current"]:
            spine = spine.replace(_marker(row["key"]), "")
    text = _expand(spine, bodies)
    refreshed, _ = _flat_shape(result, text)
    for key in list(updated):
        if bodies.get(key) and key not in refreshed:
            updated.remove(key)
            if key in data["baseline"]["nodes"]:
                baseline["nodes"][key] = data["baseline"]["nodes"][key]
            else:
                baseline["nodes"].pop(key, None)
            conflicts.append(f"{key}: reconcile document placement")
    # Keep the copy's identities stable when a separate result has been allocated during incorporation.
    reverse = {v: k for k, v in baseline.get("mapping", {}).items()}
    text = rename_labels(text, reverse)
    text, _ = derive_labels(text, data["suffix"])
    path = result.quilt.root / data["copy"]
    if path.is_symlink() or not path.resolve().is_relative_to(result.quilt.drafting_ai_dir.resolve()):
        raise SyncError("AI copy is outside its writable directory")
    original = path.read_text()
    history = _history(result)
    ledger = history.dir / "ledger.jsonl"
    ledger_before = ledger.read_bytes()
    bases = {}
    freeze = plan_freeze(result, history, document=data["source"], narrow_to=data["source"])
    # Refresh is not a source-history step. Exact raw baselines carry unrecorded author versions.
    for derived, base in history.bases(data["copy"], result.masters).items():
        if base["key"] in updated and base["key"] in freeze.current and base["key"] not in freeze.froze:
            bases[derived] = {
                **base,
                "step": history.latest_versions()[base["key"]][0],
                "hash": freeze.current[base["key"]],
            }
    context = data.get("context")
    if data["scope"].get("kind") == "section":
        from loom.section_drafts import capture_context, context_changed

        if not conflicts and (not context or context_changed(result, context)):
            context = capture_context(result, data["source"])
    if text == original and baseline == data["baseline"] and context == data.get("context"):
        return {
            "copy": data["copy"],
            "updated": [],
            "conflicts": conflicts,
            "message": "AI draft is already up to date",
        }
    try:
        temporary = path.with_suffix(".refresh.tmp")
        temporary.write_text(text)
        temporary.replace(path)
        append_entry(
            history.dir,
            "refresh",
            {"copy": data["copy"], "bases": bases, "adoption_base": baseline, "context": context},
            None,
        )
    except Exception:
        path.write_text(original)
        ledger.write_bytes(ledger_before)
        raise
    return {
        "copy": data["copy"],
        "updated": updated,
        "conflicts": conflicts,
        "message": "AI draft updated" if not conflicts else "AI draft partly updated; reconcile the listed conflicts",
    }


def decisions(
    result: ScanResult, copy: str, reviewer: str | None, *, data: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Read this reviewer's choices for the current contribution revision.

    Parameters
    ----------
    result : ScanResult
        Current quilt scan.
    copy : str
        AI document path or unique name.
    reviewer : str or None
        Identity whose pending selection is requested.

    Returns
    -------
    dict
        Current selected keys, document choice and comparison fingerprint.
    """
    data = data if data is not None else comparison(result, copy)
    path = result.quilt.root / ".loom/adoption-decisions.json"
    stored = json.loads(path.read_text()) if path.is_file() else {}
    row = stored.get(reviewer or "", {}).get(data["copy"], {})
    if row.get("fingerprint") == data["fingerprint"]:
        return dict(row)
    signatures = choice_signatures(data)
    previous = row.get("signatures", {})
    valid = {k for k, value in signatures.items() if previous.get(k) == value}
    return {
        "keys": [k for k in row.get("keys", []) if k in valid],
        "kept": [k for k in row.get("kept", []) if k in valid],
        "document": bool(row.get("document") and "document" in valid),
        "preamble": bool(row.get("preamble") and "preamble" in valid),
        "fingerprint": data["fingerprint"],
        "revision": row.get("revision", 0),
        "invalidated": [
            k
            for k in row.get("keys", [])
            + row.get("kept", [])
            + (["document"] if row.get("document") else [])
            + (["preamble"] if row.get("preamble") else [])
            if k not in valid
        ],
    }


def choice_signatures(data: dict[str, Any]) -> dict[str, str]:
    """Inputs deciding whether a saved source choice still has the same meaning."""
    from loom.section_drafts import split_preamble

    signatures = {r["key"]: _digest([r["base"], r["current"], r["proposed"], r["class"]]) for r in data["changes"]}
    parts = [
        split_preamble(t) for t in (data["baseline"]["document"], data["current_document"], data["proposed_document"])
    ]
    signatures["preamble"] = _digest([p[0] for p in parts])
    signatures["document"] = _digest([p[1] for p in parts])
    return signatures


def decide(
    result: ScanResult,
    copy: str,
    keys: list[str],
    document: bool,
    expected: str,
    reviewer: str,
    kept: list[str] | None = None,
    *,
    revision: int | None = None,
    preamble: bool = False,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Save explicit choices against the displayed contribution, without incorporating it.

    Parameters
    ----------
    result : ScanResult
        Current quilt scan.
    copy : str
        AI document path or unique name.
    keys : list of str
        Selected canonical node keys.
    document : bool
        Whether to include document-level changes.
    expected : str
        Fingerprint of the displayed comparison.
    reviewer : str
        Identity making the selection.

    Returns
    -------
    dict
        Persisted selection for this comparison.
    """
    data = data if data is not None else comparison(result, copy)
    if expected != data["fingerprint"]:
        raise SyncError("Contribution changed; refresh Incoming before selecting changes")
    offered = {r["key"] for r in data["changes"] if r["offered"]}
    if set(keys) - offered or set(kept or []) - {r["key"] for r in data["changes"]}:
        raise SyncError("Selection contains an unavailable proposal")
    previous = decisions(result, copy, reviewer, data=data)
    if revision is not None and revision != previous.get("revision", 0):
        raise SyncError("Your selected changes changed in another tab; reload Incoming")
    row = {
        "revision": previous.get("revision", 0) + 1,
        "preamble": preamble,
        "signatures": choice_signatures(data),
        "fingerprint": expected,
        "keys": sorted(set(keys)),
        "document": document,
        "kept": sorted(set(kept or []) - set(keys)),
    }
    path = result.quilt.root / ".loom/adoption-decisions.json"
    stored = json.loads(path.read_text()) if path.is_file() else {}
    stored.setdefault(reviewer, {})[data["copy"]] = row
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(stored, indent=2) + "\n")
    temporary.replace(path)
    return row
