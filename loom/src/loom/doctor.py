"""The checks behind `loom doctor`: the machine's tools and what they can do, the author name, the arras bundle, and, inside a quilt, the quilt's own setup.

Every item is `ok`, `warn` (it works, but the person will hit something) or `fail` (a command they need will refuse or misbehave), and every item that is not ok carries a one-line remedy. The quilt's items call the functions the owning commands use -- `loom agent check`, `loom upgrade`, `loom lint` -- rather than restating them. Tools are found through shutil.which, so tests point PATH at the fake TeX shim; the probes run at once and share one deadline, PROBE_TIMEOUT, so a hung tool is reported rather than waited on.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

from loom.version import INTERFACE_VERSION, __version__

OK, WARN, FAIL = "ok", "warn", "fail"
#: required: missing fails; optional: missing warns, and present but broken fails, since loom uses it when present; quilt: the quilt section
REQUIRED, OPTIONAL, QUILT = "required", "optional", "quilt"
#: Seconds a probe may take before its tool is reported as hung.
PROBE_TIMEOUT = 10.0

_MAC = platform.system() == "Darwin"
TEX = (
    "brew install --cask mactex-no-gui"
    if _MAC
    else "install TeX Live (https://tug.org/texlive) or apt install texlive-full"
)
POPPLER = "brew install poppler" if _MAC else "apt install poppler-utils"
GIT = "brew install git" if _MAC else "apt install git"
VENDOR = "cd arras && npm run build && cd ../loom && uv run python scripts/vendor_arras.py ../arras/build"


@dataclass
class Item:
    """One line of the report; `extra` holds the fields some items add to the JSON (a tool's `path`, the bundle's `source` and `interface`)."""

    name: str
    status: str
    severity: str
    detail: str = ""
    remedy: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "severity": self.severity,
            "detail": self.detail,
            "remedy": self.remedy,
            **self.extra,
        }


@dataclass(frozen=True)
class Tool:
    name: str
    severity: str
    flag: tuple[str, ...]
    remedy: str
    #: what loom uses it for, said when it is missing
    use: str


TOOLS = [
    Tool("latexmk", REQUIRED, ("-v",), TEX, "every compile runs it"),
    Tool("pdflatex", REQUIRED, ("--version",), TEX, "the default engine"),
    Tool("dvisvgm", REQUIRED, ("--version",), TEX, "the SVG of every block the viewer cannot typeset, and figures"),
    Tool(
        "latex",
        OPTIONAL,
        ("--version",),
        TEX,
        "the SVG fallback; without it those blocks show as source, with a warning",
    ),
    Tool("xelatex", OPTIONAL, ("--version",), TEX, "an engine a quilt may name"),
    Tool("lualatex", OPTIONAL, ("--version",), TEX, "an engine a quilt may name"),
    Tool("bibtex", OPTIONAL, ("--version",), TEX, "bibliographies made with \\bibliography"),
    Tool("biber", OPTIONAL, ("--version",), "tlmgr install biber", "bibliographies made with biblatex"),
    Tool("kpsewhich", OPTIONAL, ("--version",), TEX, "finding the TeX tree's files a source reads"),
    Tool("pdftotext", OPTIONAL, ("-v",), POPPLER, "cited works' page text and geometry, and the identity test"),
    Tool("pdfinfo", OPTIONAL, ("-v",), POPPLER, "cited works' page rotation"),
    Tool("pdftocairo", OPTIONAL, ("-v",), POPPLER, "PDF figures; dvisvgm --pdf stands in, less faithfully"),
    Tool(
        "git",
        OPTIONAL,
        ("--version",),
        GIT,
        "loom init --git, loom sync, and telling whether git tracks the agent's config",
    ),
]


@dataclass
class Report:
    python: str
    loom: str
    interface_version: int
    quilt: Path | None = None
    items: list[Item] = field(default_factory=list)
    strict: bool = False

    @property
    def failing(self) -> list[str]:
        return [i.name for i in self.items if i.status == FAIL]

    @property
    def warnings(self) -> list[str]:
        return [i.name for i in self.items if i.status == WARN]

    @property
    def exit_code(self) -> int:
        """2 when an item fails, or under --strict when one warns; else 0. Doctor never exits 1, which in loom means the quilt's content."""
        return 2 if self.failing or (self.strict and self.warnings) else 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "python": self.python,
            "loom": self.loom,
            "interface_version": self.interface_version,
            "quilt": str(self.quilt) if self.quilt else None,
            "ok": self.exit_code == 0,
            "failing": self.failing,
            "warnings": self.warnings,
            "items": [i.to_dict() for i in self.items],
        }

    def summary(self) -> str:
        warned = self.warnings
        count = f"{len(warned)} warning{'s' if len(warned) != 1 else ''}"
        if self.failing:
            tail = f"; warnings: {', '.join(warned)}" if self.strict and warned else f" ({count})" if warned else ""
            return f"failing: {', '.join(self.failing)}{tail}"
        if warned:
            return f"warnings: {', '.join(warned)}" if self.strict else f"ok ({count})"
        return "ok"

    def render(self) -> str:
        """The text report: one line per item in columns as wide as their contents, a remedy under each item that is not ok, and the summary last."""
        width = max(len(i.name) for i in self.items)
        # a problem's detail runs long, so only the ok lines set where the paths start
        dwidth = max((len(i.detail) for i in self.items if i.extra.get("path") and i.status == OK), default=0)
        lines = [f"loom {self.loom}, interface {self.interface_version}, python {self.python}"]
        for section, items in (
            ("machine", [i for i in self.items if i.severity != QUILT]),
            (f"quilt {self.quilt}" if self.quilt else "quilt", [i for i in self.items if i.severity == QUILT]),
        ):
            if not items:
                continue
            lines += ["", section]
            for i in items:
                path = i.extra.get("path")
                detail = f"{i.detail:<{dwidth}}  {path}" if path else i.detail
                lines.append(f"  {i.status:<4}  {i.name:<{width}}  {detail}".rstrip())
                if i.status != OK and i.remedy:
                    lines.append(f"  {'':<4}  {'':<{width}}  fix: {i.remedy}")
        lines += ["", self.summary()]
        return "\n".join(lines)


