# Section drafts and responsive AI adoption

Implementation plan, prepared on 2026-10-02 against `444c4b0`, revised after the author's review for redundancy and opaque behavior. No implementation has begun. This extends [0.17](0.17-ai-drafting-and-compare.md) and its [adoption delivery](0.17.2-luisa.md); current implemented contracts take precedence over superseded descriptions in those plans.

Two deliverables: responsive source-selection clicks in Incoming, and section drafts that can be incorporated into their original paper. The selection fix is independent and comes first. Implementation, commits, merges and publication are outside the current planning request.

## Settled scope

- Isolate a section or subsection with its descendants. Several non-overlapping section drafts of one paper may coexist; overlapping alternatives, arbitrary passages and disjoint selections within one draft are excluded.
- Create drafts through the agent/CLI. Inspect and incorporate them in Arras; no Arras creation button is added.
- Offer preamble changes separately from section prose and ordering.
- Fix the observed delay on **Use proposed version / Keep current version**, rather than assume preview or compilation is the bottleneck.
- Follow the UI principles in the previous plans. The revised behavior below clarifies accumulated proposals, source choices, affected mathematics, and completion of a draft.

Technical mechanisms and the proposed timing budget are implementation recommendations. The first measurement and regression fixtures validate them; this plan reports no measured improvement.

## Context

`reshape/copy.py` copies a whole document and records its bases. `adopt.py` already compares those bases with the current paper and AI proposal, projects selected changes back into source, and advances reconciled baselines. Incorporation stamps the paper and supports rollback; it does not require a clean Git tree or create a Git commit. Mathematical acceptance remains a separate, explicit choice, including the existing option to record it during incorporation.

The missing section contract is scope: absent material outside an extracted section must not become a deletion proposal. `scan/sections.py` already supplies expanded boundaries and per-file ownership, but these require an explicit projection contract across inclusions. Stable section identity locates the destination; a saved snapshot supplies its merge baseline.

The slow selection path is concrete: `AdoptionContribution.svelte::choose` calls `adopt-decision`, which is absent from `render/api.py::NO_REBUILD`. The server rebuilds before responding, then the client refreshes. Comparison helpers also reconstruct the same snapshots more than once. These are code findings, not timing measurements.

## User workflow

1. Ask for a draft of section 2. The agent resolves its heading to a stable ID and creates the section copy. Proposed syntax: `loom draft drafting/main.tex --section dm-0100 --ai section-2.tex`. Existing whole-document copying remains available.
2. Work in that draft while continuing to edit the paper. Incoming identifies the draft and source section and shows all its outstanding proposals, including proposals from earlier conversations.
3. Inspect a proposed edit and choose **Use proposed version** or **Leave out for now**. Select section prose/order and preamble changes independently when present.
4. Preview the resulting source changes. A separate affected-mathematics list explains unchanged results requiring review. Incorporate the selected source, optionally accepting mathematics explicitly inspected; the rest remains pending.
5. Continue working in the draft, update it from the paper, or explicitly close it. Closing retains its contents and annotations and frees its section for another draft. Reopening checks for overlap and compares against the current paper.

## Behavior specification

### 1. What Incoming means

**Incoming is the draft's outstanding contribution, not the latest chat turn.** Show the draft name and source section once in the contribution selector. Beside the proposals list, explain “Outstanding changes in this draft, including earlier edits.” Do not attribute an individual change to a conversation unless recorded provenance supports it. A latest-turn filter or per-message change history is outside this delivery.

The initial **Proposed edits** list contains source changes only. An unchanged dependent result is not another proposal. Source-only edits remain inspectable and say that their mathematical text is unchanged. Contributions from different drafts remain separately identified.

The preview presents **Source changes to apply** and **Mathematics affected**, with distinct purposes. The latter includes edited mathematical blocks and unchanged blocks whose review context changes. Each item states why it appears: “Statement edited,” “Proof unchanged; its statement changed,” or “Text unchanged; depends on Lemma 3.2, which changed,” with the relevant link. Use a document-context reason when that is the actual cause; do not invent a dependency chain or imply that the AI edited an unchanged result. The publisher supplies these reasons.

