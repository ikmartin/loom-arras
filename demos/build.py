#!/usr/bin/env python3
"""Rebuild every example quilt under demos/ (book 13.4).

The two committed quilts come from loom's generator, so they are what `loom init --demo` writes and what the
conformance fixture is made from; the quilts built from real papers are rebuilt by running the commands an author
would run, in an environment that can read nothing but the fixture directory, TeX Live and poppler, so that a macro
defined elsewhere on this machine can never make one of them work.

    python demos/build.py [--skip-papers] [--papers NAME ...]
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parent
LOOM = WS / "loom"
VENV = LOOM / ".venv" / "bin"
FIXTURES = Path(os.environ.get("LOOM_FIXTURES", WS / "tests" / "fixtures"))

PAPERS = [
    # (quilt, fixture directory, master, prefix, whether atomize moves sections too)
    ("relloc", "relloc", "draft3.tex", "rl", True),
    ("man12", "0805.2065", "virtual6.tex", "man", True),
    ("acgs", "1709.09864", "decomposition-formula.tex", "acgs", False),
    ("mmp", "2012.12270", "slice4D.tex", "mmp", True),
    ("kpsv", "2605.29265", "mZK_paper.tex", "kpsv", True),
]


def isolated_env() -> dict[str, str]:
    """PATH holding loom, TeX Live and poppler and nothing else; an empty HOME and empty TeX trees."""
    empty = WS / "build" / "empty-home"
    for sub in ("", "config", "texmf", "texmf-local", "var", "texmfcfg"):
        (empty / sub).mkdir(parents=True, exist_ok=True)
    tex = Path(shutil.which("latexmk") or "/usr/bin/latexmk").parent
    poppler = Path(shutil.which("pdftotext") or "/usr/bin/pdftotext").parent
    return {
        "PATH": os.pathsep.join([str(VENV), str(tex), str(poppler), "/usr/bin", "/bin"]),
        "HOME": str(empty),
        "XDG_CONFIG_HOME": str(empty / "config"),
        "TEXMFHOME": str(empty / "texmf"),
        "TEXMFLOCAL": str(empty / "texmf-local"),
        "TEXMFVAR": str(empty / "var"),
        "TEXMFCONFIG": str(empty / "texmfcfg"),
    }


def run(*args: str, env: dict[str, str] | None = None, cwd: Path = WS) -> None:
    print("$ " + " ".join(args), flush=True)
    proc = subprocess.run(args, cwd=cwd, env=env, check=False)
    if proc.returncode not in (0, 1):  # 1 is a content problem, which several of these quilts carry on purpose
        raise SystemExit(f"failed ({proc.returncode}): {' '.join(args)}")


def build_committed() -> None:
    run(str(VENV / "python"), str(LOOM / "scripts" / "gen_quilts.py"), "all", cwd=LOOM)
    for name in ("demo", "synthetic", "showcase"):
        dest = HERE / name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(LOOM / "tests" / "quilts" / name, dest)
        if name in ("demo", "showcase"):
            # demos/demo is exactly what `loom init --demo` writes, and demos/showcase is a quilt to open rather
            # than a fixture; the expected-lint file belongs to the test copy under loom/tests/quilts/
            (dest / "EXPECTED-LINT.txt").unlink(missing_ok=True)
        print(f"wrote demos/{name}")
    _publish_showcase()
    run("sh", str(WS / "docs" / "specs" / "tools" / "refresh-fixture.sh"))


def _publish_showcase() -> None:
    """Compile and publish the showcase, so that a fresh clone opens the viewer on it with citation labels and page numbers.

    Nothing this writes is committed -- `build/` is gitignored by the quilt -- so it is skipped where TeX is absent, and `loom build` runs anyway: the manifest, the fragments and the page images of a pending proposal need no TeX distribution.
    """
    env = isolated_env()
    loom = str(VENV / "loom")
    if shutil.which("latexmk"):
        run(loom, "compile", "--quilt", "demos/showcase", env=env)
    else:
        print("latexmk is absent: the showcase is published without a compile, so citations show their keys", file=sys.stderr)
    run(loom, "build", "--quilt", "demos/showcase", env=env)


def build_papers(only: list[str] | None = None) -> None:
    if not FIXTURES.is_dir():
        print(f"{FIXTURES} is absent (the paper sources are uncommitted): skipping the paper quilts", file=sys.stderr)
        return
    env = isolated_env()
    loom = str(VENV / "loom")
    for name, fixture, master, prefix, sections in PAPERS:
        if only and name not in only:
            continue
        quilt = HERE / name
        if quilt.exists():
            shutil.rmtree(quilt)
        rel = f"demos/{name}"
        stem = Path(master).stem
        run(loom, "init", rel, "--from", str(FIXTURES / fixture / master), "--prefix", prefix, "--yes", env=env)
        run(loom, "draft", f"canon/{master}", "--to", "drafting/main.tex", "--fix-anchoring", "--yes",
            "--quilt", rel, env=env)
        atomize = [loom, "atomize", "drafting/main.tex", "drafting/main-atomic.tex"]
        if sections:
            atomize.append("--sections")
        run(*atomize, "--quilt", rel, env=env)
        run(loom, "canonize", "drafting/main-atomic.tex", "--to", f"canon/{stem}-v1.tex",
            "-m", "Atomized", "--quilt", rel, env=env)
        run(loom, "compile", "--quilt", rel, env=env)
        print(f"wrote demos/{name}")
    digest = FIXTURES / "0805.2065" / "virtual6.tex"
    if (not only or "relloc" in only) and (HERE / "relloc").is_dir() and digest.is_file():
        run(loom, "digest", "extract", "manolache_VirtualPullbacks2012", str(digest), "--quilt", "demos/relloc", env=env)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-papers", action="store_true", help="Only the two committed quilts and the fixture.")
    ap.add_argument("--papers", nargs="+", metavar="NAME", help="Only these paper quilts; the committed quilts are left alone.")
    args = ap.parse_args()
    if args.papers:
        unknown = sorted(set(args.papers) - {p[0] for p in PAPERS})
        if unknown:
            ap.error(f"no paper quilt named {', '.join(unknown)}")
        build_papers(args.papers)
    else:
        build_committed()
        if not args.skip_papers:
            build_papers()
    print("demos rebuilt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
