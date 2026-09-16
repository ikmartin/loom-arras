# WQ-08 · `\nest` under `\part` and class-specific sectioning

**Repo:** loom

## Trigger

A fixture uses `\part`, memoir or KOMA-Script — that is, a real paper arrives that the current chain cannot shift.

## Why deferred

The implemented chain covers `\section` through `\subparagraph`, which is every level the three real fixtures use. Extending it speculatively means writing shift rules for classes no test exercises.

## Rough design

Extend the shift chain in `loom.sty` to `\part`, and to the sectioning commands memoir and KOMA-Script add or rename. The rule the book already states holds: implement the chain, extend when a fixture needs it.

## Blast radius

`loom/src/loom/assets/loom.sty`, Chapter 4 §4.5, one edge-quilt fixture per class added.

## Related

Chapter 4 §4.5; [[WQ-07]].
