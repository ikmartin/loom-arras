"""`loom digest extract` (book 8.5): a digest produced mechanically from a reference paper's LaTeX source.

The paper's closure is read with the scanner's own parsers (preamble, macros, environments, sections, master expansion); results are numbered from the paper's .aux when it compiles and from the amsthm counter emulation otherwise; every theorem-like environment becomes an external node with a slugged id, a locator title, its statement with the paper's simple macros expanded and its labels prefixed, and a `\\uses` line listing the results its dropped proof referred to. What cannot be expanded goes into the macro block.
"""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from loom.digest.counters import Numbering
from loom.refs.identity import WorkId, identify
from loom.reshape.importer import closure_of
from loom.scan.bib import citekey_slug
from loom.scan.digests import ALWAYS_LOADED, loaded_packages
from loom.scan.directives import parse_directives
from loom.scan.envtree import labels_in, norm_label, scan_environments
from loom.scan.expand import Expansion, expand_master
from loom.scan.macros import expand as expand_macro
from loom.scan.macros import expand_definition_aliases
from loom.scan.model import Env, Macro, SourceFile, Taxon
from loom.scan.preamble import build_closure, document_start
from loom.scan.scan import ScanResult
from loom.scan.sections import SectionUnit, find_sections
from loom.scan.source import read_source
from loom.scan.tokenize import match_group, read_args
from loom.tex.aux import AuxNumber, parse_aux
from loom.tex.runner import compile_tex, stage_sources

ABBREV = {
    "theorem": "thm",
    "lemma": "lem",
    "proposition": "prop",
    "corollary": "cor",
    "definition": "def",
    "remark": "rem",
    "example": "ex",
    "construction": "constr",
    "conjecture": "conj",
}
_CMD = re.compile(r"\\([A-Za-z@]+)")
_REF = re.compile(r"\\(ref|eqref|cref|Cref|autoref|vref)\s*\{([^}]*)\}")
_LABEL = re.compile(r"\\label\s*\{([^}]*)\}")
TEXT_EXTS = (".tex", ".sty", ".cls", ".ltx", ".def", ".clo")
# packages about the page, the fonts, or the bibliography, which a statement never needs; the rest of the reference's \usepackage lines become `requires:`
PRESENTATION = {
    "inputenc",
    "fontenc",
    "lmodern",
    "textcomp",
    "geometry",
    "hyperref",
    "microtype",
    "xcolor",
    "color",
    "graphicx",
    "graphics",
    "url",
    "cleveref",
    "enumitem",
    "setspace",
    "titlesec",
    "fancyhdr",
    "appendix",
    "natbib",
    "biblatex",
    "babel",
    "csquotes",
    "booktabs",
    "caption",
    "subcaption",
    "float",
    "times",
    "mathptmx",
    "fullpage",
    "titling",
    "tocloft",
    "todonotes",
    "showkeys",
    "lineno",
    "epstopdf",
    "xspace",
    "etoolbox",
    "parskip",
    "indentfirst",
    "amsrefs",
    "cite",
    "authblk",
    "datetime",
    "lastpage",
    "afterpage",
    "pdfsync",
    "placeins",
    "framed",
    "mdframed",
    "tcolorbox",
    "comment",
    "verbatim",
    "listings",
    "environ",
    "ifthen",
    "calc",
    "kvoptions",
    "xkeyval",
}


@dataclass
class Extracted:
    file: str
    env: Env
    order: float
    taxon: Taxon
    number: str | None
    page: int | None
    digest_id: str
    labels: list[str]
    unit: SectionUnit | None = None
    body: str = ""
    uses: list[str] = field(default_factory=list)


