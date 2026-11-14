# The codebase, evaluated

An evaluation of loom's code, tests and working process on `main` (commit 71621877, 13 November 2026), asked for alongside the plan for v0.1: what is inefficient, what can be streamlined, what would make the code easier for people to modify and extend, what would speed development, and which tests and practices to drop. It is the third of the study's three documents; the plan is `docs/plans/0.32-v0.1.md` and the grading against the release bar is `state.md` beside this file. Findings are cited by id from the reports under `raw/`; `register.md` says which report holds each, except for the reports it does not cover, such as `security.md`, `spike-door.md` and `spike-speed.md`, which are cited by name. Timings were taken on a machine shared with other sessions: counts and comparisons made close together hold, absolute seconds are soft.

## The verdict in one paragraph

The code is in better health than its behaviour suggests. Both codebases pass strict type checking, the tests that compile TeX are hermetic, the two sanitisers that guard the viewer rebuild from an allowlist, the agent's tools, permission files and references are generated from one table, and the agent's orientation works for a small model. What costs the project is structural and fixable. There is no single path for writing a person's file, which is where most of the write faults come from. The viewer's write API is a second implementation beside the command line. The command-line package holds the domain logic. The build redoes work for the whole quilt on every change. Generated artefacts kept in git make parallel sessions collide. And most of `docs/` is history that every agent searches. Five security holes need closing first, the worst being that a file in the quilt runs as the person through the MCP server's per-call `python -m loom`, and that a web page can read the write token and the quilt by DNS rebinding (`security.md`). In the lead's judgment, none of these needs a rewrite.

## Size and shape

| what | measure | source |
|---|---|---|
| Python under `loom/` | about 92,000 lines, source and tests together; 195 source files under strict typing | lead's count; CORE |
| `loom/src/loom/cli/` | 39 files, 13,327 lines; `cli/review.py` alone 2,136 | CORE-1 |
| viewer source under `arras/src/` | about 36,000 lines (40,000 with its unit tests), 24 pages | lead's count; INV |
| operations | 77 commands; 44 open to agents; 42 MCP tools; 47 write endpoints | INV, register a.4, a.5 |
| diagnostic codes | 74 | CORE-15 |
| unit test items | 2,546, of which 767 are one file, `test_output.py` | TEST-3 |
| hand-written test lines to source lines | 0.59 for loom, 0.42 for the viewer | TEST |
| test files that are generated or copied data | 668 of 899 under loom, 413 of 475 under the viewer | TEST; lead's count |
| vendored viewer bundle in git | 12 MB, 303 files, about 44 MiB packed over 160 commits | VIEW, TEST |
| `docs/` | 544,000 words, 87 % of it history | PROC |

## What is inefficient

**The build does whole-quilt work on every change.** On a large quilt every publication costs at least five seconds even when nothing changed (PERF-1). A prototype of six cheap changes measured what is left of a save's build with them applied, in one run on a loaded machine: adoption comparisons 18 %, preview cache reads 15 %, the scan 15 %, applying records 12 %, section-draft context 10 %, publishing 9 %, the manifest 6 % (`spike-speed.md`). No single step is above a fifth, so getting under two seconds at that size needs an incremental build and a manifest sent as a difference, which is weeks of work and belongs after v0.1.

**Cache keys carry page numbers.** Each block's key hashes the whole file's text, so every block of the edited file re-renders on every save; that costs about a second on the large quilt, and a narrower key would serve stale line numbers, so it stays. Each key also includes every document's page numbers, so one moved page break re-renders everything. With page numbers out of the keys, a page shift went from 2,384 blocks and 51 TeX runs to one of each; the change needs a check of the preamble for commands that print a page, and its first build remakes every snippet (`spike-speed.md`).

**Each agent call is a new process and a full scan.** The MCP server runs every tool as a fresh `python -m loom`, which rescans the quilt (CORE-18, INV-14). Each viewer write is answered only after a full rebuild: 6.3 to 6.7 seconds on the large quilt, 0.03 seconds when answered first in the prototype, at the price of sixteen or so tests and the viewer's assumption that a write's answer means the page is current.

**Small things that multiply.** The person's name is looked up with a `git` subprocess 609 times per build when no loom name is set (PERF-5). The viewer fetches a 10.6 MB manifest whole three or four times per save and holds it in deep reactive state that ninety files read (VIEW-2, PERF-9). Nearly half of loom's internal imports sit inside functions, which hides several import cycles (CORE-2).

