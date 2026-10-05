# CLI re-grade, appendix: tooling, sessions, the AI layer and sync

The study's sweep of this part repeated on 2026-10-04 at commit `65ce069`, for the re-grade of plan 0.18 against [the study](../cli-study.md) and its [tooling appendix](../cli-study/tooling.md). The commands are the root (`loom`, `--help`, a group's `--help`, `--version`, an unknown command, `delete`, outside a quilt), `doctor` (with `--agents`), `build`, `check`, `compile`, `serve`, `upgrade`, and every `ai`, `session` and `sync` subcommand. Writing cases ran in fresh copies of the demo quilt (`loom init --demo`, nine copies), of a fresh `loom init` quilt for `ai init`, and of the author's quilt (`relloc`, three copies, each with `[refs]` replaced by `[library] online = false`), never in the originals; `sync` ran against bare repositories made in the scratch directory. Every run went through a `subprocess` harness that records exit code, wall time, the silence before the first line and the longest silence, stdout and stderr separately, line count and widest line: 246 transcripts, kept in the scratch directory and not committed. Author-only commands ran with `CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT` and `AI_AGENT` removed and `XDG_CONFIG_HOME` in the scratch directory, and the guards were graded with `AI_AGENT=1`. Three things went outside the method. The relloc copy that `serve` ran in had `[ai] launch` set to `false`, so that no agent could be started. The first `serve` run was stopped with SIGKILL, because a command started with `&` in a non-interactive shell ignores SIGINT; the harness then reset SIGINT in the child, and every later `serve` stopped cleanly on Ctrl-C in under a second, so this is not a defect of `serve`. Widths that include a path or URL were measured in a scratch directory whose path is 130 columns long, and a grade does not count width that a normal path would not have. Grades are P pass, p partial, F fail and – not applicable; T1–T8 are book 1.10 as it reads today, K is 1.12's K1–K7.

## Grades

