# WQ-07 · `atomize --relative`

**Repo:** loom

## Trigger

A quilt wants its section files to read as standalone sections — an author moving section files between papers, or a library quilt assembled from pieces of several.

## Why deferred

`atomize --sections` already produces a working spine, and nothing has yet needed the moved files to stand alone. The flag would be untested ceremony.

## Rough design

Additionally rewrite the moved section files' sectioning commands to top level and emit `\nest` at the inclusion site, so each section file reads as a standalone section rather than as a fragment that only makes sense at its depth. Identity-preserving: `\nest` shifts levels back at the site, so the compiled document is unchanged, which the identity test must confirm.

## Blast radius

`loom/src/loom/reshape/atomize.py`, `loom.sty`'s `\nest`, Chapter 6 §6.4, the CLI reference (generated), one identity test.

## Related

Chapter 6 §6.4; [[WQ-08]], which is the other half of `\nest`'s coverage.
