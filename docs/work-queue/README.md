# Work queue

What is not being done now, and what would make each of it worth doing. **Start here**: this is the one place that says what remains.

**This is not an ordered queue.** Items come out when their trigger fires, not in sequence. Reading it top to bottom tells you what exists, not what to do next; reading the triggers tells you whether anything is ready.

## How it works

- Every item has an **observable trigger** — a condition you can check in thirty seconds. A measurement crossing a threshold, a capability existing, a dependency landing. "Someday" is not a trigger, and an item that cannot get one belongs in a plan or nowhere.
- An item's **"why deferred" is its trigger inverted**: deferred *because* X is missing, trigger *is* X existing. If they do not invert cleanly the item is vague.
- Ids are `WQ-NN` and are **never reused**, so a reference from a chapter or a decision record stays resolvable after the item closes.
- **The cap is 45 active items.** A forty-sixth means promoting, merging or dropping one. Free addition is what kills a list like this; the cap was raised from 20 on 2026-09-17, when the workbench design arrived with a queue's worth of deferred work behind it.
- An item **graduates** to `docs/plans/` when the author commits to building it — not at any size threshold.
- An item **closes** by deleting its file and its row and adding one line to [closed.md](closed.md): a pointer to the plan or record that carries it, or one sentence on why it was dropped.
- `python docs/work-queue/check.py` enforces the mechanical parts, and also that the frozen book and the specs carry no unfinished-business markers. A design question is not a queue item: it belongs in `docs/design/`, beside what it affects, under **Open.**

Several triggers below are numbers loom already prints. That is the property to aim for: you find out a port is ready to open by running `loom doctor`, not by remembering to read this file.

## Active

| id | item | repo | trigger |
|---|---|---|---|
| [WQ-03](WQ-03-reference-libraries.md) | reference libraries: one quilt depends on another | loom | a second quilt exists whose digests another quilt wants |
| [WQ-08](WQ-08-nest-sectioning-classes.md) | `\nest` under `\part` and class-specific sectioning | loom | a fixture uses memoir, KOMA-Script or `\part` |
| [WQ-10](WQ-10-locator-normalization.md) | locator normalization beyond English | loom | a digest whose locators do not match its citations |
| [WQ-13](WQ-13-graph-at-scale.md) | graph layout precomputed by the publisher | loom, arras | a quilt's graph exceeds roughly 2000 nodes, or the force layout takes over a second |
| [WQ-16](WQ-16-overleaf.md) | the Overleaf procedure | — | cutting the first tagged release |
| [WQ-17](WQ-17-external-user.md) | acceptance criterion 10: an external user | — | someone outside the project has a paper to bring in |
| [WQ-19](WQ-19-publishing.md) | publishing to PyPI and npm | loom, arras | the author decides to release |
| [WQ-22](WQ-22-extraction-node-model.md) | digest extraction shares the node model | loom | extraction and atomize disagree about what a node is |
| [WQ-25](WQ-25-history-view.md) | the history view in arras: landmarks, stamps, versions per node, the graph at a step | arras, loom | a quilt's ledger holds three or more landmarks |
| [WQ-27](WQ-27-applying-suggestions.md) | applying a suggestion: patches and `compile --with` | loom, arras | one run leaves ten or more payloads (**fired**: relloc, 2026-10-12, see the item) |
| [WQ-28](WQ-28-annotated-export.md) | an annotated view exported as LaTeX and PDF | loom, arras | a review has to reach someone who cannot run arras |
| [WQ-29](WQ-29-node-manager.md) | the node manager: fork from history, retire, merge, rename | loom, arras | ten or more forks, or a fork or rename by hand goes wrong once |
| [WQ-30](WQ-30-history-gc.md) | `loom history gc` | loom | `.loom/history/texts/` exceeds a few thousand files or fifty megabytes |
| [WQ-36](WQ-36-annotation-bodies-beside-the-manifest.md) | annotation bodies beside the manifest rather than inside it | loom, arras | a manifest crosses a few megabytes because of annotation prose |
| [WQ-38](WQ-38-digest-blocks-in-their-own-preamble.md) | a digest block rendered against the paper's own preamble | loom | a digest block the author needs shows a raw-TeX error box |
| [WQ-39](WQ-39-mechanical-version-check.md) | a mechanical version check for extracted digests | loom | the author cites, with a locator, a result in a flagged digest that the cited version numbers differently |
| [WQ-42](WQ-42-the-gradient-with-orientation-held.md) | measure the gradient with orientation held fixed | — | before the layer is claimed to make later questions cheaper outside the project |
| [WQ-50](WQ-50-publish-after-mv-test.md) | a committed test that a publish after `loom mv` keeps Overleaf's file name | loom | the next change to sync's mapping of Overleaf's main, or to `loom mv` |
| [WQ-51](WQ-51-macro-sets-leak.md) | a view's macros stay its own: no page-wide `\renewcommand` leaking between documents | arras | a real quilt has two macro sets defining one name differently |
| [WQ-52](WQ-52-simultaneous-agent-copies.md) | agent documents of overlapping scopes | loom, arras | a person wants two agent versions of one section side by side and `loom draft --ai` refuses the second as overlapping |
| [WQ-54](WQ-54-annotations-follow-adopted-text.md) | open annotations follow the text a person adopts | loom, arras | an adoption leaves an open annotation on the copy, and the person files it again on the adopted node |
| [WQ-56](WQ-56-figures-cold-build.md) | a cold build's figures: a preamble format, and the cited papers' blocks that fail | loom | `scripts/bench` shows a cold build over three minutes once cold builds are common, or a cited paper's figure shows as source with an error |
| [WQ-58](WQ-58-lazy-digests.md) | lazy digests: the extraction as an index, a result a node only when used | loom, arras | after a persistent token cache and a linear `unmatched_cites`, lint or status still spends over about 1 s on digest nodes no document reaches |
| [WQ-59](WQ-59-regrade-partials.md) | the re-grade's partials: every finding graded p | loom | the next round of work on the command line, or a finding tripped over in use |
| [WQ-60](WQ-60-annotation-anchors.md) | annotation anchors: a mark placed from the source span, re-anchoring, where a mark landed, a replacement longer than its anchor | loom, arras | an annotation drawn at block level that its writer meant for a phrase, or a finding discarded and filed again only to move its quote |
| [WQ-61](WQ-61-read-view-content-visibility.md) | the read view's blocks skipped while off screen, once the reader's place holds | arras | a way to keep the place when a skipped block above the reader changes, shown on relloc within 4 px |

Twenty-seven active, eighteen slots of headroom.

Every item above has an observable trigger, which is the rule. The rule does not catch a second failure: **a trigger that is observable and will never be observed is a polite way of saying no.** Such an item looks like a plan and is actually a decline, which is worse than an empty queue because it suggests work is coming. So each review asks two questions, not one — is the trigger checkable, and will it ever fire? Five items failed the second on 2026-09-16 and were closed for it; their reasons are in [closed.md](closed.md), and their ids are retired rather than reused.
