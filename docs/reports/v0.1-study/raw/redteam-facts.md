# Red team: the facts in the plan, state.md and codebase.md

A fact-check of `docs/plans/0.32-v0.1.md` (P below), `docs/reports/v0.1-study/state.md` (S) and `docs/reports/v0.1-study/codebase.md` (C) against the reports under `raw/`, `register.md`, `register-notes.md`, the patches under `spikes/` and the code at 71621877. Line numbers are the documents' own. Nothing was run but `git`, `grep`, `wc`, the hard-wrap checker and small read-only scripts; no document was edited.

Method. Three helpers read S lines 1-48, S lines 50-108 (without Fast) and C, sentence by sentence, quoting the source line for every verdict. I read P, S's Fast section, register-notes, the three later reports that correct earlier ones (`spike-door.md`, `spike-speed.md`, `check-labels.md`) and the parts of the others each claim needed, and re-opened the source for every row not marked †. A † row rests on a helper's quoted source line, which I did not re-open. Paths without a prefix are under `docs/reports/v0.1-study/` for reports and under `loom/src/loom/` for code.

Counts: **29 wrong, 54 overstated, 11 stale, 2 unsupported** (96 in all), then 20 consistency problems.

## 1. Errors

### Wrong

| # | where | as written | what is wrong, and the correction | source |
|---|---|---|---|---|
| W1 | S:58 | "Eleven of eighteen were achieved." | walk.md achieved 10 (tasks 1, 2, 6, 8, 9, 10, 11, 13, 16, 18), partly 5, not 3. Write "Ten of eighteen were achieved, five partly, three not." | register-notes.md:260; walk.md:44-61 |
| W2 | S:23, S:58 | "Two independent first-time users failed the same five tasks"; "Both failed or struggled on the same five: whether an AI can see my comment; whether one is connected; undoing a Keep; commenting on a sentence and not its whole paragraph; and leaving a note attached to nothing." | The notes name six tasks that both walkers failed or only partly managed: 3 (can an AI see my comment), 4 (is one connected), 7 (undo a Keep), 12 (add a paper by dropping it), 14 (all notes in one place) and 15 (Problems that cannot be fixed in the app). Task 2 (comment on a sentence) and the free-standing half of 14 are "fragile": the stronger walker managed both. "Independent" is too strong: both walkers were AI models, and the weaker used the first's browser driver. Write "Two AI walkers failed or only partly managed the same six tasks" and name them. | register-notes.md:237, :262, :264 |
| W3 | P:30 | "the five tasks both failed now succeed for both" | Six tasks, not five. "Failed" is also too strong: walk-small counts task 7 done, after about 18 actions. Name them: "tasks 3, 4, 7, 12, 14 and 15 of `raw/walk.md`". | register-notes.md:262 |
| W4 | S:34 | "Forty-one lines in the author's own quilt are signed with a test fixture's name … (checked)" | The sources count 34 record lines, dated 11-05 to 11-12. A raw grep of the live quilt's `.loom/` reaches 41 only by also counting a backup log, text snapshots, a run log, the split-look file and a digest (helper's read-only grep). Write 34. | quant-findings.md:104; register-notes.md:103 (b.28) |
| W5 | S:30 | "against copies of four quilts" | It was three quilts: synthetic, showcase and quant. | safety.md:3; register.md:40 |
| W6 | S:30, S:20 | "six faults that damage text, none needing an unusual session"; gate: "Six faults damage text in ordinary use" | Four of the six occur in an ordinary session (SAFE-1, 2, 4, 5). The other two need files with Windows line endings or Latin-1 bytes (SAFE-6, 7). | safety.md:5 |
| W7 | S:38 | "Three trials confirmed that such an edit shows nowhere in the viewer (LIVE-12, SMALL, ATT-3)" | ATT-3 comes from reading the code, not from a trial. The third trial is REV-5, which is review.md's trial 10. | register.md:64 (ATT-3, "read in code"); review.md:134 |
| W8 | S:44 | "`loom serve` serves one quilt, must be started inside it, and uses a fixed port" | `--quilt PATH` serves a quilt from any directory. The port defaults to 8791 and `--port` changes it. The real faults are that it needs a terminal and that every quilt defaults to the same port, so the second quilt fails. INST-1 itself carries both errors. | cli/serve_cmd.py:16, :23; cli/_quilt.py:23; live.md:87 |
| W9 | S:48 | "process handling, file locking and the test suite all assume POSIX (INST-14, read)" | INST-14 finds a Windows file lock already present. The blockers it lists: process control and the liveness probe, opening files, about 60 calls with no encoding, `os.replace` racing readers, Perl for latexmk, and the tests' extensionless fake TeX. | install.md:139; locks.py:26 |
| W10 † | S:46 | "a missing package can be detected from the logs in thirty of thirty-seven cases" | One pattern catches 30. Two more patterns bring it to 34 of 37; 3 name nothing loom can read. | tinytex.md:82, :182 |
| W11 | S:52 | "was refused 'mark it as checked' and 'add this paper'" | Loom refused nothing. The model never ran either command: it declined on the orientation's word. register.md's SMALL-5 row repeats the error. Write "declined, on the orientation's word, to …". | small-model.md:110, :158 |
| W12 † | S:52 | "the bridge that tells an agent what page and selection the person has open works (LIVE-9, LIVE-14, measured)" | Both ids and the mark are wrong. The bridge was tried in LIVE-10, where the page arrived and the selection worked only in an inline document, and in QF-W3, where the page worked and the selection was not verified. LIVE-9 covers the protocol and server lifetime; LIVE-14 covers modes as commands. Both are "reproduced" with a scripted stand-in for the model, not measured. | live.md:115-124; quant-findings.md:68 |
| W13 † | S:54 | "An agent's comments arrive silently: only counters change (LIVE-11)." | The margin markers became stacks and the suggestion appeared inline as green tracked text. What is missing is any notice. | live.md:130-133 |
| W14 | S:58 | "Both found the same names pointing the wrong way: 'Proposed Changes' holds a cited paper's results, and an AI's edits to the text are under 'Your Changes'." | Only walk.md raised this (WALK-12). The weaker walker read both lists correctly and called the labels good (SWALK-21). | walk-small.md:35, :131 |
| W15 | S:64 | "three bugs sit in suggested edits themselves … (CUT-14, reproduced)" | CUT-14 lists four defects, and two of them are in suggested edits: 14a (a section body edit deletes the heading) and 14b (an insertion needs a quote the rules forbid). 14c (an agent's ordinary file is counted as the person's) and 14d (copies have no versions) are not. Write "two bugs". | cuts.md:221-226 |
| W16 | S:78 | "re-anchoring annotations whose words are gone, done twice and never cached" | The quote matching inside it is cached in process (`records/selectors._find`, `lru_cache(maxsize=4096)`). Only the difflib alignment goes uncached across builds. | records/selectors.py:56; spike-speed.md:48 (FAST-2) |
| W17 | S:78 | "a first-time user loses the first second of typing after marking words (EXP-3)" | EXP-3 comes from the exploring journey, where an investigator who knew loom played a researcher. It was measured on the showcase, where each annotate write took 1.3-1.5 s. | explore.md:3, :28, :80 |
| W18 | S:40 | "shell escape is off" | Loom passes no `-shell-escape` but sets no `shell_escape=0` either. What blocks `\write18` is TeX Live's default *restricted* shell escape, which is on. This was tested on TL 2024 only, so it must be rechecked under loom's own TinyTeX. Write "full shell escape is off; TeX Live's restricted default blocks `\write18`". | security.md:5, :50, :58 |
| W19 | S:40 | "Five weaknesses were demonstrated", listing SEC-1, 2, 3, 5 and 4 | security.md's "five fixes" are SEC-1, 2, 3, 5 and SEC-6b (`.loom/serve.json` written 0644). It treats SEC-4 (the agent boundary is advice) as a known limit to state, not a fix. P's "five security fixes" follow security.md, so S names a different five. | security.md:107-127 |
| W20 | C:60 | "66 hand-written routes … (TEST-9)" | The id is TEST-10. TEST-9 is the ~220 static e2e tests of features v0.1 hides. | tests.md:17-18 |
| W21 | C:90 | change 7, "`test_output.py` to one run per case \| about a quarter of the unit tier's time" | The quarter is what the whole file costs (~115 s of ~450 worker-seconds). One run per case saves 60-70 s serial, which is 15-20 s of wall time. | tests.md:88, :165 |
| W22 † | C:44 | "Seven help and report strings still say loom never edits a file, though four operations now do (CORE)" | There are at least nine such strings: CORE-8's seven, plus `doctor.py:618` and `:626`. At least six operations edit a person's existing file: Keep, discard, restore, tick, and the incorporate steps of adopt and sync. | `grep -rn "never edit" loom/src/loom`; core.md:165-166 |
| W23 | C:52 | "The two `CONTRIBUTING` files still describe separate repositories (PROC)" | Neither does: `arras/CONTRIBUTING.md:3` says "the two are one tool". The stale sentence is `loom/CONTRIBUTING.md:5`, which says the invariance test "runs every command" (TEST-2). | arras/CONTRIBUTING.md:3; loom/CONTRIBUTING.md:5; process.md:199 |
| W24 † | C:67 | "One plan per phase is a habit, not a rule written anywhere." | PROC-37 says the rule is written in the author's memory. The current rule is also different: one master plan, with its phases planned in plan mode. | process.md:81; cuts.md:181 |
| W25 | C:63 | "the machine's load reached 38 to 55 with a dozen sessions running" | The highest load any report records is 50, and no report says "a dozen sessions". | spike-speed.md:7 |
| W26 † | S:66 | "The author's log of a month's learning" | The log covers eight days, 11-04 to 11-12. | quant-findings.md:3 |
| W27 | P:31 | "Three scripted journeys played by an agent pair, as in `raw/explore.md`" | explore.md had no pair. One investigator played both the researcher (in the viewer only) and the agent (through agent commands only). | explore.md:3 |
| W28 | P:92 | "Each block's key hashes its whole file, which is why a save re-renders them all." | A save re-renders every block of the edited file (63 in relloc's draft), not every block. The all-blocks storm comes from page numbers. The spike also advises against narrowing the per-file hash: it would serve stale line numbers and save about 1 s. | spike-speed.md:70 |
| W29 | P:92 | "The audit's three to four seconds was not reached: about 6.5 s for the build, less the last TeX run." | 6.57 s is the in-process build with changes 1 and 2, at load 3.7-4.7. Taking off the last TeX run (~2 s) leaves 4.5-5 s of build, plus ~0.5 s to reach the page. Write "roughly 5-6.5 s to first sight at the audit's load". | spike-speed.md:40 |

### Overstated

| # | where | as written | what is wrong, and the correction | source |
|---|---|---|---|---|
| O1 † | S:30 | "lost a kept edit in three of fifteen trials (SAFE-2)" | A rerun of the same script on the same code lost 1 of 15, so write 1-3 of 15. The "viewer" Keep was a call to the HTTP write API. | spike-door.md:68; safety.md:107 |
| O2 † | S:30 | "Latin-1 accents are corrupted by Keep, restore and discard" | Discard was shown only for CRLF (SAFE-7). Latin-1 damage was reproduced for Keep; for restore it was reasoned. | safety.md:126, :130 |
| O3 † | S:32 | "both first-time users failed it" | Neither found a one-step undo. walk-small counts the task done, by a whole-file restore after about 18 actions; walk.md counts a partial after about 25. | register-notes.md:247; walk-small.md:37 |
| O4 † | S:32 | "(WALK, reproduced)" | The missed edit was reproduced. Its cause ("saved under another document") is the walker's reading of the screen, which the registrar marks "not checked". No id is given. | register.md:62 |
| O5 | S:34 | "A copied quilt carries a pointer to the original's running server, with its access token (PERF, checked)" | The file travels only if the quilt is copied while its server runs, because a clean stop deletes it. Loom then ignores a `serve.json` that names another root. So the harms speed.md describes (a refused start; `here` reaching the original) do not happen at 71621877. What remains is a live token in a copied file. The id is PERF-copy. | render/serve.py:183; cli/serve_cmd.py:40; speed.md:15 |
| O6 | S:36 | "160 on the wrong block, detached 615 and lost 960" | The numbers are right, but 380 of the 1,575 detached or lost records are honest: their words are really gone. The misses are 1,195. The papers were taken as written, 92 % keyed by place; imported papers carry ids and fare better. | check-labels.md:131, :159 |
| O7 | S:36 | "One inserted theorem moves every acceptance onto the wrong theorem." | This was measured on 5 accepted statements keyed by place. The moved rows show "accepted, stale", so nothing is approved silently. Statements keyed by id are unaffected. | check-labels.md:262, :270 |
| O8 † | S:38 | "lets an agent rewrite the person's drafts and records nothing … shows nowhere in the viewer" | The page re-renders the new words, and an edit to an accepted block shows "changed since you accepted". The unprompted write needed acceptEdits mode; in Manual mode the edit asked for approval. | live.md:143, :146; review.md:135 |
| O9 † | S:40 | SEC-1 "runs as the person on every agent tool call (SEC-1, reproduced and checked)" | It runs on every loom MCP tool call; the shell route's console script is not shadowed. The reproduction ran `_run`'s command line by hand, not through an MCP session. | security.md:13-15 |
| O10 † | S:40 | SEC-2 "A web page in the same browser can read the server's token" | It takes a hostile page using DNS rebinding. It was shown with a spoofed Host header from a non-browser client. | security.md:29, :33 |
| O11 † | S:40 | SEC-5 "can send what it reads anywhere" | No outbound request was made; the exfiltration is reasoned. It also needs the person to open that HTML file. | security.md:93, :97 |
| O12 | S:40 | LIVE-13 "a well-behaved Claude Code session was refused every author-only act it tried" | The session was a scripted stand-in, and it tried evasions on purpose. No author act got through, but `python3 -c` in bypass mode did write into `.loom/annotations/`. | live.md:9, :160-167 |
| O13 † | S:44 | LIVE-1 "a paper copied in by hand shows as raw LaTeX with no reason given" | The file tree says "PDF did not compile"; the reason appears only in a hover title. | live.md:40 |
| O14 † | S:44 | "four typed commands, three questions, two or more approval prompts, and a terminal left open (`live.md`, measured)" | The approval steps are as documented, not observed, because the CLI stood in for the Code tab. TeX was already installed. | live.md:253, :264 |
| O15 | S:46 | "TinyTeX with what loom needs is a 54 MiB download and 328 MB on disk" | That is the seed only, without biber or any paper's own packages. After three real papers it was 166 MiB downloaded and 407 MB on disk. | tinytex.md:20-21 (TTX-2, TTX-3) |
| O16 † | S:46 | "produces the same words" | Two review fragments repeat their last line under TL 2026, a latent loom bug. | tinytex.md:24 |
| O17 † | S:46, P:90 | "four, eight and twenty rounds" | The rounds were counted from a minimal base, each paper starting where the last left off. With the seed and a preamble preflight, relloc needs about six. | tinytex.md:66, :76 |
| O18 † | S:46 | "every xy diagram in one test paper lost its arrows and PDF figures became broken images" | Only one diagram was compared side by side, and there was one PDF figure (`quiver.pdf`), referenced from four fragments. | tinytex.md:110-111 |
| O19 † | S:26 | gate Quiet: "A third or less of what Review draws" | This mixes two measures. Of what Review counts, 33 % and 72 %; of the rows it draws, 17 % and 13 %. Line 82 has it right. | review.md:12 |
| O20 † | S:52 | "stated the boundary correctly" | Nobody graded this. The model said "I can write in three places", fewer than the orientation allows. | small-model.md:27; assets/ai/orientation.md:29 |
| O21 † | S:52 | "the project's server starts" | The trial passed loom's server and settings in explicitly. A project's own server stays "Pending approval" until the folder is trusted. | live.md:9, :91 |
| O22 | S:54, P:91 | "Claude Code ignores every permission rule loom wrote"; "applies none of loom's rules" | Shown for the 55 allow rules only. Nothing was reported about the 54 deny rules, and only the CLI was tried. Decision 1 rests on deny, so this needs a check, not an assertion. | live.md:93; claude-code-docs.md:20 |
| O23 † | S:58 | "At 760 pixels wide, the size of a browser beside an agent app on a laptop" | The break at 760 px is reproduced (WALK-32). That pilots will work at that width is reasoned. | register-notes.md:177 (d.18) |
| O24 † | S:58 | "The first page a newcomer sees is a README written for loom's developers." | That is the showcase. A new quilt opens on its own README, which teaches CLI commands (LIVE-3). | walk.md:150; live.md:63 |
| O25 † | S:64 | "97 agent names worked on it in four days (CUT-1, measured)" | 97 is the number of distinct names in the 11-09..13 session's transcript, not a count of names that edited the copy. | cuts.md:33 |
| O26 † | S:66 | "Markdown has no undo" | Undo exists with `track_edits` on, which is off by default. | quant-findings.md:51 |
| O27 † | S:72 | "(INST-9, INST-10, read)" | INST-10 is a proposal, not a reading of today's code. "Never run against Overleaf" comes from documentation (WQ-16). | register.md:659-660; install.md:99 |
| O28 † | S:74 | "nothing notices the paper's statement changing unless the result was accepted" | `loom history` noticed the change at once. What missed it were `loom status` and the skills' checkers. | lean-trial.md:15 |
| O29 † | S:74 | "ran the collaborator's skills on one proposition" | Two lemmas were worked. The 20 minutes is `sh-0007` with the full ceremony; `sh-0006` took about 10 minutes without freeze, graph or seal. | lean-trial.md:12 |
| O30 | S:84 | "(`check-changed.md`, measured)" and the worst cases | This was simulated over replayed history, not measured from a running loom. The figures leave agent copies out. With copies in, relloc's list has median 7 and worst 333. Without them, Changed shows almost nothing of what agents rewrote on relloc (CHG-4). | check-changed.md:3, :21 |
| O31 † | S:88-90 | "each confirmed on `main`", including the bridge's selection and the hermetic TeX | The selection is dropped in documents built from included files (LIVE-10) and is unverified in Markdown (QF-W3). Hermetic TeX was read in code, not run. | live.md:115-124; quant-findings.md:68 |
| O32 † | C:7 | "the agent layer is generated from one table" | Only the MCP tools, the permission files and the references are generated. The orientation, rules and modes are written by hand. C:74 has it right. | core.md:104 |
| O33 † | C:15 | "viewer source under `arras/src/` \| about 40,000 lines" | 39,796 includes 3,752 lines of `*.spec.ts`. Source alone is 36,044, the figure the 0.42 ratio on C:19 uses. | `git ls-files arras/src \| xargs wc -l` |
| O34 † | C:20 | "729 of 899 under loom" | 729 counts 61 hand-written quilt sources. The generated or copied files are 668. | `git ls-files loom/tests/quilts` |
| O35 | C:26 | "A prototype removed the two largest avoidable costs and measured what is left" | The spike made six changes. The shares are of the build with those changes applied, from one run at load 31. | spike-speed.md:16-24, :42 |
| O36 | C:28, C:91 | "Cache keys are too broad … narrow the cache keys" | Only the page numbers should come out. Narrowing the per-file hash would serve stale line numbers to save ~1 s. Change 4 also needs a preamble check that covers `\autopageref`, and its first build remakes every snippet (183 s, then 318 s on relloc). | spike-speed.md:70, :76, :101 |
| O37 † | C:38 | "`import` names three" | Two commands are named `import`. CORE-8's third is `library add`. INV-12, cited here, supports nothing in the sentence. | core.md:185 |
| O38 † | C:44 | "Data at module boundaries is mostly untyped dictionaries, 422 of them" | 422 is the number of source lines that contain `dict[str, Any]` anywhere. Neither "at boundaries" nor "mostly" was measured. | core.md:297 |
| O39 † | C:46 | "a build, a vendoring step and a restart" | Vendoring is optional: `LOOM_ARRAS_BUNDLE` skips it. The real fault is that there is no hot reload. | viewer.md:322 |
| O40 † | C:59 | "A third of the unit items police terminal output. `test_output.py` runs every case twice" | The file is 30 % of the items, and it runs 372 of 395 cases twice. 210 of its cases are `unchanged` checks that guard the person's files, and CUT-10 keeps them. | tests.md:11, :96, :129; cuts.md:177 |
| O41 † | C:61 | "pushed red five times in nine days, from fonts, files that exist only on the author's machine, and a change of TeX Live year" | Two of the five were a real break that local runs did not show (`section-drafts.e2e.ts:33`). The causes of two more are not given. | tests.md:78-84 |
| O42 † | C:62 | "generated quilts churned more lines than hand-written source" | The churn is in the demo copies (98,730 lines), not the generated quilts (7,556). | tests.md:122 |
| O43 † | C:63 | "One unit test fails on any untracked file" | It fails only on untracked files under `loom/src`, `loom/tests/quilts` and `arras/src`. | loom/tests/unit/test_tracked.py:12 |
| O44 | C:63 | "enough to make timings meaningless" | The reports say that comparisons made close together, and all counts, are trustworthy. C's own 2.4 s and 0.03 s are comparisons of that kind. | spike-speed.md:7; speed.md:3 |
| O45 † | C:67 | "An agent that follows `AGENTS.md` honestly reads about 57,000 words" | 57,000 is everything AGENTS.md lists. It says to read them as the work needs; the honest minimum is about 5,700. | process.md:27; AGENTS.md:5 |
| O46 † | C:67 | "Plans, reports and the frozen decision records are 87 % of `docs/`" | The 87 % includes long prompts. Plans, reports and the frozen records alone are 83 %. C:22's figure is right. | `wc -w` per directory |
| O47 † | C:67 | "none uses the word 'understanding'" | The shipped modes do: `modes/question.md:3` and `modes/ingest.md:31`. | `grep -rin understand` |
| O48 † | C:86 | "the fourteen or so planned packages that add an endpoint" | Ten packages add one: A1, A4, A7, A10, I4, O1, L-D, L-G, S2 and F5. Fourteen is register-notes f's list of packages that claim `render/api.py`, which includes X2 itself and two that only hide things. | register.md:812; register-notes.md:229 |
| O49 † | C:87 | "the most frequent conflict between sessions goes" | No report ranks conflicts. By commit count, vendoring (33) is below fixture (56), quilts (44), demos (42) and CLI-reference (40) churn. Where vendoring happens is still open (a.27). | tests.md:113-118 |
| O50 † | C:76 | "Append-only records … which is what makes the fixes below cheap" | DOOR-8 says records must change shape for the door, and the door is 6-7 sessions. | spike-door.md:147-153 |
| O51 | P:41, P:55 | Critical: "agents … cannot write them"; decision 1: agents "may not write" the person's documents | Deny stops Claude Code's own Edit tool. A subprocess in bypass mode wrote past it (LIVE-13). Codex ignores deny (ATT-11, CUT-7 condition 1). Deny in an untrusted folder is untested. The Safe gate's "either refused or shown" is the accurate form; use it in both places. | live.md:165; register-notes.md:56 (a.44) |
| O52 | P:91 | "Subagents share one connection and one name" | This is documented for a subagent named by string reference; one defined inline gets its own connection. Nobody observed it. | claude-code-docs.md:15 (DOCS-9); cuts.md:132 |
| O53 | P:103 | "Twenty minutes of agent time per lemma in the trial" | That was one easy lemma with the full ceremony, and every decision a person makes was simulated. When Mathlib lacks a definition, the old estimate of hours still holds. Write "one easy lemma took twenty minutes". | register-notes.md:64 (a.52), :179 (d.20) |
| O54 | P:27 | "The anchoring harness puts no record on the wrong block across its seven papers" | The safe design still put 15 records on the wrong block; only verify mode put none. Say which mode the gate means. | check-labels.md:5 |

### Stale

| # | where | as written | what is wrong, and the correction | source |
|---|---|---|---|---|
| T1 | S:25 | gate Fast: "Under a second on the showcase; nine to fifteen seconds on relloc" | Write "Under a second on the showcase; 12-21 s on relloc for a new word (median 15.75 s, loaded machine); the cheap fixes reach about 5-6.5 s". | spike-speed.md:9, :34, :40 |
| T2 | S:78 | "nine to fifteen seconds, median 11.75 (`speed.md`, measured at load about 4)" | The audit alternated two words, so after two trials TeX came from its cache. With a word never written before, the baseline is 12.0-20.9 s, median 15.75 s, at load 4.3-13.8. | spike-speed.md:9, :34 |
| T3 | S:78 | "37 % of that is re-anchoring annotations" | The 37 % was of a 17.6 s cached build at load 15, not of the five-second floor. The duplicate costs 2.4 s of an 11 s save build (22 %). | spike-speed.md:48; speed.md:48 |
| T4 | S:78 | "Writes from the viewer answer after a full rebuild, five to six seconds" | Measured at 5.1-6.7 s across both runs. Answering first took 0.03 s in the prototype, but broke 16-17 tests and the viewer's assumption that an answer means the page is current. | spike-speed.md:37, :64; speed.md PERF-8 |
| T5 | S:78 | (cause of the per-save re-renders, missing) | The 63 blocks re-rendered on every save come from the per-file text hash, not from the page digest PERF-2 named. | spike-speed.md:70 |
| T6 | S:30 | "because a comparison of text and not a record decides whether an edit is already in the file (SAFE-1)" | This holds for loom's own double writes. But 14 of 24 double writes are text the person or an agent typed in, which no record could know about. The fix there is judging "taken" at the edit's own place. | spike-door.md:5, :135 |
| T7 | C:84 | change 1: "SAFE-12; a prototype is testing it"; buys "closes the text-damaging faults" | spike-door has reported. The door closes SAFE-2, 3, 5 and 10 for the writers it routes, and loom's own double writes. SAFE-4, SAFE-8 and three of SAFE-1's five shapes need placement fixes that are not the door. Restore of CRLF files is only partly fixed. Random-sequence damage fell from 105 to 5 of 200. A careful version is 6-7 sessions. | spike-door.md:5, DOOR-1, DOOR-19 |
| T8 | C:7, C:40 | "no single path for writing a person's file, which is where the damage comes from"; "This is the cause of the faults in `state.md`" | Only part of the damage. SAFE-4, SAFE-8, three SAFE-1 shapes and every anchoring fault in S:36 are misreadings of text, not writes outside a door. | spike-door.md:5; check-labels.md:5 |
| T9 | S:7, C:3 | "the register says which report holds it" | The register predates eight reports: security, tinytex (listed as "Pending"), check-labels, spike-door, check-changed, explore, spike-speed and claude-code-docs. SEC, EXP, KEY, DOOR, FAST, CHG, TTX and DOCS ids have no rows. | register.md:7 |
| T10 | P:61 | decision 8: "Whether a large quilt shows source first and typesets after is decided by measurement in the Speed workstream." | It has been measured. Source first delays the typeset block (median 23.7 s against 15.4 s) unless a follow-up publishes the one fragment, which `build()` cannot do. What is left is a design decision, about 3-4 sessions. | spike-speed.md:60, :102, :113 |
| T11 | S:7 | "twenty-seven reports under `raw/`" | `raw/` now holds 29 files with the red team's, 30 with this one. Write "twenty-seven investigators' reports". This one is caused by the red team, not the author. | `ls raw/` |

### Unsupported

| # | where | as written | what is wrong, and the correction | source |
|---|---|---|---|---|
| U1 | P:81 | "A session for this is already proposed." | No report says so. It is a note about the study's own process and will go stale. Delete it. | security.md (no mention) |
| U2 † | C:46 | "which the author retired as a goal on 9 November (VIEW-12)" | VIEW-12 carries no date, and no study source gives one; the principle entered the repository on 10 November (b84dcee5). The clause also narrates history. Delete it. | viewer.md:392-394; `git log -S"The viewer is part of loom"` |

### State.md's Fast section, corrected in full

Replace S:78 with:

> On the showcase quilt a save reaches the viewer in under a second (0.3-0.9 s). On a copy of relloc, saving a word never written before takes 12 to 21 s to be seen, median 15.75 s (`spike-speed.md`, measured at load 4-14); the audit's 9-15 s (`speed.md`) alternated two words, so TeX came from its cache. Every publication on relloc costs at least five seconds even when nothing changed (PERF-1). Inside a save's build, re-anchoring annotations whose words are gone runs twice, and the second run costs about 2.4 s of 11 s (FAST-2). Two TeX runs sit on the save path, one of them for Review's comparison preview (PERF-2). Each block's cache key hashes its whole file, so a save re-renders every block of the edited file, 63 in relloc's draft (FAST-7). Each key also carries every document's page numbers, so one moved page break re-renders all 2,384 blocks with about 50 TeX runs (PERF-3, FAST-7). A cold start on relloc served nothing for about eight minutes, and the typeset draft only after eighteen (PERF-6). A person with no loom author name set pays for 609 calls to git per build, 28-38 s of a build on the loaded machine (PERF-5, FAST-4). Writes from the viewer answer only after a full rebuild, 5.1-6.7 s on relloc (PERF-8). In the exploring journey, the first second of typing after marking words was lost because the mark waits for that write (EXP-3, 1.3-1.5 s on the showcase).
>
> A prototype of the cheap fixes (`spike-speed.md`, `spikes/speed.patch`) brought the median to 11.83 s at two to three times the load. It puts first sight at roughly 5-6.5 s at the audit's load, not the 3-4 s the audit predicted. Re-anchoring once and caching the git name are safe as they are. Taking page numbers out of the keys is safe with a preamble check, and turned a page shift from 2,384 blocks into one. Publishing before TeX delayed the typeset block (median 23.7 s against 15.4 s). Answering a write first took 0.03 s, but broke 16-17 tests and the viewer's assumption that an answer means the page is current. Under two seconds needs an incremental build. Every timing here was taken on a shared machine at loads of 3 to 50: the counts are exact, the seconds are soft.

And S:25's last cell becomes "Under a second on the showcase; 12-21 s on relloc for a new word (median 15.75 s, loaded machine); the cheap fixes reach about 5-6.5 s".

## 2. Marks of confidence

Sentences that read as verified when they are not, beyond the rows above:

- **The walkers were agents.** S:23, S:58 and P:30 call them first-time users. They were an investigator playing a postdoc and Haiku, and the weaker one used the first walker's browser driver (register-notes.md:237). The Legible gate is then checked by "fresh agents". Say once, in both documents, that agents stand in for people and the pilots are the real test.
- **The live trial used a scripted stand-in for the model.** S:52's "measured" (LIVE-9, LIVE-14), S:40's LIVE-13 and S:44's command counts read as a real agent's behaviour. P:29's Attachable check ("one plain request: the agent's comment appears") cannot be run until the author's queue item 4 is done; say so in the gate.
- **Exploring, Lean and check-changed carry no limit.** S:68's exploring paragraph has no mark, and EXP has no rows in the register. S:74's Lean trial ran on a Mac that already had Homebrew and git, and its three "independent" audits were subagents of one session (register-notes.md:218). S:84's check-changed is a simulation over replayed history, not a measurement.
- **Wrong marks on two claims.** S:34's "(checked)" covers a count that matches no source (41 against 34). "(PERF, checked)" covers a hazard the code already guards against (O5).
- **Shell escape is untested under loom's own TeX.** S:40's TeX safety was shown on TL 2024 with its stock configuration (W18). It must be rechecked under loom's own TinyTeX, whose `texmf.cnf` differs (tinytex.md:39).
- **codebase.md carries no marks at all**, so every sentence reads as checked. These rest on one agent's estimate or reasoning:
  - "a day, mechanical" (C:85) is CORE's estimate.
  - "an everyday lane under three minutes" (C:89) is an estimate of 60-90 s unloaded (tests.md:221).
  - "vendoring only at release or in CI" (C:87) is an open decision (register-notes a.27), presented as settled.
  - "agents search all of it as though it were current" (C:67) is PROC's reasoning, not an observation.
  - "None of these needs a rewrite" (C:7) is the lead's judgement.
- **codebase.md's timings come from a loaded machine.** C:26-30 and C:91 were taken at loads of 4 to 31; C:63 then calls such timings meaningless.
- **The plan:**
  - P:91 "Until the folder is trusted Claude Code applies none of loom's rules" is CLI-only and covers the allow rules only (O22).
  - P:91 "Subagents share one connection and one name" comes from documentation (O52).
  - P:103's twenty minutes is one trial with simulated decisions (O53).
  - P:94 "Usable at 760 pixels beside an agent app" is a target resting on a reasoned width (d.18).
  - P:65 decision 11, "the smallest cut as the trial amended it", inherits the trial's simulated decisions.
  - P:32's Fast thresholds are honestly marked provisional.

## 3. Writing rules

- **Hard wrapping: clean.** `python3 scripts/checks/hardwrap.py` printed "hardwrap: ok", but only because its `SKIP` pattern excludes `docs/plans/` and `docs/reports/`, so it never judged these files. It does read untracked files, but these three fall under that exclusion. Applying the checker's own `markdown_pairs` function to the three files directly, read-only, found 0 wrapped pairs in each.
- **History narrated rather than the current state:**
  - S:30: "The two fixes merged in the week before the study did not close the underlying fault". Write "At 71621877 Keep can still write an edit twice (REV-3)".
  - C:46: "the static, host-neutral reader it began as, which the author retired as a goal on 9 November".
  - C:58: "both bugs of the week before the study were found in the author's own quilt". The past-tense "Nothing tested" and "No test ran" read as fixed; the test is still not in `loom/tests`.
  - C:84: "a prototype is testing it".
  - P:47: "were each proposed for hiding and stay".
  - P:81: "A session for this is already proposed".
- **Unbuilt read as built:**
  - S:46 "A small private TeX works": it worked by hand beside loom; loom has no private TeX (`tex/private.py` does not exist). Write "A private TinyTeX, tried by hand, works".
  - P:17 "A quilt carries a format number … and an upgrade never deletes" sits among v0.1's properties, which is fine. But no workstream owns `cli/upgrade.py`, and today `review_queue._data` resets silently (CORE-7). Give "an upgrade never deletes" an owner and a test, or drop it.
- **Flat "never":** S:20 restates the Safe gate as "Loom never damages … and every write is undone", while P:27 says "does not damage … each write is undone in one step where it happened". Quote the plan. No flat "loom never X" about open territory was found in P.

## 4. Consistency

| # | between | the problem | fix |
|---|---|---|---|
| K1 | P:42 against P:51 | The tiers put "Zotero through a Better BibTeX export" under Highly desirable, while the author's decision two screens later says "Zotero a nice-to-have". | Move it to Nice to have, or ask the author. |
| K2 | P:30, S:23, S:58, register-notes g | Three different lists of the walkers' shared failures: P says "the five", S names five that include tasks 2 and 14, and the notes name six (3, 4, 7, 12, 14, 15). | Use the notes' six by number everywhere. |
| K3 | S:40, P:41, P:81, security.md | "Five" security items name different sets. S lists SEC-1, 2, 3, 5 and 4. security.md's five fixes, which P follows, are SEC-1, 2, 3, 5 and 6b, with SEC-4 a stated limit. C never mentions SEC-1 or SEC-2 although its verdict calls the code healthy and C:30 describes the same `python -m loom` call that SEC-1 exploits. | Name the five ids in P and S; add a security line to C's verdict. |
| K4 | S:20-26 against P:27-33 | S restates every gate in different words, and in places a weaker bar. Installable drops "no TeX and no Homebrew … diagrams and figures"; Attachable drops "is told when it writes"; Complete says "with no command" where P says "using only the viewer, their editor and plain words"; Fast is "Save in your editor, see it in loom" where P adds "at any size, and nothing typed is lost". | Copy P's "passes when" column into S verbatim. |
| K5 | P:126 against P:13 and P:30 | Pilots report "an issue with what `loom doctor` prints", but no human types a loom command and no screen shows one. | Give doctor's output a place in the viewer (INV-24 proposes Settings) and point pilots there. |
| K6 | P:32 against P:44 and spike-speed | "First sight within 5 s" sits below the 5-6.5 s the spike expects from every cheap fix, so it probably needs part of the incremental tail (FAST-10 b-c, 4-6 sessions), which P puts under "Not needed yet". "Typeset within 20 s" is beaten by today's code (median 15.4 s) but missed if change 5 lands without a one-fragment follow-up (23.7 s). | Either set the thresholds from spike-speed, or move the tail and the follow-up into Speed. |
| K7 | C:91, P:92, spike-speed | C says "narrow the cache keys", P says "page numbers out of the cache keys", and the spike says only page numbers, never the per-file hash. | Use the spike's wording. |
| K8 | C:63 against C:26-32, C:91 and S:78 | C calls the timings meaningless and then relies on them; S and C also quote different baselines (S the audit's 9-15 s, C the spike's 6.3-6.7 s and 2.4 s). | Drop "meaningless"; give both documents the spike's figures. |
| K9 | P:74, P:82 against DOOR-18 and KEY-13 | Ownership collides in four places. P gives `render/api.py` to Foundations, but the door needs `_change`, `_reopen`, `_history` and the endpoint list, and anchoring needs `render/api.py`, `mcp/`, `cli/review.py`, `cli/suggest.py`, `links.py`, `since.py` and `review_queue.py` (Review's). The door adds a line to `doctor.py` (Install's). Foundations and Safe both claim `tests/unit/test_write_safety.py`. Safe's list also omits `records/snapshots.py`, `history/steps.py`, `tasks.py`, `config_edit.py`, `adopt.py`, `cli/suggest.py`, `records/locate.py` (new), `records/log.py` and `records/annotations.py`. | Take Safe's list from DOOR-18 (spike-door.md:230) and KEY-13 (check-labels.md:324-331), and say how Safe edits `render/api.py` before the registry exists. |
| K10 | P:55, P:41 against owners | Decision 1's default needs `cli/quilt.py:39-42` and `scan/quilt.py:66` (register-notes a.1: both must change), and no workstream owns either. `scan/quilt.py` is also where Speed's git-name cache (spike change 3) and the name asked once (`save_author`) live. | Give `cli/quilt.py` and `scan/quilt.py` one owner, probably Safe. |
| K11 | P:41-43 against the workstreams | Five tier items have no owner. "An agent activity page" and "Zotero through a Better BibTeX export" (both Highly desirable). "Annotations and suggested edits on Markdown" (Critical): Learner says they wait for Safe, and no After-Safe workstream takes them. "The manifest compressed" (Nice to have). The viewer's one-step undo: DOOR-18 step 5 puts it in Safe, editing `arras/src/lib/review/history.svelte.ts`, which sits inside Review's `review/`. | Name an owner for each. |
| K12 | P:101 against P:67 | Review's done-when reads "accept an AI's change and undo it in two actions", using Accept for Keep, the confusion decision 13 and walk task 7 name. | Write "keep an agent's suggested edit and undo it". |
| K13 | P:41 against P:27 | Critical says agents "cannot write" the person's documents, while the Safe gate says "either refused or shown". | The gate is right (O51). |
| K14 | P:94, P:80 and C:87 against register-notes b | Three open decisions are settled silently: b.17 (links open in the same pane: Legibility's cell), b.20 (the operations registry before v0.1: Foundations), and a.27/b.26 (where vendoring happens: C:87). | List them under Decisions, or leave them open. |
| K15 | P:61 against register-notes b.8, INST-8, TTX-8 | Decision 7's open question covers only diagrams and PDF figures. Without Homebrew there is also no poppler, so no page text for agents, no words under marks, no import identity test (INST-8; pypdfium2 is the proposal). On 7 March 2027 a TL 2026 tlmgr refuses the live repository, and on-demand installs stop for every pilot unless loom has pointed it at `tlnet-final` (tinytex.md:151). | Add both to Install's traps. |
| K16 | P:90 against INST-18 and register-notes a.17 | Install's cell omits the one constraint read in code: viewer preferences live in localStorage, per origin with the port, so each quilt needs a stable remembered port. | Add it. |
| K17 | P:29, P:45 against register-notes b "Already made" | The author kept "Use with Codex", `codex://` and `.agents/skills/` (vendor-neutral where cheap). P mentions only "Use with Claude", and its Detracting "Setup entries for agent apps nobody uses" could be read to cover Codex and Gemini. | Name the entries to hide (desktop chat, LM Studio, Zed, JetBrains: CUT-13) and say Codex's stay. |
| K18 | S:104 against P:113 | S lists "whether project hooks run" in the Code tab; P's queue item 1 omits it. | Add it to item 1, or drop it from S. |
| K19 | S:7, C:3 against register.md:7 | Both call the register the merge of every report's findings, but it covers 19 of 27 (T9). | Say which reports it holds. |
| K20 | C:7, C:40 against S:36 | C names the missing single write path as the cause of the damage; S's anchoring faults have a different cause (T8). | Say "most of the write faults", not "the damage". |

## 5. Pointers

- **Every report, harness and patch the three documents cite exists.** That covers all `raw/*.md` named, `spikes/labels.patch`, `spikes/one-door.patch`, `spikes/speed.patch`, `safety-harness/` and `safety-harness/keep/test_write_safety.py`, `docs/plans/0.31-your-changes-mathematics-first.md` (which does say "a person need not review their own changes"), and register headings 1-13.
- **Every existing code path named exists.** `Column.svelte` is `arras/src/lib/shell/Column.svelte`; the viewer's `review/` is `arras/src/lib/review/`; `loom.sty` is `loom/src/loom/assets/loom.sty`.
- **P's relative paths resolve only from the study directory.** P cites `raw/…` and `spikes/…` relative to `docs/reports/v0.1-study/` without saying so; from `docs/plans/` they do not resolve. Once (P:27) it uses the full path for `safety-harness/`. Say once where `raw/` and `spikes/` are.
- **Paths missing without a "(new)" mark:** `scripts/install.sh` (P:90) and `assets/lean-skills/` (P:103). `src/app/` (P:90) is ambiguous: under the register's convention it means `loom/src/loom/app/`, and it is new. The paths marked new (`writes.py`, `presence.py`, `tex/private.py`, `records/formal.py`, `cli/formal.py`, `formal/`) are correctly absent. `scripts/regen` is a goal.
- **"the Markdown renderer" (P:95) names no file.** Candidates I found: `loom/src/loom/raw_html.py`, the sanitiser, which SEC-6a also touches, and `arras/src/lib/workspace/items/FileItem.svelte`, unconfirmed. Name the files.
- **Most harnesses live in a temporary directory.** Only `safety-harness/` and the three patches are in the repository. These all sit in `/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/` (20 GB):
  - the walk drivers;
  - check-changed's replay scripts (`scripts/replay.py`, `simulate.py`, `units.py`);
  - spike-speed's tools (`seen.cjs`, `builds.py`, `stale.py`);
  - live.md's driver (`driver.mjs`, the fake API);
  - explore's setup.

  P:30, P:31, P:32 and P:33 point to reports whose harnesses will not survive. Copy the scripts, not the data, into the repository, as was done for `safety-harness/`.
- **The anchoring harness needs papers that are not in the repository.** `spikes/labels.patch` carries the harness but not its seven papers: five from the main checkout's gitignored `tests/fixtures/`, relloc's `draft3.tex`, and quant's solutions (check-labels.md:27-34).
- **Ids that do not resolve:**
  - S cites SEC-n, EXP-n and CUT-14 as if the register held them (T9). SEC and EXP have no rows; CUT-14's defects appear only as CUT-14a-d.
  - S:32 "(WALK, reproduced)" carries no id.
  - C:60's TEST-9 should be TEST-10 (W20).
  - S:34's "PERF" is PERF-copy.

## 6. Editing the plan for efficiency

### Where a builder will have to guess

1. **P:30 Legible.** Which five tasks? Which one of eighteen may stay failed? Write: "tasks 3, 4, 7, 12, 14 and 15 of `raw/walk.md` succeed for both walkers; the stronger achieves at least seventeen of eighteen, task 17 included."
2. **P:33 Quiet.** "Nine rows in ten" of what? Rows drawn or rows counted, on which copies, at what moment? The 25-row replay also depends on CHG-7's grouping rule: one row per Markdown or other file, and one row for a file where more than 20 blocks moved at once. Put that rule in decision 2, which now says only "a bulk arrival as one row".
3. **P:27 Safe.** The harness counts a refused concurrent Keep as damage; 5 such cases are what the prototype left (DOOR-2). Say whether they count. Name the anchoring mode, which is verify mode (O54).
4. **P:32 Fast.** "First sight" and "typeset" are undefined; the spike defines both (new words in the DOM; the TeX-made fragment). Name the edit: a word never written before. Name the load: P says only "a quiet machine".
5. **P:31 Complete.** The "three scripted journeys" have no scripts and no owner. Say which workstream writes them.
6. **P:41 Critical.** "Problems by class": the classes are undefined, and a.6 is open on the borderline codes. "The cheap speed fixes": say which (changes 1, 3 and 4). "Writes that answer at once" needs the design FAST-6 asks for; name the option chosen.
7. **P:61 decision 8.** The measurement is done (T10); state the design question instead.
8. **P:84.** "Review's rebuild" means its redesign. "Suggested edits on Markdown wait for Safe" without saying who builds them after (K11).
9. **P:95 and P:90.** Name "the Markdown renderer"; fix `src/app/`.
10. **P:72.** "Sizes are the study's estimates" promises sizes that only Safe's row gives. Either add them (spike-speed.md:105-117 sizes Speed; library.md and lean-trial.md size theirs) or delete the sentence.

### Said twice, or carrying nothing

1. **P:3, middle sentence.** Delete "It says what v0.1 is, … the workstreams that do it." It is a table of contents in prose (−33 words).
2. **P:5.** Delete it. AGENTS.md has the rule, and "Implementation" says where results go (−31).
3. **P:51.** Replace the author's list with: "Made by the author: everything under 'What v0.1 is'; Overleaf over git with no zip path; Zotero a nice-to-have and every other library fix a must; formalization built in v0.1; a person need not review their own changes (plan 0.31)." Six of its eleven items restate "What v0.1 is" or P:19 (−30).
4. **P:53.** Replace with "Recommended by the study; built unless the author strikes one." Most decisions cite no evidence, so "from the evidence cited" is not true (−12).
5. **P:64, decision 10.** Delete it. The tiers and the Overleaf row say the same (−9).
6. **P:47.** Delete it, and add "(relloc relies on it; CUT-1)", "(CUT-3)" and "(CUT-6)" to decisions 3, 4 and 5 (−20 net).
7. **P:72, second and third sentences.** Delete "Each plans its own steps; this plan gives …" and the sizes sentence (−38).
8. **P:74.** Replace with: "`render/api.py` is Foundations' until the operations registry lands; until then Safe edits `_change`, `_reopen`, `_history` and the endpoint list (DOOR-18) through Foundations' review. A file two workstreams need is listed under both, the earlier first." The other four sentences repeat the owns columns, and the new text fixes K9 (−40 net).
9. **P:101.** Delete "Never guess an author from timing." Decision 2 says "an author named only from loom's records" (−7).
10. **P:31.** Shorten the formalization clause to "one lemma end to end (Formalization's done-when)" (−12).
11. **P:105-107, "Last: the gates".** Fold this into the author's queue, item 8: "Before shipping: every gate's check, the clean-Mac install, the Code tab, the Overleaf mirror, Codex and Gemini by hand, the introduction, and the pilots and how they report" (−35).
12. **P:128-130, "What waits".** Delete it; it repeats the "Not needed yet" row. Add "splitting the largest modules and deleting what v0.1 hid" to that row (−45).

### Cells too dense to act on

- **P:41 Critical tier** is 159 words and 17 items in one cell.
  - Best fix: move every Critical and Highly desirable item into the row of the workstream that builds it, marked "(highly desirable)" where it is. Keep only Nice to have, Not needed yet and Detracting in the tier table. Each item then appears once, and the five unowned ones (K11) must get an owner (about −250 words).
  - Smaller fix: write "Critical: whatever the seven gates check, plus sensible library keys and a library page" (about −130).
- **P:82 Safe's traps** (185 words) should become three bullets: the door, anchoring, also here. Add "Register 1", which is the only heading not cited. Add that the register's S0 and S7 predate spike-door and check-labels and lose to them.
- **P:92 Speed's traps** (121 words, two of them errors) should read:

  > Register 6 and `raw/speed.md` predate `raw/spike-speed.md`; where they differ the spike wins (`spikes/speed.patch`). Land as they are: re-anchoring once per build with its memo, and the git name cached. Land with a preamble check that covers `\autopageref`: page numbers out of the keys; its first build remakes every snippet. Keep the per-file text hash. TeX off the save path delays the typeset block unless a follow-up publishes the one fragment (3-4 sessions). Answering writes first breaks the viewer's contract and 16-17 tests: design it first. With all of this, first sight is about 5-6.5 s at load 4. First open: the default document before digests and previews. The bench runs with compiles on. Any change to `render/`, `scan/` or `tex/` makes every user remake every preview once.

  Its owns list also needs `scan/quilt.py`, `section_drafts.py`, `render/snippets.py`, `render/fragments.py`, `render/compiles.py`, and arras `write.ts` with its callers (spike-speed.md:109-115).
- **P:103 Formalization's traps** (158 words) should become bullets.
- **P:90 Install's traps** gains three warnings: the TL 2027 freeze, poppler (K15), and stable ports (K16).

### Does the reading path work? Two workstreams checked

- **Safe.** P's row does not cite a register heading. Register §1 predates spike-door and check-labels.
  - It carries S0 as SAFE-12 described it: the journal in `.loom/writes`, act ids derived from content. DOOR-7 and DOOR-13 correct both.
  - It carries S7, "search a lost quote across the file, days (2-3)". KEY-5 says never to build that, and KEY-13 sizes the safe design at 4-5 sessions.
  - P's cell does carry those corrections, but a reader who meets §1 first gets no warning that the later reports win.
  - The cited reports hold everything the cell assumes: DOOR-17/18 give the landing order and files, KEY-13 the design, order, files and size.
  - "Also here: the quilt's format number" is register S4 (CORE-7), which owns `review_queue.py`, `cli/upgrade.py` and `cli/quilt.py`. "These two names are one person" is register S8 (QF-25), which owns `scan/quilt.py`'s `save_author` and `.loom/looked/`; CHG-13 adds that both quilts hold two looks. Neither set of files is in Safe's owns list.
  - Verdict: enough to start; not enough to stay in lane (K9, K10).
- **Speed.** Register §6 states the stale 3-4 s target and P3 "per-label numbers" (a day or two). The spike instead landed "keys without page numbers" and split the digests out as 4b.
  - `raw/spike-speed.md` holds every assumption in P's cell: FAST-1 to FAST-10, which changes to land, sizes and files.
  - But the cell never says the spike supersedes the register and `speed.md`, and two of its sentences misread it (W28, W29).
  - Its owns list misses six files the spike names.
  - Verdict: the evidence is there, the cell is not.
- **Install, briefly.** Register §2 still carries I2's "recompile once" and INST-5's sizes, which TTX-11 refutes, but it does hold INST-18 (ports) and INST-8 (poppler). P's cell surfaces neither, and tinytex's TL 2027 freeze is in no cell.

### How much can go

The cuts above total about 580 words: 15 % of P's 3,880. The tier restructure supplies about 250 of them. The missing warnings proposed here add about 120 back, so the net cut is about 12 %. The plan has little pure redundancy left. A full quarter would mean cutting the statement of purpose, the pilots section or decision bodies, and I would not. If the length must fall further, a better lever is to move the gate checks' details (P:27-33, 540 words) into the workstream rows that own them, leaving the bar as a seven-line table of "passes when".

## 7. Corrections not applied to state.md and codebase.md

Every row of section 1 that concerns `state.md` or `codebase.md` is applied in them, the † rows after re-opening their sources. What was not applied, and why:

- **Every row about the plan.** W3, W27-W29, O17's plan half, O51-O54, T10 and U1, and the consistency items that touch only the plan (K1, K5, K6, K9-K17, and the plan halves of K2, K7 and K13), are left to the plan's rewrite.
- **Gate wording now follows the current plan.** `state.md`'s bar table quotes P:27-33's "passes when" wording as it stands (K4). If the rewrite changes that wording, the table must follow.
- **K18, Code-tab hooks.** `state.md` keeps "whether project hooks run" among the Code-tab questions. It is a real open question; the plan's queue should gain it.
- **The 41.** `state.md` keeps it beside the 34. A read-only grep of `~/quilts/quant/.loom` for the fixture author gives 41 lines: the 34 record lines (13 ledger, 4 notes, 2 edits, 1 inbox, 14 bibliography), plus 2 in a backup of the annotation log, 1 in a run log, 2 in stored texts, 1 in the split look's own file and 1 in a digest.
- **C:13, "about 92,000 lines, source and tests together".** Left as it is. The count also includes 2,093 lines of scripts, which is within the rounding.
- **TEST-4's red pushes.** Two of the five, 72a89691 and ec739962, have no cause in tests.md. `codebase.md` therefore names the two real breaks and lists the other causes TEST-4 gives without assigning them to pushes.
- **Length.** `state.md` grew from about 2,980 to 4,000 words, `codebase.md` from 2,210 to 2,590. The growth is mostly the replacement Fast section and the limits each trial now states: a scripted model, simulated decisions, a loaded machine, AI walkers.
