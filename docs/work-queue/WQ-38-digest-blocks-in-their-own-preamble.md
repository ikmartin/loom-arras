# WQ-38 · A digest block rendered against the paper's own preamble

**Repo:** loom

## Trigger

A digest block the author needs to read shows a raw-TeX error box in arras. It does today on the study quilt: Chang–Kiem–Li's overview (`\CMcal already defined`), and most digest diagrams.

## Why deferred

It needs a design change, not a fix. The fallback renderer composes a digest block's preamble from the author's packages plus the digest's `requires:`, and the paper's own macros used inside diagrams are neither expanded nor in the digest's macro block. So packages collide (`calrsfs` from the author against the paper's `\CMcal`) and 112 diagrams in plan 0.12's first iteration failed on undefined control sequences. Reordering the attempts was tried and made it worse (215 → 317 failures) and was reverted.

## Rough design

For a digest block, compile against the cited paper's own preamble, read from its fetched source, when the source is on disk. Fall back to today's composition when it is not. Cache by the paper's preamble hash.

## Blast radius

`render/fallback.py`, `render/fragments.py` (digest context), `digest/extract.py` if the preamble is recorded at extraction.
