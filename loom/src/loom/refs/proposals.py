"""Proposed and verified digest results (plan 0.12 §4.1, §5; digest contract §9).

Three files per cited work, and the split between them is the whole design.

- `digests/<citekey>.tex` holds **verified nodes only**. It is what a bundle `\\input`s.
- `digests/<citekey>.proposed.tex` holds proposals. loom scans it and **nothing ever `\\input`s it**, so a proposal cannot enter a closure, be cited, or reach a compile. That is a structural guarantee rather than a check. It is a `.tex` rather than rows in JSON because a proposal exists to be *looked at*, and the pipeline that turns LaTeX into something a person can look at is the one that reads `.tex` files.
- `digests/<citekey>.results.json` carries what the document cannot: both texts, the anchor, the level, the state and the provenance. Contract §9 governs its shape, so a digest weft wrote is readable here.

Events append to `digests/<citekey>.proposals.jsonl`, which is what makes a discard visible to the agent that proposed it: `loom refs propose` refuses a discarded work-and-local-id and returns the reason in the same turn.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from loom.anchors import Anchor as Anchor  # re-exported: a result's anchor is the shared type
from loom.clock import stamp
from loom.digest.extract import ABBREV

# Contract §9.9. `proposed` is written, and not yet vouched for; `verified` is a person having compared the
# rendering to the source text and accepted it. Nothing else may sit in `<citekey>.tex`.
PROPOSED = "proposed"
VERIFIED = "verified"
DISCARDED = "discarded"


@dataclass
class Result:
    """One result of a cited work, with the two texts of contract §9.4."""

    id: str
    local: str
    taxon: str = "theorem"
    number: str = ""
    locator: str = ""
    statement: str = ""
    source_text: str = ""
    anchor: Anchor = field(default_factory=Anchor)
    level: int = 3
    cls: str = "anchored"
    state: str = PROPOSED
    origin: list[dict[str, str]] = field(default_factory=list)
    supersedes: str = ""
    env: str = ""  # the quilt's environment the node is written in; the taxon when empty

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        d["class"] = d.pop("cls")
        d["anchor"] = self.anchor.to_dict()
        return d

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> Result:
        return cls(
            id=str(d["id"]),
            local=str(d.get("local", "")),
            taxon=str(d.get("taxon", "theorem")),
            number=str(d.get("number", "")),
            locator=str(d.get("locator", "")),
            statement=str(d.get("statement", "")),
            source_text=str(d.get("source_text", "")),
            anchor=Anchor.from_dict(dict(d.get("anchor") or {})),
            level=int(d.get("level", 3) or 3),
            cls=str(d.get("class", d.get("cls", "anchored"))),
            state=str(d.get("state", PROPOSED)),
            origin=list(d.get("origin", [])),
            supersedes=str(d.get("supersedes", "")),
            env=str(d.get("env", "")),
        )


def results_path(root: Path, citekey: str) -> Path:
    return root / "digests" / f"{citekey}.results.json"


def proposed_path(root: Path, citekey: str) -> Path:
    return root / "digests" / f"{citekey}.proposed.tex"


def digest_path(root: Path, citekey: str) -> Path:
    return root / "digests" / f"{citekey}.tex"


def log_path(root: Path, citekey: str) -> Path:
    return root / "digests" / f"{citekey}.proposals.jsonl"


def load_results(root: Path, citekey: str) -> dict[str, Result]:
    """Every result recorded for a work, by id; an empty map when none has been."""
    path = results_path(root, citekey)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out: dict[str, Result] = {}
    for d in data.get("results", []):
        try:
            r = Result.from_json(d)
        except (KeyError, TypeError, ValueError):
            continue
        out[r.id] = r
    return out


def save_results(root: Path, citekey: str, results: dict[str, Result]) -> None:
    """Write the work's results back, in id order so a diff is readable."""
    path = results_path(root, citekey)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "record": 1,
        "citekey": citekey,
        "results": [results[k].to_json() for k in sorted(results)],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def append_event(root: Path, citekey: str, event: dict[str, Any]) -> None:
    """Append one line to the work's proposal log; the log is the only place a discard's reason lives."""
    path = log_path(root, citekey)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"when": stamp(), **event}, sort_keys=False) + "\n")


