# Diagnostics

A diagnostic is a structured report of something wrong or notable in a corpus. Publishers emit them into the manifest; viewers render them on a problems page, as badges on the keys they concern, and in header counts. Interface version 1.

## 1. Schema

**[decided]**

| field | type | meaning |
|---|---|---|
| `severity` | `error`, `warning`, `info` | how serious |
| `code` | string | stable identifier; reserved (no namespace) or publisher-namespaced (`loom:...`) |
| `message` | string | human-readable, one sentence |
| `locations` | list of `{file, line, column?}` | where, zero or more |
| `keys` | list of keys or node ids | what it concerns, zero or more |
| `subject` | `source`, `record` | optional; what the diagnostic is about. Absent means `source`. |
| `fixes` | list of `{label, command}` | optional; commands that would resolve it |

Viewers group by code, filter by severity, code and subject, and link locations and keys. A viewer renders unknown codes generically and never fails on one.

**[decided]** `subject` separates what is wrong with the corpus's text from what is wrong with the publisher's own record of it. They are different kinds of work, and a viewer may group them apart; a viewer that ignores the field loses nothing.

**[decided]** `fixes` are data, never actions. A viewer shows each command and may offer to copy it; nothing in a viewer runs one. The label says what the command would achieve, so that a reader choosing between two fixes is choosing between outcomes.

## 2. Reserved codes

**[decided]** These describe any inclusion tree and link graph over nodes. Any publisher may emit them; a viewer may give each a specific affordance. They cannot be disabled by a publisher's lint configuration.

| code | severity | meaning | viewer affordance |
|---|---|---|---|
| `duplicate-id` | error | the same identifier is defined by two nodes | link both locations; show the id as conflicted wherever it appears |
| `dangling-link` | error | a link to no node or region | mark the source |
| `missing-include` | error | an inclusion names a file that does not exist | link the site |
| `double-inclusion` | error | one node under two parents in one root | link both paths |
| `inclusion-cycle` | error | a node includes itself through a chain | list the cycle |
| `unreachable` | info | a node or file no root reaches (loom: loose) | filter |

**[decided]** A publisher may leave a doubly-defined identifier with no text and the state `conflicted` (manifest §3, §8) rather than choosing between the definitions. A viewer renders that state like any other the manifest declares.

## 3. Loom codes

**[decided]** Namespaced `loom:`. Severity in parentheses. All except those marked fixed can be silenced with `[lint] disable`.

Source and structure:

- `loom:environment-spans-files` (error): a theorem-like environment opens in one file and closes in another.
- `loom:line-anchoring` (error, fixed): a `\begin` or `\end` of a theorem-like environment is not alone on its line; reported by `draft` and `atomize`.
- `loom:unknown-environment` (error): a theorem-like environment the preamble closure does not declare; fix with `% !LOOM environment:`.
- `loom:unattached-proof` (error): a `proof` neither adjacent to a node nor referencing one.
- `loom:multi-target-proof` (warning): a proof's optional argument references several nodes; attached to the first.
- `loom:reference-to-loose` (error in masters, info in loose files): a reference to a node the master does not reach; never for a target in a digest file, which is loose by construction (DR-76).
- `loom:duplicate-label` (error): a non-id label defined twice anywhere in the quilt.
- `loom:macros-unloaded` (error): `\uses`, `\incomplete`, or `\nest` used in a master that does not load `loom.sty`.
- `loom:macro-shadowed` (warning): the preamble defines one of the three names before `loom.sty`.
- `loom:taxon-conflict` (warning): two masters declare different taxa for one environment.
- `loom:prefix-is-citekey` (warning): the quilt's id prefix equals a bibliography key.
- `loom:unknown-directive` (warning): a `% !LOOM` key not in the inventory.
- `loom:documentclass-outside-drafts` (info): a file with `\documentclass` outside the masters directory.
- `loom:unlabelled-node` (info): a theorem-like environment without an id.
- `loom:positional-proof-key` (info): a node with more than one unlabelled proof.
- `loom:unexpected-proof` (info): a proof attached to a definition- or remark-style node.
- `loom:missing-proof` (warning): a plain-style node with no proof, no `\incomplete`, and no citation in its title.
- `loom:equation-in-proof-referenced` (warning): another node references an equation inside this node's proof.
- `loom:uses-missing` (info): a `\ref` in a proof not listed in `\uses`.
- `loom:uses-unused` (info): a `\uses` entry the proof's text never mentions.
- `loom:see-redundant` (info): a `% !LOOM see:` item that names the node it is written in, or that repeats a relation already declared on that node.
- `loom:dependency-cycle` (warning): statement dependencies form a cycle; breaks settledness.
- `loom:converter-fallback` (info): a block rendered by SVG fallback, naming the construct; warning when the fallback itself failed, naming the node and each attempt's first error (DR-79).
- `loom:bundle-failed` (error): a bundle did not compile; first LaTeX error attached; `loom check` prints it under this code and `loom compile` names `loom:missing-package` first when a digest in the closure requires a package the preamble lacks (8.11).
- `loom:atomize-target-exists` (error, fixed): atomize would overwrite a file.
- `loom:import-outside-tree` (warning): import found a file outside the paper directory and did not copy it.
- `loom:non-utf8-source` (warning): a scanned file was not UTF-8 and was decoded as Mac Roman or Latin-1 (DR-47).
- `loom:unknown-theoremstyle` (warning): a `\theoremstyle` other than plain, definition, or remark; treated as plain (DR-46).
- `loom:taxon-name-macro` (info): a `\newtheorem` display name is a macro the closure does not define; the environment name is used (DR-46).
- `loom:citekey-slug-collision` (error): two citekeys share a digest prefix after slugging (DR-45).
- `loom:main-not-found` (warning): `[quilt] main` names a file that is not a master; the first master is used.
- `loom:unknown-config-key` (warning): `config.toml` has a table or key outside the inventory of 4.2; it is ignored (M7).

