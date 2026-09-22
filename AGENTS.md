# Agents working in loom-arras

This is one repository holding five tools and the documents that govern them: `loom` (Python, in `loom/`), `arras` (Svelte, in `arras/`), and the three editor clients `loom-lsp/`, `loom-nvim/` and `loom-vscode/`. Each keeps its own build, tests and release; a change that crosses them is one branch and one pull request. Read in this order:

1. **`docs/work-queue/README.md`: start here.** What is not done, and the observable trigger that says when each becomes worth doing. It is not an ordered queue — read the triggers, not the order, and act on an item whose trigger has fired. If none has, there is no work waiting and you should ask rather than invent some.
2. `docs/book/`: the design book. It describes what is implemented, so read it as the specification of what exists rather than a plan. `docs/specs/` is the loom–arras interface and wins over the book where shapes are concerned.
3. `docs/deviations.md`: what has already been changed from the book and why, each row with its decision record in `docs/book/A-decision-records.md`.
4. `docs/plans/`: the plan for work in progress, if there is one. `implementation-plan.md` and 0.2 to 0.4 are history — what was intended at the time, not what to do now. The milestone records they produced are in `docs/work-queue/closed/`.

Rules that are not negotiable:

- Never edit anything under `~/notes/`. Paper sources are copies under `tests/fixtures/`; quilts built from them live under `demos/` and are gitignored.
- Every LaTeX compile in a test runs in an isolated environment (empty HOME, TEXMFHOME, TEXMFLOCAL, TEXMFVAR, TEXMFCONFIG; no TEXINPUTS) with the quilt root as cwd, so a test never passes because of a file elsewhere on the machine.
- When implementation contradicts a `[decided]` statement, append a decision record to `docs/book/A-decision-records.md`, add a row to `docs/deviations.md`, and continue. Do not silently bypass the book.
- A new decision record's id is `DR-<number>-<username>`: the number one above the highest in `docs/book/A-decision-records.md`, and `<username>` the GitHub username of the human you are working for (for example `DR-228-ikmartin`), never your own name. Cite it by that full id everywhere. The format section of that file is the normative statement.
- The book describes what is implemented. It carries no `[deferred]` or `[assumed]` statements and no "Open questions" sections; both markers were retired by DR-107. Work you are not doing now goes in the work queue as an item with a trigger, never into a chapter as a wish. `python docs/work-queue/check.py` fails if either rule is broken, and it runs during the end-of-round walk beside `docs/deviations.md`.
- Adding a queue item means a row in `docs/work-queue/README.md` and a `WQ-NN-<slug>.md` beside it, with an **observable** trigger — a measurement crossing a threshold, a capability existing, a dependency landing. "Someday" is not a trigger. An item's "why deferred" must be its trigger inverted; if the two do not invert cleanly the item is too vague to add. The cap is 45 active items, so a 46th means promoting, merging or dropping one.
- Closing a queue item means deleting its file and its row and appending one line to `docs/work-queue/closed.md`: a pointer to the plan or record that carries it, or one sentence on why it was dropped. Ids are never reused, so references to a closed item still resolve. An item graduates to `docs/plans/` when the author commits to building it.
- Author files are never modified by loom; tests enforce it.
- Prose in every file is never hard-wrapped (see `CLAUDE.md`).
- Publishing to PyPI or npm is done by the user, never by an agent.