def read_events(root: Path, citekey: str) -> list[dict[str, Any]]:
    """Every event recorded for a work, oldest first; a malformed line is skipped rather than fatal."""
    path = log_path(root, citekey)
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def discarded_locals(root: Path, citekey: str) -> dict[str, str]:
    """Local ids this work has had discarded, and why, so a re-proposal can be refused with the reason (§5.5).

    Replayed rather than stored: a local id discarded and later proposed again under `--supersedes` is no longer discarded, and replaying is what keeps that true without a second record to maintain.
    """
    out: dict[str, str] = {}
    for e in read_events(root, citekey):
        local = str(e.get("local", ""))
        if not local:
            continue
        if e.get("event") == DISCARDED:
            out[local] = str(e.get("reason", "")) or "no reason given"
        elif e.get("event") in ("proposed", VERIFIED):
            out.pop(local, None)
    return out


# Contract §3.2's map, and one taxon only a reader proposes: a labelled display equation the paper names as a result.
# Graber and Pandharipande's main result is their equation (1); proposed as "Theorem 1", its locator named something
# the paper never says, and a citation of "(1)" could not match it.
PROPOSAL_ABBREV = {**ABBREV, "equation": "eq"}
TAXON_OF = {v: k for k, v in PROPOSAL_ABBREV.items()}
# `<abbrev>-<number>` as the paper numbers it -- dot-separated parts, each digits with at most one trailing letter or
# up to four capitals (4.1, 2.3.1, A, A.2, IV.3, 3.4a) -- or `<abbrev>-star-<n>` for the n-th unnumbered one.
LOCAL = re.compile(r"(?P<abbrev>[a-z]+)-(?P<number>star-\d+|(?:\d+[a-z]?|[A-Z]{1,4})(?:\.(?:\d+[a-z]?|[A-Z]{1,4}))*)")


def abbrev_for(taxon: str) -> str:
    """The id fragment a taxon contributes (contract §3.2); an environment outside the map contributes its own name."""
    t = taxon.strip().lower()
    return PROPOSAL_ABBREV.get(t, re.sub(r"[^a-z0-9]", "", t) or "res")


def quilt_env(result: Any, taxon: str) -> str:
    """The quilt's own environment for a taxon, chosen by display name as the extractor chooses one: numbered first, never a starred twin.

    A proposal written as `\\begin{corollary}` in a quilt with no corollary environment is not a node at all: verified, it was "recorded but in no digest loom can scan". A taxon the quilt lacks, and a display equation, go into the quilt's theorem; the locator still carries the paper's own name.
    """
    ranked = sorted(result.taxa.items(), key=lambda kv: (not kv[1].numbered, kv[1].env != kv[1].name.lower(), kv[0]))
    by_name: dict[str, str] = {}
    for env, t in ranked:
        by_name.setdefault(t.name.lower(), env)
    want = taxon.strip().lower()
    return by_name.get(want) or by_name.get("theorem") or "theorem"


def check_local(local: str, taxon: str | None) -> tuple[str, str]:
    """(taxon, number) for a proposal's local name, or ValueError naming the form to use.

    The taxon is read off the name when not given, so `--local cor-2.3.1` needs nothing else; a given taxon must agree with it. Brion numbers corollaries within a subsection, and an agent that invented `cor-2.3-quotient` made a result no citation by number could find.
    """
    m = LOCAL.fullmatch(local.strip())
    if not m:
        raise ValueError(
            f"--local {local!r} is not the paper's own number. Name a result <abbrev>-<number> as the paper numbers "
            "it -- thm-4.1; cor-2.3.1 for the first corollary under 2.3; thm-A; eq-1 for its display (1) -- or "
            "<abbrev>-star-<n> for the n-th unnumbered one (digest contract §3.2)."
        )
    ab = m.group("abbrev")
    t = (taxon or "").strip().lower() or TAXON_OF.get(ab, "")
    if not t:
        raise ValueError(f"{ab}- is none of {', '.join(sorted(TAXON_OF))}; pass --taxon to name the environment")
    if abbrev_for(t) != ab:
        raise ValueError(f"--local {local} names a {TAXON_OF.get(ab, ab)}, and --taxon says {t} ({abbrev_for(t)}-…)")
    number = m.group("number")
    return t, "" if number.startswith("star-") else number


