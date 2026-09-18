# WQ-32 · Rewrite every mode against loom's CLI, and let the gaps name the missing commands

**Repo:** loom

## Trigger

[0.10](../plans/0.10-annotations-and-review.md) has landed. The annotation log is what a mode's findings become, so the output contract every mode is written against changes in that plan; rewriting the modes first means rewriting them twice.

## Why deferred

Not for lack of value — this is the highest-value item in the queue that nothing forces. The modes came from `docs/source/global-rules.md`, a chat system prompt, and `global-rules-mapping.md` records the translation honestly: inputs became commands, outputs became files, findings became anchored comments. But the translation was a *port*, done once, and it stopped at making each mode work. No mode was written by someone asking "what can loom do that a chat cannot, and what would this mode be if it started from that?"

## Rough design

Two passes, and the second is the point.

**The forward pass: rewrite each mode to use the CLI deliberately.** Today's modes name a handful of commands — `referee.md` names `loom comment`, `loom bundle --with`, `loom compile`; `audit.md` names the digests and `refs/`. What none of them do is treat the quilt as a thing that can be *interrogated*. `loom deps KEY` and `loom unravel KEY` give an audit its hypothesis ledger's skeleton for free. `loom search --json` finds every statement of a shape. `loom status --json` says what is stale and what is unreached. `loom graph` gives a mode the dependency structure it currently reconstructs by reading. A mode that opens with the right three queries starts where a chat session ends.

**The reverse pass: let the friction name the missing commands.** This is the deliverable that outlasts the rewrite. Each time a mode wants something the CLI cannot answer, write it down rather than working around it. The candidates already visible from the modes as they stand:

- an audit wants "every key whose proof cites this hypothesis" — `unravel` is the closest and is not it;
- a referee re-check wants "what changed in this key since the annotation was written", which the workbench's versions can now answer and no command exposes;
- review mode wants a document's results in order with their states, which is `status --json` plus `linearize` plus assembly by hand;
- every mode wants "the text I am reviewing, at the version I am reviewing it at", and `bundle` gives the current one.

The output is a list of proposed commands with the mode that wanted each, which is a far better basis for growing the CLI than guessing. Some will be flags on commands that exist; a few will be new; some will turn out to be things the agent should compose itself, and saying so is also an answer.

**What 0.10 already does to them.** `loom bundle` is deleted there, so every mode's Input line changes to `loom source KEY --closure` and the verification lines to `loom compile --with`. That is the minimum edit, made because the command went away. This item is the pass nobody is forced to make.

**What this is not.** Not a rewrite of the *procedures* — the blocks, the personas and the checklists are the author's and are carried over. Only the inputs, the queries and the output plumbing change.

## Blast radius

`loom/src/loom/assets/ai/modes/*.md` (all of them) and the demo copies; `ai/orientation.md` §7 where each mode is summarised; `docs/book/C-mode-templates.md`, which reproduces every mode verbatim; Chapter 11's mode table; `docs/source/global-rules-mapping.md`, whose rows record what each mode became; and `loom/src/loom/cli/` for whatever the reverse pass justifies.

## Related

[[WQ-23]] for the review workflow the modes serve; [[WQ-24]], since an agent with its own quilt would query differently again; `docs/source/global-rules-mapping.md`, which is the record of the first translation and should gain a column or a successor for the second.
