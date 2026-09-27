"""Whether an agent's copy is stale (book 17.7): what has moved on the person's side since each of its nodes' bases."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loom.history.ledger import History
from loom.history.versions import read_version
from loom.render.manifest import own_text
from loom.reshape.linearize import flatten
from loom.scan.hashing import mathematical_hash, normalize
from loom.scan.scan import ScanResult

_DOCUMENT = re.compile(r"\\begin\s*\{document\}")


@dataclass
class CopyState:
    copy: str
    source: str
    changed: list[str] = field(default_factory=list)  # plain keys whose mathematics moved since their base
    gone: list[str] = field(default_factory=list)  # plain keys the source no longer has
    prose: bool = False  # the text between the source's nodes moved
    preamble: bool = False

    @property
    def stale(self) -> bool:
        return bool(self.changed or self.gone or self.prose or self.preamble)

    def to_dict(self) -> dict[str, Any]:
        return {
            "copy": self.copy,
            "source": self.source,
            "stale": self.stale,
            "changed": self.changed,
            "gone": self.gone,
            "prose": self.prose,
            "preamble": self.preamble,
        }


def _split(text: str) -> tuple[str, str]:
    """(preamble, body) of a flat document."""
    m = _DOCUMENT.search(text)
    return (text[: m.start()], text[m.end() :]) if m else ("", text)


def _between_nodes(body: str, envs: set[str]) -> str:
    """A body with every theorem-like environment, proof and comment line taken out, whitespace normalised: the prose and order around the nodes."""
    names = "|".join(re.escape(e) for e in sorted(envs | {"proof"}, key=len, reverse=True))
    stripped = re.sub(r"\\begin\s*\{(" + names + r")\}.*?\\end\s*\{\1\}", "", body, flags=re.S)
    # a comment line is no prose: a node's directives (`% !LOOM name:`) sit between nodes and change nothing a reader sees
    stripped = re.sub(r"^[ \t]*%[^\n]*\n?", "", stripped, flags=re.M)
    return " ".join(normalize(stripped).split())


def copy_states(result: ScanResult, history: History) -> list[CopyState]:
    """Every live agent copy and what has moved on the person's side since it was based.

    Parameters
    ----------
    result : ScanResult
        A scan of the quilt now.
    history : History
        The quilt's history, which holds each copy's step and bases.

    Returns
    -------
    list of CopyState
        One per live copy, by path. A copy is stale when a node it was based on changed mathematically (a display name alone is no change), left the source, or when the source's prose between nodes or its preamble moved since the copy was made.
    """
    out: list[CopyState] = []
    for copy, source in sorted(history.copies(result.masters).items()):
        state = CopyState(copy, source)
        for base in sorted(history.bases(copy, result.masters).values(), key=lambda b: str(b["key"])):
            key = str(base["key"])
            n = result.nodes.get(key)
            if n is None or source not in n.reached_by:
                state.gone.append(key)
                continue
            try:
                _, then = read_version(history, key, str(base["step"]))
            except LookupError:
                state.changed.append(key)
                continue
            if mathematical_hash(then) != mathematical_hash(own_text(result, n)):
                state.changed.append(key)
        made = next(
            (
                e
                for e in reversed(history.steps())
                if e.action == "copy" and history.current_document(str(e.get("to", "")), result.masters) == copy
            ),
            None,
        )
        if made is not None and source in result.masters:
            # the step keeps the source's flat text under the source's own file name
            recorded = history.dir / (made.dir or "") / Path(str(made.get("from", ""))).name
            then_text = recorded.read_text(encoding="utf-8") if recorded.is_file() else ""
            now_text = flatten(result.quilt.root, source).text
            (then_pre, then_body), (now_pre, now_body) = _split(then_text), _split(now_text)
            state.preamble = normalize(then_pre) != normalize(now_pre)
            envs = set(result.taxa)
            state.prose = _between_nodes(then_body, envs) != _between_nodes(now_body, envs)
        out.append(state)
    return out
