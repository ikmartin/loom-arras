# Agents working in loom-arras

This is one repository holding five tools and the documents that govern them: `loom` (Python, in `loom/`), `arras` (Svelte, in `arras/`), and the three editor clients `loom-lsp/`, `loom-nvim/` and `loom-vscode/`. Each keeps its own build, tests and release; a change that crosses them is one branch and one pull request. Read in this order:

1. **`docs/design/README.md`: start here.** What loom is for, the three people every decision is tested against (the Learner, the Explorer, the Author), how to judge a change, and what is decided but not built. Then `principles.md`, `model.md`, `agents.md` and `invariants.md` beside it as the work needs them. Judge a change against the principles and cite them by name.
2. `docs/work-queue/README.md`: deferred work, each item with the observable trigger that says when it becomes worth doing. It is not an ordered queue; read the triggers, not the order. If no trigger has fired and nobody has asked for something, there is no work waiting, and you should ask rather than invent some.
3. `docs/specs/`: the formats — the loom–arras interface, the source contract, digests, diagnostics. A spec wins over the design where a shape is concerned; the design wins on what a thing means.
4. `docs/contributing.md`: how to build, test, verify and release.
5. History, which is never normative: `docs/book/` (the frozen design book and its decision records), `docs/deviations.md`, `docs/plans/` and `docs/reports/`. Read them for why something was done, not for what to do now.

Rules that are not negotiable:

- **The design is being discovered.** `docs/design/` records current thinking, not a contract. When implementation teaches you that it is wrong, correct it in the same change and say why in the commit message. Put a question you cannot settle beside the design it affects, under a paragraph that begins **Open.**, and mark anything decided but not implemented **(not built yet)**. Nothing unbuilt may read as built.
- **Invariants change deliberately.** An entry in `docs/design/invariants.md` records a failure that happened. Change one only when the person you are working for agrees, and add a dated line to its entry saying what changed and why.
- **Principles live in `docs/design/principles.md` and nowhere else.** Change one by editing it, with the reason in the commit message; add one as a heading at the end of its set, then run `python3 scripts/checks/principles.py --write`. Names are permanent. Elsewhere, cite a principle by its name (V3) rather than restating it.
- Never edit `docs/book/` or `docs/deviations.md`; they are frozen history. Decision records are no longer written: the why of a change goes in its commit message.
- Never edit anything under `~/notes/`. Paper sources are copies under `tests/fixtures/`; quilts built from them live under `demos/` and are gitignored.
- Every LaTeX compile in a test runs in an isolated environment (empty HOME, TEXMFHOME, TEXMFLOCAL, TEXMFVAR, TEXMFCONFIG; no TEXINPUTS) with the quilt root as cwd, so a test never passes because of a file elsewhere on the machine.
- Loom changes an author's file only when the author incorporates a change (P7); tests enforce it.
- Adding a queue item means a row in `docs/work-queue/README.md` and a `WQ-NN-<slug>.md` beside it, with an **observable** trigger — a measurement crossing a threshold, a capability existing, a dependency landing. "Someday" is not a trigger. An item's "why deferred" must be its trigger inverted; if the two do not invert cleanly the item is too vague to add. The cap is 45 active items, so a 46th means promoting, merging or dropping one.
- Closing a queue item means deleting its file and its row and appending one line to `docs/work-queue/closed.md`: a pointer to the plan or commit that carries it, or one sentence on why it was dropped. Ids are never reused, so references to a closed item still resolve. An item graduates to `docs/plans/` when the author commits to building it.
- Verification is `scripts/verify`: `fast` (the default) while working, `full` before a commit, `--only loom|arras|docs` for one lane. It ends by printing the branch's latest CI runs; read them.
- Prose in every file is never hard-wrapped (see `CLAUDE.md`).
- Publishing to PyPI or npm is done by the user, never by an agent.
