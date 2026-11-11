#!/usr/bin/env python3
"""Write the pages TeX makes of a committed quilt's documents, for the viewer's served suites, which run with no TeX.

Each document of `tests/quilts/<name>/` is compiled with `loom compile --html` on a copy, in an environment that reads nothing outside the copy and TeX Live, and the copy is built with TeX; under `arras/tests/pages/<name>/`, which `arras/tests/served-setup.ts` lays into each served copy's build, are kept each document's page directory (`<document>/html/`), its aux and bibliography, which number it, and the snippets the build made (`cache/snippets/`: digests, landmarks, comparisons), which a build with `--no-compile` reads and makes no more of. A page names the sources it was made from, so one left behind by a change to the quilt is read as edited since; a snippet is keyed by the code that makes it, so one left behind by a change to that code is never read, and its text shows as source.

    python scripts/gen_pages.py [synthetic|showcase|all] [--check]
"""

from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
QUILTS = REPO / "tests" / "quilts"
PAGES = REPO.parent / "arras" / "tests" / "pages"
SERVED = ("synthetic", "showcase")
#: What a page directory keeps: the page, its stylesheet, its pictures, and what it was made from.
KEPT = (".html", ".css", ".svg", ".png", ".jpg", ".jpeg", ".json")


def _env(home: Path) -> dict[str, str]:
    """The tools TeX and poppler need and loom's own environment, with a home and TeX trees of nothing."""
    path = [str(Path(shutil.which(tool) or "/usr/bin/true").parent) for tool in ("latexmk", "pdftotext")]
    return {
        "PATH": ":".join([*path, str(Path(sys.executable).parent), "/usr/bin", "/bin"]),
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "TEXMFHOME": str(home),
        "TEXMFLOCAL": str(home),
        "TEXMFVAR": str(home / "var"),
        "TEXMFCONFIG": str(home / "config"),
        "LOOM_FIXED_TIME": "2026-09-16T00:00:00Z",
    }


def pages(name: str, out: Path) -> list[str]:
    """Compile every document of quilt `name` with its HTML into `out`, one directory per document; return the documents."""
    from loom.paths import document_build
    from loom.scan.quilt import load_quilt
    from loom.scan.scan import scan

    with tempfile.TemporaryDirectory(prefix="loom-pages-") as tmp:
        q = Path(tmp) / name
        shutil.copytree(QUILTS / name, q, ignore=shutil.ignore_patterns("build"))
        home = Path(tmp) / "home"
        (home / ".config" / "loom").mkdir(parents=True)
        # the author the served suites run as (arras/tests/served.ts), whose perspective decides which comparisons a build asks for
        author = "The synthetic quilt" if name == "synthetic" else "The loom showcase"
        (home / ".config" / "loom" / "config.toml").write_text(f'[author]\nname = "{author}"\n')
        masters = scan(load_quilt(q)).masters
        loom = str(Path(sys.executable).parent / "loom")
        for master in masters:
            subprocess.run(
                [loom, "compile", master, "--html", "--quilt", str(q)], env=_env(home), capture_output=True, check=False
            )
            made = q / document_build(master) / "html"
            if not (made / f"{Path(master).stem}.html").is_file():
                print(f"{name}: {master} made no page", file=sys.stderr)
                continue
            dest = out / Path(document_build(master)).relative_to(".loom/build") / "html"
            dest.mkdir(parents=True, exist_ok=True)
            for f in sorted(made.iterdir()):
                if f.is_file() and f.suffix.lower() in KEPT and f.name != "fragment.html":
                    shutil.copy2(f, dest / f.name)
            for suffix in (".aux", ".bbl"):
                kept = q / document_build(master) / f"{Path(master).stem}{suffix}"
                if kept.is_file():
                    shutil.copy2(kept, dest.parent / kept.name)
        # the build makes, as snippets, what no compile does; what TeX refused is left for the served build to refuse again
        subprocess.run([loom, "build", "--quilt", str(q)], env=_env(home), capture_output=True, check=False)
        made = q / ".loom/build/cache/snippets"
        for f in sorted(made.rglob("*")) if made.is_dir() else ():
            if f.is_file() and f.suffix.lower() != ".failed":
                dest = out / "cache" / "snippets" / f.relative_to(made)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
        return masters


def _same(a: Path, b: Path) -> bool:
    cmp = filecmp.dircmp(a, b)
    if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
        return False
    return all(_same(a / d, b / d) for d in cmp.common_dirs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("which", nargs="?", default="all", choices=[*SERVED, "all"])
    parser.add_argument(
        "--check", action="store_true", help="Say whether the committed pages are this script's output."
    )
    args = parser.parse_args()
    names = SERVED if args.which == "all" else (args.which,)
    stale = []
    for name in names:
        if args.check:
            with tempfile.TemporaryDirectory() as tmp:
                pages(name, Path(tmp) / name)
                if not (PAGES / name).is_dir() or not _same(Path(tmp) / name, PAGES / name):
                    stale.append(name)
            continue
        shutil.rmtree(PAGES / name, ignore_errors=True)
        made = pages(name, PAGES / name)
        print(f"{name}: {len(made)} documents compiled into {(PAGES / name).relative_to(REPO.parent)}")
    if stale:
        print(
            "pages differ from a fresh compile: " + ", ".join(stale) + "; run python scripts/gen_pages.py",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    os.chdir(REPO)
    sys.exit(main())