@dataclass
class ExtractReport:
    citekey: str
    slug: str
    numbering: str = "aux"
    # results whose number came from counting rather than from the .aux, however the paper compiled
    emulated: int = 0
    compile_error: str | None = None
    by_taxon: dict[str, int] = field(default_factory=dict)
    sections: int = 0
    uses: int = 0
    expanded: set[str] = field(default_factory=set)
    block: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    unknown_envs: dict[str, str] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)

    def summary(self) -> str:
        total = sum(self.by_taxon.values())
        by = ", ".join(f"{n} {t}" for t, n in sorted(self.by_taxon.items(), key=lambda x: (-x[1], x[0])))
        lines = [f"Extracted {total} results ({by}); {self.sections} sections"]
        lines.append(f"\\uses recorded: {self.uses}")
        lines.append(
            f"Macros expanded: {len(self.expanded)}"
            + (f" ({', '.join(sorted(self.expanded))})" if self.expanded else "")
            + f"; macro block: {len(self.block)} definition(s)"
            + (f" ({', '.join(self.block)})" if self.block else "")
        )
        lines.append(
            "Packages required: " + (", ".join(self.requires) if self.requires else "none beyond amsmath, amsthm")
        )
        if self.numbering == "aux" and self.emulated:
            lines.append(
                f"Numbering: from the paper's .aux, except {self.emulated} unlabelled result(s) counted by emulation"
            )
        elif self.numbering == "aux":
            lines.append("Numbering: from the paper's .aux")
        else:
            lines.append(
                "Numbering: emulated" + (f" (compile failed: {self.compile_error})" if self.compile_error else "")
            )
        for env, hint in self.unknown_envs.items():
            lines.append(f"Environment {env} is not declared in this quilt; add {hint}")
        for s in self.skipped:
            lines.append(f"Skipped: {s}")
        return "\n".join(lines)


def _today() -> str:
    fixed = os.environ.get("LOOM_FIXED_TIME")
    if fixed:
        return fixed[:10]
    return datetime.now(UTC).date().isoformat()


def _store_home(result: ScanResult, citekey: str) -> Path | None:
    """The work's directory in the store, or None when nothing readable is filed for it.

    Extraction must still work with no document at all (DR-198), so everything that depends on one asks here first.
    """
    from loom.refs.fetch import work_dir
    from loom.refs.pages import read_map

    entry = result.bib.get(citekey)
    if entry is None:
        return None
    home = work_dir(result.quilt.root, entry)
    return home if read_map(home) is not None and (home / "paper.pdf").is_file() else None


def _page_of(home: Path, citekey: str, taxon: str, number: str | None, statement: str, hint: int | None) -> int | None:
    """The page of the filed copy a result sits on, or None when it cannot be told.

    **The page is found in the work's own committed page text, never asserted.** The `.aux` gives an exact page when the paper compiled, but it is the page of the PDF *that compile produced*, which need not be the artifact in the store: a preprint and its published version differ by exactly this. So the aux page is a hint to check first, and what is recorded is a page whose text actually carries the result.

    The printed label — `Proposition 2.1` — is what is searched for, because it is on the page in the form the reader sees, while the statement is LaTeX. A forward reference names the label before the statement arrives, so where several pages carry it the one that also carries the statement's own prose wins.

    Parameters
    ----------
    home : Path
        The work's directory in the store, holding `pages/`.
    citekey : str
    taxon : str
        The result's kind as printed, `Proposition`.
    number : str or None
        Its number; an unnumbered result has no printed label to find and gets no page.
    statement : str
        The result's LaTeX, for choosing between pages that share the label.
    hint : int or None
        The page the `.aux` gave, checked before anything is searched.

    Returns
    -------
    int or None
    """
    from loom.refs.pages import read_page
    from loom.refs.search import find_in_page, grep_work, words_not_on_page

    if not number or not (home / "pages").is_dir():
        return None
    label = f"{taxon} {number}"
    if hint is not None and hint > 0:
        text = read_page(home, hint)
        if text and find_in_page(text, label):
            return hint
    hits = [h.page for h in grep_work(home, citekey, label)]
    if not hits:
        return None
    if len(hits) == 1:
        return hits[0]
    return min(hits, key=lambda p: len(words_not_on_page(statement, read_page(home, p) or "")))


def _body_text(env: Env, clean: str) -> str:
    """The statement: the environment's body minus nested theorem-like environments and proofs."""
    pieces: list[str] = []
    pos = env.body_start
    for child in env.children:
        if child.theorem_like or child.is_proof:
            if child.start > pos:
                pieces.append(clean[pos : child.start])
            pos = child.end
    if env.body_end > pos:
        pieces.append(clean[pos : env.body_end])
    text = "".join(pieces)
    lines = [ln.rstrip() for ln in text.split("\n")]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


