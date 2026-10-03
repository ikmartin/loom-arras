"""What a case is, and the setups the case modules share."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

Setup = Callable[[Path], None]


def nothing(_: Path) -> None:
    return None


def solo_spine(q: Path) -> None:
    """A spine that shares no node with another document, which is what `linearize` accepts."""
    (q / "drafting" / "solo.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\n\\input{drafting/solo-part}\n\\end{document}\n", encoding="utf-8"
    )
    (q / "drafting" / "solo-part.tex").write_text("Words.\n", encoding="utf-8")


def ingest_pdf(q: Path) -> None:
    """An input PDF exists even in a checkout containing only tracked files."""
    from tests.unit._quilts import work_home

    inbox = q / "refs"
    inbox.mkdir(exist_ok=True)
    (inbox / "paper.pdf").write_bytes((work_home(q, "Calloway14") / "paper.pdf").read_bytes())


def ai_copy(q: Path) -> None:
    from loom.scan.quilt import save_author
    from tests.helpers import ok

    save_author("Tester")
    ok("draft", "drafting/main.tex", "--ai", "contribution.tex", cwd=q)


def author(_: Path) -> None:
    """A local author name, which the commands that record who acted need."""
    from loom.scan.quilt import save_author

    save_author("Tester")


@dataclass(frozen=True)
class Case:
    """One run of a command on a fresh demo quilt.

    `args` follow the command path; `setup` prepares the quilt first; `exit` is the code book 12.1 gives the outcome; `json` runs it again with `--json` when the command takes it; `poppler` needs the real pdftotext; `env` sets variables for the run (None unsets); `why` says what the case is for when it is a refusal or an edge; `unchanged` asserts the quilt's files are byte-identical afterwards, as a dry run's and a refusal's must be (K3, K4).
    """

    args: tuple[str, ...] = ()
    setup: Setup = nothing
    exit: int = 0
    json: bool = True
    poppler: bool = False
    env: tuple[tuple[str, str | None], ...] = ()
    why: str = ""
    unchanged: bool = False
