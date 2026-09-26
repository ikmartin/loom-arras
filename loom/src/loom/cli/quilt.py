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
from loom.scan.quilt import is_quilt_root, load_user_config, user_config_path

ASSETS = resources.files("loom") / "assets"

CONFIG_TEMPLATE = """[quilt]
name = "{name}"
main = "{drafting}/main.tex"    # default master
drafting = "{drafting}"           # working documents, every one live
canon = "{canon}"              # landmarks: flat, self-contained, never scanned
prefix = "{prefix}"               # default id prefix for loom new
engine = "pdflatex"         # default engine; % !TEX program in a master overrides

[refs]
fetch = false               # may loom fetch sources and PDFs for cited works (loom refs fetch); --fetch allows one run
resolve = false             # may loom look identifiers up at zbMATH Open and Crossref (loom refs resolve); --resolve allows one run

[lint]
disable = []                # diagnostic codes to silence, e.g. ["loom:unmatched-postnote"]

[author]
name = "{author}"{author_pad}# who this quilt's records name; empty until you write it here or pass --author

[ai]
launch = {launch}              # may loom serve run the command in ai/ai-config.toml for a turn when a message waits
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


AI_CHOICES = ("claude", "codex", "other", "none")
AI_LABELS = {"claude": "Claude (Claude Code)", "codex": "ChatGPT (Codex)", "other": "another agent", "none": "none"}


def ask_ai(yes: bool) -> str:
    """Which AI the person works with: `claude`, `codex`, `other` or `none`, asked when a terminal is attached.

    Anything but 1, 2 or 3 is 4, no AI; without a terminal, or with `--yes`, the answer is `none` -- loom starts nothing it was not told about.
    """
    if yes or not sys.stdin.isatty():
        return "none"
    click.echo(
        "Which AI do you use with this quilt?\n  1. Claude (Claude Code)\n  2. ChatGPT (Codex)\n  3. Other\n  4. No AI"
    )
    value = click.prompt("Enter 1, 2, 3 or 4", default="4")
    return {"1": "claude", "2": "codex", "3": "other"}.get(str(value).strip(), "none")


def _set_launch(target: Path, launch: bool) -> None:
    """Say in `config.toml` whether `loom serve` may start the agent; written only when it differs from what the file says."""
    from loom.agent import launching

    if launching(target) == launch:
        return
    p = target / "config.toml"
    text = p.read_text(encoding="utf-8")
    value = "true" if launch else "false"
    import re as _re

    if _re.search(r"(?m)^launch\s*=", text):
        text = _re.sub(r"(?m)^launch\s*=\s*\w+", f"launch = {value}", text, count=1)
    elif _re.search(r"(?m)^\[ai\]\s*$", text):
        text = _re.sub(r"(?m)^\[ai\]\s*$", f"[ai]\nlaunch = {value}", text, count=1)
    else:
        text = text.rstrip("\n") + f"\n\n[ai]\nlaunch = {value}\n"
    p.write_text(text, encoding="utf-8")


def setup_ai(target: Path, choice: str, launch: bool) -> list[str]:
    """Write `ai/ai-config.toml` for the answer, install the AI layer for Claude or Codex, and say what will happen.

    Returns the lines `loom init` prints: which AI, where its command lives, and whether `loom serve` will start it.
    """
    from loom.agent import CONFIG, config_text

    if choice in ("claude", "codex") and not (target / "ai").exists():
        from loom.ai.layout import init_layer

        init_layer(target)
    (target / CONFIG).parent.mkdir(parents=True, exist_ok=True)
    (target / CONFIG).write_text(config_text(choice), encoding="utf-8")
    _set_launch(target, launch)
    said = {
        "claude": f"AI: {AI_LABELS['claude']}. The command loom would run is in {CONFIG}; loom agent check tests it.",
        "codex": f"AI: {AI_LABELS['codex']} configured. Run codex login if needed, then loom agent check. Start and resume commands are in {CONFIG}.",
        "other": f"AI: another agent. Fill in {CONFIG} with the command that starts it for one turn -- its header says how -- and loom agent check tests it.",
        "none": f"AI: none. {CONFIG} is there, commented out, should that change.",
    }[choice]
    when = (
        "Agents will be launched by loom serve when a message waits: set launch = false under [ai] in config.toml to stop that."
        if launch
        else "Agents will not be launched by loom serve: set launch = true under [ai] in config.toml to change that."
    )
    return [said, when]


def ask_author(default: str, yes: bool) -> str:
    """The name this quilt's records will carry, written to `[author] name` (book 4.2).

    Asked under the same rule as the prefix: once, when a terminal is attached and `--yes` is absent. An empty answer is a fine one -- the key is then written empty and the author fills it in, which is what a quilt with no terminal and no `--author` gets.
    """
    if yes or not sys.stdin.isatty():
        return default
    value = click.prompt(
        "Author name for this quilt's records (empty to fill in later)", default=default, show_default=False
    )
    return str(value).strip()


GITIGNORE_NOTE = """wrote .gitignore, ignores:
  build/ (everything loom can rebuild)
  refs/**/paper.pdf and refs/**/src/ (outside papers, fetched not written)
  but not refs/**/pages/ or sections.json: the page text an anchor names is committed
  all stray LaTeX files (.aux, .log, .bbl and the rest)"""


def _user_dirs() -> tuple[str, str]:
    """The drafting and canon directory names a person's user config asks for, else the defaults; init writes them into the quilt so the layout is explicit there."""
    uq = load_user_config().get("quilt", {})
    uq = uq if isinstance(uq, dict) else {}
    drafting = str(uq.get("drafting", "drafting")).strip("/") or "drafting"
    canon = str(uq.get("canon", "canon")).strip("/") or "canon"
    return drafting, canon