def make_id(prefix: str, taxon: str, number: str, taken: set[str]) -> str:
    """A result's id: `<prefix>-<abbrev>-<number>`, or `<prefix>-<abbrev>-star-<n>` when the paper does not number it (contract §3.2)."""
    ab = abbrev_for(taxon)
    if number.strip():
        return f"{prefix}-{ab}-{number.strip()}"
    n = 1
    while f"{prefix}-{ab}-star-{n}" in taken:
        n += 1
    return f"{prefix}-{ab}-star-{n}"


def numbers_of(number: str) -> list[str]:
    """Every number a result carries: "3.2, 3.3" and "3.2-3.3" are two results the paper states together."""
    return [n for n in re.split(r"\s*(?:,|;|\band\b|&|(?<=\d)-(?=\d+\.\d))\s*", number.strip()) if n]


def node_tex(r: Result, citekey: str) -> str:
    """One result as a digest node, in the shape `loom digest extract` writes (contract §4.2).

    A result the paper states as two numbers -- "Theorem (3.2), (3.3)" -- gets the first as its id and the rest as id-shaped aliases, which contract §6.2 reads a number off. Recorded as one id, `...-thm-3.2-3.3`, it was citable by neither number: `\\cite[Theorem 3.2]` matched nothing.
    """
    nums = numbers_of(r.number)
    taxon = r.taxon.strip().lower() or "theorem"
    if taxon == "equation":
        # the paper's own name for a display is its number in parentheses; the node needs a theorem-like environment
        # to carry a title at all (contract §4.1), so the equation sits in the quilt's theorem
        locator = r.locator or (f"Equation {', '.join(f'({n})' for n in nums)}" if nums else "Equation")
        env = r.env or "theorem"
    else:
        locator = r.locator or (f"{r.taxon.title()} {', '.join(nums)}" if nums else "Statement")
        env = r.env or taxon
    span = f"{r.anchor.page}--{r.anchor.last}" if r.anchor.last > r.anchor.page else f"{r.anchor.page}"
    page = f", p.~{span}" if r.anchor.page else ""
    prefix = r.id[: -len(r.local)].rstrip("-") if r.local and r.id.endswith(r.local) else ""
    aliases = "".join(f"\\label{{{prefix}-{abbrev_for(r.taxon)}-{n}}}" for n in nums[1:]) if prefix else ""
    return (
        f"\\begin{{{env}}}[{{\\cite[{locator}{page}]{{{citekey}}}}}]\\label{{{r.id}}}{aliases}\n"
        f"{r.statement.strip()}\n"
        f"\\end{{{env}}}\n"
    )


def header(citekey: str, prefix: str, kind: str) -> str:
    """The provenance header a digest or a proposal file carries (contract §2)."""
    return (
        f"% !LOOM digest: {citekey}\n"
        f"% !LOOM prefix: {prefix}\n"
        f"% !LOOM method: pdf\n"
        f"% !LOOM proofs: none\n"
        f"% !LOOM created: {stamp()[:10]}\n"
        + (
            "% Proposed nodes. Nothing inputs this file: a proposal is not part of the paper until it is verified.\n"
            if kind == "proposed"
            else ""
        )
    )


def write_proposed_tex(root: Path, citekey: str, prefix: str, results: dict[str, Result]) -> Path | None:
    """Rewrite the work's shadow file from every result still in the `proposed` state; removes it when none is left."""
    path = proposed_path(root, citekey)
    pending = [results[k] for k in sorted(results) if results[k].state == PROPOSED]
    if not pending:
        path.unlink(missing_ok=True)
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(node_tex(r, citekey) for r in pending)
    path.write_text(header(citekey, prefix, "proposed") + "\n" + body, encoding="utf-8")
    return path


