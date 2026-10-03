# CLI study, appendix: tooling, sessions, the AI layer and sync

The sweep of `doctor`, `build`, `check`, `compile`, `serve`, `upgrade`, `agent check`, every `ai`, `session` and `sync` subcommand, and the root (`loom`, `--help`, `--version`, an unknown command, outside a quilt), made 2026-10-02 at commit `468c9af` for [the study](../cli-study.md). Writing cases ran in copies of the demo quilt and of the author's quilt (`relloc`: 64 results of the author's, 4,089 nodes counting digests); `sync` ran against bare repositories made for the purpose. 257 transcripts. Grades: P pass, F fail, ~ partial, – not applicable.

## Grades

| command | purpose | T1 | T2 | T3 | T4 | T5 | T6 | worst problem |
|---|---|---|---|---|---|---|---|---|
| `loom` (no args) | command list | – | F | – | F | P | – | 7 of 43 entries are aliases repeating their target's text; truncated descriptions; stderr, exit 2 |
| `loom --help` | the same, exit 0 | – | F | – | F | P | – | no task groups; `serve` is "serve arras" with arras never explained |
| `loom --version` | version | P | – | – | P | P | – | none |
| unknown command | refusal | P | – | P | P | P | – | none ("Did you mean 'session'?") |
| outside a quilt | refusal | P | – | F | F | F | – | 172-column absolute path; no `loom init` or `cd` |
| `doctor` | check machine and quilt | F | F | ~ | ~ | F | P | verdict last; 143-column rows; with no TeX one fix line nine times |
| `build` | scan, render, publish `build/` | ~ | F | F | F | F | F | relloc: `--force` 955 s and cached 54 s silent; 139 errors without location |
| `check` | lint, compile masters (and bundles) | F | F | F | F | F | F | relloc: 64 s silent, then `check: FAILED` last; 279 stderr lines up to 339 columns |
| `compile` | latexmk one target | P | – | F | F | P | F | a failure prints only `! Undefined control sequence.`; `--engine troff` accepted |
| `serve` | build, watch, view | P | – | ~ | P | P | F | relloc: 62.6 s silent after "building the quilt ..."; a busy port gives a bare errno |
| `upgrade` | refresh generated files | F | ~ | F | P | P | P | overwrites an edited loom.sty silently; an edited CLAUDE.md unreported; no dry run |
| `agent check` | will serve launch an agent | F | – | ~ | ~ | F | P | verdict last; a 513-column line; exit 1 where doctor says ok |
| `ai annotations` | list annotations | F | F | F | F | P | ~ | `--status discarded` never matches; after a discard, "no annotations yet" |
| `ai check` | mtime audit of a session | F | F | F | F | F | P | 57 identical errors on a freshly copied quilt |
| `ai discard` | flag annotations ignored | ~ | – | – | F | F | P | `--before yesterday` discards every session |
| `ai drafts` | agent copies and staleness | P | P | F | P | P | P | a stale copy names no `loom ai refresh` |
| `ai init` | write `ai/` and vendor files | F | F | P | P | F | P | never writes ai-config.toml |
| `ai name` | retitle a session | P | – | P | P | P | P | duplicates `session rename` |
| `ai orient` | agent orientation and live state | – | P | P | ~ | F | F | relloc: 51 s silent on every call |
| `ai refresh` | update an agent copy | F | – | F | F | P | P | reports a conflict as "already up to date", exit 0 |
| `ai start` | open a session | ~ | – | P | P | P | P | prints a bare id; duplicates `session new` |
| `session close` | end a round | P | – | ~ | P | P | P | "no session is active" with no next command |
| `session delete` | tombstone or purge | P | – | P | P | ~ | P | an agent can purge; an ambiguous name is "no match" |
| `session list` | list sessions | ~ | P | P | P | P | P | no count or `*` legend; closed sessions hidden unsaid |
| `session new` | open a session | P | – | P | P | P | P | `untitled`, against the help; duplicate titles accepted |
| `session next` | agent waits for messages | P | P | P | ~ | F | – | times as HH:MM with no date |
| `session rename` | retitle | P | – | F | P | P | P | an ambiguous name is "no match" |
| `session say` | agent posts | P | – | P | P | P | P | none (its link checking is good) |
| `session send` | person posts | P | – | F | P | P | P | its hint names `watch`, the wrong command |
| `session use` | switch the active session | P | – | F | P | P | P | an ambiguous name is "no match" |
| `session watch` | person tails a session | P | – | P | P | P | – | none |
| `sync documents` | choose published documents | P | – | ~ | F | ~ | P | a nonexistent document exits 1 |
| `sync fetch` | fetch Overleaf changes | ~ | – | F | F | P | F | no change count, no next command; a full build runs silently |
| `sync finish` | checked incorporation | P | – | P | F | P | P | a second run reports success again |
| `sync incorporated` | record a pull | P | – | – | P | P | P | checks nothing; caused a silent revert |
| `sync init` | pair the remote | P | – | F | F | P | P | dangerous defaults; raw git errors |
| `sync patch` | print the incoming diff | P | – | P | P | F | P | `--to` an existing file exits 1 |
| `sync prepare` | write a pinned patch | ~ | – | ~ | F | F | P | one 305-column line with a 40-hex patch name |
| `sync publish` | project and optionally push | F | – | F | F | P | F | verdict last; a rejection advises `git pull`, then "Done." |
| `sync status` | show sync state | F | – | F | F | P | P | hashes with no verdict; a stale "Prepared" block after finish |

