# Speed: where the time goes

Auditor: speed. Study checkout `v0.1-study` at 71621877 (equal to main). All numbers are from copies of `~/quilts/relloc` and `demos/showcase` in scratch, with the study checkout's own `.venv`, TeX Live 2024, Python 3.13, on an 8-core machine shared with other sessions. Load average is given beside every wall-clock figure; it ranged from 3 to 34 during the run, so attribution (shares) is more reliable than absolute seconds.

## How this was measured

- `tools/probe.py`: runs `build()` in process, wraps `subprocess.Popen` to log every child (exe, start, end, thread), takes stage stamps from `build()`'s own `progress` callback, and optionally cProfiles (one profiler sees every thread on 3.13). cProfile inflates Python time about 2.4x, so profiled runs are used for shares only.
- `tools/parts.py`: unprofiled wall time of each named step of `build()` (`gone_annotations`, `attach_context`, …).
- `tools/serveprobe.py`: `ServeSession` in process on ports 47810-47813 with timestamped events (watcher call, each build stage, publication, compile begin/end, make4ht begin/end) plus the subprocess log.
- `tools/viewer.cjs`: headless Chromium through the main checkout's Playwright 1.63, read-only. It opens `/master/drafting/draft5`, waits for a phrase in the DOM, then writes an edit to the source and waits until the new words are in the DOM and the old ones gone (save to seen). It also records long tasks and every manifest fetch.
- Scripts live in `/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/speed/tools/`, raw logs beside them in `logs/`.

**Copy hygiene.** The relloc copy carried `.loom/serve.json` naming the author's live server (pid 23240, port 8791, its token, root `/Users/isaac/quilts/relloc`). Left in place, `loom serve` on the copy refuses to start (`cli/serve_cmd.py:40-43`) and `loom here` on the copy would talk to the author's server (`cli/here_cmd.py:30-40`). I deleted it in both copies. `.claude/settings.json` and `.codex/rules` hold only relative permissions; nothing else in the copy points back.

**Identity caveat.** My `XDG_CONFIG_HOME` has no loom author, so `resolve_author` falls back to `git config user.name` (`scan/quilt.py:231-241`). The author's own machine has `[author] name` set, so where it matters I measured both ways (`--cache-git` = one git call per process, as with a configured name). A new v0.1 user who has git configured but has never set a loom name is in the slow case.

## relloc's shape

Two drafts of 2,765 lines in all (`drafting/draft5.tex`, `drafting/examples.tex`), two adopted copies under `.loom/copies/`, 37 cited works with digests, 437 annotations. Of 2,354 manifest nodes, 2,012 (85 %) are statements of cited papers; the drafts own 139. The copy is 966 MB, of which `.loom/build` is 865 MB and `.loom/build/cache/previews` alone 537 MB in 57,774 files, the oldest from 12 October.

## Headline numbers

| what | showcase | relloc | load |
|---|---|---|---|
| `loom serve` listening | 0.25 s | 0.23 s | 3.8 |
| warm start, first build done (nothing to render) | 0.6 s | 9.3 s | 3.8 |
| cold start, first build done (manifest 404 until then) | 0.6 s (fragments present, no PDFs) | 502 s | 3 rising to 20-33 |
| cold start, draft readable as TeX4ht page | ~20 s (5 documents compiled) | 1,100 s (18 min) | 11-33 |
| save a word in a proof, seen in the viewer | 0.92 / 0.31 / 0.41 s | 11.75 / 9.22 / 14.56 s | 4.7 / 3.8-4.1 |
| save a word in a statement, seen | n/a | 12.09 / 11.53 s | 4.1 |
| save, until the whole compile chain settles | ~4.5 s | 31-53 s, once 107 s | 4 |
| save a `.tex` no document includes, republished | n/a | 7.0 / 6.4 / 6.6 s | 5 |
| save a Markdown file, republished | n/a | 5.9 / 5.6 / 5.3 s | 5 |
| annotation via HTTP, answered (manifest current) | n/a | 5.05 / 5.85 / 6.27 s | 3.2-3.6 |
| annotation via CLI: command / in manifest | n/a | 1.98 / 1.75 / 2.03 s; 8.1-8.5 s | 4.2-4.5 |
| `loom build`, cached (nothing to render) | 0.66 s | 15.5 s; 8.6 s with a loom author name | 11; 8 |
| `loom build`, cold | n/a | 316 s (profiled; TeX 274 s of it) | 7-34 |
| manifest | 0.22 MB | 10.6 MB (1.07 MB gzipped), served uncompressed | |

