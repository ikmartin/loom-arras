# WQ-57 · Agent documents written from scratch

**Repo:** loom, arras

## Trigger

A person asks an agent for a document of its own — a survey, a companion note, a new section to be placed later — that is drafted from none of their documents, and the agent has to fake it: a `loom draft --ai` of an unrelated document emptied out, or a `.tex` file in its session's directory that the viewer does not show as a document.

## Why deferred

The vocabulary already names such a document: every document in `drafting-ai/` is an **agent document**, drafted or not (book 3, DR-330-ikmartin). But loom refuses one no `copy` step made: `loom lint` reports it as `loom:agent-document-not-a-copy` (error), `loom adopt` and `loom ai refresh` refuse it for having no source and no bases (`adopt.py` `_resolve`), and the orientation tells an agent never to write a document there by hand. Every agent document so far has been a copy, so nobody has needed the other kind.

## Rough design

- **Making one.** A command beside `loom draft DOC --ai NAME`, e.g. `loom draft --ai NAME --new`, writes a skeleton with the default document's preamble and records a step with no `from`, so the history still knows every agent document's origin. Writing the file by hand stays refused, since an unrecorded document is what the lint guards against.
- **Its ids.** Every node it defines is new, so each is derived with no counterpart: `loom id --next` plus `-ai`, as a node an agent adds to a copy is today. `derived_of` names a plain key no person's document defines.
- **Adopting it.** There is no working document to incorporate into, so adoption becomes "start a working document from it": like `loom history restore`, it writes a new document directly in `drafting/` with every derived id made plain, through `destination(drafting=True)`. Whether that is `loom adopt` with `--to FILE` or a separate verb needs deciding, as does whether a from-scratch document can instead be adopted *into* an existing working document at a place the person names.
- **What does not apply.** `loom ai refresh` and staleness (`loom ai drafts`' "what moved") need a source, so they skip such a document and say why.
- **The viewer.** It lists under the agent's drafting directory with the rest; compare has no base for it, so it compares as two of the person's documents do (presence and order only).

## Blast radius

`scan/lint.py` (`loom:agent-document-not-a-copy` becomes a document no step made), `history/ledger.py` (`copy_of` and a `copy` line without `from`), `reshape/copy.py`, `cli/history_cmds.py` (`draft`), `adopt.py`, `drafts.py`, the orientation and `ai/modes/draft.md`, arras's Incoming, chapters 4.4, 5.3.1, 11.8 and 17.7, `specs/diagnostics.md`.

## Related

[WQ-52](WQ-52-simultaneous-agent-copies.md), several agent documents drafted from one document; [plan 0.18.4](../plans/0.18.4-surface.md), which named the agent document and left this open.
