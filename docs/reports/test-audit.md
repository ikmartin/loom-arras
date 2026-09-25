# The test and verification system: an audit, and a revision

This report is for the author. It audits every test in the workspace and `loom doctor`, critiques them, and recommends a revision of both. Written 2026-09-23, after plan 0.14 and WQ-48.

**Scope.** About 1,140 test functions (about 1,170 collected items):

| suite | tests |
|---|---|
| loom pytest | 632 |
| arras vitest | 120 |
| arras Playwright: default e2e | 217 |
| arras Playwright: write | 11 |
| arras Playwright: reading | 20 |
| arras Playwright: minimal | 32 |
| arras Playwright: perf | 6 |
| arras Playwright: shots | 7 |
| loom-lsp | 26 |
| loom-nvim | 48 |
| loom-vscode | 47 |

On top of the tests: `loom doctor`'s 16 checks and their 5 tests, and 37 suites, commands and scripts that make up verification. Seven slices were audited in parallel by reading the code. A separate job ran and timed every suite that can run here.

**Where the per-test detail is.** Each slice's inventory lists every test with what it tests, what it assumes and what it asserts, followed by that slice's full critique with `file:line` references:

1. [loom refs and digests](test-audit/1-loom-refs.md) (161)
2. [records, history, review](test-audit/2-loom-records-history-review.md) (105)
3. [scan, render, TeX, papers](test-audit/3-loom-scan-render-tex.md) (191)
4. [CLI, AI layer, chat, fixtures](test-audit/4-loom-cli-ai-chat.md) (147)
5. [arras unit, e2e part 1](test-audit/5-arras-unit-and-e2e-part1.md) (181)
6. [arras e2e part 2, write, reading, minimal, perf, shots](test-audit/6-arras-e2e-part2-write-reading-minimal-perf-shots.md) (232)
7. [editor clients, `loom doctor`, the verification process](test-audit/7-editor-clients-doctor-process.md) (121 plus doctor and process)

This report is the synthesis. It repeats only what the recommendation needs.

**How to read it.** "Verified" means reproduced here. Everything else was found by reading, and the slice files name the line.

---

## 1. First, what is broken now

These are faults, not matters of style. Most of them the audit found only because it ran suites the usual verification never runs.

| # | fault | effect | fix | verified |
|---|---|---|---|---|
| 1 | The workspace `.gitignore` line `ai/` is unanchored. It ignores `loom/src/loom/assets/ai/formatting.md` and its three quilt copies. | They were never committed, so **CI has been red since 2026-09-22**: loom unit fails 17 tests, and loom tex fails `gen_quilts`. Every local run is green because the files exist on disk. The commit "Phase 1 of new chat stuff" shipped without them. | Change the line to `/ai/` and `git add` the four files. | yes (`git check-ignore`, `gh run list`) |
| 2 | `mypy`, which runs in CI but not locally, fails with 2 errors in `loom/src/loom/agent.py` (plan 0.14 code). | The next commit that includes `agent.py` turns CI red a second way. | Type the two `Optional`s. | yes |
| 3 | `agent.argv` substitutes each placeholder in turn, so a value containing a placeholder is expanded again: `argv(["{prompt}"], prompt="see {agent_session}", agent_session="u")` gives `['see u']`. | A person's text or a quilt path containing `{…}` is rewritten in the agent's command line. The test named "filled item by item" does not catch it. | Substitute in one pass with a regex over the template. | yes |
| 4 | The test harness clears `LOOM_RUN`, which nothing reads now, but not `LOOM_SESSION` or `LOOM_FIXED_TIME`. | With `LOOM_SESSION` set, dozens of tests fail with "no session matches". The launcher sets it for every agent turn, so **an agent loom started cannot run the suite**. | Clear every `LOOM_*` variable in `isolated_env`. | yes (by the slice-4 agent) |
| 5 | `tests/e2e-write/shots.e2e.ts` runs inside every `test:write` and writes into `records/images/`. | Every verification run modifies committed images. Two are modified now. | Move it to the shots config. | yes |
| 6 | The CI artefact named `bundle` is uploaded after `test:e2e` and `test:minimal` have rebuilt `arras/build` with a fixture staged into it. | The artefact is a fixture build, not the product. | Upload from a separate build, or stop the configs rebuilding (see §5.8). | by reading |
| 7 | All three editor-client suites run nowhere. loom-lsp fails 10 of 26 and loom-nvim 1 of 48, because plan 0.9 renamed `drafts/` to `drafting/`. `mirror-nvim.yml` publishes `loom-nvim/` to a public repository on every push to main without running a test. | Red, unseen, and published. | Add the suites to CI, read the master from `config.toml`, and gate the mirror on the tests. | yes (lsp); nvim by the slice-7 agent |
| 8 | The vendored bundle's new chunk files under `loom/src/loom/assets/arras/_app/` are untracked. | A commit of the tracked files would ship an `index.html` that loads chunks the commit lacks. No test loads the vendored bundle. | Use the tracked-file guard (§5.7). | by the slice-7 agent |