# What a result's class says the file's `method:` must be (contract §2.5).
_METHOD = {"mechanical": "extract", "anchored": "pdf", "declared": "manual"}


def _reconcile_method(text: str, want: str) -> str:
    """Set the digest's `method:` to `mixed` when a node arrives that the declared method does not describe.

    A digest extracted from LaTeX that gains a node read off a PDF is no longer `method: extract`, and a header that
    still says so is a provenance claim nobody checked. `mixed` says the file is not uniform and sends a reader to
    `results.json`, where contract §9.6 records the class of each result separately.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines[:20]):
        if line.startswith("% !LOOM method:"):
            have = line.split(":", 1)[1].strip()
            if have and have != want and have != "mixed":
                lines[i] = "% !LOOM method: mixed"
            return "\n".join(lines)
    return text


def append_to_digest(root: Path, citekey: str, prefix: str, r: Result) -> Path:
    """Put a verified node into `digests/<citekey>.tex`, creating the file with a header when it is the first."""
    path = digest_path(root, citekey)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        path.write_text(header(citekey, prefix, "digest") + "\n" + node_tex(r, citekey), encoding="utf-8")
        return path
    text = _reconcile_method(path.read_text(encoding="utf-8").rstrip("\n"), _METHOD.get(r.cls, "pdf"))
    path.write_text(text + "\n\n" + node_tex(r, citekey), encoding="utf-8")
    return path


def rewrite_in_digest(root: Path, citekey: str, r: Result) -> bool:
    """Replace a verified node's body in `digests/<citekey>.tex` with its record's statement; False when the node is not there.

    A re-verify with the author's own text once changed the record and not the document, so `loom source`, every bundle and the viewer kept the text the author had corrected -- and an agent asked what the author changed reported the document faithfully and was wrong. `\\uses` lines at the head of the body are the dependency record and are kept.
    """
    path = digest_path(root, citekey)
    if not path.is_file():
        return False
    lines = path.read_text(encoding="utf-8").split("\n")
    label = f"\\label{{{r.id}}}"
    start = next((i for i, ln in enumerate(lines) if label in ln and ln.lstrip().startswith("\\begin{")), None)
    if start is None:
        return False
    m = re.match(r"\s*\\begin\{([^}]*)\}", lines[start])
    env = m.group(1) if m else ""
    end = next((j for j in range(start + 1, len(lines)) if lines[j].strip() == f"\\end{{{env}}}"), None)
    if end is None:
        return False
    keep = [ln for ln in lines[start + 1 : end] if ln.strip().startswith("\\uses{")]
    lines[start + 1 : end] = keep + r.statement.strip().split("\n")
    path.write_text("\n".join(lines), encoding="utf-8")
    return True


#: The page a locator names, as `digest extract` writes it: `Proposition 2.1, p.~7`.
_LOCATOR_PAGE = re.compile(r"\bpp?\.\s*~?\s*(\d+)")


def _extracted_anchor(root: Path, citekey: str, entry: Any, locator: str, statement: str, rel: str, sha: str) -> Anchor:
    """The anchor a mechanically extracted result carries.

    A page anchor against the filed copy where extraction located the result on one, **with the statement's own span on that page** rather than the page alone: a reader following a citation wants the result, not the sheet it is printed on. The source file stays on the anchor as its provenance either way, and a work with no readable copy keeps the tex anchor it has always had (DR-198).
    """
    from loom.refs.fetch import work_dir
    from loom.refs.pages import read_map, read_page
    from loom.refs.search import statement_span

    found = _LOCATOR_PAGE.search(locator or "")
    if not found or entry is None:
        return Anchor(kind="tex", sha256=sha, path=rel)
    try:
        home = work_dir(root, entry)
    except Exception:
        # a work with no identity to file under has no store directory, and so no page anybody could open
        return Anchor(kind="tex", sha256=sha, path=rel)
    m = read_map(home)
    if m is None or not (home / "paper.pdf").is_file():
        return Anchor(kind="tex", sha256=sha, path=rel)
    page = int(found.group(1))
    anchor = Anchor(kind="pdf", sha256=m.sha256, page=page, path=rel)
    inner = re.search(r"\\cite\s*\[([^\]]*)\]", locator or "")
    label = (inner.group(1) if inner else locator or "").split(",")[0].strip()
    text = read_page(home, page) or ""
    span = statement_span(text, label, statement) if text and label else None
    if span is not None:
        anchor.basis, anchor.start, anchor.end = "text", span[0], span[1]
    return anchor


def record_extracted(result: Any, citekey: str) -> int:
    """Write `results.json` entries for a digest that `loom digest extract` produced; returns how many.

    Mechanical extraction and an agent's reading must end in the same place, or half the digest is invisible to every surface that reads results. These carry `class: mechanical` and `state: verified` — verified by construction, since the statement *is* the source (contract §9.4), with the file and its hash as the anchor (§9.3). An entry already recorded is left alone, so this never overwrites a result a person edited.
    """
    from loom.refs.pages import sha256_of

    root = result.quilt.root
    rel = None
    for f, ck in result.assembly.digest_files.items():
        if ck == citekey:
            rel = f
            break
    if rel is None:
        return 0
    path = root / rel
    sha = sha256_of(path) if path.is_file() else ""
    results = load_results(root, citekey)
    added = 0
    for key, n in result.nodes.items():
        if n.file != rel or n.kind != "environment" or not n.id:
            continue
        if n.id in results:
            continue
        text = _own_text(result, n)
        results[n.id] = Result(
            id=n.id,
            local=n.id.split("-", 1)[-1],
            taxon=(n.taxon or n.env or "theorem").lower(),
            number=(n.directives.get("number") or ""),
            locator=n.title or "",
            statement=text.strip(),
            source_text=text.strip(),
            anchor=_extracted_anchor(root, citekey, result.bib.get(citekey), n.title or "", text.strip(), rel, sha),
            level=3,
            cls="mechanical",
            state=VERIFIED,
            origin=[{"act": "extracted", "by": "loom digest extract", "when": stamp()}],
        )
        added += 1
        _ = key
    if added:
        save_results(root, citekey, results)
    return added


def _own_text(result: Any, node: Any) -> str:
    """A node's own text, via the records store; imported here so this module costs nothing at load time."""
    from loom.records.store import Records

    text, _pieces = Records.own_pieces(result, node)
    return str(text)


