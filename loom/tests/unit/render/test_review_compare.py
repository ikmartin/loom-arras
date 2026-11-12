"""The review panel's comparison spans (`render/review_compare._changed`): which characters of the accepted and the current text differ, word by word."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from loom.render.review_compare import _changed


@pytest.mark.parametrize(
    ("before", "after", "left", "right"),
    [
        ("a b c", "a x c", [[2, 3]], [[2, 3]]),  # a word replaced
        ("a c", "a b c", [[2, 2]], [[2, 3]]),  # a word inserted: an empty span marks where on the left
        ("a b", "a", [[2, 3]], [[1, 1]]),  # a trailing word removed: the right's point is its end
        ("x", "", [[0, 1]], [[0, 0]]),
        ("same text", "same text", [], []),
        ("one two three", "one 2 three four", [[4, 7], [13, 13]], [[4, 5], [12, 16]]),
        ("a line\nrewrapped  here", "a line rewrapped\nhere", [], []),  # spacing alone is no change
    ],
)
def test_changed_spans_are_character_ranges_of_the_differing_words(
    before: str, after: str, left: list[list[int]], right: list[list[int]]
) -> None:
    assert _changed(before, after) == (left, right)


def test_a_whole_document_is_matched_over_its_words_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    """An agent's copy against its document: the matcher is given the words and never the spaces between them, since one indexing each of a document's thousands of single spaces took fourteen seconds on relloc's, on every build."""
    import difflib

    given: list[tuple[int, int]] = []

    class Seen(difflib.SequenceMatcher[str]):
        def __init__(
            self, isjunk: Callable[[str], bool] | None, a: list[str], b: list[str], autojunk: bool = True
        ) -> None:
            given.append((len(a), len(b)))
            assert not any(not w.strip() for w in [*a, *b])
            super().__init__(isjunk, a, b, autojunk)

    monkeypatch.setattr(difflib, "SequenceMatcher", Seen)
    words = ["the" if i % 7 == 0 else f"w{i % 3000}" for i in range(12000)]
    before = " ".join(words)
    after = " ".join(words[:6000] + ["changed"] + words[6000:])
    left, right = _changed(before, after)
    assert given == [(12000, 12001)]
    assert right == [[after.index(" changed ") + 1, after.index(" changed ") + 8]] and left