Product faults found along the way. Each is small; none is in a test:

| fault | where | verified |
|---|---|---|
| A `quilt:canon/<file>.tex` link opens as an unknown node, because `isDocument` knows masters only. | `arras/src/lib/review/run.ts:6` | by reading |
| The Chat skips its first poll, so the status line waits a second on opening. | `ChatView.svelte`, the `landed` guard | by reading |
| `render/fallback.py:101` tells the reader to run `loom build --force-svg`, which does not exist. A remembered SVG failure can never be cleared. | `render/fallback.py` | by reading |
| `_kpsewhich` is cached by name, not by PATH. Answers from the fake toolchain leak into later TeX-tier tests in a mixed run. | `scan/expand.py:83` | by reading |

## 2. What runs where

| suite | local block | CI | nowhere |
|---|---|---|---|
| loom ruff lint and format | yes (lint also covers `scripts/`) | yes (`src tests`) | |
| loom mypy | **no** | yes, on 3 Pythons | |
| loom pytest, unit tier | yes | yes | |
| loom pytest, TeX tier | yes, minus one hand-deselected test | yes (`loom-tex.yml`) | |
| loom paper and network tiers | skip themselves | no | **yes** |
| `gen_quilts --check` | yes (**duplicates** a pytest test) | via pytest | |
| install from clone, `loom doctor` exit 2 | no | yes | |
| arras check, vitest, e2e | yes | yes | |
| arras minimal | **no** | yes | |
| arras write, reading | yes | **no** | |
| arras perf, shots, prerender | no | no | **yes** (perf and one shots spec are broken) |
| work-queue check | yes | **no** | |
| loom-lsp, loom-nvim, loom-vscode | no | no | **yes** (red) |
| appendices C and D against the assets; chapter 12 against the CLI reference; the three fixture copies; the vendored bundle; the hard-wrap rule | — | — | **no check exists** |

The local block is pasted into each plan, and the copies differ: 0.13.2 has `mypy`, 0.14 does not. Local green does not mean CI green, and nothing in the loop shows CI's state. The hand-deselected "biber" test passed twice here, so that exclusion is stale or environment-specific, and it lives in no file.

## 3. The critique

### 3.1 Tests that cannot fail, or that pass on a crash

This is the most serious finding across all seven slices.

- **Exit code 1 means both "refused" and "crashed".** loom's `EXIT_CONTENT` is 1, and click's `CliRunner` also reports an uncaught exception as 1. So these all accept a traceback as a pass:
  - `exit_code in (0, 1)`: 11 in scan/render, 5 in refs, `test_did.py:87`, and more in slice 4;
  - `exit_code in (0, 1, 2)` in `test_never_modifies_author_files`, which runs over 13 quilts;
  - every bare `!= 0` refusal check: about 20 across slices 1, 2 and 4.

  One helper change fixes the class: invoke with `catch_exceptions=False`, or re-raise anything that is not a `SystemExit`.
- **Tautologies:**
  - `… or True` (`test_review_commands.py:300`, `test_commands_m1`);
  - `"-" in output` and `"+" in output`, which any key name satisfies;
  - `"draft" in output`, which the path `drafting/` satisfies;
  - `arras.path is None or arras.source` in the doctor JSON test.
