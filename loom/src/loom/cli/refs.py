"""`loom refs path | add | resolve | crawl` (book 8.9, 8.9.1, 8.13): where a cited work's fetched artifacts are, how to put one there by hand, and which identifier an entry that states none most likely has."""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

import click

from loom.cli._common import EXIT_CONTENT, EnvError, note
from loom.cli._quilt import open_scan, quilt_option
from loom.refs.crawl.arxiv import SPACING as ARXIV_SPACING
from loom.refs.crawl.arxiv import Arxiv
from loom.refs.crawl.fetch import downloaders
from loom.refs.crawl.fetch import fetch as crawl_fetch_run
from loom.refs.crawl.net import Service
from loom.refs.crawl.openalex import SPACING as OPENALEX_SPACING
from loom.refs.crawl.openalex import OpenAlex
from loom.refs.crawl.plan import (
    Clients,
    Planner,
    PlanRefused,
    Settings,
    fingerprint,
    load_plan,
    save_plan,
    survey_summary,
)
from loom.refs.crawl.plan import summary as plan_summary
from loom.refs.crawl.work import load_all
from loom.refs.crawl.zbmath import SPACING as ZBMATH_SPACING
from loom.refs.crawl.zbmath import Zbmath
from loom.refs.identity import declared, primary
from loom.refs.resolve import Resolver, ResolveRefused, query_for, save
from loom.scan.quilt import QuiltConfig
from loom.scan.scan import ScanResult, find_bib_files


def _home(result: ScanResult, citekey: str) -> Path:
    """The work's directory under `refs/`, or a refusal naming what is missing."""
    entry = result.bib.get(citekey)
    if entry is None:
        raise EnvError(f"{citekey} is not in the bibliography, so it has no identity to file under")
    wid = primary(entry)
    assert wid is not None  # identify() always yields at least a synthetic id for a real entry
    return result.quilt.root / "refs" / wid.path


@click.group(name="refs")
def refs() -> None:
    """Fetched works: where their artifacts are, how to add one by hand, identifiers for works that state none, and a library crawled from the bibliography."""


@refs.command(name="path")
@click.argument("citekey")
@click.option("--pdf", "want", flag_value="pdf", help="The PDF rather than the directory.")
@click.option("--src", "want", flag_value="src", help="The unpacked source rather than the directory.")
@quilt_option
@click.pass_context
def path_command(ctx: click.Context, citekey: str, want: str | None, quilt_path: str | None) -> None:
    """Print where CITEKEY's fetched artifacts live. Nothing under refs/ is meant to be navigated by hand."""
    result = open_scan(quilt_path)
    home = _home(result, citekey)
    target = home if want is None else (home / "paper.pdf" if want == "pdf" else home / "src")
    click.echo(target)
    if not target.exists():
        # printed anyway: the path is where it *would* go, which is what `refs add` and `digest fetch` need
        note(f"nothing there yet; loom digest fetch {citekey}" + (" --pdf" if want == "pdf" else ""))
        ctx.exit(EXIT_CONTENT)


@refs.command(name="add")
@click.argument("citekey")
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--force", is_flag=True, help="Replace an artifact that is already there.")
@quilt_option
@click.pass_context
def add_command(ctx: click.Context, citekey: str, file: Path, force: bool, quilt_path: str | None) -> None:
    """File FILE as CITEKEY's PDF under refs/.

    A published PDF usually sits behind a subscription that loom cannot and should not automate past, so the author supplies the bytes and names the citekey they know; loom resolves the identifier and does the filing.
    """
    result = open_scan(quilt_path)
    if file.suffix.lower() != ".pdf":
        raise EnvError(f"{file.name} is not a PDF; only a work's PDF can be added by hand (its source is fetched)")
    home = _home(result, citekey)
    dest = home / "paper.pdf"
    if dest.exists() and not force:
        raise EnvError(f"{dest.relative_to(result.quilt.root)} exists; pass --force to replace it")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(file, dest)
    click.echo(f"Wrote {dest.relative_to(result.quilt.root)}")
    note("refs/ is not in version control: a collaborator cloning the quilt fetches or adds their own copy")


