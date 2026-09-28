# Review that opens on the mathematics, and dependencies that name what was used

**Status: implemented on `review-blocks`; browser validation blocked by the local sandbox**, 2026-09-28. The implementation adds a separate precise mathematical dependency context, the Review workspace, and rendered prose/document inspection in Incoming. DR-314-luisa records the structural-versus-mathematical distinction. Backend, frontend and documentation verification are recorded below; the approved illustrations remain design references rather than browser verification evidence.

## Purpose

Review should put the reader in front of the mathematics that needs a decision, with the evidence for that decision beside it. A dependency should ask for attention when the thing relied on changes. An unrelated edit elsewhere in its containing section should ask for nothing.

These are one piece of work at two layers. Making the panel quieter without narrowing the causes leaves a smaller interface carrying the same false alarms. Narrowing the causes without showing the changed equation and its use leaves the reader to reconstruct why a block appeared.

## Context

**The review machinery already exists.** `arras/src/routes/review/+page.svelte` has working-document tabs, Needs review, Incoming, a guided comparison, personal review decisions, and Finish review. Pending OK is distinct from acceptance. The queue already suppresses certain indirect causes provisionally and restores them if the upstream decision becomes invalid. These are useful semantics to preserve.

**The panel makes the reader pass through its own account of itself.** The route renders a title, reviewer line, navigation and explanatory lead before its content. Document mode adds six summary counts and a table with state, basis, date, causes and further columns. Needs review requires Start review, selects the first cause with a comparison, and continues to render the three queue groups below the active block, including empty groups. This is a source inspection, not a measured browser study; the first phase establishes what the current screen actually costs.

**The equation's identity survives scanning, but its dependency scope does not.** `scan/nodes.py` records labelled regions with their label, owner and offset. In `scan/edges.py`, `_resolve` maps a referenced region to `region.container`. `Records.closure_hashes` in `records/store.py` then hashes environment and section nodes. This is a concrete code path consistent with the reported false alarm; a regression fixture must establish the exact case before the fix is claimed.

**The queue has the same broad comparison.** `review_queue.fingerprint` hashes the own text of nodes in the dependency closure. Changing only the stale-cause calculation would still let an unrelated section edit invalidate a pending OK or Requires attention decision. Acceptance, queue decisions, origin baselines and comparisons must agree on the dependency context.

**A labelled region is not yet a complete independently tracked unit.** The scanner's `RegionRec` stores a label position, not a verified mathematical extent or a dependency signature. Published regions are already link and annotation targets, but that is not evidence that their published spans suffice for freshness. Precise extraction is part of this work.

## The six principles, applied to Review

1. **Open on the thing itself.** Entering Needs review opens the first outstanding block, or the block named by the link, with its evidence. No Start review screen stands between them.
2. **Say it once, in the place that governs it.** The queue chooses the block; the cause selector chooses the evidence; the decision controls record the choice. Counts belong to those controls, not to a second summary paragraph.
3. **Claim only what is known.** A changed equation is named as a changed equation. A missing earlier equation is explained in ordinary language. Pending decisions are never drawn as accepted. No claim of mathematical equivalence is inferred from an unchanged formula alone.
4. **Name the question. One element, one question.** The queue answers what needs review. The main pane answers what is being reviewed. The evidence pane answers why. Details answers how the record was obtained.
5. **Following a connection must not cost the thing followed from.** Opening a dependency keeps the reviewed block, its citation, queue position and pending decision available.
6. **Show less by default.** Accepted history, raw identifiers, source diffs and empty groups stay out of the working view until needed. Every actionable reason remains discoverable.

## Scope

This delivery covers the `/review` surface, rendered prose inspection in Incoming, selective AI incorporation with final preview, mathematical review after incorporation, exact equation targets in freshness, and the common dependency context used by review decisions. It preserves personal acceptance, shared-block identity, staged Finish review, and the existing distinction between source incorporation and mathematical acceptance.

Equation targets are the first precise regions. Figures, tables and list items retain their existing behavior until their extent and meaning have been specified and tested. Semantic inference from arbitrary prose, automatic proof checking, and automatic acceptance are outside this delivery. The alternatives below record the limits of this delivery; they are not additional implementation phases.

## The design

### 1. One working surface

