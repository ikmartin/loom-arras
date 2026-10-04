"""Output cases for `library update` and `library add`: the commands that fill the store; see `tests/output_cases/__init__.py`.

Nothing here touches the network: `update` runs offline, and `--online` is run only where it is refused.
"""

from __future__ import annotations

from pathlib import Path

from tests.output_cases.base import Case, ingest_pdf

AGENT = (("CLAUDECODE", "1"),)


def _fake_pdf(path: Path, text: str) -> None:
    """A PDF in the shape the fake toolchain's pdftotext reads."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(f"%PDF-1.4\n%FAKE-LOOM\n%%Pages: 1\n{text}\n".encode())


def tex_file(q: Path) -> None:
    """A LaTeX file to file as a work's source, and a text file that is neither PDF nor LaTeX."""
    (q / "man12.tex").write_text("\\documentclass{article}\n\\begin{document}\nX.\n\\end{document}\n", encoding="utf-8")
    (q / "notes.txt").write_text("notes\n", encoding="utf-8")


def pile(q: Path) -> None:
    """A folder of PDFs: one Man12 shows plainly, one only resembling Har77, one matching nothing."""
    _fake_pdf(q / "pile" / "a.pdf", "Virtual pull-backs\nCristina Manolache\nfirst copy")
    _fake_pdf(q / "pile" / "Hartshorne - 1977 - Algebraic Geometry.pdf", "Some other text entirely\nnobody at all")
    _fake_pdf(q / "pile" / "d.pdf", "Lecture notes on something unrelated\nA. Stranger")


def wrong(q: Path) -> None:
    """A PDF whose first page is another paper's."""
    _fake_pdf(q / "wrong.pdf", "Advanced Topics in the Arithmetic of Elliptic Curves\nJoseph Silverman")


def retired(q: Path) -> None:
    """A config still carrying the consent keys `[library] online` replaced."""
    cfg = q / "config.toml"
    cfg.write_text(cfg.read_text().replace("[library]\nonline = false", "[refs]\nfetch = true\nresolve = false"))


KIND: dict[str, str] = {
    "library update": "report",
    "library add": "report",
}

CASES: dict[str, list[Case]] = {
    "library update": [
        Case(),
        Case(("--dry-run",), unchanged=True),
        Case(("--only", "gather")),
        Case(("Calloway14", "--only", "map", "--redo")),
        Case(("Man12", "--only", "fetch"), why="offline: says how to go online"),
        Case(("Nobody99xyz",), exit=2, why="names no work", unchanged=True),
        Case(("--only", "polish"), exit=2, why="an unknown step", unchanged=True),
        Case(("--online",), env=AGENT, exit=2, why="an agent may not grant itself the network", unchanged=True),
        Case((), setup=retired, exit=2, why="the retired [refs] consent keys", unchanged=True),
    ],
    "library add": [
        Case(("man12.tex", "--for", "Man12", "--as", "Tester"), tex_file),
        Case(("pile",), pile, why="filed, and skipped with their reasons"),
        Case(("pile", "--dry-run"), pile, unchanged=True),
        Case(("refs",), ingest_pdf, poppler=True, why="the shipped PDF again: already in the store"),
        Case(("notes.txt", "--for", "Man12"), tex_file, exit=2, why="neither a PDF nor LaTeX", unchanged=True),
        Case(("man12.tex", "--for", "Nobody99xyz"), tex_file, exit=2, why="names no work", unchanged=True),
        Case(("wrong.pdf", "--for", "Man12"), wrong, exit=2, why="it does not show it is Man12", unchanged=True),
        Case(("man12.tex", "--force"), tex_file, exit=2, why="--force without --for", unchanged=True),
        Case(("man12.tex", "--for", "Man12"), tex_file, env=AGENT, exit=2, why="the author's", unchanged=True),
    ],
}
