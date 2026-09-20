"""The history ledger `<history>/ledger.jsonl` (book 17.2, 17.6): one JSON object per line, appended only, never rewritten.

Read once per scan and cached by the file's mtime and size, since a served quilt rescans on every keystroke. Steps (`import`, `canonize`, `stamp`) carry a quilt-wide number and a directory; every other action is a plain line.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loom.clock import stamp
from loom.scan.labels import is_id_shaped

LEDGER = "ledger.jsonl"
TEXTS = "texts"
STEP_ACTIONS = ("import", "canonize", "stamp")
ACTIONS = (*STEP_ACTIONS, "draft", "atomize", "linearize", "fork", "revert", "live")


@dataclass
class Entry:
    line: int  # 1-based line number in the ledger
    action: str
    when: str
    actor: str | None
    data: dict[str, Any] = field(default_factory=dict)  # every other field of the line

    @property
    def step(self) -> int | None:
        s = self.data.get("step")
        return int(s) if self.action in STEP_ACTIONS and isinstance(s, int) else None

    @property
    def dir(self) -> str | None:
        d = self.data.get("dir")
        return str(d) if isinstance(d, str) else None

    @property
    def name(self) -> str:
        """The step's name: its directory without the number, `paper-v1` or `stamp-referee-points`."""
        d = self.dir or ""
        return d.split("-", 1)[1] if "-" in d else d

    @property
    def message(self) -> str:
        return str(self.data.get("message") or "")

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"when": self.when, "actor": self.actor, "action": self.action}
        out.update(self.data)
        return out


@dataclass
class Version:
    key: str
    step: int
    hash: str
    dir: str
    name: str
    of: str | None = None


@dataclass
class History:
    dir: Path
    entries: list[Entry] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def ledger(self) -> Path:
        return self.dir / LEDGER

    @property
    def texts(self) -> Path:
        return self.dir / TEXTS

    @property
    def exists(self) -> bool:
        return bool(self.entries)

    def steps(self) -> list[Entry]:
        return [e for e in self.entries if e.step is not None]

    def step(self, n: int) -> Entry | None:
        for e in self.entries:
            if e.step == n:
                return e
        return None

    def next_step(self) -> int:
        return max((e.step or 0 for e in self.entries), default=0) + 1

    def resolve_step(self, ref: str) -> Entry | None:
        """A step by number (`3`, `0003`), by name (`paper-v2`), or by its directory (`0004-paper-v2`)."""
        ref = ref.strip()
        if ref.isdigit():
            return self.step(int(ref))
        for e in reversed(self.steps()):
            if ref in (e.name, e.dir):
                return e
        return None

    def step_for_path(self, path: str) -> Entry | None:
        """The latest import or canonize step that wrote `path` (a canon document)."""
        for e in reversed(self.steps()):
            to = e.get("to") or {}
            if isinstance(to, dict) and to.get("path") == path:
                return e
        return None

    def superseded_paths(self) -> dict[str, Entry]:
        """Documents a conversion replaced (its `superseded` list), minus those a later `live` line restored; path -> the superseding entry."""
        out: dict[str, Entry] = {}
        for e in self.entries:
            if e.action == "live":
                out.pop(str(e.get("path", "")), None)
                continue
            for p in e.get("superseded") or []:
                out[str(p)] = e
        return out

    def _walk(self) -> tuple[dict[str, tuple[int, str]], dict[str, tuple[int, str]], dict[str, int]]:
        """(state, ever, removed_at) after the last step: the live versions, every key's last version, and the step at which a key was last removed without being restored since."""
        state: dict[str, tuple[int, str]] = {}
        ever: dict[str, tuple[int, str]] = {}
        removed_at: dict[str, int] = {}
        for e in self.steps():
            n = e.step or 0
            for k, h in (e.get("froze") or {}).items():
                state[k] = ever[k] = (n, str(h))
                removed_at.pop(k, None)
            for k in e.get("restored") or []:
                if k in ever:
                    state[k] = ever[k]
                    removed_at.pop(k, None)
            for k in e.get("removed") or []:
                state.pop(k, None)
                removed_at[k] = n
        return state, ever, removed_at

    def latest_versions(self) -> dict[str, tuple[int, str]]:
        """key -> (step, hash) of every key's last recorded version, removed keys included."""
        return self._walk()[1]

    def state_at(self, n: int) -> dict[str, tuple[int, str]]:
        """key -> (step at which its text was frozen, hash) for every key live at step `n`."""
        state: dict[str, tuple[int, str]] = {}
        ever: dict[str, tuple[int, str]] = {}
        for e in self.steps():
            if (e.step or 0) > n:
                break
            for k, h in (e.get("froze") or {}).items():
                state[k] = ever[k] = (e.step or 0, str(h))
            for k in e.get("restored") or []:
                if k in ever:
                    state[k] = ever[k]
            for k in e.get("removed") or []:
                state.pop(k, None)
        return state

    def removed_ids(self) -> dict[str, int]:
        """id -> the step that removed it, for every recorded key whose last event is a removal (book 17.14)."""
        return self._walk()[2]

    def versions_of(self, key: str) -> list[Version]:
        out: list[Version] = []
        for e in self.steps():
            froze = e.get("froze") or {}
            if key in froze:
                of = (e.get("of") or {}).get(key)
                out.append(Version(key, e.step or 0, str(froze[key]), e.dir or "", e.name, of))
        return out

    def recorded_ids(self) -> set[str]:
        """Every id the history has ever named as a key: frozen, removed, restored, or allocated by a fork. Never reused (book 5.3.2, 17.14)."""
        out: set[str] = set()
        for e in self.entries:
            for k in list(e.get("froze") or {}) + list(e.get("removed") or []) + list(e.get("restored") or []):
                out.add(k.split("/", 1)[0])
            if e.action == "fork":
                out.add(str(e.get("new", "")))
        return {i for i in out if is_id_shaped(i)}

    def last_preamble(self) -> str | None:
        for e in reversed(self.steps()):
            p = e.get("preamble")
            if p:
                return str(p)
        return None


