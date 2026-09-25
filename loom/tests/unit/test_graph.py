"""The dependency graph from the command line (book 12): `search`, `deps`, `unravel`, and the refusals of `pop` and `delete`."""

from __future__ import annotations

import shutil
from pathlib import Path

from tests.helpers import json_of, ok, refused
from tests.unit._quilts import demo

SYNTHETIC = Path(__file__).resolve().parents[1] / "quilts" / "synthetic"


def test_deps_prints_see_also(tmp_path: Path) -> None:
    """`deps` reports relations in a final section marked not-a-dependency, and `--json` carries them beside the closure (plan 0.2 §2.2)."""
    q = tmp_path / "syn"
    shutil.copytree(SYNTHETIC, q)
    r = ok("deps", "sy-0008", cwd=q)
    assert "see also (not a dependency):" in r.output
    assert "sy-0009" in r.output.split("see also (not a dependency):")[1]

    payload = json_of("deps", "sy-0009", "--json", cwd=q)
    assert payload["relations"] == [{"key": "sy-0008", "kind": "see"}]  # both directions are reported
    assert all(e["key"] != "sy-0008" for e in payload["closure"])  # and a relation is not in the closure


def test_search_deps_unravel_delete(tmp_path: Path) -> None:
    q = demo(tmp_path)
    entries = json_of("search", "orbits", "--json", cwd=q)
    assert entries[0]["key"] == "dm-0002" and "lem:orbits" in entries[0]["aliases"]
    assert ok("search", "lem:orbits", cwd=q).output.startswith("dm-0002 ")
    payload = json_of("deps", "dm-0003", "--json", cwd=q)
    assert [e["key"] for e in payload["proof"]] == [
        "dm-0002",
        "Calloway14-prop-3.2",
    ]  # \cite[Proposition 3.2]{Calloway14} resolves to the digest node
    assert payload["closure"] == [{"key": "dm-0003"}]
    dp = ok("deps", "dm-0003/proof", "--closure", cwd=q)
    assert set(dp.output.splitlines()[2:]) == {
        "  dm-0002 (Lemma)",
        "  dm-0003 (Theorem)",
        "  Calloway14-def-3.1 (Definition)",
        "  Calloway14-prop-3.2 (Proposition)",
    }  # the closure includes the digest nodes the proof cites by postnote (book 8.11)
    up = json_of("unravel", "dm-0001", "--json", cwd=q)
    assert {x["key"] for x in up["dependents"]} == {"dm-0002/proof", "dm-0005/proof"}
    assert any(i["file"] == "drafting/main.tex" for i in up["inclusions"])
    assert "nothing is changed" in ok("pop", "dm-0001", cwd=q).output
    refused("delete", "dm-0001", cwd=q, code=1, match="loom will not delete your notes")
    refused("rm", cwd=q, code=1, match="loom will not delete your notes")
    refused("deps", "dm-9999", cwd=q, code=2, match="no such key: dm-9999")


def test_unravel_reports_the_ledger_and_the_annotations_it_heads(tmp_path: Path) -> None:
    """`unravel` lists a node's ledger rows and the annotations on it; `annotations: (none)` on a reviewed node would say it was never reviewed (F13)."""
    q = demo(tmp_path)
    ok("annotate", "dm-0002", "Which orbits?", "--author", "Tom", cwd=q)

    payload = json_of("unravel", "dm-0002", "--json", cwd=q)
    assert [r["key"] for r in payload["ledger"]] == ["dm-0002", "dm-0002/proof"]  # the statement and its proof
    (a,) = payload["annotations"]
    assert a["message"] == "Which orbits?" and a["target"] == "dm-0002" and a["status"] == "open"

    text = ok("unravel", "dm-0002", cwd=q).output
    assert "Which orbits?" in text
    assert "annotations:\n  (none)" not in text
