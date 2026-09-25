"""A notes file as a report (plan 0.11 Part A): its blocks, its findings as anchors, its source offsets, and the order of passes. The Markdown pass inside it is `records/test_render_markdown.py`'s."""

from __future__ import annotations

from pathlib import Path

from loom.render.reports import parse_report
from tests.helpers import ok
from tests.unit._quilts import demo

SAMPLE = """## [summary]
Two claims are mixed; one step is unsaid.

## [referee-review] Major and minor

### Major Issues
- The finiteness hypothesis is never used, though $|X|$ is finite anyway. (a-2026-09-17-0001)
- Continuity of $\\sigma$ is asserted. (a-2026-09-17-0002)

## [decision]
Minor Revision.
"""


def test_report_parses_into_its_blocks() -> None:
    r = parse_report(SAMPLE, run="r-1", src="ai/runs/r-1/referee-dm-0003.notes.md")
    assert [b.name for b in r.blocks] == ["summary", "referee-review", "decision"]
    assert [b.title for b in r.blocks] == ["summary", "Major and minor", "decision"]
    assert r.findings == ["a-2026-09-17-0001", "a-2026-09-17-0002"]
    assert r.blocks[0].findings == [] and len(r.blocks[1].findings) == 2


def test_every_finding_is_an_anchor() -> None:
    """The report pane scrolls to a finding and the draft scrolls to its quote; both need the finding to be addressable."""
    r = parse_report(SAMPLE, src="x.md")
    assert '<li id="finding-a-2026-09-17-0001" data-annotation-id="a-2026-09-17-0001" data-src=' in r.html
    assert r.html.count("data-annotation-id=") == 2


def test_the_readers_view_is_free_of_the_agents_syntax() -> None:
    """The brackets classify a block and the trailing id names an annotation; both are carried as attributes, so neither belongs in the prose a person reads."""
    r = parse_report(SAMPLE, src="x.md")
    assert "[summary]" not in r.html and "[referee-review]" not in r.html
    assert '<h2 data-src="x.md:0:12">summary</h2>' in r.html
    assert ">Major and minor</h2>" in r.html  # what the agent wrote after the brackets wins
    assert "(a-2026-09-17-0001)" not in r.html  # but the anchor for it is still there
    assert 'data-annotation-id="a-2026-09-17-0001"' in r.html


def test_every_offset_lies_inside_the_file() -> None:
    """A `data-src` past the end of its file is a source map that cannot be followed."""
    import re as _re

    r = parse_report(SAMPLE, src="x.md")
    spans = [(int(a), int(b)) for a, b in _re.findall(r'data-src="x\.md:(\d+):(\d+)"', r.html)]
    assert spans
    assert all(0 <= a <= b <= len(SAMPLE) for a, b in spans)


def test_blocks_carry_offsets_into_the_notes_file() -> None:
    src = "ai/runs/r-1/referee-dm-0003.notes.md"
    r = parse_report(SAMPLE, src=src)
    start = SAMPLE.index("## [decision]")
    assert f'<section data-block="decision" data-src="{src}:{start}:{len(SAMPLE)}">' in r.html
    assert f'data-src="{src}:0:{len(SAMPLE)}"' in r.html  # the root spans the whole file


def test_an_unparseable_report_is_one_block_not_an_error() -> None:
    r = parse_report("Just prose, no headings at all.\n", src="x.md")
    assert len(r.blocks) == 1
    assert r.blocks[0].name == "" and "Just prose" in r.html


def test_a_second_pass_sorts_after_its_first(tmp_path: Path) -> None:
    """`referee-x.2.notes.md` sorts before `referee-x.notes.md` by plain name order, which would show pass 2 first; a session's pipeline lists the first pass, then the second, whatever order the directory gives."""
    from loom.render.threads import build_threads
    from loom.sessions import files_dir, sessions

    q = demo(tmp_path)
    sid = ok("session", "new", "two passes", "--author", "A. Author", cwd=q).stdout.split()[0]
    notes = files_dir(q, sessions(q)[sid])
    notes.mkdir(parents=True, exist_ok=True)
    (notes / "referee-dm-0003.2.notes.md").write_text("## [summary]\nSecond.\n")
    (notes / "referee-dm-0003.notes.md").write_text("## [summary]\nFirst.\n")
    pipeline = build_threads(q)[sid]["pipeline"]
    assert [(e["report"].rsplit("/", 1)[-1], e.get("pass")) for e in pipeline] == [
        ("referee-dm-0003.notes.md", None),
        ("referee-dm-0003.2.notes.md", 2),
    ]