def find_result(result: Any, target: str) -> tuple[str, str, dict[str, Result]]:
    """(citekey, id, that work's results) for a result id, wherever it is recorded.

    An id carries its work's prefix but not its citekey, and the two differ, so the id is looked up rather than parsed.
    """
    root = result.quilt.root
    for path in sorted((root / "digests").glob("*.results.json")):
        citekey = path.name[: -len(".results.json")]
        results = load_results(root, citekey)
        if target in results:
            return citekey, target, results
    raise LookupError(f"no result {target}; loom refs coverage names the works that have any")


def verify_result(
    result: Any, target: str, statement: str | None, author: str, *, local: str | None = None, taxon: str | None = None
) -> list[str]:
    """Record that a transcription is faithful: promote a proposal into the digest, or re-verify one already there.

    Parameters
    ----------
    result : ScanResult
        The scanned quilt.
    target : str
        A result id, proposed or already verified.
    statement : str or None
        The author's own rendering, replacing the proposed one before verifying. Never touches `source_text`, so the anchor survives and the node stays re-checkable.
    author : str
        Who is making the claim; recorded beside whoever proposed it.
    local : str, optional
        The paper's own name for the result, correcting the proposal's (`cor-3.2.1` for what was proposed as `thm-3.2`). Only while it is still proposed: a verified id may already be cited.
    taxon : str, optional
        The environment, when `local` does not imply it.

    Returns
    -------
    list of str
        Lines describing what happened, the first of which is the headline.

    See Also
    --------
    discard_result : the other half of the decision.
    """
    from loom.cli.review import write_acceptance
    from loom.scan.quilt import load_quilt
    from loom.scan.scan import scan

    root = result.quilt.root
    citekey, rid, results = find_result(result, target)
    r = results[rid]
    prefix = result.assembly.prefix_of(citekey)
    renamed = ""
    if local or taxon:
        if r.state != PROPOSED:
            raise LookupError(f"{rid} is verified and may already be cited; rename it in digests/{citekey}.tex by hand")
        try:
            new_taxon, number = check_local(local or r.local, taxon)
        except ValueError as exc:
            raise LookupError(str(exc)) from exc
        new_local = (local or r.local).strip()
        new_id = f"{prefix}-{new_local}"
        if new_id != rid and new_id in results:
            raise LookupError(f"{new_id} is already recorded ({results[new_id].state})")
        if new_id != rid:
            # the author's correction of the name, recorded like a correction of the text: the old id is what the
            # proposer and any link knew it by
            r.origin.append({"act": "renamed", "by": author, "when": stamp(), "was": rid})
            _rename_in_links(root, rid, new_id)
            results.pop(rid)
            renamed, rid = rid, new_id
            results[rid] = r
        r.id, r.local, r.taxon, r.locator = rid, new_local, new_taxon, ""
        r.env = quilt_env(result, new_taxon)
        r.number = number
    edited = False
    if statement is not None and statement.strip() and statement.strip() != r.statement.strip():
        # the proposed text is kept beside the author's: "edited by isaac" said an edit happened and not what it was,
        # and in the second study run the edit was a dropped mathematical clause -- the one thing worth learning from
        r.origin.append({"act": "edited", "by": author, "when": stamp(), "was": r.statement.strip()})
        r.statement = statement.strip()
        edited = True
    was_proposed = r.state == PROPOSED
    if was_proposed:
        append_to_digest(root, citekey, prefix, r)
    elif (edited or r.cls != "mechanical") and not rewrite_in_digest(root, citekey, r):
        # re-verifying says the record is faithful, so the document is brought to the record; a mechanical node's
        # text is the digest's own, and only an edit replaces it
        raise LookupError(
            f"{rid} is not in digests/{citekey}.tex in the shape loom writes; put your text there by hand"
        )
    r.state = VERIFIED
    r.origin.append({"act": "verified", "by": author, "when": stamp()})
    save_results(root, citekey, results)
    write_proposed_tex(root, citekey, prefix, results)
    if renamed:
        append_event(root, citekey, {"event": "renamed", "id": rid, "was": renamed, "by": author})
    append_event(root, citekey, {"event": VERIFIED, "id": rid, "local": r.local, "by": author, "edited": edited})
    out = [
        f"verified {rid} as a faithful transcription of {citekey}"
        + (" (with your own rendering)" if edited else "")
        + (f" (renamed from {renamed})" if renamed else "")
    ]
    if was_proposed:
        out.append(f"written into digests/{citekey}.tex")
    # The ledger is what `loom status` reads, and what makes a later `transcription-changed` detectable at all.
    # Written after the node is in the digest, because the row names the text it saw there.
    rescan = scan(load_quilt(root))
    if rid not in rescan.nodes:
        raise LookupError(f"{rid} is recorded but is in no digest loom can scan; check digests/{citekey}.tex")
    _rows, written, present = write_acceptance(rescan, [rid], author)
    out.append(f"snapshots: {written} written, {present} already present")
    return out


