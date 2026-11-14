# Spike: does relloc's save-to-seen reach 3-4 s?

Spike lead: speed. Throwaway prototype on a shared clone of the repository at 71621877 (`spike-speed/repo`, worktrees `mod` and `stage`), measured on APFS copies of the audit's own relloc copy (`speed/relloc`), with the audit's harness (`serveprobe.py`, `probe.py`, a variant of `viewer.cjs`). Everything lives in `/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/spike-speed/` (`tools/`, `logs/`). The whole change is `docs/reports/v0.1-study/spikes/speed.patch` (six commits squashed, 351 lines of diff). Nothing here is meant to merge.

## How this was measured, and what to distrust

- **The machine was far busier than during the audit.** Other sessions ran TeX throughout; the one-minute load average was 3.4-13.8 during the baseline viewer run and 16-30 during the final one, and reached 50 while the staleness runs went. Every absolute second below is inflated by that, unevenly. The comparisons that are trustworthy are the ones made close together in one process (the per-change build timings, `logs/builds.jsonl`) and the counts (blocks rendered, TeX runs, git forks), which load does not change.
- **Save to seen** is `tools/seen.cjs`: headless Chromium on `/master/drafting/draft5`, an atomic write of the proof of `rl-000G` (the phrase "has fibered products, for which"), time until the new words are in the DOM and the old ones gone, then wait until no compile, TeX4ht pass or rebuild is running and the server has been quiet 5 s. Load is recorded beside each edit.
- **Every edit writes a word never written before** (seven random letters in place of "fibered"). The audit alternated "fibred"/"fibered"; after the first two trials both texts' snippet and comparison preview are in the cache and no TeX runs on the save path. I measured that too (median 7.8 s, below), which is how I noticed. Real writing produces new text, so the never-seen-word numbers are the honest baseline.
- **Code fingerprint pinned.** `render/keys.code_hash` and the snippet fingerprint cover `render/`, `scan/` and `tex/`, so any edit there invalidates every cached fragment, snippet and preview (on relloc: minutes of TeX). The harness pins both to the unmodified code's values so the steady state is measured, not that one-off. The cost of the one-off is real and is reported under FAST-8.
- **Per-change attribution** comes from `tools/builds.py`: in one process, a warm-up build, then two never-seen-word edits each followed by the build `loom serve` would run for that save, with the flags the spike's server would pass. The first publication in the viewer is that build plus 0.3-0.5 s (watcher notice, manifest fetch).
- **Mishap, recovered.** Stopping an early run mid-`latexmk` left `draft5.aux` empty, and the next server start re-rendered all 2,384 blocks and remade every digest by TeX (PERF-3 live). I restored `.loom/build/drafting/draft5` from a pristine copy and reran; the runs reported here are after that.

## The changes, in the audit's order

