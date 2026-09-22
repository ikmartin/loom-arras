"""Lint: the checks that turn scan facts into diagnostics (book 5.14).

Everything here reads the scan result and emits; nothing is stored. `[lint] disable` silences publisher codes only.
"""

from __future__ import annotations

import re
from pathlib import Path

from loom.refs.identity import declared, parse
from loom.refs.resolve import load as load_candidates
from loom.scan.bib import citekey_slug
from loom.scan.diagnostics import can_disable
from loom.scan.digests import digest_header, extracted_from, missing_packages, published_as, source_version
from loom.scan.directives import KNOWN_KEYS, REGION_KEYS
from loom.scan.edges import EdgeResult
from loom.scan.graph import Graph
from loom.scan.model import Diagnostic, Fix, Location
from loom.scan.nodes import Assembly, NodeRec
from loom.scan.scan import ScanResult

COMMON_THEOREM_ENVS = {
    "theorem",
    "thm",
    "lemma",
    "lem",
    "proposition",
    "prop",
    "corollary",
    "cor",
    "definition",
    "defn",
    "def",
    "remark",
    "rmk",
    "rem",
    "example",
    "exmp",
    "conjecture",
    "conj",
    "claim",
    "question",
    "notation",
    "construction",
    "convention",
    "assumption",
    "hypothesis",
    "axiom",
    "postulate",
    "fact",
    "observation",
    "setting",
    "condition",
    "problem",
    "exercise",
}
LOOM_MACROS = ("uses", "incomplete", "nest")