## Findings by command

**Root.**
- **Bare `loom`.** Prints the help to stderr and exits 2.
- **Aliases listed as commands.** Seven aliases repeat their target's text (`delete`/`remove`/`rm`; `downstream`/`pop`/`reach`/`unravel`).
- **Truncated descriptions.** For example `agent The agent loom serve may start for a turn:...`, `sync Prepare and review a source-only document workspace; the...`.
- **No grouping.** Commands are alphabetical, with no task groups.
- **Outside a quilt.** `Error: not inside a quilt: no config.toml with a [quilt] table above /private/tmp/…` (172 columns), with no next command.

**doctor.**
- **What works.**
  - 1.2–1.5 s.
  - Exit codes are right: 0, 2 on failure, 2 under `--strict` with a warning.
  - The JSON matches 12.1.
  - A bad `config.toml` is well diagnosed.
- **Verdict last (T1).** `ok (3 warnings)` or `failing: latexmk, pdflatex, dvisvgm, engine (9 warnings)` comes after 20–40 rows.
- **Ungrouped (T2).** All 22 ok rows are listed. With no TeX, one fix line appears under nine tools.
- **Too wide (T5).** Rows are 143 columns because of an absolute-path column.
- **Internal wording (T4).** `arras bundle  vendored, arras 320e399 interface 1 vendored 2026-10-02T20:42:15Z`.
- **Fixes that name nothing.**
  - `fix: install it if you use it: loom serve starts agents with codex` names no command.
  - An `ok` author row asks for an action.
- **Disagrees with `agent check`.** It reports the demo as `ok agent none configured, launch off`; `agent check` exits 1 for the same state.

**build.**
- **No progress (T6).** On relloc, cached took 54.5 s and `--force` 955 s, with nothing printed until the end. There is no progress code anywhere in `src/loom`.
- **Errors without location (T2/T3/T4).** One per line, with no file or node:

  ```
  error   dangling-link                        \ref{lem:spaces} refers to no node or label
  error   duplicate-id                         label behrendfantechiIntrinsicNormalCone1997-sec-2 is defined twice
  ```

  - Counts: duplicate-id 88, dangling-link 25, loom:duplicate-label 19, loom:unknown-environment 6, loom:environment-spans-files 1.
  - Some lines are exact duplicates, printed four times.
  - Nearly all come from digests, unsaid.
  - The `loom:` prefix is inconsistent.