| # | change (commit) | before → after | load (1-min) | lines (+/-) | staleness | tests broken |
|---|---|---|---|---|---|---|
| — | **all of 1, 2, 3, 5, 6, viewer save to seen, median of 5** | **15.75 s → 11.83 s** | 4.3-13.8 → 16-30 | 103 / 25 | as below | as 6 |
| 1 | re-anchoring once per build: the build's marks passed to the section-draft context instead of a fresh `Records` and a second `gone_annotations`; `aligned()` memoised on its exact inputs (d1d96cc4) | save build 10.95 → 8.55 s | 3.7-4.7 | +29 / -6 | none found | 0 |
| 2 | previews (Review's comparison, versions, suggested edits) from the cache only on a save's publication; TeX on the next (99356fa4) | 8.55 → 6.57 s | 3.7-3.8 | +28 / -8 | intended: previews are source for one publication; a hole if `latexmk` makes no PDF | 0 |
| 3 | `git config user.name` once per process per state of the git config files (e0185403) | author: 0; no loom name: 38.7-49.2 → 9.4-10.5 s, 609 → 0 forks | 5-25 → 14-15 | +35 / 0 | a name from an `include.path` file is not noticed | 0 |
| 4 | cache keys without page numbers: `aux_bytes` drops pages; a snippet's aux digest drops `\newlabel` pages and contents lines unless the text uses a `\pageref`-family command (d8d5e4c8) | word edit: 0; page shift 201.9 s, 2,384 blocks, 51 TeX runs → 41.8 s, 1 block, 1 run | 34 → 26 | +37 / -4 | none found in the steps run; risk: a page printed by a command outside the list or a preamble macro | 0 |
| 5 | a save's publication runs no TeX; a follow-up rebuild starts at once for the edited block and previews (4bf5f540) | 9.4-10.5 → 6.9-8.4 s; typeset block median 15.4 → 23.7 s | 14-15 → 11-12 | +7 / -10 | intended: the edited block is source until the follow-up, later than base shows it typeset | 0 |
| 6 | viewer writes answered once on disk, rebuilt in a thread (2172f533) | answered 6.3-6.7 → 0.03 s; in manifest 6.3-6.7 → 3.1 s | 5-6 → 7-8 | +4 / -1 | the viewer refreshes before the write is published | 16-17 in `test_write_api.py` |

"Save build" is the in-process build a save triggers (`tools/builds.py`, two never-seen-word edits each; the viewer sees it 0.3-0.5 s after it ends). Medians of five through the viewer were run only for the baseline and for the combination, because one run took 8-15 minutes on the loaded machine; see the method notes above.

## Findings

### FAST-1. The claim of 3-4 s is not reached; the best first publication measured is about 6.5 s

| measurement | before | after | load (1-min) |
|---|---|---|---|
| save to seen, viewer, never-seen word, median of 5 | 15.75 s (12.0, 12.6, 15.8, 18.5, 20.9) | 11.83 s (8.2, 9.0, 11.8, 12.5, 13.0), changes 1, 2, 3, 5, 6 | before 4.3-13.8; after 16-30 |
| same, the audit's alternating words (TeX from cache) | 7.82 s (6.8, 7.5, 7.8, 8.8, 19.2) | not rerun | 3.4-9.7 |
| save build in process, same load window | 10.95 s (11.19, 10.71) | 6.57 s (6.59, 6.55) with changes 1-2; 6.9-8.4 s with 1, 2, 3, 5 at load 11 | 3.7-4.7; 11-12 |
| HTTP annotation answered / in manifest, 3 writes | 6.25-6.66 s / 6.29-6.70 s | 0.03 s / 3.06-3.19 s | 5.3-6.1; 6.7-8.1 |
| `loom status`, no loom author name, alternating base and spike | 19.7, 20.0, 26.3 s | 13.5, 14.7, 16.7 s | 26-38 |

The viewer run after the changes went at two to three times the baseline's load and still came in 4 s faster. The cleanest before/after is the in-process save build at load 3.7-4.7, measured minutes apart: 10.95 s to 6.57 s with changes 1 and 2, the edited block still made by TeX. Change 5 takes off the remaining TeX run (about 2 s at load 4, by the audit's subprocess log and my E/F comparison). At the audit's load that puts the first publication near 4.5-5 s of build plus 0.5 s to the DOM: **roughly 5-6.5 s, not 3-4**. Under today's load it was 8-13 s.

What the remaining first publication is made of, from `tools/parts2.py` on the spike code with no TeX (17.3 s at load 31; shares hold, seconds scale down by about three at load 4): adoption comparisons 3.1 s (18 %), previews read from the cache and shaped 2.6 s (15 %), scan 2.5 s (15 %), `Records.apply` 2.1 s (12 %), section-draft context 1.8 s (10 %), publish 1.5 s (9 %), `build_manifest` 1.0 s (6 %), rendering the 63 blocks of draft5 1-2 s, everything else under 0.4 s each. `gone_annotations` fell from about 2.5 s to 0.09 s. In the viewer runs the stages were: scanning 1.6-5.4 s, rendering 1.0-3.3 s, recording 3.2-7.4 s, publishing 0.4-1.2 s (base: 1.9-4.0, 3.1-5.3, 5.7-10.4, 0.3-0.6).

