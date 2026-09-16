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
  refs/ (outside papers which are fetched not written; your digests are in digests/)
  all stray LaTeX files (.aux, .log, .bbl and the rest)"""


def write_minimal_quilt(target: Path, prefix: str, minimal_master: bool = True) -> list[Path]:
    """Write the skeleton of a quilt into `target`.

    Returns the paths it created, deepest first, so `init --from` can undo them when the import that follows fails; paths that were already there are not listed and so are never removed.
    """
    made: list[Path] = []

    def mkdir(path: Path) -> None:
        if not path.exists():
            made.append(path)
        path.mkdir(parents=True, exist_ok=True)

    def write(path: Path, text: str) -> None:
        if not path.exists():
            made.append(path)
        path.write_text(text, encoding="utf-8")

    mkdir(target / "drafts")
    for d in ("nodes", "digests", "refs", "comments"):
        mkdir(target / d)
    write(target / "config.toml", CONFIG_TEMPLATE.format(prefix=prefix))
    write(target / "loom.sty", (ASSETS / "loom.sty").read_text(encoding="utf-8"))
    if minimal_master:
        write(target / "drafts" / "main.tex", (ASSETS / "init" / "main.tex").read_text(encoding="utf-8"))
    write(target / ".gitignore", (ASSETS / "init" / "gitignore").read_text(encoding="utf-8"))
    write(target / "README.md", (ASSETS / "readme-contract.md").read_text(encoding="utf-8"))
    return sorted(made, key=lambda q: len(q.parts), reverse=True)


def undo_minimal_quilt(target: Path, existed: bool, made: list[Path]) -> None:
    """Remove the skeleton again, for an `init --from` whose import failed before writing anything of its own.

    A directory init created goes whole; one that was already there keeps everything init did not write, which is the author's paper in the in-place case.
    """
    if not existed:
        shutil.rmtree(target, ignore_errors=True)
        return
    for path in made:
        try:
            if path.is_dir():
                path.rmdir()  # only if still empty: the import may have left nothing, but a node the author wrote is not ours to delete
            else:
                path.unlink()
        except OSError:
            pass


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
    existed = target.exists()
    made: list[Path] = []
    chosen = ""
    if demo:
        write_demo_quilt(target)
    else:
        chosen = prefix or ask_prefix("q", yes)
        if not PREFIX.match(chosen):
            raise EnvError(f"prefix {chosen!r} must be letters and digits without hyphens")
        made = write_minimal_quilt(target, chosen, minimal_master=paper is None)
    _write_user_config_template()

    def announce() -> None:
        """Say what was created, once the quilt is certain to outlive the command."""
        note(f"wrote the demo quilt to {target}" if demo else f"created quilt {target} with prefix {chosen}")
        note(GITIGNORE_NOTE)
        if git_init and _git_init(target):
            note(f"git init {target} (--git asked; loom itself reads no history)")

    if paper is not None:
        from loom.cli.paper import run_import
        from loom.scan.quilt import load_quilt

        try:
            ident = run_import(load_quilt(target), paper, yes, fix_anchors, prefix)
        except BaseException:
            # the import writes nothing into the quilt until it says "Wrote N files", so a failure before that leaves only the skeleton above; leaving that behind would refuse the obvious retry -- the same command with --fix-anchoring -- as "already inside a quilt"
            undo_minimal_quilt(target, existed, made)
            raise
        announce()
        if ident is not None and not ident.passed and not ident.skipped:
            ctx.exit(EXIT_CONTENT)
        return
    announce()
    note('next: loom doctor; loom lint; loom new lemma "Title"')
