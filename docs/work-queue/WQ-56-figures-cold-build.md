# WQ-56 · A cold build's figures: a preamble format, and the cited papers' blocks that fail

**Repo:** loom

## Trigger

`scripts/bench` on a copy of the author's quilt shows a cold build over three minutes after a change that makes cold builds common (a loom release that changes the SVG cache key, or a workflow that deletes `build/`), or the author reports a cited paper's figure shown as source with an error.

## Why deferred

Plan 0.18.2 took the author's cold build from 688 s to 314 s by compiling figures on one shared pool, each once, with the review previews sharing the fragments' preamble, and by loading `xy` for `\xymatrix`. What remains is per compile, and a cold build is rare: the SVG cache is keyed by content and survives every rebuild and every loom upgrade, and a failure is remembered, so only deleting `build/` pays again.

## What is left

Measured on 2026-10-03, a cold build of the relloc copy ran 1,020 compiles at about 2.2 s each across eight threads, and 739 of them failed:

1. **Each compile loads the whole preamble.** The master's preamble (TikZ and the rest) is most of each run. Compiling against a format dumped once per distinct preamble (`mylatexformat`'s `\endofdump`, with the digest's macro block and added packages after the dump point) would make a compile a fraction of that; a preamble that cannot be dumped falls back to the present route.
2. **Most failures are a cited paper's block that cannot compile in a standalone box.** By message: undefined control sequences (150, the commonest being macros the paper defined in a part of its preamble the macro block does not carry), a macro the digest's block defines that the quilt's preamble already defines (`\CMcal`, `\corollary`, `\Sun`: about 150), `\rm` undefined under a modern class (44), and packages not installed (`widebar.sty`, `notn.sty`). Each is a digest-layer fault, not a rendering one: the block shows its source with the error, as book 9.4.2 says it must.

## Rough design

- A format per distinct prepared master preamble, under `build/cache/fmt/`, keyed by its text; `compile_svg` takes it when it exists and builds it once, under the per-key lock, when it does not.
- For the failures, the extraction (`loom digest extract`) records which of the paper's macros a block uses, so the macro block carries them, and a clash with the quilt's preamble is resolved by `\providecommand` rather than `\newcommand`; `\rm` and its kin are provided in the fallback preamble as LaTeX 2.09 compatibility.
