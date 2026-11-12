"""The code a snippet's cache key reads (`render/snippets._as_code`): its comments and docstrings left out, and the same under every Python."""

from __future__ import annotations

from loom.render.snippets import _as_code

CODE = '''"""A module."""
X = 1  # a comment


def f(a: int) -> str:
    """Says what f does.

    At length.
    """
    # a note
    return f"{a} # not a comment"


class C:
    """A class."""

    y = "keep"
'''


def test_a_comment_or_a_docstring_reworded_is_the_same_code() -> None:
    reworded = (
        CODE.replace("# a comment", "# another comment")
        .replace("Says what f does.", "Says something else.")
        .replace("# a note", "# a longer note\n    # over two lines")
        .replace('"""A class."""', '"""Another class."""')
    )
    assert _as_code(reworded) == _as_code(CODE)


def test_a_change_of_code_is_another_code() -> None:
    assert _as_code(CODE.replace("X = 1", "X = 2")) != _as_code(CODE)
    # a `#` inside a string is code, not a comment
    assert _as_code(CODE.replace("# not a comment", "# still code")) != _as_code(CODE)
    assert _as_code(CODE.replace('y = "keep"', 'y = "kept"')) != _as_code(CODE)


def test_the_code_is_text_and_no_python_s_ast() -> None:
    """A key made from an AST dump never met a cache made under another Python, which is how CI's write suite lost every seeded snippet."""
    assert _as_code(CODE) == "\n".join(
        [
            "X = 1",
            "def f(a: int) -> str:",
            '    return f"{a} # not a comment"',
            "class C:",
            '    y = "keep"',
        ]
    )
