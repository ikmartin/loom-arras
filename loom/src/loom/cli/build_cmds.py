"""`loom compile`, `loom source`, `loom check` (book 12.5)."""

from __future__ import annotations

from pathlib import Path

import click

from loom.cli._common import EXIT_CONTENT, ContentError, EnvError, find_session, note
from loom.cli._quilt import open_scan, quilt_option, require_text, resolve_key
from loom.cli.diagnostics import groups as diagnostic_groups
from loom.cli.diagnostics import has_errors, tally
from loom.cli.report import Group, Item, Progress, Report, counted
from loom.clock import stamp
from loom.reshape.linearize import flatten
from loom.scan.model import Diagnostic
from loom.scan.scan import ScanResult
from loom.tex.bundle import (
    Bundle,
    build_bundle,
    bundle_filename,
    draft_bundle,
    region_text,
    substituted_region,
    substituted_region_text,
)
from loom.tex.runner import ENGINE_FLAGS, CompileResult, compile_tex, normalise_engine


def engine_for(result: ScanResult, master: str, override: str | None = None) -> str:
    closure = result.closures.get(master)
    return normalise_engine(override or (closure.engine if closure else None) or result.quilt.config.engine)


def log_run(session: str | None, command: str, root: Path | None = None) -> None:
    """Append `command` to a session's command log, which is the scrollback a later sitting resumes from.

    The same resolver every other `--session` uses, and it never creates one: an unmatched value used to be mkdir'd at the quilt root, and the directory that left behind then shadowed the real run for every later command, so a whole sitting's annotations were filed under a run that did not exist.
    """
    if not session or root is None:
        return
    from loom.sessions import files_dir

    found = find_session(root, session)  # an unmatched value is an error, never a directory quietly created
    p = files_dir(root, found)
    p.mkdir(parents=True, exist_ok=True)
    with (p / "run.log").open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp()}  {command}\n")


#: Where a key's closure document is written and compiled, under the quilt root.
CLOSURES = Path("build") / "closures"


def write_bundle(result: ScanResult, b: Bundle) -> Path:
    """Write a key's closure document under build/closures/, for `loom compile KEY` and `loom check` to run latexmk on.

    Internal: `loom source KEY --closure` is how a reader or an agent gets the text, so nothing copies one elsewhere and nothing gitignores it.
    """
    root = result.quilt.root
    out = root / CLOSURES / bundle_filename(b.key)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(b.text, encoding="utf-8")
    return out


