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

CONFIG_KEYS: dict[str, set[str]] = {
    "quilt": {"main", "drafts", "prefix", "engine"},
    "refs": {"fetch"},
    "lint": {"disable"},
    "ai": {"agent", "runner"},
}


class NoQuiltError(Exception):
    """Raised when no config.toml with a [quilt] table is found walking up from the start directory."""


class NoAuthorError(Exception):
    """Raised when no author name can be resolved; str(exc) is NO_AUTHOR_MESSAGE."""


@dataclass
class QuiltConfig:
    main: str = "drafts/main.tex"
    drafts: str = "drafts"
    prefix: str = "q"
    engine: str = "pdflatex"
    fetch: bool = False
    lint_disable: list[str] = field(default_factory=list)
    ai_agent: str = ""
    ai_runner: str = ""
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QuiltConfig:
        cfg = cls()
        for table, keys in data.items():
            if not isinstance(keys, dict):
                cfg.warnings.append(f"config.toml: [{table}] is not a table; ignored")
                continue
            known = CONFIG_KEYS.get(table)
            if known is None:
                cfg.warnings.append(f"config.toml: unknown table [{table}]; ignored")
                continue
            for key in keys:
                if key not in known:
                    cfg.warnings.append(f"config.toml: unknown key {table}.{key}; ignored")
        q = data.get("quilt", {})
        cfg.main = str(q.get("main", cfg.main))
        cfg.drafts = str(q.get("drafts", cfg.drafts))
        cfg.prefix = str(q.get("prefix", cfg.prefix))
        cfg.engine = str(q.get("engine", cfg.engine))
        cfg.fetch = bool(data.get("refs", {}).get("fetch", False))
        cfg.lint_disable = [str(x) for x in data.get("lint", {}).get("disable", [])]
        cfg.ai_agent = str(data.get("ai", {}).get("agent", ""))
        cfg.ai_runner = str(data.get("ai", {}).get("runner", ""))
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
    def drafts_dir(self) -> Path:
        return self.root / self.config.drafts


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
    raise NoQuiltError(f"not inside a quilt: no config.toml with a [quilt] table above {start}")


def load_quilt(root: Path) -> Quilt:
    data = tomllib.loads((root / "config.toml").read_text(encoding="utf-8"))
    return Quilt(root=root, config=QuiltConfig.from_dict(data))


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
    """Return (name, source) by the book's order: --author, user config, git config; else NoAuthorError."""
    if explicit:
        return explicit, "--author"
    name = load_user_config().get("author", {}).get("name")
    if isinstance(name, str) and name.strip():
        return name.strip(), str(user_config_path())
    git_name = git_user_name(cwd)
    if git_name:
        return git_name, "git config user.name"
    raise NoAuthorError(NO_AUTHOR_MESSAGE)
