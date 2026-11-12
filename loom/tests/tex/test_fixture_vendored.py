"""TeX tier: loom's build of the synthetic quilt equals the vendored conformance fixture (docs/specs/fixture.md §3): the manifest by section, and every other file the fixture vendors by path, none missing and none extra, modulo timestamps, SVG bodies and the whitespace in what TeX made, which depend on the TeX Live version."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from tests.helpers import exits, ok, same_tree

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "fixture"
SVG = re.compile(r"<svg\b.*?</svg>", re.S)
#: A picture published under svg/, named by its bytes, which dvisvgm writes differently from one TeX Live, and one environment, to another.
PICTURE = re.compile(r'src="svg/[0-9a-f]+\.(svg|png|jpe?g)"')
REFRESH = "if the change is intended, regenerate with docs/specs/tools/refresh-fixture.sh"
#: The build directories refresh-fixture.sh copies into the fixture, besides manifest.json.
VENDORED = ("fragments", "svg", "source", "diffs", "transcripts", "files", "changes")


def _norm_fragment(text: str) -> str:
    return _unspaced(PICTURE.sub(r'src="svg/PICTURE.\1"', SVG.sub("<svg/>", text)))


def _unspaced(html: str) -> str:
    """`html` without its whitespace, which TeX4ht writes differently from one TeX Live to the next (`By Lemma~` is a no-break space and two spaces in 2024's, the space alone in 2026's) where the words and the markup agree."""
    return re.sub(r"\s+", "", html)


def _norm_html(value: object) -> object:
    """Every `*_html` string in `value`, at any depth, without its whitespace (`_unspaced`)."""
    if isinstance(value, dict):
        return {
            k: _unspaced(v) if k.endswith("_html") and isinstance(v, str) else _norm_html(v) for k, v in value.items()
        }
    if isinstance(value, list):
        return [_norm_html(v) for v in value]
    return value


def published(root: Path) -> dict[str, bytes]:
    """Every file the fixture vendors beside the manifest, by path under `root`: fragments with SVG bodies blanked and pictures unnamed, SVG files counted by kind (both depend on the TeX Live version), and source/, diffs/ and transcripts/ as written."""
    tree: dict[str, bytes] = {}
    for sub in VENDORED:
        kinds = sorted(f.suffix.lower() for f in (root / sub).rglob("*") if f.is_file()) if sub == "svg" else []
        for i, kind in enumerate(kinds):
            tree[f"svg/picture-{i}{kind}"] = b""
        for f in sorted((root / sub).rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(root).as_posix()
            if sub == "svg":
                continue
            elif sub == "fragments":
                tree[rel] = _norm_fragment(f.read_text(encoding="utf-8")).encode("utf-8")
            else:
                tree[rel] = f.read_bytes()
    return tree


def _norm_manifest(m: dict) -> dict:  # type: ignore[type-arg]
    m = json.loads(json.dumps(m))
    m.pop("generated", None)
    for master in m.get("masters", []):
        master.pop("compiled", None)
    # Canon hashes cover their rendered SVGs; dvisvgm produces different
    # bytes across TeX Live versions even when the surrounding HTML agrees.
    for canon in m.get("canon", []):
        canon.pop("hash", None)
    m["publisher"].pop("version", None)
    return _norm_html(m)  # type: ignore[return-value]


@pytest.mark.tex
def test_fixture_matches_vendored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if not (FIXTURE / "manifest.json").exists():
        pytest.skip("no vendored fixture")
    monkeypatch.setenv("LOOM_FIXED_TIME", "2026-09-16T00:00:00Z")
    from loom.scan.quilt import save_author

    save_author("The synthetic quilt")
    q = tmp_path / "synthetic"
    shutil.copytree(REPO / "tests" / "quilts" / "synthetic", q)
    # as refresh-fixture.sh compiles them: each with its HTML, which the build reads its documents from, the agent's copy too
    ok("compile", "drafting/main.tex", "--html", cwd=q)
    ok("compile", "drafting/talk.tex", "--html", cwd=q)
    ok("compile", ".loom/copies/aidoc.tex", "--html", cwd=q)
    exits(1, "build", cwd=q)  # the synthetic quilt carries intentional errors
    ours = _norm_manifest(json.loads((q / ".loom/build" / "manifest.json").read_text()))
    theirs = _norm_manifest(json.loads((FIXTURE / "manifest.json").read_text()))
    assert sorted(ours) == sorted(theirs), f"the manifest's top-level sections differ; {REFRESH}"
    differ = [k for k in theirs if ours[k] != theirs[k]]
    for key in theirs:
        assert ours[key] == theirs[key], (
            f"manifest section {key!r} differs from the fixture (all that differ: {differ}); {REFRESH}"
        )
    same_tree(
        published(q / ".loom/build"),
        published(FIXTURE),
        "the build of the synthetic quilt against tests/fixture",
        "docs/specs/tools/refresh-fixture.sh",
    )
