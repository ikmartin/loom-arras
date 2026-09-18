"""Fetching a planned crawl under its cap (book 8.13.6).

Works are taken in the plan's order — shallowest first, then most cited — and downloaded until the cap is reached: an arXiv source where the work has an arXiv number, otherwise the open copy's PDF. Every work already downloaded counts against the cap before anything is fetched, so running fetch again never exceeds it, and a failure retried on a later run takes a place only if one is free. Each result is written into the work's record at once, so an interrupted fetch resumes by skipping what is on disk; a failure is recorded and reported, and does not stop the crawl unless arXiv refuses several downloads in a row, when every later request would be refused too. A downloaded source's `\\bibitem`s are read into its record, so a later plan knows its references.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from loom.digest.fetch import FetchRefused, _get, _unpack
from loom.refs.crawl.arxiv import eprint_url
from loom.refs.crawl.bibitem import from_source
from loom.refs.crawl.net import Service, ServiceError
from loom.refs.crawl.plan import Plan
from loom.refs.crawl.work import Reference
from loom.refs.crawl.work import load as load_work
from loom.refs.crawl.work import save as save_work

Download = Callable[[str], bytes]
# arXiv refuses every request for a while once it refuses one this way; going on would only record a failure for every work
STOP_AFTER = 3


def _via_digest_fetch(url: str, headers: dict[str, str]) -> bytes:
    """The digest fetcher's GET, which retries what arXiv answers under load, as a crawl transport."""
    try:
        return _get(url)
    except FetchRefused as exc:
        raise ServiceError(str(exc)) from exc


def downloaders(arxiv_spacing: float = 3.0, web_spacing: float = 1.0) -> tuple[Download, Download]:
    """Downloads from arXiv three seconds apart, and from anywhere else a second apart; neither is cached, since the bytes are kept in the work's directory."""
    arxiv = Service("arxiv-downloads", arxiv_spacing, None, _via_digest_fetch)
    web = Service("web-downloads", web_spacing, None, _via_digest_fetch)
    return arxiv.get, web.get


@dataclass
class FetchReport:
    fetched: int = 0
    already: int = 0
    failed: int = 0
    left_out: int = 0
    bytes: int = 0
    errors: list[str] = field(default_factory=list)
    stopped: str = ""  # why the fetch ended before the plan did: arXiv refusing, or an interruption


def fetch(
    root: Path,
    plan: Plan,
    cap: int,
    arxiv_get: Download,
    web_get: Download,
    log: Callable[[str], None] = lambda _: None,
) -> FetchReport:
    report = FetchReport()
    works = [load_work(root / plan.homes.get(key, "") / "work.json") for key in plan.order]
    pending = [w for w in works if w is not None and w.downloadable]
    report.already = sum(1 for w in pending if w.download.get("fetched"))
    used = report.already
    refused = 0
    try:
        for work in pending:
            if refused >= STOP_AFTER:
                report.stopped = f"arXiv refused {refused} downloads in a row; run fetch again later to resume"
                break
            if work.download.get("fetched"):
                continue
            if used >= cap:
                report.left_out += 1
                continue
            kind = work.downloadable
            url = eprint_url(work.arxiv or "") if kind == "source" else work.open_pdf
            dest = root / work.home
            try:
                if kind == "source":
                    data = arxiv_get(url)
                    _unpack(data, dest / "src")
                    items = from_source(dest / "src")
                    work.add_references(
                        [
                            Reference(
                                id=f"arxiv:{i.arxiv}" if i.arxiv else f"doi:{i.doi}" if i.doi else None, text=i.text
                            )
                            for i in items
                        ]
                    )
                else:
                    data = web_get(url)
                    if not data.startswith(b"%PDF"):
                        raise ServiceError(f"{url}: not a PDF")
                    dest.mkdir(parents=True, exist_ok=True)
                    (dest / "paper.pdf").write_bytes(data)
            except (ServiceError, OSError) as exc:
                work.download = {
                    "kind": kind,
                    "from": url,
                    "error": str(exc),
                    "tried": time.strftime("%Y-%m-%d", time.gmtime()),
                }
                save_work(root, work)
                report.failed += 1
                report.errors.append(f"{work.ids[0]}: {exc}")
                log(f"failed {work.ids[0]}: {exc}")
                refused = refused + 1 if kind == "source" else refused
                continue
            work.download = {
                "kind": kind,
                "from": url,
                "fetched": time.strftime("%Y-%m-%d", time.gmtime()),
                "bytes": len(data),
            }
            save_work(root, work)
            used += 1
            refused = 0 if kind == "source" else refused
            report.fetched += 1
            report.bytes += len(data)
            log(f"fetched {work.ids[0]} ({len(data) // 1024} KB)")
    except KeyboardInterrupt:
        report.stopped = "interrupted; what was fetched is kept, and fetch resumes from there"
    return report