Bare `/review` opens Needs review. An explicit document or Incoming URL still opens that view. When no undecided blocks remain, the body reflects the remaining work: “2 decisions ready to record” with Finish review if choices are pending; “3 blocks still require attention” with that group open if concerns remain; or “Nothing needs review” only when neither exists. If both groups remain, show both. Incoming remains separately available and is not described as accepted work.

Keep three distinct destinations: **Needs review**, **Documents**, and **Incoming**. Documents uses one document selector instead of one top-level tab per filename. Existing document URLs remain resolvable. The reviewer name appears once beside the controls whose decisions it governs.

In Needs review, a narrow queue sits beside the current block and its evidence. The following is a layout sketch, not a pixel specification:

```text
Needs review (4)   Documents   Incoming           Reviewing as Luisa

Queue                 Lemma 4.2                 Equation (2.3) changed
                      Current block             Since your acceptance
  Proposition 3.1     … citation of (2.3) …      Before / Now
> Lemma 4.2                                     … changed formula …
  Proof of 4.2

Ready to record (2)   Mark OK   Requires attention   Skip
Requires attention    Finish review · record 2 decisions
```

The queue renders one short name and, where needed to distinguish entries, one reason. The incorporated AI draft or collaborator contribution is identified once below the active block title when it explains the current review; technical provenance stays in Details. Ready to record and Requires attention are collapsed groups with counts while undecided work remains; empty groups disappear. Ready to record is the user-facing name for pending OK, not a new stored state. The active block is not listed again underneath its own comparison.

Current text and comparison evidence appear beside one another whenever readable. Collapse the queue to a disclosure or compact item selector first; do not stack the comparison merely because a desktop sidebar consumes its width. Stack only when the two text panes themselves no longer fit, preserving the selected item, cause and scroll position. Apply this rule to both Needs review and Incoming. Validate a side-by-side comparison at the conversation-preview width of approximately 736 pixels with navigation collapsed, as well as at 1100 and 1440 pixels; use the narrow mobile layout only when needed. Long formulas must remain readable without shrinking the whole page.

### 2. Evidence is selected by cause

Every active cause is available under “Why this needs review.” A single cause is a plain heading; several causes produce a selector showing the current reason and position, such as “Equation (2.3) changed · 1 of 3.” Selecting one updates the evidence without replacing the reviewed block. The default is an own-text change when present, otherwise the first cause in a stable publisher-provided order. Having no renderable comparison must not make a cause disappear.

For an own-text edit, show the current block beside the version this reviewer accepted, with the existing word-level comparison. For an equation dependency, keep the citation visible in the current block and show the exact equation before and now in the evidence pane. Surrounding text can be opened for context without becoming part of the displayed claim about what changed.

**A changed lemma is its own review item.** Show the current statement beside the active reviewer's last accepted statement, with changed words and formulas marked. When inspecting its unchanged proof, keep that proof visible and show the changed statement as the evidence, including earlier/current statement text where available. Direct users of the changed lemma remain review items when their dependency signatures changed. Marking the lemma OK or accepting it does not automatically accept its proof or clear independent direct causes. A new lemma with no earlier acceptance says “No earlier acceptance” and shows its current statement without fabricating an old version.

**Authorship and acceptance are distinct.** “Reviewing as Luisa” identifies the active reviewer; “Last accepted by Luisa · [date]” identifies the displayed baseline. A known change source appears as “Source: AI draft [name]” or the recorded collaborator. Never infer an edit author from the person fetching, incorporating or reviewing it. For an unchanged proof affected by an AI statement edit, the agreed label is **“Existing proof · statement changed in the AI revision”**. Do not say that the proof itself was edited by AI when only its statement changed.

For an indirect cause, say “This block uses Lemma 3.1, which uses the changed equation (2.3).” The evidence follows the immediate dependency and explains the chain. It never invents a direct citation to a remote ancestor. Missing targets, unavailable snapshots, classification changes and preamble changes each get their own truthful explanation and the evidence actually available.

The main heading uses the document's equation number when known, then its label; no guessed number. Raw keys, first-observed dates and source paths belong in Details. Color supplements words and change marks; it does not carry the only explanation.

### 3. Decisions stay where the reading ends

Keep the existing two-stage decision process, using **Mark OK**, **Requires attention**, and **Finish review**. Under Mark OK, say “Recorded as accepted when you finish review.” Requires attention moves the block to the named group without accepting it; that group allows reopening the block. Finish review records eligible pending decisions after validation and reports how many were recorded and which, if any, need another look. An empty undecided queue never implies the pending decisions were recorded.

