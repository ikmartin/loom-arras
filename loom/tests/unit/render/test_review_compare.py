"""The review panel's comparison spans (`render/review_compare._changed`): which characters of the accepted and the current text differ, word by word."""

from __future__ import annotations

import pytest

from loom.render.review_compare import _changed


@pytest.mark.parametrize(
    ("before", "after", "left", "right"),
    [
        ("a b c", "a x c", [[2, 3]], [[2, 3]]),  # a word replaced
        ("a c", "a b c", [[2, 2]], [[2, 4]]),  # a word inserted: an empty span marks where on the left
        ("a b", "a", [[1, 3]], [[1, 1]]),  # a trailing word removed: the right's point is its end
        ("x", "", [[0, 1]], [[0, 0]]),
        ("same text", "same text", [], []),
        ("one two three", "one 2 three four", [[4, 7], [13, 13]], [[4, 5], [11, 16]]),
    ],
)
def test_changed_spans_are_character_ranges_of_the_differing_words(
    before: str, after: str, left: list[list[int]], right: list[list[int]]
) -> None:
    assert _changed(before, after) == (left, right)