Shared-source effects differ from mathematical dependencies. At the relevant source choice, say “This shared definition also changes in talk.tex” for documents whose assembled content changes through the same node file. In the review list, say “Lemma 4.1 needs review because it uses this definition.” Keep the exact physical files in the patch details. A section scope limits proposals, not the consequences of updating a shared definition.

**Leave out for now** replaces **Keep current version** in the adoption source-choice UI. It records a deliberate exclusion from this incorporation; the proposal remains outstanding and can return later. An unselected proposal has no recorded decision. Neither action permanently rejects or accepts mathematics. No permanent-rejection feature is added here.

Offer **Section prose & ordering** and **Preamble changes** only when changed. Preamble selection states its paper-wide effect. When a selected edit needs an unselected macro or supporting-node proposal, identify the required choice and stop before applying; never add it silently. Preserve existing explicit mathematical acceptance in the final preview without making source selection imply acceptance.

### 2. Scope, identity and creation

Record a versioned scope containing the source document, stable root section ID, structural level, included canonical keys and snapshot reference. Read existing records without scope as whole-document copies. Follow recorded document moves; do not treat filenames, displayed section numbers or byte offsets as persistent section identity.

Resolve “section 2” or its title against the named paper before creation. If it has no stable ID, return its exact file and heading location and explain that creation needs a label. The existing `loom id FILE` prints a patch for untagged sections and mathematical blocks; the author inspects that patch and applies the relevant section label, then reruns the draft command with that ID. Do not imply this command applies its patch or silently label unrelated nodes. The agent-enabled copy operation never writes author source. Duplicate headings or IDs require disambiguation.

Extract the complete subtree from its heading to the next heading of equal or higher level, including subsections and intervening prose. Retain the mapping back to physical source and inclusion boundaries. Extraction and application must agree for inline, included and nested content; refuse an ambiguous occurrence with its location rather than guess a destination.

Reject overlapping active scopes at creation, refresh and incorporation. A whole-document draft overlaps every section, and a parent overlaps descendants. Name the blocking draft and provide its Close action or CLI instruction. Two structurally disjoint sections may contain the same shared node; this is a shared-source effect handled by §1, not structural overlap.

A moved section retains its destination through its ID within the original paper. A deleted/duplicated ID, movement into another paper, or newly overlapping scopes requires resolution. Preserve the root heading's identity and level in the proposal; its title and descendants may change. Splitting or reorganizing descendants is allowed. Scope expansion and root removal are outside this delivery.

Give new section copies persistent, quilt-unique discriminators, using the existing WQ-52 proposed family such as `dm-0001-ai-01`. Apply the discriminator to all copied labels and aliases; preserve existing unnumbered `-ai` copies. Never reuse a historical discriminator. Centralize canonicalization across references, proof/qualified keys, allocation, hashes, diagnostics and Compare. This is internal identity machinery, not a name the user must manage. References outside the copied subtree remain canonical.

### 3. Reading and compiling a section draft

The normal Arras view shows the section with its inherited preamble and links to external context. Other sections and supporting definitions are not editable proposal contents. Resolve context against the last explicitly synchronized source snapshot: creation establishes it, and **Update draft from paper** advances it. Record all relevant local styles, bibliography, macros and support inputs so this is reproducible.

If the paper's context has moved on, show “Paper context changed since this draft was updated,” with Update draft from paper. This describes the draft's reading context; the adoption preview always shows the proposed result against the current paper. Do not silently mix creation-time macro context with current dependency text.

For PDF compilation, generate a disposable whole-paper wrapper with the proposed section substituted into that synchronized source snapshot. The PDF action is labelled **Preview in paper** and opens at the section when a reliable anchor exists. Say “Draft section in paper context from [recorded date/version]”; do not invent a page destination. Other material in that PDF is context, not proposed changes. Wrapper files live under `build/`, do not become live documents, and never enter the adoption patch. TeX compilation follows the repository's isolation rules.