### FAST-2. Change 1 (re-anchoring once, alignments memoised) is safe and worth 2.4 s per build

In-process at load 3.7-4.7: 10.95 s to 8.55 s (8.45, 8.64). `gone_annotations` now runs once per build and costs 0.09 s in steady state (the memo answers every unchanged alignment). The rebuild after a records write (reuse scan) dropped from about 6.3 s to 3.1 s, which is most of FAST-6's in-manifest gain. The memo is keyed on the exact strings (`old`, `new`, offset), so it cannot answer for a different text; it is bounded at 4,096 entries and cleared when full. The section-draft fragments now use the build's own `Records` snapshot instead of a second read of the log mid-build, which is more consistent, not less: a log written by another process during the build can no longer give the section draft different marks from the rest of the publication. Staleness: see FAST-9. Tests: none broken.

The audit's attribution was roughly right but overstated: in `loom serve` the selector matching inside the second resolution is already memoised in process (`records/selectors._find`, an `lru_cache`), so the duplicate cost about 2.4 s of 11 s (22 %), not 37 % of every build.

### FAST-3. Change 2 (comparison previews off the save path) is worth 2.0 s and leaves Review on source for one publication

In-process at load 3.7-3.8: 8.55 s to 6.57 s (6.59, 6.55); one `make4ht` run fewer per save (2 to 1), `deferred=1` preview per save on relloc. The previews show `marked_source` until the next publication. In the spike that is the post-`latexmk` rebuild when a compile is due (11-15 s after the save at today's load) and a follow-up rebuild otherwise. If `latexmk` produces no PDF, `_made` never fires and the previews stay as source until the next save: a hole a proper version must close (a scheduled follow-up independent of compiles). This is not "on demand" in the sense of made when Review opens; that needs an endpoint the viewer calls and a way to give it the build's renderer context, which I did not build. Tests: none broken.

### FAST-4. Change 3 (git name cached) is safe, and on a loaded machine it is the largest single cost for a new user

With no loom author name, every build forks `git config user.name` 609 times (confirmed). On today's machine those forks cost 28-38 s per build: the unmodified save build took 49.2 s and 38.7 s (load 5.2 and 24.7) against 9.4-10.5 s for the same build with the name cached (load 14-15), 0 forks. For the author, who has `[author] name` set, it changes nothing. `loom status` without a name went from 19.7-26.3 s to 13.5-16.7 s alternating at load 26-38 (the audit had 5.8-7.1 s and 2.3-2.6 s at load 5). The cache is keyed on the mtimes of `~/.gitconfig`, `$XDG_CONFIG_HOME/git/config`, the repository's `.git/config` and the `GIT_CONFIG_*`/`HOME` variables, so `git config --global user.name X` during a session is noticed; a name that comes from an `include.path` file is not. Tests: none broken.

### FAST-5. Change 5 (no TeX on a save's publication) is worth about 2 s to first sight but makes the typeset block arrive later

In-process, flags as the spike's server passes them: 8.38 s and 6.87 s with no TeX (load 11-12) against 10.47 s and 9.43 s with the edited block's snippet (load 14-15); the snippet run itself is 2.2-2.4 s at load 4 in the audit. In the viewer the edited proof appears as its LaTeX source first. The typeset version came with the follow-up publication 16.99-29.87 s after the save (median 23.7 s) against 11.7-20.4 s (median 15.4 s) in the unmodified code, where the first publication already carries it. So the audit's "the edited block flashes as source for a few seconds" is wrong on today's code: the follow-up publication repeats the whole fixed tail (FAST-1) and competes for the lock and the CPU with the `latexmk` the same save started. Deferring TeX only pays if a follow-up can publish the one fragment without rebuilding everything, which `build()` cannot do. Needs a design decision. Tests: none broken.

### FAST-6. Change 6 (answer writes before rebuilding) makes the answer instant and breaks the viewer's contract

Answered in 0.03 s instead of 6.3-6.7 s; the annotation reached the served manifest after 3.1 s instead of 6.3-6.7 s (that part is change 1). The viewer calls `store.refresh()` right after a write answers (`arras/src/lib/review/ask.ts:15` and the controls that annotate), expecting the write to be published; with the early answer it fetches the old manifest and shows nothing until the stream announces the rebuild 3 s later, and a rebuild that fails is no longer reported to the writer. It breaks 16-17 of the 85 tests in `tests/unit/render/test_write_api.py` and `test_serve.py`, all of the kind "the manifest shows the write when the answer arrives" (for example `test_write_api.py:873`, `:1160`); with changes 1-5 alone the same 85 pass. Needs a design decision (optimistic display in the viewer, or a `published` sequence number in the answer the viewer waits for on the stream).

### FAST-7. Change 4 (keys without page numbers) removes PERF-3's page-break storm, and the audit misplaced the cause of the 63 re-renders

A page shift (every `\newlabel` page in `draft5.aux` plus one, `tools/stale.py` step s4): the unmodified code rebuilt 2,384 blocks with 51 `make4ht` runs in 201.9 s (load 34); the spike rebuilt one (the landmark `fragments/canon/draft5.html`, whose key `_canon_hash` still reads the whole aux) with one `make4ht` run, in 41.8 s at load 26, most of it the fixed tail. The published result is the same (FAST-9). A save no longer queues behind a page-break storm, which is what the audit wanted. It does not touch a word edit's first publication. Renumbering a cited label (s5) still rebuilds everything in both, as it must (2,384 blocks, 51 runs; 250 s base, 120 s spike at lower load).

The audit says the 63 blocks re-rendered on every save are "every node of draft5, because the stale page's digest is in every node's cache key" (PERF-2). That is not what happens: a page's digest is taken from the TeX4ht page and its recorded sources (`render/fromhtml.py:84`), which a save does not touch. The 63 re-render because a node's key hashes the whole text of the file it is in (`render/build.py:246-257`), so any edit to `draft5.tex` changes the key of every node in it. Narrowing that to a node's own text would serve stale `data-src` line numbers after a line is inserted above it; it is not worth it, since the 63 cost about 1 s without TeX.

Risks found: a text that prints a page through a command outside the list (`\autopageref`, `\thepage`, or a preamble macro that wraps `\pageref`) would keep a stale page number. The list is `\pageref`, `\cpageref`, `\vpageref`, `\Vpageref`, `\vref`, `\Vref`, `\labelcpageref`, `\pagerefrange`, `\cpagerefrange`. A proper version should also look in the preamble for any of them and fall back to the whole aux. Python-rendered fragments never print a page (only `AuxNumber.number` is read, `render/fromhtml.py:206,507,854`; `render/mathset.py:171`), so dropping pages from `aux_bytes` is safe for them. Digests are still keyed on the draft's numbers: a renumbering of the draft still remakes cited papers' statements by TeX, which the audit's "key digests on their own file and preamble" would stop. Tests: none broken.

### FAST-8. Upgrading loom remakes every preview by TeX, and change 4 remakes every snippet once

`code_hash()` covers all of `render/`, `scan/` and `tex/` and is part of every fragment key and of the previews' salt (`render/fragments.py:110-130`), so any loom change in those packages makes the next build of relloc remake every Review preview by TeX (the audit's 145 s of cold previews). Change 4 changes every snippet key besides: its first build on relloc took 183 s (2,383 blocks, 49 `make4ht` runs) and the build after it 318 s (11 more runs) at load 36. Every one of the six changes touches those packages, so each landing costs every user one such rebuild, on relloc several minutes of TeX. A released version has the same effect through its version string. Worth knowing before sequencing them as separate releases.