@refs.command(name="resolve")
@click.argument("citekeys", nargs=-1)
@click.option("--refresh", is_flag=True, help="Ask again even where an answer is recorded.")
@click.option("--json", "as_json", is_flag=True, help="Print the candidates as JSON.")
@quilt_option
@click.pass_context
def resolve_command(
    ctx: click.Context, citekeys: tuple[str, ...], refresh: bool, as_json: bool, quilt_path: str | None
) -> None:
    """Look up identifiers for cited works whose bibliography entry states none. Requires [refs] resolve = true.

    Asks zbMATH Open, then Crossref, and prints candidates with how well each matched. Nothing is changed: a candidate becomes the work's identity when you add the field to your own bibliography entry. Answers are kept under refs/, so `loom lint` can name them and a second run asks nothing. With no CITEKEYS, every cited entry that states no identifier.
    """
    result = open_scan(quilt_path)
    cfg = result.quilt.config
    if not cfg.resolve:
        raise EnvError(
            "looking up is off: set resolve = true under [refs] in config.toml to allow it (it sends bibliography titles and authors to zbMATH Open and Crossref)"
        )
    root = result.quilt.root
    if citekeys:
        missing = [ck for ck in citekeys if ck not in result.bib]
        if missing:
            raise EnvError(f"not in the bibliography: {', '.join(missing)}")
        wanted = list(citekeys)
    else:
        cited = {c.citekey for c in result.edges.cites}
        wanted = sorted(ck for ck in cited if ck in result.bib and not declared(result.bib[ck]))
    resolver = Resolver(cache=root / "refs" / "cache" / "resolve", contact=cfg.contact, refresh=refresh)
    report: dict[str, object] = {}
    failures = 0
    for ck in wanted:
        entry = result.bib[ck]
        if declared(entry) and not citekeys:
            continue
        try:
            found = resolver.candidates(query_for(entry))
        except ResolveRefused as exc:
            failures += 1
            report[ck] = {"error": str(exc)}
            if not as_json:
                click.echo(f"{ck}: {exc}")
            continue
        path = save(root, entry, found)
        report[ck] = {
            "candidates": [asdict(c) | {"strength": c.strength} for c in found],
            "record": str(path.relative_to(root)),
        }
        if as_json:
            continue
        if not found:
            click.echo(f"{ck}: no match")
            continue
        for i, c in enumerate(found[:3]):
            lead = f"{ck}:" if i == 0 else " " * (len(ck) + 1)
            names = ", ".join(a.split(",")[0] for a in c.authors[:3]) + (" et al." if len(c.authors) > 3 else "")
            also = f" (also {', '.join(c.also)})" if c.also else ""
            click.echo(
                f"{lead} {c.id}{also}  {c.strength} {c.confidence:.2f}  {c.source}  {c.title} — {names} {c.year}".rstrip()
            )
    if as_json:
        click.echo(json.dumps({"lookups": resolver.requests, "works": report}, indent=2))
    else:
        if not wanted:
            click.echo("every cited work states an identifier")
        note(
            "nothing was changed: add the field to your own bibliography entry to make a candidate the work's identity"
        )
    if failures:
        ctx.exit(EXIT_CONTENT)


@refs.group(name="crawl")
def crawl() -> None:
    """Build a library from the bibliography: plan by depth and subject from metadata, then fetch under a cap (book 8.13)."""