# Primitives that make a definition a program rather than an abbreviation. A macro whose body uses any of them is
# kept as written: expanding it textually runs the program badly. Behrend-Fantechi's `\\Bbb` is one, and eight passes
# of expansion unrolled it into its own error-message trap in the middle of two statements.
_NOT_SIMPLE = re.compile(
    r"\\(ifmmode|if[a-z@]*|let|def|edef|gdef|xdef|errmessage|expandafter|csname|relax|next|Err@|futurelet)(?![A-Za-z@])"
)


def is_simple(mac: Macro) -> bool:
    """Whether a macro is an abbreviation that textual expansion reproduces faithfully: no control flow, no definitions, and no reference to itself."""
    body = mac.body or ""
    if _NOT_SIMPLE.search(body):
        return False
    return not re.search(r"\\" + re.escape(mac.name) + r"(?![A-Za-z@])", body)


def expand_macros(text: str, macros: dict[str, Macro], max_passes: int = 8) -> tuple[str, set[str]]:
    """Textually expand the paper's simple macros in `text`; returns the text and the names expanded."""
    expanded: set[str] = set()
    for _ in range(max_passes):
        out: list[str] = []
        pos = 0
        changed = False
        while True:
            m = _CMD.search(text, pos)
            if m is None:
                out.append(text[pos:])
                break
            mac = macros.get(m.group(1))
            if mac is None or not is_simple(mac):
                out.append(text[pos : m.end()])
                pos = m.end()
                continue
            has_default = mac.default is not None
            spec = ("o" if has_default else "") + "m" * max(mac.args - (1 if has_default else 0), 0)
            vals, _spans, after = read_args(text, m.end(), spec) if spec else ([], [], m.end())
            args: list[str] = []
            if has_default:
                args.append(vals[0] if vals and vals[0] is not None else (mac.default or ""))
                vals = vals[1:]
            if any(v is None for v in vals):
                out.append(text[pos : m.end()])
                pos = m.end()
                continue
            args.extend(v or "" for v in vals)
            body = re.sub(
                r"\\xspace(?![A-Za-z@])", "", expand_macro(mac, args)
            )  # a no-op in math and harmful before ^ or _
            out.append(text[pos : m.start()])
            out.append(body)
            if body and body[-1].isalpha() and after < len(text) and text[after].isalpha():
                out.append(" ")
            pos = after
            changed = True
            expanded.add(m.group(1))
        text = "".join(out)
        if not changed:
            break
    return text, expanded


def _definitions(raw: str) -> dict[str, str]:
    """Raw definition text per macro name in a preamble closure, for the macro block; the last definition of a name wins."""
    raw = expand_definition_aliases(raw)
    defs: dict[str, str] = {}
    for m in re.finditer(r"\\(?:new|renew|provide)command\*?\s*\{?\\([A-Za-z@]+)\}?", raw):
        pos = m.end()
        while True:
            _v, _s, after = read_args(raw, pos, "o")
            if after == pos:
                break
            pos = after
        p = raw.find("{", pos)
        if p < 0:
            continue
        end = match_group(raw, p)
        if end > 0:
            defs[m.group(1)] = raw[m.start() : end]
    for m in re.finditer(r"\\def\s*\\([A-Za-z@]+)", raw):
        p = raw.find("{", m.end())
        if p < 0:
            continue
        end = match_group(raw, p)
        if end > 0:
            defs[m.group(1)] = raw[m.start() : end]
    for m in re.finditer(r"\\DeclareMathOperator(\*?)\s*\{\\([A-Za-z@]+)\}\s*\{", raw):
        end = match_group(raw, m.end() - 1)
        if end > 0:
            body = raw[m.end() : end - 1]
            defs[m.group(2)] = f"\\newcommand{{\\{m.group(2)}}}{{\\operatorname{m.group(1)}{{{body}}}}}"
    for m in re.finditer(r"\\let\s*\\([A-Za-z@]+)\s*=?\s*\\[A-Za-z@]+", raw):
        defs[m.group(1)] = m.group(0)
    for m in re.finditer(
        r"\\(?:New|Renew|Provide|Declare)DocumentCommand\s*\{?\\([A-Za-z@]+)\}?\s*\{[^}]*\}\s*\{", raw
    ):
        end = match_group(raw, m.end() - 1)
        if end > 0:
            defs[m.group(1)] = raw[m.start() : end]
    return defs