@dataclass(frozen=True)
class Answer:
    """What a probed command said: its exit code (None when it could not start or hung) and its output."""

    code: int | None
    out: str = ""
    err: str = ""
    hung: bool = False

    @property
    def first_line(self) -> str:
        lines = (self.out.strip() or self.err.strip()).splitlines()
        return lines[0].strip()[:60] if lines else ""


class Probe:
    """One command started now and read later, in a process group of its own so a hung one can be killed whole.

    Every probe is started from one thread before any is read: forking while another thread runs can leave a child stuck before its exec on macOS, holding a copy of every pipe open at the time, so that each probe then looks hung.
    """

    def __init__(self, argv: list[str]) -> None:
        self.error = ""
        try:
            self.proc: subprocess.Popen[str] | None = subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors="replace",
                start_new_session=True,
            )
        except OSError as exc:
            self.proc, self.error = None, str(exc)

    def answer(self, deadline: float) -> Answer:
        """Its output, waiting no later than `deadline` (a `time.monotonic` value); past it the process group is killed and the answer is `hung`."""
        if self.proc is None:
            return Answer(None, err=self.error)
        left = deadline - time.monotonic()
        # one that finished while an earlier probe used up the time is read, not reported hung
        timeout = left if left > 0 or self.proc.poll() is None else 1.0
        try:
            out, err = self.proc.communicate(timeout=max(0.0, timeout))
        except subprocess.TimeoutExpired:
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
            except OSError:
                self.proc.kill()
            try:
                self.proc.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                pass
            return Answer(None, hung=True)
        return Answer(self.proc.returncode, out, err)


def _tiny_pdf() -> bytes:
    """A valid one-page PDF, 72 points square, for the `-bbox-layout` probe."""
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 72 72] >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for n, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (n, body)
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % off for off in offsets)
    return out + b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)