Ordinary Compare pairs the section draft with the corresponding source section. Material outside it is outside scope, not deleted. The complete source paper remains available through existing workspace navigation.

### 4. Incorporation, refresh and preview validity

Extend the existing planner with scoped extraction and projection rather than a second merge engine. Three-way comparison uses the saved section, its current counterpart and the proposal. Detect removals only within the scope; preserve unrelated author bytes and the current file/include representation. Preview all selected changes, including unrenderable changes through source details.

Keep independent statement/proof choices, a section skeleton baseline for prose/order, and a separate preamble baseline. Preserve non-conflicting author changes, stop on conflicts and advance only reconciled baselines. Shared nodes retain canonical identity. When one draft updates a node also present in another draft, the latter compares the new canonical text against its own baseline; its outstanding proposals are not silently replaced.

Pin the exact source, proposal, scope, context, reviewer, allocation inputs, choices and resulting patch, then revalidate before writing. Retain the existing landmark, rollback, review-origin and optional-acceptance contract. Source incorporation that succeeds while acceptance fails reports both outcomes and leaves mathematics pending; it must not invite a duplicate application.

Invalidation explains the event: “The paper changed since this preview; preview again,” “The AI draft changed,” or “Your selected changes changed.” Recompute and retain choices whose compared inputs and meaning still match; identify choices that require another look. A conservative unrelated-source invalidation may require a new preview, but must not claim the section itself changed or discard still-valid decisions. Never apply an obsolete patch to avoid an extra preview.

**Update draft from paper** writes only the AI draft and its records, merges author changes within scope, updates recorded context and preserves outstanding proposals. Distinguish source-section changes from changed context. Unrelated section prose does not make the section proposal stale. Repeating incorporation or refresh is a no-op when nothing remains to reconcile.

### 5. Finishing with a draft

Add a minimal explicit **Close draft** action in the existing contribution controls, with corresponding proposed CLI operations `loom ai close DOC` and `loom ai reopen DOC`. Final command naming is settled with the CLI schema. Close/reopen are author actions; this does not add an Arras creation flow.

Closing changes draft lifecycle metadata only: it does not incorporate, accept, delete or permanently reject anything. If proposals remain, state “Close this draft with N unapplied changes? Its text and annotations will be kept.” A fully incorporated draft remains active until explicitly closed; do not infer that the user has finished editing it.

Closed drafts leave active Incoming and stop reserving a scope. Preserve a snapshot of their contents, annotations and lineage, accessible through a compact closed-drafts disclosure in the existing document listing. Closed contents are historical/read-only and define no live IDs. Preserve old links by resolving them to that closed view; define annotation targeting and snapshot identity in the schema before implementation. Reuse existing historical rendering and superseded-document facilities where suitable, but do not assume `loom live` alone supplies this contract.

Reopening restores the retained draft as active, checks scope overlap and identity availability, and reevaluates it against today's paper without accepting or overwriting author changes. Name any blocking draft and retain the closed copy on failure. Manual filesystem deletion is not the advertised way to free a scope.

### 6. Responsive source selection

Measure click-to-confirmed-choice, endpoint work and browser refresh/typesetting on a representative scratch quilt. Record the fixture and machine, one cold run and at least 30 warm selections. Count scans, comparisons, builds, fragment renders and TeX invocations. Never benchmark by modifying `~/notes/`.

Give `adopt-decision` a metadata-only publication path before exempting it from rebuilds. Validate and atomically persist the choice, update the corresponding published metadata, and return the authoritative selection revision. Serialize this with source publication so a concurrent rebuild cannot restore older choices. Reject stale same-reviewer tab writes through a revision check or equivalent mechanism.

The client shows a local pending state, then confirms the returned choice without remounting unchanged comparison fragments or retypesetting mathematics. A failure retains the prior confirmed choice with an inline error. Keep the active item, keyboard focus and scroll position. Subsequent manifest refreshes must converge with the response.

