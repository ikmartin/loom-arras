"""Quilt discovery, quilt config, user config, and author-name resolution (book 4.1-4.3).

find_quilt walks up from a directory to the nearest config.toml with a [quilt] table. resolve_author applies the order flag, user config, git, refusal; the refusal message is part of the contract and tests check it verbatim.
"""

from __future__ import annotations

import os
import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

NO_AUTHOR_MESSAGE = (
    'no author name: add name = "Your Name" under [author] in ~/.config/loom/config.toml, or pass --author'
)


def no_author_in_quilt(root: Path) -> str:
    """The refusal when the quilt states an `[author]` table with no name: its own config is the one to fill in, never the machine's."""
    return f'no author name: add name = "Your Name" under [author] in {root / "config.toml"}, or pass --author'


CONFIG_KEYS: dict[str, set[str]] = {
    # `history` is the record's directory, documented and never written by init
    "quilt": {"name", "main", "drafting", "canon", "history", "prefix", "engine"},
    "refs": {"fetch", "resolve", "contact"},
    "lint": {"disable"},
    "author": {"name"},
    # `launch`: whether `loom serve` may start the agent `ai/ai-config.toml` names (plan 0.14)
    "ai": {"launch"},
    # `[basis]` names environments, so any key is valid there and each value is checked instead
    "basis": set(),
}


class NoQuiltError(Exception):
    """Raised when no config.toml with a [quilt] table is found walking up from the start directory."""


class NoAuthorError(Exception):
    """Raised when no author name can be resolved; str(exc) is NO_AUTHOR_MESSAGE."""


# the `[quilt]` keys a person may set for every quilt in their user config; the quilt's own value wins (book 4.3)
USER_QUILT_KEYS = ("name", "drafting", "canon", "history")


@dataclass
class QuiltConfig:
    name: str = ""
    main: str = ""
    drafting: str = "drafting"
    canon: str = "canon"
    history: str = ".loom/history"
    prefix: str = "q"
    engine: str = "pdflatex"
    fetch: bool = False
    resolve: bool = False
    contact: str = ""
    author: str = ""  # [author] name: who this quilt's records name (book 4.3)
    author_declared: bool = False  # the quilt states an `[author]` table, even with an empty name
    lint_disable: list[str] = field(default_factory=list)
    basis: dict[str, str] = field(default_factory=dict)  # [basis]: environment name -> basis, over the built-in names
    launch: bool = False  # [ai] launch: whether `loom serve` may start the configured agent for a turn (plan 0.14)
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any], user: dict[str, Any] | None = None) -> QuiltConfig:
        """The config of a quilt from its `config.toml` table, with the user config's `[quilt]` values (USER_QUILT_KEYS only) as defaults under it."""
        cfg = cls()

        def table(name: str) -> dict[str, Any]:
            """A named table, or empty when the file gives that name a scalar (which is warned about below)."""
            value = data.get(name, {})
            return value if isinstance(value, dict) else {}

        for table_name, keys in data.items():
            if not isinstance(keys, dict):
                cfg.warnings.append(f"config.toml: [{table_name}] is not a table; ignored")
                continue
            known = CONFIG_KEYS.get(table_name)
            if known is None:
                cfg.warnings.append(f"config.toml: unknown table [{table_name}]; ignored")
                continue
            for key in keys:
                if key not in known and table_name != "basis":
                    cfg.warnings.append(f"config.toml: unknown key {table_name}.{key}; ignored")
        q = dict(table("quilt"))
        uq = (user or {}).get("quilt", {})
        if isinstance(uq, dict):
            for key in USER_QUILT_KEYS:
                if key in uq and key not in q:
                    q[key] = uq[key]
        cfg.name = str(q.get("name", cfg.name)).strip()
        cfg.drafting = str(q.get("drafting", cfg.drafting)).strip("/") or cfg.drafting
        cfg.canon = str(q.get("canon", cfg.canon)).strip("/") or cfg.canon
        cfg.history = str(q.get("history", cfg.history)).strip("/") or cfg.history
        cfg.main = str(q.get("main", f"{cfg.drafting}/main.tex"))
        cfg.prefix = str(q.get("prefix", cfg.prefix))
        cfg.engine = str(q.get("engine", cfg.engine))
        cfg.fetch = bool(table("refs").get("fetch", False))
        cfg.resolve = bool(table("refs").get("resolve", False))
        cfg.contact = str(table("refs").get("contact", ""))
        cfg.lint_disable = [str(x) for x in table("lint").get("disable", [])]
        cfg.launch = bool(table("ai").get("launch", False))
        from loom.scan.nodes import NAMED_BASES

        for env_name, basis in table("basis").items():
            if basis in NAMED_BASES:
                cfg.basis[str(env_name).lower().replace(" ", "-")] = basis
            else:
                cfg.warnings.append(
                    f"config.toml: basis.{env_name} = {basis!r} is not one of {', '.join(NAMED_BASES)}; ignored"
                )
        cfg.author_declared = isinstance(data.get("author"), dict)
        cfg.author = str(table("author").get("name", "")).strip()
        return cfg