def write_minimal_quilt(target: Path, prefix: str, minimal_master: bool = True, author: str = "") -> list[Path]:
    """Write the skeleton of a quilt into `target`.

    Returns the paths it created, deepest first, so `init --from` can undo them when the import that follows fails; paths that were already there are not listed and so are never removed.
    """
    made: list[Path] = []
    drafting, canon = _user_dirs()

    def mkdir(path: Path) -> None:
        # every directory this call brings into being is recorded, parents included, so undo_minimal_quilt leaves nothing behind
        for p in [path, *path.parents]:
            if p == target or target not in p.parents:
                break
            if not p.exists() and p not in made:
                made.append(p)
        if not path.exists() and path not in made:
            made.append(path)
        path.mkdir(parents=True, exist_ok=True)

    def write(path: Path, text: str) -> None:
        if not path.exists():
            made.append(path)
        path.write_text(text, encoding="utf-8")

    mkdir(target / drafting)
    mkdir(target / canon)
    for d in ("nodes", "digests", "refs"):
        mkdir(target / d)
    mkdir(target / ".loom" / "history")
    write(
        target / "config.toml",
        CONFIG_TEMPLATE.format(
            name=target.resolve().name,
            prefix=prefix,
            drafting=drafting,
            canon=canon,
            author=author,
            author_pad=" " * max(1, 22 - len(author)),
            launch="false",
        ),
    )
    write(target / "loom.sty", (ASSETS / "loom.sty").read_text(encoding="utf-8"))
    if minimal_master:
        write(target / drafting / "main.tex", (ASSETS / "init" / "main.tex").read_text(encoding="utf-8"))
    write(target / ".loom" / "history" / "ledger.jsonl", "")
    gitignore = (ASSETS / "init" / "gitignore").read_text(encoding="utf-8").replace("drafting/", f"{drafting}/")
    write(target / ".gitignore", gitignore)
    # the orientation is written with this quilt's own directory names and id prefix, so nothing in it is an example the author has to translate
    readme = (
        (ASSETS / "init" / "readme.md")
        .read_text(encoding="utf-8")
        .replace("drafting/", f"{drafting}/")
        .replace("canon/", f"{canon}/")
        .replace("q-0", f"{prefix}-0")
    )
    write(target / "README.md", readme)
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
    """Copy the demo's content over the skeleton `write_minimal_quilt` just wrote.

    `.gitignore` comes from `assets/init/`, never from the demo's own copy. The demo is a quilt like any other and has nothing of its own to ignore -- and when it carried a copy, that copy named `refs/pdf/` and `refs/src/` for three plans after DR-108 moved the artifacts into `refs/<work-id>/`, so a demo quilt ignored two directories that no longer existed and committed the PDFs that did.
    """
    demo = ASSETS / "demo"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        str(demo), str(target), dirs_exist_ok=True, ignore=shutil.ignore_patterns("build", "__pycache__", ".gitignore")
    )
    # written from the one source, never from the demo's copy of it
    (target / ".gitignore").write_text((ASSETS / "init" / "gitignore").read_text(encoding="utf-8"), encoding="utf-8")
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
@click.option(
    "--author",
    default=None,
    metavar="NAME",
    help="Who this quilt's records name; written to config.toml. Asked for when not given, and left empty when nobody answers.",
)
@click.option("--git", "git_init", is_flag=True, help="Also run git init. A quilt is files; loom reads no history.")
@click.option(
    "--ai",
    "ai",
    type=click.Choice(AI_CHOICES),
    default=None,
    help="Which AI you use, instead of being asked: its command goes in ai/ai-config.toml.",
)
@click.option(
    "--launch-agents/--no-launch-agents",
    default=False,
    help="Let loom serve start the agent for a turn when a message waits (config.toml [ai] launch). Off by default.",
)
@click.option("--yes", "-y", is_flag=True, help="Skip questions; take defaults and confirm the import.")
@click.pass_context
def init(
    ctx: click.Context,
    directory: str | None,
    from_file: str | None,
    demo: bool,
    prefix: str | None,
    author: str | None,
    git_init: bool,
    ai: str | None,
    launch_agents: bool,
    yes: bool,
) -> None:
    """Create a quilt in DIRECTORY (default: the current directory); with --from FILE, import a paper into it as its first canon document (then: loom draft)."""
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
        # `--author ""` is an answer, so the prompt is offered only when the flag was absent altogether
        named = author.strip() if author is not None else ask_author("", yes)
        made = write_minimal_quilt(target, chosen, minimal_master=paper is None, author=named)
    _write_user_config_template()
    choice = ai or ask_ai(yes)

    def announce() -> None:
        """Set up the AI side and say what was created, once the quilt is certain to outlive the command."""
        said_ai = setup_ai(target, choice, launch_agents)
        note(f"wrote the demo quilt to {target}" if demo else f"created quilt {target} with prefix {chosen}")
        note(GITIGNORE_NOTE)
        for line in said_ai:
            note(line)
        if git_init and _git_init(target):
            note(f"git init {target} (--git asked; loom itself reads no history)")

    if paper is not None:
        from loom.cli.paper import run_import
        from loom.scan.quilt import load_quilt

        try:
            ident = run_import(load_quilt(target), paper, yes)
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
