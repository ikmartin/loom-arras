"""Close and reopen agent documents without deleting text, provenance or annotations."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from loom.history.ledger import History, append_entry, load_history
from loom.scan.scan import ScanResult
from loom.section_drafts import check_overlap, metadata
from loom.sync import SyncError


def closed_drafts(history: History) -> dict[str, dict[str, Any]]:
    """Latest closed state by copy path; reopening removes it without erasing its snapshot."""
    out: dict[str, dict[str, Any]] = {}
    for e in history.entries:
        if e.action == "draft-close":
            out[str(e.get("copy"))] = {**e.to_dict(), "when": e.when}
        elif e.action == "draft-reopen":
            out.pop(str(e.get("copy")), None)
    return out


def resolve_copy(result: ScanResult, given: str, *, closed: bool = False) -> str:
    """Resolve a full path, filename or unique stem among active or closed copies."""
    history = load_history(result.quilt.history_dir)
    pool = closed_drafts(history) if closed else history.copies(result.masters)
    if given in pool:
        return given
    found = [p for p in pool if given in (Path(p).name, Path(p).stem)]
    if len(found) != 1:
        raise SyncError(f"{given} does not name one {'closed' if closed else 'active'} agent document")
    return found[0]


def close_draft(
    result: ScanResult, copy: str, reviewer: str, *, confirmed: bool = False, write: bool = True
) -> dict[str, Any]:
    """Freeze a readable draft and its annotations, then release its active scope."""
    from loom.adopt import comparison
    from loom.render.build import build
    from loom.render.publish import write_atomic

    copy = resolve_copy(result, copy)
    issue = ""
    try:
        data = comparison(result, copy)
        count = (
            sum(r["offered"] for r in data["changes"]) + int(data["document_changed"]) + int(data["preamble_changed"])
        )
    except SyncError as exc:
        count = 1
        issue = str(exc)

    if count and not confirmed:
        return {
            "copy": copy,
            "confirmation_required": True,
            "unapplied": count,
            "message": (
                f"Close this draft with unresolved changes ({issue})?"
                if issue
                else f"Close this draft with {count} unapplied changes?"
            )
            + " Its text and annotations will be kept.",
        }
    if not write:
        return {
            "copy": copy,
            "closed": True,
            "unapplied": count,
            "message": "Would close the agent document, retaining its text and annotations.",
        }
    root = result.quilt.root
    before = (root / copy).read_bytes()
    build(result.quilt)
    manifest = json.loads((root / "build/manifest.json").read_text())
    if (root / copy).read_bytes() != before:
        raise SyncError("The agent document changed while closing; inspect it and close again")
    master = next(m for m in manifest["masters"] if m["path"] == copy)
    keys = {k for k, n in result.nodes.items() if copy in n.reached_by} | {copy}
    annotations = {
        k: a
        for k, a in manifest.get("annotations", {}).items()
        if a.get("target", {}).get("key") in keys or a.get("in") == copy
    }
    # Preserve replies even when they carry a different target.
    while True:
        replies = {k: a for k, a in manifest.get("annotations", {}).items() if a.get("in_reply_to") in annotations}
        if replies.keys() <= annotations.keys():
            break
        annotations.update(replies)
    context = next((m for m in manifest["masters"] if m["path"] == master.get("context_document")), None)
    frozen = {
        "master": master,
        "annotations": annotations,
        "macros": manifest["macros"],
        "keys": sorted(keys),
        "context": context,
    }
    digest = hashlib.sha256(before + json.dumps(frozen, sort_keys=True).encode()).hexdigest()
    home = result.quilt.history_dir / "closed-drafts" / digest
    write_atomic(home / "source.tex", before)
    write_atomic(home / "fragment.html", (root / "build" / master["fragment"]).read_bytes())
    fragments = [(root / "build" / master["fragment"]).read_text()]
    if context:
        context_html = (root / "build" / context["fragment"]).read_text()
        write_atomic(home / "context.html", context_html)
        fragments.append(context_html)
    for fragment in fragments:
        for asset in re.findall(r'(?:src|href)="((?:svg|graphics)/[^"?#]+)"', fragment):
            path = root / "build" / asset
            if path.is_file():
                write_atomic(home / "assets" / asset, path.read_bytes())
    write_atomic(home / "view.json", json.dumps(frozen))
    entry = append_entry(
        result.quilt.history_dir,
        "draft-close",
        {
            "copy": copy,
            "snapshot": str(home.relative_to(root)),
            "hash": hashlib.sha256(before).hexdigest(),
            "unapplied": count,
            "metadata": metadata(result, copy),
        },
        reviewer,
    )
    return {
        "copy": copy,
        "closed": True,
        "when": entry.when,
        "message": "Draft closed. Its text and annotations have been kept.",
    }


def reopen_draft(result: ScanResult, copy: str, reviewer: str, *, write: bool = True) -> dict[str, Any]:
    """Reactivate retained source only when no active scope or identity conflicts."""
    copy = resolve_copy(result, copy, closed=True)
    history = load_history(result.quilt.history_dir)
    record = closed_drafts(history)[copy]
    path = result.quilt.root / copy
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != record["hash"]:
        raise SyncError(
            "The retained draft file was changed or removed while closed; restore its saved source before reopening"
        )
    meta = record["metadata"]
    source = history.current_document(str(meta["source"]), result.masters)
    if not source:
        raise SyncError("The source paper is unavailable; restore it before reopening")
    check_overlap(result, source, meta["scope"])
    # Inspect identities from the saved snapshot without making the draft live.
    from loom.scan.labels import LABEL_DEF

    labels = {m[2] for m in LABEL_DEF.finditer(path.read_text())}
    taken = labels & set(result.assembly.labels)
    if taken:
        raise SyncError(
            f"Draft identities are already active: {', '.join(sorted(taken))}; close the conflicting draft first"
        )
    if not write:
        return {"copy": copy, "closed": False, "message": "Would reopen the retained agent document."}
    append_entry(history.dir, "draft-reopen", {"copy": copy}, reviewer)
    return {"copy": copy, "closed": False, "message": "Draft reopened. Compare its proposals with the current paper."}


def attach_closed(result: ScanResult, manifest: dict[str, Any], files: dict[str, str | bytes]) -> None:
    """Publish frozen views under their original document URLs without live node definitions."""
    for copy, record in closed_drafts(load_history(result.quilt.history_dir)).items():
        home = result.quilt.root / record["snapshot"]
        saved = json.loads((home / "view.json").read_text())
        fragment = f"fragments/closed/{home.name}.html"
        files[fragment] = (home / "fragment.html").read_bytes()
        for asset in (home / "assets").rglob("*"):
            if asset.is_file():
                files[str(asset.relative_to(home / "assets"))] = asset.read_bytes()
        context = saved.get("context")
        if context and not any(m["path"] == context["path"] for m in manifest["masters"]):
            files[context["fragment"]] = (home / "context.html").read_bytes()
            manifest["masters"].append(context)
            manifest["macros"]["sets"][context["macros"]] = saved["macros"]["sets"][context["macros"]]
        macros = saved["macros"]["sets"].get(saved["master"].get("macros", copy), saved["macros"].get("default", []))
        macro_name = "closed:" + home.name
        manifest["macros"]["sets"][macro_name] = macros
        manifest["masters"].append(
            {
                **saved["master"],
                "fragment": fragment,
                "closed": True,
                "closed_at": record["when"],
                "macros": macro_name,
                "closed_annotations": list(saved["annotations"].values()),
                "closed_keys": saved["keys"],
            }
        )
