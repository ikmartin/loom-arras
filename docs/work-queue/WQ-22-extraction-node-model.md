# WQ-22 · Digest extraction shares the node model

**Repo:** loom

## Trigger

Extraction and `atomize` disagree about what counts as a node — a nested statement, a proof by enclosure, a label rule one honours and the other does not.

## Why deferred

The duplication is real but currently harmless, and the refactor it wants is not small. Nothing has yet diverged.

## Rough design

Two separable pieces that share a cause.

**Lift the quilt requirement off the node model.** `plan_atomize` consumes `ScanResult` → `Assembly` → `NodeRec`: keys, allocated ids, `proofs`, `attach_via`, ordinals. `extract_digest` consumes raw scanner primitives — `Env`, `SectionUnit`, `Expansion` — because a reference paper *is not a quilt*: no `config.toml`, no ids, no `\usepackage{loom}`, so `scan()` cannot be pointed at it. Both already share the layer beneath (`envtree`, `find_sections`, `expand_master`, `labels_in`) and extraction already imports `closure_of` from the importer, so closure resolution is not duplicated.

What is duplicated is the node-selection layer: ordering results by position, attaching proofs to statements, computing section containment. Extraction reimplements thinner versions of all three — its proof attachment is `att.statement or att.fallback.statement` against the node model's richer adjacency, reference and enclosure rules (DR-41). That is what will quietly diverge as the scanner grows.

A `scan_paper(dir, master)` returning an `Assembly` without requiring a `config.toml` fixes it. The importer already fakes this by mirroring the quilt into a temp directory and scanning that, which proves the shape works; doing it properly replaces extraction's parallel pass with `NodeRec` selection, inherits every attachment rule for free, and makes "which results become nodes" a filter over a list.

**It is the minority of extraction, though.** Genuinely digest-specific, with no `atomize` analogue: numbering from the `.aux` plus the amsthm counter emulation, macro expansion with a self-contained residue block for a foreign preamble, label namespacing (every label prefixed, every `\ref` rewritten to a digest id or a literal number), and single-file output rather than node-files-plus-spine. Call it 60% irreducible. The refactor is worth doing for correctness, not for size.

## Blast radius

`loom/src/loom/scan/scan.py` (a non-quilt entry point), `loom/src/loom/digest/extract.py`, `loom/src/loom/reshape/importer.py` (its staging trick becomes redundant), Chapter 8.

## Related

Plan 0.5 (which established the `refs/` layout). The second half of this item — caching the `.aux` so that digesting a corpus is not one LaTeX run per work — went to **weft** with the crawl (DR-144, `docs/plans/weft-and-loom.md` §4): the cost only bites at corpus scale, and weft's copy of `digest/extract.py` is where it will be paid. What is left here is loom's, and is about correctness rather than speed.
