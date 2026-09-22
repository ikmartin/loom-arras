#!/usr/bin/env python3
"""How often a quotation taken from a page places on that page's word boxes (plan 0.13 step 1).

The slice's central risk: `pages/NNNN.txt` comes from plain `pdftotext -q` and `locate_span` works on `-bbox-layout`, which is a different extraction of the same page. Item 2's anchor rule — text offsets of record, quads for drawing — assumes the two agree. This measures how far they do, on real documents, before and after any fix to `search.py`.

    uv run python scripts/measure_mapping.py [--per-doc 40] [--show 3]

Every document is read where it lies; nothing is copied, written or changed.
"""

from __future__ import annotations

import argparse
import random
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from loom.refs.pages import page_texts, token_boxes  # noqa: E402
from loom.refs.search import locate_span  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
HOME = Path.home()

#: (label, pdf, committed page text directory or None). A document with no store is read straight from the PDF.
CORPUS: list[tuple[str, Path, Path | None]] = [
    (
        "showcase Bellamy (invented, TeX)",
        REPO / "demos/showcase/digests/storage/doi/10.4171_showcase_19-2/paper.pdf",
        REPO / "demos/showcase/digests/storage/doi/10.4171_showcase_19-2/pages",
    ),
    (
        "showcase Arden (invented, TeX)",
        REPO / "demos/showcase/digests/storage/arxiv/2504.01234v1/paper.pdf",
        REPO / "demos/showcase/digests/storage/arxiv/2504.01234v1/pages",
    ),
    (
        "Grunrock-Herr 2014 (arXiv, TeX)",
        REPO / "demos/kpsv/digests/storage/work/d63cc279/paper.pdf",
        REPO / "demos/kpsv/digests/storage/work/d63cc279/pages",
    ),
    ("Atiyah-Bott (scan, OCR)", HOME / "Downloads/atiyahbott_moment.pdf", None),
    ("Ekedahl-van der Geer (scan, OCR)", HOME / "Downloads/BF02441086.pdf", None),
]

_SENTENCE = re.compile(r"(?<=[.;:])\s+(?=[A-Z(])")


@dataclass
class Trial:
    page: int
    text: str
    placed: bool
    words: int = 0


def sentences(text: str) -> list[str]:
    """Quotation-sized pieces of a page: eight to forty words, as a reader would select."""
    out = []
    for piece in _SENTENCE.split(text.replace("\n", " ")):
        piece = re.sub(r"\s+", " ", piece).strip()
        if 8 <= len(piece.split()) <= 40 and sum(c.isalpha() for c in piece) > len(piece) * 0.6:
            out.append(piece)
    return out


def page_source(pdf: Path, pages_dir: Path | None) -> dict[int, str]:
    """Each page's text as of record: the committed `pages/NNNN.txt` where there is a store, else the PDF itself."""
    if pages_dir and pages_dir.is_dir():
        return {
            int(p.stem): p.read_text(encoding="utf-8", errors="replace") for p in sorted(pages_dir.glob("[0-9]*.txt"))
        }
    return {i: t for i, t in enumerate(page_texts(pdf), start=1)}


def measure(label: str, pdf: Path, pages_dir: Path | None, per_doc: int, rng: random.Random) -> list[Trial]:
    by_page = page_source(pdf, pages_dir)
    pool = [(n, s) for n, text in by_page.items() for s in sentences(text)]
    rng.shuffle(pool)
    trials: list[Trial] = []
    boxes: dict[int, str] = {}
    for page, text in pool:
        if len(trials) >= per_doc:
            break
        if page not in boxes:
            try:
                boxes[page] = token_boxes(pdf, page)
            except Exception as exc:  # noqa: BLE001 -- a page poppler cannot read is a finding, not a crash
                print(f"  ! page {page}: {exc}", file=sys.stderr)
                boxes[page] = ""
        span = locate_span(boxes[page], text, page) if boxes[page] else None
        trials.append(Trial(page, text, span is not None, span.words if span else 0))
    return trials


def diagnose(text: str) -> str:
    """A guess at why a quotation did not place, from what the page text contains."""
    if "-" in text and re.search(r"[a-z]-\s", text):
        return "hyphen"
    if re.search(r"[A-Za-z]\s?[0-9]", text) or re.search(r"[⊆∈≤≥∑∫√]", text):
        return "math/superscript"
    if len(text.split()) > 30:
        return "long"
    return "?"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--per-doc", type=int, default=40, help="quotations sampled per document")
    ap.add_argument("--show", type=int, default=3, help="failing quotations to print per document")
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    print(f"{'document':36} {'n':>4} {'placed':>7} {'rate':>7}   misses by cause")
    print("-" * 96)
    total = placed_total = 0
    for label, pdf, pages_dir in CORPUS:
        if not pdf.is_file():
            print(f"{label:36} {'—':>4} {'absent':>7}")
            continue
        trials = measure(label, pdf, pages_dir, args.per_doc, rng)
        placed = sum(t.placed for t in trials)
        total += len(trials)
        placed_total += placed
        causes: dict[str, int] = {}
        for t in trials:
            if not t.placed:
                causes[diagnose(t.text)] = causes.get(diagnose(t.text), 0) + 1
        rate = f"{placed / len(trials):.0%}" if trials else "—"
        tail = ", ".join(f"{k} {v}" for k, v in sorted(causes.items(), key=lambda kv: -kv[1])) or "none"
        print(f"{label:36} {len(trials):>4} {placed:>7} {rate:>7}   {tail}")
        for t in [t for t in trials if not t.placed][: args.show]:
            print(f"      p{t.page} [{diagnose(t.text)}] {t.text[:96]}")
    print("-" * 96)
    print(f"{'all':36} {total:>4} {placed_total:>7} {placed_total / total:>7.0%}" if total else "nothing measured")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
