"""Property harness for writes to a person's files: random sequences of acts on a copy of a quilt, invariants checked after each act.

Drivers: InProc calls loom.render.api.handle directly; Http talks to a real `loom serve`. Acts are symbolic (random numbers resolved against the world at run time) so a failing sequence can be shrunk by deleting acts.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

for _m in ("AI_AGENT", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CODEX_SANDBOX", "CURSOR_AGENT", "GEMINI_CLI"):
    os.environ.pop(_m, None)

LOOM_VENV = Path("/Users/isaac/dev/loom-arras/.claude/worktrees/v01-study/loom/.venv/bin")
AGENT = "Agent Smith"
PERSON_ENV = {k: v for k, v in os.environ.items()}

WORDS = (
    "orbit group action finite widget lemma bound measure compact dense closed open map kernel image quotient "
    "series limit sequence converges uniformly hence therefore suppose assume each every some there exists "
    "integral norm space vector basis linear operator spectrum martingale drift volatility hedge price option"
).split()


# ---------------------------------------------------------------------------------------------------------------- files


def person_files(root: Path) -> dict[str, bytes]:
    """Every file of the quilt outside `.loom/`, by relative path, as bytes."""
    out: dict[str, bytes] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        rel = Path(dirpath).relative_to(root)
        if rel.parts[:1] == (".loom",):
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if not (rel == Path(".") and d == ".loom")]
        for f in filenames:
            p = Path(dirpath) / f
            if p.is_symlink() or not p.is_file():
                continue
            out[(rel / f).as_posix()] = p.read_bytes()
    return out


def flat(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def paragraphs(data: bytes) -> Counter[str]:
    """Paragraphs of twenty words or more, whitespace normalised, counted."""
    text = data.decode("utf-8", "replace")
    out: Counter[str] = Counter()
    for para in re.split(r"\n[ \t]*\n", text.replace("\r\n", "\n")):
        f = flat(para)
        if len(f.split()) >= 20:
            out[f] += 1
    return out


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------------------------------------------- drivers


class InProc:
    """The write API's handler, called in this process."""

    name = "inproc"

    def __init__(self, root: Path) -> None:
        self.root = root

    def call(self, endpoint: str, body: dict[str, Any]) -> dict[str, Any]:
        from loom.render.api import ApiError, handle

        try:
            return handle(self.root, endpoint, dict(body))
        except ApiError as exc:
            return {**exc.answer(), "status": exc.status}

    def stop(self) -> None:
        pass


class Http:
    """A real `loom serve --no-compile` over HTTP."""

    name = "http"

    def __init__(self, root: Path, port: int, env: dict[str, str]) -> None:
        self.root = root
        self.port = port
        log = open(root.parent / f"serve-{port}.log", "w")
        self.proc = subprocess.Popen(
            [str(LOOM_VENV / "loom"), "serve", "--no-compile", "--port", str(port), "--quilt", str(root)],
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=root,
        )
        deadline = time.time() + 180
        self.token = ""
        while time.time() < deadline:
            try:
                data = json.loads((root / ".loom/serve.json").read_text())
                if data.get("port") == port and data.get("pid") == self.proc.pid:
                    self.token = str(data.get("token") or "")
                    # wait for first build: the API answers
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/_api", timeout=5).read()
                    break
            except (OSError, ValueError, urllib.error.URLError):
                pass
            if self.proc.poll() is not None:
                raise RuntimeError(f"serve exited {self.proc.returncode}")
            time.sleep(0.2)
        else:
            raise RuntimeError("serve never came up")
        # wait until the first build is published (manifest exists)
        deadline = time.time() + 300
        while time.time() < deadline and not (root / ".loom/build/manifest.json").is_file():
            time.sleep(0.2)

    def call(self, endpoint: str, body: dict[str, Any]) -> dict[str, Any]:
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/_api/{endpoint}",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "X-Loom-Token": self.token},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            try:
                return {**json.loads(e.read()), "status": e.code}
            except ValueError:
                return {"error": {"code": "http", "message": str(e)}, "status": e.code}

    def stop(self) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()


# ---------------------------------------------------------------------------------------------------------------- world


@dataclass
class Meta:
    """What the harness knows about one suggested edit."""

    id: str
    key: str
    file: str
    placement: str
    with_text: str
    marker: str | None
    quote: str | None
    person_typed: bool = False


@dataclass
class Failure:
    check: str
    act_index: int
    act: dict[str, Any]
    detail: str

    def sig(self) -> str:
        return f"{self.check}@{self.act.get('op')}"


@dataclass
class World:
    root: Path
    driver: Any
    rng: random.Random
    metas: dict[str, Meta] = field(default_factory=dict)
    counter: int = 0
    live_typed: set[str] = field(default_factory=set)
    gone_typed: set[str] = field(default_factory=set)
    last_request: tuple[str, dict[str, Any]] | None = None
    keeps: list[dict[str, Any]] = field(default_factory=list)  # (doc files bytes before, version, edit ids)
    discards: list[dict[str, Any]] = field(default_factory=list)  # in-place discards: (path, from digest, bytes before)
    ticks: list[dict[str, Any]] = field(default_factory=list)
    settings_before: list[bytes] = field(default_factory=list)
    log: list[str] = field(default_factory=list)
    dirty: bool = False  # a person's or agent's own write since the last request
    ev: dict[str, list[str]] = field(default_factory=dict)  # what happened to each edit, for classifying a failure

    def note(self, eid: str | None, what: str) -> None:
        if eid:
            self.ev.setdefault(eid, []).append(what)

    def mark(self, kind: str) -> str:
        self.counter += 1
        letters = "".join(chr(ord("a") + (self.counter * 7 + i * 3) % 26) for i in range(3))
        return f"{kind}{letters}{self.counter:03d}x"

    def scan(self):
        from loom.scan.quilt import load_quilt
        from loom.scan.scan import scan

        return scan(load_quilt(self.root))

    def pending(self, result=None):
        from loom.pending import pending

        result = result or self.scan()
        from loom.scan.quilt import reviewer_identity

        return pending(result, reviewer_identity(self.root)[0] or "")