def _bbox(got: Answer, item: Item) -> None:
    """pdftotext must write `-bbox-layout` word boxes, which `loom refs locate` and the viewer's highlights need; xpdf's has no such flag."""
    if got.hung:
        item.status, item.detail = FAIL, f"{item.detail}: hung writing word boxes (-bbox-layout)"
    elif got.code != 0 or "<page " not in got.out:
        item.status, item.detail = (
            FAIL,
            f"{item.detail}: no -bbox-layout, so cited works have no page geometry (xpdf's?)",
        )
    else:
        return
    item.remedy = f"{POPPLER}, and put poppler's pdftotext first on PATH"


_BIBER = re.compile(r"biber version:?\s*(\d+)\.(\d+)", re.I)
_BIBLATEX = re.compile(r"\\def\\abx@version\{(\d+)\.(\d+)")


def biber_pairs(biber: tuple[int, int], biblatex: tuple[int, int]) -> bool | None:
    """Whether a biber reads what a biblatex writes: since biber 2.15 and biblatex 3.15 each release pairs with the other's of the same minor number, as the two are released together.

    None when both are older than that, since those pairs followed no rule a comparison could apply, or when either major number is not the one that rule covers.
    """
    if biber[0] != 2 or biblatex[0] != 3:
        return None
    if biber[1] < 15 and biblatex[1] < 15:
        return None
    return biber[1] == biblatex[1]


def _biber(found: Answer, item: Item) -> None:
    """Compare biber with the biblatex kpsewhich found; a mismatch is the classic failure of a hand-updated TeX tree."""
    m = _BIBER.search(item.detail)
    sty = Path(found.out.strip().splitlines()[0]) if found.code == 0 and found.out.strip() else None
    try:
        text = sty.read_text(encoding="utf-8", errors="replace") if sty else ""
    except OSError:
        text = ""
    b = _BIBLATEX.search(text)
    if m is None or b is None:
        return
    mine, theirs = (int(m.group(1)), int(m.group(2))), (int(b.group(1)), int(b.group(2)))
    pairs = biber_pairs(mine, theirs)
    said = f"biber {mine[0]}.{mine[1]}, biblatex {theirs[0]}.{theirs[1]}"
    if pairs is None:
        item.detail = f"{said} (pairs this old are not compared)"
    elif pairs:
        item.detail = said
    else:
        item.status, item.detail = (
            WARN,
            f"{said}: by their version numbers they do not pair, so biblatex documents are unlikely to compile",
        )
        item.remedy = "tlmgr update biber biblatex, so both come from one TeX Live; compiling a master that uses biblatex settles it"


def check_tools() -> list[Item]:
    """Find every tool, ask its version, and probe what loom needs of it beyond presence: pdftotext's word boxes, and whether biber pairs with biblatex.

    Every probe starts before any is read and all share one deadline, so doctor takes as long as its slowest tool, and at most PROBE_TIMEOUT.
    """
    paths = {t.name: shutil.which(t.name) for t in TOOLS}
    with tempfile.TemporaryDirectory(prefix="loom-doctor-") as tmp:
        probes = {t.name: Probe([p, *t.flag]) for t in TOOLS if (p := paths[t.name])}
        if paths["pdftotext"]:
            pdf = Path(tmp) / "page.pdf"
            pdf.write_bytes(_tiny_pdf())
            probes["-bbox-layout"] = Probe(
                [paths["pdftotext"], "-q", "-bbox-layout", "-f", "1", "-l", "1", str(pdf), "-"]
            )
        if paths["biber"] and paths["kpsewhich"]:
            probes["biblatex.sty"] = Probe([paths["kpsewhich"], "biblatex.sty"])
        deadline = time.monotonic() + PROBE_TIMEOUT
        answers = {name: probe.answer(deadline) for name, probe in probes.items()}
    items = []
    for tool in TOOLS:
        path = paths[tool.name]
        if path is None:
            status = FAIL if tool.severity == REQUIRED else WARN
            items.append(Item(tool.name, status, tool.severity, f"not found: {tool.use}", tool.remedy, {"path": None}))
            continue
        got = answers[tool.name]
        item = Item(tool.name, OK, tool.severity, got.first_line or "found", "", {"path": path})
        if got.hung:
            item.status, item.detail = FAIL, f"hung: {' '.join(tool.flag)} did not answer in {PROBE_TIMEOUT:g} s"
            item.remedy = f"reinstall it ({tool.remedy}), or take {path} off PATH"
        elif got.code is None:
            item.status, item.detail, item.remedy = FAIL, f"cannot run: {got.err}", tool.remedy
        elif tool.name == "pdftotext":
            _bbox(answers["-bbox-layout"], item)
        elif tool.name == "biber" and "biblatex.sty" in answers:
            _biber(answers["biblatex.sty"], item)
        items.append(item)
    return items