def _env_definitions(raw: str) -> dict[str, str]:
    """Raw definition text per environment the reference declares with \\newenvironment or enumitem's \\newlist (with its \\setlist lines), keyed by environment name."""
    defs: dict[str, str] = {}
    for m in re.finditer(r"\\(?:new|renew)environment\*?\s*\{([A-Za-z*]+)\}", raw):
        pos = m.end()
        while True:
            _v, _s, after = read_args(raw, pos, "o")
            if after == pos:
                break
            pos = after
        p1 = raw.find("{", pos)
        e1 = match_group(raw, p1) if p1 >= 0 else -1
        p2 = raw.find("{", e1) if e1 > 0 else -1
        e2 = match_group(raw, p2) if p2 >= 0 else -1
        if e2 > 0:
            defs[m.group(1)] = raw[m.start() : e2]
    for m in re.finditer(r"\\newlist\s*\{([A-Za-z*]+)\}\s*\{[^}]*\}\s*\{\d+\}", raw):
        name = m.group(1)
        parts = [m.group(0)]
        for sm in re.finditer(r"\\setlist\s*\[" + re.escape(name) + r"(?:,[^\]]*)?\]\s*\{", raw):
            end = match_group(raw, sm.end() - 1)
            if end > 0:
                parts.append(raw[sm.start() : end])
        defs[name] = "\n".join(parts)
    return defs


def _provenance(result: ScanResult, citekey: str, src: Path) -> tuple[str, str | None]:
    """What this digest was extracted from, and what the bibliography cites it as.

    Two facts, not two candidates for one. The statements and their numbers come from the artifact that was parsed; the work a reader will open is whatever the entry cites. When those differ -- an arXiv source against a published DOI -- every locator is unverified, which `loom:unverified-locators` says and this pair is what lets it (DR-109).
    """
    entry = result.bib.get(citekey)
    published = next((str(w) for w in identify(entry) if w.published), None) if entry else None
    # the artifact is decided by where the source actually sits: a path inside the store names its own work
    resolved = src.resolve()
    parts = resolved.parts
    if "storage" in parts:
        i = len(parts) - 1 - parts[::-1].index("storage")
        if len(parts) > i + 2:
            from loom.refs.fetch import recorded_source

            # the directory names the work; what was fetched into it may be another version of it (src.json)
            fetched = recorded_source(Path(*parts[: i + 3]))
            return fetched or str(WorkId(parts[i + 1], parts[i + 2])), published
    if entry is not None:
        eprint = next((str(w) for w in identify(entry) if w.preprint), None)
        if eprint:
            return eprint, published
        if published:
            return published, published
    return f"local:{src.name}", published


