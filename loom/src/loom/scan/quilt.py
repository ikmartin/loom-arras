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
    # `drafts` is the pre-0.9 name of `drafting` and is read as it (DR-132); `history` is the record's directory, documented and never written by init
    "quilt": {"name", "main", "drafting", "drafts", "canon", "history", "prefix", "engine"},
    "refs": {"fetch", "resolve", "contact"},
    "lint": {"disable"},
    "crawl": {"depth", "subjects", "categories", "cap"},
    # `runner` is retired: the runner was declined (docs/work-queue/closed.md, WQ-15). It stays accepted and ignored
    # so that a quilt loom itself wrote the key into does not now report it as unknown; `loom upgrade` removes the line.
    "ai": {"agent", "runner"},
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
    crawl_depth: int = 2
    crawl_subjects: list[str] = field(default_factory=list)
    crawl_categories: list[str] = field(default_factory=list)
    crawl_cap: int = 1000
    lint_disable: list[str] = field(default_factory=list)
    ai_agent: str = ""
    warnings: list[str] = field(default_factory=list)
    deprecations: list[str] = field(
        default_factory=list
    )  # keys loom still reads under their old names (loom:deprecated-config-key)

    @classmethod
    def from_dict(cls, data: dict[str, Any], user: dict[str, Any] | None = None) -> QuiltConfig:
        """The config of a quilt from its `config.toml` table, with the user config's `[quilt]` values (USER_QUILT_KEYS only) as defaults under it."""
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
        q = dict(data.get("quilt", {}))
        uq = (user or {}).get("quilt", {})
        if isinstance(uq, dict):
            for key in USER_QUILT_KEYS:
                if key in uq and key not in q:
                    q[key] = uq[key]
        if "drafts" in q:
            if "drafting" not in q:
                q["drafting"] = q["drafts"]
            cfg.deprecations.append("[quilt] drafts is now drafting; loom upgrade renames the key, nothing is moved")
        cfg.name = str(q.get("name", cfg.name)).strip()
        cfg.drafting = str(q.get("drafting", cfg.drafting)).strip("/") or cfg.drafting
        cfg.canon = str(q.get("canon", cfg.canon)).strip("/") or cfg.canon
        cfg.history = str(q.get("history", cfg.history)).strip("/") or cfg.history
        cfg.main = str(q.get("main", f"{cfg.drafting}/main.tex"))
        cfg.prefix = str(q.get("prefix", cfg.prefix))
        cfg.engine = str(q.get("engine", cfg.engine))
        cfg.fetch = bool(data.get("refs", {}).get("fetch", False))
        cfg.resolve = bool(data.get("refs", {}).get("resolve", False))
        cfg.contact = str(data.get("refs", {}).get("contact", ""))
        crawl = data.get("crawl", {}) if isinstance(data.get("crawl", {}), dict) else {}
        for key, attr in (("depth", "crawl_depth"), ("cap", "crawl_cap")):
            if key in crawl:
                value = crawl[key]
                if isinstance(value, int) and not isinstance(value, bool) and value >= (1 if key == "depth" else 0):
                    setattr(cfg, attr, value)
                else:
                    cfg.warnings.append(
                        f"config.toml: crawl.{key} must be a whole number{' of at least 1' if key == 'depth' else ''}; using {getattr(cfg, attr)}"
                    )
        for key, attr, example in (
            ("subjects", "crawl_subjects", 'MSC families such as ["14N", "14D"]'),
            ("categories", "crawl_categories", 'arXiv categories such as ["math.AG"]'),
        ):
            if key in crawl:
                value = crawl[key]
                if isinstance(value, list) and all(isinstance(s, str) for s in value):
                    setattr(cfg, attr, [s.strip() for s in value if s.strip()])
                else:
                    cfg.warnings.append(f"config.toml: crawl.{key} must be a list of {example}; ignored")
        cfg.lint_disable = [str(x) for x in data.get("lint", {}).get("disable", [])]
        cfg.ai_agent = str(data.get("ai", {}).get("agent", ""))
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
