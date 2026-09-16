from loom.scan.hashing import child_marker, hash_text, normalize
from loom.scan.labels import is_id_shaped, next_local, split_id


def test_id_grammar_loomlocal_and_paperlocal() -> None:
    assert is_id_shaped("rl-0004")
    assert is_id_shaped("rl-000Z")
    assert not is_id_shaped("rl-0004x")
    assert not is_id_shaped("lem:res-indep")
    assert not is_id_shaped("rl-intro")
    assert is_id_shaped("Man12-thm-4.1", {"Man12"})
    assert is_id_shaped("stacksproject-05QA", {"stacksproject"})
    assert not is_id_shaped("Man12-thm 4.1", {"Man12"})
    assert split_id("sec-intro") == ("sec", "intro") and not is_id_shaped("sec-intro")


def test_alloc_next_base36() -> None:
    assert next_local([]) == "0001"
    assert next_local(["0001", "000Z", "0012"]) == "0013"
    assert next_local(["ZZZZ"]) == "10000"[-5:]  # overflow grows; never collides
    assert next_local(["intro", "0009"]) == "000A"


def test_normalize_comments_whitespace() -> None:
    raw = "\\begin{lemma}\t x  \n% a comment line\n  % !LOOM tags: a\nline % inline stays\n\n\n\nlast\r\n"
    assert normalize(raw) == "\\begin{lemma}     x\n  % !LOOM tags: a\nline % inline stays\n\nlast\n"
    assert hash_text(raw) == hash_text(raw.replace("% a comment line\n", ""))
    assert hash_text(raw) != hash_text(raw + child_marker("rl-0001"))
    assert normalize("") == "" and normalize("\n\n") == ""