## What makes it hard to modify

**The command-line package is the domain layer.** Error types, identity checks and the cores of annotating and accepting live in `cli/`. Twenty-one modules outside it import from it, and the HTTP API calls private functions in `cli/review.py` (CORE-1). A change to the viewer therefore routinely edits a command module.

**Three surfaces, two implementations.** MCP tools are generated from the commands, so those two agree. The HTTP write API is a separate dispatcher that repeats validation, the author guard and error mapping for each endpoint (CORE-3). They already differ: Accept in the viewer does more than `loom accept`; fifteen operations exist only over HTTP; "restore" names three different acts; two commands are named `import`, while adding a PDF is `library add`; `ai delete` deletes annotations (CORE-3, INV-10, INV-11, CORE-8).

**No single place writes a person's file.** Keep, discard, restore, tick, adoption and Overleaf pulls each write in their own way, with their own idea of what to keep first (SAFE §1). A prototype of one door for every write closed the faults in which loom writes twice, loses a write made beside it, or replaces bytes it does not keep (`spike-door.md`); the faults in which loom misreads text someone else typed, or which block a key names, need separate placement fixes, as do the records that follow the text. Without the door, each new feature that writes has to re-derive safety.

**A few very large units.** `cli/review.py`, the `lint` function, `build_manifest` and the `Records` class carry most of the accidental complexity (CORE-14). The TeX-reading core is large too, but its complexity is essential and it was not examined for correctness by this study.

**Text that misleads a reader.** At least nine help and report strings, seven in `cli/` and two in `doctor.py`, still say loom never edits a file, though Keep, discard, restore, tick and the incorporate steps of adoption and Overleaf sync do (CORE-8). Docstrings narrate how code used to be, against the repository's own rule. `dict[str, Any]` appears on 422 source lines, behind otherwise complete annotations.

**The viewer has no live development loop.** Its development server serves a static fixture with no write API, so no control that writes can be tried there. Seeing a change in a running `loom serve` means a build, then vendoring it or pointing `LOOM_ARRAS_BUNDLE` at it, then a restart and a reload (VIEW-13). The viewer still carries the machinery of a static, host-neutral reader, which is no longer a goal (VIEW-12).

**Quilts carry no format number.** One records file silently resets to empty when its schema number differs (CORE-7).

## What makes it hard to extend

Adding one operation today touches a command, the table of agent commands, the write API's capability list and handler, the viewer's write module, two generated references and their tests. Adding a diagnostic means a registry entry with no notion of who the message is for. Nothing in the contributor guide says how to add a mode, a kind of record, an operation or a kind of file the viewer opens (CORE-16). `loom/CONTRIBUTING.md` still says the invariance test runs every command (TEST-2).

## Tests

The suite is not oversized: the apparent excess is copied and generated data. Its problems are of balance and of ritual.

- **Nothing tests what matters most.** No test in the suite runs a realistic sequence of writes and then looks at the person's files, and the two latest write bugs were found in the author's own quilt, not by a test (TEST-1). The contributor guide says the invariance test runs every command; it runs about twenty that read or record and none that write a person's text (TEST-2). The safety trial left the missing test, outside the suite for now: ten seconds, failing against the code from before each of those two bugs' fixes, with nine expected failures for the faults still open (`safety-harness/keep/test_write_safety.py`).
- **Almost a third of the unit items police terminal output.** `test_output.py` is 767 of the 2,546 items: it runs 372 of its 395 cases twice and enforces column width and phrasing for a command line no person is meant to type; its 210 checks that a case leaves the person's files unchanged stay (TEST-3, CUT-10).
- **The static browser suite fakes the write API** in 66 hand-written routes whose shapes nothing checks against the real one, while the same paths are also tested against a real server (TEST-10).
- **CI finds out after the push.** `main` was pushed red five times in nine days; two of those were a real break that local runs did not show, and the other failures came from Linux fonts, a file that exists only on the author's machine, test order and a change of TeX Live year. There is no macOS job (TEST-4, INST-15).
- **Rituals.** A change can need up to seven regeneration steps, three of them needing TeX, with no one command to run them. The conformance fixture and the demonstration quilt each exist in three copies. Vendoring the viewer by hand was 33 of 220 commits in a month, and the generated quilts and demonstration copies churned more lines than hand-written source (TEST-5 to TEST-7).
- **Shared-machine hazards.** One unit test fails on any untracked file under `loom/src`, `loom/tests/quilts` or `arras/src`, which includes another session's work in a shared checkout (TEST-12). During this study the machine's load reached 50 with other sessions running TeX, which inflates every absolute time here; counts and comparisons made close together hold.