| command | was | T1 | T2 | T3 | T4 | T5 | T6 | T7 | T8 | K | worst problem now |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `loom` (no args) | = | – | P | – | p | P | – | P | – | p | `serve` is still "serve arras", and "document workspace" is never explained (K6) |
| `loom --help` | = | – | P | – | p | P | – | P | – | p | the same text as bare `loom`; arras and the document workspace unexplained (K6) |
| a group's `--help`, and a bare group | new | – | P | – | p | P | – | F | – | p | bare `loom sync` prints `Error: Usage: …` and the whole help to stderr, exit 2, with `; see \`loom sync --help\`.` glued to the last command's description (K6) |
| `loom --version` | = | P | – | – | P | P | – | P | – | P | none |
| unknown command | = | P | – | P | P | P | – | P | – | P | none (`Did you mean 'session'?; see …` has stray punctuation) |
| `delete`, `rm`, `remove` | `delete`, `remove`, `rm` (commands that only refused) | P | – | P | P | p | – | P | – | P | none of weight; the refusal is 116 columns |
| outside a quilt | = | P | – | F | P | p | – | P | – | P | names no `loom init` or `cd`; the path makes the line as long as the path |
| `doctor` | = | P | p | p | p | P | P | P | P | P | all 22 ok rows are listed; with no TeX one fix line ten times; `--quilt` to a missing directory advises "fix config.toml" |
| `doctor --agents` | `agent check` | P | p | F | p | P | P | F | P | P | "fill in ai/ai-config.toml (loom ai init writes it)", but `ai init` keeps the commented-out file `loom init` wrote; "codex not found: loom serve cannot start the agent" when the agent is Claude |
| `build` | = | P | p | p | p | F | P | P | P | P | "in cited works (115)" lists four lines that sum to 115, then "… and 111 more" |
| `check` | `check`, `check --no-compile` (now `lint`) | P | p | p | p | F | p | P | P | P | the same "… and 173 more"; on relloc 5.4 s silent before the first line; one sentence repeated 19 times under one heading |
| `compile` | = | P | – | F | p | P | P | P | P | P | a failure is still only `! Undefined control sequence.`, with no macro, line or log |
| `serve` | = | P | – | p | p | p | p | p | – | P | a busy port is a bare errno; after an edit on relloc, 4 s then 7 s with no line; two serves retrigger each other |
| `upgrade` | = | P | P | p | P | p | P | F | P | p | an edited `loom.sty` is overwritten and reported as "wrote loom.sty"; an agent may run it and rewrite its own permission files (K5) |
| `ai annotations` | = | P | p | – | p | P | P | F | P | P | after `ai discard`, "no annotations yet" while three withdrawn annotations exist; the promised status column is severity |
| `ai discard` | = | P | P | – | P | P | P | p | P | p | a repeat run reports "withdrew" again; no `--why`, so every withdrawal reads "no reason given" (K2) |
| `ai drafts` | = | P | P | p | P | P | P | P | P | P | its `next:` command is an unquoted path with a space and fails as printed |
| `ai init` | = | P | P | p | P | p | P | F | P | F | `--agent claude` does nothing on a quilt `loom init` made, and says nothing (K3); an agent may run it (K5) |
| `ai orient` | = | – | P | P | P | p | P | P | – | P | raw markdown lines to 1,487 columns (raw by design) |
| `ai refresh` | = | P | P | F | P | P | P | P | P | P | its conflict `fix:` line, `loom ai refresh Referee Agent.tex`, fails as printed |
| `session close` | = | P | – | F | P | P | P | F | P | p | with nothing active it advises `loom session new "a name"`, which is refused; closing a closed session says "closed" and records it again (K4) |
| `session delete` | = | P | – | p | p | p | P | P | P | P | deleting a deleted session: exit 1, "nothing new can be written to it" |
| `session list` | = | P | p | – | P | P | P | P | P | P | closed sessions are left out without saying so |
| `session new` | `session new`, `ai start` | P | – | P | P | P | P | P | P | P | duplicate titles accepted, which makes the title ambiguous to every other verb |
| `session next` | = | P | P | – | p | P | – | P | P | P | times as UTC `HH:MM`, no date or zone (00:33 at 19:33 local) |
| `session rename` | `session rename`, `ai name` | P | – | P | P | p | P | P | P | p | the session is positional `WHICH` here and `--session` on `next`, `say`, `orient` and `annotations` (K2) |
| `session say` | `session say`, `session send` | P | – | P | P | P | P | P | P | p | a link naming nothing is refused with exit 1, not 2 (K3) |
| `session use` | = | P | – | P | P | p | P | P | P | p | the selector forms of `session rename` (K2) |
| `session watch` | = | P | – | – | p | P | – | P | – | P | times as UTC `HH:MM`, no date or zone |
| `sync documents` | = | P | P | p | p | P | P | p | P | P | "1 document publish to"; adding a selected document says "added" again |
| `sync fetch` | = | P | p | P | p | P | P | p | P | P | no count of what changed; a fetch that found nothing new says "fetched" with the old time |
| `sync incorporate` | `sync prepare`, `sync finish`, `sync incorporated` | P | P | p | p | p | P | P | P | P | a pull that does not apply is refused with git's own `git apply … error: patch failed` text |
| `sync init` | = | P | – | F | F | F | P | p | P | p | accepts the quilt's own upstream (see below); a bad URL is a raw `git clone` line with a temporary path, 474 columns |
| `sync publish` | = | p | – | p | F | p | p | F | P | P | a rejected push prints git's `use 'git pull'` hints, then "Done." |
| `sync status` | `sync status`, `sync patch` | P | P | P | p | P | P | p | P | P | the "prepared" row still names the revision prepared before the incorporation |

Counts, now (35 rows) and in the study (40 rows):