def extract_digest(
    result: ScanResult, citekey: str, src: Path, *, engine: str | None = None, compile: bool = True
) -> tuple[str, ExtractReport]:
    """Return the digest file text for `citekey` extracted from the paper whose main file is `src`, and a report."""
    slug = citekey_slug(citekey)
    report = ExtractReport(citekey=citekey, slug=slug)
    paper_dir = src.resolve().parent
    master_rel = src.name
    found, outside = closure_of(paper_dir, src.resolve())
    files: dict[str, SourceFile] = {}
    for rel, path in found.items():
        if path.suffix.lower() in TEXT_EXTS:
            files[rel] = read_source(paper_dir, rel)
    if master_rel not in files:
        files[master_rel] = read_source(paper_dir, master_rel)
    master = files[master_rel]
    closure = build_closure(master, paper_dir, files, parse_directives(master), foreign=True)
    taxa = closure.taxa
    exp = expand_master(master, paper_dir, files)
    units = find_sections(exp, files)
    theorem_names = set(taxa)
    envs_by_file = {}
    for rel in [master_rel, *[f for f in exp.reached if f != master_rel]]:
        if rel not in files:
            continue
        s = files[rel]
        body = document_start(s) if rel == master_rel else None
        envs_by_file[rel] = scan_environments(s, theorem_names, body or 0)

    aux_numbers: dict[str, AuxNumber] = {}
    if compile:
        with tempfile.TemporaryDirectory(prefix="loom-extract-") as tmp:
            staged = stage_sources(paper_dir, Path(tmp) / "src", outside)
            eng = engine or closure.engine or "pdflatex"
            res = compile_tex(staged, master_rel, Path(tmp) / "out", eng, halt_on_error=False)
            if res.aux is not None and res.aux.exists():
                aux_numbers = parse_aux(res.aux.read_text(errors="replace"))
        if not aux_numbers:
            report.numbering = "emulated"
            report.compile_error = res.errors[0] if res.errors else ("latexmk produced no .aux" if not res.ok else None)
    else:
        report.numbering = "emulated"

    events: list[tuple[float, int, str, object]] = []
    for u in units:
        events.append((float(u.exp_start), 0, "heading", u))
    for m in re.finditer(r"\\appendix\b", exp.text):
        events.append((float(m.start()), 0, "appendix", None))
    for rel, fe in envs_by_file.items():
        for env in fe.theorem_envs:
            e = exp.exp_offset(rel, env.start)
            if e is None:
                continue
            events.append((float(e), 1, "env", (rel, env)))
    events.sort(key=lambda x: (x[0], x[1]))

    num = Numbering(taxa)
    unit_numbers: dict[int, str | None] = {}
    results: list[Extracted] = []
    label_to_id: dict[str, str] = {}
    starred = 0
    for off, _p, kind, payload in events:
        if kind == "appendix":
            num.mark_appendix()
        elif kind == "heading":
            unit = payload
            assert isinstance(unit, SectionUnit)
            n = num.heading(unit.name, unit.starred)
            if unit.labels and unit.labels[0] in aux_numbers and aux_numbers[unit.labels[0]].number:
                n = aux_numbers[unit.labels[0]].number
            unit_numbers[id(unit)] = n
        else:
            assert isinstance(payload, tuple)
            rel, env = payload
            taxon = taxa[env.name]
            n = num.theorem(taxon)
            clean = files[rel].clean
            labels = [lab for lab, _ in labels_in(clean, env.own_ranges())]
            page = None
            from_aux = False
            for lab in labels:
                an = aux_numbers.get(lab)
                if an is not None and an.number and n is not None:
                    n = an.number
                    num.resync(taxon, n)
                    page = an.page
                    from_aux = True
                    break
                if an is not None and an.page is not None:
                    page = an.page
            if n is not None and not from_aux:
                # an unlabelled result keeps the number the emulation gave it, even when the paper compiled
                report.emulated += 1
            abbrev = ABBREV.get(taxon.name.lower(), re.sub(r"[^a-z0-9]", "", taxon.env.lower()) or "res")
            if n is None:
                starred += 1
                local = f"{abbrev}-star-{starred}"
            else:
                local = f"{abbrev}-{n}"
            digest_id = f"{slug}-{local}"
            if any(r.digest_id == digest_id for r in results):
                report.skipped.append(
                    f"{taxon.name} {n} at {rel}:{files[rel].line_of(env.start)}: duplicate number {n}"
                )
                continue
            rec = Extracted(rel, env, off, taxon, n, page, digest_id, labels)
            results.append(rec)
            for lab in labels:
                label_to_id.setdefault(lab, digest_id)

    for r in results:
        containing = [
            u for u in units if u.level <= 2 and u.exp_start <= r.order < u.exp_end and unit_numbers.get(id(u))
        ]
        r.unit = max(containing, key=lambda u: u.level) if containing else None

    body_labels: set[str] = set()
    for r in results:
        raw_body = _body_text(r.env, files[r.file].clean)
        for m in _LABEL.finditer(raw_body):
            body_labels.add(norm_label(m.group(1)))

    def rewrite(text: str) -> str:
        text, names = expand_macros(text, closure.macros)
        report.expanded.update(names)
        text = _LABEL.sub(lambda m: f"\\label{{{slug}-{norm_label(m.group(1))}}}", text)

        def ref_repl(m: re.Match[str]) -> str:
            cmd = m.group(1)
            outs: list[str] = []
            for raw_lab in m.group(2).split(","):
                lab = norm_label(raw_lab)
                if not lab:
                    continue
                if lab in label_to_id:
                    outs.append(f"\\ref{{{label_to_id[lab]}}}")
                elif lab in body_labels:
                    outs.append(f"\\{'eqref' if cmd == 'eqref' else 'ref'}{{{slug}-{lab}}}")
                else:
                    an = aux_numbers.get(lab)
                    number = an.number if an is not None and an.number else "??"
                    outs.append(f"({number})" if cmd == "eqref" else number)
            return ", ".join(outs)

        return _REF.sub(ref_repl, text)

    for rel, fe in envs_by_file.items():
        env_index = {(r.file, r.env.start): r for r in results}
        for proof in fe.proofs:
            att = fe.attachments.get(proof.start)
            stmt = att.statement if att is not None else None
            if stmt is None and att is not None and att.fallback is not None:
                stmt = att.fallback.statement
            if stmt is None:
                continue
            hit = env_index.get((rel, stmt.start))
            if hit is None:
                continue
            ptext, _ = expand_macros(
                files[rel].clean[proof.start : proof.end], closure.macros
            )  # \thmref-style wrappers
            for m in _REF.finditer(ptext):
                for raw_lab in m.group(2).split(","):
                    lab = norm_label(raw_lab)
                    target = label_to_id.get(lab)
                    if target and target != hit.digest_id and target not in hit.uses:
                        hit.uses.append(target)

    quilt_env_by_name: dict[str, str] = {}
    for env_name_q, tq in sorted(
        result.taxa.items(), key=lambda kv: (not kv[1].numbered, kv[1].env != kv[1].name.lower(), kv[0])
    ):
        quilt_env_by_name.setdefault(
            tq.name.lower(), env_name_q
        )  # a numbered environment of that display name first, never the starred twin
    used_names: set[str] = set()
    out: list[str] = []
    extracted_from, published_as = _provenance(result, citekey, src)
    out.append(f"% !LOOM digest: {citekey}")
    out.append(f"% !LOOM prefix: {slug}")  # declared, not derived, so the ids survive a citekey rename
    out.append(f"% !LOOM extracted-from: {extracted_from}")
    if published_as and published_as != extracted_from:
        out.append(f"% !LOOM published-as: {published_as}")
    out.append("% !LOOM method: extract")
    out.append(f"% !LOOM created: {_today()}")
    if report.numbering == "emulated":
        out.append("% !LOOM numbering: emulated")
    elif report.emulated:
        # A compile that succeeded does not mean every number was read from it. A digest that says nothing claims
        # compiled numbers throughout, and Behrend-Fantechi's said nothing while every result after its first
        # definition was counted -- and counted wrongly (contract §2.9).
        out.append("% !LOOM numbering: mixed")
    dm = result.default_master
    quilt_loaded = loaded_packages(result.closures[dm]) if dm and dm in result.closures else set()
    report.requires = sorted(loaded_packages(closure) - ALWAYS_LOADED - PRESENTATION - quilt_loaded)
    header_end = len(out)  # the requires: line is inserted here once the macro block is known

    body_lines: list[str] = []
    body_lines.append("\\section*{Overview}")
    overview = _overview(units, exp, rewrite)
    body_lines.append(overview if overview else "\\incomplete{Overview not extracted; the paper has no introduction.}")
    body_lines.append("")
    setup_env = quilt_env_by_name.get("theorem", "theorem")
    body_lines.append(f"\\begin{{{setup_env}}}[{{\\cite[Standing assumptions]{{{citekey}}}}}]\\label{{{slug}-setup}}")
    conventions = _conventions(exp, rewrite)
    body_lines.append(conventions or "\\incomplete{Standing assumptions not extracted; see the paper.}")
    body_lines.append(f"\\end{{{setup_env}}}")
    body_lines.append("")
    # **Every result that can be located gets its page**, so a digest node's locator points into the paper rather than only naming the result. The aux gives one when the paper compiled; the store's page text is what confirms it, and what supplies it when there was no compile at all — which is the state every `--no-compile` extraction is in.
    home = _store_home(result, citekey)
    if home is not None:
        for r in results:
            r.page = _page_of(home, citekey, r.taxon.name, r.number, _body_text(r.env, files[r.file].clean), r.page)

    written_units: set[int] = set()
    for r in sorted(results, key=lambda x: x.order):
        chain: list[SectionUnit] = []
        cur: SectionUnit | None = r.unit
        while cur is not None:
            if unit_numbers.get(id(cur)) and cur.level <= 2:
                chain.append(cur)
            cur = cur.parent
        for su in reversed(chain):
            if id(su) in written_units:
                continue
            written_units.add(id(su))
            cmd = "section" if su.level == 1 else "subsection"
            title = rewrite(su.title.strip())
            body_lines.append(f"\\{cmd}{{{title}}}\\label{{{slug}-sec-{unit_numbers[id(su)]}}}")
            body_lines.append("")
        env_name = quilt_env_by_name.get(r.taxon.name.lower())
        if env_name is None:
            env_name = r.taxon.env
            report.unknown_envs[r.taxon.env] = f"\\newtheorem{{{r.taxon.env}}}[theorem]{{{r.taxon.name}}}"
        locator = f"{r.taxon.name} {r.number}" if r.number else f"{r.taxon.name} (unnumbered)"
        if r.env.optarg:
            locator += f" ({rewrite(r.env.optarg.strip())})"
        if r.page is not None:
            locator += f", p.~{r.page}"
        statement = rewrite(_body_text(r.env, files[r.file].clean))
        r.body = statement
        used_names.update(_CMD.findall(statement) + _CMD.findall(locator))
        body_lines.append(f"\\begin{{{env_name}}}[{{\\cite[{locator}]{{{citekey}}}}}]\\label{{{r.digest_id}}}")
        if r.uses:
            body_lines.append(f"\\uses{{{', '.join(r.uses)}}}")
            report.uses += len(r.uses)
        if statement:
            body_lines.append(statement)
        body_lines.append(f"\\end{{{env_name}}}")
        body_lines.append("")
        report.by_taxon[r.taxon.name] = report.by_taxon.get(r.taxon.name, 0) + 1
    report.sections = len(written_units)
    used_names.update(_CMD.findall(overview))

    defs = _definitions(closure.raw_text())
    residue = sorted(n for n in used_names if n in defs and n not in report.expanded)
    block: list[str] = []
    for name in residue:
        block.append(f"\\let\\{name}\\undefined")
        block.append(defs[name])
    env_defs = _env_definitions(closure.raw_text())
    used_envs = sorted({m for m in re.findall(r"\\begin\{([A-Za-z*]+)\}", "\n".join(body_lines)) if m in env_defs})
    for name in used_envs:
        block.append(env_defs[name])
        residue.append(f"env:{name}")
        if env_defs[name].startswith("\\newlist") and "enumitem" not in report.requires:
            report.requires.append("enumitem")
    report.block = residue
    if report.requires:
        out.insert(header_end, f"% !LOOM requires: {', '.join(sorted(report.requires))}")
    if block:
        out.append("")
        out.append("% !LOOM begin macros")
        out.extend(block)
        out.append("% !LOOM end macros")
    out.append("")
    out.extend(body_lines)
    text = "\n".join(out).rstrip("\n") + "\n"
    if header_end == 0:
        raise AssertionError("no header")
    return text, report


