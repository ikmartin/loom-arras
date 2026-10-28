"""`loom --version`, and what holds across commands: a long text given as `-` is read from stdin, an argument that names nothing exits 2, and every patch applies as printed; `loom doctor` has its own file, `test_doctor.py`."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from loom.version import __version__
from tests.helpers import edit, json_of, ok, refused
from tests.unit._quilts import demo

AS = ("--as", "Test Agent")
#: LaTeX a shell mangles: a prime, a backslash, a dollar.
LATEX = "Is $y'$ the $\\prime$ of $f(x)$, or \\emph{its} $\\partial$?"


def test_cli_version() -> None:
    result = ok("--version")
    assert result.output.strip() == f"loom {__version__}"


def bodies(q: Path) -> list[str]:
    log = q / "annotations" / "log.jsonl"
    return [json.loads(ln).get("body", "") for ln in log.read_text().splitlines() if ln.strip()]


def test_a_long_text_given_as_dash_is_read_from_stdin(tmp_path: Path) -> None:
    """A shell mangles LaTeX (relloc's agent wrote `y^\\prime` to get past the quoting), so every command that takes a long text reads `-` from stdin, as `session say` and `write` do; relloc's `a-2026-10-26-0002` is a reply whose text was the "-" itself."""
    q = demo(tmp_path)
    before = len(bodies(q))
    ok("annotate", "dm-0002", "-", "--kind", "question", *AS, cwd=q, stdin=LATEX)
    first = ok("annotate", "dm-0002", "Which orbits?", "--kind", "question", *AS, cwd=q).output.split()[0]
    ok("annotate", "--reply", first, "-", *AS, cwd=q, stdin=LATEX)
    assert bodies(q)[before:] == [LATEX, "Which orbits?", LATEX]
    proposal = json_of(
        "library", "propose", "Calloway14", "--local", "rem-9.1", "--level", "1", "--page", "1",
        "--source-text", "An involution of a topological space fixes a subspace", "--statement", "-",
        "--dry-run", "--json", *AS, cwd=q, stdin=LATEX,
    )  # fmt: skip
    assert LATEX in json.dumps(proposal, ensure_ascii=False).replace("\\\\", "\\")


def test_stdin_holds_one_text(tmp_path: Path) -> None:
    q = demo(tmp_path)
    before = bodies(q)
    refused(
        "annotate", "dm-0002", "-", "--kind", "suggestion", "--payload", "-", *AS,
        cwd=q, code=2, match="MESSAGE and --payload are both -", stdin=LATEX,
    )  # fmt: skip
    refused("annotate", "--batch", "--payload", "-", *AS, cwd=q, code=2, match="--batch reads its lines from stdin")
    assert bodies(q) == before


def test_an_argument_that_names_nothing_exits_2(tmp_path: Path) -> None:
    """K3: an argument that names nothing, or names it ambiguously, is refused by name with exit 2 -- exit 1 is a run that found a problem in the quilt, which none of these is."""
    q = demo(tmp_path)
    refused("library", "read", "Calloway14", "99", cwd=q, code=2, match="99 is past the end")
    refused(
        "library", "propose", "Calloway14", "--local", "rem-9.1", "--level", "1", "--page", "99",
        "--source-text", "x", "--statement", "S", *AS, cwd=q, code=2, match="runs past the end",
    )  # fmt: skip
    refused(
        "library", "propose", "Calloway14", "--local", "remark-nine", "--level", "1", "--page", "1",
        "--source-text", "x", "--statement", "S", *AS, cwd=q, code=2, match="remark-nine",
    )  # fmt: skip
    refused("annotate", "dm-0002", "x", "--quote", "not in its text", *AS, cwd=q, code=2, match="loom source dm-0002")
    refused("write", "state", "See [](quilt:dm-9999).", *AS, cwd=q, code=2, match="dm-9999")


def _applies(q: Path, printed: str) -> None:
    """`git apply` takes the patch as loom printed it, at its default strip level: `--- a/PATH`, `+++ b/PATH`."""
    assert "--- a/" in printed and "+++ b/" in printed, printed
    patch = printed[printed.index("--- a/") :]
    r = subprocess.run(["git", "apply", "--check", "-"], input=patch, cwd=q, text=True, capture_output=True)
    assert r.returncode == 0, r.stderr + patch


def test_every_patch_loom_prints_applies_with_git_apply_as_it_stands(tmp_path: Path) -> None:
    """K2: `adopt` and `suggestion` wrote `--- a/PATH` patches and `revert`, `fork` and `id` `--- PATH`, so one took `-p1` and the others `-p0`."""
    q = demo(tmp_path)
    edit(q / "nodes" / "dm-0001.tex", "\\sigma x = x", "\\sigma(x) = x")
    _applies(q, ok("revert", "dm-0001@1", cwd=q).stdout)
    _applies(q, ok("fork", "dm-0001", "--in", "drafting/main.tex", "--dry-run", cwd=q).stdout)
    (q / "drafting" / "extra.tex").write_text("\\begin{lemma}\nA.\n\\end{lemma}\n")
    _applies(q, ok("id", "drafting/extra.tex", cwd=q).stdout)
    _applies(q, ok("suggestion", "a-2026-09-16-0002", cwd=q).stdout)