Reuse one immutable comparison within each request and select the latest effective baseline before parsing a superseded snapshot. Start with this request-local reuse and removal of full builds. Do not introduce persistent parsed/rendered caches unless profiling still shows they are required to meet the interaction budget; any such addition needs explicit input keys, invalidation and size bounds recorded before implementation.

Acceptance: each source-choice save causes zero full builds, document/comparison renders or TeX invocations, and does not duplicate its comparison. The proposed warm-fixture budget is p95 at or below 300 ms from click to persisted confirmation. Report before/after timings and any miss; do not use fragile unit-test wall-clock assertions or optimistic button feedback as proof of improvement.

Preview and final-incorporation times may be recorded separately. Compilation-cache replacement, watcher coalescing and general viewer optimization are not required by this delivery. If measurements justify them, scope separate work with an observable trigger rather than add them to this implementation by default.

## UI principles and review

The governing principles are in [0.13.3](0.13.3-reading-ui-improvements.md) and [the Review plan](review-panel-and-precise-dependencies.md); control placement follows [0.16](0.16-documents-that-move-and-floating-controls.md). Apply them to this extension as follows:

| Principle | Design check |
|---|---|
| Open on the thing itself | Incoming opens on the selected passage and its comparison, without a Start screen or draft dashboard. |
| Say it once, where it is governed | The contribution selector owns the draft/scope identity; proposal choices own selection state. No repeated scope banners, counts panels or reviewer lines. |
| Claim only what is known | The distinct reasons and outcomes specified in §1, §3 and §4 are supplied from recorded facts, not inferred by the viewer. |
| One element, one question | Proposed edits answer what to apply; affected mathematics answers what needs checking; explicit acceptance records the mathematical judgment. |
| Following a connection preserves its origin | Dependency and affected-document links retain the inspected proposal and reading position through existing workspace navigation. |
| Show less by default | IDs, patches and file lists stay in Details. Empty groups disappear; consequential shared-source effects remain visible at the relevant choice. |

Use existing typography, spacing, color, controls and accessibility patterns. Color supplements words and state. At narrow desktop widths collapse the change list into a compact selector before stacking the comparison; inspect near 736 pixels with navigation collapsed, and at 1100 and 1440 pixels. Do not shrink formulas to preserve navigation. Local contribution actions stay on that surface, not the global rail.

No second Previous/Next system, prose acceptance ledger, permanent rejection control or latest-chat filter is introduced. Before changing the layout, make a fixture-backed design of an accumulated proposal, unchanged affected proof, shared-node effect, independent preamble choice, invalid preview and closed draft. Validate the built UI against those states and the principles, recording any gaps with reproduction steps.

## Implementation phases

1. **Measure and fix selection independently.** Establish the §6 baseline and API revision contract, implement metadata-only publication and request-local reuse, and verify the interaction budget. Section schemas and draft lifecycle design are not prerequisites for this phase.
2. **Specify section and lifecycle interfaces.** Define compatible scope, namespace, snapshot, close/reopen, annotation-link and preview schemas. Identify reusable scanner/history/rendering facilities. Finalize the fixture-backed UI states before dependent implementation.
3. **Implement section copying and lifecycle.** Add extraction, identity handling, overlap validation, synchronized rendering context and close/reopen. Verify physical-file boundaries and historical access before adoption uses them.
4. **Implement scoped adoption and Arras integration.** Extend the shared planner, projection and refresh; expose the proposal/affected-mathematics distinction, separate selection groups, reasons, invalidation messages and scoped Compare.
5. **Document and verify delivery.** Update interface specifications, agent orientation and permission tables, then the book for shipped behavior. Record deviations from decided rules with newly allocated decision IDs. Reconcile WQ-52 with the delivered non-overlapping scopes, retaining overlapping alternatives as a distinct remainder. Regenerate fixtures, rebuild/re-vendor Arras and record results below.

