# The v0.1 study

A study of loom on `main` at commit 71621877, made on 13 November 2026 to decide what v0.1 is, where loom stands against it, and how to get there. About forty investigators, each a separate agent, read the code, ran loom on copies of real quilts, played first-time users, built three prototypes, and then attacked the plan that came out. This directory is the evidence. It is history, never normative: the plan is `docs/plans/0.32-v0.1.md`.

## Read in this order

| file | what it is |
|---|---|
| `docs/plans/0.32-v0.1.md` | The plan: what v0.1 is, the bar, what goes in, decisions, order of work, workstreams, the author's queue |
| `state.md` | Where loom stands today, gate by gate, each claim marked reproduced, measured, read or checked |
| `codebase.md` | The code, tests and process evaluated, with changes ranked for before and after v0.1 |
| `register.md` | 456 findings from nineteen of the reports under thirteen headings, each ending in the work the reports propose and the files it touches |
| `register-notes.md` | Where reports disagree and how each was settled; decisions for the author; the verdict on each proposed cut; the weakest claims; what only the author can do; what a first-time user could and could not do |

The register predates the last round. Eight later reports are not in it and win where they differ: `spike-door.md`, `spike-speed.md`, `check-labels.md`, `check-changed.md`, `tinytex.md`, `security.md`, `explore.md` and `claude-code-docs.md`.

## The reports under `raw/`

| round | reports |
|---|---|
| Audits by reading and measuring | `core.md` (Python architecture), `viewer.md`, `tests.md`, `inventory.md` (every operation on every surface), `speed.md`, `process.md`, `attach.md`, `install.md`, `lean.md` |
| Trials on a running loom | `review.md`, `library.md`, `quant-findings.md` (the author's month of use, checked item by item), `walk.md` and `walk-small.md` (two first-time users), `live.md` (install and a real agent client), `small-model.md`, `safety.md`, `lean-trial.md`, `tinytex.md`, `explore.md`, `security.md` |
| Checks of the claims most work rested on | `cuts.md` (each proposed cut attacked), `check-changed.md`, `check-labels.md`, `spike-door.md`, `spike-speed.md`, `claude-code-docs.md` |
| The plan attacked | `redteam-execution.md` (its appendix B, which workstream owns which file, is part of the plan), `redteam-coverage.md`, `redteam-facts.md` |

## What can be run again

- `safety-harness/keep/test_write_safety.py`: the ten-second test of writes to a person's files, with nine expected failures for faults open on `main`; `repro/` and `crash/` hold one script per fault, and `harness/` the random-sequence runner.
- `spikes/one-door.patch`, `spikes/speed.patch`, `spikes/labels.patch`: the three prototypes as patches against 71621877. The anchoring harness is inside `labels.patch`.
- `harnesses/`: the scripts behind the other trials, among them the browser driver the first-time-user walks used (`harnesses/walk/driver.mjs` with `DRIVER.md`), the history replay behind `check-changed.md`, and the timing scripts.
- `shots/`: the trials' screenshots. They are large and need not be committed.

The quilt copies the trials ran on were in a session's scratch directory and are gone; the papers the anchoring harness used are not in git.

## Limits to keep in mind

- No trial used a real model inside Claude Code's own connection to loom, and none ran in the desktop app's Code tab or in Codex.
- Both first-time users were AI models.
- Every decision that belongs to a person in the Lean trial was simulated.
- Timings were taken on a machine the study itself had loaded heavily.

## Proposed and not applied

The design's opening was corrected with this study (`docs/design/README.md`). "The one idea" at the head of `docs/design/principles.md` still speaks only of atomicity and LaTeX. A principle changes by the author's edit; the wording proposed is:

> Loom is a tool for understanding mathematics, built on atomicity married to as-close-to-pure LaTeX as possible. Mathematics is a graph of statements and proofs; each statement is addressable by a permanent identifier; dependencies are read from the text the author already writes; and the LaTeX compiles with or without loom. What a person or an AI says about the mathematics attaches to the statement it concerns, so that understanding accumulates where it can be found.
>
> Loom calls no model and is complete without one. It is built to be excellent with an AI, whose mathematics and documents are welcome in it, and much of its design exists to keep a clear boundary around what an AI may change.
