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

Viewers group by code, filter by severity and code, and link locations and keys. A viewer renders unknown codes generically and never fails on one.

## 2. Reserved codes

**[decided]** These describe any inclusion tree and link graph over nodes. Any publisher may emit them; a viewer may give each a specific affordance. They cannot be disabled by a publisher's lint configuration.

| code | severity | meaning | viewer affordance |
|---|---|---|---|
| `duplicate-id` | error | the same identifier is defined by two nodes | link both locations |
| `dangling-link` | error | a link to no node or region | mark the source |
| `missing-include` | error | an inclusion names a file that does not exist | link the site |
| `double-inclusion` | error | one node under two parents in one root | link both paths |
| `inclusion-cycle` | error | a node includes itself through a chain | list the cycle |
| `unreachable` | info | a node or file no root reaches (loom: loose) | filter |

## 3. Loom codes

**[decided]** Namespaced `loom:`. Severity in parentheses. All except those marked fixed can be silenced with `[lint] disable`.

Source and structure:

- `loom:environment-spans-files` (error): a theorem-like environment opens in one file and closes in another.
- `loom:line-anchoring` (error, fixed): a `\begin` or `\end` of a theorem-like environment is not alone on its line; reported by import and atomize.
- `loom:unknown-environment` (error): a theorem-like environment the preamble closure does not declare; fix with `% !LOOM environment:`.
- `loom:unattached-proof` (error): a `proof` neither adjacent to a node nor referencing one.
- `loom:multi-target-proof` (warning): a proof's optional argument references several nodes; attached to the first.
- `loom:reference-to-loose` (error in masters, info in loose files): a reference to a node the master does not reach.
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
- `loom:dependency-cycle` (warning): statement dependencies form a cycle; breaks settledness.
- `loom:converter-fallback` (info): a block rendered by SVG fallback, naming the construct.
- `loom:bundle-failed` (error): a bundle did not compile; first LaTeX error attached.
- `loom:atomize-target-exists` (error, fixed): atomize would overwrite a file.
- `loom:import-outside-tree` (warning): import found a file outside the paper directory and did not copy it.

Review:

- `loom:retired-ledger-key` (info): a ledger row whose key no longer exists.
- `loom:detached-annotation` (info): annotations whose selectors no longer match, with a count per key.
- `loom:previous-key-match` (info): an acceptance row matches the text of a differently keyed proof.

References and digests:

- `loom:unmatched-postnote` (warning): a `\cite[postnote]` that matched no digest node.
- `loom:undigested-citekey` (info): a cited key with no digest; the ingest trigger.
- `loom:version-mismatch` (warning): a digest's source version differs from the bibliography's.
- `loom:missing-package` (warning): a digest requires a package the preamble closure does not load.
- `loom:digest-without-bib` (warning): a digest whose citekey is not in the bibliography.

Interface:

- `loom:interface-version` (error, fixed): emitted by the viewer, not loom, when the manifest's version is not accepted; listed here so the code is reserved.

## 4. Adding a code

**[decided]** A new loom code is added here with a severity and a one-line meaning before it is emitted. A new reserved code requires an interface version discussion, since every viewer may give it an affordance.
