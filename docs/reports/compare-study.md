# Compare: a study

The design of **compare**, the rail's control for reading two documents against each other, settled with the author on 2026-09-26 and built in plan 0.17 beside the AI drafting of [ai-drafting-study.md](ai-drafting-study.md), whose §9 it completes. The drafts, the critique and both final states are in the demo page, [images/0.17/demo.html](../plans/images/0.17/demo.html), published at https://claude.ai/artifact/ThJxYy2RNkYxkiJd9qgvVF; the screenshots of the final designs are in [docs/plans/images/0.17/](../plans/images/0.17/). Every design is drawn in the `p1` format, the compiled page.

Part one is what was decided. Part two is how it was reached, kept so that no rejected option is proposed again without its reason. Part three is what it changes in the book and the code.

## Part one: the decisions

### 1. What compare is

- **A mode of the two panes.** The rail's **compare** (drawn disabled since plan 0.16) compares the focused item of the left pane with the focused item of the right. It is a toggle: pressed while comparing, released to stop. It is never a new tab or item, which would copy what the panes already show.
- **What can be compared:** documents (in `drafting/` or `drafting-ai/`), landmarks, and nodes. A paper, a session and a node's context have no nodes with ids to pair, so compare is disabled while either pane's focused item is one, its title saying why.
- **It ends when either pane's focused tab changes**, since the comparison was of those two items.
- **It works in every format** (`p1`, `p2`, `b1`, `b2`); its marks stand outside the text or as a wash on it, never in the format's own furniture.
- **Each side typesets with its own macros**, as Review's comparisons already do (`isolatedMacros`), since the two sides may be versions whose macro definitions differ (WQ-51).

### 2. Pairing

- **Nodes pair by id, never by number.** Two nodes pair when they carry the same id, when one is the other's agent copy (`zk-0001` and `zk-0001-ai`), or when they are two versions of one key (`key@3` and today). Lemma 1.2 in one and Lemma 1.3 in the other are one pair when their ids say so.
- **A node with no partner** is a node only one side has.
- **The prose between nodes is not marked**: nothing pairs it.

### 3. Two comparisons: with a base, and without

What loom can say about a pair depends on whether it knows a base — which side the other began from. It shows a direction exactly when it knows one (P3, both ways).

| comparison | base | marks |
|---|---|---|
| an agent copy against its source | each `-ai` node records the version it began from | with a base (§4) |
| a landmark against today, or two landmarks | ordered in time | with a base |
| two versions of one key | ordered by version | with a base |
| two of the author's documents, `main.tex` and `talk.tex` | none | without a base (§5) |

A pair takes the base of its nodes, so a comparison may hold both kinds: `talk.tex` against `aidoc.tex` pairs `zk-0003` with `zk-0003-ai`, whose base is a version of `zk-0003`.

### 4. With a base: a git gutter

![With a base, at rest](../plans/images/0.17/compare-based.png)
![With a base, lower in the documents](../plans/images/0.17/compare-based-lower.png)
![With a base, dark](../plans/images/0.17/compare-based-dark.png)

- **An 18px gutter at the left edge of each pane**, as git and every editor draw a diff. The side holding the base draws `−` in red on each line of the page that differs; the other side draws `+` in green. The direction belongs to the documents, not the panes: whichever pane holds the base shows `−`.
- **The changed words** are washed to match, red on the base side and green on the other.
- **A node only one side has** is marked on every line, `−` or `+`, and tagged: "removed in aidoc.tex" on the base side, "new" on the other. The other pane draws a wedge in its gutter at the place the base says the node stood, red or green by the same rule — a place that is known, not guessed.
- **A move:** a node whose text is the same and whose place in the document differs from its base's is marked `↕` on every line on both sides, tagged "moved in aidoc.tex" and "moved from §2", with a grey wedge where it came from. A move is reported only between an agent copy and its source, whose order the copy began with.
- **Changed on both sides since the base.** A node the author edited after the copy was made, and the agent edited too, is old on neither side: red and green would call the author's own new words "removed". It takes Review's amber and `~` on both sides instead, each side's wash its own change, tagged "changed on both sides since the copy". It is the case adoption treats as a conflict.
- **No rule on the node**: the gutter carries what the rule carried.

### 5. Without a base: presence and order

![Without a base](../plans/images/0.17/compare-unbased.png)
![Without a base, lower](../plans/images/0.17/compare-unbased-lower.png)
![Without a base, dark](../plans/images/0.17/compare-unbased-dark.png)

- **A shared node is always the same text.** Two live documents may not define one id (`duplicate-id`, book 5.3), so a node they share lives in one node file that both `\input`. A comparison without a base therefore has no changed nodes and no word washes, ever.
- **Presence:** a node only one side has takes a dashed rule at its left and "not in talk.tex".
- **Order:** where the shared nodes stand in a different order, a dotted rule and "order differs" on both sides, since without a base loom cannot say which of the two moved. The mark goes on the fewest nodes that explain the difference (the nodes outside a longest common subsequence).
- **Symmetric:** no red, no green, no old and new.

### 6. Annotations are off while comparing

![Annotations turned back on while comparing](../plans/images/0.17/compare-based-annotations-on.png)
![Compare released: the documents and annotations as they were](../plans/images/0.17/compare-released.png)

- **The annotation filter gains `off`**: `this session · all · off`, available at any time, drawing no annotation marks.
- **Pressing compare chooses off; releasing it restores what was chosen before.** The reader may choose again while comparing.
- **Why:** annotation marks own the wash (which box is open) and the hues (red an objection, ochre a suggestion, A4). With them off, the comparison's washes and colours mean one thing each, and in compare mode the differences are what the reader came for (P1).

