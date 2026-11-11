# WQ-56 · A cold build's snippets: a preamble format, and the cited papers' statements TeX refuses

**Repo:** loom

## Trigger

`scripts/bench` on a copy of the author's quilt shows a cold build over three minutes after a change that makes cold builds common (a loom release that changes the snippet cache key, or a workflow that deletes `.loom/build/`), or the author reports a cited paper's statement shown as its source with TeX's complaint.

## Why deferred

Text no compile makes, a digest's statements, a landmark, a node no document reaches, a comparison, is made by TeX as snippets (plan 0.29.5): one TeX4ht run per preamble with every text between marks, as many runs at once as half the cores, at most four, each text cached by its content. The 0.29.4 gate measured a thousand of relloc's statements at 22 s cold with four runs at once, and a cold build is rare: the cache survives every rebuild and every loom upgrade that leaves the code making a text alone, and a text TeX refused is remembered, so only deleting `.loom/build/` pays again.

## What is left

Measured on 2026-10-03, before snippets, a cold build of the relloc copy compiled 1,020 blocks the translator could not draw, at about 2.2 s each, and 739 of them failed. Snippets replace those compiles with runs of many texts, but both causes carry over:

1. **Each run loads the whole preamble.** The master's preamble (TikZ and the rest) is most of a short run. Running against a format dumped once per distinct preamble (`mylatexformat`'s `\endofdump`, with the digest's macro block and added packages after the dump point) would make a run a fraction of that; a preamble that cannot be dumped keeps the present route.
2. **Most refusals are a cited paper's statement that cannot be read under the quilt's preamble.** By message, before snippets: undefined control sequences (150, the commonest being macros the paper defined in a part of its preamble the macro block does not carry), a macro the digest's block defines that the quilt's preamble already defines (`\CMcal`, `\corollary`, `\Sun`: about 150), `\rm` undefined under a modern class (44), and packages not installed (`widebar.sty`, `notn.sty`). Each is a digest-layer fault, not a rendering one: the statement shows its source and `loom:snippet-failed` names TeX's complaint, as it must.

## Rough design

- A format per distinct preamble a run is made under, under `.loom/build/cache/fmt/`, keyed by its text; `snippets.render_snippets` runs against it when it exists and dumps it once when it does not.
- For the failures, the extraction (`loom digest extract`) records which of the paper's macros a block uses, so the macro block carries them, and a clash with the quilt's preamble is resolved by `\providecommand` rather than `\newcommand`; `\rm` and its kin are provided in a digest's preamble as LaTeX 2.09 compatibility.
