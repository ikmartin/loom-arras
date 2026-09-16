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
    """Nothing under refs/ is the quilt's text: it holds fetched works, and a digest lives in digests/ (DR-108)."""
    for rel in [
        "drafts/main.tex",
        "nodes/a.tex",
        "digests/Kre99.tex",
        "build/x.tex",
        "refs/arxiv/1/src/d.tex",
        "notes.txt",
    ]:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
    assert discover_files(tmp_path) == ["digests/Kre99.tex", "drafts/main.tex", "nodes/a.tex"]


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


def test_scan_reads_an_unsaved_buffer_from_an_overlay(tmp_path: Path) -> None:
    """An editor holds text the disk does not; `scan(quilt, overlay)` sees the buffer, so diagnostics follow the keystrokes rather than the last save."""
    from loom.scan.quilt import load_quilt
    from loom.scan.scan import scan
    from tests.unit.scan.helpers import DEFAULT_CONFIG, PREAMBLE

    root = tmp_path / "q"
    (root / "drafts").mkdir(parents=True)
    (root / "nodes").mkdir()
    (root / "config.toml").write_text(DEFAULT_CONFIG, encoding="utf-8")
    (root / "drafts" / "main.tex").write_text(
        PREAMBLE + "\\begin{document}\n\\input{nodes/ab-0001}\n\\end{document}\n", encoding="utf-8"
    )
    (root / "nodes" / "ab-0001.tex").write_text(
        "\\begin{lemma}[Saved]\\label{ab-0001}\nOn disk.\n\\end{lemma}\n", encoding="utf-8"
    )
    quilt = load_quilt(root)

    assert scan(quilt).nodes["ab-0001"].title == "Saved"

    edited = scan(
        quilt, {"nodes/ab-0001.tex": "\\begin{lemma}[Edited]\\label{ab-0001}\nIn the buffer.\n\\end{lemma}\n"}
    )
    assert edited.nodes["ab-0001"].title == "Edited"
    assert "In the buffer." in edited.files["nodes/ab-0001.tex"].text
    assert "On disk." in (root / "nodes" / "ab-0001.tex").read_text()  # nothing was written

    # a file the buffer has created but never saved is scanned too
    created = scan(
        quilt,
        {
            "nodes/ab-0002.tex": "\\begin{lemma}[New]\\label{ab-0002}\nUnsaved.\n\\end{lemma}\n",
            "drafts/main.tex": PREAMBLE
            + "\\begin{document}\n\\input{nodes/ab-0001}\n\\input{nodes/ab-0002}\n\\end{document}\n",
        },
    )
    assert created.nodes["ab-0002"].title == "New"
    assert created.nodes["ab-0002"].reached_by == ["drafts/main.tex"]