def lint(result: ScanResult, edges: EdgeResult, graph: Graph) -> list[Diagnostic]:
    asm = result.assembly
    files = result.files
    diags: list[Diagnostic] = list(result.diagnostics) + list(edges.diagnostics)
    for w in result.quilt.config.warnings:
        diags.append(Diagnostic("warning", "loom:unknown-config-key", w, [Location("config.toml", 1)]))
    for w in result.quilt.config.deprecations:
        diags.append(Diagnostic("warning", "loom:deprecated-config-key", w, [Location("config.toml", 1)]))
    from loom.history.checks import quick_checks
    from loom.history.ledger import load_history

    diags.extend(quick_checks(result, load_history(result.quilt.history_dir)))
    if not result.masters and result.canon_files:
        # every view that is about nodes is empty until a landmark is drafted; the viewer shows that, and this says how to end it
        newest = result.canon_files[-1]
        drafting = result.quilt.config.drafting
        diags.append(
            Diagnostic(
                "info",
                "loom:no-live-document",
                f"nothing is being worked on: {drafting}/ holds no document, so the quilt defines no nodes",
                [],
                fixes=[
                    Fix(
                        f"start from the newest landmark, {newest}",
                        f"loom draft {newest} --to {drafting}/{Path(newest).name}",
                    )
                ],
            )
        )
    digest_keys = set(asm.digest_files.values())
    slugs = {citekey_slug(k) for k in result.bib} | {citekey_slug(k) for k in digest_keys}
    for path, directives in asm.directives.items():
        for d in directives:
            if d.key == "basis" and not any(
                n.kind == "environment" and n.file == path and any(a <= d.offset < b for a, b in n.own)
                for n in asm.nodes.values()
            ):
                diags.append(
                    Diagnostic(
                        "warning",
                        "loom:misplaced-basis",
                        "% !LOOM basis belongs inside one theorem-like block",
                        [Location(path, d.line)],
                    )
                )
    # The basis is inferred during every live scan; an unresolved basis is a review task, not a proof waiver.
    for key, n in asm.nodes.items():
        if n.kind != "environment" or n.conflict_of:
            continue
        if n.basis == "unclassified" and n.reached_by:
            diags.append(
                Diagnostic(
                    "warning",
                    "loom:needs-classification",
                    f"{key} needs classification: {n.basis_reason}",
                    [_loc(result, n)],
                    [key],
                )
            )
        if n.basis == "local-proof" and not n.proofs and not n.inline_proof and not n.incomplete:
            diags.append(
                Diagnostic("warning", "loom:missing-proof", f"{key} ({n.taxon}) has no proof", [_loc(result, n)], [key])
            )
        if n.basis in ("expository", "assumption", "open-claim") and n.proofs:
            diags.append(
                Diagnostic("info", "loom:unexpected-proof", f"{key} ({n.taxon}) has a proof", [_loc(result, n)], [key])
            )
    # references to loose nodes; equations in proofs referenced from elsewhere
    for e in edges.edges:
        if e.via == "nested":
            continue
        target = asm.nodes.get(e.to)
        source = asm.nodes.get(e.src)
        if target is None or source is None:
            continue
        src_masters = set(source.reached_by)
        if target.file in asm.digest_files:  # digests are loose by construction (8.1.2)
            continue
        loose_to_loose = not src_masters and not target.reached_by and target.file != source.file
        if (src_masters and not (src_masters & set(target.reached_by))) or loose_to_loose:
            sev = "error" if any(m in result.masters for m in src_masters) else "info"
            diags.append(
                Diagnostic(
                    sev,
                    "loom:reference-to-loose",
                    f"{e.src} refers to {e.to}, which its master does not reach",
                    [Location(e.file, e.line)],
                    [e.src, e.to],
                )
            )
        if (
            target.kind == "proof"
            and e.label
            and target.of
            and e.src != target.key
            and not e.src.startswith(target.key)
        ):
            region = asm.regions.get(f"{target.key}#{e.label}")
            if region is not None:
                diags.append(
                    Diagnostic(
                        "warning",
                        "loom:equation-in-proof-referenced",
                        f"{e.src} references {e.label}, which lies inside the proof {target.key}",
                        [Location(e.file, e.line)],
                        [e.src, target.key],
                    )
                )
    # uses vs refs in proofs
    for key, n in asm.nodes.items():
        if n.kind != "proof":
            continue
        refs = [asm.labels.get(x) for x in edges.refs_in.get(key, [])]
        ref_keys = {_stmt(asm, r) for r in refs if r}
        uses = edges.uses_in.get(key, [])
        use_keys = {_stmt(asm, asm.labels.get(u)) for u in uses if asm.labels.get(u)}
        for rk in sorted(k for k in ref_keys - use_keys if k):
            if rk != n.of:
                diags.append(
                    Diagnostic(
                        "info",
                        "loom:uses-missing",
                        f"{key} references {rk} but its \\uses does not list it",
                        [_loc(result, n)],
                        [key],
                    )
                )
        for uk in sorted(k for k in use_keys - ref_keys if k):
            if True:
                diags.append(
                    Diagnostic(
                        "info",
                        "loom:uses-unused",
                        f"{key} lists {uk} in \\uses but never references it",
                        [_loc(result, n)],
                        [key],
                    )
                )
    # directives
    for path, ds in asm.directives.items():
        for d in ds:
            if (
                d.form == "unknown"
                or (d.form == "kv" and d.key not in KNOWN_KEYS)
                or (d.form in ("begin", "end") and d.key not in REGION_KEYS)
            ):
                diags.append(
                    Diagnostic(
                        "warning", "loom:unknown-directive", f"unknown directive {d.key}", [Location(path, d.line)]
                    )
                )
    # theorem-like environments the preamble does not declare
    for path, fe in asm.envs.items():
        seen: set[str] = set()
        for env in fe.all_envs():
            if env.name in result.taxa or env.name in seen or env.is_proof:
                continue
            if env.name in COMMON_THEOREM_ENVS:
                seen.add(env.name)
                diags.append(
                    Diagnostic(
                        "error",
                        "loom:unknown-environment",
                        f"environment {env.name} looks theorem-like but no master declares it; add % !LOOM environment: {env.name} = Name, plain",
                        [Location(path, files[path].line_of(env.start))],
                    )
                )
    # loom macros without loom.sty, and shadowed macros
    for master, closure in result.closures.items():
        exp = result.expansions[master]
        used = sorted({m for m in LOOM_MACROS if re.search(r"\\" + m + r"(?![A-Za-z@])", exp.text)})
        if used and not closure.loads_loom:
            names = ", ".join("\\" + m for m in used)
            diags.append(
                Diagnostic(
                    "error",
                    "loom:macros-unloaded",
                    f"{master} uses {names} but never loads loom.sty",
                    [Location(master, 1)],
                )
            )
        for frag in closure.fragments:
            if frag.file.endswith("loom.sty"):
                continue
            for m in LOOM_MACROS:
                if re.search(
                    r"\\(?:new|renew|provide)command\s*\{?\\" + m + r"\b", frag.src.clean[frag.start : frag.end]
                ):
                    diags.append(
                        Diagnostic(
                            "warning",
                            "loom:macro-shadowed",
                            f"{frag.file} defines \\{m}, which loom.sty also provides",
                            [Location(frag.file, 1)],
                        )
                    )
    # prefix vs citekeys
    if citekey_slug(result.quilt.config.prefix) in slugs:
        diags.append(
            Diagnostic(
                "warning",
                "loom:prefix-is-citekey",
                f"the id prefix {result.quilt.config.prefix} is also a bibliography key",
                [],
            )
        )
    # citekey slug collisions
    by_slug: dict[str, set[str]] = {}
    for k in set(result.bib) | digest_keys:
        by_slug.setdefault(citekey_slug(k), set()).add(k)
    for slug, keys in sorted(by_slug.items()):
        if len(keys) > 1:
            diags.append(
                Diagnostic(
                    "error",
                    "loom:citekey-slug-collision",
                    f"citekeys {', '.join(sorted(keys))} share the digest prefix {slug}",
                    [],
                )
            )
    # citations without digests
    undigested: dict[str, list[str]] = {}
    for c in edges.cites:
        # a citation inside a digest is the cited paper's own bibliography, not a work the author cites: counting them
        # listed thirty "undigested" citekeys of which three were the author's, and two agents took the rest as real
        if c.file in asm.digest_files:
            continue
        if c.postnote and c.citekey not in digest_keys:
            undigested.setdefault(c.citekey, []).append(c.src)
    for ck, srcs in sorted(undigested.items()):
        diags.append(
            Diagnostic(
                "info",
                "loom:undigested-citekey",
                f"{ck} is cited with a locator but has no digest",
                [],
                sorted(set(srcs)),
            )
        )
    # a cited work with no global identifier can never be deduplicated, fetched, or matched against another quilt's
    for ck in sorted({c.citekey for c in edges.cites}):
        entry = result.bib.get(ck)
        if entry is not None and not declared(entry):
            # a lookup already made is named here, read from refs/; lint itself never touches the network
            found = load_candidates(result.quilt.root, entry)
            if found:
                best = found[0]
                scheme, _, value = best.id.partition(":")
                field_name = {"doi": "doi", "zbl": "zbl", "mr": "mrnumber", "arxiv": "eprint"}.get(scheme, scheme)
                advice = f"a lookup found {best.id} ({best.strength} match, {best.source}); if it is the right work, add {field_name} = {{{value}}} to the entry"
            else:
                advice = (
                    "add doi = {...} or eprint = {...} to its bibliography entry, or look it up with loom refs resolve"
                )
            diags.append(
                Diagnostic(
                    "info",
                    "loom:unresolved-work",
                    f"{ck} states no identifier, so loom cannot name the work the same way on another machine; {advice}",
                    [],
                    [ck],
                )
            )
    for ck in sorted(digest_keys):
        if ck not in result.bib:
            diags.append(
                Diagnostic(
                    "warning", "loom:digest-without-bib", f"digest {ck} names a citekey not in the bibliography", []
                )
            )
    diags.extend(_no_readable_copy(result, digest_keys))
    # digest provenance against the bibliography, and requires: against the default master's preamble closure
    dm = result.default_master
    dm_closure = result.closures.get(dm) if dm else None
    for f, ck in sorted(asm.digest_files.items()):
        header = digest_header(asm, f)
        bib = result.bib.get(ck)
        got, cites_as = extracted_from(header), published_as(header)
        a, b = parse(got), parse(cites_as)
        why = None
        if a is not None and b is not None and a.preprint and b.published:
            why = f"was extracted from {got} but the bibliography cites {cites_as}"
        elif not got and header.get("method", "") == "extract":
            why = "does not say what it was extracted from"
        if why:
            diags.append(
                Diagnostic(
                    "warning",
                    "loom:unverified-locators",
                    f"digest {ck} {why}; its result numbers and page references are unverified against the version a reader will open",
                    [Location(f, 1)],
                )
            )
        sv = source_version(got)
        if bib is not None and bib.version and sv and bib.version != sv:
            diags.append(
                Diagnostic(
                    "warning",
                    "loom:version-mismatch",
                    f"digest {ck} was made from v{sv} but the bibliography cites v{bib.version}",
                    [Location(f, 1)],
                )
            )
        missing = missing_packages(asm, f, dm_closure)
        if missing:
            diags.append(
                Diagnostic(
                    "warning",
                    "loom:missing-package",
                    f"digest {ck} requires {', '.join(missing)}, which the preamble of {dm} does not load",
                    [Location(f, 1)],
                )
            )
    # loose files
    for path, src in files.items():
        if src.ignored or path in result.masters or path in asm.digest_files:
            continue
        if not any(path in e.reached for e in result.expansions.values()):
            node_keys = [k for k, n in asm.nodes.items() if n.file == path and n.kind in ("environment", "section")]
            diags.append(Diagnostic("info", "unreachable", f"no master reaches {path}", [Location(path, 1)], node_keys))
    # dependency cycles
    for cyc in graph.cycles():
        diags.append(
            Diagnostic(
                "warning",
                "loom:dependency-cycle",
                "statement dependencies form a cycle: " + " -> ".join(cyc + cyc[:1]),
                [],
                cyc,
            )
        )
    disabled = set(result.quilt.config.lint_disable)
    diags = [d for d in diags if not (d.code in disabled and can_disable(d.code))]
    diags.sort(
        key=lambda d: (
            {"error": 0, "warning": 1, "info": 2}[d.severity],
            d.code,
            d.locations[0].file if d.locations else "",
            d.locations[0].line if d.locations else 0,
        )
    )
    return diags


