# 12. CLI reference

Every loom command, with syntax, flags, behaviour, exit codes, and machine output. Behaviour is specified in the earlier chapters; this chapter is the index and the fixed surface. The implementation generates the `--help` text and the user-facing reference from the same definitions, so that this chapter, the help, and the code cannot drift apart without a test failing.

## 12.1 Conventions

**[decided]**

- Quilt discovery: every command except `init` and `doctor` walks up from the current directory to the nearest `config.toml` with a `[quilt]` table and runs against that quilt. `--quilt PATH` overrides.
- Exit codes: `0` success; `1` a content problem (lint errors, a failed identity test, a failed compile, a refused write that the author can fix in the source); `2` a usage or environment problem (bad arguments, missing tools, no author name, refused destination).
- `--json`: machine output on stdout, one JSON document, nothing else on stdout; diagnostics and progress go to stderr.
- `--yes`: skip confirmations that would otherwise be asked on a terminal. Commands that would ask and have no terminal and no `--yes` exit 2.
- `--run DIR`: on `bundle`, `comment`, `search`, `status`, `deps`, `unravel`, `check`: append the invocation to `DIR/run.log`; on `bundle`, also copy the output into `DIR`; on `comment`, make the run the author and write to `DIR/annotations.json`.
- `--author NAME`: on `accept` and `comment`, the author name, overriding the user config.
- `--quiet` / `-q` and `--verbose` / `-v`: less or more on stderr.
- Keys are written as ids (`rl-0004`), proof keys (`rl-0004/proof`, `rl-0004/proof/2`), qualified keys (`rl-0004#eq:main`, `drafts/main.tex#section:3`), or master paths. Aliases are accepted wherever an id is and resolved.
- Ids in output are always shown with their number in the default master when known: `rl-0004 (Lemma 3.4)`.

## 12.2 Quilt

### `loom init [DIR] [--from FILE] [--demo] [--prefix P] [--no-git] [--yes]`

Create a quilt (4.7). `--from FILE` imports a paper (6.1). `--demo` writes the demo quilt. Refuses inside an existing quilt or in a nonempty directory that does not contain `FILE`. Exit 2 on refusal, 1 if the imported paper's identity test fails (the quilt is left in place).

### `loom doctor`

Report: Python version; `latexmk`, the configured engine, `bibtex`/`biber`, `dvisvgm`, `pdftotext`, `git`, and their versions; the arras bundle's location and version; the resolved author name and its source; the interface version loom produces. Exit 2 if a required tool is missing.

### `loom upgrade`

Refresh `loom.sty`, `ai/orientation.md`, the generated vendor files, permission settings, and the demo's `README.md` to the installed loom's versions; migrate `config.toml` and the ledger schema if needed, showing the diff first. Never touches author files.

## 12.3 Nodes and files

### `loom new TAXON ["TITLE"] [--prefix P] [--print]`

Allocate an id (5.3.2) and write `nodes/<id>.tex` with the skeleton (author, created, tags directives; the environment with the title and `\label{<id>}`; a `proof` environment for plain-style taxa). `TAXON` is an environment name or display name declared by the default master's preamble closure. `--print` prints the skeleton to stdout and allocates nothing. Exit 2 for an unknown taxon.

### `loom id FILE [--to DEST] [--sections | --no-sections] [--all-levels] [--prefix P]`

Print a patch (unified diff) inserting `\label{<id>}` into every untagged theorem-like environment and sectioning command in `FILE`, or write the patched copy to `DEST`. Never modifies `FILE`. Exit 1 on line-anchoring violations, listing lines.

### `loom import FILE [--yes]`

Copy a paper into the quilt with ids inserted (6.2). Shows the diff and asks. Exit 1 if the original does not compile or the identity test fails.

### `loom atomize SRC DEST | SRC --to DEST [--proofs attached|separate] [--sections] [--all --to-dir DIR]`

Move each node of `SRC` to `nodes/`, writing the spine to `DEST` (6.4). Without a destination: exit 2 with `ERROR: specify a destination file after the source, or with --to`. Exit 1 on refusal (line anchoring, missing ids, target exists) or identity failure.

