# Process and documents audit (area: PROC)

Checkout: branch v0.1-study at `/Users/isaac/dev/loom-arras/.claude/worktrees/v01-study`. Word counts are `wc -w` over the Markdown files. Nothing was installed or run except the read-only checkers `docs/work-queue/check.py`, `scripts/checks/principles.py` and `scripts/checks/hardwrap.py --all`, which report: queue ok with 25 active of 45, principles ok (6 sets, 48 principles), 144 hard-wrapped pairs remain in the repository (the check judges only added lines).

## 1. Census

| directory or file | files | words | class |
|---|---|---|---|
| `docs/design/` without the frozen records | 5 | 23,592 (README 1,246; principles 4,540; model 8,127; agents 3,884; invariants 5,795) | normative |
| `docs/design/decision-records-frozen.md` | 1 | 55,742 (360 records) | history, frozen |
| `docs/specs/` (md only) | 8 | 28,729 (manifest 9,938; write-api 6,885; dialect 3,179; diagnostics 2,663; digests 2,359; source-contract 2,040; fixture 1,145; README 520) | normative; `fixture/` is generated and copied twice |
| `docs/contributing.md` | 1 | 1,286 | normative |
| `docs/work-queue/` | 27 | 11,503 (25 items, README 1,296, closed.md 73 lines) | live backlog |
| `docs/ideas/` | 3 | 4,364 | non-normative |
| `docs/plans/` | 45 | 224,037 | history |
| `docs/reports/` (before this study) | 33 | 173,437 | history |
| `docs/long-prompts/` | 9 | 21,148 | history (prompts the author wrote) |
| `AGENTS.md`, `CLAUDE.md` | 2 | 708 + 1,211 | normative process |
| `README.md`, `loom/README.md`, `arras/README.md` | 3 | 718 + 862 + 189 | front doors |
| `loom/CONTRIBUTING.md`, `arras/CONTRIBUTING.md` | 2 | 138 + 167 | normative, stale (PROC-21) |
| `loom/docs/RELEASE.md` | 1 | about 310 | normative |
| `loom/docs/cli-reference.md` (and `mcp-tools.json`) | 1 | 12,033 | generated, committed |
| `loom/src/loom/assets/ai/` (orientation 1,916; rules 3,402; formatting 798; README 216) | 4 | 6,332 | normative, shipped to agents |

`docs/` as a whole is 132 Markdown files, 543,837 words. History (plans, reports, long prompts, frozen records) is 474,364 words, 87 percent. Everything normative under `docs/` is about 65,000 words (design 23.6k, specs 28.7k, contributing 1.3k, queue 11.5k).

How many words an agent must read if it follows `AGENTS.md:3-13` honestly: CLAUDE.md (auto-loaded, 1,211) + AGENTS.md (708) + design README (1,246) + principles (4,540) + model (8,127) + agents (3,884) + invariants (5,795) + work-queue README (1,296) + all of `docs/specs/` (28,729) + contributing (1,286) = about 56,800 words, roughly 75,000 tokens, before any code. Item 1 says "start here" and items 1 and 3 say to read the rest "as the work needs them", so the honest minimum is about 5,700 words (CLAUDE, AGENTS, design README, queue README, contributing), but nothing says which of model, agents, invariants and specs a given change needs, so agents either read everything or guess.

Proposed path at a third of the length (about 19,000 words, and 12,000 of them are the first-read set):

1. CLAUDE.md trimmed to its rules, about 500 words: the hard-wrap rule in two sentences, the docstring register, no ten-pass essay (that belongs in a release checklist). AGENTS.md rewritten to about 450 words: what loom is for (the new statement), the one reading path, the non-negotiables.
2. A rewritten `docs/design/README.md`, about 900 words, that states the purpose (understanding, AI boundary, network mirroring the head), the three surfaces, what v0.1 contains and what is hidden.
3. `principles.md`: read "The one idea" and the generated index only (about 600 words); read a principle's body when citing it.
4. `invariants.md`: read the 38 rule titles only (a generated list, about 400 words); open an entry when touching its area.
5. `model.md` (8,127) and `agents.md` (3,884): read the section for the area you touch (a section index at the top of each, about 150 words each).
6. `docs/specs/README.md` (520) first; read a spec file only when changing what crosses the boundary.
7. A single `docs/v0.1.md` of about 1,000 words replaces the work-queue README for the push.
8. `docs/contributing.md` trimmed to about 700 words: commands, the three checks that matter, how to add a test.