def _no_readable_copy(result: ScanResult, digest_keys: set[str]) -> list[Diagnostic]:
    """The artifact invariant (plan 0.13 §4, as relaxed): renderable content with no artifact behind it, or none that can be read.

    Renderable content is a digest file or a recorded result; a bibliography entry alone is not, and a work nobody has fetched is a perfectly good state. What backs it may be either artifact, and which one decides what can be done with it. **Source** is enough to check a statement against -- it is the paper's own LaTeX, better evidence than a page image -- but carries no pagination and no page to read, so it reports as `info`. **Nothing at all** is the state the invariant is about and reports as `warning`. Never an error either way: loom cannot fetch without consent, and a build must not fail for want of a document.

    A work the author has declared unreadable is silent here, and `refs build` lists it instead.
    """
    from loom.refs.fetch import work_dir
    from loom.refs.pages import read_map
    from loom.refs.proposals import load_results
    from loom.refs.unreadable import declarations

    root = result.quilt.root
    silent = declarations(root, "unreadable")
    out: list[Diagnostic] = []
    for ck in sorted(set(result.bib)):
        if ck in silent:
            continue
        if ck not in digest_keys and not load_results(root, ck):
            continue
        try:
            home = work_dir(root, result.bib[ck])
        except Exception:  # noqa: BLE001 -- an entry with no identifier has no home; loom:unresolved-work says so
            continue
        m = read_map(home)
        if m is not None and m.pages > 0:
            continue
        has_pdf, has_source = (home / "paper.pdf").is_file(), (home / "src").is_dir()
        if has_pdf:
            sev, what, how = "warning", "its pages have never been read", f"loom refs map {ck}"
        elif has_source:
            sev = "info"
            what = "loom holds its LaTeX and no PDF, so there is no page to read and its page locators are unverified"
            how = f"loom refs fetch {ck}, or loom refs add {ck} <FILE>"
        else:
            sev = "warning"
            what = "no copy of the paper is on this machine, so nothing it says can be checked against the paper"
            how = f"loom refs fetch {ck}, or loom refs add {ck} <FILE>"
        out.append(
            Diagnostic(
                sev,
                "loom:no-readable-copy",
                f"{ck} has a digest but {what}; {how}, or loom refs unreadable {ck} --why '...' when there is no document to hold",
                [],
                [ck],
            )
        )
    return out


def _stmt(asm: Assembly, key: str | None) -> str | None:
    if key is None:
        return None
    region = asm.regions.get(key)
    if region is not None:
        key = region.container
    n = asm.nodes.get(key)
    if n is not None and n.kind == "proof" and n.of:
        return n.of
    return key


def _loc(result: ScanResult, n: NodeRec) -> Location:
    return Location(n.file, result.files[n.file].line_of(n.start))
