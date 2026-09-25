"""`fetch_work` offline (book 8.9): the arrival check, the consent and candidate gates, the PDF-link route, `_get`'s retries and `_unpack`'s containment. The transport is faked; nothing here touches the network."""

from __future__ import annotations

import gzip
import io
import json
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from loom.refs import fetch as F
from loom.refs.pages import sha256_of
from loom.refs.resolve import Candidate, save
from loom.scan.bib import BibEntry
from loom.scan.quilt import Quilt, load_quilt
from loom.scan.scan import scan
from tests.helpers import edit
from tests.unit._quilts import demo

EPRINT = "https://export.arxiv.org/e-print/0805.2065v2"
PDF = "https://export.arxiv.org/pdf/0805.2065v2"


def tarball(members: dict[str, bytes], *, links: dict[str, str] | None = None) -> bytes:
    """A gzipped tar holding `members` by name, plus symlinks `links` (name -> target)."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        for name, target in (links or {}).items():
            info = tarfile.TarInfo(name)
            info.type = tarfile.SYMTYPE
            info.linkname = target
            tar.addfile(info)
    return gzip.compress(buf.getvalue())


def source(title: str) -> bytes:
    return tarball({"ms.tex": f"\\documentclass{{amsart}}\n\\title{{{title}}}\n\\begin{{document}}\nx\n".encode()})


def fake_pdf(first_page: str) -> bytes:
    """A PDF in the shape the fake toolchain's pdftotext reads (tests/fake_latex)."""
    return f"%PDF-1.4\n%FAKE-LOOM\n%%Pages: 1\n{first_page}\n".encode()


class Transport:
    """Stands in for `fetch._get`: answers by URL, records every URL asked."""

    def __init__(self, answers: dict[str, bytes | Exception]) -> None:
        self.answers = answers
        self.urls: list[str] = []

    def __call__(self, url: str, attempts: int = 3) -> bytes:
        self.urls.append(url)
        got = self.answers.get(url, F.FetchRefused(f"{url}: HTTP 404 Not Found"))
        if isinstance(got, Exception):
            raise got
        return got


def fetching(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, answers: dict[str, bytes | Exception]
) -> tuple[Quilt, Transport]:
    q = demo(tmp_path)
    edit(q / "config.toml", "fetch = false", "fetch = true")
    t = Transport(answers)
    monkeypatch.setattr(F, "_get", t)
    return load_quilt(q), t


def man12(quilt: Quilt) -> BibEntry:
    return scan(quilt).bib["Man12"]