_CACHE: dict[str, tuple[tuple[float, int], History]] = {}


def load_history(hist_dir: Path) -> History:
    """The history under `hist_dir`; empty when there is no ledger. A malformed line or a step out of order is a problem, reported and skipped, never a refusal."""
    ledger = hist_dir / LEDGER
    if not ledger.is_file():
        return History(dir=hist_dir)
    st = ledger.stat()
    sig = (st.st_mtime, st.st_size)
    cached = _CACHE.get(str(ledger))
    if cached is not None and cached[0] == sig:
        return cached[1]
    hist = History(dir=hist_dir)
    last_step = 0
    for i, raw in enumerate(ledger.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            hist.problems.append(f"line {i} is not JSON")
            continue
        if not isinstance(data, dict) or not isinstance(data.get("action"), str):
            hist.problems.append(f"line {i} has no action")
            continue
        action = str(data.pop("action"))
        when = str(data.pop("when", "") or "")
        actor = data.pop("actor", None)
        e = Entry(i, action, when, str(actor) if actor is not None else None, data)
        if action in STEP_ACTIONS:
            if not isinstance(data.get("step"), int) or not isinstance(data.get("dir"), str):
                hist.problems.append(f"line {i}: {action} has no step number or directory")
                continue
            if data["step"] <= last_step:
                hist.problems.append(f"line {i}: step {data['step']} does not follow step {last_step}")
                continue
            last_step = data["step"]
        hist.entries.append(e)
    _CACHE[str(ledger)] = (sig, hist)
    return hist


def append_entry(hist_dir: Path, action: str, data: dict[str, Any], actor: str | None) -> Entry:
    """Append one line and return it as an Entry; `when` is the clock's (LOOM_FIXED_TIME honoured)."""
    hist_dir.mkdir(parents=True, exist_ok=True)
    ledger = hist_dir / LEDGER
    when = stamp()
    line: dict[str, Any] = {"when": when, "actor": actor, "action": action}
    line.update(data)
    existing = ledger.read_text(encoding="utf-8") if ledger.is_file() else ""
    n = sum(1 for ln in existing.splitlines() if ln.strip()) + 1
    with ledger.open("a", encoding="utf-8") as fh:
        if existing and not existing.endswith("\n"):
            fh.write("\n")
        fh.write(json.dumps(line, ensure_ascii=False) + "\n")
    _CACHE.pop(str(ledger), None)
    return Entry(n, action, when, actor, dict(data))


def actor_for(root: Path) -> str | None:
    """The author's name for a ledger line, or None: a record of what loom was told never refuses for want of a name."""
    from loom.scan.quilt import NoAuthorError, resolve_author

    try:
        return resolve_author(None, root)[0]
    except NoAuthorError:
        return None
