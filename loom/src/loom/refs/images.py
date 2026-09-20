"""The anchor page of a proposal as an image, for the surface where a person judges the rendering (plan 0.12 §5.3).

The text layer a quotation is checked against keeps words and drops notation: one "X" for a stack and its coarse space, no superscripts or subscripts, no script, bold or blackboard. In the third study run a hypothesis moved from the space to the stack and passed every text check loom has, and two Brion statements read sigma^0 as sigma-cap-tau and a T as a G. Only the page image settles a symbol. Rendered at build time from the local PDF, into `build/` -- nothing here is committed, so §4.2's decision that page text is committed and PDFs are not is untouched.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from loom.refs.pages import sha256_of
from loom.refs.proposals import Result, home_of

RESOLUTION = 110  # dpi: a 612pt page is ~935px wide, legible for sub- and superscripts, ~150-250 KB a page
DIR = "pages"  # under build/, beside fragments/ and svg/


def anchor_images(root: Path, build_dir: Path, r: Result) -> list[str]:
    """Render the page(s) a result's anchor names, returning their paths relative to `build_dir`.

    Parameters
    ----------
    root : Path
        The quilt root.
    build_dir : Path
        Where the images are written, under `pages/`.
    r : Result
        A result with a PDF anchor.

    Returns
    -------
    list[str]
        One path per anchored page; empty when the PDF is not on this machine, is not the artifact the anchor names, or pdftoppm is missing -- the surface then says it has no image rather than showing a different page.
    """
    if r.anchor.kind != "pdf" or not r.anchor.page:
        return []
    home = home_of(root, r)
    pdf = home / "paper.pdf" if home else None
    tool = shutil.which("pdftoppm")
    if pdf is None or not pdf.is_file() or tool is None:
        return []
    out: list[str] = []
    checked = False
    for n in r.anchor.pages:
        rel = f"{DIR}/{r.anchor.sha256[:12]}-{n:04d}.png"
        dest = build_dir / rel
        if not dest.is_file():
            if not checked:
                # a replaced PDF would show a different page under the anchor's name; an image named by the hash is only ever the page of that artifact
                if sha256_of(pdf) != r.anchor.sha256:
                    return []
                checked = True
            dest.parent.mkdir(parents=True, exist_ok=True)
            stem = dest.with_suffix("")
            proc = subprocess.run(
                [tool, "-png", "-r", str(RESOLUTION), "-f", str(n), "-l", str(n), "-singlefile", str(pdf), str(stem)],
                capture_output=True,
                timeout=120,
                check=False,
            )
            if proc.returncode != 0 or not dest.is_file():
                return []
        out.append(rel)
    return out


_PAGE_BOX = re.compile(r'<page\s+width="([\d.]+)"\s+height="([\d.]+)"')


def anchor_focus(root: Path, r: Result) -> float | None:
    """How far down its first page a result's quotation starts, as a fraction of the page height; None when it cannot be placed.

    The page image opens at the top of the page, and on Graber and Pandharipande's first page that is the journal's masthead: the formula being judged was below the fold of the box that shows it.
    """
    from loom.refs.pages import token_boxes
    from loom.refs.search import locate_span

    home = home_of(root, r)
    pdf = home / "paper.pdf" if home else None
    if pdf is None or not pdf.is_file() or r.anchor.kind != "pdf" or not r.anchor.page:
        return None
    try:
        xml = token_boxes(pdf, r.anchor.page)
    except Exception:  # noqa: BLE001 -- geometry is a convenience; a page without it still shows
        return None
    box = _PAGE_BOX.search(xml)
    # the quotation's opening words: a whole statement over a text layer's glyph soup rarely places, its start usually does
    words = r.source_text.split()
    span = next((s for n in (24, 8, 4) if (s := locate_span(xml, " ".join(words[:n]), r.anchor.page))), None)
    if box is None or span is None or float(box.group(2)) <= 0:
        return None
    return round(max(0.0, min(1.0, span.quad[1] / float(box.group(2)))), 3)