def test_a_source_titled_as_another_paper_is_discarded_and_nothing_is_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The arrival check is the guard: the right identifier serving the wrong paper leaves no source, no src.json and no PDF request."""
    quilt, t = fetching(tmp_path, monkeypatch, {EPRINT: source("The intrinsic normal cone"), PDF: fake_pdf("x")})
    entry = man12(quilt)
    got = F.fetch_work(quilt, "Man12", entry)
    home = F.work_dir(quilt.root, entry)
    assert not got.ok and got.files == [] and not got.source
    assert got.discarded.startswith('fetched source is titled "The intrinsic normal cone", which does not match')
    assert got.title_score is not None and got.title_score < F.ARRIVAL
    assert not (home / "src").exists() and not (home / "src.json").exists() and not (home / "paper.pdf").exists()
    assert t.urls == [EPRINT]


def test_a_source_that_arrives_is_filed_recorded_and_its_pdf_fetched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    quilt, t = fetching(
        tmp_path, monkeypatch, {EPRINT: source("Virtual pull-backs"), PDF: fake_pdf("Virtual pull-backs")}
    )
    entry = man12(quilt)
    got = F.fetch_work(quilt, "Man12", entry)
    home = F.work_dir(quilt.root, entry)
    assert got.ok and got.source and got.pdf and (got.ident, got.via) == ("0805.2065v2", "declared")
    assert got.files == [home / "src" / "ms.tex", home / "paper.pdf"] and got.refused == ""
    recorded = json.loads((home / "src.json").read_text())
    assert (recorded["identifier"], recorded["via"]) == ("arxiv:0805.2065v2", "declared")
    assert t.urls == [EPRINT, PDF]
    # a PDF already on disk is not asked for again
    t.urls.clear()
    F.fetch_work(quilt, "Man12", entry)
    assert t.urls == [EPRINT]


def test_a_failed_source_still_takes_the_pdf_and_records_no_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    quilt, _ = fetching(tmp_path, monkeypatch, {PDF: fake_pdf("Virtual pull-backs")})
    entry = man12(quilt)
    got = F.fetch_work(quilt, "Man12", entry)
    assert got.ok and got.pdf and not got.source and got.refused == ""
    assert not (F.work_dir(quilt.root, entry) / "src.json").exists()


def test_the_gates_refuse_before_anything_is_asked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fetching off, no entry, no identifier at all, and a candidate-only entry under `allow_candidate=False` each refuse with no request."""
    quilt, t = fetching(tmp_path, monkeypatch, {})
    bare = BibEntry("Bare", "article", {"title": "Virtual pull-backs", "author": "Manolache, C.", "year": "2012"})
    assert F.fetch_work(quilt, "Nope", None).refused == "Nope is not in the bibliography"
    assert "names no arXiv identifier or PDF link" in F.fetch_work(quilt, "Bare", bare).refused
    save(
        quilt.root,
        bare,
        [
            Candidate(
                id="doi:10.1/x",
                source="crossref",
                confidence=0.97,
                title="Virtual pull-backs",
                also=["arxiv:0805.2065"],
            )
        ],
    )
    refusal = F.fetch_work(quilt, "Bare", bare, allow_candidate=False).refused
    assert refusal == "Bare declares no identifier (a candidate exists; pass --candidates to use it)"
    off = load_quilt(quilt.root)
    off.config.fetch = False
    assert F.fetch_work(off, "Man12", man12(off)).refused.startswith("fetching is off: set fetch = true under [refs]")
    assert t.urls == []
    # the same candidate, allowed, is fetched on and says so
    t.answers["https://export.arxiv.org/e-print/0805.2065"] = source("Virtual pull-backs")
    got = F.fetch_work(quilt, "Bare", bare, pdf=False)
    assert got.ok and got.via == "candidate"


def test_an_entry_with_only_a_pdf_link_is_fetched_from_it_and_checked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Book 8.9: kept only if its first page carries the entry's title, and dated in fetched.json with its hash."""
    url = "https://example.org/~a/notes.pdf"
    quilt, t = fetching(tmp_path, monkeypatch, {url: b"<html>not a pdf</html>"})

    def entry(key: str) -> BibEntry:
        return BibEntry(key, "misc", {"title": "Stacks and moduli", "author": "Alper, J.", "year": "2024", "url": url})

    got = F.fetch_work(quilt, "A", entry("A"))
    assert (
        got.refused == f"{url} did not return a PDF" and not (F.work_dir(quilt.root, entry("A")) / "paper.pdf").exists()
    )

    t.answers[url] = fake_pdf("Lecture notes on something else entirely\nby Somebody")
    got = F.fetch_work(quilt, "B", entry("B"))
    assert got.discarded.startswith(f"the PDF at {url} does not carry this entry's title")
    assert not (F.work_dir(quilt.root, entry("B")) / "paper.pdf").exists()

    t.answers[url] = fake_pdf("Stacks and moduli\nJarod Alper")
    got = F.fetch_work(quilt, "C", entry("C"))
    home = F.work_dir(quilt.root, entry("C"))
    assert got.ok and (got.via, got.ident) == ("url", url) and got.files == [home / "paper.pdf"]
    stamp = json.loads((home / "fetched.json").read_text())
    assert stamp["url"] == url and stamp["sha256"] == sha256_of(home / "paper.pdf") and stamp["fetched"].endswith("Z")


# ---- _get ------------------------------------------------------------------


