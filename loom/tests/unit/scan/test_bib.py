from pathlib import Path

from loom.scan.bib import citekey_slug, parse_bib

BIB = r"""
@comment{ignored}
@string{jams = "J. Amer. Math. Soc."}
@article{Man12,
  author = {Manolache, Cristina},
  title = {Virtual pull-backs},
  year = 2012,
  eprint = {0805.2065v2},
  journal = jams # {, extra},
}
@book(stacks-project, author="The Stacks Project Authors", title={{Stacks} Project}, url={https://stacks.math.columbia.edu})
@misc{Parker: gluing,
 title = {Gluing}}
"""


def test_bib_entries_and_fields() -> None:
    entries = parse_bib(BIB)
    assert set(entries) == {"Man12", "stacks-project", "Parker: gluing"}
    man = entries["Man12"]
    assert man.type == "article"
    assert man.fields["author"] == "Manolache, Cristina"
    assert man.fields["year"] == "2012"
    assert man.eprint == "0805.2065v2" and man.version == "2"
    assert entries["stacks-project"].fields["title"] == "{Stacks} Project"


def test_citekey_slug() -> None:
    assert citekey_slug("stacks-project") == "stacksproject"
    assert citekey_slug("Parker: gluing") == "Parkergluing"
    assert citekey_slug("Man12") == "Man12"


def test_the_quilts_bibliography_is_the_only_bib_read(tmp_path: Path) -> None:
    """An author's `.bib`, a fetched source's, a run's: none is the quilt's bibliography until `loom refs scan` copies an entry into `digests/bibliography.bib` (book 8.15)."""
    from tests.unit.scan.helpers import PREAMBLE, make_quilt

    result = make_quilt(
        tmp_path,
        {
            "drafting/main.tex": PREAMBLE + "\\begin{document}\n\\end{document}\n",
            "refs.bib": "@book{Author, title={Mine}}\n",
            "refs/arxiv/1/src/theirs.bib": "@book{Theirs, title={Theirs}}\n",
            "digests/bibliography.bib": "@book{Owned, title={Owned}}\n",
        },
    )
    assert set(result.bib) == {"Owned"}
