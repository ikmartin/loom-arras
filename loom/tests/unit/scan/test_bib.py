from pathlib import Path

from loom.scan.bib import citekey_slug, parse_bib
from loom.scan.scan import find_bib_files

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


def test_a_bib_inside_a_fetched_source_is_not_the_quilts(tmp_path: Path) -> None:
    (tmp_path / "refs.bib").write_text("")
    (tmp_path / "refs" / "arxiv" / "1" / "src").mkdir(parents=True)
    (tmp_path / "refs" / "arxiv" / "1" / "src" / "theirs.bib").write_text("")
    (tmp_path / "ai" / "runs" / "r").mkdir(parents=True)
    (tmp_path / "ai" / "runs" / "r" / "draft.bib").write_text("")
    assert find_bib_files(tmp_path) == ["refs.bib"]
