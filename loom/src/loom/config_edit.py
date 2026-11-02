"""Editing a quilt's `config.toml` line by line, so the person's comments, order and spacing survive.

The file is the person's and committed, so loom changes only the lines it was asked to: a key's value in place, a commented template line (`# main = "…"`) made active, a new line at the end of its table, or a new table at the end of the file. Every edit is checked by parsing the result and comparing it with what was asked for; a layout loom cannot edit that way (a dotted key, an inline table) is refused rather than rewritten.
"""

from __future__ import annotations

import copy
import json
import os
import re
import tempfile
import tomllib
from collections.abc import Callable, Collection
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loom.scan.quilt import Quilt, QuiltConfig, load_user_config

if TYPE_CHECKING:
    from loom.scan.scan import ScanResult

Value = str | bool | list[str]

#: The keys the viewer's Settings may change, in the order its pages show them.
EDITABLE = (
    "quilt.name",
    "quilt.prefix",
    "quilt.engine",
    "quilt.main",
    "quilt.home",
    "library.online",
    "library.contact",
    "lint.disable",
    "agents.deny",
)

#: Keys shown and never written: each names where files already are, so changing it alone would lose them.
READ_ONLY = ("quilt.history", "quilt.research_state")

_HEADER = re.compile(r"^[ \t]*\[[ \t]*([A-Za-z0-9_-]+)[ \t]*\][ \t]*(?:#.*)?$")
_KEY = re.compile(r'^([ \t]*)(#[ \t]*)?([A-Za-z0-9_-]+|"[^"\\\n]*")[ \t]*=[ \t]*')
_BARE = re.compile(r"[^\s#,\]}]+")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class ConfigRefused(Exception):
    """An edit loom will not make, with the reason for each key it refused; nothing was written."""

    def __init__(self, refused: dict[str, str]) -> None:
        super().__init__("; ".join(f"{k}: {why}" for k, why in refused.items()))
        self.refused = refused


@dataclass
class _Span:
    """One `key = value` line: where it starts, where its value is, and where the line (with any trailing comment) ends."""

    start: int
    value: int
    end: int
    line_end: int
    lead: str  # the text before the value, with a template's `#` taken off


def _string_end(text: str, i: int) -> int:
    """The index past the string that opens at `i`, basic or literal, single- or multi-line."""
    quote = text[i]
    triple = text.startswith(quote * 3, i)
    if triple:
        close = text.find(quote * 3, i + 3)
        if close < 0:
            raise ValueError("unterminated string")
        while text.startswith(quote, close + 3):  # a closing run may hold up to two quotes of the content
            close += 1
        return close + 3
    j = i + 1
    while j < len(text) and text[j] != "\n":
        if quote == '"' and text[j] == "\\":
            j += 2
            continue
        if text[j] == quote:
            return j + 1
        j += 1
    raise ValueError("unterminated string")


def _value_end(text: str, i: int) -> int:
    """The index past the TOML value starting at `i`; arrays and inline tables may run over lines and hold comments."""
    if i >= len(text):
        raise ValueError("no value")
    c = text[i]
    if c in "\"'":
        return _string_end(text, i)
    if c in "[{":
        depth = 0
        j = i
        while j < len(text):
            ch = text[j]
            if ch in "\"'":
                j = _string_end(text, j)
                continue
            if ch == "#":
                nl = text.find("\n", j)
                j = len(text) if nl < 0 else nl
                continue
            if ch in "[{":
                depth += 1
            elif ch in "]}":
                depth -= 1
                if depth == 0:
                    return j + 1
            j += 1
        raise ValueError("unterminated array")
    m = _BARE.match(text, i)
    if not m:
        raise ValueError("no value")
    return m.end()


def _layout(text: str) -> tuple[dict[tuple[str, str], _Span], dict[tuple[str, str], _Span], dict[str, int]]:
    """(active entries, template lines, where each table's header or last key line ends), keyed by (table, key); a comment of no key's belongs to no table, so a new key goes before it."""
    entries: dict[tuple[str, str], _Span] = {}
    templates: dict[tuple[str, str], _Span] = {}
    tail: dict[str, int] = {}
    table = ""
    pos = 0
    while pos < len(text):
        nl = text.find("\n", pos)
        line_end = len(text) if nl < 0 else nl + 1
        line = text[pos:line_end].rstrip("\r\n")
        header = _HEADER.match(line)
        if header:
            table = header.group(1)
            tail[table] = line_end
            pos = line_end
            continue
        m = _KEY.match(line)
        if m:
            try:
                end = _value_end(text, pos + m.end())
            except ValueError:
                end = -1
            commented = bool(m.group(2))
            if end >= 0:
                nl = text.find("\n", end)
                span_end = len(text) if nl < 0 else nl + 1
                rest = text[end:span_end].strip()
                one_line = "\n" not in text[pos:end]
                if (not rest or rest.startswith("#")) and (one_line or not commented):
                    lead = text[pos : pos + m.end()]
                    if commented:
                        lead = m.group(1) + lead[len(m.group(1)) + len(m.group(2)) :]
                    key = (table, m.group(3).strip('"'))
                    (templates if commented else entries).setdefault(
                        key, _Span(pos, pos + m.end(), end, span_end, lead)
                    )
                    tail[table] = span_end
                    pos = span_end
                    continue
        pos = line_end
    return entries, templates, tail