After a successful choice, refresh the queue and choose the next surviving entry from the refreshed result. Do not choose it from the old queue: an upstream OK may have removed it. Use the queue and browser Back to return to earlier items; do not add a second Previous/Next system. A single Skip control moves to the next undecided block without saving a choice, leaving the skipped block in the queue. A failed save keeps the item visible with its choice uncommitted and an error next to the control.

If an upstream Mark OK provisionally removes dependent blocks, show one inline result beside the decision area: “2 dependent blocks set aside until you finish review,” with a disclosure naming them and explaining that they return if the upstream decision changes. This explains existing queue behavior, not a new decision state. The publisher supplies the affected blocks and their reason; the viewer must not infer them from a shrinking count. If they return after an edit, explain “Equation (2.3) changed again; these blocks need another look.” Keep this explanation at the affected action or rows, not as a permanent dashboard. Once Finish review succeeds, report the actual result without claiming those dependents received new acceptances.

Changing reviewer resets the working selection and loads that reviewer's decisions. A source update invalidates only decisions whose recorded review context changed. Finish review rechecks the reviewer and context server-side; the layout does not weaken those checks. Requires attention remains explicitly unaccepted and can be reopened.

Store the selected block and a stable cause identifier in the URL so reload, Back and a copied link recover the review location. A selector index is insufficient when causes change order. Restore scroll position within the review session. An item that ceased to need review remains readable when explicitly linked, with its current state; the interface does not silently substitute another block under the same URL.

### 4. Documents is the record

The document view opens on a compact list: block name, recorded state, and an actionable reason where one exists. Dates, basis, provenance, reached-by lists and detailed review facts move into each row's disclosure. Missing proof, incompleteness and unclassified basis remain visible when they require action; they are not hidden merely to reduce columns.

Do not add a new filter system or a new history browser in this renovation. Preserve existing supported filters where present. Any retained filter count comes from the same document rows; remove the separate six-count summary. Selecting a shared block uses its existing common identity and personal review state; no document-local duplicate acceptance is created.

### 5. Incoming is a source decision

Incorporation stays in **Review → Incoming**. Its changes list is an inspection list, distinct from the mathematical acceptance queue in **Needs review**. It includes prose passages and mathematical blocks so the reader can inspect the complete source change before applying it.

#### Fetched collaborator changes

Fetch retrieves a revision for inspection and never applies it to working source or records mathematical acceptance. Incoming displays “Fetched revision · not incorporated,” the known contributor, and the current working passage beside the fetched passage. In a conflict-free case these are the versions the reader is deciding between; when local edits or conflicts prevent a direct comparison from describing the actual application, retain the existing conflict checks and require reconciliation rather than imply that the incoming pane is the merged result.

Group prose changes by section and identify each changed passage. Selecting “§2 · Introduction — prose edited” opens rendered before/after text with word-level additions and deletions, with enough surrounding text to orient the reader. Added or removed passages have an explicit empty side. Prose and mathematical changes share this Incoming list; Previous change and Next change navigate that inspection list only. At narrow desktop widths a compact passage selector replaces the list before comparisons stack. Raw source diffs, file inventories and revision identifiers remain available behind disclosure; any changed source that cannot be rendered must remain visible with a source-diff fallback, never silently omitted.

**Prose has no Mark OK, accept, dismiss or mark-read control.** A passage outside mathematical blocks creates no mathematical acceptance task merely because its text changed. Prose within a lemma, definition or proof is part of that mathematical unit and follows its ordinary freshness rules. Preamble or structural changes are displayed honestly and keep their existing effects; “document changes” must not be labelled harmless prose when they alter mathematical context.

**Incorporate pull** explicitly applies the entire pinned pull after the existing revision/base and conflict validation. Its label or adjacent copy states that it applies all changes in that pull. Navigating to one passage does not select only that passage for incorporation. This plan does not introduce selective collaborator-pull incorporation.

#### AI contributions

Incoming identifies the AI draft and offers **Use proposed version** or **Keep current version** for each eligible statement or proof. Prose, preamble and ordering remain one explicit **Prose & document changes** selection group, as in the existing adoption contract; displaying individual prose passages does not imply separate selection per paragraph. When the group contains only prose, say so; otherwise its preview lists the preamble and ordering changes too.