## Findings

### PERF-1. Every publication on relloc costs at least 5 s even when nothing changed

**Evidence.** A Markdown save republishes with the last scan reused and renders 0 blocks, yet takes 5.3-5.9 s (load 5); a `.tex` file no document includes takes 6.4-7.0 s (full scan, 0 blocks); a cached `loom build` takes 8.6 s with an author name (load 8). The fixed cost is in the steps `build()` runs unconditionally after rendering (`render/build.py:427-431`, `:566-622`). Unprofiled shares of a 17.6 s cached build at load 15 (`tools/parts.py --cache-git`):

| step | time | share | code |
|---|---|---|---|
| re-anchoring annotations whose words are gone, twice | 6.6 s | 37 % | `render/versions.py:118`, called from `render/build.py:430` and again via `section_drafts.py:314` → `render/build.py:298` |
| section-draft context (incl. one of the two above) | 3.4 s | 19 % | `section_drafts.py:276` |
| scan | 2.6 s | 15 % | `scan/scan.py:232` |
| marks per node | 2.5 s (2 calls) | 14 % | `render/build.py:292` |
| adoption comparisons (5 throwaway scans of temp quilts) | 2.1 s | 12 % | `render/incoming.py:207`, `adopt.py:99-115` |
| previews made (cache reads, shaping) | 1.3 s | 8 % | `render/build.py:592` |
| session transcripts rewritten | 1.0 s | 6 % | `render/build.py:344`, `:597` |
| publish (diff and write) | 0.9 s | 5 % | `render/publish.py:62` |

`gone_annotations` diffs every detached annotation's old text against the key's text now with `difflib` (`render/versions.py:56-82`) on every build, 476 alignments per build on relloc, with nothing cached across builds; `section_drafts.py:314` builds a fresh `Records` and calls `_marks_by_node` without the `gone` list the build already has, so the whole computation runs twice. **Weight:** blocks (it is half of save to seen). **Effort:** a day for caching the alignment by (old-text hash, own-text hash, selector) and passing `gone` through; days to make attach_context and adoption comparisons incremental. **Recommendation:** fix.

### PERF-2. Save to seen on relloc is 9-15 s, and two TeX runs sit on the path