- **Summary (T4/T5).** `rendered 4143 fragment(s), 0 unchanged; 4089 nodes, 3204 keys; 139 error(s)` uses undefined words, counts digests among the nodes, and gives no hint to `serve`.
- **Cache.** The cache key includes loom's code in a checkout, so any loom change re-renders everything.
- **Bad keys.** `--keys nope-9999` exits 0.

**check.**
- **Contradictory verdict, last (T1).** On relloc, stdout is `ok drafting/draft4.tex` then `check: FAILED`; the reason is in 279 stderr lines.
- **Slow and wide.** 64.6 s silent; 339 columns.
- **Plan wording in help.** `--bundles … (stale needs the ledger, milestone M3)`.
- **The demo fails `--bundles all`.** `error loom:bundle-failed bundle dm-0006: ! LaTeX Error: Environment conjecture undefined.` Bundles use the default document's preamble (book 9), and `dm-0006` lives in `outline.tex`.

**compile.**
- **Success.** `compiled drafting/main.tex -> build/main/ (pdflatex)` names the directory, not the PDF.
- **Failure without location.** `FAILED drafting/main.tex: ! Undefined control sequence.` names no macro, file, line or log.
- **Slow.** 53.5 s silent on a fresh relloc compile.
- **Withdrawn noun.** `compiled bundle dm-0002`.
- **No validation.** `--engine troff` exits 0, saying "(pdflatex)". `compile dm-0002 --draft F` ignores the key.

**serve.**
- **Good start.** The URL and Ctrl-C come first, then one line per change.
- **Slow start.** On relloc, "building the quilt ..." then 62.6 s silent.
- **Busy port.** `Error: cannot listen on port 8898: [Errno 48] Address already in use`, with no `--port` hint.
- **Two serves on one quilt.** Allowed, and they retrigger each other.

**upgrade.**
- **Edited loom.sty overwritten.** It printed "wrote loom.sty".
- **Edited CLAUDE.md ignored.** Neither refreshed nor reported.
- **Unresolved `.new` files.** `kept ai/orientation.md (edited); the new shipped version is beside it as ai/orientation.md.new` repeats on every run, and no command resolves the `.new`.
- **No dry run.**
- **Adds nothing new.** Never adds ai-config.toml or skills.

**agent check.**
- **Verdict last.** It is the last of seven lines.
- **Width.** The `prompt:` line is 511–513 columns.
- **Wrong exit code.** It exits 1 in the normal unconfigured state.
- **Asks for a file nothing creates.** "fill in ai/ai-config.toml".

**ai annotations.**
- **Unaligned and uncounted.**
- **Wrong column.** The help promises status; the output shows severity.
- **`--status discarded` never matches.** Discarded annotations keep status `open`, and the display word is "withdrawn".
- **Wrong empty state.** After a discard it says "no annotations yet".
- **No validation.** `--severity huge` and `--status bogus` are accepted.

**ai check.**
- **False alarms.** A freshly copied demo gave 57 lines of `error loom:agent-wrote-outside-run <path> changed after the session opened`, at 144 columns, exit 1, with no count or verdict.
- **The method cannot work.** Modification times cannot attribute a write to an agent.

**ai discard.**
- **No date validation.** `--before yesterday` discarded every session, exit 0.
- **No counts.** Re-discarding repeats the same line.
- **Scope.** `--target dm-0003` discarded the whole session.
- **Naming.** The usage says `[RUN]` and the error `SESSION`; `--author` here is a filter.
- **No agent guard.**

**ai drafts.**
- **Empty state.** Good.
- **Stale line.** `drafting-ai/Referee Agent.tex  from drafting/main.tex  stale: dm-0002 changed; the prose between nodes` names no `loom ai refresh`.
- **Help gap.** `--json` has no help.