- **Vacuous by construction:**
  - `test_a_fresh_digest_is_not_called_thin`: the demo has 2 pages and "thin" needs 8;
  - an order test whose data sorts the same alphabetically;
  - `test_match_lists_only…`, which accepts both outcomes;
  - two negative checks against `refs/`, although the code now writes `digests/storage/`;
  - the network test, which asserts a stale path;
  - a lastseen test that DR-284 made unfalsifiable;
  - three chat tests that assert the default text shown before any poll;
  - `base-path.e2e.ts`, which cannot fail with an empty base;
  - a hover test with no positive control.
- **Checks on source text:**
  - `"break" not in inspect.getsource(...)` and `"if w.source:"`, in refs;
  - private-function tests in several slices;
  - exact attribute-order markup substrings, which is how the `data-tex` change broke two tests for no behavioural reason.

### 3.2 Redundancy, overlap, and tests filed in the wrong place

- **Misfiled tests:**
  - About 18 tests in `test_refs_layer.py` are about sessions, the mailbox, CSRF and page notes, not refs.
  - `test_commands_m1.py` is named for a milestone and holds init, graph, lint, id and config tests.
  - arras has `phase3`, `phase4`, `phase5`, `study`, `requests` and `queue` files named for plans and studies, not features.

  A reader cannot find the tests for a feature, and overlap follows from that.
- **Overlap clusters:**
  - The same agent-guard property is tested five times in refs.
  - The same `dm-0001` edit, producing the same stale cause, appears in six review tests.
  - Batch behaviour is split across four tests.
  - `render_markdown` has four tests in three files.
  - The deny list is tested three times.
  - Closure order is asserted three times.
  - "A warm build renders nothing" is asserted four times.
  - The editor clients test root detection, the key under the cursor and argv building two or three times over, with copied cases.
  - In arras, about a dozen pairs:
    - Chat beside the reading;
    - the contents rail;
    - the key gutter;
    - "no write API, no controls";
    - the Kre99 citation link;
    - "a node in no document";
    - floating-box closing, tested three times.
- **Delete lists.** Each slice file has a "Delete or combine" section, with the reason each removal is safe. Together they list about 40 deletions and about 30 merges.

### 3.3 Length and speed (measured)

Serial wall time for the local block is about **260 s**:

| part | time |
|---|---|
| loom pytest | 129 s |
| arras reading | 53 s |
| arras e2e | 36 s |
| arras write | 25 s |
| `gen_quilts --check` | about 12 s |
| everything else | under 10 s |

The hotspots:
- **TeX tier: about 50 s.** Of that, the reshape tests take 34 s, and the showcase generator comparison 8 s even though it is marked `tex` and runs by default.
- **Fixed sleeps in the reading suite: about 33 s.** `opened()` alone sleeps 1.5 s, twelve times, and one zoom test takes 15 s.
- **Three `vite build`s per run,** because each Playwright config rebuilds, and write and reading produce identical builds.
- **About 6 s of serve-test teardown,** from `serve_forever`'s 0.5 s poll interval.
- **`test_never_modifies_author_files`: 7 s,** running about 20 commands on each of 13 quilts.
- **One fixed `sleep(1.5)` in the mailbox wake test.**

Repeated `loom init --demo` is *not* a cost: it takes 15 ms.

### 3.4 Missing tests (the largest gaps)

- **refs:**
  - `fetch_work` offline: the arrival check, retries on 406/429/5xx, and the `_unpack` path-escape refusal.
  - These commands have no test: `refs ingest`, `drop`, `links --depth`, `unlink`, `path`.
  - Request spacing.
  - Digest numbering rules from 8.4/8.5.
- **records and history:**
  - `freeze_moved`'s write path, which nothing reaches since DR-284.
  - Foreign log lines.
  - `loom:dangling-ancestry` and `loom:history-corrupt`.
  - `migrate_history`.
  - Revert with child markers.
  - `stamp --in`, `canonize --parent` and `live: false`.
  - The review-queue refusals.
