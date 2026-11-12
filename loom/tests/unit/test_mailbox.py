"""A session's transcript (plan 0.13 §8): a post lands, carries what its writer marked since their last one, and is read, never consumed."""

from __future__ import annotations

from pathlib import Path

import pytest

from loom.mailbox import read_events
from tests.helpers import ok
from tests.unit._quilts import demo, new_session

WHO = "A. Author"


def test_a_post_lands_is_read_not_consumed_and_carries_what_changed(tmp_path: Path) -> None:
    """`loom session say` appends to the transcript; a post carries what its writer marked since the last one, so the record says what the message was about."""
    q = demo(tmp_path)
    sid = new_session(q, "referee pass", WHO)
    ok("annotate", "dm-0002", "Orbits may be empty.", "--as", WHO, cwd=q)
    said = ok("session", "say", "Have a look at dm-0003.", "--session", sid, "--as", WHO, cwd=q)
    assert said.stdout.startswith(f"said in {sid} with 1 annotation you marked")
    first = read_events(q, sid)
    assert [e.body for e in first] == ["Have a look at dm-0003."]
    assert [c["target"] for c in first[-1].changed] == ["dm-0002"]
    assert first[-1].changed[0]["by"] == WHO and first[-1].changed[0]["act"] == "created"
    assert read_events(q, sid) == first  # read twice, the same: nothing consumes a message

    ok("session", "say", "And the hypothesis.", "--session", sid, "--as", WHO, cwd=q)
    # the next post carries only what changed after the last one, rather than repeating itself
    assert read_events(q, sid)[-1].changed == []


@pytest.mark.poppler
def test_a_message_carries_a_mark_on_a_pdf_page_with_its_crop(tmp_path: Path) -> None:
    """What a person marked on a PDF goes with their next message as `loom since` reports it: its page, its file, its place and a crop of the page."""
    from tests.unit._pdfs import PROSE, lines_pdf

    q = demo(tmp_path)
    sid = new_session(q, "reading", WHO)
    lines_pdf(q / "notes" / "paper.pdf", [PROSE])
    ok("annotate", "notes/paper.pdf", "Look.", "--page", "1", "--quote", "the median polytope", "--as", WHO, cwd=q)
    ok("session", "say", "See the mark.", "--session", sid, "--as", WHO, cwd=q)
    (carried,) = read_events(q, sid)[-1].changed
    assert (carried["page"], carried["file"], carried["mark"], carried["quote"]) == (
        1,
        "notes/paper.pdf",
        None,
        "the median polytope",
    )
    assert carried["crop"].startswith(".loom/build/crops/") and carried["rects"]