### FAST-9. Staleness: what the spike publishes against what the unmodified code publishes

`tools/stale.py` runs one sequence of edits in one process, as `loom serve` would, on two copies of the same relloc: after each step a save-like build (previews from the cache only, where the code has that switch), then a second build from the same scan with TeX for everything, fingerprinting every published file (`manifest.json`, `fragments/`, `source/`, `spans/`, `transcripts/`, `diffs/`, `files/`) after each. Runs: unmodified code (`stale-base.json`); changes 1, 2, 3 and 5's server path (`stale-no4.json`, steps s0-s3); all six (`stale-mod.json`). `tools/stalediff.py` compares files at the same step; `tools/stepdiff.py` compares what each step changed.

| step | what it tries to break | changes 1-3 against base | all six against base |
|---|---|---|---|
| s0 warm | nothing | identical (manifest differs only in `corpus.directory` and `generated`) | 78 files differ, all from the one-off remake of FAST-8: TeX makes a picture's SVG afresh, so a remade fragment names different `svg/<hash>.svg` files (checked on the digest of `aranha-pstragowski_IntrinsicNormalCone2024` and on `canon/draft5.html`, identical once the names are masked) |
| s1 word in a proof | the snippet and the alignment memo | save build: the edited block's Review preview is source (`fragments/review/…-block.html`), as intended; settled build: identical | same set of 668 files changed as base |
| s2 an annotation's words removed (`a-2026-11-09-0012`, rl-001P's proof) | the gone-annotation memo and the section-draft marks | save build: the review preview and the version fragment `fragments/versions/1a27f59e3eda370e.html` are source, as intended; settled: identical, the annotation detached with `version.at: true` in both | same 623 files changed |
| s3 the words put back | a memo answering for words that came back | identical | same 623 files changed |
| s4 page shift (aux edited) | keys without pages | not run | base changed 15 files, spike 2 (manifest, landmark); the 13 only base changed are digest fragments remade by TeX with new picture names; the 59 nodes' `page` entries in the manifest are the same in both |
| s5 a cited label renumbered (aux edited) | keys still carrying numbers | not run | spike changed every file base changed (15) plus two more fragments of the same digest (picture names) |
| s6 a macro added to the preamble | snippet keys | not run | the same 1,722 files changed in both |