**Evidence.** Five edits through the viewer (load 3.8-4.1): 11.75, 9.22, 14.56 s (a word in the proof of `rl-000G`) and 12.09, 11.53 s (a word in the statement of `rl-000H`). Server timeline for trial 1, seconds after the save: watcher calls rebuild 0.11; scan stage to 2.10 (it also covers records, gone annotations, marks and pages, `render/build.py:419-436`); rendering 63 blocks to 5.25; recording to 11.13; publishing to 11.42; viewer sees it at 11.75. Inside that, the subprocess log shows a `make4ht` snippet run of 2.2-2.4 s in the rendering stage in every trial (the edited block remade by TeX on the stale page, `render/fromhtml.py:365-400`) and a second one of 2.2 s in the recording stage when the text is new (Review's comparison preview of the changed block, `render/review_compare.py`, files `drafting/review-*.tex` under `cache/previews`). The 63 re-rendered blocks are every node of draft5, because the stale page's digest is in every node's cache key (`render/build.py:259-262`). Showcase does the same loop in 0.3-0.9 s. **Weight:** blocks. **Effort:** see the five changes below. **Recommendation:** fix.

### PERF-3. A compile that moves a page number re-renders all 2,384 blocks, and can rerun TeX on all 37 cited papers

**Evidence.** Every fragment's cache key includes `aux_bytes` of every document's numbers and page numbers (`render/build.py:255`, `render/keys.py:37-46`), and every snippet's key includes the SHA-256 of the default document's whole `.aux` file (`render/snippets.py:185-186`, passed at `render/fragments.py:286`), including the snippets of cited papers' digests, which are made under the default document's preamble (`render/fragments.py:336-356`). After the background `latexmk` in trial 1 the rebuild rendered 2,384 of 2,386 blocks (16.6 s, no TeX); in trial 2 it rendered 2,384 and ran about 50 `make4ht` snippet jobs over 54 s, a 78 s rebuild in all (`logs/rl-serve.jsonl`, subprocess log). In trials 3-5 the aux did not change and the same rebuild rendered 0 blocks in 6 s. Review comparison previews are keyed the same way and were remade at the same moments. The rebuild holds the publication lock (`render/serve.py:704`), so a save made in that window waits: in trial 3 the edit's rebuild waited 4 s behind the previous trial's. A cited paper's statement does not depend on the draft's page numbers. **Weight:** blocks (an author writing new text moves page breaks often). **Effort:** a day or two: key each block on the numbers it actually cites, and key digests on their own file and preamble, not on the draft's aux. **Recommendation:** fix.

### PERF-4. Each save runs the full document compile, a TeX4ht pass and two more full rebuilds

**Evidence.** After the first publication the queue compiles draft5 (`latexmk` 4.6-5.1 s), publishes a rebuild (`render/serve.py:812`, 6-6.5 s normally, 16.6-78 s per PERF-3), runs `make4ht` on the whole document (13.1-14.2 s), then rebuilds again when the run ends (`render/compiles.py:194-196` → `render/serve.py:688`, 6-7 s). That is 31-53 s of background work per save, 107 s once, with the rebuild lock held for 12-90 s of it. On showcase the same chain is about 4.5 s. The PDF matters only to someone who opens it; the TeX4ht page replaces snippets that already show the edit. **Weight:** hurts (it is background, but it competes for the lock and the CPU with the next save). **Effort:** hours to drop the rebuild after the PDF (publish the PDF file alone; rebuild once after the page); a day to debounce the whole chain while the author keeps saving. **Recommendation:** fix.

### PERF-5. Without a loom author name, every build forks `git config user.name` 609 times

**Evidence.** `git_user_name` has no cache (`scan/quilt.py:214-228`) and is reached once per annotation through `Records._on_kept` → `pending.in_place` → `pending.reviewer` (`records/store.py:652-661`, `pending.py:132-136`, `:190-194`); `in_place` asks for the reviewer before `look_texts` checks `track_edits` (`pending.py:151`), so a quilt that does not track edits pays too. Measured: 609 forks, 6.8 s of a 15.5 s cached build (load 11); `loom status`, `ai orient`, `lint`, `ai annotations` take 5.8-7.1 s, and 2.3-2.6 s once the name is cached. **Weight:** blocks for a new user who has git but no loom name; irrelevant for the author. **Effort:** hours (cache per process, or resolve once per build). **Recommendation:** fix.

### PERF-6. A cold start shows nothing for minutes, and the draft's own page comes last

**Evidence.** `ServeSession.start` runs the whole first build before it watches or compiles (`render/serve.py:889-895`); the compiles of documents never compiled are queued only after it (`render/serve.py:907-925`). Until the first build publishes, `/build/manifest.json` is 404 (measured). The cold `loom build` (profiled, load 7-34) took 316 s, of which a TeX subprocess was running for 274 s (109 `make4ht` runs, 823 s of child time): cited papers' digests 103 s (`render/fragments.py:302-356`, scan stage), previews and comparison pictures 145 s (recording stage, `render/build.py:566-592`), landmarks (canon) 25 s, section-draft context 25 s. A cold `loom serve` on relloc (load 3 rising to 33) listened at 0.19 s, answered 404 for the manifest until 502 s, when the draft appeared as its source (a headless tab was readable at 494 s after it navigated); during those 502 s a TeX subprocess ran for 470 s. The queue then compiled the two adopted copies before the draft (my headless tab apparently never reported its place, so `_reading()` had nothing to put first, `render/compiles.py:150-153`; a focused real tab may fare better, unverified). Each compile changed the aux, so each following rebuild re-rendered 2,383-2,385 blocks and remade snippets and previews by TeX: 265 s after the first copy, 146 s of digest snippets after draft5's PDF, because the digests had first been made against no aux at all and are keyed on it (PERF-3). draft5's TeX4ht page was first published at 1,100 s. After the first build, 540 s of the 613 s had a TeX subprocess running: 68 `make4ht` runs (1,852 s of child time) but only 4 `latexmk` runs (35 s); the documents themselves were a small part. **Weight:** blocks (every v0.1 user's first contact is a cold start: on a quilt with a library, minutes of nothing and a quarter of an hour to the typeset draft). **Effort:** days: publish the draft first (scan, compile the default document, publish), then digests, previews, landmarks in the background or on first view. **Recommendation:** fix (order) and defer (digests and previews to on demand).