def _toml(value: Value) -> str:
    """`value` as a one-line TOML value: a basic string, a boolean or an array of strings."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    return "[" + ", ".join(_toml(v) for v in value) + "]"


def edit_text(text: str, changes: dict[str, Value | None]) -> str:
    """`text` with each `table.key` set to its value, or its line removed for None; comments and every other line kept.

    The caller checks the result (`set_values` parses it); this only places the lines.
    """
    for dotted, value in changes.items():
        table, key = dotted.split(".", 1)
        entries, templates, tail = _layout(text)
        found = entries.get((table, key))
        if value is None:
            if found:
                text = text[: found.start] + text[found.line_end :]
            continue
        rendered = _toml(value)
        if found:
            text = text[: found.value] + rendered + text[found.end :]
        elif (table, key) in templates:
            t = templates[(table, key)]
            text = text[: t.start] + t.lead + rendered + text[t.end :]
        elif table in tail:
            at = tail[table]
            line = f"{key} = {rendered}\n"
            text = text[:at] + ("" if at == 0 or text[at - 1] == "\n" else "\n") + line + text[at:]
        else:
            body = text.rstrip("\n")
            text = (body + "\n\n" if body else "") + f"[{table}]\n{key} = {rendered}\n"
    return text


def _expected(data: dict[str, Any], changes: dict[str, Value | None]) -> dict[str, Any]:
    out = copy.deepcopy(data)
    for dotted, value in changes.items():
        table, key = dotted.split(".", 1)
        if value is None:
            if isinstance(out.get(table), dict):
                out[table].pop(key, None)
        else:
            out.setdefault(table, {})[key] = value
    return out


def set_values(quilt: Quilt, changes: dict[str, Value | None]) -> QuiltConfig:
    """Write `changes` into the quilt's `config.toml` and return the config it now gives.

    Parameters
    ----------
    quilt : Quilt
        The quilt whose `config.toml` is edited.
    changes : dict
        `"table.key"` -> the new value, or None to remove the key's line. Values are strings, booleans or lists of strings; nothing here checks what a value means (`check` does).

    Returns
    -------
    QuiltConfig
        The config the edited file gives, with the user config under it as `load_quilt` reads it.

    Raises
    ------
    ConfigRefused
        The file is laid out in a way these edits cannot change exactly, or the result would carry a warning the file did not; nothing is written.
    """
    path = quilt.root / "config.toml"
    text = path.read_text(encoding="utf-8")
    before = tomllib.loads(text)
    user = load_user_config()
    for dotted in changes:
        table, _ = dotted.split(".", 1)
        if table in before and not isinstance(before[table], dict):
            raise ConfigRefused({dotted: f"[{table}] is not a table in config.toml; change it there"})
    new = edit_text(text, changes)
    try:
        after = tomllib.loads(new)
    except tomllib.TOMLDecodeError:
        after = None
    if after != _expected(before, changes):
        raise ConfigRefused(
            {k: "config.toml is laid out in a way loom cannot edit line by line; change it there" for k in changes}
        )
    old = set(QuiltConfig.from_dict(before, user).warnings)
    config = QuiltConfig.from_dict(after, user)
    gained = [w for w in config.warnings if w not in old]
    if gained:
        raise ConfigRefused({k: gained[0] for k in changes})
    if new != text:
        _replace(path, new)
    return config


def _replace(path: Path, text: str) -> None:
    """Write `text` to `path` through a temporary file beside it, so a reader never sees half a config."""
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".config.", suffix=".toml")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _text(value: Any, *, required: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError("must be text")
    text = value.strip()
    if _CONTROL.search(text):
        raise ValueError("must be one line, without control characters")
    if required and not text:
        raise ValueError("must not be empty")
    return text


def _texts(value: Any) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ValueError("must be a list of text")
    return list(dict.fromkeys(_text(v) for v in value if v.strip()))


def check(
    key: str,
    value: Any,
    *,
    masters: Collection[str] | None = None,
    shown: Callable[[str], bool] | None = None,
) -> Value | None:
    """`value` as `set_values` writes it for `key`, or ValueError saying why it is refused.

    Parameters
    ----------
    key : str
        One of `EDITABLE`; `READ_ONLY` and unknown keys are refused.
    value : object
        What the viewer sent.
    masters : collection of str, optional
        The person's documents, which `quilt.main` must name; unchecked when None.
    shown : callable, optional
        Whether a quilt-relative file exists and the viewer shows it, which `quilt.home` must; unchecked when None.

    Returns
    -------
    str, bool, list of str, or None
        The value to write; None removes the key, which an empty `main`, `home` or `contact` does.
    """
    from loom.agents import compile_pattern
    from loom.scan.diagnostics import can_disable
    from loom.scan.labels import PREFIX
    from loom.tex.runner import ENGINE_FLAGS

    if key in READ_ONLY:
        raise ValueError("is read-only here: change it in config.toml, and move the files with it")
    if key not in EDITABLE:
        raise ValueError("is not a setting loom changes")
    if key == "quilt.name":
        return _text(value, required=True)
    if key == "quilt.prefix":
        prefix = _text(value, required=True)
        if not PREFIX.match(prefix):
            raise ValueError("must be letters and digits, without hyphens")
        return prefix
    if key == "quilt.engine":
        engine = _text(value, required=True)
        if engine not in ENGINE_FLAGS:
            raise ValueError(f"must be one of {', '.join(ENGINE_FLAGS)}")
        return engine
    if key == "quilt.main":
        main = _text(value).strip("/")
        if main and masters is not None and main not in masters:
            raise ValueError(f"{main} is not one of your documents")
        return main or None
    if key == "quilt.home":
        home = _text(value).strip("/")
        if home and shown is not None and not shown(home):
            raise ValueError(f"{home} is not a file the viewer shows")
        return home or None
    if key == "library.online":
        if not isinstance(value, bool):
            raise ValueError("must be true or false")
        return value
    if key == "library.contact":
        return _text(value) or None
    if key == "lint.disable":
        codes = _texts(value)
        for code in codes:
            if not can_disable(code):
                raise ValueError(f"{code} is not a diagnostic that can be silenced")
        return codes
    entries = _texts(value)
    for entry in entries:
        got = compile_pattern(entry)
        if isinstance(got, str):
            raise ValueError(got)
    return entries


def save(
    quilt: Quilt,
    changes: dict[str, Any],
    *,
    masters: Collection[str] | None = None,
    shown: Callable[[str], bool] | None = None,
) -> QuiltConfig:
    """Check every change, then write them all or none: the viewer's Settings saving to `config.toml`.

    Parameters
    ----------
    quilt : Quilt
        The quilt.
    changes : dict
        `"table.key"` -> the value the viewer sent.
    masters, shown
        As `check` takes them.

    Returns
    -------
    QuiltConfig
        The config the file now gives.

    Raises
    ------
    ConfigRefused
        Naming each refused key and why; nothing is written.
    """
    refused: dict[str, str] = {}
    values: dict[str, Value | None] = {}
    for key, value in changes.items():
        try:
            values[key] = check(key, value, masters=masters, shown=shown)
        except ValueError as exc:
            refused[key] = str(exc)
    if refused:
        raise ConfigRefused(refused)
    return set_values(quilt, values)


def published(result: ScanResult) -> dict[str, Any]:
    """The manifest's `config`: what `config.toml` holds and what follows from it, for the viewer's Settings.

    Commands a person runs reach the viewer here as data (`command`), since the viewer names none of its own. Called once per build.
    """
    from loom.agents import always_protected
    from loom.ai.clients import PROJECT, names_loom
    from loom.ai.layout import SHELL, permissions_stale, variant
    from loom.paths import AI
    from loom.scan.diagnostics import LOOM, can_disable
    from loom.sync import SyncError, SyncState, source_label

    quilt = result.quilt
    root = quilt.root
    cfg = quilt.config
    layer = (root / AI).is_dir()
    way = variant(root)
    clients: list[dict[str, Any]] = []
    for c in PROJECT:
        assert c.file is not None
        path = root / c.file
        text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else None
        set_up = text is not None and names_loom(c, text)
        if set_up:
            command = ""
        elif text is not None:
            command = f"loom ai init --client {c.key}"  # a file of the person's: loom prints the entry to add
        else:
            command = "loom ai init --mcp" if way == SHELL else "loom ai init"
        clients.append({"key": c.key, "label": c.label, "file": c.file, "set_up": set_up, "command": command})
    try:
        state = SyncState.read(root)
        sync: dict[str, Any] = {
            "paired": True,
            "directory": state.directory,
            "workspace": source_label(state.url) if state.url else "",
            "branch": state.branch,
            "documents": list(state.documents),
        }
    except SyncError:
        sync = {"paired": False, "command": "loom sync init DIR"}
    return {
        "editable": list(EDITABLE),
        "read_only": list(READ_ONLY),
        "quilt": {
            "name": cfg.name,
            "main": cfg.main,
            "home": cfg.home,
            "prefix": cfg.prefix,
            "engine": cfg.engine,
            "history": cfg.history,
            "research_state": cfg.research_state,
        },
        "library": {"online": cfg.online, "contact": cfg.contact},
        "lint": {"disable": list(cfg.lint_disable), "codes": sorted(c for c in LOOM if can_disable(c))},
        "agents": {
            "deny": list(cfg.agents_deny),
            "protected": always_protected(cfg),
            "layer": layer,
            "variant": way,
            "stale": permissions_stale(root, cfg),
            "command": "" if layer else "loom ai init",
            "clients": clients,
        },
        "sync": sync,
        "warnings": list(cfg.warnings),
    }
