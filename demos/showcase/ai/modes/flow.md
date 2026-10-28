# Mode: flow

When it fits: reading order and clarity for a named reader, with the same mathematics ("edit for clarity and flow", "write it so it is clear to me").

## What it is for

Revise a passage for the order it is read in and the clarity of each sentence, for the reader the author names — "someone who knows the paper's earlier sections", "me". With nobody named, the reader is the author.

**The mathematics does not change.** No hypothesis is added, dropped or weakened; no argument is replaced by a citation; no statement changes (those are simplify and referee). An error that surfaces is flagged at the top and its passage left untouched. Every original sentence is kept or its removal recorded, and the exact words an open annotation quotes stay as they are, so it stays anchored.

**Structure before sentences.** When the passage's organization is in question, settle [structure-map] and the structural changes first, then polish sentences once, in their final place. `loom status --master DOC --in-order` lists a document's results in order; `loom downstream ID` gives each one's consumers.

The changes, by type — name a new one in the same style and define it in one clause:

- **hypothesis-placement**: a hypothesis moved to its first consumer; standing assumptions stated once in prose, never in a theorem environment; a numbered remark holds only the consequences later proofs cite.
- **essence-first**: a proof reopened with the two to four sentences an expert would give as the reason it is true, then the checks under italic headings, every original sentence kept under one.
- **lead-in**: one or two sentences opening a block, saying what it establishes and why the next block needs it.
- **forward-reference**: a citation of a later result removed, by reordering or by citing the external source directly.
- **one-symbol-one-meaning**: overloaded notation split; a reference's own symbol used only where its object is imported.
- **dissolve**: a numbered result with a single consumer absorbed into that consumer's proof, as a labelled claim if it has its own argument; a result with several consumers stays numbered.
- **condensation**: wording tightened, old → new where meaning could shift.

**For a large pass, or when asked, a [rubric]**: criteria for this text, each with a good and a bad example taken from it, and the text graded before and after. Criteria that have served: answer first; the reader's own sequence; each step's output first; compute, justify and check kept apart; special cases said once; one name per object; a running example; status visible in one place; a sentence budget; no unflagged forward reference.

**At the end, a fresh reader**: one given only what the named reader knows reads the result and lists what still fails, and you act on it. A second agent, where your app can start one; otherwise your own reading, setting aside everything that reader would not know.

## Report

Core: [structure-map], [flow-edits], [rejected], [meaning-drift-check]. Optional: [rubric], [fresh-reader].

## Where changes go

On the author's text, the sentence-level types are suggestions, and the structural ones — dissolve, a reordering, a hypothesis moved between results — are an agent document of the passage.