Primary code areas: `cli/history_cmds.py`, `cli/ai.py`, `reshape/copy.py`, `scan/sections.py`, `scan/labels.py` and their identity consumers; `history/ledger.py`, `drafts.py`, `adopt.py`; `render/api.py`, `render/serve.py`, `render/incoming.py` and historical rendering; `incorporation_review.py` for factual review reasons; and Arras's contribution, document-listing, manifest and Compare components. Exact optional fields and compatibility behavior belong in the manifest/write-API specifications before implementation. Incompatible old preview tokens may require a fresh preview; existing copies and histories remain readable.

## Verification

Use `scripts/verify fast` while implementing and `scripts/verify full` before implementation commits and final delivery. Run the documentation/work-queue checks through that workflow and read its reported CI status. Tests exercise these outcomes rather than repeat the implementation structure:

- **Selection:** no build/render/compile; persisted choices survive reload; failed requests preserve prior state; concurrent tabs and source rebuilds cannot lose decisions; no MathJax restart or reading-position loss. Record the §6 benchmark results.
- **Scope:** inline/included/nested sections, missing or duplicate IDs, source rename/reorder, root deletion/level change, overlaps at creation and after movement, old unnumbered copies, shared nodes in disjoint scopes and label/reference collisions.
- **Application:** unrelated author bytes and include structure stay intact; outside-scope omissions never become deletions; preamble and source selections remain independent; shared-source effects identify every affected paper; conflicts and injected write failures leave recoverable, verified history.
- **Lifecycle:** a whole-document draft blocks a section with a usable close instruction; closing frees the scope without losing text or annotations; old links open retained content; reopening after paper edits preserves proposals; overlapping reopen fails without altering either draft.
- **Comprehension:** a fixture has two older proposals, one new proposal and an unchanged dependent proof. Initial Incoming shows the three proposed edits without implying they came from one chat; the mathematical preview explains the proof separately. Leaving a proposal out does not imply rejection. Distinguish shared-source edits from review-only effects.
- **Context and validity:** recorded context reproduces the section view and Preview in paper; source context changes produce an honest update notice; final previews use the current paper; stale previews name the cause and retain valid choices. No-op refresh/incorporation does not resurrect old changes.
- **Review regression:** prose creates no mathematical acceptance tasks; statement/proof/dependency changes retain existing freshness; optional acceptance stays explicit; source success plus acceptance failure reports both. Whole-document adoption, collaborator pulls, personal review, static viewing and Compare still work.
- **End to end:** through CLI creation and real-server Arras, work on two disjoint sections, incorporate a shared-node and explicit preamble change, inspect the second draft's context, close the first draft and reopen it. Check the UI principles and responsive layouts with screenshots of the actual implementation. All TeX tests use the repository's isolated environment and scratch quilt.

## Delivery

Implemented on `section-drafts-responsive-adoption`, without a commit or publication. Section/subsection copies, disjoint scopes, numbered identities, saved rendering context, scoped adoption and refresh, separate preamble selection, Preview in paper, close/reopen and retained historical views are implemented. Selection publishes choice metadata without a quilt rebuild; the viewer retains mounted content when only choices change. Incoming distinguishes accumulated proposals from affected mathematics and names changed support.

Final `scripts/verify fast` passed 981 Python unit tests, 206 frontend unit tests, types, lint and documentation checks. The earlier full verification run also passed the frontend build and 14 TeX tests (with six skipped). No CI runs exist for this branch. The new scoped PDF test passed. One Biber test also fails on the unchanged base revision; Chromium cannot launch under this macOS sandbox. Consequently browser end-to-end tests, responsive screenshots and the complete click-to-confirm timing budget remain unverified here. Regression coverage includes the real-server scoped workflow at 736, 1100 and 1440 pixels, awaiting execution in an environment that can launch Chromium.

A disposable copy of `/Users/luisa/Documents/Overleaf/mZK-test` exercised two disjoint section drafts and successfully compiled Preview in paper; the original quilt was untouched. Selection measurements on the real quilt reached approximately 203 ms p95 for the local HTTP request after removing repeated scans, excluding browser rendering. A smaller server-path fixture improved from 32.60 ms to 8.85 ms p95 and from one rebuild per decision to none. These measurements precede the final conservative support-file fingerprint addition and do not establish the full browser interaction budget.