def crawl_clients(root: Path, cfg: QuiltConfig, refresh: bool) -> Clients:
    """The services a crawl plan asks, caching under refs/cache/crawl/; tests replace this."""
    cache = root / "refs" / "cache" / "crawl"
    return Clients(
        zbmath=Zbmath(Service("zbmath", ZBMATH_SPACING, cache, refresh=refresh)),
        openalex=OpenAlex(
            Service("openalex", OPENALEX_SPACING, cache, refresh=refresh), os.environ.get("LOOM_OPENALEX_KEY", "")
        ),
        arxiv=Arxiv(Service("arxiv", ARXIV_SPACING, cache, refresh=refresh)),
        resolver=Resolver(cache=root / "refs" / "cache" / "resolve", contact=cfg.contact, refresh=refresh),
    )


def crawl_downloaders() -> tuple[Callable[[str], bytes], Callable[[str], bytes]]:
    """Where a crawl's downloads come from; tests replace this."""
    return downloaders()


def _settings(cfg: QuiltConfig) -> Settings:
    return Settings(
        depth=cfg.crawl_depth, subjects=cfg.crawl_subjects, categories=cfg.crawl_categories, cap=cfg.crawl_cap
    )


def _bib_texts(root: Path) -> list[str]:
    return [(root / rel).read_text(encoding="utf-8", errors="replace") for rel in find_bib_files(root)]


@crawl.command(name="plan")
@click.option("--refresh", is_flag=True, help="Ask the services again instead of using recorded answers.")
@click.option("--json", "as_json", is_flag=True, help="Print the plan as JSON.")
@quilt_option
def crawl_plan(refresh: bool, as_json: bool, quilt_path: str | None) -> None:
    """Plan a crawl from metadata alone: identify the cited works, follow references to [crawl] depth, keep the works in [crawl] subjects and categories, and say what fetch would download. Downloads nothing. Requires [refs] resolve = true.

    Without [crawl] subjects, and deeper than depth 1, it surveys instead: it counts the works the cited works cite by MSC family and arXiv category, to choose subjects and categories from, and makes no plan.
    """
    result = open_scan(quilt_path)
    cfg = result.quilt.config
    root = result.quilt.root
    if not cfg.resolve:
        raise EnvError(
            "looking up is off: set resolve = true under [refs] in config.toml to allow a crawl plan (it asks zbMATH Open, OpenAlex, arXiv and Crossref)"
        )
    if not os.environ.get("LOOM_OPENALEX_KEY"):
        note("no LOOM_OPENALEX_KEY: OpenAlex requests draw on its small anonymous allowance")
    settings = _settings(cfg)
    cited = sorted({c.citekey for c in result.edges.cites if c.citekey in result.bib})
    clients = crawl_clients(root, cfg, refresh)
    planner = Planner(root, clients, log=note)
    surveying = settings.depth > 1 and not settings.subjects
    try:
        if surveying:
            survey = planner.survey(result.bib, cited)
        else:
            plan = planner.run(settings, result.bib, cited, _bib_texts(root))
    except PlanRefused as exc:
        raise EnvError(str(exc)) from exc
    for client in (clients.zbmath, clients.openalex, clients.arxiv):
        service = getattr(client, "service", None)
        if service is not None and service.failures:
            hint = "; set LOOM_OPENALEX_KEY" if service.name == "openalex" and "HTTP 40" in service.last_failure else ""
            note(
                f"{service.name}: {service.failures} requests failed, so the plan lacks what they would have added (the last: {service.last_failure}){hint}"
            )
    if surveying:
        if as_json:
            click.echo(json.dumps({"survey": asdict(survey)}, indent=2))
            return
        for line in survey_summary(survey):
            click.echo(line)
        note(
            "no plan was made: under [crawl], set subjects = [...] to the MSC families to keep, and categories = [...] to the arXiv categories that keep a work with no MSC code; then plan again"
        )
        return
    path = save_plan(root, plan)
    if as_json:
        click.echo(json.dumps(asdict(plan), indent=2))
        return
    for line in plan_summary(plan):
        click.echo(line)
    note(f"wrote {path.relative_to(root)}; nothing was downloaded")