@click.command()
@click.argument("target", required=False, default=None)
@click.option("--engine", type=click.Choice(sorted(ENGINE_FLAGS)), default=None, help="Override the document's engine.")
@click.option(
    "--with",
    "with_file",
    default=None,
    metavar="FILE",
    help="Substitute a unified diff, a .tex file, or an annotation's proposed text for KEY's text; the quilt is not touched.",
)
@click.option("--draft", "draft_file", default=None, metavar="FILE", help="Compile a node file not yet in the quilt.")
@click.option(
    "--session", "run_dir", default=None, metavar="SESSION", envvar="LOOM_SESSION", help="Log this call to the session."
)
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def compile(  # noqa: A001
    target: str | None,
    engine: str | None,
    with_file: str | None,
    draft_file: str | None,
    run_dir: str | None,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Run latexmk from the root into build/<stem>/ for a master (default: the default master), or for a key.

    Compiling a key builds the document of its closure and runs latexmk on that, so `--with` previews a proposed diff and `--draft` a node that has no id yet: neither writes into the quilt, and a failure names the digests whose packages are missing.
    """
    result = open_scan(quilt_path)
    root = result.quilt.root
    parts = ["loom compile"] + ([target] if target else [])
    if with_file:
        parts += ["--with", with_file]
    if draft_file:
        parts += ["--draft", draft_file]
    missing: list[Diagnostic] = []
    if draft_file:
        if not result.masters:
            raise ContentError("the quilt has no master; compiling a draft needs a preamble")
        b = draft_bundle(result, Path(draft_file).expanduser())
        if b.missing:
            raise ContentError(f"the draft references unknown labels: {', '.join(b.missing)}")
        log_run(run_dir, " ".join(parts), root)
        out = write_bundle(result, b)
        label = f"the draft {Path(draft_file).name}"
        with Progress("compiling", 1) as p:
            p.item(label)
            res = compile_tex(
                root,
                str(out.relative_to(root)),
                root / CLOSURES / out.stem,
                engine_for(result, result.default_master or result.masters[0], engine),
            )
    elif target is None or target in result.masters or (root / target).is_file() and target.endswith(".tex"):
        if with_file:
            raise EnvError("--with substitutes one key's text; give a KEY rather than a master")
        master = target or result.default_master
        if master is None:
            raise EnvError("the quilt has no master")
        label = master
        log_run(run_dir, " ".join(parts), root)
        with Progress("compiling", 1) as p:
            p.item(master)
            res = compile_tex(root, master, root / "build" / Path(master).stem, engine_for(result, master, engine))
    else:
        key = resolve_key(result, target)
        require_text(result, key)
        if not result.masters:
            raise ContentError("the quilt has no master; compiling a key needs a preamble")
        override = None
        if with_file:
            override = substitution_for(result, key, with_file)
        b = build_bundle(result, key, override_text=override)
        log_run(run_dir, " ".join(parts), root)
        out = write_bundle(result, b)
        label = f"{key}'s closure" + (f" with {Path(with_file).name}" if with_file else "")
        with Progress("compiling", 1) as p:
            p.item(key)
            res = compile_tex(
                root,
                str(out.relative_to(root)),
                root / CLOSURES / out.stem,
                engine_for(result, result.default_master or result.masters[0], engine),
            )
        if res.usable == "failed":
            missing = missing_packages(result, b.closure + [key])
    compile_report(res, label, root, missing).emit(as_json)


def substitution_for(result: ScanResult, key: str, with_file: str) -> str:
    """Resolve `--with`: a file on disk, else an annotation id whose payload is the proposal it names.

    A file is tried first, because a path is what the option has always taken and a filename could otherwise be shadowed by an id. An annotation is accepted because the payload **is** the proposal — it is what `loom annotate --payload` was for — and asking an agent to copy its own suggestion into a file before compiling it is a step with nothing in it.
    """
    from loom.records.annotations import find_annotation
    from loom.records.store import Records

    root = result.quilt.root
    p = Path(with_file).expanduser()
    try:
        if p.is_file():
            return substituted_region(result, key, p)
        found = find_annotation(Records(root, result.quilt.history_dir).records, with_file)
        if found is None:
            raise EnvError(f"--with {with_file}: no such file, and no annotation has that id")
        _, ann = found
        if not ann.payload:
            raise ContentError(f"--with {with_file}: that annotation proposes no text")
        if ann.target_key != key:
            raise ContentError(f"--with {with_file}: that annotation is on {ann.target_key}, not {key}")
        return substituted_region_text(result, key, ann.payload)
    except OSError as exc:
        raise EnvError(f"--with {with_file}: {exc.strerror or exc}") from exc
    except ValueError as exc:
        raise ContentError(f"--with {with_file}: {exc}") from exc


def compile_report(res: CompileResult, label: str, root: Path, missing: list[Diagnostic] | None = None) -> Report:
    """The outcome of one compile, as `loom compile` reports it: exit 0 when it produced a PDF, whether or not the log carried warnings.

    A nonzero exit with a readable PDF and no `!` line is reported as warnings, not as a failure: latexmk exits nonzero on an undefined reference, and an agent told FAILED cannot tell its own proposal from a document that was already like that. `missing` are the digests' missing-package diagnostics, named before the error.
    """
    state = res.usable
    where = f"{res.outdir.relative_to(root).as_posix()}/"
    data = {
        "target": label,
        "state": state,
        "engine": res.engine,
        "outdir": where,
        "warnings": list(res.warnings),
        "errors": list(res.errors),
        "missing_packages": [d.to_dict() for d in missing or []],
    }
    if state == "ok":
        return Report(f"compiled {label} into {where} ({res.engine})", data=data)
    if state == "warnings":
        return Report(
            f"compiled {label} into {where} ({res.engine}), with {counted(len(res.warnings), 'warning')}",
            groups=[Group("warnings", [Item(w) for w in res.warnings], next=None)],
            data=data,
        )
    # a missing package is a digest's, so it is listed in full here rather than summarised as a cited work's
    groups = diagnostic_groups(missing or [], None)
    named = (
        f"; {counted(len({tuple(d.keys) for d in missing}), 'digest')} it includes requires a package that is missing"
        if missing
        else ""
    )
    return Report(
        f"{label} did not compile: {res.first_error}{named}", ok=False, exit=EXIT_CONTENT, groups=groups, data=data
    )


def missing_packages(result: ScanResult, keys: list[str]) -> list[Diagnostic]:
    """The `loom:missing-package` diagnostics of the digests among `keys`, named before a failed closure compile (book 8.11)."""
    files = {result.nodes[k].file for k in keys if k in result.nodes and result.nodes[k].digest}
    return [
        d for d in result.lint if d.code == "loom:missing-package" and any(loc.file in files for loc in d.locations)
    ]


@click.command()
@click.option(
    "--closures",
    type=click.Choice(["all", "stale", "none"]),
    default="stale",
    help="Which statements' closures to compile after the documents: all of them, or none; stale compiles none yet.",
)
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def check(closures: str, as_json: bool, quilt_path: str | None) -> None:
    """Lint, then compile every document, then the closures asked for. Exit 1 on any failure; the CI command.

    `loom lint` is the same check without LaTeX.
    """
    from loom.cli.lint_cmd import all_diagnostics

    result = open_scan(quilt_path)
    root = result.quilt.root
    diags = all_diagnostics(result)
    documents: list[dict[str, object]] = []
    compiled: list[dict[str, object]] = []
    keys = (
        [k for k, n in result.nodes.items() if n.kind == "environment" and n.digest is None]
        if closures == "all"
        else []
    )
    with Progress("compiling", len(result.masters) + len(keys)) as p:
        for master in result.masters:
            p.item(master)
            res = compile_tex(root, master, root / "build" / Path(master).stem, engine_for(result, master))
            bad = res.usable == "failed"
            documents.append({"document": master, "ok": not bad, "error": res.first_error if bad else None})
        for key in keys:
            p.item(key)
            b = build_bundle(result, key)
            out = write_bundle(result, b)
            res = compile_tex(
                root,
                str(out.relative_to(root)),
                root / CLOSURES / out.stem,
                engine_for(result, result.default_master or result.masters[0]),
            )
            bad = res.usable == "failed"
            compiled.append({"key": key, "ok": not bad, "error": res.first_error if bad else None})
    failed_docs = [d for d in documents if not d["ok"]]
    failed_closures = [c for c in compiled if not c["ok"]]
    failed = has_errors(diags, result) or bool(failed_docs) or bool(failed_closures)
    said = [tally(diags, result)]
    if documents:
        said.append(
            (
                f"{len(failed_docs)} of {counted(len(documents), 'document')} do not compile"
                if len(documents) > 1
                else "the document does not compile"
            )
            if failed_docs
            else (
                "the document compiles" if len(documents) == 1 else f"all {counted(len(documents), 'document')} compile"
            )
        )
    if compiled:
        said.append(
            (
                f"{len(failed_closures)} of {counted(len(compiled), 'closure')} do not compile"
                if len(compiled) > 1
                else "the closure does not compile"
            )
            if failed_closures
            else ("the closure compiles" if len(compiled) == 1 else f"all {counted(len(compiled), 'closure')} compile")
        )
    groups = diagnostic_groups(diags, result)
    if documents:
        groups.append(
            Group(
                "documents",
                [
                    Item(f"does not compile: {d['error']}" if not d["ok"] else "compiles", key=str(d["document"]))
                    for d in documents
                ],
                limit=None,
                problem=bool(failed_docs),
            )
        )
    if failed_closures:
        groups.append(
            Group(
                "error loom:closure-failed",
                [Item(f"does not compile: {c['error']}", key=str(c["key"])) for c in failed_closures],
                problem=True,
                next="loom check --closures all --json" if len(failed_closures) > 12 else None,
            )
        )
    Report(
        ("check failed: " if failed else "check passed: ") + "; ".join(said),
        ok=not failed,
        exit=EXIT_CONTENT if failed else 0,
        groups=groups,
        data={
            "diagnostics": [d.to_dict() for d in diags],
            "documents": documents,
            "closures": compiled,
        },
    ).emit(as_json)


def document_rel(result: ScanResult, target: str) -> str | None:
    """The quilt-relative path when TARGET names a scanned document rather than a key, else None."""
    if not target.endswith(".tex"):
        return None
    p = Path(target)
    rel = str(p.resolve().relative_to(result.quilt.root)) if p.is_absolute() else target
    return rel if rel in result.files else None


@click.command()
@click.argument("target", metavar="TARGET")
@click.option("--closure", is_flag=True, help="Everything TARGET depends on, in dependency order, then TARGET itself.")
@click.option(
    "--session", "run_dir", default=None, metavar="SESSION", envvar="LOOM_SESSION", help="Log this call to the session."
)
@quilt_option
def source(target: str, closure: bool, run_dir: str | None, quilt_path: str | None) -> None:
    """Print TARGET's LaTeX source: a key's own text, or a document flattened with every inclusion expanded in place.

    This is how a reader or an agent gets the text of a result or of a whole paper. It writes nothing: there is no file to clean up, none to keep out of version control, and none to go stale against the author's next edit.

    With --closure, a key is preceded by exactly the statements it depends on, in dependency order. A document is already whole, so --closure does not apply to one.
    """
    result = open_scan(quilt_path)
    doc = document_rel(result, target)
    if doc is not None:
        if closure:
            raise EnvError(f"--closure is for a key; {doc} is a document and already carries what it includes")
        log_run(run_dir, f"loom source {doc}", result.quilt.root)
        click.echo(flatten(result.quilt.root, doc).text.rstrip("\n"))
        return
    key = resolve_key(result, target)
    region = result.assembly.regions.get(key)
    if region is not None:
        # an equation's label names a point inside a node, not a node: print the node that holds it, and say so,
        # rather than index a region as if it were one -- which crashed with a KeyError on a digest's display equation
        note(
            f"{region.label} labels {'an equation' if region.where != 'prose' else 'a line'} inside {region.container}; printing that"
        )
        key = region.container
    require_text(result, key)
    from loom.scan.digests import other_version

    ck = result.assembly.digest_files.get(result.nodes[key].file) if key in result.nodes else None
    v = other_version(result.assembly, result.nodes[key].file) if ck else None
    if v is not None:
        note(
            f"{key} is read off {ck}'s digest, which {v.why}; its number and page are unverified, so check them with loom library read {ck}"
        )
    log_run(run_dir, f"loom source {key}" + (" --closure" if closure else ""), result.quilt.root)
    if not closure:
        click.echo(region_text(result, key).rstrip("\n"))
        return
    if not result.masters:
        raise ContentError("the quilt has no master; a closure document needs a preamble")
    b = build_bundle(result, key)
    click.echo(b.text.rstrip("\n"))
    if b.missing:
        note(f"closure entries without a statement: {', '.join(b.missing)}")