### `loom inline SRC DEST | SRC --to DEST [--all]`

Reverse of atomize (6.5). Same exit rules.

### `loom search QUERY [--json]`

Match `QUERY` against ids, aliases, titles, taxa, tags, and citekeys; print matches ranked (exact id or alias first, then title prefix, then substring). `--json` returns `[{key, kind, taxon, title, aliases, tags, file, number, url}]` where `url` is the arras route. Used by editors for completion and by other tools to resolve an id to a file.

### `loom delete` (aliases `rm`, `remove`)

Print `loom will not delete your notes; do this yourself with rm. Run loom unravel <ID> to see the consequences first.` Exit 1. Accepts and ignores any arguments.

## 12.4 Graph

### `loom deps KEY [--closure] [--json]`

What `KEY` depends on: direct statement-edges and proof-edges, grouped; `--closure` the transitive statement closure in dependency order. `--json`: `{key, statement: [...], proof: [...], closure: [...]}` with each entry `{key, via, kind}`.

### `loom unravel ID [--json]` (aliases `downstream`, `reach`, `pop`)

Everything downstream of `ID`: transitive dependents (with the edge kind that reaches each), every reference site (file, line), every inclusion site, ledger rows for the id and its proofs, annotations targeting them. The pre-deletion report; changes nothing. `pop`'s help text says it reports and changes nothing.

## 12.5 Build and check

### `loom build [--keys KEY...]`

Scan, derive, render, publish (9.1). Exit 1 if any error-severity diagnostic exists (the build is still published, with the diagnostics in the manifest).

### `loom bundle KEY [--to FILE] [--run DIR] [--with FILE]` and `loom bundle --draft FILE [--run DIR]`

Write `build/bundles/<key>.tex` (9.7) or `FILE`; with `--run`, also copy to the run directory as `bundle-<key>.tex`. `--with FILE` substitutes `FILE` for the key's own text before building: a unified diff is applied to a copy of the node's file, or a `.tex` file replaces it; the quilt is not touched. `--draft FILE` builds a bundle for a node that is not yet in the quilt: `FILE` is a complete node file, its `\ref`s and `\uses` determine the closure, and the bundle is written as `build/bundles/draft-<stem>.tex`. Both exist so that proposals and drafts can be compiled before promotion. Exit 1 if `KEY` does not exist, the diff does not apply, or a draft's dependency is unknown.

### `loom compile [MASTER | KEY] [--engine E]`

`latexmk` from the root into `build/<stem>/` for a master (default: the default master), or for a bundle by key (writing the bundle first if absent). Exit 1 on LaTeX errors, with the first error printed.

### `loom assemble MASTER DEST`

Write `DEST`, a single flat `.tex` with every `\input`, `\nest` (levels shifted), and `\include` expanded, for arXiv or `latexdiff`. Refuses without `DEST`.

### `loom lint [--json]`

Scan and print every diagnostic (5.14, `specs/diagnostics.md`), grouped by severity. Exit 1 if any error, else 0. Fast; no LaTeX runs.

### `loom check [--no-compile] [--bundles all|stale|none]`

`lint`; then `compile` every master; then compile bundles (default: every key whose acceptance is stale or that changed since the last check, **[assumed]**). Exit 1 on any failure. The CI command.

### `loom status [FILTERS] [--explain KEY] [--json] [--run DIR]`

The state table (7.7). Filters: `--stale`, `--draft`, `--incomplete`, `--loose`, `--unmatched-cites`, `--undigested`, `--retired`, `--runs`, `--master PATH`, `--tag TAG`. `--explain KEY` prints causes with diffs. `--json` returns `{summary: {...}, keys: {...}, runs: [...], undigested: [...]}` using the manifest's `keys` shape. Always exits 0.

### `loom serve [--port N] [--open] [--no-compile]`

Watch, republish, serve arras and `build/` (9.8). Runs until interrupted. Exit 2 if the port is busy or the arras bundle is not installed.

## 12.6 Review

### `loom accept KEY... [--proofs] [--stale] [--author NAME] [--force] [--yes]`

Write acceptance rows and snapshots (7.3). Exit 2 without an author name or for an unknown key; exit 1 for an incomplete key or a master that does not compile (`--force` overrides the latter).

