# WQ-66 · A document that needs shell escape or its own build rules

**Repo:** loom

## Trigger

A document the author wants loom to compile needs `-shell-escape`, or a build rule only a `latexmkrc` can add.

## Why deferred

From phase 0.29.1 of plan 0.29, loom's compiles read no rc file, and no document needs one. On 2026-11-09 no quilt, note or demo carried a `latexmkrc`, and none used `\write18` or the common shell-escape packages (`minted`, `svg`, `pythontex`, `gnuplottex`, `shellesc`, `auto-pst-pdf`).

## Rough design

An approval given per machine, as `direnv allow` works: it names the quilt and the digest of what it allows, is kept outside the quilt, and lapses when that file changes. It cannot be a key in `config.toml`, which the quilt carries (the invariant "Loom never runs a command the quilt carries"). It has to reach the TeX4ht run as well as the PDF, or the two disagree.