These controls choose source versions. They never make a mathematical acceptance decision. Begin with the current reviewer's saved choices when valid, or with no proposals selected. The interface must distinguish an unselected proposal from an explicit Keep current choice, while both remain unapplied. **Preview selected changes** opens the exact proposed source changes before **Incorporate selected changes** performs the write. The preview contains every selected source change, including document-level changes and any required additions; it cannot omit an unrenderable change. Back to choices returns without writing source.

Reuse the existing server validation: a changed working source, AI draft, reviewer or selection invalidates the preview. Conflicts or unresolved required dependencies stop incorporation and direct the reader to reconciliation followed by a fresh preview. Do not silently add an unselected mathematical proposal to satisfy a dependency. Keep the original AI draft and its annotations accessible after incorporation. Proposals kept or left unselected remain in that draft and appear again while they differ from the working document.

#### After incorporation

Report exactly what was applied and provide links to read the updated passages. A prose-only change outside mathematical blocks creates no new mathematical acceptance tasks; it must not hide or clear pre-existing review tasks. A mixed change offers **Review affected mathematics**, with the actual publisher-derived affected count rather than the mockup's illustrative count of two. Incorporation itself writes no acceptance.

In Needs review, an AI-modified statement is compared with the active reviewer's accepted baseline, not automatically with the AI draft's creation base. **Mark OK → Finish review** records personal mathematical acceptance. The statement can be accepted while its proof remains Requires attention. Changed direct dependents retain their own applicable decisions; indirect provisional coverage follows §3. New statements use the missing-baseline treatment in §2.

After incorporation, ordinary document comparison remains the place to inspect prose differences between versions independently. Reuse that existing surface with a visible comparison version where available; do not create a prose acceptance history or attach unrelated section edits to a lemma's review details. Incoming provides inspection before application, and document comparison provides subsequent comparison without changing review state.

## Dependencies: settled boundaries and implementation

**Settled with the author:** section references are navigational; equations are tracked without separate acceptance tasks; freshness follows the whole display and explicit mathematical dependencies only; enclosing prose is not inherited. These rules apply to equations in sections, theorems, definitions and proofs alike.

Sections retain their existing nodes for structure, navigation and annotation targets. Equations retain ownership information and gain precise dependency signatures; statements and proofs retain their acceptance units.

**Contains and depends on are distinct relations.** `Section S contains Equation E` records where E belongs; `Proposition P depends on Equation E` records what P uses. Neither relation implies that P depends on S or on another block inside S. This remains true through any number of nested sections. Section nodes take no acceptance and impose no acceptance, proof or settlement obligation on their children or on users of those children.

For a section containing equation E and lemma L, with proposition P referencing only E: editing section prose leaves P fresh; editing L leaves P fresh; editing E makes P stale. Existing genuine mathematical obligations, such as a proof's relation to its statement, remain explicit.

### 6. Preserve the referenced object

A reference needs two identities: the exact target used for freshness, and its containing node used for navigation and ownership. Preserve the equation label through resolution instead of replacing it with the owner. Several references from one block to the same target share one dependency signature while retaining their individual citation locations.

Introduce a typed dependency target and a freshness traversal that can visit node and region targets. The traversal contract is: containment and section-navigation relations serve structure, reachability, links and annotation placement; mathematical dependency relations serve freshness, cause propagation, pending-review fingerprints, review ordering, and mathematical blocking or settlement. A structural path must never become a mathematical path implicitly. A diagnostic or navigation tool that intentionally walks both relations must distinguish its results rather than label all reached blocks as mathematically affected. Audit edges currently called `nested` by their actual purpose: nesting in the source is not sufficient evidence of dependency.

Ordinary edits to a reviewed block's own prose still change that block; the narrowing concerns what its dependents relied on. In the UI, call the target “Equation (2.3)” or its actual label, never “region node” or “dependency signature.”

### 7. Bound the equation before hashing it

For a standalone labelled equation, use the complete enclosing math environment. For `align`, `gather`, `split` and similar groups, use the complete enclosing display, including all its lines. A nested `split` belongs to its enclosing display. Labels in the same display share its content signature. Row-level extraction is outside this plan; the author selected whole-display tracking.

Compute signatures from source using the existing conservative normalization, with a versioned extraction policy. Numbering and file position are presentation facts, not mathematical content. Test label-only and number-only edits explicitly rather than assuming the current hash already ignores them. The implementation must not normalize away TeX tokens that may change meaning.

