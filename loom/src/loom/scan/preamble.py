"""The preamble closure of a master and the taxa it declares (book 5.5).

The closure is the master's text before \\begin{document} plus every local file it loads, transitively: \\input, \\usepackage and \\RequirePackage lists (one \\usepackage may name several packages, over several lines), and a local \\documentclass. System packages are never read. Taxa come from \\newtheorem, \\newtheorem*, thmtools' \\declaretheorem, and the % !LOOM environment: directive; the style class is the \\theoremstyle in force at the declaration.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from loom.scan.macros import expand, parse_macros
from loom.scan.model import Diagnostic, Directive, Location, Macro, SourceFile, Taxon
from loom.scan.source import read_source
from loom.scan.tokenize import read_args, tokenize

STANDARD_STYLES = {"plain", "definition", "remark"}
SECTIONING = ["part", "chapter", "section", "subsection", "subsubsection", "paragraph", "subparagraph"]


@dataclass
class Fragment:
    file: str
    start: int
    end: int
    src: SourceFile


@dataclass
class PreambleClosure:
    master: str
    fragments: list[Fragment] = field(default_factory=list)
    taxa: dict[str, Taxon] = field(default_factory=dict)
    macros: dict[str, Macro] = field(default_factory=dict)
    loads_loom: bool = False
    engine: str | None = None
    custom_styles: set[str] = field(default_factory=set)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def files(self) -> list[str]:
        return [f.file for f in self.fragments]

    def clean_text(self) -> str:
        return "\n".join(f.src.clean[f.start : f.end] for f in self.fragments)

    def raw_text(self) -> str:
        return "\n".join(f.src.text[f.start : f.end] for f in self.fragments)


def document_start(src: SourceFile) -> int | None:
    m = re.search(r"\\begin\s*\{document\}", src.clean)
    return m.start() if m else None


def _local(root: Path, name: str, exts: tuple[str, ...]) -> str | None:
    name = name.strip()
    if not name or "/" in name and name.startswith("/"):
        return None
    for ext in exts:
        cand = name if name.endswith(ext) else name + ext
        if (root / cand).is_file():
            return Path(cand).as_posix()
    return None


_STYLE_CACHE: dict[tuple[str, str, float], SourceFile] = {}


def _load(root: Path, rel: str, files: dict[str, SourceFile]) -> SourceFile:
    """A scanned .tex file from `files`, or a local .sty/.cls/.tex read on demand and cached by mtime; never added to `files`."""
    if rel in files:
        return files[rel]
    mtime = (root / rel).stat().st_mtime
    key = (str(root), rel, mtime)
    if key not in _STYLE_CACHE:
        _STYLE_CACHE[key] = read_source(root, rel)
    return _STYLE_CACHE[key]


def build_closure(
    master: SourceFile,
    root: Path,
    files: dict[str, SourceFile],
    directives: list[Directive],
    *,
    foreign: bool = False,
) -> PreambleClosure:
    """Collect the closure, then parse taxa and macros over it in inclusion order.

    `foreign` is for someone else's paper, read by `loom digest extract`: it also takes theorem environments declared in the body and environments defined as wrappers around theorem-like ones. A quilt's own scan does not, deliberately -- an author is asked to declare in the preamble so a node file describes itself -- but a cited paper cannot be asked, and missing either idiom cost three of sixteen real papers their results or their numbering.
    """
    closure = PreambleClosure(master=master.path)
    seen: set[str] = set()
    doc = document_start(master)
    _collect(master, 0, doc if doc is not None else len(master.clean), root, files, closure, seen)
    text = closure.clean_text()
    closure.macros = parse_macros(text)
    closure.loads_loom = bool(
        re.search(r"\\(usepackage|RequirePackage)\s*(\[[^\]]*\])?\s*\{[^}]*\bloom\b[^}]*\}", text)
    )
    for d in directives:
        if d.form == "tex" and d.key == "program" and d.file == master.path:
            closure.engine = d.value
    _parse_taxa(closure)
    if foreign:
        if doc is not None:
            _parse_body_taxa(closure, master, doc)
        _parse_wrappers(closure, master, doc)
    for d in directives:
        if d.form == "kv" and d.key == "environment" and d.file == master.path:
            m = re.match(r"([^=]+)=\s*([^,]+)(?:,\s*(\w+))?\s*$", d.value)
            if m:
                env, name, style = m.group(1).strip(), m.group(2).strip(), (m.group(3) or "plain").strip()
                if env not in closure.taxa:
                    closure.taxa[env] = Taxon(
                        env, name, style if style in STANDARD_STYLES else "plain", True, d.file, d.offset
                    )
    return closure


def _collect(
    src: SourceFile,
    start: int,
    end: int,
    root: Path,
    files: dict[str, SourceFile],
    closure: PreambleClosure,
    seen: set[str],
) -> None:
    key = f"{src.path}:{start}"
    if key in seen:
        return
    seen.add(key)
    closure.fragments.append(Fragment(src.path, start, end, src))
    text = src.clean
    for t in tokenize(text[start:end]):
        if t.kind != "cmd":
            continue
        pos = start + t.end
        if t.value in ("usepackage", "RequirePackage"):
            (_, names), _, _ = read_args(text, pos, "om")
            for pkg in (names or "").split(","):
                rel = _local(root, pkg, (".sty",))
                if rel:
                    child = _load(root, rel, files)
                    _collect(child, 0, len(child.clean), root, files, closure, seen)
        elif t.value in ("documentclass", "LoadClass"):
            (_, name), _, _ = read_args(text, pos, "om")
            rel = _local(root, name or "", (".cls",))
            if rel:
                child = _load(root, rel, files)
                _collect(child, 0, len(child.clean), root, files, closure, seen)
        elif t.value in ("input", "include"):
            (name,), _, _ = read_args(text, pos, "m")
            if name is None:
                continue
            rel = _local(root, name, ("", ".tex"))
            if rel:
                child = _load(root, rel, files)
                if child.path == src.path:
                    continue
                _collect(child, 0, len(child.clean), root, files, closure, seen)


_STYLE = re.compile(r"\\(newtheoremstyle|theoremstyle|newtheorem|declaretheorem)(\*?)(?![A-Za-z@])")


def _display_name(raw: str, closure: PreambleClosure, file: str, offset: int, env: str) -> str:
    name = raw.strip()
    if not name.startswith("\\"):
        return re.sub(r"\s+", " ", name)
    m = re.match(r"\\([A-Za-z@]+)\s*$", name)
    macro = closure.macros.get(m.group(1)) if m else None
    if macro is not None and macro.args == 0:
        expanded = expand(macro, []).strip()
        if "\\" not in expanded and "#" not in expanded and expanded:
            return expanded
    closure.diagnostics.append(
        Diagnostic(
            "info",
            "loom:taxon-name-macro",
            f"display name of environment {env} is the macro {name}; using {env.capitalize()}",
            [Location(file, closure.fragments[0].src.line_of(offset) if file == closure.master else 0)],
        )
    )
    return env.capitalize()


def _parse_taxa(closure: PreambleClosure) -> None:
    style = "plain"
    for frag in closure.fragments:
        text = frag.src.clean
        pos = frag.start
        while True:
            m = _STYLE.search(text, pos, frag.end)
            if not m:
                break
            cmd, starred = m.group(1), bool(m.group(2))
            after = m.end()
            if cmd == "theoremstyle":
                (val,), _, after = read_args(text, after, "m")
                style = (val or "plain").strip()
                if style not in STANDARD_STYLES and style not in closure.custom_styles:
                    closure.diagnostics.append(
                        Diagnostic(
                            "warning",
                            "loom:unknown-theoremstyle",
                            f"\\theoremstyle{{{style}}} is not plain, definition, or remark; treating it as plain",
                            [Location(frag.file, frag.src.line_of(m.start()))],
                        )
                    )
            elif cmd == "newtheoremstyle":
                (val,), _, after = read_args(text, after, "m")
                if val:
                    closure.custom_styles.add(val.strip())
            elif cmd == "newtheorem":
                (env, counter, name, within), _, after = read_args(text, after, "momo")
                if env and name is not None:
                    env_name = env.strip()
                    disp = _display_name(name, closure, frag.file, m.start(), env_name)
                    closure.taxa[env_name] = Taxon(
                        env_name,
                        disp,
                        _style_class(style),
                        not starred,
                        frag.file,
                        m.start(),
                        counter.strip() if counter else None,
                        within.strip() if within else None,
                    )
            else:  # declaretheorem
                (opts, env), _, after = read_args(text, after, "om")
                if env:
                    env_name = env.strip()
                    kv = dict(re.findall(r"(\w+)\s*=\s*([^,]+)", opts or ""))
                    disp = _display_name(kv.get("name", env_name.capitalize()), closure, frag.file, m.start(), env_name)
                    st = kv.get("style", style).strip()
                    numbered = kv.get("numbered", "yes").strip() != "no"
                    closure.taxa[env_name] = Taxon(env_name, disp, _style_class(st), numbered, frag.file, m.start())
            pos = max(after, m.end())


def _parse_body_taxa(closure: PreambleClosure, master: SourceFile, doc: int) -> None:
    """Theorem environments declared after `\\begin{document}`, which the preamble closure cannot see.

    Legal, and common in older papers: Totaro 2004 declares `theorem`, `lemma`, `corollary` and `proposition` on the four lines after `\\begin{document}`, and an extractor that read only the preamble found no theorem-like environment at all and extracted nothing from it. A declaration already made in the preamble wins; the body adds, it never overrides.
    """
    before = dict(closure.taxa)
    body = PreambleClosure(master=closure.master, fragments=[Fragment(master.path, doc, len(master.clean), master)])
    body.macros = closure.macros
    body.custom_styles = set(closure.custom_styles)
    _parse_taxa(body)
    for env, taxon in body.taxa.items():
        closure.taxa.setdefault(env, taxon)
    closure.taxa.update(before)


_WRAPPER = re.compile(r"\\(?:re)?newenvironment\s*\*?\s*\{([^{}]+)\}")
_BOLD_NAME = re.compile(r"(?:\{\\bf\s+|\\textbf\s*\{|\{\\bfseries\s+)([A-Z][A-Za-z ]{1,30}?)\.?\s*\}")


def _parse_wrappers(closure: PreambleClosure, master: SourceFile, doc: int | None) -> None:
    """Environments defined as a wrapper around a theorem-like one are theorem-like, on the same counter.

    `\\newtheorem{defnp}[prop]{Definition}` then `\\newenvironment{defn}{\\begin{defnp}\\rm}{\\end{defnp}}` is how a paper written without amsthm's `\\theoremstyle` sets a definition upright, and the body then uses only `defn`. Missing it does worse than lose the definitions: they share the `prop` counter, so every result after them is numbered wrongly. Behrend-Fantechi's digest read `lem-3.6` for the paper's Lemma 3.8 this way, and Romagny 2022, which builds every environment as a wrapper around one `\\newtheorem{counter}`, extracted one result of twenty-seven.

    The wrapper takes the wrapped environment's counter, so the two step together. Its display name is the wrapped one's, unless that is empty or not a word -- Romagny's counter is named `$\\!\\!$` -- in which case it is read from the `{\\bf Name.}` the wrapper prints.
    """
    frags = list(closure.fragments)
    if doc is not None:
        frags.append(Fragment(master.path, doc, len(master.clean), master))
    for frag in frags:
        text = frag.src.clean
        for m in _WRAPPER.finditer(text, frag.start, frag.end):
            env = m.group(1).strip()
            if not env or env in closure.taxa:
                continue
            (_nargs, _default, begin, _end), _, _after = read_args(text, m.end(), "oomm")
            if not begin:
                continue
            inner = re.search(r"\\begin\s*\{([^{}]+)\}", begin)
            if not inner or inner.group(1).strip() not in closure.taxa:
                continue
            wrapped = closure.taxa[inner.group(1).strip()]
            name = wrapped.name if re.search(r"[A-Za-z]{2,}", wrapped.name or "") else ""
            if not name:
                bold = _BOLD_NAME.search(begin)
                name = bold.group(1).strip() if bold else env.split("-")[0].capitalize()
            closure.taxa[env] = Taxon(
                env,
                name,
                wrapped.style,
                wrapped.numbered,
                frag.file,
                m.start(),
                wrapped.counter or wrapped.env,
                None,
            )


def _style_class(style: str) -> str:
    return style if style in STANDARD_STYLES else "plain"


def taxa_union(closures: list[PreambleClosure]) -> dict[str, Taxon]:
    """Every environment name any master declares, the default master first so its declaration wins on conflict."""
    out: dict[str, Taxon] = {}
    for c in closures:
        for env, taxon in c.taxa.items():
            out.setdefault(env, taxon)
    return out


def taxa_conflicts(closures: list[PreambleClosure]) -> list[tuple[str, list[tuple[str, str]]]]:
    by_env: dict[str, list[tuple[str, str]]] = {}
    for c in closures:
        for env, taxon in c.taxa.items():
            by_env.setdefault(env, []).append((c.master, f"{taxon.name}/{taxon.style}"))
    return [(env, decls) for env, decls in by_env.items() if len({d[1] for d in decls}) > 1]
