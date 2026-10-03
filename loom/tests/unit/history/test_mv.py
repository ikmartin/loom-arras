"""`loom mv` (book 4.4, 17.12): moving a drafting document and recording the move, or recording a rename made elsewhere, so every record naming the document follows it."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from loom.scan.quilt import load_quilt
from loom.scan.scan import scan
from tests.helpers import json_of, ok, refused

AUTHOR = ["--author", "Markas Hecht"]


@pytest.fixture(autouse=True)
def local_reviewer() -> None:
    """Status reports the local reviewer's acceptance, so the reviewer is the author who accepts."""
    from loom.scan.quilt import save_author

    save_author("Markas Hecht")


def demo(tmp_path: Path) -> Path:
    """The demo quilt with its shipped ledger and annotation log removed, so the history starts blank."""
    ok("init", str(tmp_path / "demo"), "--demo", cwd=tmp_path)
    d = tmp_path / "demo"
    shutil.rmtree(d / ".loom", ignore_errors=True)
    shutil.rmtree(d / "annotations", ignore_errors=True)
    return d


def ledger(d: Path) -> list[dict]:
    p = d / ".loom" / "history" / "ledger.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.is_file() else []


def main_of(d: Path) -> str:
    return next(ln for ln in (d / "config.toml").read_text().splitlines() if ln.startswith("main")).split('"')[1]


def fresh(d: Path, key: str = "dm-0001") -> bool:
    return bool(json_of("status", "--json", cwd=d)["keys"][key]["acceptance"]["fresh"])


def gone(d: Path) -> list[dict]:
    return [x for x in json_of("lint", "--json", cwd=d)["diagnostics"] if x["code"] == "loom:document-gone"]


def test_mv_moves_a_document_and_records_the_move(tmp_path: Path) -> None:
    d = demo(tmp_path)
    r = ok("mv", "drafting/outline.tex", "drafting/plan.tex", cwd=d)
    assert r.stdout == "moved drafting/outline.tex to drafting/plan.tex; every record naming it follows\n"
    assert r.stderr == ""
    assert not (d / "drafting" / "outline.tex").exists() and (d / "drafting" / "plan.tex").is_file()
    line = ledger(d)[-1]
    assert {k: line[k] for k in ("action", "from", "to", "moved")} == {
        "action": "move",
        "from": "drafting/outline.tex",
        "to": "drafting/plan.tex",
        "moved": True,
    }
    assert "via" not in line
    assert main_of(d) == "drafting/main.tex"
    assert "drafting/outline.tex -> drafting/plan.tex\n" in ok("history", cwd=d).stdout


def test_moving_the_default_document_moves_main_and_its_acceptances_stay_fresh(tmp_path: Path) -> None:
    d = demo(tmp_path)
    ok("accept", "dm-0001", "--force", *AUTHOR, cwd=d)
    r = ok("mv", "drafting/main.tex", "drafting/paper.tex", cwd=d)
    assert "config.toml: main = drafting/paper.tex" in r.stdout
    assert main_of(d) == "drafting/paper.tex"
    assert fresh(d)
    lint = json_of("lint", "--json", cwd=d)["diagnostics"]
    assert not [x for x in lint if x["code"] in ("loom:document-gone", "loom:main-not-found")], lint


def test_mv_records_a_rename_made_by_hand_and_the_document_is_no_longer_gone(tmp_path: Path) -> None:
    """The hand rename of phase 1: `document-gone` until `loom mv` records where the document went, then fresh, the annotation drawn in the new document, and `[quilt] main` moved."""
    d = demo(tmp_path)
    ok("accept", "dm-0001", "--force", *AUTHOR, cwd=d)
    ok("annotate", "dm-0001", "Read here.", "--in", "drafting/main.tex", *AUTHOR, cwd=d)
    (d / "drafting" / "main.tex").rename(d / "drafting" / "paper.tex")
    assert [g["fixes"][0]["command"] for g in gone(d)] == ["loom mv drafting/main.tex NEW"]
    assert not fresh(d)
    r = ok("mv", "drafting/main.tex", "drafting/paper.tex", cwd=d)
    assert r.stdout == (
        "drafting/main.tex was renamed to drafting/paper.tex outside loom; every record naming it follows\n"
        "config.toml: main = drafting/paper.tex\n"
    )
    assert ledger(d)[-1]["moved"] is False
    assert gone(d) == []
    assert fresh(d)
    ok("build", cwd=d)
    m = json.loads((d / "build" / "manifest.json").read_text())
    assert [a["in"] for a in m["annotations"].values() if a["body_html"].startswith("<p>Read here.")] == [
        "drafting/paper.tex"
    ]
    assert "drafting/main.tex -> drafting/paper.tex (renamed outside loom)" in ok("history", cwd=d).stdout


