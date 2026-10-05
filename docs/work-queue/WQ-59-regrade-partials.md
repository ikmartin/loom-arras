# WQ-59 · The re-grade's partials

**Repo:** loom, loom-lsp

## Trigger

The next round of work on the command line, or a person or agent tripping over one of these findings in use.

## Why deferred

Plan 0.18.6 fixed the re-grade's defects and every finding graded **F**; the findings graded **p** — the command mostly meets the principle and falls short in a case — were left, since each is small and together they are many. They are listed, with the case that shows each, in the three appendices of [the re-grade](../reports/cli-regrade.md): [library](../reports/cli-regrade/library.md), [records, history and reshaping](../reports/cli-regrade/records.md), [tooling, sessions, the AI layer and sync](../reports/cli-regrade/tooling.md), under "What is still wrong", every entry whose row in the grade table reads `p` for that principle.

## Rough design

Take them by principle, as the appendices group them, each with a test reproducing it first: the remaining T2 repetition (one sentence under a heading many times), T4's raw LaTeX titles and implementation words (`fragments`, `via postnote`, preview tokens), T5's counts that disagree between commands and lines over 100 columns on stderr, T6's one-to-four-second silences, and the K2 leftovers (`WHICH` against `--session` for a session, `--why` missing from `ai discard`, `-p1` against `-p0` patches).

Found while fixing the Fs and left for this item: `loom fork` copies a forked node's inner labels, the defect `linearize --fork` had, so a fork can leave a label defined twice; `history shwo` without `--help` says "no such key"; `import --dry-run` names step 0001 where the step will be the next.

## Blast radius

Most of `loom/src/loom/cli/`; no data model.

## Related

[plan 0.18](../plans/0.18-the-command-line.md), §0.18.6.
