"""File annotations and suggested edits on a copy of a paper, apply co-author edits, and classify where each record now sits.

Usage: python harness.py PAPER_DIR OUT_DIR RESULTS_JSON

Truth is tracked by anchors (file, offset) moved through every text operation the scenario performs: each target's block start and its quote's start. A record is `right` when it resolves to the block now at the truth anchor and, when it quotes, to the truth quote offset; `wrong` when it resolves anywhere else while not detached; `detached` when shown detached on a key that still names a block (`honest` when its truth is gone, `miss` when its block and words still stand); `lost` when its key names nothing now.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from loom.cli.review import _one_comment, _version
from loom.clock import stamp, today
from loom.records import edits as E
from loom.records.selectors import find_quote, make_selector
from loom.records.store import Records
from loom.render.manifest import key_hash
from loom.scan.labels import is_id_shaped, rename_labels
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan

try:
    from loom.records.store import place_context
except ImportError:  # today's code has none
    place_context = None

WORD = re.compile(r"^[A-Za-z][A-Za-z,.;:'-]*$")


# ---------------------------------------------------------------- targets


@dataclass
class Target:
    tid: str
    kind: str  # stmt-label | stmt-none | proof-of-label | proof-of-none | proof-alone | sec-label | sec-none | eq | master
    key: str  # the key records are filed on (canonical, as the CLI resolves it)
    block: str  # the node key that owns the text
    file: str
    start: int  # node start in file
    end: int
    qstart: int  # quote's offset in file
    quote: str
    stmt_start: int | None = None  # for proofs: their statement's start, so moves carry both
    stmt_end: int | None = None
    labels: list[str] = field(default_factory=list)


def _plain_window(own: str, n: int = 6) -> tuple[int, int] | None:
    toks = [(m.start(), m.end(), m.group()) for m in re.finditer(r"\S+", own)]
    if len(toks) < n:
        return None
    mid = len(toks) // 2
    order = sorted(range(len(toks) - n + 1), key=lambda i: abs(i - mid))
    for i in order:
        win = toks[i : i + n]
        if all(WORD.match(t[2]) for t in win):
            a, b = win[0][0], win[-1][1]
            if len(find_quote(own, own[a:b])) == 1:
                return a, b
    for i in order:
        win = toks[i : i + n]
        a, b = win[0][0], win[-1][1]
        if "\\" not in own[a:b] and "%" not in own[a:b] and len(find_quote(own, own[a:b])) == 1:
            return a, b
    return None


def pick_targets(result) -> list[Target]:
    nodes = [n for n in result.nodes.values() if not n.file.startswith(".loom") and not n.external]
    nodes.sort(key=lambda n: (n.file, n.start))
    out: list[Target] = []

    def add(kind: str, n, key: str | None = None, quote_span=None) -> None:
        own, pieces = Records.own_pieces(result, n)
        if n.kind == "master":
            # prose after \begin{document}
            pieces = [(c, f, l) for c, f, l in pieces if f + l > n.body_start]
            if not pieces:
                return
            c0 = pieces[0][0] + max(0, n.body_start - pieces[0][1])
            sub = own[c0 : c0 + 3000]
            span = _plain_window(sub)
            if span is None:
                return
            span = (span[0] + c0, span[1] + c0)
        else:
            span = quote_span or _plain_window(own)
        if span is None:
            return
        quote = own[span[0] : span[1]]
        if len(find_quote(own, quote)) != 1:
            return
        fs = Records.to_file_span(pieces, span)
        if fs is None:
            return
        t = Target(f"{kind}{sum(1 for x in out if x.kind == kind) + 1}", kind, key or n.key, n.key, n.file, n.start, n.end, fs[0], quote, labels=list(n.labels))
        if n.kind == "proof" and n.of:
            st = result.nodes[n.of]
            t.stmt_start, t.stmt_end = st.start, st.end
        out.append(t)

    def spread(items, k):
        if not items:
            return []
        if len(items) <= k:
            return items
        return [items[int((i + 1) * len(items) / (k + 1))] for i in range(k)]

    stmts = [n for n in nodes if n.kind == "environment" and not n.id]
    lab = [n for n in stmts if n.labels]
    nolab = [n for n in stmts if not n.labels]
    for n in spread(lab, 3):
        add("stmt-label", n)
    for n in spread(nolab, 2):
        add("stmt-none", n)
    proofs = [n for n in nodes if n.kind == "proof" and not n.id]
    pl = [p for p in proofs if p.of and result.nodes[p.of].labels and not result.nodes[p.of].id]
    pn = [p for p in proofs if p.of and not result.nodes[p.of].labels]
    pa = [p for p in proofs if not p.of]
    for n in spread(pl, 1):
        add("proof-of-label", n)
    for n in spread(pn, 1):
        add("proof-of-none", n)
    nonempty = [p for p in pa if len(Records.own_pieces(result, p)[0].split()) > 8]
    for n in spread(nonempty, 3):
        add("proof-alone", n)
    empty = [p for p in pa if len(Records.own_pieces(result, p)[0].split()) <= 2]
    if len(empty) >= 2:
        n = empty[len(empty) // 2]
        out.append(Target(f"proof-empty1", "proof-empty", n.key, n.key, n.file, n.start, n.end, -1, ""))
    ids = [n for n in nodes if n.kind == "environment" and n.id]
    for n in spread(ids, 2):
        add("stmt-id", n)
    secs = [n for n in nodes if n.kind == "section" and not n.id]
    for n in spread([s for s in secs if s.labels and len(Records.own_pieces(result, s)[0].split()) > 30], 1):
        add("sec-label", n)
    for n in spread([s for s in secs if not s.labels and len(Records.own_pieces(result, s)[0].split()) > 30], 1):
        add("sec-none", n)
    regs = [r for r in result.assembly.regions.values() if not r.file.startswith(".loom") and r.where in ("statement",) or r.where.startswith("proof:")]
    regs = [r for r in regs if not r.file.startswith(".loom") and not result.nodes[r.container].id]
    for r in spread(regs, 1) + regs[len(regs) // 2 :] + regs:
        if any(x.kind == "eq" for x in out):
            break
        cont = result.nodes[r.container]
        own, pieces = Records.own_pieces(result, cont)
        # the formula just after the \label inside the equation
        local = next((c + (r.offset - f) for c, f, l in pieces if f <= r.offset < f + l), None)
        if local is None:
            continue
        m = re.match(r"\\label\{[^}]*\}\s*", own[local:])
        if not m:
            continue
        qa = local + m.end()
        line = own[qa : qa + 40].split("\n")[0].rstrip()
        quote = line
        if len(quote) < 8 or len(find_quote(own, quote)) != 1:
            continue
        span = (qa, qa + len(quote))
        add("eq", cont, key=r.key, quote_span=span)
    for m in [n for n in nodes if n.kind == "master"][:1]:
        add("master", m)
    return out


# ---------------------------------------------------------------- filing


def file_records(root: Path, targets: list[Target]) -> list[dict]:
    result = scan(load_quilt(root))
    recs = []
    for t in targets:
        if t.kind == "proof-empty":
            said = _one_comment(result, ("human", "Tester"), t.key, f"whole-block note on {t.tid}", None, None, None, None)
            recs.append({"tid": t.tid, "type": "ann", "id": said.split()[0], "quoted": False})
            event = {"event": "created", "when": stamp(), "author": "Agent Tester", "kind": "agent", "target": t.key, "against": _version(result, t.key) or key_hash(result, t.key), "anchor": None, "with": "The answer an agent wrote for this problem.", "placement": "replace"}
            if place_context:
                event["context"] = place_context(result, result.nodes[t.key])
            recs.append({"tid": t.tid, "type": "edit", "id": E.append_new(root, event, today()), "quoted": False})
            t.file_hits = 0  # type: ignore[attr-defined]
            continue
        said = _one_comment(result, ("human", "Tester"), t.key, f"note on {t.tid}", t.quote, None, None, None)
        recs.append({"tid": t.tid, "type": "ann", "id": said.split()[0], "quoted": True})
        if t.kind in ("stmt-none", "proof-of-none", "proof-alone", "stmt-label", "sec-none"):
            said = _one_comment(result, ("human", "Tester"), t.key, f"whole-block note on {t.tid}", None, None, None, None)
            recs.append({"tid": t.tid, "type": "ann", "id": said.split()[0], "quoted": False})
        node_key = result.assembly.regions[t.key].container if t.key in result.assembly.regions else t.key
        node = result.nodes[node_key]
        own, _ = Records.own_pieces(result, node)
        # the shortest leading run of the quote's words that stands once in the block: how a person selects two words
        words = t.quote.split()
        for k in range(2, len(words)):
            short = " ".join(words[:k])
            if len(find_quote(own, short)) == 1:
                said = _one_comment(result, ("human", "Tester"), t.key, f"short-quote note on {t.tid}", short, None, None, None)
                recs.append({"tid": t.tid, "type": "ann", "id": said.split()[0], "quoted": True, "short": short})
                break
        text = result.files[t.file].text
        t.file_hits = len(find_quote(text, t.quote))  # type: ignore[attr-defined]
        sel = make_selector(own, t.quote)
        words = t.quote.split()
        new = " ".join(words[:-1] + [words[-1].upper() + "X"])
        event = {
            "event": "created",
            "when": stamp(),
            "author": "Agent Tester",
            "kind": "agent",
            "target": t.key,
            "against": _version(result, t.key) or key_hash(result, node_key),
            "anchor": sel.to_dict(),
            "with": new,
            "placement": "replace",
        }
        if place_context:
            event["context"] = place_context(result, node, t.quote)
        eid = E.append_new(root, event, today())
        recs.append({"tid": t.tid, "type": "edit", "id": eid, "quoted": True})
    return recs


# ---------------------------------------------------------------- workspace with tracked anchors


class WS:
    def __init__(self, root: Path):
        self.root = root
        self.files: dict[str, str] = {}
        self.anchors: dict[str, tuple[str, int] | None] = {}
        self.renamed: dict[str, str] = {}

    def load(self, path: str) -> str:
        if path not in self.files:
            self.files[path] = (self.root / path).read_text(encoding="utf-8", errors="surrogateescape")
        return self.files[path]

    def insert(self, path: str, pos: int, text: str) -> None:
        t = self.load(path)
        self.files[path] = t[:pos] + text + t[pos:]
        for k, v in self.anchors.items():
            if v and v[0] == path and v[1] >= pos:
                self.anchors[k] = (path, v[1] + len(text))

    def replace(self, path: str, a: int, b: int, text: str, keep: dict[str, int] | None = None) -> None:
        t = self.load(path)
        self.files[path] = t[:a] + text + t[b:]
        d = len(text) - (b - a)
        for k, v in self.anchors.items():
            if not v or v[0] != path:
                continue
            if keep and k in keep:
                self.anchors[k] = (path, a + keep[k])
            elif a <= v[1] < b and not (v[1] == a and text.startswith(t[a:b][:1]) and False):
                self.anchors[k] = None
            elif v[1] >= b:
                self.anchors[k] = (path, v[1] + d)

    def move(self, path: str, a: int, b: int, dest: str, dpos_before_cut: int) -> None:
        """Cut [a, b) of `path` and paste it at `dpos_before_cut` of `dest` (an offset read before the cut)."""
        t = self.load(path)
        cut = t[a:b]
        inside = {k: v[1] - a for k, v in self.anchors.items() if v and v[0] == path and a <= v[1] < b}
        self.files[path] = t[:a] + t[b:]
        for k, v in self.anchors.items():
            if k in inside or not v or v[0] != path:
                continue
            if v[1] >= b:
                self.anchors[k] = (path, v[1] - (b - a))
        if dest == path and dpos_before_cut >= b:
            dpos = dpos_before_cut - (b - a)
        else:
            dpos = dpos_before_cut
        d = self.load(dest)
        self.files[dest] = d[:dpos] + cut + d[dpos:]
        for k, v in self.anchors.items():
            if k in inside or not v or v[0] != dest:
                continue
            if v[1] >= dpos:
                self.anchors[k] = (dest, v[1] + len(cut))
        for k, off in inside.items():
            self.anchors[k] = (dest, dpos + off)

    def rename(self, old: str, new: str) -> None:
        self.load(old)
        self.files[new] = self.files.pop(old)
        self.renamed[old] = new
        for k, v in self.anchors.items():
            if v and v[0] == old:
                self.anchors[k] = (new, v[1])

    def write(self) -> None:
        for old in self.renamed:
            (self.root / old).unlink(missing_ok=True)
        for p, t in self.files.items():
            (self.root / p).parent.mkdir(parents=True, exist_ok=True)
            (self.root / p).write_text(t, encoding="utf-8", errors="surrogateescape")


# ---------------------------------------------------------------- co-author edits


def body_end(text: str) -> int:
    for pat in (r"\\bibliographystyle", r"\\bibliography\{", r"\\begin\{thebibliography\}", r"\\printbibliography", r"\\end\{document\}"):
        m = re.search(pat, text)
        if m:
            return m.start()
    return len(text)


def env_name_at(text: str, start: int) -> str:
    m = re.match(r"\\begin\{([^}]+)\}", text[start:])
    return m.group(1) if m else "theorem"


def insert_above(ws: WS, targets: list[Target]) -> None:
    """A co-author puts a new statement (with a proof) of each annotated kind, and a new unattached proof, above the first target in each file."""
    by_file: dict[str, list[Target]] = {}
    for t in targets:
        by_file.setdefault(ws.anchors[f"blk:{t.tid}"][0], []).append(t)
    for path, ts in by_file.items():
        text = ws.load(path)
        names = []
        for t in ts:
            s = ws.anchors.get(f"stmt:{t.tid}") or ws.anchors[f"blk:{t.tid}"]
            if (t.kind.startswith("stmt") and t.kind != "stmt-id") or t.kind.startswith("proof-of") or t.kind == "eq":
                names.append(env_name_at(text, s[1]))
        firsts = [ws.anchors.get(f"stmt:{t.tid}") or ws.anchors[f"blk:{t.tid}"] for t in ts if t.kind != "master"]
        if not firsts:
            continue
        pos = min(f[1] for f in firsts)
        # never inside an environment: back up to the line start
        pos = text.rfind("\n", 0, pos) + 1
        block = ""
        for name in dict.fromkeys(names):
            block += f"\\begin{{{name}}}\nA new result a co-author added above.\n\\end{{{name}}}\n\\begin{{proof}}\nIts short proof.\n\\end{{proof}}\n\n"
        if any(t.kind == "proof-empty" for t in ts):
            block += "\\begin{proof}[Answer]\n\\end{proof}\n\n"
        if any(t.kind == "proof-alone" for t in ts):
            block += "\\begin{proof}[Answer]\nA new answer a co-author added above.\n\\end{proof}\n\n"
        ws.insert(path, pos, block)


def insert_section_above(ws: WS, targets: list[Target]) -> None:
    for path in {ws.anchors[f"blk:{t.tid}"][0] for t in targets}:
        text = ws.load(path)
        m = re.search(r"\\(section)(\*?)\{", text)
        if not m:
            continue
        ws.insert(path, m.start(), f"\\section{m.group(2)}{{A section a co-author added}}\nSome words of the new section.\n\n")


def _body_of(text: str, start: int) -> tuple[int, int]:
    """The env body (after the \\begin line, before \\end) of the environment at `start`."""
    name = env_name_at(text, start)
    depth, i = 0, start
    pat = re.compile(r"\\(begin|end)\{" + re.escape(name) + r"\}")
    for m in pat.finditer(text, start):
        depth += 1 if m.group(1) == "begin" else -1
        if depth == 0:
            nl = text.find("\n", start)
            return (nl + 1 if 0 <= nl < m.start() else start), m.start()
    return start, start


def light_edit(ws: WS, targets: list[Target]) -> None:
    """A short sentence added inside each annotated block, away from the quoted words."""
    for t in targets:
        path, s = ws.anchors[f"blk:{t.tid}"] or (None, None)
        if path is None:
            continue
        q = ws.anchors[f"q:{t.tid}"]
        text = ws.load(path)
        if t.kind == "proof-empty":
            a, b = _body_of(text, s)
            ws.insert(path, b, "The person's own answer, written in.\n")
            continue
        if q is None:
            continue
        if t.kind in ("master", "sec-label", "sec-none"):
            # after the quote's sentence
            end = text.find(".", q[1] + len(t.quote))
            pos = end + 1 if end > 0 else q[1] + len(t.quote)
        else:
            a, b = _body_of(text, s)
            pos = b
            # end of body: before trailing whitespace
            while pos > a and text[pos - 1] in " \n\t":
                pos -= 1
        ws.insert(path, pos, " Indeed, a co-author added this sentence.")


def heavy_edit(ws: WS, targets: list[Target]) -> None:
    """Most of the words around the quote rewritten, the quote kept."""
    for t in targets:
        path, s = ws.anchors[f"blk:{t.tid}"] or (None, None)
        q = ws.anchors[f"q:{t.tid}"]
        if path is None or q is None:
            continue
        text = ws.load(path)
        qa, qb = q[1], q[1] + len(t.quote)
        if t.kind in ("master", "sec-label", "sec-none"):
            # the sentence that holds the quote
            a = max(text.rfind(". ", 0, qa) + 2, text.rfind("\n", 0, qa) + 1)
            nb = [x for x in (text.find(". ", qb), text.find("\n", qb)) if x >= 0]
            b = min(nb) if nb else qb
        else:
            a, b = _body_of(text, s)
            a, b = max(a, qa - 2000), min(b, qb + 2000)
            # keep \label lines at the head of the body
            head = re.match(r"(\s*(\\label\{[^}]*\}|\\uses\{[^}]*\})\s*)*", text[a:qa])
            a = a + (head.end() if head else 0)
        if a > qa or b < qb:
            continue
        labs = "".join(m.group(0) for m in re.finditer(r"\\label\{[^}]*\}", text[a:b]) if not (qa <= m.start() < qb))
        new = "Rewritten by a co-author: the argument now runs differently, and " + text[qa:qb] + " in the new wording, with more words after." + labs
        ws.replace(path, a, b, new, keep={f"q:{t.tid}": new.index(text[qa:qb])})


def edit_quote(ws: WS, targets: list[Target]) -> None:
    """The quoted words themselves rewritten."""
    for t in targets:
        q = ws.anchors.get(f"q:{t.tid}")
        if q is None:
            continue
        text = ws.load(q[0])
        qb = q[1] + len(t.quote)
        if text[q[1] : qb] != t.quote:
            continue
        ws.replace(q[0], q[1], qb, "words a co-author wrote instead")


def move_statements(ws: WS, targets: list[Target]) -> None:
    """Each annotated statement (with its proof) and each unattached proof cut and pasted at the end of the body."""
    done = set()
    for t in targets:
        if t.kind not in ("stmt-label", "stmt-none", "stmt-id", "proof-of-label", "proof-of-none", "proof-alone", "proof-empty", "eq"):
            continue
        sa = ws.anchors.get(f"stmt:{t.tid}") or ws.anchors[f"blk:{t.tid}"]
        if sa is None or sa in done:
            continue
        path, s = sa
        text = ws.load(path)
        # the statement and the proofs right after it
        _, e = _body_of(text, s)
        e = text.find("}", e) + 1
        while True:
            m = re.match(r"\s*\\begin\{proof\}", text[e:])
            if not m or t.kind in ("proof-alone", "proof-empty"):
                break
            _, pe = _body_of(text, e + m.end() - len("\\begin{proof}"))
            e = text.find("}", pe) + 1
        done.add(sa)
        ws.move(path, s, e, path, body_end(text))
        ws.insert(path, ws.anchors[f"blk:{t.tid}"][1], "\n")


def move_sections(ws: WS, targets: list[Target]) -> None:
    for t in targets:
        if t.kind not in ("sec-label", "sec-none"):
            continue
        path, s = ws.anchors[f"blk:{t.tid}"]
        text = ws.load(path)
        lvl = re.match(r"\\(section|subsection|subsubsection)", text[s:]).group(1)
        order = ["section", "subsection", "subsubsection"]
        stops = [r"\\" + x + r"\*?\{" for x in order[: order.index(lvl) + 1]]
        m = re.search("|".join(stops), text[s + 5 :])
        e = s + 5 + m.start() if m else body_end(text)
        e = min(e, body_end(text))
        # to just before the file's last section heading (or its first, when it is in the last), so it never swallows the bibliography
        heads = [h.start() for h in re.finditer(r"\\section\*?\{", text) if h.start() < body_end(text)]
        later = [h for h in heads if h >= e]
        dest = later[-1] if later else next((h for h in heads if h < s), s)
        ws.move(path, s, e, path, dest)


def rename_label_scn(ws: WS, targets: list[Target], result) -> None:
    renames = {}
    for t in targets:
        for lab in t.labels:
            if not is_id_shaped(lab, result.assembly.citeslugs):
                renames[lab] = lab + "-renamed"
        if t.kind == "eq":
            lab = t.key.rsplit("#", 1)[1]
            renames[lab] = lab + "-renamed"
    from loom.scan.labels import HYPERREF, LABEL_DEF, LABEL_REFS

    for path in list({v[0] for v in ws.anchors.values() if v}):
        text = ws.load(path)
        spans = []
        for pat in (LABEL_DEF, LABEL_REFS, HYPERREF):
            for m in pat.finditer(text):
                base = m.start(2)
                for part in re.finditer(r"[^,\s]+", m.group(2)):
                    if part.group() in renames:
                        spans.append((base + part.start(), base + part.end(), renames[part.group()]))
        for a, b, new in sorted(set(spans), reverse=True):
            ws.replace(path, a, b, new)


def delete_statements(ws: WS, targets: list[Target]) -> None:
    for t in targets:
        if t.kind not in ("stmt-label", "stmt-none", "stmt-id", "proof-alone", "proof-empty"):
            continue
        sa = ws.anchors.get(f"blk:{t.tid}")
        if sa is None:
            continue
        path, s = sa
        text = ws.load(path)
        _, e = _body_of(text, s)
        e = text.find("}", e) + 1
        if t.kind not in ("proof-alone", "proof-empty"):
            m = re.match(r"\s*\\begin\{proof\}", text[e:])
            if m:
                _, pe = _body_of(text, e + m.end() - len("\\begin{proof}"))
                e = text.find("}", pe) + 1
        ws.replace(path, s, e, "")


def _stmt_span(text: str, s: int, with_proof: bool) -> int:
    _, e = _body_of(text, s)
    e = text.find("}", e) + 1
    if with_proof:
        m = re.match(r"\s*\\begin\{proof\}", text[e:])
        if m:
            _, pe = _body_of(text, e + m.end() - len("\\begin{proof}"))
            e = text.find("}", pe) + 1
    return e


def label_reused(ws: WS, targets: list[Target]) -> None:
    """Each labelled statement deleted with its proof, and its label put on a new, different statement at the end of the body."""
    for t in targets:
        if t.kind != "stmt-label" or not t.labels:
            continue
        path, s = ws.anchors[f"blk:{t.tid}"]
        text = ws.load(path)
        name = env_name_at(text, s)
        e = _stmt_span(text, s, True)
        ws.replace(path, s, e, "")
        text = ws.load(path)
        ws.insert(path, body_end(text), f"\\begin{{{name}}}\\label{{{t.labels[0]}}}\nA different result that took over the label.\n\\end{{{name}}}\n")


def duplicate_label(ws: WS, targets: list[Target]) -> None:
    """Each labelled statement restated verbatim, label and all, near the top of its file (LaTeX warns of a label defined twice)."""
    first = {}
    for t in targets:
        a = ws.anchors.get(f"stmt:{t.tid}") or ws.anchors[f"blk:{t.tid}"]
        first[a[0]] = min(first.get(a[0], a[1]), a[1])
    for t in targets:
        if t.kind != "stmt-label":
            continue
        path, s = ws.anchors[f"blk:{t.tid}"]
        text = ws.load(path)
        e = _stmt_span(text, s, False)
        copy = text[s:e] + "\n"
        pos = text.rfind("\n", 0, first[path]) + 1
        ws.insert(path, pos, copy)
        first[path] = pos


def rename_file(ws: WS, targets: list[Target], cfg_main: str) -> None:
    files = {ws.anchors[f"blk:{t.tid}"][0] for t in targets}
    for path in files:
        new = re.sub(r"([^/]+)\.tex$", r"renamed-\1.tex", path)
        ws.rename(path, new)
        if path == cfg_main:
            ws.config_main = new  # type: ignore[attr-defined]


def split_file(ws: WS, targets: list[Target]) -> None:
    """The second half of each target file's body moved into its own file, \\input in its place."""
    for path in {ws.anchors[f"blk:{t.tid}"][0] for t in targets}:
        text = ws.load(path)
        end = body_end(text)
        secs = [m.start() for m in re.finditer(r"\\section\*?\{", text) if m.start() < end]
        if len(secs) < 2:
            continue
        cut = secs[len(secs) // 2]
        stem = path.rsplit("/", 1)[-1].removesuffix(".tex")
        part = path.rsplit("/", 1)[0] + f"/{stem}-part2.tex" if "/" in path else f"{stem}-part2.tex"
        ws.files[part] = ""
        ws.move(path, cut, end, part, 0)
        rel = part.removesuffix(".tex")
        ws.insert(path, cut, f"\\input{{{rel}}}\n")


SCENARIOS = {
    "insert-above": ["insert"],
    "insert-section-above": ["insert_section"],
    "light-edit": ["light"],
    "heavy-edit-keep-quote": ["heavy"],
    "quoted-words-edited": ["quote"],
    "move-statement": ["move"],
    "move-section": ["move_section"],
    "rename-label": ["rename_label"],
    "delete-statement": ["delete"],
    "rename-file": ["rename_file"],
    "split-file": ["split"],
    "insert-above+light-edit": ["insert", "light"],
    "insert-above+heavy-edit": ["insert", "heavy"],
    "move-statement+light-edit": ["move", "light"],
    "rename-label+light-edit": ["rename_label", "light"],
    "rename-file+light-edit": ["rename_file", "light"],
    "split-file+insert-above": ["split", "insert"],
    "label-reused": ["label_reused"],
    "duplicate-label": ["duplicate_label"],
}


def apply_scenario(root: Path, name: str, targets: list[Target], result, cfg_main: str) -> WS:
    ws = WS(root)
    for t in targets:
        ws.anchors[f"blk:{t.tid}"] = (t.file, t.start)
        ws.anchors[f"q:{t.tid}"] = (t.file, t.qstart) if t.qstart >= 0 else None
        if t.stmt_start is not None:
            ws.anchors[f"stmt:{t.tid}"] = (t.file, t.stmt_start)
    for step in SCENARIOS[name]:
        if step == "insert":
            insert_above(ws, targets)
        elif step == "insert_section":
            insert_section_above(ws, targets)
        elif step == "light":
            light_edit(ws, targets)
        elif step == "heavy":
            heavy_edit(ws, targets)
        elif step == "quote":
            edit_quote(ws, targets)
        elif step == "move":
            move_statements(ws, targets)
        elif step == "move_section":
            move_sections(ws, targets)
        elif step == "rename_label":
            rename_label_scn(ws, targets, result)
        elif step == "delete":
            delete_statements(ws, targets)
        elif step == "rename_file":
            rename_file(ws, targets, cfg_main)
        elif step == "split":
            split_file(ws, targets)
        elif step == "label_reused":
            label_reused(ws, targets)
        elif step == "duplicate_label":
            duplicate_label(ws, targets)
    ws.write()
    new_main = getattr(ws, "config_main", None)
    if new_main:
        cfg = (root / "config.toml").read_text()
        (root / "config.toml").write_text(cfg.replace(f'"{cfg_main}"', f'"{new_main}"'))
    # the truth for a quote is dead when its words no longer stand at the anchor
    for t in targets:
        q = ws.anchors.get(f"q:{t.tid}")
        if q is not None and t.quote:
            text = ws.files.get(q[0]) or (root / q[0]).read_text(encoding="utf-8", errors="surrogateescape")
            if text[q[1] : q[1] + len(t.quote)] != t.quote:
                ws.anchors[f"q:{t.tid}"] = None
    return ws


# ---------------------------------------------------------------- classify


def node_at(result, path: str, start: int, kind_hint: str):
    for n in result.nodes.values():
        if n.file == path and n.start == start and n.kind not in ("master", "file", "conflict"):
            return n
    if kind_hint == "master":
        return result.nodes.get(path)
    return None


def classify(root: Path, targets: list[Target], recs: list[dict], ws: WS) -> list[dict]:
    result = scan(load_quilt(root))
    R = Records(root)
    res_by_id = {r.annotation.id: r for r in R.resolved(result)}
    edits = {e.id: e for e in E.replay(root)[0]}
    tmap = {t.tid: t for t in targets}
    out = []
    for rec in recs:
        t = tmap[rec["tid"]]
        blk = ws.anchors.get(f"blk:{t.tid}")
        truth = node_at(result, blk[0], blk[1], "master" if t.kind == "master" else "") if blk else None
        if t.kind == "master" and blk:
            truth = result.nodes.get(blk[0])
        q = ws.anchors.get(f"q:{t.tid}")
        row = {"tid": t.tid, "kind": t.kind, "type": rec["type"], "quoted": rec["quoted"], "truth": truth.key if truth else None}
        if rec["type"] == "ann":
            r = res_by_id[rec["id"]]
            key = r.target or r.annotation.target_key
            n = result.nodes.get(key)
            if n is None and key in result.assembly.regions:
                n = result.nodes.get(result.assembly.regions[key].container)
            row["now"] = key
            if r.detached:
                row["outcome"] = "lost" if n is None else "detached"
            else:
                at = None
                if r.span is not None and n is not None:
                    own, pieces = Records.own_pieces(result, n)
                    fs = Records.to_file_span(pieces, r.span)
                    at = fs[0] if fs else None
                ok_block = truth is not None and n is not None and n.key == truth.key
                if not rec["quoted"]:
                    row["outcome"] = "right" if ok_block else "wrong"
                else:
                    row["outcome"] = "right" if ok_block and q is not None and at == q[1] else "wrong"
        else:
            e = edits[rec["id"]]
            node = E.home(result, e)
            row["now"] = node.key if node else None
            try:
                placed = E.place(result, e)
                ok_block = truth is not None and placed.key == truth.key and placed.file == truth.file
                if rec["quoted"]:
                    row["outcome"] = "right" if ok_block and q is not None and placed.at[0] == q[1] else "wrong"
                else:
                    row["outcome"] = "right" if ok_block else "wrong"
                row["now"] = placed.key
            except E.Unplaced:
                row["outcome"] = "lost" if node is None else "detached"
        if row["outcome"] == "detached":
            alive = truth is not None and q is not None if rec["quoted"] else truth is not None
            row["detail"] = ("miss" if alive else "honest") + ("" if truth is not None and row["now"] == truth.key else "-elsewhere")
        if row["outcome"] == "lost":
            alive = truth is not None and (q is not None or not rec["quoted"])
            row["detail"] = "miss" if alive else "honest"
        if row["outcome"] == "wrong":
            row["detail"] = "other-block" if truth is None or row["now"] != truth.key else "other-words"
        out.append(row)
    return out


def main(paper: Path, out: Path, results: Path, only: list[str] | None = None) -> None:
    out.mkdir(parents=True, exist_ok=True)
    base = out / "filed"
    if base.exists():
        shutil.rmtree(base)
    shutil.copytree(paper, base)
    (base / ".loom" / "serve.json").unlink(missing_ok=True)
    result = scan(load_quilt(base))
    targets = pick_targets(result)
    recs = file_records(base, targets)
    cfg_main = load_quilt(base).config.main if hasattr(load_quilt(base).config, "main") else ""
    all_rows = {}
    for name in SCENARIOS:
        if only and name not in only:
            continue
        work = out / name
        if work.exists():
            shutil.rmtree(work)
        shutil.copytree(base, work)
        ws = apply_scenario(work, name, targets, result, cfg_main)
        try:
            rows = classify(work, targets, recs, ws)
        except Exception as exc:  # report and go on
            rows = [{"error": repr(exc)}]
        all_rows[name] = rows
        c = Counter(r.get("outcome", "error") for r in rows)
        print(f"{paper.name:10s} {name:28s} " + " ".join(f"{k}={c[k]}" for k in ("right", "wrong", "detached", "lost", "error") if c[k]), flush=True)
    results.write_text(json.dumps({"targets": [t.__dict__ for t in targets], "records": recs, "rows": all_rows}, indent=1))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4:] or None)