Review:

- `loom:retired-ledger-key` (info): a ledger row whose key no longer exists.
- `loom:detached-annotation` (info): annotations whose selectors no longer match, with a count per key.
- `loom:previous-key-match` (info): an acceptance row matches the text of a differently keyed proof.
- `loom:foreign-annotations` (warning): a line of `annotations/log.jsonl` that is not a review event; it is skipped and the rest of the log still loads (book 7.4.1).
- `loom:agent-wrote-outside-run` (error): reported by `loom ai check`: a file outside the run, `comments/`, and `build/` changed after the run started (book 11.8).

References and digests:

- `loom:unmatched-postnote` (warning): a `\cite[postnote]` that matched no digest node, when a digest for the citekey exists; a digest node's own locator title is exempt (DR-66).
- `loom:undigested-citekey` (info): a cited key with no digest; the ingest trigger.
- `loom:unresolved-work` (info): a cited work whose bibliography entry states no identifier (`doi`, `eprint`, `mrnumber`, `zbl`, or a URL carrying one). It can still be digested and still enters the graph; what it cannot do is deduplicate against another corpus's copy or be fetched (DR-109).
- `loom:unverified-locators` (warning): a digest extracted from a preprint while the bibliography cites a published version, or one that does not say what it was extracted from. Its result numbers and page references are unverified against the document a reader will open (DR-109).
- `loom:version-mismatch` (warning): a digest's source version differs from the bibliography's.
- `loom:missing-package` (warning): a digest requires a package the preamble closure does not load.
- `loom:digest-without-bib` (warning): a digest whose citekey is not in the bibliography.

Interface:

- `loom:interface-version` (error, fixed): emitted by the viewer, not loom, when the manifest's version is not accepted; listed here so the code is reserved.

### The workbench and the record

**[decided]** These concern loom's own record of the quilt (Chapter 17) and carry `subject: "record"` except where noted.

- `loom:superseded-file` (info): a document a conversion replaced; it defines nothing until `loom live`.
- `loom:canon-edited` (warning): a canon document is not the text the step that wrote it recorded.
- `loom:history-missing` (error): a step directory or one of its files is gone.
- `loom:history-edited` (error): a version file, a preamble, or a step's document copy does not hash to what the ledger recorded.
- `loom:history-corrupt` (error): a ledger line cannot be read, or a step number does not follow the last.
- `loom:dangling-ancestry` (warning): a `fork`, `revert`, or `draft` line names a step or version the history no longer resolves.
- `loom:id-reused` (error, subject `source`): an id the history retired is defined again with a text the history never recorded.
- `loom:node-recovered` (info, subject `source`): an id the history retired is defined again with a text it did record.
- `loom:no-live-document` (info, subject `source`): the drafting directory holds no document, so the quilt defines no nodes; carries the fix that starts one.
- `loom:deprecated-config-key` (warning, subject `source`): a configuration key loom still reads under an older name.

## 4. Adding a code

**[decided]** A new loom code is added here with a severity and a one-line meaning before it is emitted. A new reserved code requires an interface version discussion, since every viewer may give it an affordance.