## Documents and process

An agent that reads everything `AGENTS.md` lists reads about 57,000 words before starting; the honest minimum is about 5,700. Plans, reports, long prompts and the frozen decision records are 87 % of `docs/`, and, by PROC's reasoning, agents search all of it as though it were current. The governing documents still describe a command-line tool with a static viewer, and neither they, the orientation nor the rules use the word "understanding" (PROC). The checks themselves are cheap; what costs parallel sessions is merge conflicts on generated files (the command reference, fixture copies, the vendored bundle). The rule for plans lives in the author's own notes, not in the repository (PROC-37).

## What is sound and should be kept

- Strict typing that passes in about five seconds on loom, and a clean type check on the viewer.
- The hermetic TeX environment for tests, and the tests that guard the person's files, once their scope matches their claim.
- Sanitising by rebuilding from an allowlist, for HTML in Markdown and for HTML made from TeX.
- One table of agent commands from which the MCP tools, the permission files and the references are generated.
- The orientation and rules an agent is given: a small model understood the boundary from them alone.
- Append-only records with the state computed from them.

## Changes, ranked by what they buy

Before v0.1, because each makes the rest of the work safer or lets more of it run at once:

| # | change | buys | evidence |
|---|---|---|---|
| 1 | One door for every write to a person's file, with the safety test in the unit tier; the placement fixes beside it | closes the faults in which loom writes twice, loses a write made beside it or replaces bytes it does not keep, and every later feature that writes inherits that; the placement fixes close the rest | SAFE-12; `spike-door.md`: a prototype took random-sequence damage from 105 of 200 to 5, a careful version 6-7 sessions |
| 2 | Errors, identity and `key_hash` out of `cli/` first; the annotation and acceptance cores follow once the write path is rebuilt, since 49 files import the module and the safe write path rewrites those cores | viewer work stops editing command modules; the first step is small and mechanical | CORE-1; `redteam-execution.md` RTX-3 |
| 3 | The write API's dispatcher and its test file split by family, each family owned by the workstream that builds it | the ten planned packages that add an endpoint stop colliding in `render/api.py`; the registry of operations (CORE-3) can then wait until after v0.1 | CORE-3; `redteam-execution.md` RTX-2 |
| 4 | A development proxy from the viewer to a running `loom serve`, and vendoring out of everyday commits (the plan recommends release and CI) | write controls can be developed; one source of conflicts between sessions goes | VIEW-13, TEST-6 |
| 5 | One `scripts/regen`; regeneration checked at merge, not per change; one copy of the fixture | fewer conflicts and no forgotten step | TEST-5, TEST-7 |
| 6 | An everyday lane under three minutes (an estimate) run in each session's own worktree; merge only on green; a macOS job; a pinned TeX image | a check an agent can trust and afford | TEST |
| 7 | `test_output.py` to one run per case, keeping each case's check that files are unchanged | 60-70 s of serial time, 15-20 s of wall time per run | TEST-3, CUT-10 |
| 8 | The cheap speed fixes: re-anchor annotations once and cache it, cache the git name, take page numbers out of the cache keys with a check of the preamble | 2.4 s per build on a large quilt; 609 subprocesses for a new user; a page shift from 2,384 blocks to one, at the price of one full remake of snippets | `spike-speed.md` |
| 9 | Archive history out of the path agents search; a reading path a third as long; the framing corrected | every session starts faster and from true statements | PROC |
| 10 | A format number in each quilt, and readers that refuse instead of resetting | a stale quilt says so instead of misbehaving | CORE-7 |

After v0.1, because each is larger than its v0.1 benefit:

- an incremental build, a persistent scan, and a manifest sent as a difference;
- a registry of operations with one generic endpoint, one guard and one error type, and then MCP tools run in process on it;
- the three or four largest units split along their seams;
- the static-host machinery and whatever v0.1 hid deleted;
- typed records at module boundaries;
- a contributor's recipe for each kind of addition, and short current-state headers on the viewer's modules.

## Not examined

The TeX-reading core (`scan/`, `digest/`, the HTML conversion) for correctness; the library's digest building and search beyond intake; accessibility; and third-party dependencies beyond noting that two builds of MathJax ship.
