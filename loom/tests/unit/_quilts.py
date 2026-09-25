"""Quilts the unit tests share: the demo, a fresh session in one, the demo with one work of hand-written page text, and a copy of the showcase."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from click.testing import Result

from tests.helpers import exits, ok, refused

REPO = Path(__file__).resolve().parents[2]
SHOWCASE = REPO / "tests" / "quilts" / "showcase"


def demo(tmp_path: Path) -> Path:
    """`loom init --demo` into `tmp_path/q`, shipped ledger, sessions and annotation log included."""
    ok("init", str(tmp_path / "q"), "--demo", cwd=tmp_path)
    return tmp_path / "q"


def new_session(q: Path, title: str = "a sitting", author: str = "A. Author") -> str:
    """A fresh session made by `loom session new`, returning its id; the demo's own sessions are left as they are."""
    return ok("session", "new", title, "--author", author, cwd=q).stdout.split()[0]


def open_session(root: Path) -> str:
    """An open session to write into, made if there is none; every write over the API names one."""
    from loom.sessions import create, sessions

    have = [s for s in sessions(root).values() if s.state == "open"]
    return have[0].id if have else create(root, "test sitting", "tester").id


def work_home(q: Path, ck: str = "Vir12") -> Path:
    """Where the store keeps one cited work; named rather than globbed, because the demo ships a work of its own."""
    from loom.refs.fetch import work_dir
    from loom.scan.quilt import load_quilt
    from loom.scan.scan import scan

    return work_dir(q, scan(load_quilt(q)).bib[ck])


def mapped(tmp_path: Path) -> tuple[Path, str]:
    """The demo with an uncited work `Vir12` whose page text (pp.1 and 12 of 12) is written by hand, with no PDF behind it.

    The section map's hash is a placeholder: nothing here reads a PDF, so nothing compares it.
    """
    q = demo(tmp_path)
    ck = "Vir12"  # not Calloway14: the demo already ships a digest under that key
    with (q / "digests" / "bibliography.bib").open("a") as fh:
        fh.write("\n@article{Vir12, title={Virtual pull-backs}, author={Manolache, C.}, year={2012}}\n")
    home = work_home(q, ck)
    pages = home / "pages"
    pages.mkdir(parents=True, exist_ok=True)
    (pages / "0001.txt").write_text(
        "1 Introduction\nLet $f$ be a DM-type morphism with a perfect obstruction theory.\n"
    )
    (pages / "0012.txt").write_text("Theorem 4.1. Every widget is a gadget when the theory is perfect.\n")
    sections = {
        "sha256": "0" * 64,
        "pages": 12,
        "chars": 120,
        "sections": [{"n": "1", "title": "Introduction", "page": 1}],
    }
    (home / "sections.json").write_text(json.dumps(sections))
    return q, ck


def propose(
    q: Path,
    citekey: str,
    local: str,
    page: int | str,
    source: str,
    statement: str,
    level: str = "1",
    *,
    code: int = 0,
    match: str | None = None,
    **kw: str,
) -> Result:
    """Run `refs propose` and assert its exit `code`; with `match`, assert a refusal naming it.

    `kw` become `--key value` options, so `code` and `match` are the only names a caller cannot pass through.
    """
    args = [
        "refs", "propose", citekey, "--local", local, "--page", str(page), "--level", level,
        "--source-text", source, "--statement", statement,
    ]  # fmt: skip
    for k, v in kw.items():
        args += [f"--{k.replace('_', '-')}", v]
    if match is not None:
        return refused(*args, code=code, match=match, cwd=q)
    return exits(code, *args, cwd=q)


def showcase(tmp_path: Path) -> Path:
    """A copy of the showcase, the one test quilt that carries real PDFs; a copy because reading a page caches its word boxes inside it."""
    q = tmp_path / "showcase"
    shutil.copytree(SHOWCASE, q)
    return q