### 7. The rail while comparing

![Stepped to the second difference](../plans/images/0.17/compare-based-stepped.png)

- The filter at the left; at the right, **"6 differences ‹ ›"** and then **compare**, pressed. Stepping reads "2 of 6" and brings both panes to that pair at the same height, flashing it. Keys `[` and `]`.
- **A difference** is a pair whose texts differ, a node only one side has, or a move. They are counted in the left pane's order, with the right pane's unpaired nodes at the place their wedge stands.
- **No document names on the rail**: the tabs already say what is compared (P2).
- Stepping to a node only one side has brings the other pane to its wedge with a base, and leaves it where it is without one.

### 8. Finding a partner

![A double-click brings the partner to the same height](../plans/images/0.17/compare-based-partner.png)

- **Double-click a node** and its partner comes to the same height in the other pane and flashes, as a SyncTeX jump does; the word selection the double-click makes is cleared. A node with no partner jumps to its wedge with a base, and does nothing without one.
- **Hovering a node lights its partner** while both are in view.
- **The panes never scroll together.** The author ruled synced scrolling out: two documents of different lengths and orders cannot scroll together without one of them jumping.

## Part two: how it was reached

### 9. The principles

The drafts were measured against P1–P6 of plans 0.13.3 and 0.14 (open on the thing itself; say it once, in the place that governs it; claim only what is known; one element, one question; following a connection must not cost the thing followed from; show less rather than more) and the annotation principles A1–A6 of the annotation study (plan 0.15), of which A4 — each visual channel answers one question — decided the most.

### 10. The drafts

Five drafts were drawn first, each the same comparison of `main.tex` against its agent copy, then redrawn in `p1` at the author's request, and a sixth was added:

- **A · Marks only.** Review's rule at the left of a changed node, its changed words in the stale wash, a dashed rule on a node the other lacks.
- **B · Holes.** A, and a one-line placeholder where only the other document has a node.
- **C · Sameness folded.** Nodes that match fold to a single line.
- **D · Stepping from the rail.** A, and a difference counter with ‹ › on the rail.
- **E · A seam.** The divider widened into a strip drawing a band from each node to its partner, as a merge tool does.
- **F · A git gutter.** Red `−` and green `+` down each pane's left edge, the words washed to match, a wedge where the other side has a node this one lacks.

The first round assumed synced scrolling; the author replaced it with a jump to the partner, "something resembling tex syncing".

### 11. The critique

Two findings held for every draft: the rail's "main.tex ↔ aidoc.tex" restated the tabs (P2), and a wash on changed words shared its channel with an open annotation's wash in an amber beside the suggestion's ochre, so a changed phrase and an annotated one looked alike (A4).

| draft | verdict | reason |
|---|---|---|
| A | kept, with annotations off | the page is the page; its one fault was A4's collision |
| B | rejected | a hole stands at a guessed place, refused for detached annotations for the same reason (A3); it draws in the page what is not in the document (P1) |
| C | rejected | the document becomes a summary of itself (P1), and reading a changed lemma costs the lemma it cites (P5) |
| D | counter kept | "where is the next difference?" is asked while comparing, about both panes, so it passes the rail's place test (P4) |
| E | rejected | it answers "which is whose partner?", which hover answers (P4), with the most drawing on screen (P6) |
| F | rejected at first | red is the objection's hue and green the accepted state's (A4), and it claims a direction (P3) |

The first recommendation held word differences back until the reader opened a pair, to keep them off annotation washes. The author proposed an `off` for the annotation filter, chosen by compare; that removed the collision, and the open-pair step was dropped as a mechanism answering A4 by hiding the answer.

### 12. What the recommendation lost, and what came back

Asked what the rejected drafts would have given, the losses were: from F, direction, the line within a node, a deletion seen from the side that lost it, and marks that do not depend on colour; from B, a partner for every node; from C, reading only the differences; from E, order — a node moved but unchanged was marked by no draft but E; from the open-pair step, a current pair.

The author judged F very useful where the direction is known. With annotations off, F's red no longer reads as an objection; and a base places a wedge where a node stood rather than guessing, which is what B lacked. So F's marks were taken wherever a base is known (R1), moves were added to both, and writing the demo for two author documents exposed §5's fact: shared nodes are one node file, so without a base only presence and order can differ (R2). Folding and the seam stay rejected for the reasons above. The author accepted R1 and R2 on 2026-09-26.

## Part three: what it changes

Built by [plan 0.17.4](../plans/0.17.4-ikmartin.md), which carries the file references.

- **loom:** every node element in every fragment gains `data-pair` and `data-hash` (`render/fragments.py`); the manifest gains `compare.pairs`, the highlighted renderings of each pair of differing texts with its direction, and a fragment per recorded version of a key.
- **arras:** the annotation filter's `off` (`sessions/sessions.svelte.ts`, `SessionFilter.svelte`); the rail's counter and compare (`workspace/GlobalRail.svelte`); the comparison itself — pairing, the swapped bodies, the gutter, the rules, stepping, the jump — over the two panes; a node item that shows a recorded version.
- **The book:** chapter 15 gains a section for compare, and every account of the filter gains `off`; decision records for the two kinds of marks and for `off`.
- **Tests:** the rail's placeholder test (`tests/e2e/workspace.e2e.ts`) and the filter's two-value tests (`tests/unit/sessions.spec.ts`, `tests/e2e/panel.e2e.ts`) change; compare gets its own.
