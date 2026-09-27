"""The copy across the border (book 4.4, 17.7): a drafting document made flat, with every label it defines derived, for an agent to edit in `[quilt] drafting_ai`."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from loom.history.ledger import History
from loom.history.steps import FreezePlan, plan_freeze
from loom.reshape.linearize import flatten
from loom.scan.labels import LOOMLOCAL, split_id
from loom.scan.scan import ScanResult

SUFFIX = "-ai"
_LABEL = re.compile(r"(\\label\s*\{\s*)([^}\s]+)(\s*\})")
# every command that names a label: the reference family, \uses, and hyperref's optional argument
_REF = re.compile(r"(\\(?:ref|eqref|cref|Cref|autoref|pageref|vref|Vref|nameref|uses)\*?\s*\{)([^}]*)(\})")
_HYPERREF = re.compile(r"(\\hyperref\s*\[)([^\]]*)(\])")
_SEE = re.compile(r"^([ \t]*%[ \t]*!LOOM[ \t]+see[ \t]*:[ \t]*)([^\n]*)()$", re.M)


@dataclass
class CopyPlan:
    source: str
    dest: str
    text: str  # the copy: flat, every label it defines with the suffix
    source_text: str  # the source flattened, as the copy step records it
    labels: dict[str, str] = field(default_factory=dict)  # label -> its copy's label
    freeze: FreezePlan = field(default_factory=FreezePlan)
    bases: dict[str, dict[str, object]] = field(default_factory=dict)  # derived key -> {key, step, hash}


def derived_key(key: str) -> str | None:
    """The copy's key for a plain key, `zk-0001/proof` -> `zk-0001-ai/proof`; None for a key whose head is no loom-local id."""
    head, sep, rest = key.partition("/")
    parts = split_id(head)
    if parts is None or LOOMLOCAL.match(parts[1]) is None:
        return None
    return head + SUFFIX + sep + rest


def derive_labels(text: str) -> tuple[str, dict[str, str]]:
    """Every label `text` defines given the suffix, and every reference to one of them rewritten.

    Labels are claimed quilt-wide, so an equation's label is suffixed as an id is: the copy defines nothing its source also defines. A reference to a label the copy does not define is left as it is.
    """
    labels = {m.group(2): m.group(2) + SUFFIX for m in _LABEL.finditer(text)}

    def names(m: re.Match[str]) -> str:
        # each name in a comma list replaced where the copy defines it, the separators and spacing kept as written
        parts = re.split(r"(\s*,\s*)", m.group(2))
        out = [
            p if i % 2 else (p[: len(p) - len(p.lstrip())] + labels.get(p.strip(), p.strip()) + p[len(p.rstrip()) :])
            for i, p in enumerate(parts)
        ]
        return m.group(1) + "".join(out) + m.group(3)

    text = _LABEL.sub(lambda m: m.group(1) + labels[m.group(2)] + m.group(3), text)
    text = _REF.sub(names, text)
    text = _HYPERREF.sub(names, text)
    text = _SEE.sub(names, text)
    return text, labels


def plan_copy(result: ScanResult, history: History, source: str, dest: str) -> CopyPlan:
    """What `loom draft SOURCE --ai NAME` writes and records, nothing written yet.

    The step it plans freezes every key the source reaches whose text no step records yet, so every base is a version loom can read back; the base of each derived key is its plain key's version as it stands.
    """
    flat = flatten(result.quilt.root, source)
    text, labels = derive_labels(flat.text)
    freeze = plan_freeze(result, history, document=source, narrow_to=source)
    # a copy records the source, not the quilt: nothing removed or restored elsewhere is its business
    freeze.removed = []
    freeze.restored = [k for k in freeze.restored if k in freeze.current]
    latest = history.latest_versions()
    step = history.next_step()
    bases: dict[str, dict[str, object]] = {}
    for key, h in sorted(freeze.current.items()):
        derived = derived_key(key)
        if derived is None:
            continue
        at = step if key in freeze.froze else latest[key][0]
        bases[derived] = {"key": key, "step": at, "hash": h}
    return CopyPlan(source, dest, text, flat.text, labels, freeze, bases)