@dataclass
class Quilt:
    root: Path
    config: QuiltConfig

    @property
    def config_path(self) -> Path:
        return self.root / "config.toml"

    @property
    def main_master(self) -> Path:
        return self.root / self.config.main

    @property
    def drafting_dir(self) -> Path:
        return self.root / self.config.drafting

    @property
    def canon_dir(self) -> Path:
        return self.root / self.config.canon

    @property
    def history_dir(self) -> Path:
        return self.root / self.config.history

    @property
    def name(self) -> str:
        """The project's name: `[quilt] name`, else the root directory's."""
        return self.config.name or self.root.name


def is_quilt_root(path: Path) -> bool:
    cfg = path / "config.toml"
    if not cfg.is_file():
        return False
    try:
        data = tomllib.loads(cfg.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return False
    return isinstance(data.get("quilt"), dict)


def find_quilt(start: Path | None = None) -> Quilt:
    """Locate the quilt containing `start` (default: LOOM_QUILT or the current directory)."""
    if start is None:
        env = os.environ.get("LOOM_QUILT")
        start = Path(env).expanduser() if env else Path.cwd()
    start = start.resolve()
    for candidate in [start, *start.parents]:
        if is_quilt_root(candidate):
            return load_quilt(candidate)
    # A `config.toml` that is there and will not parse is a different problem from one that is absent, and saying
    # "no config.toml" about a file the author is looking at sends them hunting for the wrong thing. Found by the
    # reading study, 2026-09-21, after a stray second `[author]` table made a quilt vanish.
    for candidate in [start, *start.parents]:
        cfg = candidate / "config.toml"
        if not cfg.is_file():
            continue
        try:
            tomllib.loads(cfg.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            raise NoQuiltError(f"{cfg} is not valid TOML, so this is not a readable quilt: {exc}") from exc
        except OSError:
            continue
    raise NoQuiltError(f"not inside a quilt: no config.toml with a [quilt] table above {start}")


def load_quilt(root: Path) -> Quilt:
    data = tomllib.loads((root / "config.toml").read_text(encoding="utf-8"))
    return Quilt(root=root, config=QuiltConfig.from_dict(data, load_user_config()))


def user_config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    return (Path(base) if base else Path.home() / ".config") / "loom" / "config.toml"


def load_user_config() -> dict[str, Any]:
    path = user_config_path()
    if not path.is_file():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return {}


def git_user_name(cwd: Path | None = None) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            errors="replace",
            cwd=cwd,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    name = proc.stdout.strip()
    return name or None


def resolve_author(explicit: str | None, cwd: Path | None = None) -> tuple[str, str]:
    """Return (name, source) by the book's order: --author, the quilt's own `[author] name`, the user config, git config; else NoAuthorError.

    A quilt that states an `[author]` table settles the question by itself, empty or not: whoever works in it records that name or is asked for one, rather than the name of whichever machine or agent shell the command happened to run in.
    """
    if explicit:
        return explicit, "--author"
    try:
        quilt = find_quilt(cwd)
    except (NoQuiltError, OSError):
        quilt = None
    if quilt is not None and quilt.config.author_declared:
        if quilt.config.author:
            return quilt.config.author, str(quilt.root / "config.toml")
        raise NoAuthorError(no_author_in_quilt(quilt.root))
    name = load_user_config().get("author", {}).get("name")
    if isinstance(name, str) and name.strip():
        return name.strip(), str(user_config_path())
    git_name = git_user_name(cwd)
    if git_name:
        return git_name, "git config user.name"
    raise NoAuthorError(NO_AUTHOR_MESSAGE)