_CONVENTIONS_HEADING = re.compile(
    r"\\(?:(?:sub)*section|(?:sub)?paragraph)\*?\s*(?:\[[^\]]*\])?\s*\{((?:[^{}]|\{[^{}]*\})*)\}"
)
_CONVENTIONS_TITLE = re.compile(r"convention|notation|standing assumption|terminology", re.I)
_NEXT_HEADING = re.compile(
    r"\\(?:(?:sub)*section|(?:sub)?paragraph|chapter)\*?\s*[\[{]|\\begin\{proof\}|\\end\{document\}"
)
# A standing assumption stated as one sentence inside an ordinary paragraph, which is how Edidin and Graham state that
# every Chow group in their paper has rational coefficients. A sentence scoped to a section or a proof is not standing.
_STANDING = re.compile(
    r"\bThroughout\b|\bFor the (?:remainder|rest) of (?:the|this) (?:paper|article|note)\b"
    r"|\bWe (?:always |will )?work over\b|\bUnless (?:otherwise )?(?:stated|specified|mentioned|noted|indicated)\b"
    r"|\b(?:All|all|Every|every)\b[^.]{0,60}?\b(?:is|are) (?:always )?(?:assumed|supposed|taken|defined over)\b"
    r"|\bwe (?:always )?assume (?:throughout|that all|all)\b"
)
_SCOPED = re.compile(r"\bthis (?:section|subsection|proof|example|chapter|remark)\b", re.I)
# proofs under the names this corpus gives them: Romagny 2005's is `proo`
_PROOF = re.compile(r"\\begin\{(pro+f?|pf|dem\w*|preuve)\*?\}.*?\\end\{\1\*?\}", re.S)
_ENV_MARK = re.compile(r"\\(?:begin|end)\{[^{}]*\}(?:\{[^{}]*\})?\s*")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z\\$])")
STANDING_MAX = 6  # sentences, when they are gathered from the body rather than found under a heading
CONVENTIONS_CAP = 1500  # characters: a conventions section can run to pages, and the node is read on every hover