**ai init.**
- **No ai-config.toml.** It is never written.
- **Silent skips.** Existing CLAUDE.md and AGENTS.md are skipped without a word.
- **`--skills` refused.** Once `ai/` exists, it says "run loom upgrade", which does not write skills.
- **Noisy.** 17–19 `wrote` lines.
- **Book disagrees.** 12.11 says `init --ai` was folded into `ai init`.

**ai start and ai name.**
- **Bare output.** `ai start` prints a bare id and does not say the author's active session was displaced.
- **Untitled default.** No name gives `untitled`.
- **Duplicates.** Same as `session new` and `session rename`.

**ai orient.**
- **Slow.** 51–52 s silent on relloc, every call; it is the first command an agent runs.
- **Good content.**
- **Very long lines.** Up to 1,469 columns, in markdown meant for an agent.

**ai refresh.**
- **Conflict reported as success.** It prints `AI draft is already up to date` then `dm-0002`, exit 0, while `--json` says `"conflicts": ["dm-0002"]`.
- **Wrong argument, unclear error.** Passing the working document gives `Adoption requires a live AI draft`.

**session list, new, use, rename, close, delete.**
- **Ambiguity reported as no match.** `session use "Referee section 2"` with two such sessions says `no session matches`. `sessions.resolve` returns None on ambiguity; `_common.find_session` names the matches.
- **Titles.** `untitled` is the default, and duplicate titles are accepted.
- **`list`.** No count or legend.
- **`close`.** With nothing active, it names no next command.
- **`delete`.** Under an agent environment, `--purge --yes` erased three annotations.

**session send, say, next, watch.**
- **Exemplary refusal.** The agent identity refusal names the marker, the flag and an example.
- **`say`.** Its link checking is good.
- **`send` points the wrong way.** It says `Start one with: loom session watch`, but watching answers nothing.
- **Asymmetry.** A person is refused `say`; an agent may `send --as "Helper AI"`.
- **`next`.** Shows HH:MM with no date.
- **`watch`.** Works.

**sync.**
- **`init` defaults.** `--remote origin --branch main` replaced the quilt's `origin/main` tree on `publish --push` (book 4.6 names `overleaf`/`master`).
- **`init` errors.** They are raw git, exit 1, with no fix named.
- **`incorporated --yes` checks nothing.** The next push reverted the coauthor. Without a terminal it prints `Aborted!`, exit 1.
- **`publish`.**
  - Verdict last, after `Local ref: refs/loom/publication` and a 40-hex commit.
  - No `--push` hint.
  - A rejected push mixes git's `use git pull` with loom's "Done.".
- **`fetch`.** `Document workspace incoming 5a1f17275fb7 observed …; review updated` gives no count and no next command, and runs a silent build.
- **`status`.** Hashes and refs, no verdict, and a stale "Prepared" block.
- **`prepare`.** One 305-column line: `git apply '/abs/path/build/incoming/<40hex>.patch'`.
- **`finish`.** A repeat run reports success again.
- **Exit codes.** `documents` with a missing document, and `patch --to` an existing file, exit 1.
- **No `--json` and no agent guard** on any of the nine.

## Structural problems

- **S1. Duplicate session commands.** `ai start` and `ai name` duplicate `session new` and `session rename`.
- **S2. Overlapping commands.** `build`, `check`, `compile`, `lint`, `doctor` and `serve` overlap with no stated division.
- **S3. "check" means three things.** `loom check`, `ai check` and `agent check`.
- **S4. Two posting verbs.** `say` and `send` write to one inbox.
- **S5. Two incorporation paths**, one of them unchecked.
- **S6. Three AI setups, none complete.**
- **S7. Uneven agent marking and guards.**
  - The audience is invisible.
  - The guard (`refuse_under_agent`) misses purge, discard, `sync incorporated` and `sync publish --push`.
  - An agent's `ai start` moves the shared active session.
- **S8. Naming.**
  - The session selector has five forms.
  - Identity is `--as` on four verbs and `--author` on five; on `ai discard`, `--author` is a filter.
  - One state has three words: discard, withdrawn and discarded.
  - One object has four names: AI draft, agent copy, `drafting-ai/`, `draft --ai`.
  - "bundle" is still in output.
  - "document workspace" is never explained.
