"""The copy across the border (book 4.4, 17.7): a drafting document made flat, with every label it defines derived, for an agent to edit in `[quilt] drafting_ai`."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loom.history.ledger import History
from loom.history.steps import FreezePlan, plan_freeze
from loom.reshape.linearize import flatten
from loom.scan.labels import LABEL_DEF, LOOMLOCAL, SUFFIX, rename_labels, split_id
from loom.scan.scan import ScanResult


@dataclass
class CopyPlan:
    source: str
    dest: str
    text: str  # the copy: flat, every label it defines with the suffix
    source_text: str  # the source flattened, as the copy step records it
    labels: dict[str, str] = field(default_factory=dict)  # label -> its copy's label
    scope: dict[str, Any] = field(default_factory=lambda: {"kind": "document"})
    suffix: str = SUFFIX
    freeze: FreezePlan = field(default_factory=FreezePlan)
    bases: dict[str, dict[str, object]] = field(default_factory=dict)  # derived key -> {key, step, hash}


def derived_key(key: str, suffix: str = SUFFIX) -> str | None:
    """The copy's key for a plain key, `zk-0001/proof` -> `zk-0001-ai/proof`; None for a key whose head is no loom-local id."""
    head, sep, rest = key.partition("/")
    parts = split_id(head)
    if parts is None or LOOMLOCAL.match(parts[1]) is None:
        return None
    return head + suffix + sep + rest


def derive_labels(text: str, suffix: str = SUFFIX) -> tuple[str, dict[str, str]]:
    """Every label `text` defines given the suffix, and every reference to one of them rewritten.

    Labels are claimed quilt-wide, so an equation's label is suffixed as an id is: the copy defines nothing its source also defines. A reference to a label the copy does not define is left as it is.
    """
    labels = {m.group(2): m.group(2) + suffix for m in LABEL_DEF.finditer(text)}
    return rename_labels(text, labels), labels


def plan_copy(result: ScanResult, history: History, source: str, dest: str, section: str | None = None) -> CopyPlan:
    """What `loom draft SOURCE --ai NAME` writes and records, nothing written yet.

    The step it plans freezes every key the source reaches whose text no step records yet, so every base is a version loom can read back; the base of each derived key is its plain key's version as it stands.
    """
    flat = flatten(result.quilt.root, source)
    scope: dict[str, Any] = {"kind": "document"}
    suffix = SUFFIX
    if any(e.action == "copy" and e.get("from") == source for e in history.entries):
        from loom.section_drafts import next_suffix

        suffix = next_suffix(history)
    source_text = flat.text
    if section:
        from loom.section_drafts import extract, next_suffix, resolve_section

        scope = resolve_section(result, source, flat.text, section)
        suffix = next_suffix(history)
        source_text = extract(flat.text, scope)
    text, labels = derive_labels(source_text, suffix)
    freeze = plan_freeze(result, history, document=source, narrow_to=source)
    if section:
        heads = set(scope["keys"])
        keep = {k for k in freeze.current if k.split("/")[0] in heads}
        for field_name in ("froze", "of", "texts", "current"):
            setattr(freeze, field_name, {k: v for k, v in getattr(freeze, field_name).items() if k in keep})
        freeze.reaches = [k for k in freeze.reaches if k in keep]
    # a copy records the source, not the quilt: nothing removed or restored elsewhere is its business
    freeze.removed = []
    freeze.restored = [k for k in freeze.restored if k in freeze.current]
    latest = history.latest_versions()
    step = history.next_step()
    bases: dict[str, dict[str, object]] = {}
    for key, h in sorted(freeze.current.items()):
        derived = derived_key(key, suffix)
        if derived is None:
            continue
        at = step if key in freeze.froze else latest[key][0]
        bases[derived] = {"key": key, "step": at, "hash": h}
    return CopyPlan(
        source=source,
        dest=dest,
        text=text,
        source_text=source_text,
        labels=labels,
        scope=scope,
        suffix=suffix,
        freeze=freeze,
        bases=bases,
    )
