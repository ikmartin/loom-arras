"""Compare two HTML trees of loom output modulo whitespace: tokens are start/end tags with attributes, and text with runs of whitespace collapsed.

Usage: python3 -I htmlcmp.py DIR_A DIR_B [--show N]   (compares every *.html present in both, recursively)
"""

import difflib
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


class Tok(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.toks = []
        self.text = []

    def flush(self):
        t = re.sub(r"\s+", " ", "".join(self.text)).strip()
        if t:
            self.toks.append("T " + t)
        self.text = []

    def handle_starttag(self, tag, attrs):
        self.flush()
        self.toks.append("<" + tag + " " + " ".join(f"{k}={v}" for k, v in sorted(attrs)))

    def handle_endtag(self, tag):
        self.flush()
        self.toks.append("</" + tag)

    def handle_data(self, data):
        self.text.append(data)


def toks(p):
    t = Tok()
    t.feed(p.read_text(errors="replace"))
    t.flush()
    return t.toks


def words(p):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", p.read_text(errors="replace"))).split()


def main():
    a, b = Path(sys.argv[1]), Path(sys.argv[2])
    show = int(sys.argv[sys.argv.index("--show") + 1]) if "--show" in sys.argv else 0
    files = sorted(p.relative_to(a) for p in a.rglob("*.html") if (b / p.relative_to(a)).is_file())
    only_a = sorted(p.relative_to(a) for p in a.rglob("*.html") if not (b / p.relative_to(a)).is_file())
    only_b = sorted(p.relative_to(b) for p in b.rglob("*.html") if not (a / p.relative_to(b)).is_file())
    byte_same = tok_same = word_same = 0
    diffs = []
    for f in files:
        pa, pb = a / f, b / f
        if pa.read_bytes() == pb.read_bytes():
            byte_same += 1
            continue
        ta, tb = toks(pa), toks(pb)
        if ta == tb:
            tok_same += 1
            continue
        if words(pa) == words(pb):
            word_same += 1
        d = [x for x in difflib.unified_diff(ta, tb, lineterm="", n=0) if x[:1] in "+-" and x[:3] not in ("+++", "---")]
        diffs.append((f, len(d), words(pa) == words(pb), d))
    print(f"files compared {len(files)}; byte-identical {byte_same}; identical modulo whitespace {tok_same}; differing in markup only (same words) {word_same}; differing in words {len(diffs) - word_same}; only in A {len(only_a)}; only in B {len(only_b)}")
    for f, n, same_words, d in diffs:
        print(f"  {f}: {n} token lines differ{' (same words)' if same_words else ''}")
        for x in d[:show]:
            print("     ", x[:220])


main()
