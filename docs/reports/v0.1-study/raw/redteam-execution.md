# Red team: can plan 0.32 be executed by parallel agents?

Reviewer's angle: whether `docs/plans/0.32-v0.1.md` can be run as written by Opus-class agents, one workstream per branch and worktree, with one human merging and deciding, without lanes wrecking each other's work or finding halfway that the order was wrong. Read at 71621877 in the `v01-study` worktree. Everything below was read in code or in the study's reports; nothing was run except `grep`, `wc`, `du`, `df` and `uptime`. Plan line numbers refer to `docs/plans/0.32-v0.1.md` as it stands.

Verdict: the plan's goals and gates are sound, but its execution layer is not ready. Its ownership is by file name, not by what each package edits. It names five hot files when at least fifteen are claimed by three or more lanes. One of the five has the wrong owner. Its "First" stage runs two lanes, Foundations and Safe, that edit the same functions. The lanes it calls "alongside Safe" touch Safe's files. And it carries the prototypes' headlines but drops most of the warnings that would cost a builder days. The fix is cheap: about three sessions of contracts and splits before any lane branches, a merge and regeneration rule, a short list of decisions the author makes on day zero, and stages redrawn by real dependencies (section C).

## Objections

### On file ownership

#### RTX-1. The hot-file list is a third of what it needs to be

- **Claim.** Five hot files have one owner each: `render/api.py`, `ai/layout.py` with `assets/ai/`, `pending.py`/`records/edits.py`/`records/store.py`/`history/acts.py`, `render/build.py` and `Column.svelte` (plan :74).
- **Evidence.** Appendix B lists every file that two lanes running at the same time would both change, built from the register's "Proposed work" tables and the code. These files are claimed by three or more lanes and are not named:
  - `render/serve.py`: Speed, Security, Safe, Attach, Library and Install.
  - `arras/src/lib/write.ts` and its 56 importing files: Speed change 6, Foundations X2/X6, Attach A10 and Safe's refusal codes.
  - `arras/src/lib/review/history.svelte.ts`: Safe step 5, Review and Legibility. Its header says every annotation write and every Keep or Discard goes through it (`history.svelte.ts:1-3`).
  - The manifest trio, `render/manifest.py`, `arras/src/lib/manifest/types.ts` and `docs/specs/fixture/manifest.json` (×3 copies): seven lanes.
  - `cli/review.py`: Foundations, Safe, Review, Learner and Formalization.
  - `since.py`: five lanes. `config_edit.py`: four. `scan/quilt.py` with `cli/quilt.py`: five.
  - `paths.py` with `agents.py:48` `LOOM_DIRS` and the generated `.claude/settings.json`: four.
  - `loom/tests/unit/render/test_write_api.py`: every lane that adds an endpoint, and Speed.
  - `doctor.py` with `test_doctor.py:391, 648`: three. `scan/diagnostics.py`: five. `annotation-types.toml` (copied into every quilt): two. The showcase quilt: five.
  - The plan file itself: all thirteen (RTX-24).
- **How bad.** Would waste days. Each unnamed file is a merge conflict found at merge time, by the author.
- **Change.** Replace the hot-file paragraph with Appendix B as a table: file, owner, which other lanes may edit it, and how (a pre-approved region or hook; see RTX-7, RTX-10, RTX-25). Own by function or region where a file is shared. Name the integrator who regenerates generated files (RTX-9).

#### RTX-2. `render/api.py` has the wrong owner, and the registry would break Safe's own gate

- **Claim.** `render/api.py` belongs to Foundations until the operations registry exists; after that, a workstream adds an operation (plan :74). Foundations' done-when includes "an operations registry carrying the viewer's writes" (plan :80). Safe runs in the same stage and does not own `render/api.py` (plan :82).
- **Evidence.**
  - The door must rewrite `_change`, `_reopen`, `_history` and the endpoint list, and add `change-undo`. Its patch changed `render/api.py` by 29 lines, and DOOR-18 lists `render/api.py` among the files Safe must own exclusively (`spike-door.md:223, 225, 230`).
  - `_change` also carries Review's look logic (`render/api.py:430-432`: `track_edits`, `read_look`, `keep_all`). `review-accept` calls `keep_accepted` and `keep_versions`, which are Safe's (`:966-972`). `reviewer-settings` calls `save_author`, which is S8 (`:920-928`).
  - X2's own entry says "`handle` goes" (register :812). Every instrument of the Safe gate drives `loom.render.api.handle` directly: `safety-harness/keep/test_write_safety.py:53`, `harness/safety_lib.py:91, 838`, and eight reproductions under `repro/`.
  - X2's list of operations to port (annotate, edit, delete, keep, discard, accept, restore, record, tick, settings, sessions, library add) is the same set of handlers that Safe, Review, Library and Attach are about to rewrite.
  - Decision b.20 ("the ops registry before v0.1") is still open (register-notes :95).
- **How bad.** Would waste days. Either Safe's critical path waits for a refactor whose v0.1 value is only collision avoidance, or two lanes rewrite the same handlers and the gate's harness breaks under both.
- **Change.** On day zero, split `handle()` into a dispatch dict and move each family into its own module (`render/api_changes.py`, `api_library.py`, `api_sessions.py`, `api_review.py`, `api_sync.py`, `api_settings.py`). Split `test_write_api.py`'s `CASES` (`:235`) the same way. Assign each family to the lane that rewrites it:
  - changes, history, tick and settings: Safe;
  - library: Library;
  - sessions, agents and `here`: Attach;
  - review-accept and reviewer-settings: Review;
  - sync and adopt: Safe until door step 6, then Overleaf and Review.

  Keep `handle(root, endpoint, body)` as the entry point the harness calls. Move X2 proper (one guard, one error type, a generic op) after door step 5, or out of v0.1, and say so in Decisions.

#### RTX-3. Foundations' move out of `cli/` runs at the same time as the lane that edits what it moves

- **Claim.** Foundations and Safe are both "First" (plan :76-82); errors and identity move out of `cli/` (plan :80).
- **Evidence.**
  - 49 files import `loom.cli._common`, nine of them tests, and 22 modules outside `cli/` import from `loom.cli` (counted with `grep`).
  - X1 also moves "annotation and acceptance cores into `records/`" and "`key_hash` into `scan/`" (register :811). Safe's `records/store.py:26` imports `key_hash` from `render/manifest.py`.
  - Safe's anchoring rewrites the annotation writers in `cli/review.py` (`_one_comment`, `:429`) to record `context` (`check-labels.md:312, 327`).
  - The anchoring harness, which the Safe gate names, imports `loom.cli.review._one_comment` and `loom.render.manifest.key_hash` (`spikes/labels.patch`, harness lines 24 and 29).
  - The author's standing rule is no shims unless asked, so after X1 a lane's new `from loom.cli._common import is_agent` breaks without a textual conflict. Only mypy or the tests find it.
- **How bad.** Would waste days: a move against an edit is the worst kind of conflict for git.
- **Change.** Land a minimal X1 (errors, identity, `key_hash`) as the first merge, before any lane branches; that is one session. Leave the annotation and acceptance cores where they are: Safe moves `_one_comment` when it rewrites it, and Review moves `accept` when it rewrites it. Add one line to the plan: "no lane branches before X1-minimal is on main".

#### RTX-4. "Alongside Safe: lanes that do not touch its files" is false, and Safe's owned list is too short