Each target retains its exact snapshot and render context. Preserve existing conservative preamble invalidation initially: an unchanged equation can change meaning when a macro changes. Reducing that separate source of noise requires its own macro-use analysis.

For an unsupported or ambiguous equation extent, say “Cannot identify the full equation for [label]” and give the specific reason and a link to its source. Explain that the system cannot verify whether this dependency changed; no repeated acceptance should be offered as a remedy for unsupported extraction. The implementation needs a distinct unavailable outcome rather than inventing a content change. It must not silently regain a section-wide signature, and it must not be declared fresh. Only users of that unresolved target need the diagnostic. Such cases are measured in the fixture study before deciding whether the first extractor covers enough real equations to ship.

### 8. Track support deliberately

An equation inside a theorem, definition or proof does not automatically depend on that owner's surrounding text or assumptions. Editing the enclosing hypothesis invalidates the owner's own acceptance as applicable, but does not invalidate a block that depends only on the unchanged equation. A block that also explicitly references the enclosing theorem retains that separate dependency and becomes stale when it changes. Apply the same rule to pending decisions, not just recorded acceptance.

Explicit mathematical references occurring within the display provide its support edges; references elsewhere in its owner do not. A section reference remains structural wherever it occurs; a removed section still produces a dangling-reference diagnostic. Traverse explicit support transitively using the same precise-target rules. Reusable assumptions may be expressed as labelled mathematical blocks and explicitly referenced, but a reference merely adjacent to a display is not automatically assigned to that display. Author-declared support outside a display would require a separate, designed mechanism and is not a prerequisite for this fix. Tracking detects changes in recorded dependencies; it does not discover unreferenced mathematical assumptions or claim semantic completeness.

### 9. Use one dependency context everywhere

One derivation returns the exact targets, relevant support edges, signatures, availability and policy version. Acceptance, stale-cause calculation, pending-decision fingerprints, Finish review, local-change origin checks and comparison publication consume it. The viewer consumes causes and evidence; it does not recompute freshness.

Preserve the existing distinction between direct and indirect causes. Re-accepting an unchanged intermediate can resolve an indirect cause as today. A pending OK remains provisional, and a separate direct cause keeps its dependent in the queue. Narrow targets must not turn “one upstream block was reviewed” into “all downstream mathematics is accepted.”

### 10. Older acceptances need an honest transition

New acceptances record versioned target signatures and enough source/render context to reproduce the evidence. Existing ledger entries remain immutable.

Where an older accepted snapshot contains enough information to reconstruct the exact equation, its identity and required context, derive the historical target signature from that snapshot. Never use the current equation as a substitute for the accepted equation. If reconstruction is not reliable, keep the acceptance history and say “The earlier version of this equation is unavailable. Review the current version once to record it.” Explain that the system cannot establish whether it changed; do not show a fabricated diff. When current extraction is supported, the ordinary Mark OK and Finish review flow records the new baseline. This message is specific to older records, unlike an equation that cannot currently be extracted.

Version pending-decision fingerprints too. Older choices whose exact context cannot be established remain recoverable as earlier decisions but cannot be silently reused as current OK. The study measures this transition's queue size; a rollout that turns every accepted paper into a fresh review is not considered successful merely because it is conservative.

## Alternatives outside this delivery

The author has chosen exact whole-display tracking, structural section references and existing statement/proof acceptance. These are settled requirements, not competing brainstorm options.

Explicit support declarations, per-dependency acknowledgement, macro-use analysis, AI equivalence suggestions and grouping decisions by shared cause are not included. Each adds authoring rules or decision semantics that the section fix does not need. Examples where an equation relies on prose outside its display may inform a later support-declaration design; no syntax or new control is introduced here.

Fixed line windows are rejected because distance does not determine support. Removing section nodes altogether is rejected because navigation and annotation ownership still need them. Neither workaround replaces precise dependency targets.

## Delivery

### Phase 0 · Establish the defect and the visual baseline

Create an isolated fixture with a section, two labelled equations, a later block using one equation, and another block using an unrelated result. Record acceptance, edit distant section prose, and capture the resulting states, queue, pending-decision behavior and cause evidence. Repeat with an actual change to the referenced equation. Do not work on the author's paper sources.