def setup_quilt(src: Path, dst: Path, variant: str = "") -> Path:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("build", ".git", "serve.json"))
    (dst / "tasks.md").write_text(
        "# Tasks\n\n- [ ] read the proof of the first lemma again\n- [x] write the second answer\n- [ ] check the bound in problem three\n",
        encoding="utf-8",
    )
    if variant == "crlf":
        for p in sorted(dst.rglob("*.tex")):
            if ".loom" in p.parts:
                continue
            p.write_bytes(p.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    return dst


# ---------------------------------------------------------------------------------------------------------------- blocks


def person_blocks(result) -> list[Any]:
    """Statements and proofs (and documents, for `after \\maketitle`) in files a person's document reads."""
    out = []
    for key, n in result.nodes.items():
        if n.file.startswith(".loom/") or n.kind not in ("environment", "proof", "master", "file"):
            continue
        if not any(result.document_role(d) == "person" for d in (n.reached_by or [])) and n.kind != "master":
            continue
        out.append(n)
    return sorted(out, key=lambda n: (n.file, n.start))


def own_text(result, node) -> str:
    from loom.records.store import Records

    return Records.own_pieces(result, node)[0]


def pick_quote(own: str, r: int) -> str | None:
    from loom.records.selectors import find_quote

    toks = [m for m in re.finditer(r"\S+", own)]
    if len(toks) < 3:
        return None
    rng = random.Random(r)
    for _ in range(30):
        i = rng.randrange(len(toks))
        n = rng.randint(2, 5)
        j = min(len(toks) - 1, i + n - 1)
        q = own[toks[i].start() : toks[j].end()]
        if q.startswith("-") or q.strip() == "-" or "%" in q or len(q) < 4:
            continue
        if len(find_quote(own, q)) == 1:
            return q
    return None


def sentence(rng: random.Random, n: int, marker: str | None) -> str:
    ws = [rng.choice(WORDS) for _ in range(n)]
    if marker:
        ws.insert(rng.randrange(len(ws) + 1), marker)
    return " ".join(ws)


# ---------------------------------------------------------------------------------------------------------------- acts


def suggest(w: World, key: str, with_text: str, quote: str | None, placement: str) -> str | None:
    from click.testing import CliRunner

    from loom.cli import main

    args = ["suggest", key, "--with", with_text, "--as", AGENT, "--json", "--quilt", str(w.root)]
    if quote:
        args += ["--quote", quote]
    if placement == "before":
        args.append("--before")
    if placement == "after":
        args.append("--after")
    res = CliRunner().invoke(main, args, env={"AI_AGENT": "1"}, catch_exceptions=True)
    if res.exit_code != 0:
        return None
    try:
        return str(json.loads(res.stdout)["edit"])
    except (ValueError, KeyError):
        return None


def act_suggest(w: World, a: dict[str, Any]) -> dict[str, Any]:
    result = w.scan()
    blocks = person_blocks(result)
    if not blocks:
        return {"skip": "no blocks"}
    rng = random.Random(a["r"])
    size = a["size"]
    if size == "after-maketitle":
        masters = [n for n in blocks if n.kind == "master" and "\\maketitle" in result.files[n.file].text]
        if not masters:
            size = "section"
        else:
            node = masters[a["r"] % len(masters)]
            marker = w.mark("sm")
            text = (
                f"\\section*{{Problem {marker}}}\n" + sentence(rng, 24, None) + "\n\\begin{proof}[Answer]\n" + sentence(rng, 30, None) + "\n\\end{proof}"
            )
            eid = suggest(w, node.key, text, "\\maketitle", "after")
            if eid:
                w.metas[eid] = Meta(eid, node.key, node.file, "after", text, marker, "\\maketitle")
            return {"edit": eid, "key": node.key}
    cand = [n for n in blocks if n.kind in ("environment", "proof")] or blocks
    node = cand[a["block"] % len(cand)]
    own = own_text(result, node)
    placement = a["placement"]
    quote = None
    if a.get("on") == "quote":
        quote = pick_quote(own, a["r"])
        if quote is None:
            return {"skip": "no quote"}
    if a.get("on") == "inside" and w.metas:
        # quote text inside another open edit's quoted range, or the same paragraph
        others = [m for m in w.metas.values() if m.key == node.key and m.quote]
        if others:
            q = others[0].quote or ""
            parts = q.split()
            quote = " ".join(parts[: max(1, len(parts) - 1)]) if len(parts) > 1 else q
            from loom.records.selectors import find_quote

            if len(find_quote(own, quote)) != 1:
                quote = others[0].quote
    marker = w.mark("sg")
    if size == "short":
        text = sentence(rng, rng.randint(1, 6), marker)
    elif size == "long":
        text = sentence(rng, rng.randint(22, 60), marker)
    elif size == "section":
        text = f"\\section*{{Part {marker}}}\n" + sentence(rng, 25, None) + "\n\\begin{proof}\n" + sentence(rng, 25, None) + "\n\\end{proof}"
        placement = "after" if placement == "replace" else placement
    elif size == "coincident":
        # text already standing elsewhere in the block: a phrase the agent proposes again
        toks = own.split()
        if len(toks) < 6:
            return {"skip": "short block"}
        i = rng.randrange(len(toks) - 3)
        text = " ".join(toks[i : i + rng.randint(2, 4)])
        marker = None
        if quote is None:
            placement = "after" if placement == "replace" else placement
    elif size == "delete":
        if not quote:
            return {"skip": "delete needs quote"}
        text = ""
        placement = "replace"
        marker = None
    else:
        text = sentence(rng, 5, marker)
    if quote is None and placement == "replace" and size != "long":
        placement = "after"
    eid = suggest(w, node.key, text, quote, placement)
    if eid:
        w.metas[eid] = Meta(eid, node.key, node.file, placement, text, marker, quote)
    return {"edit": eid, "key": node.key, "placement": placement, "size": size}


def person_write(w: World, rel: str, text: str) -> None:
    p = w.root / rel
    data = p.read_bytes()
    crlf = b"\r\n" in data
    out = text.replace("\r\n", "\n")
    if crlf:
        out = out.replace("\n", "\r\n")
    p.write_bytes(out.encode("utf-8"))


def act_person(w: World, a: dict[str, Any]) -> dict[str, Any]:
    kind = a["kind"]
    rng = random.Random(a["r"])
    result = w.scan()
    files = sorted(
        f for f in result.files if not f.startswith(".loom/") and f.endswith(".tex") and (w.root / f).is_file()
    )
    if not files:
        return {"skip": "no files"}
    metas = [m for m in w.metas.values() if (w.root / m.file).is_file()]
    if kind in ("inside_kept", "inside_quote", "type_suggestion") and not metas:
        kind = "elsewhere"
    if kind == "inside_kept":
        # work inside a suggestion's text that stands in the file (2e106a45)
        standing = [m for m in metas if m.marker and m.marker in (w.root / m.file).read_text("utf-8", "replace")]
        if not standing:
            return {"skip": "nothing standing"}
        m = standing[a["r"] % len(standing)]
        text = (w.root / m.file).read_bytes().decode("utf-8").replace("\r\n", "\n")
        at = text.find(m.marker)
        typed = w.mark("pt")
        new = text[: at + len(m.marker)] + f" {typed} with care" + text[at + len(m.marker) :]
        person_write(w, m.file, new)
        w.live_typed.add(typed)
        w.note(m.id, "edited-inside")
        return {"file": m.file, "typed": typed, "edit": m.id}
    if kind == "inside_quote":
        m = metas[a["r"] % len(metas)]
        if not m.quote:
            return {"skip": "no quote"}
        text = (w.root / m.file).read_bytes().decode("utf-8").replace("\r\n", "\n")
        at = text.find(m.quote.split()[0])
        if at < 0:
            return {"skip": "quote gone"}
        typed = w.mark("pt")
        new = text[:at] + typed + " " + text[at:]
        person_write(w, m.file, new)
        w.live_typed.add(typed)
        return {"file": m.file, "typed": typed}
    if kind == "type_suggestion":
        # the person types an open suggestion's text in by hand, where it goes
        from loom.records.edits import Placed, compose, find

        opens = [m for m in metas if (e := find(w.root, m.id)) is not None and e.status == "open" and m.with_text]
        if not opens:
            return {"skip": "none open"}
        m = opens[a["r"] % len(opens)]
        e = find(w.root, m.id)
        placed = next((pl for ed, pl in compose(result, [e]) if isinstance(pl, Placed)), None)
        if placed is None:
            return {"skip": "unplaced"}
        text = result.files[placed.file].text
        x, y = placed.at
        person_write(w, placed.file, text[:x] + placed.text + text[y:])
        m.person_typed = True
        w.note(m.id, "typed-by-person")
        return {"file": placed.file, "edit": m.id}
    f = files[a["r"] % len(files)]
    text = (w.root / f).read_bytes().decode("utf-8", "replace").replace("\r\n", "\n")
    typed = w.mark("pt")
    line = f"% {typed} a note the person wrote\n"
    if kind == "above":
        nl = text.find("\n", len(text) // 3)
        at = 0 if nl < 0 else nl + 1
        new = text[:at] + line + text[at:]
    elif kind == "append":
        new = text + ("" if text.endswith("\n") else "\n") + line
    elif kind == "elsewhere":
        nodes = [n for n in person_blocks(result) if n.file == f and n.kind in ("environment", "proof")]
        if nodes:
            n = nodes[a["r"] % len(nodes)]
            mid = n.start + (n.end - n.start) // 2
            sp = text.find(" ", mid, n.end)
            at = sp if sp > 0 else mid
            new = text[:at] + f" {typed} " + text[at:]
        else:
            new = text + line
    elif kind == "empty":
        for t in list(w.live_typed):
            if t in text:
                w.live_typed.discard(t)
        person_write(w, f, "")
        return {"file": f}
    elif kind == "rename":
        dst = f[:-4] + "-renamed.tex"
        (w.root / f).rename(w.root / dst)
        return {"file": f, "to": dst}
    else:
        new = text + line
    person_write(w, f, new)
    w.live_typed.add(typed)
    return {"file": f, "typed": typed}


def act_agent_inplace(w: World, a: dict[str, Any]) -> dict[str, Any]:
    """An agent edits a file directly (edit tracking): replaces a few words in a proof."""
    result = w.scan()
    blocks = [n for n in person_blocks(result) if n.kind in ("environment", "proof")]
    if not blocks:
        return {"skip": "no blocks"}
    n = blocks[a["r"] % len(blocks)]
    own = own_text(result, n)
    q = pick_quote(own, a["r"])
    if q is None:
        return {"skip": "no quote"}
    text = (w.root / n.file).read_bytes().decode("utf-8").replace("\r\n", "\n")
    at = text.find(q, n.start)
    if at < 0:
        return {"skip": "not found"}
    marker = w.mark("ag")
    person_write(w, n.file, text[:at] + f"{marker} " + sentence(random.Random(a["r"]), 3, None) + text[at + len(q) :])
    return {"file": n.file, "marker": marker}


def pick_pending(w: World, r: int, kind: str | None = None) -> Any:
    ps = [p for p in w.pending() if kind is None or p.kind == kind]
    if not ps:
        return None
    return ps[r % len(ps)]


def api(w: World, endpoint: str, body: dict[str, Any]) -> dict[str, Any]:
    w.last_request = (endpoint, dict(body))
    w.dirty = False
    return w.driver.call(endpoint, body)


def documents_of(w: World, paths: list[str]) -> dict[str, list[str]]:
    from loom.history.acts import documents_reaching
    from loom.history.steps import document_files

    result = w.scan()
    return {d: document_files(result, d) for d in documents_reaching(result, paths)}


def newest_version(w: World, doc: str) -> Any:
    from loom.history.acts import versions_of
    from loom.history.ledger import load_history

    result = w.scan()
    vs = versions_of(load_history(result.quilt.history_dir), doc, result.masters)
    return vs[-1] if vs else None




def classify(w: World, m: Meta) -> str:
    """The likely underlying fault behind an open edit whose text stands, or a text standing twice."""
    ev = w.ev.get(m.id, [])
    q = m.quote or ""
    if "\\end{" in q or "\\begin{" in q:
        return "outside-block"
    if "reopened-after-keep" in ev:
        return "reopened-after-keep"
    if "concurrent-keep" in ev:
        return "race"
    if "edited-inside" in ev and len(m.with_text.split()) < 20:
        return "short-edited"
    if m.key.count("#") and m.key.split("#")[-1].split(":")[0] in ("proof", "lemma", "theorem", "remark", "section"):
        return "by-place-key"
    if "typed-by-person" in ev:
        return "typed-not-seen"
    return "other"


# ---------------------------------------------------------------------------------------------------------------- invariants


class Checker:
    def __init__(self, w: World) -> None:
        self.w = w
        self.failures: list[Failure] = []

    seen: set = set()

    def fail(self, check: str, i: int, a: dict[str, Any], detail: str, once: str | None = None) -> None:
        if once is not None:
            if (check, once) in self.seen:
                return
            self.seen = self.seen | {(check, once)}
        self.failures.append(Failure(check, i, a, detail[:1500]))

    def marker_counts(self, files: dict[str, bytes]) -> Counter[str]:
        c: Counter[str] = Counter()
        markers = [m.marker for m in self.w.metas.values() if m.marker]
        blob = {k: v.decode("utf-8", "replace") for k, v in files.items() if k.endswith((".tex", ".md"))}
        for mk in markers:
            c[mk] = sum(t.count(mk) for t in blob.values())
        return c

    def in_history(self, data: bytes) -> str:
        """'exact' when these bytes are kept in the history's texts; 'normalised' when only LF text is; '' when neither."""
        hist = self.w.root / ".loom/history/texts"
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return ""
        p = hist / f"{sha(text)}.md"
        if p.is_file() and p.read_bytes() == data:
            return "exact"
        lf = text.replace("\r\n", "\n").replace("\r", "\n")
        if (hist / f"{sha(lf)}.md").is_file():
            return "normalised"
        return ""

    def typed_somewhere(self, mk: str, files: dict[str, bytes]) -> bool:
        b = mk.encode()
        if any(b in v for v in files.values()):
            return True
        hist = self.w.root / ".loom/history"
        for p in hist.rglob("*"):
            if p.is_file() and p.suffix in (".md", ".tex") and b in p.read_bytes():
                return True
        return False

    def after_loom(self, i: int, a: dict[str, Any], before: dict[str, bytes], after: dict[str, bytes], allowed: set[str] | None, expect_marker: dict[str, int] | None) -> None:
        w = self.w
        changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
        if allowed is not None and not changed <= allowed:
            self.fail("only-named-files", i, a, f"changed {sorted(changed - allowed)} allowed {sorted(allowed)}")
        tmp = [k for k in after if k.endswith(".loom-tmp")]
        if tmp:
            self.fail("temp-left", i, a, str(tmp))
        # paragraphs duplicated
        for k in changed & set(after):
            pb, pa = paragraphs(before.get(k, b"")), paragraphs(after[k])
            for para, n in pa.items():
                if n > pb.get(para, 0) and (pb.get(para, 0) >= 1 or n >= 2):
                    self.fail("paragraph-repeated", i, a, f"{k}: {n} (was {pb.get(para, 0)}) x {para[:160]}")
        # line endings and bytes outside the act
        for k in changed & set(before) & set(after):
            if before[k].count(b"\r\n") > after[k].count(b"\r\n") + 2:
                self.fail("line-endings-rewritten", i, a, f"{k}: CRLF {before[k].count(b'\r\n')} -> {after[k].count(b'\r\n')}")
        # a version kept before each write
        for k in changed & set(before):
            if before[k] == b"":
                continue
            how = self.in_history(before[k])
            if how == "":
                self.fail("no-version-before-write", i, a, f"{k}: text before the write is kept nowhere")
            elif how == "normalised":
                self.fail("version-not-byte-exact", i, a, f"{k}: only a normalised text is kept")
        # typed bytes
        for mk in sorted(w.live_typed):
            if not any(mk.encode() in v for v in after.values()):
                if not self.typed_somewhere(mk, after):
                    self.fail("typed-bytes-lost", i, a, f"{mk} gone and in no kept version")
                w.live_typed.discard(mk)
                w.gone_typed.add(mk)
        # markers
        counts = self.marker_counts(after)
        if expect_marker is not None:
            for mk, n in expect_marker.items():
                if counts.get(mk, 0) != n:
                    self.fail("marker-count", i, a, f"{mk}: {counts.get(mk, 0)} expected {n}")
        for mk, n in counts.items():
            if n > 1:
                owner = next((x for x in w.metas.values() if x.marker == mk), None)
                self.fail("duplicated", i, a, f"[{classify(w, owner) if owner else '?'}] {mk} stands {n} times", once=mk)
        self.records(i, a, counts, self.marker_counts(before))

    def records(self, i: int, a: dict[str, Any], counts: Counter[str], before_counts: Counter[str] | None = None) -> None:
        from loom.records.edits import replay

        w = self.w
        edits = {e.id: e for e in replay(w.root)[0]}
        try:
            states = {p.id: p for p in w.pending() if p.kind == "suggested"}
        except Exception as exc:  # noqa: BLE001
            self.fail("pending-crashed", i, a, repr(exc))
            return
        for eid, m in w.metas.items():
            e = edits.get(eid)
            if e is None or not m.marker:
                continue
            n = counts.get(m.marker, 0)
            st = states.get(eid)
            if e.status == "open" and st is not None and st.state == "ready" and n > 0:
                self.fail("open-ready-but-in-text", i, a, f"[{classify(w, m)}] {eid} on {m.key} ({m.placement} {m.quote!r}, {len(m.with_text.split())} words; {w.ev.get(eid)}) stands {n}x yet Keep would write it again", once=eid)
            if e.status == "open" and st is not None and st.state == "taken" and n == 0:
                self.fail("taken-but-absent", i, a, f"{eid}: reads as taken, its text is nowhere", once=eid)
            if e.status == "kept" and n == 0 and not m.person_typed and (before_counts is None or before_counts.get(m.marker, 0) > 0):
                self.fail("kept-but-absent", i, a, f"{eid}: recorded kept, its text is not in the file", once=eid)
        # phantom taken: a coincident edit read as taken that nobody wrote
        for eid, st in states.items():
            m = w.metas.get(eid)
            if m and not m.marker and st.state == "taken" and not m.person_typed and m.with_text:
                self.fail("phantom-taken", i, a, f"{eid}: '{m.with_text[:60]}' reads as taken because the words stand elsewhere in its block; Keep would record it kept and write nothing", once=eid)


# ---------------------------------------------------------------------------------------------------------------- the runner


OPS = [
    ("suggest", 22),
    ("person", 12),
    ("keep", 14),
    ("keep_all", 4),
    ("discard", 5),
    ("undo_keep_record", 4),
    ("undo_keep_reopen", 3),
    ("undo_discard", 3),
    ("repeat", 6),
    ("restore", 3),
    ("tick", 3),
    ("settings", 2),
    ("agent_inplace", 5),
    ("keep_inplace", 3),
    ("discard_inplace", 4),
    ("undo_inplace_discard", 3),
    ("concurrent_keep", 3),
    ("save_during_keep", 3),
]


def draw_act(rng: random.Random) -> dict[str, Any]:
    ops, weights = zip(*OPS)
    op = rng.choices(ops, weights)[0]
    a: dict[str, Any] = {"op": op, "r": rng.randrange(10**6)}
    if op == "suggest":
        a["block"] = rng.randrange(10**6)
        a["size"] = rng.choices(["short", "long", "section", "coincident", "delete", "after-maketitle"], [5, 4, 2, 2, 1, 2])[0]
        a["placement"] = rng.choice(["replace", "before", "after"])
        a["on"] = rng.choices(["quote", "body", "inside"], [6, 2, 1])[0]
    if op == "person":
        a["kind"] = rng.choices(
            ["inside_kept", "inside_quote", "elsewhere", "above", "append", "empty", "rename", "type_suggestion"],
            [4, 2, 3, 3, 2, 1, 1, 2],
        )[0]
    return a


def draw_sequence(seed: int, n: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    return [draw_act(rng) for _ in range(n)]


def run_sequence(src: Path, work: Path, acts: list[dict[str, Any]], driver: str = "inproc", port: int = 0, variant: str = "", stop_at_first: bool = True, track_edits: bool | None = None) -> tuple[list[Failure], list[dict[str, Any]]]:
    root = setup_quilt(src, work / "q", variant)
    if track_edits is not None:
        from loom.config_edit import set_values
        from loom.scan.quilt import load_quilt

        set_values(load_quilt(root), {"review.track_edits": track_edits})
    if driver == "http":
        env = {**PERSON_ENV}
        d: Any = Http(root, port, env)
    else:
        d = InProc(root)
    w = World(root, d, random.Random(0))
    ck = Checker(w)
    trace: list[dict[str, Any]] = []
    try:
        # the person's first look, where edits are tracked
        api(w, "change-keep", {"all": True})
        w.last_request = None
        for i, a in enumerate(acts):
            before = person_files(root)
            try:
                info = run_act(w, ck, i, a, before)
            except Exception as exc:  # noqa: BLE001
                info = {"crash": repr(exc), "tb": traceback.format_exc()[-1500:]}
                ck.fail("harness-or-loom-crash", i, a, info["tb"])
            trace.append({"i": i, **a, **{k: v for k, v in info.items() if k != "tb"}})
            if stop_at_first and ck.failures:
                break
    finally:
        d.stop()
    return ck.failures, trace


def run_act(w: World, ck: Checker, i: int, a: dict[str, Any], before: dict[str, bytes]) -> dict[str, Any]:
    op = a["op"]
    r = a["r"]
    if op == "suggest":
        w.dirty = True
        for k in w.keeps:
            k["clean"] = False
        info = act_suggest(w, a)
        after = person_files(w.root)
        ck.after_loom(i, a, before, after, set(), None)
        return info
    if op == "person":
        w.dirty = True
        for k in w.keeps:
            k["clean"] = False
        out = act_person(w, a)
        now = person_files(w.root)
        w.live_typed = {t for t in w.live_typed if any(t.encode() in v for v in now.values())}
        return out
    if op == "agent_inplace":
        w.dirty = True
        for k in w.keeps:
            k["clean"] = False
        return act_agent_inplace(w, a)
    if op in ("keep", "keep_all", "concurrent_keep"):
        result = w.scan()
        ps = w.pending(result)
        sug = [p for p in ps if p.kind == "suggested"]
        if op == "keep_all":
            body: dict[str, Any] = {"all": True}
            chosen = ps
        else:
            if not sug:
                return {"skip": "nothing to keep"}
            p = sug[r % len(sug)]
            body = {"changes": [p.id]}
            chosen = [p]
        expect: dict[str, int] = {}
        counts = ck.marker_counts(before)
        for p in chosen:
            m = w.metas.get(p.id)
            if m and m.marker:
                expect[m.marker] = counts.get(m.marker, 0) + (1 if p.state == "ready" else 0)
        allowed = {p.path for p in chosen if p.kind == "suggested"}
        docs_before = {}
        for p in chosen:
            if p.kind == "suggested" and p.state == "ready":
                for d, fs in documents_of(w, [p.path]).items():
                    docs_before[d] = {f: before.get(f) for f in fs}
        if op == "concurrent_keep":
            outs: list[Any] = []
            if isinstance(w.driver, Http):
                env = {**PERSON_ENV}
                cmd = [str(LOOM_VENV / "loom"), "changes", "--keep", body["changes"][0], "--quilt", str(w.root)]
                t = threading.Thread(target=lambda: outs.append(w.driver.call("change-keep", body)))
                t.start()
                cp = subprocess.run(cmd, env=env, capture_output=True, text=True)
                t.join()
                outs.append({"cli": cp.returncode, "out": cp.stdout[-300:] + cp.stderr[-300:]})
            else:
                from loom.render.api import handle

                ready = [p for p in sug if p.state == "ready"]
                p0 = chosen[0]
                twin = next((q for q in ready if q.path == p0.path and q.id != p0.id), None)
                bodies = [body, {"changes": [twin.id]} if twin else body]
                if twin:
                    chosen = [p0, twin]
                    allowed.add(twin.path)
                    m2 = w.metas.get(twin.id)
                    if m2 and m2.marker:
                        expect[m2.marker] = counts.get(m2.marker, 0) + 1

                def go(b: dict[str, Any]) -> None:
                    try:
                        outs.append(handle(w.root, "change-keep", dict(b)))
                    except Exception as exc:  # noqa: BLE001
                        outs.append(repr(exc))

                ts = [threading.Thread(target=go, args=(b,)) for b in bodies]
                for t in ts:
                    t.start()
                for t in ts:
                    t.join()
            w.last_request = ("change-keep", body)
            for p in chosen:
                w.note(p.id, "concurrent-keep")
            ans: Any = outs
        else:
            ans = api(w, "change-keep", body)
        for p in chosen:
            w.note(p.id, "kept")
        after = person_files(w.root)
        ck.after_loom(i, a, before, after, allowed, expect)
        # a repeated request changes nothing
        refused_first = op == "concurrent_keep" and "Error" in str(ans)
        again = w.driver.call("change-keep", body) if body.get("changes") and not refused_first else None
        if again is not None:
            after2 = person_files(w.root)
            if after2 != after:
                ch = sorted(k for k in set(after) | set(after2) if after.get(k) != after2.get(k))
                ck.fail("repeat-changed", i, a, f"second press changed {ch}: {json.dumps(again)[:300]}")
                ck.after_loom(i, {**a, "op": "repeat-of-" + op}, after, after2, allowed, expect)
        # what was written, for undo-from-the-record
        if docs_before:
            vs = {d: newest_version(w, d) for d in docs_before}
            for k in w.keeps:
                k["clean"] = False
            w.keeps.append({"clean": True, "docs": docs_before, "versions": {d: (v.name if v else None) for d, v in vs.items()}, "ids": [p.id for p in chosen]})
        return {"answer": str(ans)[:300]}
    if op == "discard":
        p = pick_pending(w, r, "suggested")
        if p is None:
            return {"skip": "nothing"}
        ans = api(w, "change-discard", {"changes": [p.id], "why": "not this"})
        after = person_files(w.root)
        ck.after_loom(i, a, before, after, set(), None)
        return {"answer": str(ans)[:200], "id": p.id}
    if op == "undo_keep_reopen":
        from loom.records.edits import replay

        kept = [e for e in replay(w.root)[0] if e.status == "kept" and e.id in w.metas]
        if not kept:
            return {"skip": "none kept"}
        e = kept[r % len(kept)]
        w.note(e.id, "reopened-after-keep")
        ans = api(w, "change-discard", {"changes": [e.id], "undo": True})
        after = person_files(w.root)
        ck.after_loom(i, a, before, after, set(), None)
        return {"answer": str(ans)[:200], "id": e.id}
    if op == "undo_discard":
        from loom.records.edits import replay

        gone = [e for e in replay(w.root)[0] if e.status == "discarded" and e.id in w.metas]
        if not gone:
            return {"skip": "none discarded"}
        e = gone[r % len(gone)]
        ans = api(w, "change-discard", {"changes": [e.id], "undo": True})
        after = person_files(w.root)
        ck.after_loom(i, a, before, after, set(), None)
        return {"answer": str(ans)[:200]}
    if op == "undo_keep_record":
        if not w.keeps:
            return {"skip": "no keep"}
        k = w.keeps.pop()
        out = []
        for d, files in k["docs"].items():
            v = k["versions"].get(d)
            if not v:
                ck.fail("no-version-to-undo", i, a, f"no version of {d} to undo the keep of {k['ids']}")
                continue
            ans = api(w, "history-restore", {"document": d, "version": v})
            out.append(str(ans)[:200])
            now = person_files(w.root)
            for f, data in files.items():
                if data is not None and now.get(f) != data and k.get("clean"):
                    # differs because the person or a later act changed it since: compare only when nothing else touched it
                    if k is not None and len(w.keeps) >= 0:
                        ck.fail("undo-keep-not-exact", i, a, f"{d}/{f}: restoring {v} does not give back the bytes before the keep ({len(now.get(f) or b'')} vs {len(data)})")
        after = person_files(w.root)
        allowed = {f for files in k["docs"].values() for f in files}
        ck.after_loom(i, a, before, after, allowed, None)
        return {"answer": out}
    if op == "repeat":
        if not w.last_request:
            return {"skip": "nothing sent"}
        ep, body = w.last_request
        ans = w.driver.call(ep, body)
        after = person_files(w.root)
        if after != before and not w.dirty:
            ch = sorted(k for k in set(after) | set(before) if after.get(k) != before.get(k))
            ck.fail("repeat-changed", i, a, f"{ep} sent again changed {ch}")
        ck.after_loom(i, a, before, after, None, None)
        return {"endpoint": ep, "answer": str(ans)[:200]}
    if op == "restore":
        from loom.history.acts import versions_of
        from loom.history.ledger import load_history
        from loom.records.snapshots import read_raw

        result = w.scan()
        docs = [d for d in result.masters if result.document_role(d) == "person"]
        if not docs:
            return {"skip": "no docs"}
        d = docs[r % len(docs)]
        hist = load_history(result.quilt.history_dir)
        vs = [v for v in versions_of(hist, d, result.masters) if v.get("files")]
        if not vs:
            return {"skip": "no versions"}
        v = vs[(r // 7) % len(vs)]
        ans = api(w, "history-restore", {"document": d, "version": v.name})
        after = person_files(w.root)
        files = v.get("files") or {}
        if "error" not in ans:
            for f, dig in files.items():
                want = read_raw(w.root, dig, result.quilt.history_dir)
                if want is not None and after.get(f, b"").decode("utf-8", "replace") != want:
                    ck.fail("restore-not-exact", i, a, f"{f} after restore differs from the version")
            # restore again: nothing
            again = w.driver.call("history-restore", {"document": d, "version": v.name})
            if person_files(w.root) != after:
                ck.fail("repeat-changed", i, a, "restore sent twice changed files")
        ck.after_loom(i, a, before, after, set(files) | {d}, None)
        return {"answer": str(ans)[:200], "version": v.name}
    if op == "tick":
        from loom.tasks import items

        p = w.root / "tasks.md"
        if not p.is_file():
            return {"skip": "no tasks"}
        ts = items(p.read_text("utf-8"))
        if not ts:
            return {"skip": "no boxes"}
        t = ts[r % len(ts)]
        ans = api(w, "file-tick", {"path": "tasks.md", "task": t.id, "done": not t.done})
        after = person_files(w.root)
        ck.after_loom(i, a, before, after, {"tasks.md"}, None)
        # untick: bytes back exactly
        t2 = next((x for x in items(p.read_text("utf-8")) if x.line == t.line), None)
        if t2 is not None and "error" not in ans:
            api(w, "file-tick", {"path": "tasks.md", "task": t2.id, "done": t.done})
            if person_files(w.root).get("tasks.md") != before.get("tasks.md"):
                ck.fail("untick-not-exact", i, a, "tick then untick changed tasks.md")
        return {"answer": str(ans)[:200]}
    if op == "settings":
        old = before.get("config.toml", b"")
        name = f"quilt {r}"
        ans = api(w, "settings-save", {"changes": {"quilt.name": name}})
        after = person_files(w.root)
        ck.after_loom(i, a, before, after, {"config.toml"}, None)
        import tomllib

        try:
            prev = tomllib.loads(old.decode())["quilt"]["name"]
        except Exception:  # noqa: BLE001
            prev = None
        if prev is not None and "error" not in ans:
            api(w, "settings-save", {"changes": {"quilt.name": prev}})
            if person_files(w.root).get("config.toml") != old:
                ck.fail("settings-undo-not-exact", i, a, "saving the old name back does not give back config.toml")
        st = os.stat(w.root / "config.toml").st_mode & 0o777
        if st != 0o644 and "error" not in ans:
            ck.fail("config-mode-changed", i, a, f"config.toml mode now {oct(st)}")
        return {"answer": str(ans)[:200]}
    if op in ("keep_inplace", "discard_inplace"):
        p = pick_pending(w, r, "edit")
        if p is None:
            return {"skip": "no in-place change"}
        ep = "change-keep" if op == "keep_inplace" else "change-discard"
        ans = api(w, ep, {"changes": [p.id]})
        after = person_files(w.root)
        allowed = set() if op == "keep_inplace" else {p.path}
        ck.after_loom(i, a, before, after, allowed, None)
        if op == "discard_inplace" and "error" not in ans:
            from loom.history.ledger import load_history

            e = load_history(w.root / ".loom/history").entries[-1]
            w.discards.append({"path": p.path, "from": e.get("from"), "bytes": before.get(p.path)})
            # the old words are back: the agent's marker is gone from the file
            agm = re.findall(r"ag[a-z]{3}\d{3}x", (p.new or ""))
            for mk in agm:
                if mk.encode() in after.get(p.path, b""):
                    ck.fail("discard-left-change", i, a, f"{mk} still in {p.path}")
            again = w.driver.call(ep, {"changes": [p.id]})
            if person_files(w.root) != after:
                ck.fail("repeat-changed", i, a, "discard of an in-place change sent twice changed files")
        return {"answer": str(ans)[:200]}
    if op == "undo_inplace_discard":
        if not w.discards:
            return {"skip": "no discard"}
        dsc = w.discards.pop()
        if not dsc["from"]:
            return {"skip": "no from"}
        ans = api(w, "history-restore", {"path": dsc["path"], "text": dsc["from"]})
        after = person_files(w.root)
        if "error" not in ans and after.get(dsc["path"]) != dsc["bytes"]:
            ck.fail("undo-discard-not-exact", i, a, f"{dsc['path']}: putting back the text the discard set aside does not give back the bytes")
        ck.after_loom(i, a, before, after, {dsc["path"]}, None)
        return {"answer": str(ans)[:200]}
    if op == "save_during_keep":
        # the person's editor saves the file while a Keep is under way: after loom scanned, before it wrote
        result = w.scan()
        ready = [p for p in w.pending(result) if p.kind == "suggested" and p.state == "ready"]
        if not ready:
            return {"skip": "nothing ready"}
        p = ready[r % len(ready)]
        typed = w.mark("pt")
        path = w.root / p.path

        def save() -> None:
            text = path.read_bytes().decode("utf-8")
            path.write_bytes((text + f"% {typed} saved by the editor\n").encode("utf-8"))

        if isinstance(w.driver, Http):
            def late() -> None:
                time.sleep(random.Random(r).uniform(0.02, 0.25))
                save()
            t = threading.Thread(target=late)
            t.start()
            ans = api(w, "change-keep", {"changes": [p.id]})
            t.join()
        else:
            import loom.history.acts as acts

            orig = acts.keep_versions

            def patched(*args: Any, **kwargs: Any) -> Any:
                out = orig(*args, **kwargs)
                if args[2] == acts.APPLY:
                    save()
                return out

            acts.keep_versions = patched
            try:
                ans = api(w, "change-keep", {"changes": [p.id]})
            finally:
                acts.keep_versions = orig
        w.live_typed.add(typed)
        after = person_files(w.root)
        ck.after_loom(i, a, before, after, {p.path}, None)
        return {"answer": str(ans)[:200], "typed": typed, "file": p.path}
    return {"skip": f"unknown {op}"}


def shrink(src: Path, work: Path, acts: list[dict[str, Any]], sig: str, **kw: Any) -> list[dict[str, Any]]:
    """Delta-debug `acts` to a shortest list whose run still fails with signature `sig`."""

    def fails(xs: list[dict[str, Any]]) -> bool:
        fs, _ = run_sequence(src, work, xs, **kw)
        return any(f.sig() == sig for f in fs)

    # cut after the failing act first
    n = 2
    cur = list(acts)
    while len(cur) >= 2:
        chunk = max(1, len(cur) // n)
        reduced = False
        for start in range(0, len(cur), chunk):
            cand = cur[:start] + cur[start + chunk :]
            if cand and fails(cand):
                cur, n, reduced = cand, max(n - 1, 2), True
                break
        if not reduced:
            if chunk == 1:
                break
            n = min(len(cur), n * 2)
    return cur