### PERF-7. A warm start is fine, but the first publication still waits 9 s

**Evidence.** On the built copy the server listens at 0.23 s and serves the previous manifest at once (10.6 MB in 35 ms), so the viewer is readable immediately with the last state; the first build completes at 9.3 s (load 3.8; 26.7 s in a second start at load 13-18) with 0 blocks rendered and no compiles. A fresh headless tab on `/master/drafting/draft5` is readable 0.80-0.92 s after navigation (three runs, load 13), with 1.6-2.1 s of long tasks in its first seconds (longest 300-364 ms) and a 97-123 MB heap; showcase is readable in 0.27-0.32 s with 78-129 ms of long tasks. **Weight:** cosmetic. **Effort:** none beyond PERF-1. **Recommendation:** keep.

### PERF-8. Viewer writes wait for a full rebuild before they answer

**Evidence.** `POST /_api/annotate` writes under the publication lock, then calls `self.rebuild(records=True)` synchronously before answering (`render/serve.py:366-370`); the viewer awaits that answer (`arras/src/lib/write.ts:89-125`). Measured 5.05, 5.85, 6.27 s on relloc (load 3.2-3.6); bench target 1 s. A CLI annotation returns in 1.75-2.03 s (import plus a full scan) and reaches the manifest at 8.1-8.5 s through the fast lane (`render/watch.py:118-120`) and a rebuild. **Weight:** hurts (annotating is a core gesture; 5 s per comment is felt). **Effort:** hours to answer before the rebuild and let the stream announce the publication; the rebuild itself shrinks with PERF-1. **Recommendation:** fix.

### PERF-9. The whole 10.6 MB manifest is refetched and reparsed on every publication

**Evidence.** The stream says only that a manifest exists (`arras/src/lib/manifest/stream.ts:24`); the store refetches it whole (`arras/src/lib/manifest/client.svelte.ts:84-120`), the server reads and SHA-256-hashes it per request and sends it uncompressed (`render/serve.py:475-494`). Largest parts: nodes 1.95 MB, keys 1.57 MB, contributions 1.39 MB, annotations 0.93 MB, search 0.77 MB, references 0.76 MB, edges 0.64 MB; 85 % of nodes are cited papers'. In the browser each publication costs 160-490 ms of long tasks (headless Chromium, load 4), and a save brings 3-4 publications. Fetches take 8-40 ms on loopback. **Weight:** cosmetic now; hurts once PERF-1 is fixed and these milliseconds are a visible share. **Effort:** hours for gzip; days to split the manifest (cited papers' nodes and search on demand). **Recommendation:** defer, except gzip.

### PERF-10. Every agent call is a fresh process that rescans the quilt