- **scan, render and TeX:**
  - There is no negative test of the dialect validator, so a validator that accepted everything would pass.
  - Several dialect constructs are covered only by the TeX-tier fixture comparison.
  - `render/assets.py`, `review_compare`, the fallback's pure functions.
  - The fixture comparison ignores extra fragments and `source/`, `diffs/` and `transcripts/`.
- **CLI, chat and launching:**
  - `session delete --purge`, the one command that rewrites the log.
  - `session watch`, `session migrate`, and the `next` timeout.
  - The endpoints `resolve`, `session-reopen` and `session-purpose`. The last two are also missing from `write-api.md`.
  - `loom serve` on SIGTERM, and stop escalating to SIGKILL.
  - Book 12.1's rule that `--json` puts nothing else on stdout.
- **arras:**
  - `Transcript` gap-resync.
  - `write.ts`'s 403 re-probe.
  - The Chat status line's nine branches.
  - `follow`, `openChat` and `interceptLinks` as units.
  - The picker's find field, delete and empty states.
  - Against a **real** publisher: that a note lands in the selected session, and that edit, discard, undo, `digest-verify`, `review-finish` and `session-delete` work end to end.
- **Clients:**
  - Any CI.
  - `\cite` definition, rename, and shutdown in the language server.

### 3.5 Failure diagnostics

- **Output missing on failure.** More than 150 `assert run(...).exit_code == 0` lines print nothing on failure, only `assert 1 == 0`.
- **stdout and stderr mixed.** `json.loads(r.output)` parses stdout and stderr together (click 8.5), so a note on stderr becomes an unexplained `JSONDecodeError`.
- **Unhelpful fixture diffs.** `test_init_demo_matches_fixture` compares dicts of bytes: the diff names no file and gives no regenerate command. The fixture test compares two 100 KB manifests whole, and pytest truncates the diff.
- **Bare lookups.** Bare `next(...)` and tuple unpacking over manifest rows fail with `StopIteration` and no key named.
- **Opaque browser failures.** In arras, `evaluate()` returning a boolean, and `expect(x).toBe(true)` over computed values, fail without saying what was on screen.
- **Order-dependent tests fail far from the cause.** The reading suite's "a locator in the URL" dies with a bare `TypeError` when run alone, because it needs a note an earlier test wrote.
- **Waits that time out silently.** The launch tests' `finish()` returns quietly when its 60 s wait runs out, and no failure shows `agent.log`.
- **One root cause, many tracebacks.** The lsp suite prints ten tracebacks for one missing path.
- **Models to copy.** Some tests already do this well:
  - `test_cli_reference`, with an equality check and "run scripts/gen_cli_reference.py";
  - `test_quilts_match_generator`, which names each differing file and prints the regenerate command;
  - the refs guard tests, which put `(verb, r.output)` in the message.

### 3.6 Fragility and hermeticity

- **Shared quilts.** The write and reading suites `cp -R` loom's quilts from loom's *working tree*, which is dirty now. They also share one quilt across tests that depend on each other's order.
- **Shared build directory.** Every Playwright config writes the same `build/` and `static/build/`, so no two configs can run at once. Reading and shots-minimal both use port 4177.
- **TeX lookup cache.** The `kpsewhich` cache leaks between tiers.
- **Poppler under the wrong marker.** The `tex`-marked page-geometry tests really need poppler: without it they fail, not skip.
- **Timing windows.** The serve watcher tests prove an absence with fixed windows. The mailbox wake test can pass without exercising the wake.
- **Placeholder concurrency test.** The two-writers lock test passes whenever the two processes happen not to interleave.
- **Machine-dependent client tests.** The client suites depend on plenary's install path and on whichever `loom` is first on PATH. The VS Code suite skips seven tests silently.
- **House-style issues.** Several test docstrings narrate changes, against CLAUDE.md, and some comments in the test code are hard-wrapped.

## 4. `loom doctor`

**What it does.** It reports Python, loom and the interface version, then checks 10 tools:
- **required:** latexmk, pdflatex, dvisvgm; any of them missing gives exit 2;
- **optional:** bibtex, biber, lualatex, kpsewhich, pdftotext, pdfinfo, git.