@crawl.command(name="fetch")
@click.option("--json", "as_json", is_flag=True, help="Print the report as JSON.")
@quilt_option
@click.pass_context
def crawl_fetch(ctx: click.Context, as_json: bool, quilt_path: str | None) -> None:
    """Download what the plan selected, shallowest and most cited first, until [crawl] cap downloads are on disk. Resumable. Requires [refs] fetch = true and a plan made from the current settings and bibliography."""
    result = open_scan(quilt_path)
    cfg = result.quilt.config
    root = result.quilt.root
    if not cfg.fetch:
        raise EnvError("fetching is off: set fetch = true under [refs] in config.toml to allow a crawl to download")
    plan = load_plan(root)
    if plan is None:
        raise EnvError("no crawl plan: run loom refs crawl plan first")
    settings = _settings(cfg)
    if plan.fingerprint != fingerprint(settings, _bib_texts(root)):
        raise EnvError(
            "the plan was made from other [crawl] settings or another bibliography: run loom refs crawl plan again"
        )
    arxiv_get, web_get = crawl_downloaders()
    report = crawl_fetch_run(root, plan, settings.cap, arxiv_get, web_get, log=note)
    if as_json:
        click.echo(json.dumps(asdict(report), indent=2))
    else:
        click.echo(
            f"fetched {report.fetched} ({report.bytes / 1e6:.1f} MB) · {report.already} already on disk · {report.failed} failed · {report.left_out} left out by the cap of {settings.cap}"
        )
        for err in report.errors[:10]:
            click.echo(f"  {err}")
        if report.stopped:
            click.echo(f"stopped: {report.stopped}")
    if report.failed or report.stopped:
        ctx.exit(EXIT_CONTENT)


@crawl.command(name="status")
@click.option("--json", "as_json", is_flag=True, help="Print the status as JSON.")
@quilt_option
def crawl_status(as_json: bool, quilt_path: str | None) -> None:
    """What the plan's library holds: its works, how many are downloaded or failed, how many are still to fetch under the cap and beyond it, and whether the plan is current."""
    result = open_scan(quilt_path)
    root = result.quilt.root
    plan = load_plan(root)
    works = load_all(root)
    planned = [works[k] for k in plan.order if k in works] if plan else list(works.values())
    downloaded = sum(1 for w in planned if w.download.get("fetched"))
    failed = sum(1 for w in planned if w.download.get("error"))
    waiting = sum(1 for w in planned if w.downloadable and not w.download.get("fetched"))
    to_fetch = min(waiting, max(0, int(plan.settings["cap"]) - downloaded)) if plan else waiting
    current = plan is not None and plan.fingerprint == fingerprint(_settings(result.quilt.config), _bib_texts(root))
    status = {
        "plan": {"made": plan.made, "settings": plan.settings, "current": current} if plan else None,
        "works": len(planned),
        "downloaded": downloaded,
        "failed": failed,
        "to_fetch": to_fetch,
        "beyond_cap": waiting - to_fetch,
        "metadata_only": sum(1 for w in planned if not w.downloadable),
        "outside_plan": len(works) - len(planned),
    }
    if as_json:
        click.echo(json.dumps(status, indent=2))
        return
    if plan is None:
        click.echo("no crawl plan yet")
    else:
        stale = "" if current else " · out of date: settings or bibliography changed"
        click.echo(
            f"plan made {plan.made} · depth {plan.settings['depth']} · subjects {' '.join(plan.subjects)} · cap {plan.settings['cap']}{stale}"
        )
    click.echo(
        f"{status['works']} works · {downloaded} downloaded · {failed} failed · {to_fetch} to fetch under the cap, {status['beyond_cap']} beyond it · {status['metadata_only']} metadata only"
    )
    if status["outside_plan"]:
        click.echo(f"{status['outside_plan']} recorded works are not in the plan (from an earlier plan)")
