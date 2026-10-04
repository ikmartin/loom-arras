# WQ-55 · Reviewing proposed digest results in Review, one at a time

**Repo:** arras, loom

## Trigger

`loom library review` shows proposals waiting on the author (its `waiting` column) in two or more works at once, or ten or more in one work, and the author sets out to verify them.

## Why deferred

The present surface works for a few proposals in one paper and fails past that, which the author found on 2026-09-28 reviewing Romagny's *Group actions on stacks* with three waiting. It needs a design study before any code, as compare and the floating toolbar had (`docs/reports/document-controls-study.md`), because what is wrong is the layout and not one bug; and nothing else waits on it.

## What is wrong now

Proposals stand under a work's Digest view (`WorkItem.svelte`), one `ProposalBox` each, as book 8.14 describes: the page on the left, the rendering on the right. Seen in the author's screenshot:

1. **Raw data leads.** Each card opens with the result's internal id (`romagnyGroupActionsStacks2005-def-2.3`) and the artifact's hash (`3d045db2f979`), neither of which a person verifying needs.
2. **The rendering is the narrow column.** The page image takes most of the width, and the rendering beside it, which is the thing being checked, is squeezed until its text runs off the right edge and is clipped.
3. **A page can be blank.** The second card's page image drew nothing; the cause is not yet known.
4. **The most useful signal reads as debug output.** The words of the rendering the page does not have ("not in the quoted page text: Let sheaf groups over") are code chips under the card rather than marks in the text.
5. **The verbs are apart from what they judge.** verify, edit and discard stand away from the result, and discarding asks for its reason only on the command line.
6. **Proposals are per paper.** Nothing gathers what waits across the library, so the author finds proposals by opening each work.

## Rough design

A third view in Review, beside Needs review and Incoming, which already reviews an agent's proposals with explicit choices (DR-313-luisa):

- **One queue** of every waiting proposal in the library, grouped by work, with the count on the view's tab; a work's Digest view lists its results and links to the queue when some are waiting, rather than holding the cards itself.
- **One result at a time, at full width**: the paper's words on top, cropped to the region of the page that holds the statement rather than the whole page, and the rendering beneath at the same width, so the two are compared by reading down, not across.
- **Names, not ids**: "Definition 2.3 · Romagny, *Group actions on stacks*, p. 7"; the id and the artifact's hash in a details fold for when something is wrong.
- **Mismatches marked in the rendering**, as compare marks changed words (DR-311-ikmartin), with one plain line: "3 words not found on the page".
- **Verify, edit and discard directly under the result**, with keys to act and move to the next; discard asks for its one-line reason in place, since the reason is what `propose` returns to the next agent that proposes the same result.

## The design study

Before a plan, a study in `docs/reports/digest-review-study.md` with a static demo page and screenshots of the current surface beside the proposal, as the controls study did:

- the states to draw: one proposal; a proposal with mismatched words; a work with no readable copy (source only, DR-198); a blank or failed page image; three works waiting at once; a result the author edited before verifying; a discard with its reason;
- the layout at a full pane, a half pane and phone width, light and dark;
- the keyboard path through ten proposals without the pointer;
- the question the study must settle: whether the page crop comes from the quads the publisher already writes (`spans/…json`, the ones the proposal test routes) or needs something new from `loom library update`'s map step.

The blank page image is investigated first and fixed on its own if it is a bug rather than a design question.

## Blast radius

`arras/src/lib/review/ProposalBox.svelte`, `arras/src/lib/workspace/items/WorkItem.svelte`, `arras/src/routes/review/+page.svelte`; the manifest's `references[…].proposed` and `results`, if the queue needs anything they do not carry (a waiting count per work); the write API's verify and discard endpoints, if discard's reason is not already carried; book 8.14's verifying paragraph and 15's Review section; `tests/e2e/library.e2e.ts`'s digest tests, which follow the cards to their new place.

## Related

DR-177 (verifying claims faithfulness only), DR-179 (why the page is shown), DR-201 (the viewer draws the page), DR-313-luisa (Incoming), [WQ-38](WQ-38-digest-blocks-in-their-own-preamble.md) (a digest block's raw-TeX error box, which the rendering half of this view would show).