No change published a wrong page, number, mark or fragment in any step. What differs on a save's publication is exactly the deferred previews; the settled publication is identical. Not covered: a text that prints a page (`\pageref`) in a snippet, an `include.path` git name, and a real `latexmk` moving a page (the aux was edited instead). One thing the edits showed that is not a staleness: renumbering by editing the aux does not change blocks cut from the TeX4ht page, in either code, because those print what TeX put on the page until `make4ht` runs again.

### FAST-10. What under 2 s would take

The first publication is one monolithic `build()`: a fresh scan of every file, then every manifest section and every attached view recomputed, then the whole 10.6 MB manifest diffed and rewritten and refetched by the viewer. After the six changes, no single step is above 20 % of it. Under 2 s at load 4 means removing most of 5-6 s spread across eight steps, which only an incremental build does: (a) scan only the changed file and splice it into the last `ScanResult` (the scan is 15 %); (b) key adoption comparisons by copy and base hash, the section-draft context by its pinned inputs, and `Records.apply` by the log's and the scan's state, so that a word edit in a proof recomputes nothing of them (40 % together); (c) memoise the preview cache reads in process instead of reading and shaping every cached preview each build (15 %); (d) publish only the files that changed and send the viewer a manifest delta instead of 10.6 MB (publish and manifest 15 %, plus 160-490 ms of long tasks in the tab per publication, PERF-9); (e) for TeX, a follow-up that writes the one remade fragment without a full rebuild, or the TeX run kept on the first publication once everything else is fast, since 2 s of TeX inside a 2 s budget is not possible. That is a dependency-tracked build, weeks rather than days, and the hard part is making every one of those caches name all of its inputs, which is exactly where this spike found its staleness risks.