def check_agent_command(name: str, configured: bool) -> Item:
    """An agent's command on PATH; found, never run, since it is a command the person wrote."""
    path = shutil.which(name)
    if path is not None:
        return Item(name, OK, OPTIONAL, "found", "", {"path": path})
    remedy = (
        "install it, or name another command in ai/ai-config.toml; loom agent check tests it"
        if configured
        else f"install it if you use it: loom serve starts agents with {name}"
    )
    return Item(name, WARN, OPTIONAL, "not found: loom serve cannot start the agent", remedy, {"path": None})


def check_author(quilt: Any) -> Item:
    """The name `accept` and `comment` record, by the book's order (4.3)."""
    from loom.scan.quilt import NoAuthorError, resolve_author, user_config_path

    try:
        name, source = resolve_author(None, cwd=quilt.root if quilt else None)
    except NoAuthorError:
        if quilt is not None and quilt.config.author_declared:
            remedy = f'set name = "Your Name" under [author] in {quilt.root / "config.toml"}'
        else:
            remedy = f'add name = "Your Name" under [author] in {user_config_path()}, or git config --global user.name "Your Name"'
        return Item("author", WARN, OPTIONAL, "none: accept and comment refuse without one", remedy)
    return Item("author", OK, OPTIONAL, f"{name} (from {source})")


def check_bundle() -> Item:
    """Which arras bundle `loom serve` would serve, and whether it reads this loom's manifests."""
    from loom.arras_bundle import (
        BundleEnvError,
        checkout_of,
        env_problem,
        find_bundle,
        parse_stamp,
        staleness,
        vendored_path,
    )

    try:
        info = find_bundle()
    except BundleEnvError:
        info = None
    checkout = checkout_of(info.path if info else vendored_path()) if not info or info.source == "vendored" else None
    stamp = parse_stamp(info.version) if info else None
    extra: dict[str, Any] = {
        "source": info.source if info else None,
        "path": str(info.path) if info else None,
        "interface": stamp[1] if stamp else None,
    }
    item = Item("arras bundle", OK, REQUIRED, f"{info.source}, {info.version}" if info else "", "", extra)
    bad_env = env_problem()
    if bad_env:
        item.status = FAIL
        item.detail = f"{bad_env}; loom serve refuses"
        item.remedy = "point LOOM_ARRAS_BUNDLE at a built arras (the directory holding index.html), or unset it"
    elif info is None:
        item.status, item.detail = FAIL, "not found: loom serve refuses"
        item.remedy = (
            VENDOR if checkout else "reinstall loom, whose package carries the viewer, or set LOOM_ARRAS_BUNDLE"
        )
    elif stamp is None:
        item.status = WARN
        item.detail += f": its interface cannot be compared with loom's {INTERFACE_VERSION}"
        item.remedy = "use a bundle loom/scripts/vendor_arras.py stamped"
    elif stamp[1] != INTERFACE_VERSION:
        item.status = FAIL
        item.detail = f"{info.source}, interface {stamp[1]}, but loom writes interface {INTERFACE_VERSION}: the viewer misreads the manifest"
        item.remedy = VENDOR if checkout else "install the loom and the arras of one release"
    elif checkout is not None:
        why = staleness(checkout, stamp[0], PROBE_TIMEOUT)
        if why:
            item.status, item.detail = WARN, f"vendored, {'; '.join(why)}"
            # vendor_arras.py refuses an arras with uncommitted changes
            item.remedy = ("commit arras, then " if stamp[0].endswith("-dirty") else "") + VENDOR
    return item


