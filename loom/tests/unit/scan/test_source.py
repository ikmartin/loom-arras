from pathlib import Path

from loom.scan.source import blank_comments, discover_files, read_source


def test_blank_comments_preserves_offsets() -> None:
    text = "a % comment\nb \\% not\n\\verb|%x| c % d\n\\begin{verbatim}\n% keep\n\\end{verbatim}\n"
    clean = blank_comments(text)
    assert len(clean) == len(text)
    assert clean.startswith("a          \nb \\% not\n")
    assert "\\verb|%x| c    " in clean
    assert "% keep" in clean


def test_scan_all_tex_recursively_skips_build(tmp_path: Path) -> None:
    for rel in ["drafts/main.tex", "nodes/a.tex", "build/x.tex", "refs/d.tex", "notes.txt"]:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
    assert discover_files(tmp_path) == ["drafts/main.tex", "nodes/a.tex", "refs/d.tex"]


def test_non_utf8_source_decoded(tmp_path: Path) -> None:
    (tmp_path / "old.tex").write_bytes(b"pages 989\xd01004\n")
    src = read_source(tmp_path, "old.tex")
    assert src.encoding == "mac_roman"
    assert "989\u20131004" in src.text
    (tmp_path / "new.tex").write_bytes("pages 989\u20131004\n".encode())
    assert read_source(tmp_path, "new.tex").encoding == "utf-8"


def test_ignore_directive_and_lines(tmp_path: Path) -> None:
    (tmp_path / "f.tex").write_text("line1\n% !LOOM ignore\nline3\n", encoding="utf-8")
    src = read_source(tmp_path, "f.tex")
    assert src.ignored
    assert src.line_of(src.text.index("line3")) == 3
    assert src.col_of(src.text.index("line3")) == 1