**Evidence.** The MCP server runs each tool as `python -m loom …` (`mcp/server.py:198-206`); every command scans afresh (`cli/_quilt.py:38-46`). On relloc (load 4.5-5.6): `--version` 0.16-0.24 s; `search`, `source KEY`, `source` of the draft, `deps`, `changes` 1.5-1.7 s; `status`, `status --json`, `ai orient`, `lint`, `ai annotations` 5.8-7.1 s, 2.3-2.6 s with an author name (they resolve every annotation, `records/store.py:547`, the same work as PERF-1). An agent making 40 calls spends 1-4 minutes waiting on loom. **Weight:** hurts. **Effort:** a day for the MCP server to keep one scan and refresh it when the watcher's files change (the server process already exists); hours to cache `Records.resolved`. **Recommendation:** fix after PERF-1 and PERF-5.

### PERF-11. Caches grow without bound

**Evidence.** `.loom/build/cache/previews` holds 57,774 files (537 MB); `snippets` 7,200 (43 MB). Nothing prunes either; `--force` deletes only failed snippets and previews (`render/build.py:446-450`). Disk only, no time measured against it. **Weight:** cosmetic. **Effort:** hours. **Recommendation:** defer.

### PERF-12. The watcher polls the tree every second, and the scan rereads every file

**Evidence.** `Watcher._loop` walks the tree outside `.loom/build` and the store every second and five times a second checks three record files (`render/watch.py:120`, `:160-178`); notice took 0.11-0.81 s after a save. The walk itself is 530 files on relloc and usually under 0.1 s, but logged 0.1-1.1 s while a build held the GIL. **Weight:** cosmetic. **Effort:** hours for FSEvents/watchdog. **Recommendation:** defer.

### PERF-13. `scripts/bench` times the edit loop with TeX switched off

**Evidence.** The bench starts `loom serve --port N --no-compile` (`scripts/bench:106`), and the server passes `tex=self.compile_masters` to every build (`render/serve.py:722-724`), so the snippet that remakes the edited block, the comparison previews and the whole compile chain never run in the row "edit one result, republished" (target 3 s). On relloc those are 2.2-4.5 s of the 9-15 s measured here. The bench also has no row for a cold `loom serve` and none on a library-heavy quilt. **Weight:** hurts (the number that guards the core loop is optimistic by a third). **Effort:** hours: add a row with compiles on, and run it on a relloc-sized fixture. **Recommendation:** fix.

## Work nobody asked for

| work | where | cold cost on relloc | per-save cost | who needs it, when | could be |
|---|---|---|---|---|---|
| cited papers' digests made by TeX (1,597 statements, 37 works) | `render/fragments.py:302-356` | 103 s TeX | 0; ~50 TeX runs, 54 s, when the draft's aux changes (PERF-3) | a reader opening a cited result | lazy per work on first view; never keyed on the draft's aux |
| previews: Review comparisons, suggested edits, versions, adoptions | `render/build.py:566-592` | 145 s TeX | 0-2.2 s TeX per save | someone in Review | lazy when Review opens; background |
| landmarks (canon) fragments | `render/canon.py:144` | 25 s TeX | 0 | someone opening a kept version | lazy |
| section-draft context | `section_drafts.py:276` | 25 s | 1.5-3.4 s | a reader of the section draft | incremental (cache by inputs); pass `gone` |
| annotation re-anchoring for gone words | `render/versions.py:118` | in Python | 3-6 s (twice) | marks on the page | cache across builds |
| adoption comparisons (5 temp-dir scans) | `adopt.py:99`, `render/incoming.py:207` | in Python | 0.9-2.1 s | someone deciding an adoption | cache by copy and base hash |
| session transcripts | `render/build.py:344` | in Python | 0.4-1.0 s | someone reading a chat | write only the session that changed |
| PDF compile + whole-page TeX4ht + 2 rebuilds | `render/serve.py:792-833` | per document | 31-53 s background | the PDF reader; the final page | debounce; one rebuild |
| the search index and cited nodes in the manifest | `render/manifest.py:264` | | 0.8 + 2 MB per publication | search, library | separate file, fetched on demand |

## Answers by question