def _conventions(exp: Expansion, rewrite: object) -> str:
    """The paper's standing assumptions for the `-setup` node, verbatim, or '' when it states none where a machine can find them.

    A heading that names conventions, notation, terminology or standing assumptions (its first three paragraphs), else every sentence outside a proof that states one -- "Throughout", "For the remainder of the paper", "We work over", "Unless otherwise stated", "All schemes are assumed" -- unless it is scoped to a section or a proof. Five study sightings: every answer about a result's hypotheses named the empty stub as its limit, and the text was usually in the paper a few lines from where the agent looked.
    """
    begin = exp.text.find("\\begin{document}")
    body = re.sub(r"(?<!\\)%[^\n]*", "", exp.text[begin:] if begin >= 0 else exp.text)
    chosen = ""
    for m in _CONVENTIONS_HEADING.finditer(body):
        if _CONVENTIONS_TITLE.search(m.group(1)):
            rest = body[m.end() :]
            stop = _NEXT_HEADING.search(rest)
            paras = [p.strip() for p in re.split(r"\n\s*\n", rest[: stop.start() if stop else len(rest)]) if p.strip()]
            chosen = "\n\n".join(paras[:3])
            if chosen:
                break
    if not chosen:
        found: list[str] = []
        for para in re.split(r"\n\s*\n", _PROOF.sub(" ", body)):
            for sentence in _SENTENCE_END.split(" ".join(_ENV_MARK.sub(" ", para).split())):
                if _STANDING.search(sentence) and not _SCOPED.search(sentence) and sentence not in found:
                    found.append(sentence)
        if found:
            # gathered, not found under a heading: a sentence can be scoped more narrowly than it reads, and the reader is told so
            chosen = "\n\n".join(
                [
                    "\\emph{Sentences of the paper that state an assumption, gathered by the extractor; check each one's scope.}"
                ]
                + found[:STANDING_MAX]
            )
    if not chosen:
        return ""
    assert callable(rewrite)
    # a heading's own label rides in with the text after it, and would name the -setup node a second time
    text = re.sub(r"\\label\{[^{}]*\}\s*", "", str(rewrite(chosen))).strip()
    if len(text) > CONVENTIONS_CAP:
        cut = text.rfind(". ", 0, CONVENTIONS_CAP)
        text = (
            text[: cut + 1 if cut > 0 else CONVENTIONS_CAP]
            + "\n\\emph{The paper's conventions continue beyond this; see the paper.}"
        )
    return text


def _overview(units: list[SectionUnit], exp: Expansion, rewrite: object) -> str:
    """Seed for the overview: the first two prose paragraphs of the introduction (or the first section), macros expanded."""
    intro = next((u for u in units if u.level == 1 and re.search("introduction", u.title, re.I)), None)
    if intro is None:
        intro = next((u for u in units if u.level == 1), None)
    if intro is None:
        return ""
    start = exp.exp_offset(intro.file, intro.heading_end)
    if start is None:
        return ""
    text = exp.text[start : intro.exp_end]
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text)]
    chosen: list[str] = []
    for p in paragraphs:
        if not p or p.startswith("\\begin") or p.startswith("\\label") or p.startswith("\\sub"):
            if chosen:
                break
            continue
        chosen.append(re.sub(r"[ \t]+\n", "\n", p))
        if len(chosen) == 2:
            break
    joined = "\n\n".join(chosen)
    assert callable(rewrite)
    return str(rewrite(joined))
