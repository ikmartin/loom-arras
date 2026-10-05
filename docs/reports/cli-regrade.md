# The loom command line, re-graded after plan 0.18

The CLI study ([cli-study.md](cli-study.md), commit `468c9af`, 2026-10-02) repeated on the command line plan 0.18 built (commit `65ce069`, 2026-10-04), as the plan's Verification asks: the same method, the same three sweeps, the same scale, every command run in realistic cases on copies of the author's quilt (offline) and of the demo, 846 transcripts. The per-command grades are in the appendices: [library](cli-regrade/library.md), [records, history and reshaping](cli-regrade/records.md), [tooling, sessions, the AI layer and sync](cli-regrade/tooling.md). No code was changed.

## The verdict

The output is fixed and the surface is mostly fixed; what is left is correctness at the edges, much of it in what 0.18 added. Of 600 T1–T6 grades the study gave 188 fails; of 486 now there are 26. Every command leads with its verdict, groups what repeats, fits the screen, and answers `--json` with the same report. The slow commands are fast or show that they work: a cold build of the author's quilt takes 356 s with a progress line every 2 s (955 s, silent for minutes, before), a cached build 4.2 s (54 s), `ai orient` 2.6 s (51 s). But the re-grade found **eight defects that lose data or report a failure as success**, five of them introduced or reopened by 0.18, and a class of advice that names a command which then fails.

## The grades

Rows are commands: 100 in the study (counting aliases and the refusing commands), 81 now. P pass, p partial, F fail.

| principle | study P / p / F | now P / p / F |
|---|---|---|
| T1 verdict first | 51 / 13 / 30 | 71 / 4 / 0 |
| T2 group, count, list | 7 / 7 / 21 | 30 / 16 / 1 |
| T3 every problem names its next command | 26 / 23 / 38 | 24 / 30 / 14 |
| T4 the reader's words | 33 / 15 / 51 | 38 / 39 / 4 |
| T5 numbers add up, fit the screen | 53 / 13 / 31 | 49 / 27 / 3 |
| T6 alive when slow | 25 / 14 / 17 | 24 / 17 / 4 |
| T7 say only what happened | — | 42 / 22 / 16 |
| T8 machine output carries the text | — | 63 / 5 / 0 |
| K1–K7 the command line | — | 39 / 36 / 6 |

T3 and T7 are where the remaining fails sit: advice that names a command that fails when run, and verdicts that claim more than happened. Of the study's per-command worst problems, the appendices mark most fixed; the library's 29 are 17 fixed, 7 partly, 5 not.

## Defects that lose data or report a failure as success

1. **`sync init` accepts the quilt's own upstream again**, and `sync publish --push` then replaced that branch's tree with the paper's sources alone, dropping `config.toml`, `ai/`, `.loom/` and the rest. 0.18.1 refused it; the sync rewrite (DR-327-ikmartin) dropped the refusal. A mistyped URL is enough. (tooling)
2. **`library drop --work W --yes` erases verified records** while saying verified nodes "are not touched"; the next `library update W --redo` then overwrites the author's verified rendering without a word. (library)
3. **`upgrade` overwrites an edited `loom.sty`**, reporting only "wrote loom.sty". (tooling)
4. **`linearize --fork` reports success over a broken quilt**: exit 0, "typesets to the same text", while it copied `\label{eq:fix}` so `lint` then finds two errors, one in a document it never touched. (records)
5. **A deleted duplicate comes back**: removing a duplicate entry as `check` and `update` advise makes the next `update` add a new entry and a second 96-result digest; `ignore` first says "set aside" and does not prevent it. (library)
6. **`library update` offline says it fetched 52 sources and 67 PDFs and extracted 52 digests**, and that 9 works need the author when `library` lists 3. (library)
7. **`ai init --agent claude` configures nothing and reports success**, because `init` already wrote a commented-out `ai-config.toml` that `ai init` never overwrites. (tooling)
8. **A rejected `sync publish --push` prints git's hints and then "Done."** (tooling)

Lesser untruths: `ai annotations` says "no annotations yet" after a discard; `status --explain` says "never accepted" of keys another reviewer accepted; `deps --closure` says "depends on nothing" after `deps` listed two; `relate --session X` records X as the relation's author; `--json` reports `"exit": 0` where the process exits 2 on an unknown `--session`.

## What 0.18 made worse

- **`library add`'s identity check turns away the author's real PDFs**: "Behrend does not lead its byline" on a page reading "K. Behrend1 , B. Fantechi2" — superscript affiliation marks break the byline match, and none of the 39 PDFs in the author's `refs/` would be filed. The rule is right; its byline reading is not. The wrong Olsson PDF is still filed, still unreported by `check`, and `add --for` to replace it answers "already in loom's store".
- **Guards by consequence (K5) are incomplete**: under an agent marker, `stamp`, `fork`, `mv`, `import`, `linearize`, `atomize`, `deloom`, `revert`, `init`, `upgrade` and `ai init` run and record the author as the actor; `new` writes the author's name into the node.
- **Advice that fails when run**: `session close` with nothing active suggests `loom session new "a name"` (it takes `--name`); `doctor --agents` says `ai init` writes the agent config, which it keeps; paths with spaces printed unquoted; after `atomize --key` or `history restore`, `status` advises a `fork` that would make things worse.
- **The list cut miscounts**: "… and N more" after group lines that already sum to the total (`cli/report.py:138`), in `build`, `check` and `lint`.
- **Click's own surface leaks**: removed names are answered with guesses (`review` → "revert?"), a mistyped `library` subcommand is read as a WORK, `history shwo --help` prints help, a bare group prints its help as an `Error:`.
- **Readers validate `--session` after printing**; `library locate --page 999` crashes with a traceback; `sync incorporate` passes raw `git apply` errors through; re-running `sync init` silently resets `--publish-main`.

## What is fixed

The output layer (T1, T2, T5, T8 nearly everywhere), the speed (T6 on every long command but `atomize` and `linearize` on a real quilt, silent for 42 s and 31 s, and `library check` for 15 s), the study's twelve defects of part two (revert recording, `inline`, hidden and silently created conflicts, the review build, scan duplicates, verified results on `--force`, consent), the aliases and duplicate commands (K1), one flag per idea outside a few leftovers (K2), the help by task (K6), and the library's shape: one group, a report of what waits, ranked search, honest states.

## Recommendation

A short plan of fixes, defects first, each with a test that reproduces it — items 1 to 8 above, then the byline reading in `add`, K5 for the history writers, the failing advice, the cut arithmetic and click's leaks — and the six worst T6 waits. None of it needs a redesign; most are a missing check or a wrong sentence.
