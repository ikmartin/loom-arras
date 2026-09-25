"""Links into what the viewer shows (plan 0.14 phase 3): `quilt:` for what the quilt owns, `cited:` for a place in a cited work, checked when an agent posts one and printed by `loom link`."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers import ok, refused
from tests.unit._quilts import demo


@pytest.fixture
def q(tmp_path: Path) -> Path:
    return demo(tmp_path)


def scanned(q: Path):  # type: ignore[no-untyped-def]
    from loom.cli._quilt import open_scan

    return open_scan(str(q))


def test_each_kind_resolves(q: Path) -> None:
    from loom.links import resolve

    result = scanned(q)
    assert resolve(result, q, "quilt:dm-0003").kind == "node"
    assert resolve(result, q, "quilt:dm-0003/proof").kind == "node"
    doc = resolve(result, q, "quilt:drafting/main.tex#dm-0003")
    assert (doc.kind, doc.key, doc.place) == ("document", "drafting/main.tex", "dm-0003")
    assert resolve(result, q, "quilt:a-2026-09-16-0001").kind == "annotation"
    assert resolve(result, q, "quilt:s-2026-09-16-0001").kind == "session"
    work = resolve(result, q, "cited:doi:10.4171/demo/14-1?page=2")
    assert (work.kind, work.key, work.place) == ("work", "Calloway14", "page=2")
    assert resolve(result, q, "cited:arxiv:0805.2065v2").key == "Man12"


def test_what_the_viewer_does_not_show_is_refused(q: Path) -> None:
    from loom.links import LinkError, resolve

    result = scanned(q)
    unreached = next(
        k for k, n in result.nodes.items() if n.kind == "environment" and "drafting/main.tex" not in n.reached_by
    )
    for href, why in [
        ("quilt:dm-9999", "no key"),
        ("quilt:nodes/dm-0001.tex", "file the documents include"),
        ("quilt:a-2026-01-01-0099", "no annotation"),
        ("quilt:s-2026-01-01-0099", "no session"),
        (f"quilt:drafting/main.tex#{unreached}", "does not include"),
        ("quilt:dm-0003#dm-0001", "is not in"),
        ("cited:doi:10.0/nobody", "no entry in the bibliography"),
        ("cited:Calloway14", "identifier"),
        ("cited:doi:10.4171/demo/14-1?page=zero", "page"),
    ]:
        with pytest.raises(LinkError, match=why):
            resolve(result, q, href)


def test_a_deleted_session_is_not_linkable(q: Path) -> None:
    from loom.links import LinkError, resolve

    ok("session", "delete", "s-2026-09-16-0001", "--author", "A. Author", cwd=q)
    with pytest.raises(LinkError, match="no session"):
        resolve(scanned(q), q, "quilt:s-2026-09-16-0001")


def test_check_names_every_bad_link(q: Path) -> None:
    from loom.links import check

    text = "See [](quilt:dm-0003), [this](quilt:dm-9999) and [that](cited:doi:10.0/none), and a [web page](https://example.org)."
    bad = check(scanned(q), q, text)
    assert len(bad) == 2 and "dm-9999" in bad[0] and "10.0/none" in bad[1]
    assert check(scanned(q), q, "no links at all") == []


def test_loom_link_prints_what_the_viewer_follows(q: Path) -> None:
    def link(*args: str) -> str:
        return ok("link", *args, cwd=q).output.strip()

    assert link("dm-0003") == "[](quilt:dm-0003)"
    assert link("drafting/main.tex", "--at", "dm-0003") == "[](quilt:drafting/main.tex#dm-0003)"
    assert link("a-2026-09-16-0004") == "[](quilt:a-2026-09-16-0004)"
    assert link("s-2026-09-16-0002") == "[](quilt:s-2026-09-16-0002)"
    assert (
        link("Calloway14", "--page", "2", "--quote", "a phrase")
        == "[](cited:doi:10.4171/demo/14-1?page=2&quote=a%20phrase)"
    )
    refused("link", "nodes/dm-0001.tex", cwd=q, code=1, match="file the documents include")
    refused("link", "dm-0003", "--page", "2", cwd=q, code=2, match="for a cited work")  # a page is a work's


def test_an_agent_posting_a_bad_link_is_refused_and_a_good_one_lands(q: Path) -> None:
    from loom.mailbox import read_events

    agent = {"AI_AGENT": "1"}
    sid = "s-2026-09-16-0002"
    bad = refused(
        "session",
        "say",
        "See [](quilt:dm-9999).",
        "--session",
        sid,
        "--as",
        "Referee Agent",
        cwd=q,
        env=agent,
        code=1,
        match="dm-9999",
    )
    assert "loom link" in bad.output
    ok("session", "say", "See [](quilt:dm-0003).", "--session", sid, "--as", "Referee Agent", cwd=q, env=agent)
    assert read_events(q, sid)[-1].body == "See [](quilt:dm-0003)."
    # an annotation's body the same way, when an agent writes it
    refused(
        "comment",
        "dm-0002",
        "As [](quilt:dm-9999) shows.",
        "--kind",
        "note",
        "--session",
        sid,
        "--author",
        "Referee Agent",
        cwd=q,
        env=agent,
        code=1,
        match="dm-9999",
    )
    # a person's comment is their own business
    ok(
        "comment",
        "dm-0002",
        "As [](quilt:dm-9999) shows.",
        "--kind",
        "note",
        "--session",
        sid,
        "--author",
        "A. Author",
        cwd=q,
    )


def test_the_formatting_document_is_in_force() -> None:
    text = (Path(__file__).resolve().parents[2] / "src" / "loom" / "assets" / "ai" / "formatting.md").read_text(
        encoding="utf-8"
    )
    assert "stub" not in text.lower() and "loom link" in text and "\\uses{" in text