def check_engine(quilt: Any) -> Item:
    """The quilt's `[quilt] engine` is one loom knows and is installed; `% !TEX program` in a master may still name another."""
    from loom.tex.runner import ENGINE_FLAGS

    engine = quilt.config.engine.strip().lower()
    if engine not in ENGINE_FLAGS:
        return Item(
            "engine",
            WARN,
            QUILT,
            f"engine = {quilt.config.engine!r} is not one of {', '.join(ENGINE_FLAGS)}; loom compiles with pdflatex",
            "set engine under [quilt] in config.toml",
        )
    path = shutil.which(engine)
    if path is None:
        return Item("engine", FAIL, QUILT, f"{engine}: not found, so every compile here fails", TEX, {"path": None})
    return Item("engine", OK, QUILT, engine, "", {"path": path})


def check_agent(d: Any) -> Item:
    """What `loom agent check` finds: a fault fails when launching is on, since loom serve will not start the agent, and warns when off."""
    from loom.agent import CONFIG

    launch = f"launch {'on' if d.launch else 'off'}"
    if not d.configured:
        if d.launch:
            return Item(
                "agent",
                FAIL,
                QUILT,
                "launch is on and no agent is configured",
                f"fill in {CONFIG}, or set launch = false under [ai] in config.toml; loom agent check tests it",
            )
        return Item("agent", OK, QUILT, f"none configured, {launch}")
    if d.faults:
        return Item("agent", FAIL if d.launch else WARN, QUILT, f"{'; '.join(d.faults)}; {launch}", "loom agent check")
    return Item("agent", OK, QUILT, f"{d.config.name}, {launch}")


def check_permissions(root: Path) -> Item:
    """`.claude/settings.json` and `.codex/rules/loom.rules` byte for byte what this loom's table renders (`vendor_files`)."""
    from loom.ai.layout import CLAUDE_SETTINGS, CODEX_RULES, vendor_files

    wanted = (CLAUDE_SETTINGS, CODEX_RULES)
    present = [rel for rel in wanted if (root / rel).is_file()]
    layer = (root / "ai").is_dir()
    if not layer and not present:
        return Item("permissions", OK, QUILT, "no ai/ (loom ai init writes it and them)")
    shipped = vendor_files(True, False, True)
    stale = [rel for rel in present if (root / rel).read_text(encoding="utf-8") != shipped[rel]]
    absent = [rel for rel in wanted if rel not in present] if layer else []
    if not stale and not absent:
        return Item("permissions", OK, QUILT, ", ".join(present))
    said = [f"{rel} missing: an agent here runs without loom's table" for rel in absent]
    said += [f"{rel}: not what this loom lets agents run" for rel in stale]
    # beside an ai/, `loom upgrade` writes both; without one, `loom ai init` does
    return Item("permissions", WARN, QUILT, "; ".join(said), "loom upgrade" if layer else "loom ai init")


def check_ai_files(root: Path) -> Item:
    """The mode files, orientation and skills against what `loom upgrade` would write, by its own dry run; the permission files are the item above."""
    from loom.ai.layout import CLAUDE_SETTINGS, CODEX_RULES, read_versions, sha, tracked_docs, upgrade_layer

    if not (root / "ai").is_dir():
        return Item("ai files", OK, QUILT, "no ai/ (loom ai init writes it)")
    rep = upgrade_layer(root, write=False)
    stale = [rel for rel in rep.written if rel not in (CLAUDE_SETTINGS, CODEX_RULES)]
    shipped, recorded = tracked_docs(), read_versions(root)

    def unseen(rel: str) -> bool:
        """An edited file whose record predates what ships now, with that version not yet beside it; once `loom upgrade` has put it there, merging is the author's."""
        new = root / f"{rel}.new"
        if recorded.get(Path(rel).name) == sha(shipped[rel]):
            return False
        return not new.is_file() or new.read_text(encoding="utf-8") != shipped[rel]

    unseen_files = [rel for rel in rep.kept if unseen(rel)]
    if not stale and not unseen_files:
        kept = f", {len(rep.kept)} edited" if rep.kept else ""
        return Item("ai files", OK, QUILT, f"current{kept}")
    said = []
    if stale:
        said.append(f"older than this loom: {', '.join(stale)}")
    if unseen_files:
        said.append(f"edited, with a newer version shipped: {', '.join(unseen_files)}")
    return Item(
        "ai files", WARN, QUILT, "; ".join(said), "loom upgrade (an edited file gets the new version beside it)"
    )