def _rename_in_links(root: Path, old: str, new: str) -> None:
    """Point every asserted link that names `old` at `new`."""
    from loom.refs.links import read_links, write_links

    links = read_links(root)
    hit = False
    for link in links:
        if link.frm == old:
            link.frm, hit = new, True
        if link.to == old:
            link.to, hit = new, True
    if hit:
        write_links(root, links)


def edit_diff(r: Result) -> list[str]:
    """The author's correction of a result as diff lines, from what was proposed to what was verified; [] when unedited.

    From the first edit's `was`, however many times the author re-verified after it: what a later proposer learns from is the distance between its own text and the verified one.
    """
    import difflib

    edits = [o for o in r.origin if o.get("act") == "edited" and o.get("was")]
    if not edits:
        return []
    before = str(edits[0]["was"]).splitlines()
    return [
        line
        for line in difflib.unified_diff(before, r.statement.splitlines(), lineterm="", n=0)
        if not line.startswith(("---", "+++", "@@"))
    ]


def home_of(root: Path, r: Result) -> Path | None:
    """The `<kind>/<id>/` directory in the store holding the artifact a PDF anchor names, found by its hash rather than the citekey."""
    from loom.refs.pages import storage_root

    if not r.anchor.sha256:
        return None
    for d in storage_root(root).glob("*/*"):
        sections = d / "sections.json"
        if sections.is_file() and r.anchor.sha256 in sections.read_text(encoding="utf-8"):
            return d
    return None