Repeat the fixture under a section, subsection and subsubsection, with a sibling lemma and a proof. Record acceptance eligibility and proved/settled outcomes as well as stale causes. This establishes whether any structural ancestor or sibling leaks into mathematical blocking, even when the displayed stale badge happens to be correct.

Capture the current panel at 1440, 1100 and approximately 736 pixels, plus the supported narrow layout: document record, one cause, multiple causes, changed lemma and unchanged proof, pending decisions, empty queue, fetched prose, AI selection and final preview. Measure how much of the first screen belongs to mathematics and which steps are required to inspect a cause. This phase produces the study and the regression cases, not a claimed implementation.

### Phase 1 · Specify precise targets and historical evidence

Add extraction fixtures for standalone equations, grouped displays, nested math environments, multiple labels, missing labels and ambiguous extents. Specify exact-target identity, explicit support edges, serialization and the extraction version. Apply the relation contract in §6. Inspect all consumers of `Graph.direct`, `Graph.closure` and `Records.closure_hashes` before choosing how the new freshness traversal integrates with them.

Specify the manifest additions and old-ledger transition alongside the implementation design, including stable cause identities, the explanation of provisionally omitted queue entries, and source attribution distinct from reviewer identity. Specify paired incoming prose fragments, section/passage locations, revision-bound comparison identities, and complete source-diff fallbacks. Derive passage locations within the compared revisions; do not create durable paragraph nodes or prose acceptance records. Reuse existing comparison/rendering and contribution contracts where they supply these facts. Exit criterion: every supported target has a reproducible extent and evidence baseline; unsupported targets have an explicit outcome.

### Phase 2 · Make freshness and review agree

Implement the target, display and explicit-support rules in §§6–8. Wire the consumers listed in §9 to the common context. Update the existing comparison publisher in `render/review_compare.py` to produce exact equation evidence with the relevant old and current render contexts.

Apply §6's relation contract to settlement, mathematical blocking and review ordering as well as freshness. Test existing proof/statement and genuine nested mathematical dependencies so excluding structural parents does not accidentally remove real obligations. Smaller equation hashes alone do not satisfy this phase if another consumer still traverses the section parent as support.

Exit criterion: the distant-prose edit leaves the equation user fresh and preserves its pending decision; editing or removing the referenced equation triggers a specific, inspectable cause. The same result appears through status, build/serve and Review.

### Phase 3 · Build the review surface

Extract pure presentation derivations into `arras/src/lib/review/`; keep route code responsible for composition and navigation. Build the queue, selected-cause evidence and decision area using existing fragments, comparison styles, display names and design tokens. Replace the first-comparison-only selection with explicit cause navigation. Derive the next review item after refresh.

Build document disclosures and the document selector. Implement lemma/proof evidence and attribution from §2, including the exact AI-revision label. Implement the comparison-first responsive behavior in §1. Keep deep links, keyboard access, focus return, live-update behavior and honest missing-evidence states part of the component work.

### Phase 4 · Render Incoming changes and preserve incorporation boundaries

Implement §5's complete incoming change inventory and rendered prose comparisons in the publisher and viewer. Preserve unrenderable source changes in the inventory with an explicit diff fallback. Reuse existing source-span and comparison machinery; do not infer prose harmlessness from a viewer-side label. Mathematical-block membership and the existing context rules determine whether incorporation affects acceptance.

Build the mixed inspection list, passage navigation and raw-source disclosure. Keep full-pull incorporation separate from the AI draft's per-block and document-group choices. Reuse and test the existing AI preview and write endpoints; retain pinned revisions, invalidation, conflict handling and original-draft access. The resulting Needs review items use the same personal baselines and precise dependencies as edits made locally.

Exit criterion: a fetched prose change is inspectable without altering source; a pull applies only on explicit incorporation; an AI prose-only selection applies no unselected lemma and creates no new mathematical acceptance task; a selected AI lemma enters personal mathematical review after incorporation. Existing pending work survives all these paths correctly.

### Phase 5 · Check the principles against the built result

Repeat the baseline scenes in both themes, with long mathematics and keyboard-only operation. The first outstanding block must be visible on entering Needs review without an intermediate button. Its cause and decision controls must be reachable without reading a summary dashboard. Opening evidence must preserve the reviewed block. No empty group or duplicate active-block list remains.