Total always-read about 4,000 words; on-demand reading about 15,000 words for a typical change.

## 2. Stale against the new framing

The author's statement governs: understanding why, not truth; AI-generated mathematics embraced inside a clear boundary; the network mirrors the person's head; the human front end is an application, no human types a command; loom is not a text editor; CLI, MCP and write API are three surfaces over one set of operations.

Word search: "understand" appears nowhere in `docs/design/README.md`, `model.md`, `agents.md`, `invariants.md`, `orientation.md`, `rules.md` or `README.md` (the only hit in the normative set is K3, `docs/design/principles.md:286`, "a value the command does not understand", a different sense). The purpose the author just gave appears in none of them.

| id | location and quote | what it should say now |
|---|---|---|
| PROC-1 | `docs/design/README.md:3` "Loom is a local command-line tool for mathematical research, and arras is the viewer it publishes to." | Loom is a local application for understanding mathematics deeply: open it on a quilt, drag in what you read and write, and let your own agent work in the quilt through loom's tools. |
| PROC-2 | `docs/design/README.md:7` "It treats mathematics as a graph of addressable statements" with no statement of purpose; `:11` "Loom is useful with no AI present and built to be excellent with one"; `docs/design/principles.md:11` "Loom does not require an AI. It is a complete tool for reading, exploring, drafting and reviewing on its own" | Lead with the purpose (why a result holds, not only whether), say that AI-generated mathematics and documents are welcome, and that loom draws the boundary of what an agent may change (invariants and P7). "Needs no AI" can stay as a secondary property. |
| PROC-3 | `docs/design/README.md:37` "it needs a running process for something a command could do" | The application is a running process. Replace with "it makes a person type a command or open a terminal for something the application could offer". |
| PROC-4 | `docs/design/README.md:13-21` the three people (Learner, Explorer, Author), each defined by stage; the Author "is where it began" | Keep as a test, but add the person the author now means: a mathematician trying to understand why a result holds, with AI output among the things read. The Learner's "ask an AI to clarify" is the only AI mention in the persona section. |
| PROC-5 | `docs/design/README.md:55-62` "Decided, not yet built" omits the application front end (launch, point at or start a quilt, drag resources in) and surface parity; `:62` "Later: running code" | Add the application and the three-surfaces rule as decided, with what is built. |
| PROC-6 | `docs/design/principles.md:109-111` P8 "No editor, server, model, or credential is required by any command. Every command runs from a terminal against files." | Commands are the agent and developer surface; a person never needs one. State that the same operations are reachable from the CLI, MCP and the viewer's write API. |
| PROC-7 | `docs/design/principles.md:115` P9 "reach loom through the same open interfaces (the command line, and MCP when it is built)" | MCP is built (`loom/docs/cli-reference.md:1115`); say "the command line, MCP and the write API" and name the one operation set they share. |
| PROC-8 | `docs/design/principles.md:3` and set K (`:272-300`), set T (`:212-246`) govern "how the command line is shaped ... how a person finds them" and "Terminal output" as if the terminal is the person's interface | Reframe K and T as the agent surface's quality rules; the person's equivalent is the V and A sets. |
| PROC-9 | `docs/design/model.md:138` "Arras shows what loom publishes ... It writes nothing itself ... It works offline, from a static build, on any host." | Contradicts P11 (`principles.md:121`, the viewer is part of loom) and the write API; the viewer is the front end, served by `loom serve`, and it writes through the write API. Drop "static build, on any host" or mark it a property for tests only. |
| PROC-10 | `docs/specs/README.md:24` "Never depend on the viewer for anything ... a build directory served as static files is read whole" and `:3` "what loom publishes ... and what its viewer, arras, reads there" | Same split: P11 already says the boundary is deprecated; the specs still describe a publisher and a separate reader. Keep the manifest contract; delete the "never depend on the viewer" obligation. |
| PROC-11 | `README.md:8` "the static viewer for a published quilt"; `README.md:3` "`loom` turns a LaTeX paper into a *quilt*"; `loom/README.md:3` the same; `arras/README.md:3` "A static viewer for node-based text corpora ... It knows nothing about LaTeX, about loom" | Three false statements: the viewer is not static, not independent of loom (P11), and a quilt is not one paper (model.md says it may hold several or none). The README should say what loom is for, show the application, and carry the install line. |
| PROC-12 | `README.md:10` "`loom` never needs the viewer: a quilt edited in a plain text editor loses nothing" | Loom is not a text editor and the viewer is the person's front end; say the quilt is plain files so nothing is locked in, which is a different claim. |
| PROC-13 | `README.md:62` "`loom` is released to PyPI, with arras vendored into it" | v0.1 is installed from GitHub; PyPI is later (WQ-19). |
| PROC-14 | `loom/README.md:38-59` the Quickstart is eleven commands, including `loom accept rl-0004 --proofs` and `loom digest extract Man12 ...`; `:49` ids `rl-0004` | The quickstart for a human is "launch the application and open or start a quilt". Commands move to an agents' appendix. The `rl-` prefix is a default presented as constant (CLAUDE.md pass 3). |
| PROC-15 | `loom/pyproject.toml:4` description "a tool for atomized mathematical research in LaTeX"; `:10` keywords "latex, mathematics, writing, review"; `loom/README.md:3` "A tool for atomized mathematical development" | A sentence matching the new statement; "writing" invites the text-editor misreading. |
| PROC-16 | `loom/src/loom/assets/ai/orientation.md` (1,916 words), `rules.md` (3,402), `agents.md` | Never say what the person is trying to do (understand) or why the boundary exists; an agent that knows the purpose can choose better between "prove it" and "explain it". Add a three-sentence purpose paragraph at the head of the orientation; do not otherwise rewrite them. |
| PROC-17 | `docs/design/model.md:134` and surrounding: "The viewer's chat composer and agent launching are retired (plan 0.20.1): conversations happen in agent apps" | Consistent with the author, but the statement "agent launching is retired" now collides with "launch it, point it at a quilt": keep, but say which launch is meant. Low weight. |
| PROC-18 | `docs/design/README.md:57` "Annotating PDFs ... Not built: ... (0.30.2) ... (0.30.3)" and similar plan-numbered "not built yet" markers | A reader cannot tell which unbuilt items matter for v0.1. Each should say "hidden in v0.1" or "in v0.1". |