It also reports the resolved author and the arras bundle.

**What is wrong with it:**
- **Missing tools.** It does not check tools loom calls: `latex` (the SVG fallback), `xelatex` (a supported engine), `pdftocairo` (figures), `claude`/`codex` (launching), `loom-lsp` (the editors).
- **Presence, not capability.** xpdf's `pdftotext` lacks `-bbox-layout` and still passes. A quilt set to `engine = "xelatex"` gets `ok`. The biber/biblatex mismatch, the classic failure, is not probed.
- **Missing author or bundle is treated as information.** Doctor prints `ok` with no author, although `accept` and `comment` exit 2 without one. It prints `ok` with no bundle, although `loom serve` exits 2 without one.
- **The bundle is not checked properly.** Its interface is printed, not compared with loom's. An invalid `LOOM_ARRAS_BUNDLE` is skipped silently. The vendored stamp names a commit even when `arras/` is dirty, so a stale bundle looks current.
- **No quilt-level checks.** The things that broke users in the recent sessions go unchecked:
  - an `ai-config.toml` that git tracks, or an incomplete one;
  - missing `.gitignore` lines;
  - stale `.claude/settings.json` or `.codex/rules/loom.rules`;
  - stale mode files or `loom.sty`.

  Only `loom agent check` and `loom upgrade` touch these, and nothing points to them. A docstring says `settings_deny_paths` exists "for tests and doctor", but doctor never calls it.
- **The output is hard to act on.** The summary says "a required tool is missing" without naming it. The JSON has no status or remedy per item. The text columns overflow. There is no warning tier.
- **Thin tests.** Three unit tests, one with a vacuous assertion, and one that depends on `/usr/bin` holding no latexmk. The CI step asserts only exit code 2, which a click usage error also produces.

## 5. Recommended revision of the test suite

### 5.1 One entry point

Add `scripts/verify` at the workspace root, in Python, with:

- **`fast`**, the inner loop, about 30–40 s: ruff, mypy, loom unit tier (xdist), svelte-check, vitest, lsp pytest, nvim plenary, vscode tsc and eslint, the work-queue check, and the tracked-file guard.
- **`full`**, before a commit or push, about 70 s with §5.8: `fast`, plus the TeX tier, every Playwright config, the fixture and doc agreement checks, and the vscode integration tests.
- **`--only loom|arras|clients|docs`.**
- **`paper`**, which stays manual.

It runs lanes in parallel. It prints one table of suite, result and seconds. It ends with `gh run list --branch <current> --limit 3`, so a red CI shows at the moment test output is being read.

Plans link to it instead of pasting a block. Each CI job calls its lane of it, so local and CI cannot diverge again. Deselections and skips live in the script with their reasons, never in session history.

### 5.2 The harness

**loom** gets one shared `tests/unit/conftest.py`, replacing the `run()` copied into about 20 files:
- **`run(args, cwd)`:** invokes with `catch_exceptions=False`, keeps stdout and stderr apart, and passes `--quilt` rather than `chdir`, which makes the suite xdist-safe.
- **`ok(...)`:** asserts exit 0, showing the command, stdout, stderr and the exception.
- **`refused(..., code, match)`:** asserts the code *and* the message, and fails if Python raised.
- **`json_of(...)`:** parses stdout only.
- **An `edit(path, old, new)` helper:** asserts that `old` is present.
- **Session-scoped templates for the expensive setups only:** a drafted-and-canonized shim quilt, a built demo, a drafted Manolache paper. Not for `init --demo`, which is cheap.

The harness itself changes too:
- `isolated_env` clears every `LOOM_*` variable and `_kpsewhich.cache_clear()`s.
- A `poppler` marker replaces `tex` where poppler is what a test needs.
- The biber test is fixed or skipped for a stated reason.

**arras** gets:
- A lint rule, or review habit, against `expect(bool).toBe(true)` over `evaluate()`: return the value and assert it, so the failure shows it.
- Each fixed `waitForTimeout` replaced by the condition it waits for.
- Per-worker quilt copies and `loom serve` ports for write and reading, from a **committed, clean** source (`git archive` of the quilt, not `cp -R` from the working tree), with no test depending on another.
- Fixture ids read from the fixture where a test depends on them, not hard-coded.