Verify that every suppressed item is suppressed because of actual review semantics, not a frontend filter hiding an unresolved cause. Record remaining exceptions explicitly. Update screenshots, the plan's delivery record, and the implemented book/specification only as behavior lands.

## Verification

Use `scripts/verify fast` while working and `scripts/verify full` before a commit, selecting the relevant loom, arras or docs lane when appropriate. Read the CI results printed by the verification script. All TeX test compiles use the repository's isolated environment.

The core acceptance matrix is behavioral:

| Change after acceptance | Expected result |
|---|---|
| Distant prose in the equation's section | Equation-only user stays fresh; pending decision survives |
| A different standalone equation in that section | User of the unchanged equation stays fresh |
| Sibling lemma changes while P references only equation E | P stays fresh; its pending decision survives |
| Prose or heading changes in any of several ancestor sections | No stale propagation, pending-decision invalidation or mathematical blocking through containment |
| A child statement and its proof satisfy their actual mathematical obligations | Acceptance and settlement require no acceptance or settled state on any containing section |
| E changes beneath several nested sections | P becomes stale through its explicit reference to E; the cause does not name a section as support |
| Section containment is retained or reorganized with target identity and mathematical context preserved | Document navigation and annotation ownership work without adding mathematical dependencies |
| A genuine proof/statement or nested mathematical dependency changes | Existing mathematical obligations remain effective despite exclusion of structural containment |
| Referenced equation content | Its users need review with exact old/current equation evidence |
| Another line in the same coupled display | Users need review under the documented group policy |
| Referenced equation removed or label unresolved | Specific missing-target cause; no invented comparison |
| Equation renumbered without changed mathematical content | No mathematical stale cause; navigation displays the new number |
| Equation moved | Identity and support are checked; position alone does not trigger review |
| Enclosing theorem hypothesis changes; user references only its unchanged equation | Equation user stays fresh; the theorem's own acceptance changes as applicable |
| Enclosing theorem changes; user explicitly references both theorem and equation | User becomes stale through the explicit theorem dependency |
| Explicit mathematical support referenced inside the display changes | Equation users receive the applicable direct or propagated cause |
| Reference outside the display changes in its containing block | No inherited equation dependency; equation-only users stay fresh |
| Referenced section prose or heading changes | Navigation-only reference produces no mathematical stale cause |
| Referenced section is removed | Dangling-reference diagnostic remains; no section-content freshness comparison |
| Relevant macro changes | Existing preamble protection remains effective |
| One of several independent causes resolved | Remaining causes keep the block in review |
| Upstream pending OK invalidated | Provisionally covered dependents reappear where still affected |
| Reviewer changes or another reviewer accepts | Personal state and baseline remain separate |
| Old acceptance lacks recoverable equation evidence | Honest baseline-unavailable state; no silent fresh claim |

The incorporation and acceptance matrix complements the dependency matrix:

| Action or state | Required result |
|---|---|
| Fetch a pull containing prose and a lemma change | Working source and acceptance remain unchanged; both changes appear in Incoming |
| Inspect a section-prose change | Rendered current/fetched text is available; no mathematical acceptance controls |
| An incoming source change cannot be rendered | Visible inventory entry with source diff; no hidden part of the pull |
| Incorporate a fetched pull | Applies the pinned pull as a whole, after validation; prose is not a separate acceptance task |
| Keep an AI lemma and select only its prose group | Prose is incorporated; the working lemma remains unchanged and its proposal remains accessible |
| Select AI prose and a lemma | Final preview includes both before source is written |
| Working source, draft, reviewer or choices change after preview | Incorporation refuses the stale preview and requires a fresh one |
| An unselected AI proposal is required by a selected change | Explicit dependency/conflict outcome; no silent expansion of selection |
| Incorporate an AI lemma | No acceptance is written; statement, proof and actual affected dependents enter review as applicable |
| Mark that lemma OK, then mark its proof Requires attention | Finish review may record the eligible statement; proof remains unaccepted and accessible |
| Another contributor authored the edit | Attribution names the known source; acceptance still belongs to the active reviewer |
| A statement has no earlier acceptance | Current text and missing-baseline explanation; no invented prior statement |
| A prose-only incorporation occurs with an existing review queue | No new prose acceptance task; existing review work remains |
| Inspect prose after incorporation | Use versioned document comparison or read the updated passage, without changing acceptance |
| Review at approximately 736 pixels | Navigation collapses before readable comparisons stack; no clipped controls or text |