| | P now | p now | F now | P then | ~ then | F then |
|---|---|---|---|---|---|---|
| T1 | 30 | 1 | 0 | 21 | 6 | 10 |
| T2 | 13 | 7 | 0 | 4 | 1 | 8 |
| T3 | 9 | 11 | 6 | 13 | 6 | 16 |
| T4 | 16 | 17 | 2 | 19 | 4 | 17 |
| T5 | 21 | 11 | 3 | 26 | 2 | 12 |
| T6 | 23 | 3 | 0 | 25 | 1 | 7 |
| T7 | 22 | 6 | 7 | – | – | – |
| T8 | 25 | 0 | 0 | – | – | – |
| K | 24 | 10 | 1 | – | – | – |

## Against the study

| old command | old T1–T6 | now (its command) | now T1–T6 | the old worst problem |
|---|---|---|---|---|
| `loom` (no args) | – F – F P – | `loom` (no args) | – P – p P – | fixed: no aliases, groups, stdout, exit 0 |
| `loom --help` | – F – F P – | `loom --help` | – P – p P – | partly: task groups; arras still unexplained |
| `loom --version` | P – – P P – | `loom --version` | P – – P P – | none then |
| unknown command | P – P P P – | unknown command | P – P P P – | none then |
| outside a quilt | P – F F F – | outside a quilt | P – F P p – | not: still no `loom init` or `cd` |
| `doctor` | F F ~ ~ F P | `doctor` | P p p p P P | partly: verdict first and rows wrap; with no TeX the fix line is now repeated ten times |
| `build` | ~ F F F F F | `build` | P p p p F P | fixed: cold 356 s with progress (longest silence 3.5 s), cached 4.2 s; the author's error has file and line |
| `check` | F F F F F F | `check` | P p p p F p | fixed: relloc 25.8 s with progress, verdict first, lines within 100 |
| `compile` | P – F F P F | `compile` | P – F p P P | partly: `--engine troff` refused; a failure still prints only the TeX error line |
| `serve` | P – ~ P P F | `serve` | P – p p p p | partly: relloc ready in 5 s with progress; the busy port is still a bare errno |
| `upgrade` | F ~ F P P P | `upgrade` | P P p P p P | partly: `--dry-run` exists and edited mode files are reported; an edited `loom.sty` is still overwritten |
| `agent check` | F – ~ ~ F P | `doctor --agents` | P p F p P P | fixed: one command, verdict first, exit 0 when unconfigured; its fault now names a command that does nothing |
| `ai annotations` | F F F F P ~ | `ai annotations` | P p – p P P | partly: `--status` is validated and `--all` shows withdrawn ones; the empty state after a discard is still false |
| `ai check` | F F F F F P | gone, nothing replaces it | – | fixed: removed with its mtime method |
| `ai discard` | ~ – – F F P | `ai discard` | P P – P P P | fixed: `--before yesterday` refused, exit 2 |
| `ai drafts` | P P F P P P | `ai drafts` | P P p P P P | fixed: a stale copy names `loom ai refresh`, unquoted |
| `ai init` | F F P P F P | `ai init` | P P p P p P | partly: it writes `ai/ai-config.toml`, but `--agent` cannot fill the one `loom init` already wrote |
| `ai name` | P – P P P P | `session rename` | P – P P p P | fixed: gone |
| `ai orient` | – P P ~ F F | `ai orient` | – P P P p P | fixed: 2.6–3.5 s on relloc, was 51 s |
| `ai refresh` | F – F F P P | `ai refresh` | P P F P P P | fixed: a conflict is "1 conflict left to reconcile; nothing written", exit 1 |
| `ai start` | ~ – P P P P | `session new` | P – P P P P | fixed: gone |
| `session close` | P – ~ P P P | `session close` | P – F P P P | partly: it names a command now, and the command fails |
| `session delete` | P – P P ~ P | `session delete` | P – p p p P | fixed: `--purge` refuses an agent; an ambiguous name lists its matches |
| `session list` | ~ P P P P P | `session list` | P p – P P P | partly: count and `(*)` legend; closed sessions still hidden unsaid |
| `session new` | P – P P P P | `session new` | P – P P P P | partly: the help says `untitled`; duplicate titles still accepted |
| `session next` | P P P ~ F – | `session next` | P P – p P – | not: still `HH:MM`, now visibly UTC |
| `session rename` | P – F P P P | `session rename` | P – P P p P | fixed: ambiguity lists the matches |
| `session say` | P – P P P P | `session say` | P – P P P P | none then |
| `session send` | P – F P P P | `session say` | P – P P P P | fixed: gone; `say` carries the person's marked packet |
| `session use` | P – F P P P | `session use` | P – P P p P | fixed: ambiguity lists the matches, and a middle of an id matches |
| `session watch` | P – P P P – | `session watch` | P – – p P – | none then |
| `sync documents` | P – ~ F ~ P | `sync documents` | P P p p P P | fixed: a missing document exits 2 |
| `sync fetch` | ~ – F F P F | `sync fetch` | P p P p P P | partly: names its next commands and runs no build (0.5 s); still no count |
| `sync finish` | P – P F P P | `sync incorporate` | P P p p p P | fixed: a second run is refused, "no incoming revision" |
| `sync incorporated` | P – – P P P | `sync incorporate` | P P p p p P | fixed: gone; incorporating applies the patch, and `publish` refuses while a pull waits |
| `sync init` | P – F F P P | `sync init` | P – F F F P | partly: no dangerous defaults, a URL is required; raw git errors remain, and the quilt's own upstream is accepted |
| `sync patch` | P – P P F P | `sync status --patch` | P P P p P P | fixed: `--to` an existing file exits 2 |
| `sync prepare` | ~ – ~ F F P | `sync incorporate` | P P p p p P | fixed: gone; no patch file or 305-column line |
| `sync publish` | F – F F P F | `sync publish` | p – p F p p | partly: verdict first and a `--push` hint; the rejection is unchanged |
| `sync status` | F – F F P P | `sync status` | P P P p P P | partly: a verdict now; the stale "prepared" row remains |
| `check --no-compile` | not graded alone | `lint` (other appendix) | – | fixed: refused as an unknown option, and `check --help` names `loom lint` |