### 5.3 Reorganise by subject

- **loom:**
  - Dissolve `test_commands_m1.py` into init, graph, lint, id and config files.
  - Move the about 18 non-refs tests out of `test_refs_layer.py` into sessions, mailbox and serve files.
  - Put the `render_markdown` tests in one file.
  - Fold `test_author.py` into `test_quilt.py`.
- **arras:**
  - Dissolve `phase3/4/5`, `study`, `requests` and `queue` into feature files: context, chat, annotations, library, graph, workspace, links.
  - Merge the minimal suite's two 16-route loops.
- **Clients:** share one table of cases for the key under the cursor and argv building, read by the nvim and vscode suites. Better still, move key-at-cursor into the language server.

### 5.4 Delete and combine

Apply the "Delete or combine" sections of the seven slice files. That is about 40 deletions and 30 merges, each with its reason for being safe. The largest:

- the lastseen test DR-284 made unfalsifiable;
- the vacuous digest and order tests;
- the two source-text tests;
- `test_init_demo_writes_demo_and_lints_clean`;
- three strict-subset tests in AI and chat;
- the duplicated arras pairs in §3.2;
- `base-path.e2e.ts`, replaced by `paths.ts` unit tests under a mocked base;
- the dead perf probes and the broken `shots/report.spec.ts`, or else their repair.

Two need your decision:
- `migrate.py` and its tests, which move artifacts into `refs/<id>`. Book 8.16 reserves that directory for the author, and the no-backwards-compatibility rule applies.
- The `basis: definition` legacy alias, if no quilt uses it.

### 5.5 Add the missing tests

In priority order:

1. An argv regression test (fault 3).
2. Every endpoint in `CAPABILITIES` exercised over the real server at least once, and the real-publisher flows in §3.4.
3. `--json` purity, walking the command tree.
4. `session delete --purge`.
5. SIGTERM ending turns.
6. `freeze_moved`'s write path, as a unit test.
7. A negative test of the dialect validator.
8. `fetch_work` offline.
9. The history integrity checks.
10. The Chat status line as a pure function with a table test.
11. `Transcript` gap-resync as a unit test.

The slice files list the rest by area.

### 5.6 Better failures

Beyond the helpers in §5.2:

- Compare fixture and quilt trees **per file**, printing the first differing path and the regenerate command.
- Compare the manifest **per top-level section**.
- Make the launch tests' `finish()` fail with `agent.log` in the message.
- Have the lsp and nvim suites assert the fixture layout once, so one root cause fails once.
- Make every "can never happen" check an `assert` with the value it saw.

### 5.7 New checks the book already promises, or ought to

These are cheap, and belong in `fast` unless noted:

- **A tracked-file guard.** Nothing under `loom/src`, `loom/src/loom/assets`, `loom/tests/quilts` or `arras/src` may be git-ignored or untracked. This would have caught faults 1 and 8.
- **Chapter 12 equals `loom/docs/cli-reference.md`.** Chapter 12 says the existing test "fails when either drifts", but it reads only the loom file. The chapter has drifted by about 115 lines.
- **Appendices C and D equal the shipped mode files and orientation.**
- **The three conformance-fixture copies agree,** and so do the committed demos and loom's test quilts.
- **The vendored bundle is current and complete.** `vendor_arras.py` stamps `-dirty` and refuses without `--allow-dirty`. Every file `index.html` needs is present and tracked. `VERSION`'s interface equals `INTERFACE_VERSION`.
- **A hard-wrap guard** for markdown, docstrings and comments, making CLAUDE.md passes 9 and 10 mechanical.
- **Counts in chapter 14 generated,** or removed; all of them are stale today.

### 5.8 Speed

From about 260 s serial to about **65–80 s**, in this order:

1. **Run the loom and arras lanes in parallel:** about 135 s. This needs only the script.
2. **Add pytest-xdist to loom:** 129 s down to about 35 s.
3. **Build arras once** and give each Playwright config its own output directory, staging each fixture into a copy. That removes two of three builds and the shared-`build/` race.
4. **Run e2e, write and reading concurrently** on distinct ports. The arras lane goes from about 114 s to about 60 s.
5. **Shard the reading suite** with per-worker quilts, and replace its about 33 s of fixed sleeps.
6. **Drop the duplicate `gen_quilts --check`.**
7. **Set `poll_interval`** in the serve tests' fixture.

In CI:
- Cache Playwright's browsers.
- Use a slimmer TeX image; container start-up is 79 s of the 2.5 min TeX job.
- Stop rebuilding arras per config.
- Upload the product build, not a fixture build (fault 6).

### 5.9 CI

One workflow per lane, each calling `scripts/verify`, running:
- **loom:** unit on the Python matrix; TeX in the container.
- **arras:** check, vitest, every Playwright config including write and reading, with loom installed from the checkout.
- **clients:** lsp, nvim with pinned Neovim and plenary, vscode under xvfb with skips disallowed.
- **docs:** work queue, agreement checks, hard-wrap.

`mirror-nvim.yml` should depend on the clients job.

## 6. Recommended revision of `loom doctor`

Doctor becomes the one command to run when something is off. It is machine-level by default, grows a quilt section when run inside a quilt, and reuses the checks other commands already own instead of re-implementing them.

- **Three states per item,** each with a one-line remedy:
  - `ok`;
  - `warn`: works, but something a user will hit;
  - `fail`: a command the user needs will refuse.

  Exit codes: 0 when nothing fails, 2 when anything fails, and 1 reserved for warnings under `--strict`. The summary names every failing item. The JSON carries `status`, `severity` and `remedy` per item. The columns size to the longest version string.
- **Machine checks, added:**
  - `latex`, `xelatex` and `pdftocairo`: fail or warn depending on use.
  - `claude` and `codex`: warn, and only when an AI is configured or `--agents` is given.
  - `loom-lsp`: optional.
  - Capability probes: `pdftotext -bbox-layout` works; `biber --version` runs, and when biblatex is present its versions match.
- **Machine checks, changed:**
  - **Author:** no author is a `warn`, with the exact command to set one.
  - **Bundle:** no bundle is a `fail` ("`loom serve` will refuse"). An invalid `LOOM_ARRAS_BUNDLE` is named, not skipped. The bundle's interface is compared with loom's, a mismatch is a `fail`, and in a checkout a `-dirty` or behind-HEAD bundle is a `warn` naming `vendor_arras.py`.
- **Quilt section, when run inside a quilt:**
  - The configured `engine` is present.
  - The agent configuration: complete, not tracked by git, ignored, launch on or off. This reuses `loom agent check`'s functions and points to `loom agent check`.
  - `.claude/settings.json` and `.codex/rules/loom.rules` current against the table, by a dry run of `vendor_files` comparing bytes.
  - The modes version and `loom.sty` current, pointing to `loom upgrade`.
  - The `.gitignore` lines `loom init` writes.
  - Deprecated config keys, pointing to `loom lint`.
- **Tests:**
  - One table-driven test per item and state, run on the shim, including the hang timeout and each bundle source.
  - A JSON schema test.
  - The CI step asserts with `jq`: the bundle is `vendored` with the expected interface, `ok` is false, the missing tool is named, and `loom serve` on the demo starts.
  - The `/usr/bin` dependence is removed with a clean PATH.

## 7. Order of work

1. **Now, one short session:** faults 1–8 of §1, and the product faults beside them. Each is small, and CI is red until fault 1 is fixed.
2. **The harness (§5.2) and the entry point (§5.1).** Everything after this is cheaper, and failures become readable at once.
3. **Reorganise, delete and combine (§5.3, §5.4)** with the new helpers, file by file. Merges shorten the suite as they go.
4. **Missing tests and checks (§5.5, §5.7)**, in the priority order given.
5. **Speed (§5.8) and CI (§5.9).**
6. **`loom doctor` (§6).**

Steps 2–6 are a plan's worth of work. I'd write them up as plan 0.15 if you want them done as a unit. Decisions only you can make are marked in §5.4: `migrate.py` and the legacy `basis: definition` alias.
