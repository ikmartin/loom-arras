import subprocess
from pathlib import Path

import pytest

from loom.scan.expand import expand_master
from loom.scan.sections import find_sections, heading_labels
from loom.scan.source import read_source


def _files(tmp_path: Path, files: dict[str, str]):
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return {rel: read_source(tmp_path, rel) for rel in files if rel.endswith(".tex")}


def test_inclusion_input_include_nest_and_span_map(tmp_path: Path) -> None:
    srcs = _files(
        tmp_path,
        {
            "drafts/main.tex": "\\begin{document}\n\\section{A}\n\\input{nodes/x}\n\\nest{nodes/sec}\n\\subsection{B}\nend\n\\end{document}\n",
            "nodes/x.tex": "\\begin{lemma}\\label{q-0001}\nX\n\\end{lemma}\n",
            "nodes/sec.tex": "\\section{Nested}\ninner\n\\input{nodes/y.tex}\n",
            "nodes/y.tex": "deep\n",
        },
    )
    exp = expand_master(srcs["drafts/main.tex"], tmp_path, srcs)
    assert exp.diagnostics == []
    assert set(exp.reached) == {"drafts/main.tex", "nodes/x.tex", "nodes/sec.tex", "nodes/y.tex"}
    assert [i.child for i in exp.inclusions] == ["nodes/x.tex", "nodes/sec.tex", "nodes/y.tex"]
    assert [i.shift for i in exp.inclusions] == [0, 1, 1]
    for rel, src in srcs.items():
        assert "".join(exp.text[s.exp_start : s.exp_end] for s in exp.segments if s.file == rel) == src.clean
    off = exp.text.index("deep")
    assert exp.locate(off) == ("nodes/y.tex", 0, 1)
    assert exp.exp_offset("nodes/y.tex", 0) == off
    units = find_sections(exp, srcs)
    assert [(u.name, u.level, u.title) for u in units] == [
        ("section", 1, "A"),
        ("section", 2, "Nested"),
        ("subsection", 2, "B"),
    ]
    assert units[1].parent is units[0] and units[2].parent is units[0]
    assert units[1].exp_end == units[2].exp_start
    assert units[1].file_end == len(srcs["nodes/sec.tex"].clean)


def test_inclusion_exact_extension_braceless_and_system(tmp_path: Path) -> None:
    srcs = _files(
        tmp_path,
        {
            "drafts/main.tex": "\\input xy\n\\input{fig.pspdftex}\n\\input{missing-file}\n\\begin{document}\n\\end{document}\n",
        },
    )
    (tmp_path / "fig.pspdftex").write_text("\\begin{picture}(1,1)\\end{picture}\n", encoding="utf-8")
    exp = expand_master(srcs["drafts/main.tex"], tmp_path, srcs)
    problems = {i.name: i.problem for i in exp.inclusions}
    assert problems == {"xy": "system", "fig.pspdftex": "opaque", "missing-file": "missing"}
    assert [d.code for d in exp.diagnostics] == ["missing-include"]
    assert "picture" not in exp.text


def test_inclusion_double_and_cycle(tmp_path: Path) -> None:
    srcs = _files(
        tmp_path,
        {
            "drafts/main.tex": "\\begin{document}\n\\input{a}\n\\input{a}\n\\input{b}\n\\end{document}\n",
            "a.tex": "A\n",
            "b.tex": "B\\input{c}\n",
            "c.tex": "C\\input{b}\n",
        },
    )
    exp = expand_master(srcs["drafts/main.tex"], tmp_path, srcs)
    codes = sorted(d.code for d in exp.diagnostics)
    assert codes == ["double-inclusion", "inclusion-cycle"]
    assert exp.text.count("A\n") == 1


def test_section_label_not_stolen_and_same_line(tmp_path: Path) -> None:
    clean = "\\subsection{Facts}\n\n\n\\begin{proposition}\\label{prop:x}\nP\n\\end{proposition}\n\\section{S}\\label{sec:s}\\label{alias}\n\\section{T}\n  \\label{sec:t}\ntext\n\\section{U}\n\\subsection{V}\\label{sec:v}\n"
    assert heading_labels(clean, clean.index("{Facts}") + 7) == []
    assert heading_labels(clean, clean.index("{S}") + 3) == ["sec:s", "alias"]
    assert heading_labels(clean, clean.index("{T}") + 3) == ["sec:t"]
    assert heading_labels(clean, clean.index("{U}") + 3) == []


def test_kpsewhich_is_probed_once_per_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The probe is a subprocess run once per unresolved inclusion, and a paper's unresolved names repeat; on the Manolache import it was 86 ms of a 166 ms scan."""
    from loom.scan import expand as expand_mod

    expand_mod._kpsewhich.cache_clear()
    calls: list[str] = []

    def fake(cmd, **kw):  # type: ignore[no-untyped-def]
        calls.append(cmd[1])
        return subprocess.CompletedProcess(cmd, 0, stdout="/usr/share/x.sty\n", stderr="")

    monkeypatch.setattr(expand_mod.shutil, "which", lambda _n: "/usr/bin/kpsewhich")
    monkeypatch.setattr(expand_mod.subprocess, "run", fake)
    for _ in range(5):
        assert expand_mod._kpsewhich("amsmath.sty") is True
    assert calls == ["amsmath.sty"]
    expand_mod._kpsewhich.cache_clear()
