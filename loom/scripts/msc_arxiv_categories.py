#!/usr/bin/env python3
"""Which arXiv categories papers in some MSC families are filed under, from arXiv's own records.

A crawl keeps a work with no MSC code when its arXiv category is one the author lists under `[crawl] categories` (book 8.13.1); loom holds no correspondence between the two schemes. This helps choose that list: arXiv's records carry the MSC codes their authors gave beside the categories they filed under, and for the families named it counts the primary categories of papers carrying a code in one of them. With no families it prints the most common categories for each two-digit area. It is a measurement: it writes nothing but a cache of the pages it fetched.

Usage: uv run python scripts/msc_arxiv_categories.py [FAMILY ...] [--from 2025-06-01] [--until 2025-06-30] [--pages 3] [--cache DIR]
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from loom.refs.crawl import msc as M  # noqa: E402
from loom.refs.crawl.net import USER_AGENT  # noqa: E402

OAI = "https://oaipmh.arxiv.org/oai"
NS = {"oai": "http://www.openarchives.org/OAI/2.0/", "a": "http://arxiv.org/OAI/arXiv/"}
SPACING = 10.0  # arXiv asks for a request every three seconds; its OAI interface refuses faster harvesting with 406
# authors write "14N35, 14D23 (Primary) 55N91 (Secondary)", "Primary 14N35; Secondary 14D23", "14Nxx", ...
CODE = re.compile(r"\b(\d{2}[A-Z-](?:\d{2}|xx|XX))\b")


def page(params: dict[str, str], cache: Path) -> bytes:
    url = OAI + "?" + urllib.parse.urlencode(params)
    hit = cache / hashlib.sha256(url.encode()).hexdigest()[:32]
    if hit.is_file():
        return hit.read_bytes()
    for attempt in range(5):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"}), timeout=120
            ) as r:
                data: bytes = r.read()
            break
        except urllib.error.HTTPError as exc:
            # arXiv's OAI interface answers 406 when harvested too fast, and 503 when busy
            if exc.code not in (406, 503) or attempt == 4:
                raise
            print(f"HTTP {exc.code}, waiting", file=sys.stderr)
            time.sleep(int(exc.headers.get("Retry-After") or 60 * (attempt + 1)))
    time.sleep(SPACING)
    cache.mkdir(parents=True, exist_ok=True)
    hit.write_bytes(data)
    return data


def records(start: str, until: str, pages: int, cache: Path) -> list[tuple[list[str], str]]:
    """(MSC codes, primary category) for each record carrying MSC codes; arXiv lists the primary category first."""
    out: list[tuple[list[str], str]] = []
    params = {"verb": "ListRecords", "metadataPrefix": "arXiv", "set": "math", "from": start, "until": until}
    for n in range(pages):
        root = ET.fromstring(page(params, cache))
        for rec in root.iter(f"{{{NS['oai']}}}record"):
            meta = rec.find("oai:metadata/a:arXiv", NS)
            if meta is None:
                continue
            codes = CODE.findall(meta.findtext("a:msc-class", default="", namespaces=NS) or "")
            cats = (meta.findtext("a:categories", default="", namespaces=NS) or "").split()
            if codes and cats:
                out.append((codes, cats[0]))
        token = root.findtext(".//oai:resumptionToken", default="", namespaces=NS)
        print(f"page {n + 1}: {len(out)} records with MSC codes so far", file=sys.stderr)
        if not token:
            break
        params = {"verb": "ListRecords", "resumptionToken": urllib.parse.unquote(token)}  # arXiv sends it encoded
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("families", nargs="*", help="MSC families such as 14N; none for every area")
    ap.add_argument("--from", dest="start", default="2025-06-01")
    ap.add_argument("--until", default="2025-06-30")
    ap.add_argument("--pages", type=int, default=3)
    ap.add_argument("--cache", type=Path, default=Path(".msc-arxiv-cache"))
    args = ap.parse_args()
    sample = records(args.start, args.until, args.pages, args.cache)
    if not sample:
        print("no records with MSC codes in the sample", file=sys.stderr)
        return 2
    print(f"{len(sample)} arXiv records with MSC codes, {args.start} to {args.until}\n")
    if args.families:
        chosen = {M.family(f) for f in args.families}
        cats: Counter[str] = Counter(primary for codes, primary in sample if chosen & set(M.families(codes)))
        n = sum(cats.values())
        print(f"{n} papers with a code in {' '.join(sorted(chosen))}, by primary arXiv category:")
        running = 0
        for cat, c in cats.most_common():
            running += c
            print(f"  {cat:<20} {c:>5}  {100 * running / n:>4.0f}% so far")
        return 0
    by_area: dict[str, Counter[str]] = defaultdict(Counter)
    for codes, primary in sample:
        by_area[codes[0][:2]][primary] += 1  # the first code is the author's primary one by convention
    for area, cats in sorted(by_area.items()):
        n = sum(cats.values())
        top = ", ".join(f"{cat} {c}" for cat, c in cats.most_common(4))
        print(f"{area}  {n:>5}  {top}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
