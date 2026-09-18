# WQ-23 · reviewing agent runs in arras

**Repo:** loom, arras

## Trigger

The author resumes the design. This is a decision rather than an observation, as WQ-21's was before it graduated into [plan 0.7](../plans/0.7-three-queue-items.md): the design was paused mid-discussion on 2026-09-16 to work the running UI requests in `docs/long-prompts/running-requests.md`, and nothing needs to be noticed before it restarts.

## Why deferred

Paused, not declined. What is settled is below; what is open is listed so a resumed session does not re-derive either.

## The prototype

Published at <https://claude.ai/artifact/DNKQMbKsdXCLLVgDn4TXvT> (version 2). Its source is [WQ-23-agent-review/](WQ-23-agent-review/): `template.html` plus `demo-data.json`, joined by `python build.py` into `page.html`, which is what gets published; `look.mjs` drives it in Playwright (`node look.mjs <dir>` from `arras/`, writing screenshots to `<dir>/shots/`). The data is two real runs on the demo quilt, kept under `runs/`: `2026-09-16T14-02-referee-dm-0003` (a referee that called the mathematics correct) and `2026-09-17T01-43-review-main` (referee → audit → simplify, which found the theorem's "only if" false, with a brute-force check, a proposal diff and seven annotations). The demo quilt is manufactured and need not be accurate; the second run's findings rely on dm-0003 as it ships.

Five views: reviewing a run (the split view), node and evidence, asking for a review, verifying a citation, notation. Violet dashed outlines mark what is proposed and not built.

## Settled with the author

- **The split view.** The draft on the left, a run on the right with Report and Transcript tabs; the right pane cycles through runs (a pipeline, an earlier run, your comments, all runs) and the draft's highlights follow the selected run. The panes scroll independently and the strip stays fixed; "show in report" scrolls only the right, and selecting a finding in a report scrolls only the left. The author: "nearly exactly what I want".
- **What launches it** is the agent's closing line in the chat, a link to `localhost:8791/review/<run>`. It is also reachable from a run in the threads index and from any finding on a node page.
- **Annotations are colour-coded highlights on the text**, expanded by selecting them and closed by selecting outside. Annotation ids are never shown to the reader.
- **The chat is the primary interface to agents.** The author's tag syntax, `[simplify][audit][referee] dm-0003 [/referee][/audit][/simplify]`, carries a node key instead of pasted LaTeX. An arras "copy for chat" is welcome; a pipeline picker in arras is a good vision but secondary.
- **Within one run, a later turn edits its own annotations in place.** Across runs, overlapping annotations both appear; noticing the overlap is the reviewer's job, not loom's.
- **Severity per finding replaces the referee's `[decision]` block,** after the author's own mode that marks issues and labels them by severity. A verdict, if any, lives in the transcript.
- **Worked examples, examples and counterexamples are promotable to nodes**: an example depends on its node by `\uses`, a counterexample is linked by `see:`.
- **Citations.** A memory-grade citation is usually one whose paper is not on file. The agent names its best guess, describes the work and does its best to check it (an arXiv identifier it can resolve and fetch itself); reviewing the guess is a human job, and adding it to the bibliography is not in loom's scope.
- **Notation belongs to agent prose only**: reports, explanations, transcript messages; never `nodes/` or `drafting/`. The agent declares a `[notation]` block once per run; arras marks each declared symbol by TeX token inside the run's math, lists them in an expandable panel on the run pane, and previews the definition on hover. A second meaning for a symbol within one run is flagged.

## Open

- **Editing an annotation.** Bodies are immutable today and only `--resolve` changes status; in-place edits within a run and the severity field are both record-format changes.
- **Recording what a run was asked**: `loom ai start --target … --pipeline …` and the matching `run.toml` fields were sketched, not agreed.
- **A candidate reference with no bibliography entry.** `loom refs add` files under the identifier the bibliography declares, or a synthetic `work:` id without one, so an accepted guess the author never adds to their bibliography is recorded only in the run.
- **`referee.md`'s re-check convention** writes `referee-KEY.2.notes.md`, which contradicts editing in place within a run.
- **The author's severity mode** is to be pasted into `docs/source/` beside `global-rules.md`; its block names decide the report's completeness check. The copy of the chat prompt in `docs/source/global-rules.md` has six modes (ingest, referee, question, quick, audit, simplify) and no severity mode, so it predates that mode.
- **What quick mode is for in loom** (`docs/source/global-rules-mapping.md`). The author reaches for question, quick, referee, audit and simplify most, the last three together. Loom has a quick mode (`ai/modes/quick.md`, writing `quick-SLUG.notes.md`), but the author's judgement is that quick has no real parallel here because it produces nothing durable, where question does. Whether quick stays a run mode, becomes chat-only, or produces something is undecided.

## Open threads from before the prototype

Three conversations that led into the prototype and were not concluded. Nothing in them is agreed; each ended on a question to the author.

### Agent drafts

The author asked whether an agent should make its own drafts — a document of chosen nodes with comments and suggested rewrites mixed in — and whether that means a new directory, or the drafting directory becoming ephemeral with another directory for real papers.