## What is still wrong

### Defects that lose data or report a failure as success

- **`sync init` accepts the quilt's own upstream, and `sync publish --push` then publishes over it.** A demo copy made a repository with `origin` a bare repository, then `loom sync init <that origin's URL>`, `loom sync publish`, `loom sync publish --push`: all exit 0. The branch `main` of the quilt's own remote went from `.claude .codex .gitignore .loom AGENTS.md CLAUDE.md CONTRACT.md README.md ai annotations config.toml digests drafting loom.sty nodes refs.bib` to `drafting loom.sty nodes refs.bib`, in a commit "Publish drafting/main.tex from loom". It is not forced, so the old tree is in the history, but whoever pulls gets a quilt with no `config.toml`. This is the study's defect 1, now reached by typing the wrong URL rather than by a default: DR-327 removed the refusal 0.18.1 had added. A fix: `sync init` compares the URL (and the clone's root commit) with every remote of the quilt's repository, when it has one, and refuses a match by name, exit 2.
- **`upgrade` overwrites an edited `loom.sty` and says only "wrote loom.sty".** Appending `% my edit` to a demo copy's `loom.sty` and running `loom upgrade` lost the line; the dry run had said "would write 1 file … loom.sty". Book 11 decides that `loom.sty` is refreshed unconditionally, so the overwrite is by design; what is wrong is that an edit is destroyed without a word. The report should list it under its own heading ("replaced your edited loom.sty; the old one is loom.sty.old") or keep it as mode files are kept.
- **`ai init --agent claude` reports success and configures nothing.** `loom init` writes `ai/ai-config.toml` with every key commented out; `ai init --agent claude` then keeps it ("An existing one is kept") and prints "refreshed the agent layer: 17 files written … next: loom session new", exit 0. `doctor --agents` afterwards: "no agent is configured: fill in ai/ai-config.toml (loom ai init writes it)". Either `--agent` fills a file that is still all comments, or it is refused by name when the file exists.
- **`sync publish --push`, rejected, ends "Done."** On a workspace that had moved: `Error: Publication rejected: git push --porcelain origin 210d7ce…:refs/heads/master: error: failed to push some refs to '…'`, then git's five `hint:` lines ending "use 'git pull' before pushing again", then the `To …` and `[rejected] (fetch first)` lines, then `Done. The prepared revision is kept; run \`loom sync fetch\` …`; exit 2, 277 columns. Nothing was lost (the follow-up fetch, incorporate and push kept both sides), but "Done." and "git pull" both say the wrong thing.