def test_a_move_into_a_superseded_path_makes_it_live(tmp_path: Path) -> None:
    """Linearize main.tex, delete it, move the flat copy back to its name: the path is a live document again, not the superseded one."""
    d = demo(tmp_path)
    ok("accept", "dm-0001", "--force", *AUTHOR, cwd=d)
    ok("linearize", "drafting/main.tex", "--to", "drafting/flat.tex", "--keep-shared", "--no-check", cwd=d)
    (d / "drafting" / "main.tex").unlink()
    ok("mv", "drafting/flat.tex", "drafting/main.tex", cwd=d)
    assert main_of(d) == "drafting/main.tex"
    assert "drafting/main.tex" in scan(load_quilt(d)).masters
    assert fresh(d)


def test_mv_json_is_the_ledger_line(tmp_path: Path) -> None:
    d = demo(tmp_path)
    got = json_of("mv", "drafting/outline.tex", "drafting/plan.tex", "--json", cwd=d)
    assert {k: got[k] for k in [*ledger(d)[-1], "line"]} == {**ledger(d)[-1], "line": 1}
    assert got["verdict"].startswith("moved drafting/outline.tex to drafting/plan.tex")
    assert got["action"] == "move" and got["moved"] is True


def _part(d: Path) -> None:
    (d / "drafting" / "part.tex").write_text("Words a document includes.\n", encoding="utf-8")


def _flat(d: Path) -> None:
    ok("linearize", "drafting/main.tex", "--to", "drafting/flat.tex", "--keep-shared", "--no-check", cwd=d)


def _renamed(d: Path) -> None:
    (d / "drafting" / "main.tex").rename(d / "drafting" / "paper.tex")
    ok("mv", "drafting/main.tex", "drafting/paper.tex", cwd=d)


def _deleted_and_part(d: Path) -> None:
    ok("accept", "dm-0001", "--force", *AUTHOR, cwd=d)
    (d / "drafting" / "main.tex").unlink()
    _part(d)


def _nothing(d: Path) -> None:
    return None


#: name -> (setup, OLD, NEW, what the refusal says); every one exits 2 and changes neither the files nor the ledger.
REFUSALS: dict[str, tuple[Callable[[Path], None], str, str, str]] = {
    "both exist": (_nothing, "drafting/main.tex", "drafting/outline.tex", "both exist; loom mv never overwrites"),
    "neither exists": (_nothing, "drafting/a.tex", "drafting/b.tex", "neither drafting/a.tex nor drafting/b.tex exists"),
    "the same path": (_nothing, "drafting/main.tex", "drafting/main.tex", "are the same path"),
    "OLD outside drafting": (_nothing, "nodes/dm-0001.tex", "drafting/x.tex", "is not directly in the drafting directory"),
    "NEW below drafting": (_nothing, "drafting/main.tex", "drafting/sub/main.tex", "is not directly in the drafting"),
    "NEW not .tex": (_nothing, "drafting/main.tex", "drafting/main.txt", "is not a .tex file"),
    "NEW in retired": (_nothing, "drafting/main.tex", "retired/main.tex", "is inside retired/, not the drafting directory"),
    "NEW in the history": (_nothing, "drafting/main.tex", ".loom/history/x.tex", "is inside .loom/history/"),
    "OLD outside the quilt": (_nothing, "/nonexistent/a.tex", "drafting/x.tex", "is outside the quilt"),
    "OLD a node file": (_part, "drafting/part.tex", "drafting/part2.tex", "is not a live drafting document"),
    "OLD superseded": (_flat, "drafting/main.tex", "drafting/other.tex", "is superseded (linearize)"),
    "OLD unknown": (_nothing, "drafting/never.tex", "drafting/outline.tex", "is not a document any record or the history names"),
    "NEW not a document": (_deleted_and_part, "drafting/main.tex", "drafting/part.tex", "a rename is recorded only to a document"),
    "already recorded": (_renamed, "drafting/main.tex", "drafting/paper.tex", "already takes drafting/main.tex to drafting/paper.tex"),
}  # fmt: skip


@pytest.mark.parametrize("case", sorted(REFUSALS))
def test_mv_refuses_with_the_reason(case: str, tmp_path: Path) -> None:
    setup, old, new, match = REFUSALS[case]
    d = demo(tmp_path)
    setup(d)
    before = ledger(d), sorted(p.name for p in (d / "drafting").iterdir()), (d / "config.toml").read_text()
    refused("mv", old, new, code=2, match=match, cwd=d)
    assert (ledger(d), sorted(p.name for p in (d / "drafting").iterdir()), (d / "config.toml").read_text()) == before