## Which changes to land

- **Safe as they are, with tests:** 1 (re-anchoring once, memo), 3 (git name).
- **Safe with a small addition:** 4 (keys), once the `\pageref` check also reads the preamble and the command list includes `\autopageref`; land it with a note that the first build after it is a cold one.
- **Need a design decision:** 2 and 5 (TeX off the save path: what the reader sees meanwhile, and a follow-up that does not repeat the fixed tail), 6 (answer before publishing: the viewer's contract).
- **What the audit got wrong:** the 63 re-renders come from the file-text hash, not the page digest (FAST-7); change 1 is worth 22 %, not 37 % (FAST-2); the "source for a few seconds" of its change 2 is in practice longer than the unmodified code's wait for the typeset block (FAST-5); its 3-4 s target needs the incremental tail it scoped out of the two weeks (FAST-1, FAST-10); and the git forks are a much larger cost on a loaded machine than its load-11 measurement suggests (FAST-4).

## Honest sizes (coding-agent sessions, each with tests)

| change | sessions | files it owns |
|---|---|---|
| 1 re-anchoring once, alignment memo | 1 | `render/versions.py`, `render/build.py`, `section_drafts.py`; tests in `tests/unit/render/test_versions.py`, `tests/unit/test_section_drafts.py` |
| 3 git name cache | 0.5 | `scan/quilt.py`; `tests/unit/test_quilt.py` |
| 4 keys without pages (plus preamble check) | 1-2 | `render/keys.py`, `render/snippets.py`; `tests/unit/render/test_build.py`, `tests/tex/test_snippets.py` (a `\pageref` case that must remake) |
| 4b digests keyed on their own file and preamble, not the draft's aux | 2 | `render/fragments.py` (digest owner), `render/snippets.py`; a digest fixture |
| 2 + 5 TeX off the save path, previews lazy, with a follow-up that publishes only what TeX made | 3-4 | `render/serve.py`, `render/build.py`, `render/changes.py`, `render/fragments.py`, `render/compiles.py`; viewer state for "typesetting" in `arras/` |
| 2b previews truly on demand (made when Review opens) | 2-3 | an API endpoint in `render/serve.py`/`render/api.py`, `render/review_compare.py`, Review in `arras/` |
| 6 writes answered before publication | 1 server + 1-2 viewer | `render/serve.py`, `arras/src/lib/write.ts` and its callers, 17 tests in `tests/unit/render/test_write_api.py` |
| incremental tail (FAST-10 b-c) | 4-6 | `render/incoming.py`, `adopt.py`, `section_drafts.py`, `records/store.py`, `render/changes.py` |
| incremental scan and manifest delta (FAST-10 a, d) | 6-10 | `scan/scan.py`, `render/publish.py`, `render/manifest.py`, `arras/src/lib/manifest/` |

## Tests

Targeted, two workers, on the final spike code: `tests/unit/render/{test_versions,test_build,test_review_compare,test_pending,test_compiles,test_snippet_code,test_compare,test_canon}.py`, `tests/unit/{test_section_drafts,test_quilt}.py`, `tests/tex/test_snippets.py`: all 118 passed. `tests/unit/render/{test_serve,test_write_api}.py`: 85 passed with changes 1-5; 16 and 17 failed in two runs with change 6 (FAST-6). In the first combined run of all thirteen files those two raised 72 setup errors ("file /priva…") that I did not chase; run as a pair with two workers they pass or fail as above, and `test_serve_static_routes` passes alone on both the unmodified and the spike code.

## Not done

- No viewer run at the audit's load; no viewer run per change (the per-change numbers are in-process builds, FAST-1 gives the method).
- Change 4 was not in the final viewer run (its one-off cold rebuild would have taken the time-box); it does not touch a word edit's first publication, only the rebuilds after a compile that moves pages.
- A real page-break move through `latexmk` was not done; the page shift and renumbering were made by editing the aux, which tests the keys exactly but not TeX's own aux.