Browser tests cover direct entry; pending-only, attention-only and genuinely empty queues; all-cause selection; decisions across refresh; explained provisional removal and return of dependents; Finish review results and failures; Skip without a decision; reopening Requires attention; readonly/missing-identity behavior; shared blocks across documents; distinct old-record and unsupported-extraction messages; and return from dependency context. Cause links remain correct when causes reorder. Existing incorporation tests continue to protect source writes and preview validation. Add tests for changed behavior, not snapshots of component internals.

## Book and interface changes

When implemented, update book chapters 5 and 7 for region dependencies and review context, chapters 10 and 15 for Review's entry and layout, and `docs/specs/manifest.md` and the write API specification where their contracts change. Add the required decision records and deviation rows for the changed `[decided]` behavior, using the repository's next available record number at implementation time. Do not preallocate IDs or describe these proposals as shipped.

## Remaining implementation questions for the first study

The dependency scope is settled: whole displays, explicit mathematical support, navigational section references, and no implicit inheritance from enclosing blocks. The study must establish which real equations have extractable extents, how much old acceptance evidence can be recovered, and which existing graph consumers need a separate structural view. Cases relying on unreferenced prose are recorded as a limitation and possible input to a future explicit-support design; they do not justify silently broadening the selected scope. The approved examples govern the layout and user-facing flow. Remaining work concerns implementation details, real rendering and validation, not reopening the settled dependency rules or moving incorporation out of Review.

## Approved interface references

The following prototypes were approved in this conversation. They are interactive design references, not application code. Their sample names, dates, counts and mathematics must be replaced by publisher facts. Their scenario selectors, simulation notices and design-tweak controls are not product features. Earlier mockups that stack too soon or show an unrelated section edit inside lemma details are superseded by §§1 and 5.

All reference fragments live under `/Users/luisa/.codex/visualizations/2026/09/28/01a0e951-3c57-7881-8828-5e3c17bbb3e8/`:

| Reference | Implementation coverage |
|---|---|
| `review-panel-examples.html` | Equation and lemma comparisons, all-cause inspection, pending/attention groups, completed review; §§1–4 and Phase 3 |
| `incoming-prose-review.html` | Rendered prose beside fetched text, mixed change navigation, explicit whole-pull incorporation; §5 and Phase 4 |
| `incoming-ai-review.html` | Per-block AI version choices, separate document-change group, final preview, retained original draft; §5 and Phase 4 |
| `ai-mathematical-acceptance.html` | Incorporated AI source, current statement versus personal acceptance, separate proof concern, exact revised label; §§2–3 and Phases 3–4 |

The prototype's ability to click through a workflow does not replace backend checks. Completion requires the real application to pass the dependency and incorporation matrices, render the approved states, and preserve the existing source-write safeguards.

## Implementation verification

Implemented in `loom/` and `arras/` with regenerated demo and conformance fixtures. Regression coverage includes section prose and removal, complete multi-line displays, equation movement, enclosing statement edits, explicit support, reviewer separation, unsupported displays, legacy snapshot recovery and missing baselines, pinned incorporation and AI choices. `scripts/verify full` built the application and ran the suites; browser suites could not launch Chromium because macOS denied its Mach-port registration in the sandbox. A separate existing TeX import test failed when biber could not open its temporary log. These environment failures remain visible; no tests were skipped to manufacture a passing full run.

Final fast verification passed: 933 backend unit tests, 203 frontend unit tests, Python and Svelte type checks, lint/format and documentation agreement checks. The production app build passed. Browser and TeX limitations above remain unresolved in this environment.

Pending review decisions publish only unresolved and covered queue metadata, without rebuilding document renderings or triggering the source watcher. Finish review validates and records the batch, then rebuilds the view (DR-315-luisa).

Incoming mathematical acceptance (DR-316-luisa): every mathematical preview item starts pending. Accept explicitly selects acceptance on final incorporation; Keep for review and unvisited items stay pending. Whole-pull incorporation remains intact, and AI retains source selection. Include unchanged affected proofs as separate decisions, bind choices to the inspected source, patch and reviewer, and show acceptance/pending counts on submission. A successful incorporation followed by failed acceptance is reported as two distinct outcomes. Verify source/proposal drift, no implicit acceptance, unchanged proofs, partial acceptance, prose-only changes and compile failures.