### T1 — lead with the verdict

- `sync publish`: the rejection above. Everything else in this part now leads with a verdict.

### T2 — group, count, then list

- `doctor`: all ok rows are enumerated (22 on the demo) where T3 asks for a count; with TeX absent (`PATH=/usr/bin:/bin`), `fix: brew install --cask mactex-no-gui` appears under ten items.
- `check` on relloc: grouped and counted, but the sentence is repeated under the heading: `N annotation(s) on rl-XXXX no longer match its text` 19 times, `… states no identifier, so loom cannot name the work the same way on another machine` 11 times, `names no result in the digest of …` 11 times, and `drafting/draft4.tex:386 \cite[Def. 2.3]{romagny_GroupActionsStacks2005} …` twice, identical.
- `session list`: shows "5 open sessions" and omits closed ones without "… and 2 closed; --all shows them".
- `ai annotations`: columns are not aligned (`dm-0003  suggestion moderate` against `dm-0003/proof  objection major`).
- `sync fetch`: "fetched 1f115d8 …; it waits for review in Incoming" gives no count; `sync status` knows it is "2 files incoming".

### T3 — every problem names its next command, and the command works

- `session close` with nothing active: `Error: no session is active; loom session new "a name" opens one` (`cli/_common.py:67`). `loom session new "a name"` is refused: `Got unexpected extra argument (a name)`; it takes `--name`. The same message is raised wherever an active session is required.
- `ai refresh` on a conflict: `fix: loom ai refresh Referee Agent.tex` (`adopt.py:811`, `cli/ai.py:495`); as printed it fails, `Got unexpected extra argument (Agent.tex)`. `ai drafts` prints `next: loom ai refresh drafting-ai/Referee Agent.tex` (`cli/ai.py:319`), which fails the same way, and its `--json` `fixes` carry the same string. Names need `shlex.quote`.
- `doctor --agents`: the fault's fix names `loom ai init`, which keeps the file (above). The codex row's fix, "install it if you use it: loom serve starts agents with codex", names nothing and is shown when the configured agent is Claude.
- `doctor --quilt /nonexistent/q`: `fail quilt not inside a quilt: … fix: fix config.toml: every command but init and doctor refuses until it reads` — there is no config.toml to fix.
- `compile` and `check` failures: `drafting/main.tex did not compile: ! Undefined control sequence.` names no macro, file, line or log; `--json`'s `errors` holds the same two lines and no log path. A closure failure in `check --closures all` (`does not compile: ! LaTeX Error: Environment conjecture undefined.  dm-0006`) names no command either.
- `serve` on a busy port: `Error: cannot listen on port 8911: [Errno 48] Address already in use`, no `--port`.
- `sync init` with a bad URL: `Error: git clone --quiet --no-tags <url> <quilt>/.loom/workspace-em9_0qys/clone: fatal: repository '<url>' does not exist`, 474 columns, no fix.
- `sync incorporate` on a pull that does not apply: the advice is right ("Read it with `loom sync status --patch`, bring those files in line in your editor, then incorporate again") but follows `git apply --whitespace=nowarn -: error: patch failed: nodes/dm-0002.tex:3`.
- `sync fetch` under `AI_AGENT=1` advises `loom sync incorporate`, which refuses that caller.
- outside a quilt: `Error: not inside a quilt: no config.toml with a [quilt] table above <path>`, no `loom init` or `cd`.
- `upgrade`: "the new version is beside it as orientation.md.new" on every run; no command resolves the `.new`.
- `session delete` of a deleted session: exit 1, `s-2026-10-05-0005 was deleted; nothing new can be written to it` — a delete is not a write, and the repeat should be "already deleted", exit 0.