### `loom comment TARGET ["MESSAGE"] [--quote TEXT] [--kind objection|suggestion|question|ok] [--run DIR | --author NAME] [--reply ID] [--resolve ID] [--batch]`

Write an annotation (7.4.3). Exit 1 if the quote is missing or ambiguous, or the target does not exist; exit 2 without an author.

`--batch` reads JSON lines from stdin: `{"target": ..., "message": ..., "quote": ..., "kind": ..., "reply": ..., "resolve": ...}`; prints one line per annotation written; stops at the first failure with its line number.

## 12.7 Digests

### `loom digest extract CITEKEY SRC.tex [--to FILE]`

Mechanical digest from LaTeX source (8.5). Exit 1 if `refs/<citekey>.tex` exists without `--to`, or if the source cannot be read.

### `loom digest fetch CITEKEY [--pdf]`

Fetch the e-print source (and PDF) by the bib entry's arXiv identifier (8.9). Exit 2 unless `[refs] fetch = true`.

### `loom digest import PATH [--as CITEKEY]`

Copy a digest into `refs/`, rewriting the prefix if renamed, remapping environments by display name (8.10). Exit 1 if the target exists.

## 12.8 AI

### `loom ai init [--permissions] [--skills]`

Write `ai/` and the vendor files (11.2, 11.3) and append the `bundle-*.tex` line to `.gitignore`. `--permissions` also writes the agents' permission settings; `--skills` also writes the skill stubs and slash commands (11.12). Refuses if `ai/` exists (`loom upgrade` refreshes; it leaves edited mode files alone and writes `<mode>.md.new` beside them).

### `loom ai orient [--run RUN]`

Print the orientation document followed by live state; with `--run`, that run's `thread.md` and `run.log` (11.3).

### `loom ai start [SLUG]`

Create a run directory, print its path, and launch `[ai] agent` if configured (11.4).

### `loom ai discard RUN | --before DATE | --author NAME | --target KEY [--undo]`

Flag review records ignored, or unflag them (7.8). `RUN` may also be a comments session path.

### `loom ai promote PATH [--prefix P] [--replace]`

Copy a draft node or a digest from a run into the quilt (11.7). Exit 1 if the target exists without `--replace`, or if lint on the result reports an error.

### `loom ai check RUN`

Report files outside `RUN`, `comments/`, and `build/` modified since the run started (11.8). **[assumed]** command name.

## 12.9 Machine output

**[decided]** Every `--json` output is a single JSON document. Shapes reuse the manifest's (specs/manifest.md) wherever the same data appears: `status --json` uses the `keys` shape; `deps --json` and `unravel --json` use the `edges` shape; `search --json` uses the `search` shape plus `file` and `url`. New shapes are documented here before they exist.

## 12.10 Environment variables

**[decided]** `LOOM_QUILT` (quilt root, overrides discovery); `LOOM_RUN` (default for `--run`); `LOOM_FIXED_TIME` (fixture generation: all timestamps take this value); `LOOM_PAPER_FIXTURES` (tests: directory of arXiv sources for the paper tier). No other variable is read.

## 12.11 Withdrawn commands

For readers of earlier design notes: `impact` became `unravel`; `dependents` and `closure` folded into `deps`/`unravel`; `resolve` folded into `search --json`; `tag` became `id`; `state set`/`state refresh` became `accept`/`status`; `ref use` disappeared when digests became LaTeX; `ai finish`, `ai resume`, `ai list`, `ai restore` folded into runs having no lifecycle, `ai orient --run`, `status --runs`, and `ai discard --undo`; `digest export` is `cp`; `init --ai` is `ai init`; `bundle --for-review` is the modes' business; `new --in FILE` is `new --print`.

## Open questions

- Whether `loom check` should compile bundles by default (slow) or only with a flag. **[assumed]** `--bundles stale` by default.
- Whether `loom search` should accept `--kind` filters. **[assumed]** Yes, `--kind node|digest|master|thread`.
- A `loom open KEY` that launches the user's editor at the node's file and line. Not in the MVP; would need a user-config editor key.