- **Most of it exists.** `loom bundle KEY` writes a compilable document of a key's closure; `loom comment TARGET --run DIR` anchors a comment to a node, so it follows that node into every document and goes stale with it; a `proposal-KEY.diff` in the run holds a rewrite, and `loom bundle --with FILE` compiles the document as if it were accepted.
- **No new directory.** `drafting/` holds the papers and is where a master is recognised; `ai/runs/` is already the ephemeral tier, and "an agent writes only under `ai/runs/`" is enforced by the orientation, by `loom ai init --permissions`, and by `loom ai check`. `loom ai promote` is the gate for a digest, and a drafted node is pasted by the author (DR-140).
- **What is missing is a reading**: an ordered list of node keys with the agent's own connective prose between them, kept in the run. It should *reference* nodes rather than copy them, so it shows current text when reread; a bundle copies, which is right for a snapshot and wrong for something returned to. Arras would stack the existing fragments. Commentary about one node stays an annotation; only commentary about the selection belongs in the reading.
- **The author's answer:** commentary must be possible on an entire draft. Loom already records it: `loom comment drafts/main.tex MESSAGE` writes an annotation whose target is the master and whose hash is the master's own text, its prose and its `\input` lines but not the nodes it includes, so it goes stale when the draft is restructured or its connecting prose changes, and not when a node inside it is edited. `loom build` publishes it. **Arras shows it nowhere:** the read view attaches comments only to elements carrying a node's key, and a master is not a node. Checked on a scratch copy of the demo quilt on 2026-09-16.
- **The author's requirement (2026-09-17):** an agent can assemble an arbitrary collection of nodes, to propose them as an order or to construct a revision of a section or a subsection. This settles that the selection is chosen, not computed, and makes the reading and the reorder preview below one feature: a proposed document in the run that references existing nodes in a chosen order, includes the agent's draft nodes and proposed rewrites of existing ones, carries its own connecting prose, and can be commented on as a whole.
- **What exists for it (checked on a scratch copy of the demo quilt):** an agent can write such a file in its run as `\input` lines under the quilt's preamble, and `loom compile PATH` runs latexmk on it. `loom assemble` refuses it (`is not a master of this quilt`), so it cannot be flattened for `latexdiff` against the section it would replace; the scanner skips `ai/`, so nothing about it is published and arras cannot show it; and `loom bundle --with` substitutes one node's text, so a revision that reorders, rewrites and adds at once has no single preview.
- **Still open:** the file's form (a `.tex` spine, or a list of keys with prose that loom renders); how its node rewrites and new nodes are carried (the existing proposal diffs and drafts, or inside it); how it is compared with the current section; how it is accepted — whether a whole revision applies as one editor edit or piece by piece; where a draft-level comment appears in the read view; and whether a comment on the proposed document uses the same master-path target.

### Proposals without loom editing files in place

The author asked for agents to propose new nodes to promote, a new order of nodes, and proof edits to accept. Verified on a scratch copy of the demo quilt:

- **A proof edit:** the agent leaves `proposal-KEY.diff`; `loom bundle KEY --with DIFF` previews it while the node is untouched; `git apply` applies it; the key goes `accepted, stale` on its own; `loom accept KEY`. The referee and simplify modes already require the agent to record the `bundle --with` result.
- **A new node:** the agent leaves `draft-*.tex` with no id; `loom ai promote` allocates the id and writes `nodes/`, and reports `unreachable` until the author adds the `\input` line that places it.
- **A reorder:** the same diff-and-apply, but nothing previews it, since `bundle --with` substitutes a node's text and not a master's structure. `loom assemble` before and after, then `latexdiff`, is the manual check. No mode asks for a reorder. The author's requirement under *Agent drafts* above makes this part of a proposed section revision rather than a separate feature.
- `git apply --check` refuses a diff whose surrounding context changed, a weaker form of a hash check. The undo is version control, which DR-105 made opt-in.

### The CLI, the editor clients and arras

The author intends the editor clients to supersede the CLI for people, with further work passed to arras, and the CLI kept as the interface for GUIs and agents. A few setup commands stay terminal-only: `init`, `upgrade`, `doctor`, `import`, `digest fetch`.

- **Where each surface stood:** the CLI's `--json` output covered only read commands, so a client could write only by parsing prose. The language server and both editor clients carried no AI workflow: no runs, comments, proposals or promote. Arras was read-only, with a write API specified in `docs/specs/write-api.md` but not built.
- **The proposed division:** source changes in the editor, reading and discussion in arras, conversation in the agent session, the CLI underneath all three.
- **In-place edits via the editor:** the language server's add-missing-`\uses` action already returns an `lsp.WorkspaceEdit`, so the editor applies the change and loom never touches the file. A proposal becomes a code action applying its diff this way, marked `needsConfirmation` so VS Code previews it; loom-nvim would show the diff itself. Promoting a draft is a `CreateFile` edit, and placing or reordering is an edit to the master.
- **Arras passing input back:** through the write API, as anchored comments rather than free chat. Loom cannot wake an agent and should not, so the agent pulls: it finds an open comment through `loom status` and answers with `loom comment --reply`. `write-api.md` §4 still says a model's reply is the business of a bridge that "invokes the runner", which was declined as WQ-15, so that section needs rewriting.
- **Arras sending you to the editor**, the reverse of the existing open-in-arras action: `vscode://file/PATH:LINE` for VS Code, and a server socket (`nvim --listen` and `--remote`) for Neovim.
- **The proposed build order:**
  1. `--json` on every write command.
  2. Proposals and drafts as code actions, each proposal carrying the hash it was written against so a stale one is not offered.
  3. The write API, with §4 rewritten.
  4. Hand-offs between arras and the editor.
  5. The AI commands in the editor clients.
- **Unanswered:** whether these are queue items or a plan.

## Blast radius

`loom/src/loom/ai/` (modes, annotation records, run metadata), `loom/src/loom/assets/ai/modes/`, arras's thread and node routes and a new review route, `docs/specs/` for the record format and `write-api.md`, `loom/src/loom/cli/` for `--json` on writes, `loom-lsp/`, `loom-nvim/` and `loom-vscode/` for proposals as code actions, Chapters 11, 15 and 16.

## Related

the `loom:` link form of plan 0.7 (dialect §2.13), which a citation finding would use to point into a paper; `docs/source/global-rules.md`.