### T4 — the reader's words

- `build`, `serve`: "fragments" (`published build/: 4144 fragments rendered, 0 unchanged`, `built 22 fragment(s)`); `build` mixes `dangling-link` and `loom:duplicate-label` code styles.
- `doctor`: `arras bundle  vendored, arras 496db17 interface 1 vendored 2026-10-04T23:17:57Z`; `ok author … tracked quilt author ignored; configure the reviewer in local Settings`.
- `session next`, `session watch`: `00:33 Isaac Martin: …` at 19:33 local — UTC with no zone or date.
- `sync status`, `fetch`, `publish`: hashes as the rows (`integrated: 1f115d8`, `prepared: 44a4eb9`); "Incoming" is a viewer panel never named as such; `sync documents remove drafting/main.tex`: "the primary document workspace document cannot be removed".
- `compile drafting/nope.tex`: "no such key: drafting/nope.tex" for a document.

### T5 — numbers that add up, and the width

- `build` and `check` (`cli/report.py:138`): `hidden = g.size - len(shown)` when a group's count is set. The cited-works group counts diagnostics (115) but lists one line per code (4 lines that already sum to 115), so it prints "… and 111 more; loom lint --json"; `check` prints 7 lines summing to 180, then "… and 173 more". The JSON has the same group (`count` 115, 4 items).
- Counts that disagree between commands on one relloc copy: `build` "1 error in your documents; 115 errors in cited works" and "14 in works nothing cites"; `serve` "130 error(s) -- run loom lint"; `ai orient` "lint: 130 error(s)"; `library check` "16 works nothing cites". "14 in works nothing cites" does not say what it counts.
- `upgrade`: "kept 1 edited file, 1 with a new version beside it to merge" for one file.
- `sync documents`: "1 document publish to".
- `sync init`: 474 columns (above); `sync publish` rejection 277; `ai orient` raw lines to 1,487 (raw by design).

### T6 — alive

- `check` on relloc: 5.4 s with no line while linting, before the first `compiling 1/1` line.
- `serve` on relloc after a one-word edit to `drafting/draft4.tex`: 4.4 s to "rebuilt …; 64 fragment(s) re-rendered", then 6.8 s to "compiled drafting/draft4.tex: ok", with no line between.
- `sync publish` (and its dry run): 2.3–3.7 s silent while it compiles the selected documents.

### T7 — say only what happened

- `ai annotations --session s-2026-09-16-0002` after `ai discard s-2026-09-16-0002`: "no annotations yet"; `--all` lists the three, withdrawn. The help promises "id, target, kind, status"; the line shows kind and severity.
- `session close "json one"` twice: "closed s-2026-10-05-0004" twice, and two `closed` events in `.loom/sessions/index.jsonl`.
- `ai discard s-2026-09-16-0002` twice: "withdrew the annotations of 1 session" twice.
- `sync documents add drafting/outline.tex` twice: "added" twice. `sync fetch` with nothing new: "fetched 1f115d8 …, observed <the earlier time>".
- `sync status` after an incorporation, and after a rejected push: `prepared: 44a4eb9, stamped as main@2, outline@3` — a revision that is no longer what would be pushed.
- `sync init` again without `--publish-main`: silently changes "drafting/main.tex publishes as main.tex" to "… as drafting/main.tex"; the next publish would add a second main document to the workspace.
- `sync publish --push --dry-run`: "holds these 9 files" and lists none.
- `doctor --agents`: "warn codex not found: loom serve cannot start the agent" when the agent configured is Claude and `claude` was found.
- A bare group (`loom sync`, `loom ai`, `loom session`): "Error: Usage: …", exit 2, for what is a request for the group's help; the error suffix lands inside the help text.
- `upgrade`'s JSON says `"ok": false` and the text "upgraded:" for the same run (an edited file to merge); defensible under 12.9, but the text verdict does not say anything waits.

