"""`loom since`: what people did since an agent last looked, read off the records against one marker per agent name.

The marker (`.loom/since/<slug>.json`) is the second the agent last looked, the records that carry that second, the keys stale then and the research state as it read then. A record is new when it is later than the marker, or of the marker's second and not among those it carries, so the clock's one-second resolution neither repeats nor drops one. Nothing here is committed or watched: the marker is this machine's note of where an agent got to, and moving it rebuilds nothing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loom.clock import stamp
from loom.scan.scan import ScanResult

#: Where the markers live, one file per agent name.
MARKERS = Path(".loom") / "since"


@dataclass
class Marker:
    """Where one agent last looked: the second, the records of that second it saw, the keys stale then, and the research state's text then (None where it had none)."""

    when: str
    seen: set[str] = field(default_factory=set)
    stale: set[str] | None = None
    state: str | None = None

    def new(self, when: str, mark: str) -> bool:
        """Whether a record of time `when`, fingerprinted `mark`, came after this marker."""
        return when > self.when or (when == self.when and mark not in self.seen)


@dataclass
class Since:
    """What people did in the window, grouped by kind of record, and the marker that closes it."""

    name: str
    start: str
    first: bool
    annotations: list[dict[str, Any]] = field(default_factory=list)
    acts: list[dict[str, Any]] = field(default_factory=list)
    accepted: list[dict[str, Any]] = field(default_factory=list)
    stale: list[dict[str, Any]] = field(default_factory=list)
    state: list[dict[str, Any]] = field(default_factory=list)
    said: list[dict[str, Any]] = field(default_factory=list)
    marker: Marker | None = None

    @property
    def empty(self) -> bool:
        return not (self.annotations or self.acts or self.accepted or self.stale or self.state or self.said)

    def to_json(self) -> dict[str, Any]:
        return {
            "as": self.name,
            "from": self.start,
            "first": self.first,
            "to": self.marker.when if self.marker else self.start,
            "annotations": self.annotations,
            "acts": self.acts,
            "accepted": self.accepted,
            "stale": self.stale,
            "state": self.state,
            "said": self.said,
        }


def slug(name: str) -> str:
    """An agent name as a file name: lower case, anything but letters, digits, `-` and `_` as `-`."""
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in name.lower()).strip("-") or "reader"


def marker_path(root: Path, name: str) -> Path:
    return root / MARKERS / f"{slug(name)}.json"


