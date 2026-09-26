# WQ-51 · A view's macros stay its own

**Repo:** arras

## Trigger

A quilt other than the synthetic fixture has two macro sets in its manifest that define one macro name differently (`macros.sets` and `macros.default`; a two-minute script over `build/manifest.json` finds them). Checked 2026-09-26: none of acgs, hostile, kpsv, man12, mmp or showcase has one.

## Why deferred

The leak shows only when two sets disagree on a name, and no real quilt's sets do yet. Plan 0.16 found the mechanism while fixing the landmark formula bug: `typeset()` in `arras/src/lib/math/mathjax.ts` gives a fragment its macros by placing `\renewcommand` definitions before its first formula, and MathJax keeps those definitions in one page-wide table. Every view typeset afterwards, in either pane, sees the last set defined, so a document opened after another can render a shared macro name with the other's meaning. The review comparison already avoids this: it passes macros through `isolatedMacros` (`arras/src/lib/math/scoped.ts`) and places nothing in a formula.

## Rough design

Give every fragment that names a macro set the scoped path the comparison uses: its macros as configuration for that typesetting and nothing placed in a formula, so `macroPrefix` goes. Measure first what a scoped typesetting costs per set against the shared one, on the largest demo (kpsv, sixteen sets), since a landmark, a digest document and a digest node's preview each name a set.

**The test is already in the fixture.** `\Hom` is defined one way by the `Kre99` set and another by the three `canon:widgets-v*` sets. Open `/canon/widgets-v1`, then the Kre99 digest (or the reverse) in the same page, and assert that each renders `\Hom` with its own definition; today the second shows the first's.

## Blast radius

`arras/src/lib/math/mathjax.ts` (`typeset`, `macroPrefix`), `arras/src/lib/math/scoped.ts`, the callers in `fragments/Fragment.svelte` and `NodePreview.svelte`; an e2e test on the fixture's `\Hom`.