### K — the command line

- **K2.** The session is positional `WHICH` on `session close/delete/rename/use/watch` and `SESSION` on `ai discard`, and `--session` on `session next/say`, `ai orient`, `ai annotations` and `compile`. A reason is `--why` on `session delete` and absent from `ai discard`, whose listing then says "withdrawn: no reason given". `--as` exists on the session verbs and not on `ai discard`.
- **K3.** `ai init --agent` silently ignored (above). `session say` refuses a link that names nothing with exit 1, not 2.
- **K4.** `session close` on a closed session writes a second `closed` record.
- **K5.** Under `AI_AGENT=1`, `upgrade` and `ai init` run and rewrite `.claude/settings.json` and `.codex/rules/loom.rules`, the files that say what an agent may run, and `loom.sty`; `sync init` re-pairs the workspace and `sync documents` changes the selection. None is in the agent's allowed list in `ai/rules.md`, which calls every other command the author's, but only eleven acts are guarded.
- **K6.** `loom --help` still describes `serve` as serving "arras" and `sync` as a "document workspace", both unexplained; a bare group answers with an error.
- `session new` accepts a duplicate title, after which that title is ambiguous to `use`, `rename`, `close`, `next` and `say`.

### Behaviour, beyond output

- `check --closures all` fails on the demo: `dm-0006` and `dm-0007` live in `drafting/outline.tex`, which defines `conjecture` and `question`, but their closures compile with the default document's preamble (`Environment conjecture undefined`). The study found the same with `--bundles all`.
- Two `serve`s on one quilt are allowed and retrigger each other: each logs "rebuilt after change to .loom/serve.json; 0 fragment(s) re-rendered" when the other writes its state.
- A relloc copy whose `ai/` is older than this loom serves an orientation naming `loom refs …`, `loom ai start` and `loom ai name`; `doctor` warns and `upgrade` fixes it, so this is upkeep, not a defect.

## What got worse

- **Regressions of behaviour.**
  - `sync init` no longer refuses the quilt's own upstream: 0.18.1 added the refusal and DR-327 removed it with `--remote`, so the study's defect 1 is reachable again by naming the wrong URL.
  - `session close` with nothing active now names a command, `loom session new "a name"`, that is refused (T3 ~ to F).
  - `doctor --agents` replaces `agent check`'s "fill in ai/ai-config.toml" with "(loom ai init writes it)", a command that does nothing in that state (T3 ~ to F).
- **New problems plan 0.18 introduced.**
  - The output layer's "… and N more" counts the group's total minus the lines shown even when the lines are themselves counts (`cli/report.py:138`), on `build` and `check`.
  - The click usage error turned into one `Error:` line also catches a bare group, so `loom sync` prints its help as an error with the suffix inside it.
  - `ai refresh`'s and `ai drafts`' new next-command lines name an unquoted path and fail when pasted.
  - `ai init --agent` is new and silently has no effect on a quilt `loom init` made.
  - `sync incorporate` passes `git apply`'s raw error into its refusal, and `sync init` run again resets `--publish-main` without saying so.
  - `upgrade`'s new summary counts one file twice.
- **Grades lower than the study's for unchanged output**, from the sharpened T text or a stricter reading rather than a change: `serve` T4 and T5 ("fragment(s)", "130 error(s)" with no split); `session watch` T4 and `session next` (the same UTC `HH:MM` the study graded ~ on `next` only); `session list` T2 (closed sessions hidden, which the study named but passed); `session delete` T3 and T4 (the repeat-delete message); `session rename` and `use` T5 (the new ambiguity line runs to 123 columns with two titles).
