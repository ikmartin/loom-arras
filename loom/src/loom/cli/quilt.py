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


def _git_init(path: Path) -> bool:
    """Create a repository at `path`, unless git is missing or the directory is already in a work tree. Returns whether one was created, so the caller can say so; a silent side effect outside the tool's own files is the hardest kind to defend."""
    if shutil.which("git") is None or _inside_git(path):
        return False
    proc = subprocess.run(["git", "init", "-q", str(path)], check=False, capture_output=True)
    return proc.returncode == 0


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


GITIGNORE_NOTE = """wrote .gitignore, ignores:
  build/ (everything loom can rebuild)
  refs/pdf/ and refs/src/ (outside papers which are fetched not written)
  all stray LaTeX files (.aux, .log, .bbl and the rest)"""


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
    shutil.copytree(str(demo), str(target), dirs_exist_ok=True, ignore=shutil.ignore_patterns("build", "__pycache__"))
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
@click.option("--git", "git_init", is_flag=True, help="Also run git init. A quilt is files; loom reads no history.")
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
    git_init: bool,
    yes: bool,
    fix_anchors: bool,
) -> None:
    """Create a quilt in DIRECTORY (default: the current directory); with --from FILE, import a paper into it."""
    here = directory is None  # the message says so: "<path> is not empty" reads oddly when the path was never typed
    target = Path(directory).expanduser() if directory else Path.cwd()
    if is_quilt_root(target) or any(is_quilt_root(p) for p in target.resolve().parents):
        raise EnvError(f"{target} is already inside a quilt")
    paper = Path(from_file).expanduser().resolve() if from_file else None
    if paper is not None and not paper.is_file():
        raise EnvError(f"{from_file} is not a file")
    if target.exists() and any(target.iterdir()):
        where = f"the current directory, {target}," if here else f"{target}"
        if paper is None:
            raise EnvError(
                f"{where} is not empty. Name an empty or new directory to create the quilt in, "
                "or pass --from FILE with a file inside it to turn an existing paper directory into a quilt."
            )
        if not paper.is_relative_to(target.resolve()):
            # the paper was given, so the advice to pass one is no help; what is wrong is where it sits
            raise EnvError(
                f"{where} is not empty, and {paper} lies outside it. Either name an empty or new directory "
                f"to create the quilt in (the paper may live anywhere), or pass a --from FILE inside the directory "
                f"to turn an existing paper directory into a quilt."
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
    note(GITIGNORE_NOTE)
    if git_init and _git_init(target):
        note(f"git init {target} (--git asked; loom itself reads no history)")
    _write_user_config_template()
    if paper is not None:
        from loom.cli.paper import run_import
        from loom.scan.quilt import load_quilt

        ident = run_import(load_quilt(target), paper, yes, fix_anchors, prefix)
        if ident is not None and not ident.passed and not ident.skipped:
            ctx.exit(EXIT_CONTENT)
        return
    note('next: loom doctor; loom lint; loom new lemma "Title"')