def check_sty(root: Path) -> Item:
    """The quilt's `loom.sty` is the one this loom ships, which is what `loom upgrade` writes."""
    shipped = resources.files("loom").joinpath("assets", "loom.sty").read_text(encoding="utf-8")
    p = root / "loom.sty"
    if not p.is_file():
        return Item("loom.sty", WARN, QUILT, "missing: a master that loads it will not compile", "loom upgrade")
    if p.read_text(encoding="utf-8") != shipped:
        return Item("loom.sty", WARN, QUILT, "not the one this loom ships", "loom upgrade")
    return Item("loom.sty", OK, QUILT, "current")


def check_gitignore(root: Path) -> Item:
    """The `.gitignore` lines loom relies on (`loom.gitignore.MANAGED`), which `loom upgrade` adds."""
    from loom.gitignore import missing as lacking

    missing = lacking(root)
    if not missing:
        return Item(".gitignore", OK, QUILT, "has loom's lines")
    return Item(".gitignore", WARN, QUILT, f"lacks {', '.join(missing)}", "loom upgrade")


def check_config(quilt: Any) -> Item:
    """What `loom lint` reports of `config.toml` itself: unknown tables and keys, values out of range."""
    w = quilt.config.warnings
    if not w:
        return Item("config", OK, QUILT, "config.toml read cleanly")
    more = f" (and {len(w) - 1} more)" if len(w) > 1 else ""
    return Item("config", WARN, QUILT, f"{w[0]}{more}", "loom lint")


def run_doctor(quilt_path: str | None = None, agents: bool = False, strict: bool = False) -> Report:
    """Check the machine, and the quilt when there is one.

    Parameters
    ----------
    quilt_path : str, optional
        The quilt to check; default the one found from the current directory, and no quilt section when there is none.
    agents : bool, default False
        Also look for `claude` and `codex`, which are otherwise looked for only when the quilt configures an agent.
    strict : bool, default False
        Warnings count against the exit code (1).

    Returns
    -------
    Report
        Every item in order, machine first; `exit_code` is what `loom doctor` exits with.
    """
    from loom.agent import PRESETS, diagnose
    from loom.scan.quilt import NoQuiltError, find_quilt

    report = Report(sys.version.split()[0], __version__, INTERFACE_VERSION, strict=strict)
    quilt, bad_quilt = None, None
    try:
        quilt = find_quilt(Path(quilt_path).expanduser() if quilt_path else None)
    except NoQuiltError as exc:
        # not being in a quilt is normal here; a quilt that cannot be read is not
        if quilt_path or not str(exc).startswith("not inside a quilt"):
            bad_quilt = str(exc)
    diagnosis = diagnose(quilt.root) if quilt else None
    configured = [cmd[0] for _, cmd in diagnosis.commands] if diagnosis is not None else []
    presets = [str(p["start"][0]) for p in PRESETS.values()] if agents else []
    report.items += check_tools()
    report.items += [check_agent_command(c, c in configured) for c in dict.fromkeys(configured + presets)]
    report.items += [check_author(quilt), check_bundle()]
    if bad_quilt is not None:
        report.items.append(
            Item(
                "quilt",
                FAIL,
                QUILT,
                bad_quilt,
                "fix config.toml: every command but init and doctor refuses until it reads",
            )
        )
    if quilt is not None:
        report.quilt = quilt.root
        root = quilt.root
        report.items += [
            check_engine(quilt),
            check_agent(diagnosis),
            check_permissions(root),
            check_ai_files(root),
            check_sty(root),
            check_gitignore(root),
            check_config(quilt),
        ]
    return report
