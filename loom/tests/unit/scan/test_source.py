from pathlib import Path

import pytest

from loom.scan.source import blank_comments, discover_files, read_source


def test_blank_comments_preserves_offsets() -> None:
    text = "a % comment\nb \\% not\n\\verb|%x| c % d\n\\begin{verbatim}\n% keep\n\\end{verbatim}\n"
    clean = blank_comments(text)
    assert len(clean) == len(text)
    assert clean.startswith("a          \nb \\% not\n")
    assert "\\verb|%x| c    " in clean
    assert "% keep" in clean


@pytest.mark.parametrize(
    "excluded",
    [
        pytest.param(".loom/build/x.tex", id="build-output"),
        pytest.param(".loom/retired/old.tex", id="a-retired-source"),
        pytest.param(".loom/digests/storage/arxiv/1/src/paper.tex", id="the-store-of-fetched-works"),
        pytest.param("notes.txt", id="not-tex"),
    ],
)
def test_the_quilts_text_is_every_tex_file_outside_loom_s_directory_but_its_digests(
    tmp_path: Path, excluded: str
) -> None:
    """Nothing under `.loom/` is the quilt's text but the digests, read there on purpose: a fetched e-print in the store is a whole paper carrying its own labels (DR-108)."""
    for rel in ["drafting/main.tex", "drafting/nodes/a.tex", ".loom/digests/Kre99.tex", excluded]:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
    assert discover_files(tmp_path) == [".loom/digests/Kre99.tex", "drafting/main.tex", "drafting/nodes/a.tex"]


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
    (root / "drafting").mkdir(parents=True)
    (root / "drafting" / "nodes").mkdir()
    (root / "config.toml").write_text(DEFAULT_CONFIG, encoding="utf-8")
    (root / "drafting" / "main.tex").write_text(
        PREAMBLE + "\\begin{document}\n\\input{nodes/ab-0001}\n\\end{document}\n", encoding="utf-8"
    )
    (root / "drafting" / "nodes" / "ab-0001.tex").write_text(
        "\\begin{lemma}[Saved]\\label{ab-0001}\nOn disk.\n\\end{lemma}\n", encoding="utf-8"
    )
    quilt = load_quilt(root)

    assert scan(quilt).nodes["ab-0001"].title == "Saved"

    edited = scan(
        quilt, {"drafting/nodes/ab-0001.tex": "\\begin{lemma}[Edited]\\label{ab-0001}\nIn the buffer.\n\\end{lemma}\n"}
    )
    assert edited.nodes["ab-0001"].title == "Edited"
    assert "In the buffer." in edited.files["drafting/nodes/ab-0001.tex"].text
    assert "On disk." in (root / "drafting" / "nodes" / "ab-0001.tex").read_text()  # nothing was written

    # a file the buffer has created but never saved is scanned too
    created = scan(
        quilt,
        {
            "drafting/nodes/ab-0002.tex": "\\begin{lemma}[New]\\label{ab-0002}\nUnsaved.\n\\end{lemma}\n",
            "drafting/main.tex": PREAMBLE
            + "\\begin{document}\n\\input{nodes/ab-0001}\n\\input{nodes/ab-0002}\n\\end{document}\n",
        },
    )
    assert created.nodes["ab-0002"].title == "New"
    assert created.nodes["ab-0002"].reached_by == ["drafting/main.tex"]


def test_a_directory_of_the_person_s_own_is_read_whatever_its_name(tmp_path: Path) -> None:
    """`notes/` and `build/` are names a person may give any directory, so loom reads them as it reads every other; `% !LOOM ignore` keeps a file out."""
    from tests.unit.scan.helpers import PREAMBLE, make_quilt

    result = make_quilt(
        tmp_path,
        {
            "drafting/main.tex": PREAMBLE + "\\begin{document}\n\\input{notes/mine}\n\\end{document}\n",
            "drafting/notes/mine.tex": "\\begin{lemma}\\label{ab-0001}\nMine.\n\\end{lemma}\n",
            "build/colleague.tex": "% !LOOM ignore\n\\begin{lemma}\\label{ab-0002}\nTheirs.\n\\end{lemma}\n",
        },
    )
    assert "ab-0001" in result.nodes and "ab-0002" not in result.nodes
    assert "build/colleague.tex" in result.files and result.files["build/colleague.tex"].ignored