- **Claim.** The heading at plan :86, and Safe owning `writes.py`, `pending.py`, `records/edits.py`, `records/store.py`, `history/acts.py` and `scan/nodes.py` (plan :82).
- **Evidence.** The prototypes say Safe must also own `render/api.py`, `config_edit.py`, `tasks.py`, `records/snapshots.py`, `history/steps.py`, `adopt.py`, `sync.py` and `cli/suggest.py` (`spike-door.md:230`). For anchoring add `cli/review.py`, `records/log.py`, `records/annotations.py`, `links.py`, `since.py`, `review_queue.py` and `mcp/` (`check-labels.md:324-331`). For S4 and S8 add `cli/quilt.py`, `cli/upgrade.py` and `scan/quilt.py:253`. And the door adds a doctor item (`spike-door.md:93`). The "alongside" lanes then collide with Safe like this:
  - **Install.** `doctor.py` (Install owns it; the door adds `writes`). `cli/quilt.py` and `cli/upgrade.py` (init asks the name once; the format stamp). `scan/quilt.py` (`save_author`).
  - **Attach.** `config_edit.py` (`:430-436, 469` for A1, and A15; door step 1 routes `config_edit` through the door). `since.py` (A4 keys it by session; anchoring routes it through the resolver). `paths.py` and `agents.py` (A4's `.loom/live`).
  - **Speed.** `render/versions.py`, whose `gone_annotations` iterates `records.resolved` (`render/versions.py:118-142`), the function anchoring replaces (RTX-6). `render/serve.py:365` (the door's lock order; RTX-5). `scan/quilt.py:214` (the git-name cache) beside S8 in the same file. `pending.py:132-194` (PERF-5). P4's `adopt.py` and `records/store.py` (`Records.apply`).
  - **Legibility.** `history.svelte.ts` and the selector format of the comments it creates (RTX-8, RTX-18).
  - **Learner.** M1's dollar rule is `records/store.py:1096` (`_MATH`), Safe's file. M7 needs `records/`, and its new lint codes need `scan/diagnostics.py` (Review's).
- **How bad.** Would waste days.
- **Change.** Give Safe the full DOOR-18 and KEY-13 file lists. Rename the heading "Alongside Safe: lanes that touch Safe's files only where listed", and list the permitted edit for each such file (for example, "Speed may add the git-name cache function to `scan/quilt.py`; Safe owns `save_author`").

#### RTX-5. The write and publish seam has no owner, and three lanes are about to redesign it independently

- **Claim.** Speed: "writes that answer at once"; "Answering a write first breaks the viewer's assumption that an answer means the page is current" (plan :41, :92). Safe: "Decide again under the lock" (plan :82). Review: undo in two actions (plan :101).
- **Evidence.**
  - The write lock and the rebuild lock are one lock: `publication_lock` is `self.lock` (`render/serve.py:863`), `rebuild()` holds it for the whole build (`:704`), and every POST but `here` takes it (`:365-367`) before `rebuild()` (`:369-370`).
  - So answering first (FAST-6) makes the first write fast, and the next one, typically Undo pressed a second later, waits for the background rebuild: 3-6 s on relloc (PERF-8; FAST-1's in-manifest 3.1 s).
  - The door nests `writes.lock` inside `publication_lock` and holds it through two rescans and the carry. "A CLI Keep beside the viewer stalls the viewer" (`spike-door.md:157`).
  - FAST-6 breaks 16-17 tests in `test_write_api.py` and `test_serve.py` (`spike-speed.md:64`) and needs a viewer contract change in `write.ts` and its callers (`spike-speed.md:115`). 56 viewer files import `write.ts`, with 43 `refresh()` calls.
  - Review builds its undo on whichever contract exists when it starts.
- **How bad.** Would waste days. The Fast gate's "a write answers within 1 s" can pass in the bench, where writes come one at a time, and fail for a person who saves and annotates. Review's undo cards would be built twice.
- **Change.** Add one decision, made before door step 3 lands: separate the records and write lock from the publication lock, and put a `published` sequence number in each answer, which the viewer waits for on `/_api/stream`. Make it one design task owned by Safe, with Speed reviewing it; Speed then implements the viewer half. Review and Legibility build write controls only after it.

#### RTX-6. Speed's first change memoises the function Safe's anchoring replaces

- **Claim.** Speed lands "annotation re-anchoring done once and cached" as it is (plan :92), while Safe builds the new resolver (plan :82).
- **Evidence.**
  - `gone_annotations` calls `records.resolved(result)` (`render/versions.py:142`), and KEY-13 replaces `written_on` and `resolved` with `follow` (`check-labels.md:304-311`).
  - Change 1's memo is keyed on `(old, new, offset)` (`spike-speed.md:46`). The safe resolver adds new inputs: two-sided neighbours, a twin flag and quilt-wide quote counts (`check-labels.md:212`).
  - A memo that omits them would answer stale placements, which is exactly the staleness class `spike-speed.md` FAST-10 warns about.
- **How bad.** Would waste hours to days, since the bug is silent.
- **Change.** Land Speed change 1 before Safe's resolver, and require the resolver lane to fold the memo key into `follow`'s inputs. State this in both rows.

#### RTX-7. `Column.svelte` belongs to Legibility, but Library, Attach and Review must edit it

- **Claim.** "`Column.svelte` and the viewer's shell belong to Legibility"; others "ask the owner before touching another's" (plan :72, :74).
- **Evidence.** `Column.svelte` imports `AddWork` (Library L-E replaces it), `shelf` (L-F), `SessionFooter` (Attach A10 hides it) and `reviewLanding`/`sectionsOf` (Review R-G) at lines 9-25, and holds the agent-document rows (R-Y). V2's fold threshold is at `:43-50` of the same file. The window drop overlay (L-E) and I4's window drop both go in `arras/src/routes/+layout.svelte`. Agents cannot ask each other anything: the only channel is the author.
- **How bad.** Would waste days, in blocked viewer lanes and author traffic.
- **Change.** On day zero, split `Column.svelte` into lane-owned children (`LibraryShelf.svelte`, `ReviewNav.svelte`, `AgentStatus.svelte`, `ColumnFooter.svelte`), with Legibility owning the frame. Do the same for a `DropZone.svelte` slot in `+layout.svelte`, owned by Library, which Install's import calls.

#### RTX-8. "The viewer's `review/`" is not Review's

- **Claim.** Review owns "the viewer's `review/`" (plan :101).
- **Evidence.** `arras/src/lib/review/` holds:
  - `AnnotateBar.svelte`, `annotating.svelte.ts` and `AnnotationPopup.svelte`: Legibility's comment on the selection (WALK-4, WALK-5, SWALK-3, SWALK-5);
  - `history.svelte.ts`: Safe's step 5, which DOOR-18 lists as Safe's (`spike-door.md:225`);
  - `LibraryRow.svelte`: Library's L-E;
  - `ProposalCard.svelte`, `ProposalQueue.svelte` and `proposed.ts`: Formalization's F8;
  - `ChangeCard.svelte`: Overleaf's "Copy new text / Done in Overleaf";
  - `ChangesMenu.svelte`: Legibility's V5 toolbar.
- **How bad.** Would waste hours to days.
- **Change.** Own by component, not by directory. The table in Appendix B gives each component's owner.

#### RTX-9. Generated artefacts have no regeneration owner and no merge rule

- **Claim.** None; the plan gives Foundations "one `scripts/regen`" (plan :80) and nothing about who runs it or when.
- **Evidence.** The generated files lanes will all touch:
  - **The quilts.** About 400 generated files in `loom/tests/quilts/{demo,synthetic,showcase}` (71, 125 and 205 files) and 402 in `demos/`, kept equal by `scripts/checks/fixtures.py`, plus `test_quilts_match_generator.py`.
  - **The spec fixture.** 198 files under `docs/specs/fixture`, copied twice more.
  - **The references.** `loom/docs/mcp-tools.json` and `cli-reference.md`, each pinned by a test.
  - **The viewer bundle.** 303 files.
  - **The permission files.** Each quilt's `.claude/settings.json` (55 allows including one `Bash(loom <cmd>*)` per agent command, and 54 denies including one per protected `.loom` path and per author command) and `.codex/rules/loom.rules` (86 lines).

  Lanes that change those inputs:
  - **New `.loom/` paths:** Attach's `.loom/live`, Library's `.loom/incoming`, Formalization's `.loom/formal`, Safe's `.loom/format`. DOOR-13 hit exactly this: `test_paths` and the demo's `settings.json` failed (`spike-door.md:95, 184`).
  - **Agent and author commands:** Library's `library suggest`, Formalization's `formal record` and `formal attest`, Install's `loom app`, Attach A16's six removals and Legibility's hides.
  - **Copied assets:** agent texts copied into every quilt (Attach, Learner, Formalization's new mode, Foundations' D11), `annotation-types.toml` (Learner's types, Legibility's V9 rename) and `loom.sty` (Learner).
  - **Record formats:** Safe's `context`, `near`, `edge` and kept hash, which change every generated record.

  The fixture is made with whatever `latexmk` is first on PATH (`docs/specs/tools/refresh-fixture.sh:17-20`). The author runs TL 2024, CI's image floats (INST-4), and Install puts loom's own TL 2026 first on PATH (I2). TL 2026 also splits paragraphs at displays: man12 goes from 274 blocks to 343 (`tinytex.md:121`).
- **How bad.** Would waste days. Every merge of two such lanes conflicts in JSON and Markdown that no one should hand-merge, and a fixture regenerated on the wrong TeX fails CI.
- **Change.** Add a merge rule:
  - Generated paths are never resolved by hand. On any conflict there, take main's side, then run `scripts/regen` on the merge commit.
  - Fixtures are regenerated only on the pinned TeX: CI's 2026 image until Install's TeX lands, then loom's own.
  - Lanes commit source changes plus a regen, and the integrator regenerates again after each merge.
  - Decide on day zero whether the CLI reference stays (a.28) and where vendoring happens (a.27). Until the dev proxy (T5) lands, no viewer lane vendors.

#### RTX-10. Two lanes needing manifest fields at once: no protocol, and mismatches fail silently

- **Claim.** None in the plan.
- **Evidence.**
  - Manifest additions are planned by Library (L-F's page text, L-G's `suggested_works`), Formalization (F7's `keys[K].formal` and a `formal` list), Attach (A5's config fields, the presence list), Review (R-C's class, R-E's Changed list, R-Y's AI-document state), Safe (unplaced and detached records, `check-labels.md:315`) and Speed (P7's hash).
  - They all append to one function tail in `render/build.py:566-602`, which Speed is restructuring (2+5).
  - `types.ts` is hand-mirrored and declared open, "so a field loom renames fails silently" (VIEW-22).
  - The repository's own rule is that "a change to the interface changes [the fixture] first" (`docs/contributing.md:53`).
- **How bad.** Would waste days. Unplaced records alone are wanted by Safe, Review (Discard on unplaced, R-D) and Legibility (the notes page).
- **Change.** Add a day-zero contracts commit. It reserves every new manifest field, record field, `.loom/` path, agent and author command, endpoint or op name, refusal code and diagnostic code in `docs/specs/*.md` and `types.ts`, with stub values in the fixture. Add one hook in `build()` (a list of `attach_*` callables) so lanes register their own attach step instead of editing Speed's function.

### On order and dependencies

#### RTX-11. Critical items have no owner, and one gate condition depends on a later lane

- **Claim.** Critical items include "A new quilt in which agents propose changes to the person's documents and cannot write them" and Decision 1's deny default (plan :41, :55). The Safe gate includes "An agent's edit to a person's document is either refused or shown" (plan :27). One-step undo "wait[s] for Safe" (plan :84). Learner says Markdown annotations and suggestions wait for Safe (plan :95).
- **Evidence.**
  - No workstream's goal or owned files include `cli/quilt.py:39-42` (`deny = []`, `track_edits = false`), `scan/quilt.py:66, 108`, `cli/paper.py` (deny at `init --from` and `import`) or `orientation.md:30`. These are register S6 and R-F.
  - The "shown" half needs R-E's Changed row for a change in a denied path, because Codex ignores deny (CUT-7 condition 1). R-E is Review's, after Safe. So the Safe gate cannot pass before Review.
  - One-step undo is DOOR-18 step 5, in Safe, including the viewer's `history.svelte.ts`. Yet Review's done-when also says "undo it in two actions", and the plan says undo waits for Safe as if someone else built it.
  - R-H (suggested edits on any text file) and M7 have no owning lane.
  - X3's hides are assigned to no one; Legibility's "hiding what the tiers table says" edits Attach's `ai/layout.py`, Foundations' `render/api.py` CAPABILITIES and `cli/__init__.py`.
  - The one-time context pass over existing records belongs in `cli/upgrade.py` (KEY-8: "the context is not optional") and is unowned.
- **How bad.** Would waste days. Items without an owner surface at the gates.
- **Change.**
  - Give S6/R-F (deny default, orientation line) to Safe.
  - Move "shown" for Codex to Review's gate and keep "refused" in Safe's.
  - Give `change-undo` and the viewer undo to Safe step 5, and Review's cards to Review.
  - Give R-H and M7 to Learner, after door steps 3 and 4.
  - Give the hides to Legibility, with explicit permission to edit those three files' lists.
  - Give the context migration pass to Safe.

#### RTX-12. Legibility is a final integration test, not a parallel lane

- **Claim.** Legibility runs alongside Safe; it is done when "the two walks, run again" pass (plan :94).
- **Evidence.**
  - The five tasks both walkers failed are spread over other lanes: "can an AI see my comment" and "is an AI connected" are Attach's; "undo a Keep" is Safe's and Review's; "add a paper" is Library's and Install's; "fix a problem" is Review's R-C plus V1 (register-notes g, :262).
  - V1 (no command on screen) "waits on A1, I3, O1, L-D" (register :573). The Overleaf pane's command (`Overleaf.svelte:22`, VIEW-1) cannot go before O1, which comes after Safe.
  - The Legible gate also requires "no screen shows a terminal command" (plan :30).
- **How bad.** Would waste days. An agent cannot reach done until four other lanes finish, and will either report done falsely or sit.
- **Change.** Split Legibility in two:
  - **Panes and toolbar** (V2-V7, the selection comment, the notes page, the showcase content), running in wave A or B.
  - **The final sweep** (V1, V8, V9 renames, then A13's name freeze, then the walks), as the last stage before the gates.

#### RTX-13. "Review waits for Safe" is too coarse in both directions

- **Claim.** Review's rebuild waits for Safe (plan :84, :97-101).
- **Evidence.**
  - R-C (Problems by class) needs nothing from Safe (register :354).
  - R-D and R-E need the door's step 5 refusal codes and `change-undo` (`spike-door.md:228`), plus S8's split look (CUT-7 condition 4) and the deny default (RTX-11).
  - "Take into my document … on a paper split into files" is adoption, which is door step 6, the last step (`spike-door.md:226`), and the file Speed's P4 makes incremental (`adopt.py`).
  - The look's cost on relloc is the first-ranked unverified claim, and R-E rests on it (register-notes d, rank 1).
- **How bad.** Would waste hours to days.
- **Change.**
  - Start R-C in wave A.
  - Start R-D and R-E after door step 5, S8 and S6, with "measure the look on relloc" as R-E's first task.
  - Start R-Y and "Take into my document" after door step 6.

#### RTX-14. Formalization's dependencies are on keys and on Review, not on "Safe"

- **Claim.** Formalization comes after Safe (plan :103).
- **Evidence.**
  - F1-F3 (pruning `.lake` in `scan/source.py:16, 28` and `render/watch.py`; finding projects; the evidence record) need nothing from Safe.
  - F3's records and F6's staleness are keyed by block keys, whose form Safe's key rule changes: rows on labelled statements are retired on upgrade (KEY-9, KEY-10, `check-labels.md:270, 278`).
  - F8's card is planned "with R-D" (register :765).
  - F10 waits on the skills' licence (author queue 7). LEAN-§7D warned that the smallest cut costs 9-11 days, with "library import and speed the likely casualties".
- **How bad.** Would waste hours.
- **Change.** Start F1-F3 in wave A. Start F5-F7 after Safe's key rule (KEY-13 step 3), and F8 after R-D. Add "keys change form under Safe's step 3; file evidence on the new form" to the row's traps.

#### RTX-15. Library's key change and Install's window drop collide with other lanes

- **Claim.** Library owns `refs/`, `cli/library/` and the library viewer (plan :93); Install builds "a window that takes a dropped paper" (plan :41).
- **Evidence.**
  - L-C changes citekeys (`key_for`, `untitled-<sha8>`, an id from the PDF's hash), and every digest label is `SLUG-label` with the citekey as slug (`digest/extract.py:551`, cited at `check-labels.md:281`). So cited statements' keys move while Safe's resolver is being built.
  - L-E's "window-wide drop overlay" (`+layout.svelte`) and I4's "window-level drop and an import endpoint" are the same surface. The register flags the overlap (register :177, :444), and the plan does not resolve it.
  - L-D's streamed upload changes `do_POST`'s body handling (`render/serve.py:340-351`, `MAX_BODY`), in Speed's file and the region RTX-5 covers.
- **How bad.** Would waste hours to days.
- **Change.** Give the window drop to Library and have Install call it. Land L-C before Safe's resolver, or have the resolver's tests include a citekey rename. Put the streamed-upload edit to `do_POST` under RTX-5's design.

### On the prototypes' warnings

#### RTX-16. The door's warnings that the plan dropped

- **Claim.** The Safe row carries the main traps (plan :82).
- **Evidence.** Dropped or softened from `spike-door.md`:
  - **The scan must record each file's raw digest and decoding**, so the precondition is a hash (DOOR-6, DOOR-17). That is a change to `scan/source.py` and `ScanResult`, outside Safe's listed files.
  - **Records change shape.** The kept hash comes from the plan; `near` and `edge`; byte digests on `undo`. Records need ids for idempotent append before anything less forgiving is journalled (DOOR-8). Every generated quilt changes (RTX-9).
  - **Lock order and hold time** (DOOR-9). This is where Speed's change 6 meets Safe (RTX-5).
  - **The CLI has no re-plan** after "changed" (DOOR-10).
  - **Versions are LF-normalised.** They must keep raw bytes (`history/steps.py`), or the CRLF harness shows 29 damaged sequences out of 40 after the door (DOOR-2, DOOR-12).
  - **Every act that moves an edit's words must update its record through the journal.** The prototype's word-share rules are stand-ins (DOOR-14).
  - **The anchor precondition makes the second of two edits on one quote "unplaced"**, a visible change Review's Proposed list must show (DOOR-15).
  - **Smaller gaps** (DOOR-16): temp files in the person's directory, `fsync` not `F_FULLFSYNC`, recovery not at `serve` start (Speed's file), and adopt and sync keeping a second rollback.
  - **Steps 3 and 4 both edit `records/edits.py` and `pending.suggested`**: "one after the other, or one owner" (DOOR-18).
  - **Four existing tests encode old behaviour**, including `test_doctor`'s pinned item set, which is Install's file (DOOR-3).
  - **The interim guards.** "Should not be done separately with an `apply`-line guard" (DOOR-18). The plan has no interim guards at all, while the author keeps writing in quant, whose `hwk1` already needs a restore.
- **How bad.** Would waste days.
- **Change.** Copy DOOR-18's six steps, its exclusive file list and its "must wait" paragraph into the Safe row verbatim. Add "versions keep raw bytes", "scan records raw digest", "records carry ids" and "recovery at serve start" as named steps. Add S1's placement guards (inside the block's body; a by-place key unplaced when its hash does not match uniquely), at a few hours, as Safe's first merge, to protect the author's own quilts during the weeks of work.

#### RTX-17. The speed prototype's warnings that the plan dropped, and a Fast gate the in-scope work cannot meet

- **Claim.** Fast: on relloc, "first sight within 5 s and typeset within 20 s; a write from the viewer answers within 1 s" (plan :32). Decision 8 leaves source-first to measurement (plan :62). The incremental build waits (plan :44, :130).
- **Evidence.**
  - The best first publication the spike measured with the cheap changes is "roughly 5-6.5 s, not 3-4" at the audit's load (FAST-1).
  - Change 5, which takes TeX off the save path, makes the typeset block arrive at a median of 23.7 s against 15.4 s without it (FAST-5). So with in-scope work, either first sight misses 5 s or typesetting misses 20 s.
  - Meeting both needs "a follow-up that publishes only what TeX made" (3-4 sessions) or the incremental tail (4-6), which the plan defers (`spike-speed.md:113-116`, FAST-10).
  - FAST-8: any change under `render/`, `scan/` or `tex/` invalidates every cached fragment, snippet and preview through `code_hash`. "Each landing costs every user one such rebuild, on relloc several minutes of TeX." With about thirty merges touching those packages, the author's quilts take a cold rebuild after most merges, and benchmark runs between merges are contaminated.
  - Change 2 leaves a hole: when `latexmk` makes no PDF, previews stay as source (FAST-3).
  - The git-name cache misses `include.path` (FAST-4).
  - Speed has no size in the plan, though the spike gives one per change (`spike-speed.md:107-117`).
- **How bad.** Would waste days. A Speed agent cannot finish against thresholds its own prototype says are unreachable with the work allowed.
- **Change.** Either move "a follow-up that publishes only what TeX made" into Speed's scope (3-4 sessions), or set the provisional thresholds to the measured ones: first sight 7 s at load 4, typeset 25 s. Add FAST-8 to the merge rules: batch merges touching `render/`, `scan/` and `tex/`, and run the Fast gate only on a build after the last of them. Copy the size table into the row.

#### RTX-18. The anchoring prototype's warnings that the plan dropped

- **Claim.** "Label keys help; searching the whole file … must not be built; the safe design checks every block it finds against recorded context" (plan :82).
- **Evidence.** Dropped from `check-labels.md`:
  - **Context is a change to the record format.** Existing records need a one-time pass; without it kpsv puts 8 records on the wrong block and quant's empty answers detach with nothing edited (KEY-8).
  - **Trust or verify.** Under trust, 15 records land on the wrong block; under verify, none, at 26 fewer right placements. KEY-13 recommends trust for annotations, which contradicts the gate's "no record on the wrong block" (RTX-19).
  - **The acceptance ledger** must use verify, and rows on labelled statements retire on upgrade (KEY-9).
  - **Labels with spaces break the link grammar.** 81 of 139 acgs labels and 70 of 96 mzk labels contain spaces, which break `quilt:` links (`links.py:19, 106`); keys need percent-encoding in links (KEY-11). That touches Legibility's `links.ts`.
  - **The showcase regresses** because of its twin lemmas (KEY-7). Legibility is rewriting the showcase.
  - **Order.** The resolver and context first, the key rule after: "Step 3 alone … loses more records" (KEY-13).
  - **The viewer must list unplaced records** and show a "rewritten since you wrote this" mark (KEY-13 step 5). These are Review's and Legibility's components.
  - **Size and tuning.** Five of the seven papers were the tuning set (KEY-7).
- **How bad.** Would waste days.
- **Change.** Copy KEY-13's order, file list and "waits for" into the Safe row. Add the migration pass, verify mode for edits and ledger rows, percent-encoded keys, and a statement of which mode annotations use. Fix the gate wording to match (RTX-19).

### On tests of done

#### RTX-19. The Safe gate cannot be judged by an agent, and can pass while unsafe writers remain

- **Claim.** The Safe gate (plan :27).
- **Evidence.**
  - The harness's `analyze.py` counted 5 of 200 sequences as damaged after the door; all were refused concurrent Keeps that lost nothing, found by inspection (DOOR-2). An agent applying "no damage" literally cannot pass.
  - CRLF restores still flag (RTX-16).
  - The anchoring harness exists only inside `spikes/labels.patch`, beside the prototype's production code. It imports symbols X1 moves (RTX-3) and reads its seven papers from the main checkout's gitignored `tests/fixtures/` (`.gitignore:1`; the papers are present only at `/Users/isaac/dev/loom-arras/tests/fixtures/`), plus relloc and quant, which are the author's. A lane's worktree has none of them.
  - "No record on the wrong block" contradicts the recommended trust mode (RTX-18).
  - The harness's acts are keep, discard, undo, restore, tick, hand edits and settings. They do not cover adopt, sync, `mv`, import, `init --from` or the agent layer, which DOOR-4 lists as not routed. So the gate passes with those writers unsafe.
- **How bad.** Would waste days.
- **Change.**
  - Before Safe starts: move the anchoring harness into `loom/scripts/harness/` independent of the prototype, and symlink the paper fixtures into each worktree (an author-queue item).
  - Reword the gate: "`analyze.py` updated so that a refused act that changed no file is not damage; zero damage on synthetic, showcase, quant and a CRLF quilt; zero wrong placements under verify for edits and ledger rows, and at most the label-reuse cases under trust for annotations, each shown as rewritten; every writer in DOOR-18 step 6 routed, checked by the grep test".

#### RTX-20. Five done-tests are the author's alone, with no agent proxy

- **Claim.** Install: "the author's clean-Mac run"; Attach: "its check above"; Overleaf: "the author's run on a real project"; Formalization: one lemma attested; Review: the Quiet check "on copies of the author's quilts" (plan :28-33, :90-103).
- **Evidence.**
  - A GitHub macOS runner has Homebrew, git and the Command Line Tools, so the Foundations "macOS job" (plan :80) is not a clean-Mac test (INST-7: the shim dialog is untested).
  - Attach needs a signed-in CLI (author queue 4) and the Code tab (register-notes e).
  - O1 already proposes tests against a local bare repository (register :677).
  - Formalization needs a person's attestation, 10.7 GB and Lean (LTRIAL-1).
  - Quiet needs the author's quilts, which are not in the repository.
- **How bad.** Would waste hours to days. Lanes either stall at done or declare it falsely.
- **Change.** Give each of these an agent-runnable done and an author confirmation, as separate lines:
  - **Install:** run the script with `HOME` and PATH stripped of `/opt/homebrew`, `/usr/local` and `/Library/TeX`, on a paper with xy diagrams and PDF figures.
  - **Attach:** live.md's scripted driver.
  - **Overleaf:** a bare-repo fixture with a co-author's edit.
  - **Formalization:** the trial's `sh-0007` replayed with a scripted attestation.
  - **Review:** `check-changed` on author-provided copies placed in the worktree.

#### RTX-21. Done-tests that pass while the thing is broken for a person

- **Claim.** Library, Legibility, Attach, Speed and Learner done-tests (plan :91-95).
- **Evidence.**
  - **Library.** The walks' drops "were synthetic DOM events, so a real browser's handling of an ignored drop was not seen" (register-notes g, :237), so "dropping a PDF anywhere" can pass in Playwright and fail from Finder or Zotero.
  - **Legibility.** The walks rerun on the showcase, which Legibility itself rewrites (plan :94). That teaches to the test.
  - **Attach.** "Connected only while a server process is alive", but idle conversations keep the server alive (LIVE-9; register-notes d, rank 6).
  - **Speed.** "First sight" can be the block's LaTeX source (FAST-5).
  - **Learner.** "Do not break what the quant log says works well" has no test (QF-W1 to QF-W10).
- **How bad.** Would waste hours, then pilot goodwill.
- **Change.** Add per lane:
  - **Library:** one real drag by the author.
  - **Legibility:** the walks also run on a fresh imported arXiv paper, not only the showcase.
  - **Attach:** the chip reads "idle" after N minutes without a call.
  - **Speed:** report first sight and typeset separately.
  - **Learner:** a QF-W regression test file.

#### RTX-22. Foundations' done-when has items no agent can verify

- **Claim.** Foundations' done-when (plan :80).
- **Evidence.**
  - "Merge only on green" is a GitHub branch-protection setting, the author's.
  - "Under three minutes" is undefined under load: `scripts/verify` runs xdist `-n auto` (`LOOM_XDIST`), and the study's own runs went to load 50.
  - "An operations registry carrying the viewer's writes" does not say which writes.
  - "Errors and identity out of `cli/`": does `cli.report`, imported by eleven non-CLI modules, count?
- **How bad.** Wording, costing hours.
- **Change.** Define each item: three minutes at load at or below 4, with two workers; branch protection as an author-queue item; the registry as RTX-2's split; "no module outside `cli/` imports `loom.cli._common`".

### On size, the human and execution

#### RTX-23. The plan gives no total, and the total does not fit the machine as run in the study

- **Claim.** "Sizes are the study's estimates" (plan :72), but only Safe has one (plan :82).
- **Evidence.**
  - Summing the register's and the prototypes' figures per lane (Appendix D) gives about 105-145 coding-agent sessions. Discounted by the author's experience, 1.5 to 2 times too high, that is 55-95.
  - Landing every 2-3 sessions gives 45-70 merges for the author.
  - **Load.** Each lane's `verify fast` uses every core.
  - **Disk.** The data volume is 96 % full with 21 GiB free (`df`). One worktree measures 0.65-0.8 GB, plus `node_modules` at 283 MB and a venv at 132 MB. A Lean project is 10.7 GB (LTRIAL-1), a relloc copy's build 865 MB (speed.md), and TinyTeX 0.33-0.41 GB (TTX-2, TTX-3). Twelve worktrees plus Lean do not fit.
  - **Quiet.** The Fast gate needs a quiet machine (plan :23), which is impossible while lanes run TeX.
- **How bad.** Would waste days, in stalls, full disks and meaningless timings.
- **Change.** Add a size per lane (Appendix D). Cap concurrency at four agents, with xdist at `-n 2` per lane and the TeX tier at merge only. Budget disk: delete each worktree on merge, and give Lean its own volume or run it last. Book a quiet window for the Fast gate with every lane stopped.

#### RTX-24. Reporting back goes through the most contended file in the repository

- **Claim.** "When building something shows that it is wrong, change it here in the same change" (plan :5); "Each workstream appends here what landed" (plan :134).
- **Evidence.** Thirteen branches editing one section and one set of tables of `docs/plans/0.32-v0.1.md` conflict on every merge. Two lanes reassigning the same file in their own copies of the plan conflict semantically, and nobody sees it.
- **How bad.** Would waste hours.
- **Change.** Give each workstream a report at `docs/plans/0.32/<lane>.md` with a fixed template:
  - what landed (commits);
  - gate checks run, with output;
  - edits outside its owned files;
  - contracts added or changed (fields, records, paths, commands, codes, refusals);
  - whether a regen is needed;
  - decisions it needs;
  - the one thing for the author to try, with steps.

  Only the author or the integrator edits the master plan.

#### RTX-25. "Asks the owner" has no channel and no default

- **Claim.** "Owns the files named, and asks the owner before touching another's" (plan :72).
- **Evidence.** Lanes are separate sessions in separate worktrees. Their only shared channel is the author, so every cross-lane edit becomes the author's message to route. Appendix B shows dozens of such edits that are certain, not occasional.
- **How bad.** Would waste hours of author attention a day.
- **Change.** Add a pre-approved cross-edit list, for example "Library may add a shelf component and one import line to the column frame", and a rule: an edit outside one's own files is allowed if it adds a new function, file or registry entry and changes no existing line; anything else goes in the lane's report as a request.

#### RTX-26. The author's queue misses inputs that block lanes

- **Claim.** The author's queue (plan :111-120).
- **Evidence.** Missing items:
  - the paper fixtures and copies of relloc and quant for worktrees (RTX-19; Speed's relloc runs; the Quiet gate);
  - branch protection for merge-on-green;
  - the change-6 write contract (RTX-5);
  - vendoring and the CLI reference (a.27, a.28, b.26);
  - trust or verify for annotations (RTX-18);
  - the definition of "changed" and whether staleness widens beyond formal checks (b.2, b.35; R-E and F6 both rest on them);
  - what opens where (b.17; V7 waits on "the author's rule", register :579);
  - the Ghostscript and figures trial. Decision 7 says "settle it first with a short trial" (plan :61), but no workstream row owns the trial and Install's traps do not mention pictures (TTX-5).
- **How bad.** Would waste days, in lanes stalled at the decision point.
- **Change.** Add these to the queue in unblocking order, marking which must be answered on day zero (contract, vendoring, CLI reference, trust or verify, worktree data) and which by the start of wave C ("changed", staleness).

#### RTX-27. Install's traps omit what tinytex.md found, and two of its fixes sit in Speed's files

- **Claim.** Install's traps (plan :90).
- **Evidence.**
  - **Pictures.** Without Ghostscript, xy diagrams lose their arrows; without dvips's headers they fail silently (TTX-5).
  - **Stale refusals.** A cached refusal is not retried after an install unless a TeX-state stamp enters `snippet_key` (`render/snippets.py:128`) and a missing picture raises a diagnostic (`render/fragments.py:247`) (TTX-4). Both files are Speed's.
  - **Pinning.** A dated TinyTeX does not pin; loom's own archive does (TTX-8).
  - **TEXMFHOME.** It must be passed to latexmk too, not only to make4ht (TTX-10, `runner.py:260`).
  - **biber.** Its first-run unpack trips doctor's 10 s probe (TTX-2).
  - **Repository floor.** `tlmgr update --self` is needed before any install (TTX-1).
- **How bad.** Would waste days. The Installable gate requires "diagrams and figures included" (plan :28).
- **Change.** Add these to Install's traps. Make the Ghostscript and figures trial Install's first task. Give Install a pre-approved edit to `snippet_key` and `fragments.py:247`, coordinated with Speed's key change (one key-format change, not two; see FAST-8).

#### RTX-28. Three stages, not the real graph

- **Claim.** Three stages: First (Foundations, Security, Safe); alongside (Install, Attach, Speed, Library, Legibility, Learner); after Safe (Review, Overleaf, Formalization), then gates (plan :76-107). The plan does not say whether "alongside" lanes wait for Foundations.
- **Evidence.** RTX-2 to RTX-15. The corrected order is in section C.
- **How bad.** Would waste days.
- **Change.** Replace the three stage headings with section C's waves and its "waits for" column.

## A. What each workstream will really change

"Plan" is the plan's owned list; "also" lists files the register's Proposed work tables, the prototypes and the code show the lane must edit. Files owned by another lane are marked with that owner.

| workstream | plan | also |
|---|---|---|
| Foundations | `scripts/`, `.github/`, `arras/vite.config.ts`, `render/api.py`, `cli/_common.py`, `docs/` layout | 49 importers of `cli._common` (22 non-CLI modules: `render/api.py`, `render/serve.py` [Speed], `review_queue.py` [Review], `since.py`, `sync.py` [Overleaf], `records/marks.py`, `history/steps.py` [Safe], `refs/*` [Library], `ai/*`, `mcp/*` [Attach], `links.py`, `locks.py`, `pages.py`, `doctor.py` [Install], `incorporation_review.py`); `cli/review.py` and `records/` (X1 cores); `render/manifest.py`, `records/store.py:26` [Safe] (`key_hash`); `scripts/verify`; `test_write_api.py`; `docs/specs/write-api.md`; `test_output.py`; `arras/src/lib/write.ts` and 58 probe sites if X6 |
| Security | lines in `raw/security.md` | `mcp/server.py` [Attach]; `render/serve.py` [Speed] (Host, CSP, 0600); `tex/runner.py`, `tex/tex4ht.py` [Install]; `raw_html.py` |
| Safe | `writes.py`, `pending.py`, `records/edits.py`, `records/store.py`, `history/acts.py`, `scan/nodes.py` | `render/api.py` [Foundations] (`_change`, `_reopen`, `_history`, `_file_tick`, `_settings`, `change-undo`); `config_edit.py`; `tasks.py`; `records/{snapshots,log,annotations}.py`; new `records/locate.py`; `history/steps.py`; `adopt.py`; `sync.py`; `cli/suggest.py`; `cli/review.py`; `scan/source.py`; `links.py`; `since.py`; `review_queue.py` [Review]; `mcp/` writers [Attach]; `doctor.py` [Install]; `render/serve.py` [Speed]; `cli/quilt.py`, `cli/upgrade.py`, `scan/quilt.py`; `paths.py`/`agents.py`; `arras/src/lib/review/history.svelte.ts` [Review]; generated quilts |
| Install | `scripts/install.sh`, release workflow, `src/app/`, `tex/private.py`, `cli/serve_cmd.py`, `doctor.py` | `tex/missing.py`; `tex/runner.py`; `render/snippets.py:128`, `render/fragments.py:247`, `render/assets.py` [Speed]; `cli/paper.py`; `cli/quilt.py`; `scan/quilt.py`; `render/api.py` (I4); `arras/src/routes/+layout.svelte`, `OutOfStep.svelte` [Legibility]; `.github/workflows/loom.yml:78` [Foundations]; READMEs; `pyproject.toml` |
| Attach | `mcp/server.py`, `presence.py`, `ai/`, `assets/ai/`, agent components | `render/serve.py`, `render/watch.py` [Speed]; `since.py`; `paths.py`, `gitignore.py`, `agents.py`; `config_edit.py` [Safe]; `render/api.py` (A1, A10); `render/build.py:344-363` [Speed]; `arras/src/lib/write.ts`; `Column.svelte` [Legibility]; `routes/threads`, `routes/review/record/sessions` [Review]; `cli/{ai,here_cmd,paper,quilt,changes_cmd}.py`; generated settings and `mcp-tools.json` |
| Speed | `render/build.py`, `render/versions.py`, `render/keys.py`, `render/serve.py`, `scripts/bench` | `section_drafts.py`; `render/{changes,fragments,snippets,compiles,incoming,review_compare,fromhtml}.py`; `scan/quilt.py`; `pending.py:132-194` [Safe]; `adopt.py`, `records/store.py` [Safe] (P4); `arras/src/lib/write.ts` and callers; `manifest/client.svelte.ts`; `render/manifest.py`; 16-17 tests in `test_write_api.py`, `test_serve.py` |
| Library | `refs/`, `cli/library/`, library viewer | `render/api.py` (L-D, L-G); `render/serve.py` (streamed upload) [Speed]; `render/build.py` [Speed], `render/manifest.py`; `ai/layout.py` [Attach]; `since.py`; `cli/quilt.py`; `config_edit.py`; `paths.py`/`agents.py`; `+layout.svelte`, `Column.svelte` [Legibility]; `lib/review/LibraryRow.svelte`, `review/sections.ts` [Review]; generated settings, `mcp-tools.json`, CLI reference |
| Legibility | viewer shell, workspace, toolbar, strings; showcase | `lib/review/{AnnotateBar,AnnotationPopup,ChangesMenu}.svelte`, `annotating.svelte.ts`, `history.svelte.ts` [Review/Safe]; `lib/fragments/FragmentNotes.svelte`; the nine VIEW-1 components including `Agents.svelte` [Attach], `Overleaf.svelte` [Overleaf], `AddWork.svelte` [Library], `Diagnostics.svelte` and the problems route [Review]; for hides, `ai/layout.py` [Attach], `cli/__init__.py`, `render/api.py` [Foundations], `render/build.py` [Speed]; `annotation-types.toml`; CLI help strings; `tests/quilts/sources/showcase` and its 205 generated files |
| Learner | `files.py`, `scan/lint.py`, Markdown renderer, `loom.sty`, wording | `records/store.py:1096` [Safe] (dollar rule); `since.py`; `FileItem.svelte`, `theme.css` [Legibility]; `annotation-types.toml`; `scan/diagnostics.py` [Review]; for M7 and R-H, `records/edits.py`, `cli/suggest.py`, `cli/review.py` [Safe] |
| Review | `review/`, `looks.py`, `review_queue.py`, `scan/diagnostics.py` | `render/api.py:430-432, 914-977`; `cli/review.py:47`; `scan/quilt.py:66, 108`, `config_edit.py:37, 348` [Safe]; `Agents.svelte:67` [Attach]; `pending.in_place` [Safe]; `review_origins.py`; `render/compiles.py`, `render/build.py:564, 612` [Speed]; `Column.svelte`, `FileTree.svelte` [Legibility]; `adopt.py` [Safe]; `render/manifest.py`; `EXPECTED-LINT.txt` in generated quilts |
| Overleaf | `sync.py`, `cli/sync.py`, sync components | `render/api.py`; `ChangeCard.svelte`, `proposed.ts` [Review]; `records/edits.py:460-477` [Safe]; `Overleaf.svelte` [Legibility]; `cli/__init__.py`; Install's new-from-link |
| Formalization | `records/formal.py`, `cli/formal.py`, `formal/`, `assets/lean-skills/`, a panel | `scan/source.py:16, 28`; `render/watch.py`; `doctor.py` [Install]; `paths.py:46-50`; `ai/layout.py:18, 21-38, 274-374`, `mcp/tools.py`, `mcp/prompts.py` [Attach]; `render/api.py`; `records/store.py:286-418` [Safe]; `cli/review.py`; `since.py:169`; `render/manifest.py`; `badges.ts`, `lib/review/{proposed.ts,ProposalCard,ProposalQueue}` [Review]; `cli/ai.py:220-236`; `NOTICE`; docs and specs |

## B. Files two concurrent lanes would both change

| file | lanes | proposed owner and rule |
|---|---|---|
| `render/api.py` | Foundations, Safe, Review, Library, Attach, Install, Overleaf, Formalization, Legibility | split per family on day zero (RTX-2) |
| `render/serve.py` | Speed, Security, Safe, Attach, Library, Install | Speed; Security first; the POST and lock region designed once (RTX-5) |
| `arras/src/lib/write.ts` and 56 importers | Speed, Foundations, Attach, Safe, Review | Speed after RTX-5's decision; others add only refusal-code handling |
| `lib/review/history.svelte.ts` | Safe, Review, Legibility | Safe through step 5, then Review |
| other `lib/review/*` | Review, Legibility, Library, Formalization, Overleaf | by component (RTX-8) |
| `Column.svelte`, `+layout.svelte` | Legibility, Library, Attach, Review, Install | split into owned children (RTX-7) |
| `render/build.py` | Speed, Library, Review, Attach, Formalization, Legibility | Speed; others register `attach_*` hooks (RTX-10) |
| `render/manifest.py`, `types.ts`, spec fixture ×3 | Library, Formalization, Attach, Review, Safe, Speed, Foundations | contracts commit; integrator regenerates (RTX-9, RTX-10) |
| `cli/review.py` | Foundations, Safe, Review, Learner, Formalization | Safe for the writers, Review for accept and status; X1 does not move cores |
| `records/edits.py` | Safe (door and anchoring), Learner, Overleaf | Safe, serialized: door step 3, then KEY-13, then R-H |
| `records/store.py` | Safe, Speed, Learner, Formalization, Foundations | Safe; others by request |
| `since.py` | Attach, Library, Learner, Formalization, Safe | Attach; others add event kinds through one function |
| `config_edit.py` | Safe, Attach, Review, Library | Safe |
| `scan/quilt.py`, `cli/quilt.py`, `cli/upgrade.py` | Safe, Speed, Review, Install, Library | Safe |
| `paths.py`, `agents.py`, generated `settings.json` and `loom.rules` | Attach, Library, Formalization, Safe | paths reserved on day zero |
| `ai/layout.py` (`AGENT_COMMANDS`, `MODES`), `mcp-tools.json`, `cli-reference.md` | Attach, Library, Formalization, Legibility, Install | Attach; commands reserved on day zero |
| `assets/ai/*`, `annotation-types.toml`, `loom.sty` | Attach, Learner, Formalization, Safe, Foundations, Legibility | Attach for texts; Learner for types and `loom.sty` |
| `doctor.py`, `test_doctor.py` | Install, Safe, Formalization | Install; items added through a list |
| `render/snippets.py`, `render/fragments.py` | Speed, Install | Speed; one key-format change |
| `tex/runner.py`, `tex/tex4ht.py` | Security, Install | Security first |
| `scan/source.py`, `render/watch.py` | Safe, Formalization, Attach, Speed | Safe for `source.py`, Speed for `watch.py` |
| `scan/diagnostics.py`, `EXPECTED-LINT.txt` | Review, Learner, Install, Safe, Formalization | Review; codes reserved on day zero |
| `adopt.py` | Safe, Speed, Review | Safe through step 6, then Review |
| `test_write_api.py` | every endpoint lane, Speed, Foundations | split per family (RTX-2) |
| the showcase (source, 205 generated files, demos) | Legibility, Safe, Attach, Learner, Library | Legibility for content; integrator regenerates |
| `.github/workflows/` | Foundations, Install | Foundations; Install owns `release.yml` |
| `docs/plans/0.32-v0.1.md` | all | author or integrator only (RTX-24) |

## C. The corrected order

**Day zero, the author:** RTX-26's day-zero decisions; the paper fixtures and copies of relloc and quant made reachable from worktrees; branch protection.

**Stage 0, serial, about 3 sessions; no lane branches before it ends.** Security runs beside it.

- X1-minimal (errors, identity, `key_hash`).
- `handle()` and `test_write_api.py` split per family.
- `Column.svelte` and `+layout.svelte` split.
- The `build()` attach-hook list.
- The contracts commit (fields, records, paths, commands, codes, refusals).
- `scripts/regen` and the merge rule.
- The dev proxy (T5).
- The worker budget.
- S5' into the unit tier.
- The anchoring harness extracted.
- S1's placement guards.

**Wave A, at most four agents.**

- **Safe door, steps 1, 2 and 3.**
- **RTX-5's lock and write-contract design.** Owned by Safe, reviewed by Speed, done before step 3 merges.
- **Speed changes 1, 3 and 4.** Change 1 before Safe's resolver; 4 together with Install's TeX stamp.
- **Install.** The Ghostscript trial first, then I1, I2, I2b, and I3 without Overleaf.
- **Attach backend.** A1's endpoint, A4, A15 and A16.
- **Library backend.** L-A, L-B, L-C and L-D.
- **Smaller pieces fitted between them:** Review R-C, Learner M1, M2, M4 and M5, and Formalization F1-F3.

**Wave B.**

- **Safe:** door step 5 (`change-undo` and the viewer undo), then KEY-13 (resolver and context, then the key rule, then ledger, links and since), then door step 6, S6 and S8.
- **Speed:** change 6 and the viewer contract, then 2+5 if in scope.
- **Viewer lanes:** Attach A5, A6 and A7; Library L-E, L-F and L-G; Legibility's panes and toolbar and the selection comment, after the selector format with context is fixed.

**Wave C.**

- **Review** R-D and R-E, after door step 5, S6 and S8, opening with the look measured on relloc. R-Y and "Take into my document" after step 6.
- **Overleaf**, after door step 6 and KEY-13.
- **Learner** R-H and M7, after door steps 3 and 4.
- **Formalization** F5-F7 after the key rule, and F8 after R-D.

**Wave D.**

- Legibility's sweep (V1, V8, V9), then A13's name freeze.
- The showcase content.
- On a quiet machine: the walks, the journeys, the safety and anchoring harnesses, and the bench.
- The author's gates.

**Critical path.** Stage 0 (3), then door steps 1-3 (3.5), then step 5 (1), then Review R-D and R-E (6-8), then Legibility's sweep (3-4), then the gates (3-5): about 20-25 sessions serial, at the study's own sizes. Overleaf, which waits on step 6 and KEY-13 (about 5.5 more after step 3, then O1's 5-6), runs a parallel tail of similar length. At realistic merge latency that is at least three to four weeks of calendar, however many agents run.

## D. Size

Sessions per lane from the register and the prototypes; the author's discount is not applied.

| lane | sessions |
|---|---|
| Foundations | 6-8.5 |
| Security | 1-1.5 |
| Safe (door 6-7, anchoring 4-5, S4, S6, S8, S1b) | 12-14.5 |
| Install | 10-13.5 |
| Attach | 10.5-14.5 |
| Speed (changes 1, 3, 4, 2+5, 6, P5, P8) | 10-14 |
| Library | 12-17.5 |
| Legibility | 11.5-15.5 |
| Learner (with R-H and M7) | 5-8 |
| Review | 10.5-14.5 |
| Overleaf | 5.5-6.5 |
| Formalization (smallest cut) | 9-12 |
| Gates | 3-5 |
| **Total** | **about 105-145; 55-95 after the author's discount** |

**How many lanes can run at once.** Four agents, given the collisions in Appendix B, a machine that reached load 50 in the study, and 21 GiB of free disk. One viewer lane at a time until stage 0's splits and the dev proxy land; two after.

**Where the author's attention is the limit.** 45-70 merge reviews, each followed by a regen. About fifteen decisions that open mid-flight (RTX-26). Thirteen handovers. Five gates only the author can run.

**The three places this plan is most likely to stall.**

1. **Safe into Review into Legibility's walks.** One lane, serialized on `records/edits.py`, carries the critical path, and its own gate instruments break under Foundations' moves (RTX-2, RTX-3, RTX-19).
2. **The write and publish seam.** Speed's early answer, Safe's lock order, X2 and Review's undo meet in `render/serve.py:365-371`, `rebuild()` and `write.ts`, with no owner and no decision (RTX-5).
3. **The merge queue at the author.** Generated quilts, `settings.json`, `mcp-tools.json`, the CLI reference, a fixture that needs TeX, and the plan file itself, merged by one person with ~15 open decisions and author-only gates (RTX-9, RTX-24, RTX-26).

## E. Done-tests at a glance

| lane | can an agent tell alone? | can it pass while broken? |
|---|---|---|
| Foundations | partly: three items are undefined or the author's (RTX-22) | yes: the dev proxy works while the release wheel ships a stale viewer if the release workflow does not build arras |
| Security | yes | yes: `openin_any=p` breaks `\input{../macros}`; security.md says `r` |
| Safe | no: `analyze.py`, gitignored papers, moved symbols (RTX-19) | yes: adopt, sync, `mv` and import are not exercised |
| Install | no: the author's clean Mac | yes: without xy and PDF figures in the test paper (TTX-5) |
| Attach | no: signed-in CLI, Code tab | yes: the chip is "connected" for idle conversations |
| Speed | no: relloc and a quiet machine; thresholds unreachable (RTX-17) | yes: first sight as source |
| Library | mostly | yes: synthetic drop events |
| Legibility | no: depends on four lanes (RTX-12) | yes: walks on the showcase it rewrites |
| Learner | mostly; "agent rules use them" needs an agent run | yes: no QF-W regression test |
| Review | no: the author's quilts | yes: Codex edits in denied paths |
| Overleaf | no: a premium project | partly: a bare-repo test exists in O1 |
| Formalization | no: a person's attestation and 10.7 GB | yes: decisions simulated, as in the trial |
