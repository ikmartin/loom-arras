"""`loom init`: create a quilt (book 4.7), or write the demo quilt (chapter 14)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path

import click

from loom.cli._common import EXIT_CONTENT, EnvError, note
from loom.scan.labels import PREFIX
from loom.scan.quilt import is_quilt_root, user_config_path

ASSETS = resources.files("loom") / "assets"

CONFIG_TEMPLATE = """[quilt]
main = "drafts/main.tex"    # default master
drafts = "drafts"           # masters directory
prefix = "{prefix}"               # default id prefix for loom new
engine = "pdflatex"         # default engine; % !TEX program in a master overrides

[refs]
fetch = false               # may loom fetch from arXiv for digest fetch

[lint]
disable = []                # diagnostic codes to silence, e.g. ["loom:unmatched-postnote"]

[ai]
agent = ""                  # command loom ai start launches, if any
runner = ""                 # deferred; see specs/runner.md
"""

USER_CONFIG_TEMPLATE = """# loom user configuration: settings that belong to a person, not a quilt.
# [author]
# name = "Your Name"
"""


def _inside_git(path: Path) -> bool:
    try:
        proc = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


def _git_init(path: Path) -> None:
    if shutil.which("git") is None or _inside_git(path):
        return
    subprocess.run(["git", "init", "-q", str(path)], check=False, capture_output=True)


def _write_user_config_template() -> None:
    p = user_config_path()
    try:
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(USER_CONFIG_TEMPLATE, encoding="utf-8")
    except OSError:
        pass


def ask_prefix(default: str, yes: bool) -> str:
    if yes or not sys.stdin.isatty():
        return default
    value = click.prompt("Id prefix for new nodes (letters and digits, no hyphen)", default=default)
    return str(value).strip()


def write_minimal_quilt(target: Path, prefix: str, minimal_master: bool = True) -> None:
    (target / "drafts").mkdir(parents=True, exist_ok=True)
    for d in ("nodes", "refs", "comments"):
        (target / d).mkdir(exist_ok=True)
    (target / "config.toml").write_text(CONFIG_TEMPLATE.format(prefix=prefix), encoding="utf-8")
    (target / "loom.sty").write_text((ASSETS / "loom.sty").read_text(encoding="utf-8"), encoding="utf-8")
    if minimal_master:
        (target / "drafts" / "main.tex").write_text(
            (ASSETS / "init" / "main.tex").read_text(encoding="utf-8"), encoding="utf-8"
        )
    (target / ".gitignore").write_text((ASSETS / "init" / "gitignore").read_text(encoding="utf-8"), encoding="utf-8")
    (target / "README.md").write_text((ASSETS / "readme-contract.md").read_text(encoding="utf-8"), encoding="utf-8")


def write_demo_quilt(target: Path) -> None:
    demo = ASSETS / "demo"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(demo), str(target), dirs_exist_ok=True)
    for cache in target.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


@click.command()
@click.argument("directory", required=False, default=None)
@click.option(
    "--from",
    "from_file",
    default=None,
    metavar="FILE",
    help="Import an existing paper: FILE is its main .tex file, anywhere on disk.",
)
@click.option("--demo", is_flag=True, help="Write the demo quilt instead of a minimal master.")
@click.option("--prefix", default=None, help="Id prefix for new nodes.")
@click.option("--no-git", is_flag=True, help="Do not run git init.")
@click.option("--yes", "-y", is_flag=True, help="Skip questions; take defaults and confirm the import.")
@click.option(
    "--fix-anchoring",
    "fix_anchors",
    is_flag=True,
    help="With --from: rewrite the copies so theorem-like environments are line-anchored.",
)
@click.pass_context
def init(
    ctx: click.Context,
    directory: str | None,
    from_file: str | None,
    demo: bool,
    prefix: str | None,
    no_git: bool,
    yes: bool,
    fix_anchors: bool,
) -> None:
    """Create a quilt in DIRECTORY (default: the current directory); with --from FILE, import a paper into it."""
    target = Path(directory).expanduser() if directory else Path.cwd()
    if is_quilt_root(target) or any(is_quilt_root(p) for p in target.resolve().parents):
        raise EnvError(f"{target} is already inside a quilt")
    paper = Path(from_file).expanduser().resolve() if from_file else None
    if paper is not None and not paper.is_file():
        raise EnvError(f"{from_file} is not a file")
    if target.exists() and any(target.iterdir()):
        if paper is None or not paper.is_relative_to(target.resolve()):
            raise EnvError(
                f"{target} is not empty; use --from FILE with a file inside it to turn an existing paper directory into a quilt"
            )
    if prefix is not None and not PREFIX.match(prefix):
        raise EnvError(f"prefix {prefix!r} must be letters and digits without hyphens")
    if demo:
        write_demo_quilt(target)
        note(f"wrote the demo quilt to {target}")
    else:
        chosen = prefix or ask_prefix("q", yes)
        if not PREFIX.match(chosen):
            raise EnvError(f"prefix {chosen!r} must be letters and digits without hyphens")
        write_minimal_quilt(target, chosen, minimal_master=paper is None)
        note(f"created quilt {target} with prefix {chosen}")
    if not no_git:
        _git_init(target)
    _write_user_config_template()
    if paper is not None:
        from loom.cli.paper import run_import
        from loom.scan.quilt import load_quilt

        ident = run_import(load_quilt(target), paper, yes, fix_anchors, prefix)
        if ident is not None and not ident.passed and not ident.skipped:
            ctx.exit(EXIT_CONTENT)
        return
    note('next: loom doctor; loom lint; loom new lemma "Title"')