class Server:
    """Stands in for `urllib.request.urlopen`: fails with each code in turn, then answers."""

    def __init__(self, failures: list[int | str], body: bytes = b"ok") -> None:
        self.failures = list(failures)
        self.body = body
        self.calls = 0

    def __call__(self, req: urllib.request.Request, timeout: float) -> io.BytesIO:
        self.calls += 1
        assert req.get_header("User-agent") == F.USER_AGENT
        if self.failures:
            f = self.failures.pop(0)
            if isinstance(f, str):
                raise urllib.error.URLError(f)
            raise urllib.error.HTTPError(req.full_url, f, "No", {}, None)  # type: ignore[arg-type]
        return io.BytesIO(self.body)


@pytest.fixture
def pauses(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    slept: list[float] = []
    monkeypatch.setattr(time, "sleep", slept.append)
    return slept


def serve(monkeypatch: pytest.MonkeyPatch, failures: list[int | str]) -> Server:
    s = Server(failures)
    monkeypatch.setattr(urllib.request, "urlopen", s)
    return s


@pytest.mark.parametrize("code", [406, 429, 500, 502, 503, 504])
def test_get_retries_a_busy_answer_twice_with_a_growing_pause(
    code: int, monkeypatch: pytest.MonkeyPatch, pauses: list[float]
) -> None:
    """Book 8.9 (DR-77): 406, 429 and 5xx are retried twice, after 3 s and then 6 s."""
    s = serve(monkeypatch, [code, code])
    assert F._get("https://x/y") == b"ok"
    assert (s.calls, pauses) == (3, [3.0, 6.0])


def test_get_gives_up_after_three_attempts_and_names_the_last_answer(
    monkeypatch: pytest.MonkeyPatch, pauses: list[float]
) -> None:
    s = serve(monkeypatch, [503, 503, 503])
    with pytest.raises(F.FetchRefused, match=r"https://x/y: HTTP 503 No"):
        F._get("https://x/y")
    assert (s.calls, pauses) == (3, [3.0, 6.0])


def test_get_does_not_retry_a_refusal_but_does_retry_an_unreachable_host(
    monkeypatch: pytest.MonkeyPatch, pauses: list[float]
) -> None:
    s = serve(monkeypatch, [404])
    with pytest.raises(F.FetchRefused, match="HTTP 404"):
        F._get("https://x/y")
    assert (s.calls, pauses) == (1, [])
    s = serve(monkeypatch, ["name not known"])
    assert F._get("https://x/y") == b"ok" and s.calls == 2


# ---- _unpack ----------------------------------------------------------------


def test_unpack_refuses_every_member_that_would_land_outside_its_directory(tmp_path: Path) -> None:
    """Book 8.9: an e-print is untrusted input. `..`, an absolute name, a sibling sharing the directory's name as a prefix, and links are all skipped."""
    home = tmp_path / "work"
    dest = home / "src"
    data = tarball(
        {
            "ms.tex": b"kept",
            "fig/a.tex": b"kept too",
            "../escaped.tex": b"no",
            "../src-evil/x.tex": b"no",
            str(tmp_path / "absolute.tex"): b"no",
        },
        links={"link.tex": "/etc/passwd"},
    )
    written = F._unpack(data, dest)
    assert sorted(p.relative_to(dest).as_posix() for p in written) == ["fig/a.tex", "ms.tex"]
    assert sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file()) == [
        "work/src/fig/a.tex",
        "work/src/ms.tex",
    ]


@pytest.mark.parametrize(
    ("data", "name"),
    [(b"%PDF-1.5 body", "paper.pdf"), (gzip.compress(b"\\documentclass{article}"), "main.tex")],
    ids=["pdf", "gzipped-single-file"],
)
def test_unpack_files_a_pdf_or_a_single_file_under_a_fixed_name(tmp_path: Path, data: bytes, name: str) -> None:
    written = F._unpack(data, tmp_path / "src")
    assert written == [tmp_path / "src" / name]
    assert written[0].read_bytes() == (gzip.decompress(data) if name == "main.tex" else data)