- **S9. `--json` is missing** across build, check, compile, upgrade, agent check, most ai and session writers, and all of sync.
- **S10. Exit codes break 12.1.**
  - Exit 1 for sync environment errors, `patch --to` an existing file, `documents add` of a missing file, `incorporated` without a terminal, a rejected push, and `agent check` unconfigured.
  - Exit 0 for unknown `--keys`, an invalid `--engine`, a garbage `--before` and a garbage `--severity`.
- **S11. No input validation.**
- **S12. Two session resolvers.** Neither matches the middle of an id, which 12.1 promises.
- **S13. `ai check` relies on modification times.**
- **S14. Scan performance.** `Dependencies.__init__` → `display_span` (719 calls) → `tokenize.env_tree` (772 calls): 47.5 s of a profiled 51.6 s run.
- **S15. Top-level help.** It needs groups and hidden aliases.
- **S16. Book and code disagree.**
  - 12.11 on `init --ai`.
  - 12.2 on `session new`'s title.
  - 12.1's ambiguity rule.
  - 12.2 on `ai annotations`.
  - 12.2 on `upgrade`.
  - 11 on `ai refresh`'s report.
  - The `check` help's "milestone M3".
  - 4.8 and 9 still name `promote`.
  - Bundles use the default document's preamble.
- **S17. `sync init` defaults** against 4.6.

## Workflows

1. **Set up a quilt.**
   - Commands: `init [DIR] [--from paper.tex | --demo] --ai claude [--launch-agents] [--git]`, `doctor`.
   - Guesses:
     - `next:` does not suggest `serve`;
     - `--ai` exists only at init;
     - sync later needs a repository with a remote.
2. **Build and view it.**
   - Commands: `serve [--open]`, `compile [TARGET]`, `check` for CI.
   - Guesses:
     - `build` is unnecessary for a person who runs `serve`;
     - each step is a silent minute on a real paper;
     - a compile failure leaves the person to find the log.
3. **Work with an agent in a session.**
   - The person: `session new`, `session send`, `serve` (needs `[ai] launch = true` and `ai/ai-config.toml`), `session watch`.
   - The agent: `ai orient`, `ai start`, `session next`, `ai annotations`/`annotate`, `draft`/`ai drafts`/`ai refresh`, `session say`.
   - Afterwards: `ai check`, `ai discard`, `session close`.
   - Guesses:
     - a reply needs a config edit, a hand-written launcher file and a running serve, yet `send` points at `watch`;
     - which verbs are the agent's;
     - two names for each act.
4. **Publish to Overleaf.**
   - Commands: git init and commit, then `git remote add overleaf URL` and `git fetch overleaf`, then `sync init --remote overleaf --branch master [--publish-main main.tex]`, `sync documents`, commit, `sync publish`, `sync publish --push`.
   - After a coauthor's edit: `sync fetch`, `sync status`/`patch`, `sync prepare`, `git apply`, `sync finish` (or the unchecked `incorporated`).
   - Guesses:
     - both `init` flags are effectively required;
     - `--publish-main` is not detected;
     - no step names the next;
     - a rejection advises `git pull`.

## Keep

- **Doctor's model.** ok/warn/fail with a fix line and an exact JSON shape; the verdict moves to the top.
- **Two refusals that name everything.** The agent identity refusal and `session say`'s link checking.
- **Empty states.** Those that name a command.
- **`serve`'s output.** Its line protocol and `session watch`'s header.
- **`session delete`.** Its tombstone explanation, and `--purge` needing `--yes` and giving a count.
- **`sync publish`'s safety.** It refuses uncommitted inputs and never forces a push.
- **Joining a session.** `ai orient --session` as the one way an agent joins.
- **"Did you mean …?"**
- **`compile --with` and `--draft`** for previews that leave the quilt untouched.
