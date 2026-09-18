"""Steps and stamps (book 17.3-17.6): what every key is at a moment, written as one version file per changed key under a numbered directory, and the ledger line last.

`plan_freeze` compares the head against the latest recorded version of each key, so a step holds only what moved; `state_at` in the ledger module puts the picture back together.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loom.history.ledger import Entry, History, append_entry
from loom.history.versions import version_filename
from loom.render.manifest import key_hash, own_text
from loom.scan.hashing import hash_text, sha256
from loom.scan.nodes import NodeRec
from loom.scan.scan import ScanResult


@dataclass
class FreezePlan:
    froze: dict[str, str] = field(
        default_factory=dict
    )  # key -> hash, for keys whose text moved since their last version
    of: dict[str, str] = field(default_factory=dict)  # proof key -> "stmt@N"
    removed: list[str] = field(default_factory=list)
    restored: list[str] = field(default_factory=list)
    reaches: list[str] = field(default_factory=list)
    preamble: str | None = None  # hash, None when unchanged since the last step that recorded one
    preamble_text: str = ""
    texts: dict[str, str] = field(default_factory=dict)  # key -> raw own text, child markers included
    current: dict[str, str] = field(default_factory=dict)  # every versionable key -> its hash now
    skipped: list[str] = field(default_factory=list)  # conflicted keys, which have no text to freeze

    @property
    def unchanged(self) -> int:
        return len(self.current) - len(self.froze)


def versionable(n: NodeRec) -> bool:
    """A statement or proof key with an identity: `rl-0001`, `rl-0001/proof`, `rl-0001/proof/2`, a labelled proof's own id; never a qualified key, a section, or a conflicted placeholder."""
    if n.kind not in ("environment", "proof") or "#" in n.key:
        return False
    if n.kind == "environment":
        return bool(n.id)
    return bool(n.id) or bool(n.of and "#" not in n.of)


def plan_freeze(
    result: ScanResult, history: History, document: str | None = None, narrow_to: str | None = None
) -> FreezePlan:
    """What a step at this moment records. `document` names the canonized document (its keys become `reaches`, its preamble is the one hashed); `narrow_to` restricts a stamp to the keys one document reaches."""
    plan = FreezePlan()
    latest = history.latest_versions()
    live = history.state_at(history.next_step() - 1)
    for key, n in result.nodes.items():
        if n.kind == "conflict":
            plan.skipped.append(key)
            continue
        if not versionable(n):
            continue
        if narrow_to is not None and narrow_to not in n.reached_by:
            continue
        h = key_hash(result, key)
        plan.current[key] = h
        if document is not None and document in n.reached_by:
            plan.reaches.append(key)
        if key in latest and key not in live:
            plan.restored.append(key)
        if latest.get(key, (0, ""))[1] != h:
            plan.froze[key] = h
            plan.texts[key] = own_text(result, n)
    for key in sorted(live):
        if key not in result.nodes or not versionable(result.nodes[key]):
            plan.removed.append(key)
    next_n = history.next_step()
    for key in plan.current:
        n = result.nodes[key]
        if n.kind != "proof" or not n.of:
            continue
        stmt = n.of
        if stmt in plan.froze:
            plan.of[key] = f"{stmt}@{next_n}"
        elif stmt in latest:
            plan.of[key] = f"{stmt}@{latest[stmt][0]}"
    master = document or result.default_master
    closure = result.closures.get(master) if master else None
    plan.preamble_text = closure.raw_text() if closure else ""
    pre_hash = hash_text(plan.preamble_text) if closure else None
    plan.preamble = pre_hash if pre_hash and pre_hash != history.last_preamble() else None
    plan.reaches.sort()
    plan.restored.sort()
    return plan


def infer_parent(history: History, current: dict[str, str], declared: int | None) -> dict[str, Any]:
    """Which step this one continues: declared by the author, else the step whose recorded state shares the most key hashes with the head, else unknown."""
    if declared is not None:
        return {"step": declared, "how": "declared"}
    best: tuple[int, int] | None = None  # (matched, step)
    for e in history.steps():
        n = e.step or 0
        state = history.state_at(n)
        matched = sum(1 for k, h in current.items() if state.get(k, (0, ""))[1] == h)
        if matched and (best is None or matched >= best[0]):
            best = (matched, n)
    if best is None:
        return {"how": "unknown"}
    return {"step": best[1], "how": "inferred", "matched": best[0], "of": len(current)}


_SLUG = re.compile(r"[^a-z0-9]+")


def slug(text: str, limit: int = 40) -> str:
    s = _SLUG.sub("-", text.lower()).strip("-")
    return (s[:limit].rstrip("-") or "step") if s else "step"


def step_dirname(n: int, stem: str) -> str:
    return f"{n:04d}-{stem}"


def write_step(
    history: History,
    action: str,
    stem: str,
    plan: FreezePlan,
    actor: str | None,
    extra: dict[str, Any] | None = None,
    document_text: str | None = None,
    document_name: str | None = None,
) -> Entry:
    """Create `NNNN-<stem>/` with the version files, the preamble when it changed, and the document's copy, then append the ledger line; the line is last so a step that is only half written is never in the record."""
    n = history.next_step()
    dirname = step_dirname(n, stem)
    step_dir = history.dir / dirname
    if step_dir.exists():
        raise FileExistsError(str(step_dir))
    step_dir.mkdir(parents=True)
    for key, text in plan.texts.items():
        (step_dir / version_filename(key)).write_text(text, encoding="utf-8")
    if plan.preamble:
        (step_dir / "preamble.tex").write_text(plan.preamble_text, encoding="utf-8")
    if document_text is not None and document_name:
        (step_dir / document_name).write_text(document_text, encoding="utf-8")
    data: dict[str, Any] = {"step": n, "dir": dirname}
    data.update(extra or {})
    data["froze"] = dict(sorted(plan.froze.items()))
    if plan.of:
        data["of"] = dict(sorted(plan.of.items()))
    if plan.removed:
        data["removed"] = list(plan.removed)
    if plan.restored:
        data["restored"] = list(plan.restored)
    data["preamble"] = plan.preamble
    return append_entry(history.dir, action, data, actor)


def file_hash(path: Path) -> str:
    """sha256 over a file's exact text, so a comment-only edit to a canon document is seen (book 17.15)."""
    return sha256(path.read_text(encoding="utf-8", errors="replace"))


def text_hash(text: str) -> str:
    return sha256(text)