def read_marker(root: Path, name: str) -> Marker | None:
    """The agent's marker, or None before its first look (or when the file does not parse, which is the same thing)."""
    try:
        d = json.loads(marker_path(root, name).read_text(encoding="utf-8"))
        stale = d.get("stale")
        return Marker(
            when=str(d["when"]),
            seen={str(s) for s in d.get("seen", [])},
            stale=None if stale is None else {str(k) for k in stale},
            state=d.get("state"),
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def write_marker(root: Path, name: str, marker: Marker) -> None:
    p = marker_path(root, name)
    p.parent.mkdir(parents=True, exist_ok=True)
    d = {
        "as": name,
        "when": marker.when,
        "seen": sorted(marker.seen),
        "stale": sorted(marker.stale or ()),
        "state": marker.state,
    }
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def since(result: ScanResult, name: str) -> Since:
    """What people did since `name` last looked, and the marker that would close the window; nothing is written.

    With no marker the window opens when the active session was last opened, or at the start of the quilt with none. "People" are the records whose kind is human, and for a message or a page write the names `is_agent` does not call an agent.

    Parameters
    ----------
    result : ScanResult
        The quilt, scanned.
    name : str
        The agent, by the name it declared; its marker is its own.

    Returns
    -------
    Since
        The report, with `marker` set to what `write_marker` should store once it has been read.
    """
    from loom.sessions import active, sessions

    root = result.quilt.root
    now = stamp()
    kept = read_marker(root, name)
    if kept is None:
        here = active(root)
        found = sessions(root).get(here) if here else None
        start = found.last_opened if found else ""
        window = Marker(when=start)
    else:
        start, window = kept.when, kept
    out = Since(name=name, start=start, first=kept is None)
    marks: set[str] = set()

    def new(when: str, mark: str) -> bool:
        if when >= now:
            marks.add(mark)
        return window.new(when, mark)

    from loom.records.store import Records

    states = Records(root, result.quilt.history_dir).key_states(result, observe=False)
    stale = {k for k, ks in states.items() if ks.state == "accepted" and not ks.fresh}
    _annotations(root, name, new, out)
    _acceptances(result, window, new, out, states, stale)
    current = _state(result, window, new, out)
    _said(root, new, out)
    out.marker = Marker(when=now, seen=marks, stale=stale, state=current)
    return out


def _annotations(root: Path, name: str, new: Any, out: Since) -> None:
    """A person's annotations and replies, whole, then what a person did to an annotation: resolved, applied, discarded or reopened."""
    from loom.mailbox import annotation_row
    from loom.records.annotations import load_records
    from loom.records.log import log_path

    records, _ = load_records(root)
    by_id = {a.id: (a, r.rel) for r in records for a in r.annotations}
    try:
        lines = log_path(root).read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    made: set[str] = set()
    for line in lines:
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(e, dict):
            continue
        kind, aid, when = str(e.get("event", "")), str(e.get("id", "")), str(e.get("when", ""))
        mark = aid if kind in ("created", "replied") else f"{kind}:{aid}:{when}"
        if not new(when, mark) or e.get("kind") == "agent" or aid not in by_id:
            continue
        a, session = by_id[aid]
        if kind in ("created", "replied"):
            # what a person wrote and settled in one window is reported once, as it stands
            made.add(aid)
            if a.status == "discarded":
                continue
            row = {**annotation_row(root, a), "when": when, "session": session}
            if a.status != "open":
                row["status"] = a.status
            parent = by_id.get(str(a.in_reply_to or ""))
            if parent is not None:
                row["to"] = parent[0].author_id
            if parent is not None and parent[0].author_id == name:
                row["yours"] = True
            out.annotations.append(row)
        elif kind in ("resolved", "discarded") and aid not in made:
            undo = bool(e.get("undo"))
            act = "reopened" if undo else ("applied" if e.get("applied") else kind)
            row = {
                "id": aid,
                "act": act,
                "kind": a.kind,
                "target": a.target_key,
                "of": a.author_id,
                "by": str(e.get("author", "")),
                "when": when,
                "body": str(e.get("body") or ""),
            }
            if a.author_id == name:
                row["yours"] = True
            out.acts.append(row)


def _acceptances(
    result: ScanResult, window: Marker, new: Any, out: Since, states: dict[str, Any], stale: set[str]
) -> None:
    """Each acceptance since, and each accepted key stale now that was not when the agent last looked (every one, on a first look), with why."""
    from loom.cli.review import _cause_words
    from loom.records.ledger import read_ledger

    root = result.quilt.root
    for row in read_ledger(root):
        if new(row.date, f"accept:{row.key}:{row.author}:{row.date}"):
            out.accepted.append({"key": row.key, "by": row.author, "when": row.date, "name": _name(result, row.key)})
    seen = window.stale or set()
    for key in sorted(stale - seen):
        ks = states[key]
        out.stale.append(
            {
                "key": key,
                "name": _name(result, key),
                "accepted": ks.row.date if ks.row else None,
                "why": [_cause_words(c.kind, c.id) for c in ks.causes],
            }
        )


def _state(result: ScanResult, window: Marker, new: Any, out: Since) -> str | None:
    """A person's writes of the research state since, and an edit by hand after the last text loom knew; the page's text now."""
    from loom.cli._common import is_agent
    from loom.pages import read, state_page, text_hash, writes
    from loom.records.snapshots import read_raw
    from loom.reshape.ids import unified_diff

    root, quilt = result.quilt.root, result.quilt
    page = state_page(quilt.config)
    current = read(root, page)
    done = writes(root, quilt.history_dir, page)

    def text(digest: object) -> str | None:
        return read_raw(root, str(digest), quilt.history_dir) if digest else None

    for e in done:
        if is_agent(str(e.actor)) or not new(str(e.when), f"page:{e.when}:{e.get('to')}"):
            continue
        diff = unified_diff(text(e.get("from")) or "", text(e.get("to")) or "", page.path)
        out.state.append({"act": "written", "by": str(e.actor), "when": str(e.when), "diff": diff})
    last = done[-1] if done else None
    # the last text loom knew: what the agent saw when it last looked, unless a write came after that
    if last is not None and (window.state is None or str(last.when) >= window.when):
        known = text(last.get("to"))
    else:
        known = window.state
    if current is not None and known is not None and text_hash(current) != text_hash(known):
        out.state.append({"act": "edited", "by": None, "when": None, "diff": unified_diff(known, current, page.path)})
    elif current is not None and known is None and not done:
        out.state.append({"act": "edited", "by": None, "when": None, "diff": unified_diff("", current, page.path)})
    elif current is None and known is not None:
        out.state.append({"act": "deleted", "by": None, "when": None, "diff": unified_diff(known, "", page.path)})
    return current


def _said(root: Path, new: Any, out: Since) -> None:
    """What a person said in any session's transcript since."""
    from loom.cli._common import is_agent
    from loom.mailbox import read_events
    from loom.sessions import sessions

    for s in sessions(root).values():
        for e in read_events(root, s.id):
            if e.kind != "message" or is_agent(e.who) or not new(e.when, f"said:{s.id}:{e.seq}"):
                continue
            out.said.append(
                {"session": s.id, "seq": e.seq, "by": e.who, "when": e.when, "body": e.body, "carried": len(e.changed)}
            )


def _name(result: ScanResult, key: str) -> str:
    """A key as a reader knows it: its taxon and title, else the key."""
    n = result.nodes.get(key)
    if n is None:
        return key
    return " · ".join(x for x in (n.taxon, n.title) if x) or key
