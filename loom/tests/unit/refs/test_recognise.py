"""What a pasted text is, read without the network: each kind of identifier in each form a person pastes it."""

from __future__ import annotations

import pytest

from loom.refs.identity import arxiv_base, recognise


@pytest.mark.parametrize(
    ("text", "kind", "value"),
    [
        ("10.1007/s002220050351", "doi", "10.1007/s002220050351"),
        ("doi:10.1090/S1056-3911-2011-00606-1", "doi", "10.1090/S1056-3911-2011-00606-1"),
        ("https://doi.org/10.1112/S0010437X20007393.", "doi", "10.1112/S0010437X20007393"),
        ("http://dx.doi.org/10.1007/BF01234659", "doi", "10.1007/BF01234659"),
        # arXiv's own DOI names a preprint
        ("10.48550/arXiv.2207.01652", "arxiv", "2207.01652"),
        ("arXiv:0805.2065", "arxiv", "0805.2065"),
        ("0805.2065v2", "arxiv", "0805.2065v2"),
        ("https://arxiv.org/abs/2207.01652v3", "arxiv", "2207.01652v3"),
        ("https://arxiv.org/pdf/2207.01652.pdf", "arxiv", "2207.01652"),
        ("math/9810166", "arxiv", "math/9810166"),
        ("arXiv:math.AG/9810166v2", "arxiv", "math.AG/9810166v2"),
        ("solv-int/9901001", "arxiv", "solv-int/9901001"),
        ("Zbl 0921.14007", "zbl", "0921.14007"),
        ("https://zbmath.org/?q=an:0921.14007", "zbl", "0921.14007"),
        ("MR1667326", "mr", "1667326"),
        ("MR 1667326", "mr", "1667326"),
        ("ISBN 978-0-387-98549-7", "isbn", "9780387985497"),
        ("0-387-98549-2", "isbn", "0387985492"),
    ],
)
def test_each_identifier_is_recognised_in_each_form(text: str, kind: str, value: str) -> None:
    got = recognise(text)
    assert (got.kind, got.value) == (kind, value), got


def test_a_bibtex_entry_is_read_with_its_identifiers() -> None:
    got = recognise(
        "@article{Hal21,\n  author = {Halberd, C.},\n  title = {Gadget towers},\n  year = {2021},\n  eprint = {2102.11789}, archivePrefix = {arXiv}\n}"
    )
    assert got.kind == "bibtex" and got.value == "Hal21"
    assert got.entry is not None and got.entry.fields["title"] == "Gadget towers"
    assert str(got.work_id) == "arXiv:2102.11789"


@pytest.mark.parametrize(
    "text",
    ["", "somewhere I read about widgets", "978-0-387-98549-8", "10.1/x", "@article", "MR12"],
)
def test_what_is_none_of_them_is_not_recognised(text: str) -> None:
    """A wrong ISBN check digit, a prefix too short for a DOI, an entry with no body: none is guessed at."""
    assert recognise(text).kind == "unknown"


def test_an_arxiv_version_is_cut_only_at_its_end() -> None:
    assert arxiv_base("0805.2065v2") == "0805.2065"
    assert arxiv_base("solv-int/9901001v1") == "solv-int/9901001"
    assert arxiv_base("solv-int/9901001") == "solv-int/9901001"