1. **Starting.** Warm: listening 0.23 s, readable at once from the last build, current at 9.3 s (PERF-7). Cold: manifest 404 for 502 s, the typeset draft at 1,100 s (PERF-6); everything waits for the first build, digests and previews included, the draft compiles after the adopted copies, and each compile invalidates every block again.
2. **Edit loop.** 9-15 s to seen on relloc against 0.3-0.9 s on showcase (PERF-2); 31-53 s until the compile chain settles (PERF-4). Rebuilt without need: all 63 blocks of draft5 on every save, 2,384 blocks after a page-number shift (PERF-3), the whole fixed tail (PERF-1). A file no document includes still costs a full 6-7 s rebuild and no compile; a Markdown file 5-6 s.
3. **Viewer writes.** HTTP 5-6 s, CLI 2 s plus 6 s to the manifest (PERF-8).
4. **Whole builds.** Cold 316 s, 87 % in TeX subprocesses; cached 8.6-15.5 s, all Python except the git forks (PERF-1, PERF-5, PERF-6).
5. **Client.** Manifest 10.6 MB; biggest pages: `.loom/copies/examples-shared` page 1.47 MB, its fragment 1.46 MB, `fragments/nodes/rl-00I0-ai.html` 0.78 MB. A warm tab on relloc is readable in 0.8-0.9 s, then busy for 1.6-2.1 s more; showcase 0.3 s. Each publication 160-490 ms of long tasks (PERF-9).
6. **Work nobody asked for.** Table above.
7. **Agents.** PERF-10; the five slow commands are slow for the reason PERF-1 and PERF-5 give.

## The five changes that would most shorten the loop

| # | change | gain on relloc | effort | risk |
|---|---|---|---|---|
| 1 | Re-anchor gone annotations once per build and cache the alignments across builds; pass `gone` to the section-draft context (PERF-1) | 3-4 s off every publication, write and status call | a day | an annotation drawn at a stale place if the cache key misses an input |
| 2 | Take TeX off the first publication: publish the stale page with the edited block as source (or its previous rendering), then remake it by TeX and publish again; make Review's comparison previews lazy (PERF-2) | 2.2-4.5 s off save to seen | a day | the edited block flashes as source for a few seconds |
| 3 | Narrow cache keys to what a block cites: per-label numbers instead of `aux_bytes` of every document, and digests keyed on their own file and preamble (PERF-3) | removes 10-70 s lock-held rebuilds after a page-break shift, so a save never queues behind one | a day or two | a stale cross-reference number if the dependency set is wrong |
| 4 | Make the fixed tail incremental: section-draft context, adoption comparisons and transcripts only when their inputs changed; answer HTTP writes before rebuilding (PERF-1, PERF-8) | 2-4 s off every publication; writes answer in under 0.5 s | days | a view showing an old comparison if an input is missed |
| 5 | Cold start in the right order: scan, compile and publish the default document first, then digests, previews and landmarks in the background or on first view; cache the git name (PERF-6, PERF-5) | typeset draft on a cold start from about 18 min (8 min to anything) to the draft's own compile, roughly 30-60 s | days | features that read digests show "not yet made" for a while |

**Realistic target in two weeks.** Today's floor on relloc is about 5 s of fixed tail plus 2 s of scan plus 2-4.5 s of TeX plus up to 1 s of polling. Changes 1, 2 and 4 bring the first publication to the scan plus a thin tail, about 3-4 s at load 4, with the edited block shown as source until the snippet lands 2-3 s later; change 3 keeps that true while the compile chain runs. Under 2 s on a quilt of relloc's size needs an incremental scan and a manifest diff, which is more than two weeks. On a showcase-sized quilt it is already under 1 s.

## Not measured

- The viewer on a real (non-headless) browser and on a quiet machine; all long-task figures are headless Chromium at load 4.
- Memory of `loom serve` over a long session.
- `examples.tex` and the two copies' compile chains on save (only draft5 was edited).
- py-spy was not installed and I did not install it; thread attribution comes from cProfile on 3.13 (one profiler sees all threads) and the subprocess log.