Weights for 1 to 13: hurts (an agent or a pilot user reads the first sentence and takes a wrong framing; CLAUDE.md's own pass 8 names this fault). PROC-1, 2, 6, 9, 11 are the ones to fix first; each is a sentence. Effort: hours for the lot. Recommendation: fix.

## 3. Rituals

| id | ritual (source) | prevents | cost per change | for two weeks |
|---|---|---|---|---|
| PROC-30 | Work-queue rows with observable triggers, cap of 45 (`AGENTS.md:19`, `docs/work-queue/check.py:15`) | an unbounded wish list | 10 to 20 minutes per item, two files; 25 of 45 used. The README's own count is stale: `docs/work-queue/README.md` says "Twenty-four active, twenty-one slots of headroom" but the table has 25 rows and the checker reports 25; the checker does not test that sentence | suspend adding; keep the checker; fix the count (PROC-31) |
| PROC-32 | Closing an item: delete file and row, one line in `closed.md` (`AGENTS.md:20`) | dead items | minutes; 73 lines | keep |
| PROC-33 | Principle names, generated index, `scripts/checks/principles.py --write` (`AGENTS.md:17`) | dangling citations | small, but "cite by name" means every comment and docstring carries a P/V/A/K letter; 48 principles to know | keep the check; stop requiring citations in new code comments |
| PROC-34 | Hard-wrap ratchet (`CLAUDE.md:5-25`, `scripts/checks/hardwrap.py`) | noisy diffs, malformed prose | near zero once automated; but 1,211 words of CLAUDE.md are spent partly on it | keep the check; trim the prose |
| PROC-35 | "(not built yet)" and **Open.** markers (`docs/design/README.md:50-53`) | unbuilt features reading as built | a sentence per feature | keep, but tag each with "hidden in v0.1" where true |
| PROC-36 | Dated invariant lines (`AGENTS.md:15`, `docs/design/invariants.md`, 38 entries, 5,795 words) | silent weakening of a rule learned from a failure | edit only when an invariant changes; each entry names guard tests | keep; the invariants are what stops agents breaking the boundary |
| PROC-37 | Plan files per phase (`docs/plans/`, 45 files, 224k words; the "plan phases in plan mode" rule is in the author's memory, not in the repository) | design drift across many sessions | 2,000 to 24,000 words per plan; 235 source files cite a plan | suspend: one `docs/v0.1.md` for the push, plan files only for work that spans more than a day |
| PROC-38 | Re-vendoring arras (`scripts/checks/bundle.py`, `loom/scripts/vendor_arras.py`, `docs/contributing.md:78`) | shipping an old viewer in a loom | a build plus a commit of a built bundle; in parallel sessions two branches vendoring conflict; the checker only warns on a `-dirty` stamp. The committed bundle currently reads `arras 4c4ba495-dirty vendored 2026-11-12T23:58:56Z` (`loom/src/loom/assets/arras/VERSION`) | keep, but vendor once per merge to main and once at release; make the release check fail on `-dirty` |
| PROC-39 | Fixture regeneration (`scripts/checks/fixtures.py`, `refresh-fixture.sh`, `gen_quilts.py`, `gen_pages.py`; `docs/contributing.md:42`) | contract drift between loom and viewer, and between three copies of the fixture | any output change regenerates three fixture copies and the demos; `gen_pages.py` needs TeX Live; a hot merge-conflict spot across parallel sessions | keep the fixture; loosen the demo copies (check at merge, not per commit) |
| PROC-40 | CLI reference generation (`loom/scripts/gen_cli_reference.py --check`, 12,033 words, `loom/docs/cli-reference.md`) | docs saying commands that do not exist | every help-text edit rewrites a committed 12k-word file; conflicts across sessions | keep as a release check; stop committing it per change if the check can run at release |
| PROC-41 | Diagnostic codes listed in `docs/specs/diagnostics.md` before emitted (`loom/CONTRIBUTING.md:6`) | codes agents cannot look up | one table row | keep |
| PROC-42 | `test_never_modifies_author_files`, `paths.py` single spelling, hermetic TeX, `test_tracked` | the boundary of what an AI may change; machine-dependent passes; CI missing untracked files | transparent | keep: this is the AI boundary in executable form |
| PROC-43 | `scripts/verify` fast / full / slots (`docs/contributing.md:24-37`, 326-line script) | broken main | full run includes TeX tier and three Playwright suites; slot logic exists because parallel sessions starved each other | fast per commit, full before merge to main |
| PROC-44 | Release checklist, ten steps (`loom/docs/RELEASE.md`) | a bad tag | the paper tier needs arXiv fixtures; step 2 needs gitignored `demos/man12`, `demos/acgs` that only the author has; step 7 is a manual Overleaf round trip; step 4 regenerates figures into `docs/design/figures/`, which does not exist | loosen: steps 1, 3, 5, 6, 8, 9 only, plus a short Overleaf check; step 10 is not for v0.1 |
| PROC-45 | Ten documentation review passes (`CLAUDE.md:63-85`) | stale or contradicting docs | 700 words of CLAUDE.md read by every agent every session | move to a release-time checklist; the review itself is what finds PROC-1 to PROC-13 |
| PROC-46 | "Never edit `~/notes/`" in `AGENTS.md:21`, `docs/contributing.md:60` | the author's own notes | none, but it is a path on one person's machine in public documents | remove from public docs; keep in the author's private CLAUDE.md |
| PROC-47 | Publishing to PyPI or npm by the user only (`AGENTS.md:26`) | an agent publishing | none | keep |

## 4. Work queue, one line each (trigger against the pilot and the new framing)

| item | verdict |
|---|---|
| WQ-08 nest under `\part`, KOMA, memoir | not fired; a pilot paper in memoir or with `\part` fires it; watch, defer |
| WQ-10 locator normalization | not fired; defer |
| WQ-13 graph at scale (2000 nodes) | not fired; the graph is now the product, so a pilot quilt of a long paper could fire it; check the largest demo once; defer |
| WQ-16 Overleaf procedure | fired: its trigger is "cutting the first tagged release"; do a thirty-minute manual check on `demos/demo`; relevant to v0.1 |
| WQ-17 external user | fired: the pilot is this item; convert it into the pilot protocol and close it |
| WQ-19 PyPI and npm | its trigger "the author decides to release" is a decision, not an observation; v0.1 goes via GitHub; defer, and reword |
| WQ-22 extraction shares node model | not fired; defer |
| WQ-28 annotated export as LaTeX and PDF | fires if a pilot user must show a review to a coauthor without the application; likely asked early; defer, watch |
| WQ-29 node manager | not fired; defer |
| WQ-30 history gc | not fired for a two-week pilot; defer |
| WQ-36 annotation bodies beside manifest | not fired; defer |
| WQ-39 mechanical version check | not fired; defer |
| WQ-42 gradient with orientation held | moot: it exists to protect a release-note claim that the reference layer makes questions cheaper; the claim is not the new framing; drop |
| WQ-51 macro sets leak | not fired; two macro sets in one quilt is plausible with imported papers; defer |
| WQ-52 simultaneous agent copies | relevant to AI-generated mathematics; fires if a pilot wants two agent versions of one section; defer, watch |
| WQ-54 annotations follow adopted text | relevant: adopting an agent's text is the central boundary act; its trigger is observable in a pilot session; watch, possibly promote |
| WQ-56 figures cold build | relevant: a pilot user's first compile is cold; time it on a clean machine; one hour |
| WQ-58 lazy digests | not fired; defer |
| WQ-60 annotation anchors | relevant if pilot users annotate AI output heavily; defer, watch |
| WQ-63 taking part of a pull | relevant: choosing part of an AI change is the use case the boundary exists for; the trigger will fire quickly; candidate for the push |
| WQ-64 HTML file reach | not fired; defer |
| WQ-66 shell escape documents | likely fires on a real paper (minted, externalized tikz); defer, handle by a clear refusal message |
| WQ-67 corrections to a digest | not fired; defer |
| WQ-68 toolbar changes | an author workshop, not a trigger; the toolbar was just reshaped; defer |
| WQ-69 every note | matches "network mirrors the head"; its trigger is "the author asks"; candidate for after the pilot starts |

Nothing in the queue speaks to the new framing's actual gaps (application launch, start a quilt, drag resources in, three-surface parity); those are plans, not deferred items.

## 5. History load

Citations (grep, approximate): plan files cited by a normative document 25 of 45, by loom or arras source or tests 29 of 45; 14 plans are cited by neither (for example 0.1, 0.16.1, 0.17.3, 0.17.4, 0.26, 0.3, 0.4, 0.6, 0.9.6). Source and test files that cite `plan 0.N` or `docs/plans`: 235, with 332 citations. Reports: only about 6 files are cited anywhere outside plans and reports (hostile-demo.md from two tests and the queue; viewer-speed-study, review-panel-study, open-quilt-study, cli-study each once). `docs/design/README.md:74` and `AGENTS.md:15` tell agents history is "never normative", but `docs/plans/` and `docs/reports/` sit in the default search path, and a keyword search for any feature name returns a plan first. `docs/plans/0.1-implementation-plan.md` is named like the release, and its header points to `docs/deviations.md`, which is deleted.

Frozen records: `decision-records-frozen.md` holds 360 records in 55,742 words (a quarter of the normative-sized corpus). `DR-NNN` appears 100 times in 49 source and test files, about 75 times in normative documents (`docs/design/invariants.md` 29, `docs/specs/manifest.md` 16, `diagnostics.md` 10, `write-api.md` 6, `closed.md` 22, `README.md:58`), and 507 times in plans and reports. A reader who meets "DR-196" has to open a 55,000-word file and search; most citations are the justification for a rule that the rule's own sentence could carry. The cost is a lookup per citation and a pointer to a file the author has said is frozen and "no longer written".

| id | finding | weight | effort | recommendation |
|---|---|---|---|---|
| PROC-50 | Move `docs/plans/`, `docs/reports/` (including all but the v0.1-study reports), `docs/long-prompts/` and the frozen records into `docs/archive/`, with a one-line README saying "history, not instructions". Update the 235 citing files with one sed (`docs/plans` to `docs/archive/plans`); `plan 0.NN` text citations need no change | hurts: 87 percent of `docs/` is history and agents search it as if current | hours | fix |
| PROC-51 | Keep `decision-records-frozen.md`, but strip the 75 normative DR citations to the rule's own words where the rule is self-contained; leave them in code | cosmetic | hours | defer |
| PROC-52 | `docs/plans/0.1-implementation-plan.md` collides with "v0.1" | cosmetic, but a pilot-week source of confusion | minutes | fix (rename on archiving) |

## 6. Onboarding for a human contributor (top README, `docs/contributing.md`)

Steps a newcomer hits, checked against the files named:

- PROC-60: the top README never states the prerequisites. `README.md:28-35` says `git clone`, `uv tool install -e ./loom`, `loom --version`. The dependency table is in `loom/README.md:11-16` (Python 3.11, uv or pipx, TeX Live with `latexmk`, `pdflatex`, `dvisvgm`, `bibtex`/`biber`, poppler, git), and CI installs `make4ht tex4ht luaxml` too (`.github/workflows/loom.yml:96`), which that table does not name. A newcomer has no `uv`, no TeX Live (several gigabytes) and learns it from `loom doctor`, which the top README never mentions. Weight hurts; effort hours; fix.
- PROC-61: `loom serve` in `demos/showcase` (`README.md:40`) needs TeX to compile the documents; `--no-compile` exists (`loom/docs/cli-reference.md:1155`) but is not offered. If TeX is missing the first run is a compile failure on the front page.
- PROC-62: the Tests table (`README.md:47-52`) omits `uv sync`, `npm ci` and `npx playwright install chromium` (they are in `docs/contributing.md:21`), and omits `scripts/verify`, the command contributing calls "the one verification command".
- PROC-63: `docs/contributing.md:21` lists set-up in one sentence for three toolchains and gives no Node version (`arras/README.md:13` says 20 or newer), no Python version, and no TeX Live version (CI uses a pinned container; CI's TeX Live 2026 appears in the author's memory, not in the file). Several tests need `LOOM_PAPER_FIXTURES`, arXiv sources the newcomer cannot get; `docs/contributing.md:60` says paper sources are copies under `tests/fixtures/`, gitignored, which a clone does not have, and `demos/build.py` full mode needs them (`demos/README.md:15-22`).
- PROC-64: wrong repository names. `loom/README.md:21` `pipx install git+https://github.com/ikmartin/loom`, `:28` `git clone https://github.com/ikmartin/loom`, `loom/pyproject.toml:27` Repository, `arras/README.md:16` `git clone https://github.com/ikmartin/arras`, `loom/CONTRIBUTING.md:3` "the loom-arras workspace repository". The git remote is `ikmartin/loom-arras` and the package is in the `loom/` subdirectory, so `pipx install git+https://github.com/ikmartin/loom-arras` cannot work either; it needs `#subdirectory=loom`. CI tests `pipx install .` from `loom/`, never the documented URL (`.github/workflows/loom.yml:39`). Weight blocks for the pilot install and hurts for contributors; effort hours; fix.
- PROC-65: contributing assumes knowledge: "P7", "C3", "K5", "WQ-NN", "DR-196", "quilt", "landmark", "digest", "acceptance", "node" with no glossary; `AGENTS.md` and `CLAUDE.md` are the only place the reading order is stated, and neither is linked from the top README as the thing to read first for contributors (the README says "Read it first" only in the documents list, `README.md:22`).
- PROC-66: no contributor guide a person would recognise: no root `CONTRIBUTING.md`, no description of how to run one test (the slowest part is learning the four test tiers and markers `tex`, `paper`, `network`, `client`, whose list is in `README.md:49`), no architecture map. `loom/README.md:69-75` ("Layout of this repository") is the nearest, and lists seven of about 50 modules in `loom/src/loom/`.
- PROC-67: parallel-session rituals (slots, `ARRAS_SLOT`, `PATIENCE`, `noPolls`, `docs/contributing.md:44-52`) are explained to a newcomer before they can run a test.
- PROC-68: public documents carry one person's machine (`~/notes`) and workflow (the author's memory-only rules about plans and co-author trailers are invisible to a contributor but enforced by habit).

Overall weight for onboarding: hurts for contributors, blocks only PROC-64 for the pilot. Effort: a day for a real contributor page, hours for PROC-60 to 64. Recommendation: fix PROC-60, 62, 64 now; defer a full guide until the pilot.

## 7. Release path

Present: `loom/pyproject.toml:3` and `loom/src/loom/version.py:3` both `0.1.0.dev0`; package name `loomtex`; a ten-step `loom/docs/RELEASE.md`; CI lanes; a vendored viewer in `loom/src/loom/assets/arras/` committed so a clone carries it; `loom doctor` and a CI job installing from the clone on a bare runner; `loom upgrade` (refreshes a quilt's agent files, `cli-reference.md:1277`, not the tool).

Missing for "easy to install from GitHub":

| id | gap | evidence | weight | effort | rec |
|---|---|---|---|---|---|
| PROC-70 | no tag, no GitHub Release | `git tag` returns nothing; version is `0.1.0.dev0` | blocks | hours | fix |
| PROC-71 | no tested one-line install | docs name a repository that is not this one (PROC-64); the working form is `pipx install "git+https://github.com/ikmartin/loom-arras@v0.1.0#subdirectory=loom"` or the `uv tool install` equivalent, and CI should run exactly that | blocks | hours | fix |
| PROC-72 | no changelog a pilot user can read | no `CHANGELOG*` anywhere; RELEASE.md says "release notes" (`:`7, 9) without naming where | hurts | hours | fix (one page, written by hand at tag time) |
| PROC-73 | no way to update | no `loom self-update`; `loom upgrade` is for quilts; with `uv tool install` the update is `uv tool upgrade`, never written down | hurts | hours | fix (two lines in the README and in `loom doctor` output) |
| PROC-74 | no way to report a problem | no `.github/ISSUE_TEMPLATE`, no mention of issues in any README (grep found none) | hurts | hours | fix (a template asking for `loom doctor` output) |
| PROC-75 | the bundled viewer is stamped dirty | `loom/src/loom/assets/arras/VERSION`: "4c4ba495-dirty"; `bundle.py` warns only | hurts | minutes | fix at tag time; make the release step fail on `-dirty` |
| PROC-76 | prerequisites are heavy and unstated for a mathematician: TeX Live with make4ht, tex4ht, luaxml (CI installs these, `loom.yml:96`), poppler, uv or pipx, Python 3.11 | `loom/README.md:11-16`; `doctor.py:93-96` lists make4ht | blocks if the pilot users do not already have them | days if loom is expected to bundle anything; hours to write a per-OS preflight page | fix the page; defer bundling |
| PROC-77 | RELEASE.md steps that the pilot does not need or cannot run | step 2 (gitignored `demos/man12`, `demos/acgs`), step 4 (writes to nonexistent `docs/design/figures/`), step 7 (manual Overleaf round trip), step 10 (publish) | hurts | hours | loosen to the v0.1 subset |
| PROC-78 | the "launch it" application does not exist as a command a mathematician finds | the only way in is a terminal `loom serve` (`README.md:40`); no `loom` with no arguments, no launcher, no packaged app (this is another auditor's area; recorded here because install instructions depend on it) | blocks for the new framing | days | fix (even a one-command start page is a v0.1 decision) |

## Reading of the process itself

The documents were written for one author and a fleet of agents, and the machinery (queue, plans, frozen records, generated indexes) is tuned for keeping agents consistent over months. For the next two weeks the dominant cost is not enforcement, which is automated and mostly cheap, but reading: an agent that obeys the order reads about 57,000 words and then finds a plan, report or frozen record for every keyword. The framing sentences (PROC-1 to 13) are cheap to fix and will otherwise be inherited by every agent session and by the first pilot user.

## Ten changes that would most speed up the next two weeks, ranked

1. Rewrite the first screen of the design (PROC-1, 2, 3, 5), principles 8 and 9 (PROC-6, 7), `README.md`, `loom/README.md`, `arras/README.md`, `pyproject.toml` description (PROC-11, 15) around the author's statement. Hours.
2. Fix the install path and tag v0.1 (PROC-64, 70, 71, 73, 74, 75): one tested command naming this repository and `#subdirectory=loom`, a tag, `uv tool upgrade` documented, an issue template. Hours.
3. Add `docs/v0.1.md` (about 1,000 words): what is in v0.1, what is hidden, the pilot protocol (absorbing WQ-17 and WQ-16), the daily checklist. Hours.
4. Move plans, reports, long prompts and the frozen records to `docs/archive/` with a banner README, and point AGENTS.md at the new reading path (PROC-50, 52). Hours.
5. Rewrite AGENTS.md and CLAUDE.md to about 450 and 500 words, and give model.md and agents.md section indexes and invariants.md a title list (section 1's path). A day.
6. Suspend plan-per-phase and new queue items for the push; keep the checkers (PROC-30, 37). Minutes.
7. Move the CLI reference and the demo copies of fixtures out of the per-commit gate into the merge-to-main gate (PROC-39, 40, 43), and vendor arras once per merge, not per branch (PROC-38). Hours; reduces merge conflicts between parallel sessions.
8. Add the prerequisites and `loom doctor` to the top README and a per-OS preflight page (PROC-60, 61, 76). Hours.
9. Trim RELEASE.md to the v0.1 subset and make the release step fail on a `-dirty` bundle (PROC-44, 75, 77). Hours.
10. Remove or hide the purely personal or stale rules from public documents: the `~/notes` rule, the ten passes in CLAUDE.md, the stale queue count, stale repository URLs in `loom/CONTRIBUTING.md` and `arras/CONTRIBUTING.md` (PROC-21, 46, 45). An hour.

## To restore or tighten once the pilot is running

- Reinstate plans for work that spans sessions, now as short files under `docs/plans/` with the v0.1 list as the index.
- Reopen the work queue cap and triggers; convert pilot observations into triggers (WQ-63, 54, 28, 56, 66 are the likely fires).
- Re-run the ten documentation passes and the DR-citation cleanup (PROC-51).
- Put the CLI reference check and full fixture comparison back into every commit's gate if conflicts prove rare.
- Write the real contributor guide (a map of the 50 modules, the four test tiers, a glossary) once someone outside the author has tried to contribute.
- Decide the PyPI question (WQ-19, name `loomtex`) after the first pilot update cycle.

## Note on ids

PROC-19 to 29 and PROC-53 to 59 and 69 are unused; the tables above are keyed by section. PROC-21 is the stale `loom/CONTRIBUTING.md:3` and `arras/CONTRIBUTING.md:3` pair ("in the loom-arras workspace repository", "arras is loom's viewer ... built here and vendored" in a codebase that is no longer a separate repository, `arras/README.md:16` clones `ikmartin/arras`); weight hurts, effort minutes, recommendation fix.
