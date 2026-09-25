# Mapping: from the chat rules to the loom files

Each row names a part of `global-rules.md`, where its content lives in the loom project, and what changed. "Kept" means the wording is carried over; "adapted" means the procedure is the same and the environment-specific wording changed; "dropped" means it has no counterpart because the environment that needed it is gone; "new" means loom required something the chat never did. The four environmental differences that drive every adaptation: inputs come from commands, not uploads; outputs are files, not a reply; findings are anchored comments, not paragraphs; the agent can run code and compile.

## Global rules

| chat text | loom destination | change |
|---|---|---|
| "professional mathematician with 30 years ... never bluff ... depth over breadth ... conceptual simplicity ... superficiality is failure" | `ai/modes/blocks.md` §Standing rules, items 1–2 | kept |
| "Differentiate fact vs speculation explicitly" | `blocks.md` §Standing rules, item 3 (epistemic labels `file-verified`, `memory-grade`, `proved-here`) | adapted: the labels name what "fact" is checked against in a quilt |
| "Cite exact source text when using uploaded papers" | `blocks.md` §Standing rules, item 4 (cite by id; quote from the bundle when wording matters) | adapted: sources are keys and digest nodes |
| "Report numerical trials explicitly ..." | `blocks.md` §Standing rules, item 7 (scripts saved as `MODE-TARGET.check.py`, outputs appended) | adapted: trials are files |

## Formatting rules

| chat text | loom destination | change |
|---|---|---|
| 1–6, 8–11 (KaTeX delimiters, subset, tag placement, table escaping, no cross-refs, math in headings) | — | dropped: outputs are LaTeX files and Markdown notes rendered by the viewer; the rules in `blocks.md` §Outputs replace them |
| 7, 12 (pre-send checklist; double-check) | every mode file's final §Checklist, copied into the notes and ticked | adapted |
| "Never use \eqref, \ref, \label" | inverted: `blocks.md` §Outputs requires `\ref{ID}` and `\uses` in LaTeX outputs | inverted: loom's graph is read from references |

## Blocks

| chat block | loom destination | change |
|---|---|---|
| [overview], [proof-basics], [dependencies], [reconstruction-plan] | `blocks.md` §Blocks; used by `ingest.md` as the prose of a digest's overview | kept; the paper's numbered results additionally become external nodes |
| [gaps-and-ambiguities], [worked-examples], [counterexample], [referee-review], [referee-revised], [decision] | `blocks.md`; used by `referee.md` | kept; items in gaps and referee-review are also annotations; referee-revised is a diff |
| [definition], [worked-numerical-examples], [edge-cases], [stress-test], [answer], [follow-up] | `blocks.md`; used by `question.md`, `quick.md` | kept |
| [hypothesis-ledger], [citation-ledger], [self-containedness], [sharpenings], [patch-list] | `blocks.md`; used by `audit.md` | kept; citation-ledger entries name digest node ids; patch-list entries are also suggestion annotations |
| [simplifications], [rejected], [revised], [meaning-drift-check] | `blocks.md`; used by `simplify.md` | kept; revised is a diff |
| — | [uses-ledger] in `blocks.md`; used by `audit.md` | new: dependencies the text does not name, anchored to the invoking sentence |
| — | [notation] in `blocks.md`; used by `ingest.md` | new: replaces the chat's global variable table for cited papers |
| — | [summary] in `blocks.md`; opens every notes file | new: replaces [intuition] for a reader scanning a thread |

## Tagged query rules

| chat text | loom destination | change |
|---|---|---|
| global [variable-defs] table at the start of every tagged answer | [notation] in digests (via `ingest.md`); nowhere else | adapted: the quilt's macros define its notation; each digest carries its paper's |
| [intuition] at the end | [summary] at the start of every notes file | adapted |
| nested tags inner-first with a divider | `blocks.md` §Sequential applications | adapted: each application is its own file; read earlier notes first; no dividers |
| untagged query → judgement | the author names a mode; `orientation.md` §7 lists them | adapted |

## Modes

| chat text | loom destination | change |
|---|---|---|
| "Source may be pasted text, an uploaded file, a path, a prior document" | `blocks.md` §Inputs (bundle, `search`, `status --json`, digest nodes) | adapted |
| "[variable-defs] opens and [intuition] closes every response" | dropped; see above | dropped |
| "[audit] diagnoses, [simplify] executes; simplify may consume a prior patch-list" | `simplify.md` §Input ("if an audit notes file exists in this run, its patch-list is your starting list") | kept |
| Mode 1 ingest (4 blocks, verbal intuition) | `ingest.md`: the four blocks as the digest overview, plus [notation], plus external nodes per Chapter 8 | adapted and extended |
| Mode 2 referee (6 blocks, hostile persona) | `referee.md` | kept; findings are annotations; revised is a diff; decision stays in notes and never touches the ledger |
| Mode 3 question (5 blocks) | `question.md` | kept |
| Mode 4 quick (2 blocks) | `quick.md` | kept |
| Mode 5 audit (5 ledgers; search project files and web) | `audit.md`: six ledgers (uses-ledger added); search digests, then `refs/pdf/`, then web, saying which | adapted and extended |
| Mode 6 simplify (4 blocks; compiled artifacts) | `simplify.md`: revised is `proposal-KEY.diff`; "compiled artifacts" becomes `loom bundle KEY --with proposal-KEY.diff` then `loom compile` | adapted |
| — | `draft.md` | new: the author supplies the strategy; the agent completes the local argument |

## Things loom needed that the chat never did

| loom text | where | why |
|---|---|---|
| write policy in the first lines of every mode file | every mode file §Before you begin | an agent may load a mode without the orientation |
| `--run $LOOM_RUN` on every command | `blocks.md` §Inputs, §Findings | the run log and the record files |
| findings as `loom annotate` calls with `--quote` | `blocks.md` §Findings | margins in the viewer; nothing else makes a finding visible |
| resolving one's own annotations after a re-check | `referee.md`, `audit.md` §On a re-check | the review facts depend on it |
| never `loom accept`, never write outside the run | `blocks.md` §Never | P7 and the ledger's human-only rule |
| requesting a dependency's proof is a signal | `blocks.md` §Inputs, item 3 | atomicity: a needed proof is a missing statement |