def locate_quote(text: str, quote: str) -> tuple[int, int] | None:
    """The character range of `quote` in `text`, whitespace-insensitive and otherwise exact; None when absent."""
    words = quote.split()
    if not words:
        return None
    m = re.search(r"\s+".join(map(re.escape, words)), text)
    return (m.start(), m.end()) if m else None


def discard_result(result: Any, target: str, reason: str, author: str) -> str:
    """Discard a proposed result with a reason, which `loom refs propose` returns to whatever proposes it again."""
    root = result.quilt.root
    citekey, rid, results = find_result(result, target)
    r = results[rid]
    if r.state == VERIFIED:
        raise LookupError(
            f"{rid} is verified and in the digest; edit or remove it there, or loom refs drop --work {citekey}"
        )
    r.state = DISCARDED
    r.origin.append({"act": "discarded", "by": author, "when": stamp()})
    save_results(root, citekey, results)
    write_proposed_tex(root, citekey, result.assembly.prefix_of(citekey), results)
    append_event(root, citekey, {"event": DISCARDED, "id": rid, "local": r.local, "by": author, "reason": reason})
    return f"discarded {rid}: {reason}"


def page_context(root: Path, r: Result, *, lines: int = 12) -> tuple[str, bool]:
    """The page text around a result's anchor, and whether the quoted span was found in it.

    What a person compares a rendering against. `source_text` alone is not it: an agent quotes only as much as the anchor check needs, and in the first study run a ten-line rendering stood beside the one clause "Let X be a nonsingular filtrable T-variety." Both texts were on screen and nobody could have judged the one against the other. The page around the quote is the thing the rendering claims to transcribe.
    """
    from loom.refs.pages import read_pages
    from loom.refs.search import normalize

    if r.anchor.kind == "tex" and r.anchor.path and r.cls != "mechanical":
        try:
            data = (root / r.anchor.path).read_bytes()
        except OSError:
            return r.source_text, False
        # surrogateescape, as propose decodes: the byte offsets map to the same characters in a Latin-1 source
        text = data.decode("utf-8", "surrogateescape")
        a, b = r.anchor.bytes or (0, 0)
        first, end = len(data[:a].decode("utf-8", "surrogateescape")), len(data[:b].decode("utf-8", "surrogateescape"))
        if not r.anchor.bytes or text[first:end].split() != r.source_text.split():
            return r.source_text, False
        lo = text.rfind("\n", 0, max(0, text.rfind("\n", 0, first))) + 1
        hi = text.find("\n", text.find("\n", end) + 1)
        return text[lo : hi if hi > 0 else len(text)].rstrip("\n"), True
    if r.anchor.kind != "pdf" or not r.anchor.page:
        return r.source_text, False
    # found by the artifact the anchor names rather than by the citekey: the directory is named by identifier
    home = home_of(root, r)
    page = read_pages(home, r.anchor.page, max(r.anchor.page, r.anchor.last)) if home else None
    if page is None:
        return r.source_text, False
    rows = page.splitlines()
    head = normalize(r.source_text)[:40]
    at = next((i for i, row in enumerate(rows) if head and head[:24] in normalize(row)), None)
    if at is None:
        return page.rstrip("\n"), False
    # a statement over a page break is shown to the end of its last page: the continuation is what has to be read
    lo, hi = max(0, at - 2), len(rows) if r.anchor.last > r.anchor.page else min(len(rows), at + lines)
    return "\n".join(rows[lo:hi]).rstrip("\n"), True
