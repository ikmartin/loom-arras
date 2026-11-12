"""PDFs the PDF tests write by hand: lines of Helvetica at known places, so a test moves words a line down or onto the next page and knows where they went, with no TeX."""

from __future__ import annotations

from pathlib import Path

#: Where the first line's baseline stands, its left edge, and the distance between baselines, in points from the page's top left.
TOP, LEFT, STEP = 100.0, 72.0, 14.0
HEIGHT = 792.0


def lines_pdf(path: Path, pages: list[list[str]], *, tail: bytes = b"") -> Path:
    """A PDF of `pages`, each a list of lines set in 12 pt Helvetica from `TOP` down by `STEP`; `tail` appended after it changes the file's bytes and nothing it shows, as a re-save does."""

    def esc(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    n = len(pages)
    objs: list[bytes] = [b"<< /Type /Catalog /Pages 2 0 R >>", b""]
    kids = []
    for lines in pages:
        rows = " ".join(
            f"1 0 0 1 {LEFT:g} {HEIGHT - TOP - k * STEP:g} Tm ({esc(line)}) Tj" for k, line in enumerate(lines)
        )
        stream = f"BT /F1 12 Tf {rows} ET".encode()
        page_no = len(objs) + 1
        kids.append(f"{page_no} 0 R")
        objs.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 {HEIGHT:g}] /Contents {page_no + 1} 0 R "
            f"/Resources << /Font << /F1 {2 + 2 * n + 1} 0 R >> >> >>".encode()
        )
        objs.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    objs[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {n} >>".encode()
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    start = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode() + tail
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(out))
    return path


#: A page of prose to mark: each line distinct, so a run of words is found in one place.
PROSE = [
    "The median order of a weighted digraph minimises",
    "the total weight of the arcs that run backwards.",
    "Every vertex of the median polytope is integral",
    "because the incidence matrix is totally unimodular,",
    "and the counting function is a quasi-polynomial",
    "that becomes an honest polynomial when balanced.",
    "Nothing below is constructive in any sense.",
]


def line_box(page_lines: list[str], line: int, first_word: int, words: int) -> list[float]:
    """Roughly where words `first_word`..`first_word + words - 1` of line `line` stand: their line's band, from the left margin to a guess at their right; for a test that wants a box over them or beside them."""
    top = TOP + line * STEP - 10
    return [LEFT - 2, top, LEFT + 6 * len(" ".join(page_lines[line].split()[: first_word + words])), top + 13]
