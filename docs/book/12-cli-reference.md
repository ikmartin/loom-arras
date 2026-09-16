# 12. CLI reference

Every loom command, with syntax, flags, behaviour, exit codes, and machine output. Behaviour is specified in the earlier chapters; this chapter is the index and the fixed surface. The implementation generates the `--help` text and the user-facing reference from the same definitions, so that this chapter, the help, and the code cannot drift apart without a test failing; 12.2 below is that generated reference.

## 12.1 Conventions

**[decided]**

- Quilt discovery: every command except `init` and `doctor` walks up from the current directory to the nearest `config.toml` with a `[quilt]` table and runs against that quilt. `--quilt PATH` overrides.
- Exit codes: `0` success; `1` a content problem (lint errors, a failed identity test, a failed compile, a refused write that the author can fix in the source); `2` a usage or environment problem (bad arguments, missing tools, no author name, refused destination).
- `--json`: machine output on stdout, one JSON document, nothing else on stdout; diagnostics and progress go to stderr.
- `--yes`: skip confirmations that would otherwise be asked on a terminal. Commands that would ask and have no terminal and no `--yes` exit 2.
- `--run DIR`: on `bundle`, `comment`, `status`, `search`, `deps`, `unravel`, `lint`, and `ai orient`: append the invocation to `DIR/run.log` (`LOOM_RUN` is the default); on `bundle`, also copy the output into `DIR`; on `comment`, make the run the author (refusing `--author`) and write to `DIR/annotations.json`; `ai promote` logs its move to the run the file came from (M6, M7).
- `--author NAME`: on `accept` and `comment`, the author name, overriding the user config.
- `--quiet` / `-q` and `--verbose` / `-v` were planned and are not implemented; diagnostics go to stderr, summaries to stdout (M7).
- Keys are written as ids (`rl-0004`), proof keys (`rl-0004/proof`, `rl-0004/proof/2`), qualified keys (`rl-0004#eq:main`, `drafts/main.tex#section:3`), or master paths. Aliases are accepted wherever an id is and resolved.
- Ids in output are always shown with their number in the default master when known: `rl-0004 (Lemma 3.4)`.

## 12.2 Commands

**[decided]** The reference below is generated from the command tree by `loom/scripts/gen_cli_reference.py`; `loom/docs/cli-reference.md` is the same text, and the test `test_cli_reference_matches_checked_in` fails when either drifts from the code. Every command's `--help` prints the same usage and options. Behaviour is specified in the earlier chapters; the sections 12.2 to 12.8 of the pre-implementation book, which listed the commands by hand, are replaced by this generated list (M7). Aliases: `rm` and `remove` for `delete`; `downstream`, `reach`, and `pop` for `unravel`.

### `loom`

`loom [OPTIONS] COMMAND [ARGS]...`

loom: a tool for atomized mathematical development.

Every command except `init` and `doctor` runs against the nearest quilt, found by walking up from the current directory to a `config.toml` with a [quilt] table.

| option | description |
|---|---|
| `--version`, `-V` | Show the version and exit. |

### `loom accept`

`loom accept [OPTIONS] [KEYS]...`

Record acceptance rows and snapshots for KEYS; the only writer of the ledger.

| option | description |
|---|---|
| `--proofs` | Also accept every proof attached to each statement given. |
| `--stale` | Accept every key that is currently accepted-stale, after confirmation. |
| `--author` |  |
| `--force` | Accept even when the master does not compile. |
| `--yes`, `-y` |  |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom ai`

`loom ai [OPTIONS] COMMAND [ARGS]...`

The optional AI layer: runs, orientation, promotion, and discarding review records.

#### `loom ai check`

`loom ai check [OPTIONS] RUN`

Report files outside RUN, comments/, and build/ modified since the run started (loom:agent-wrote-outside-run).

| option | description |
|---|---|
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom ai discard`

`loom ai discard [OPTIONS] [RUN]`

Flag a run's or a comment session's records ignored (or unflag with --undo). Nothing is deleted.

| option | description |
|---|---|
| `--before` `DATE` | Discard every record created before this date (YYYY-MM-DD). |
| `--author` | Discard every record whose author matches. |
| `--target` | Discard every record with an annotation on this key. |
| `--undo` | Reverse: mark matching records not discarded. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom ai init`

`loom ai init [OPTIONS]`

Write ai/ (orientation, modes, runs/) and the vendor files CLAUDE.md and AGENTS.md; refuses if ai/ exists.

| option | description |
|---|---|
| `--permissions` | Also write the agents' permission settings (.claude/settings.json). |
| `--skills` | Also write skill stubs and slash commands for Claude Code. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom ai orient`

`loom ai orient [OPTIONS]`

Print the orientation document followed by the quilt's live state (and a run's journal with --run).

| option | description |
|---|---|
| `--run` `RUN` | Also print this run's thread.md and run.log. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom ai promote`

`loom ai promote [OPTIONS] PATH`

Copy a draft node (to nodes/<id>.tex, allocating an id if it has none) or a digest (to refs/) out of a run; lint runs on the result.

| option | description |
|---|---|
| `--prefix` | Allocate a new id under this prefix instead of [quilt] prefix. |
| `--replace` | Overwrite an existing digest after showing the diff. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom ai start`

`loom ai start [OPTIONS] [SLUG]`

Create a run directory under ai/runs/, print its path, and launch [ai] agent from config.toml if set.

| option | description |
|---|---|
| `--no-launch` | Create the run without launching [ai] agent. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom assemble`

`loom assemble [OPTIONS] MASTER DEST`

Write DEST: MASTER flattened with every \input, \nest (levels shifted), and \include expanded, for arXiv or latexdiff.

| option | description |
|---|---|
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom atomize`

`loom atomize [OPTIONS] SRC [DEST]`

Move each node of SRC into nodes/<id>.tex and write DEST, a copy of SRC with inclusion lines in their place. SRC is not modified.

| option | description |
|---|---|
| `--to` `DEST` |  |
| `--proofs` |  |
| `--sections` | Also move labelled sections and subsections to nodes/. |
| `--all` | Act on SRC and every file it reaches, writing spines under --to-dir. |
| `--to-dir` `DIR` |  |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom build`

`loom build [OPTIONS]`

Scan, derive, render, and publish build/. Exit 1 if any error-severity diagnostic exists (the build is still published).

| option | description |
|---|---|
| `--keys` | Limit rendering to these keys and their masters; the manifest is always complete. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom bundle`

`loom bundle [OPTIONS] [KEY]`

Write build/bundles/<key>.tex: the statements KEY depends on, in dependency order, then KEY itself.

| option | description |
|---|---|
| `--to` `FILE` | Write here instead of build/bundles/. |
| `--run` `DIR` | Also copy into the run directory and log the call. |
| `--with` `FILE` | Substitute a unified diff or a .tex file for the key's text. |
| `--draft` `FILE` | Bundle a node file that is not yet in the quilt. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom check`

`loom check [OPTIONS]`

lint, then compile every master, then bundles. Exit 1 on any failure. The CI command.

| option | description |
|---|---|
| `--no-compile` | Lint only. |
| `--bundles` | Which bundles to compile (stale needs the ledger, milestone M3). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom comment`

`loom comment [OPTIONS] [TARGET] [MESSAGE]`

Write an annotation on TARGET (a key, an equation's qualified key, or a master path); the only writer of review records.

| option | description |
|---|---|
| `--quote` | Anchor to this exact text, which must occur once in the target's own text. |
| `--kind` |  |
| `--run` | Write into this run directory's annotations.json; the run is the author. |
| `--author` |  |
| `--reply` `ID` |  |
| `--resolve` `ID` |  |
| `--batch` | Read JSON lines from stdin: {target, message, quote, kind, reply, resolve}. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom compile`

`loom compile [OPTIONS] [TARGET]`

Run latexmk from the root into build/<stem>/ for a master (default: the default master), or for a bundle by key.

| option | description |
|---|---|
| `--engine` | Override the engine (pdflatex, lualatex, xelatex). |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom delete`

`loom delete [OPTIONS] [ARGS]...`

Refuse: loom never deletes your notes.

### `loom deps`

`loom deps [OPTIONS] KEY`

What KEY depends on: direct statement-edges and proof-edges, grouped.

| option | description |
|---|---|
| `--closure` | The transitive statement closure in dependency order. |
| `--json` |  |
| `--run` `DIR` | Log this call to DIR/run.log. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom digest`

`loom digest [OPTIONS] COMMAND [ARGS]...`

Digests of cited papers: extract one from a paper's source, port one in, or fetch a source.

#### `loom digest extract`

`loom digest extract [OPTIONS] CITEKEY SRC`

Produce refs/CITEKEY.tex mechanically from the reference paper whose main file is SRC (proofs dropped, ids prefixed).

| option | description |
|---|---|
| `--to` `PATH` | Write here instead of refs/<citekey>.tex. |
| `--engine` | Engine for compiling the reference (default: its magic comment or pdflatex). |
| `--no-compile` | Skip compiling the reference; number results by emulation. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom digest fetch`

`loom digest fetch [OPTIONS] CITEKEY`

Fetch the arXiv e-print source for CITEKEY into refs/src/ (gitignored). Requires [refs] fetch = true.

| option | description |
|---|---|
| `--pdf` | Also fetch the PDF into refs/pdf/. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

#### `loom digest import`

`loom digest import [OPTIONS] PATH`

Copy a digest from another quilt into refs/, rewriting its id prefix when --as renames the citekey.

| option | description |
|---|---|
| `--as` `CITEKEY` | Rename the digest's citekey on the way in. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom doctor`

`loom doctor [OPTIONS]`

Report Python, the TeX toolchain, git, the arras bundle, the resolved author name, and the interface version.

| option | description |
|---|---|
| `--json` | Machine-readable report on stdout. |

### `loom id`

`loom id [OPTIONS] FILE`

Print a patch (or write a copy with --to) inserting \label{<id>} on every untagged theorem-like environment and section in FILE. Never modifies FILE.

| option | description |
|---|---|
| `--to` `DEST` | Write the patched copy here instead of printing a diff. |
| `--sections`, `--no-sections` | Also label sections through subsubsection (default on). |
| `--all-levels` | Also label paragraphs and subparagraphs. |
| `--prefix` |  |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom import`

`loom import [OPTIONS] FILE`

Copy a paper and everything it reaches into the quilt, inserting ids into the copies and changing nothing else.

| option | description |
|---|---|
| `--yes`, `-y` |  |
| `--fix-anchoring` | Rewrite the copy so every theorem-like \begin and \end is alone on its line. |
| `--prefix` |  |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom init`

`loom init [OPTIONS] [DIRECTORY]`

Create a quilt in DIRECTORY (default: the current directory); with --from FILE, import a paper into it.

| option | description |
|---|---|
| `--from` `FILE` | Import an existing paper: FILE is its main .tex file, anywhere on disk. |
| `--demo` | Write the demo quilt instead of a minimal master. |
| `--prefix` | Id prefix for new nodes. |
| `--git` | Also run git init. A quilt is files; loom reads no history. |
| `--yes`, `-y` | Skip questions; take defaults and confirm the import. |
| `--fix-anchoring` | With --from: rewrite the copies so theorem-like environments are line-anchored. |

### `loom inline`

`loom inline [OPTIONS] SRC [DEST]`

Write DEST, a copy of SRC with every \input of a node file replaced by its contents. The reverse of atomize.

| option | description |
|---|---|
| `--to` `DEST` |  |
| `--all` | Inline recursively. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom lint`

`loom lint [OPTIONS]`

Scan and print every diagnostic. Fast; no LaTeX runs.

| option | description |
|---|---|
| `--json` |  |
| `--run` `DIR` | Log this call to DIR/run.log. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom new`

`loom new [OPTIONS] TAXON [TITLE]`

Allocate an id and write nodes/<id>.tex with a skeleton for TAXON.

| option | description |
|---|---|
| `--prefix` | Allocate under this prefix instead of [quilt] prefix. |
| `--print` | Print the skeleton without allocating an id or writing a file. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom search`

`loom search [OPTIONS] QUERY`

Find ids by id, alias, title, taxon, tag, or citekey; exact matches first.

| option | description |
|---|---|
| `--kind` |  |
| `--json` |  |
| `--run` `DIR` | Log this call to DIR/run.log. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom serve`

`loom serve [OPTIONS]`

Watch, republish, and serve arras at / and build/ at /build/ until interrupted.

| option | description |
|---|---|
| `--port` | Port to listen on; fails if busy. |
| `--open` | Open the browser. |
| `--no-compile` | Never run latexmk after a change. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom status`

`loom status [OPTIONS]`

Every key with its computed state, cause if stale, and review facts. Never exits nonzero.

| option | description |
|---|---|
| `--stale` |  |
| `--draft` |  |
| `--incomplete` |  |
| `--loose` |  |
| `--unmatched-cites` |  |
| `--undigested` |  |
| `--retired` |  |
| `--runs` |  |
| `--master` |  |
| `--tag` |  |
| `--explain` `KEY` |  |
| `--json` |  |
| `--run` |  |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom unravel`

`loom unravel [OPTIONS] ID`

Everything downstream of ID: dependents, reference and inclusion sites, ledger rows, annotations. Reports; changes nothing.

| option | description |
|---|---|
| `--json` |  |
| `--run` `DIR` | Log this call to DIR/run.log. |
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

### `loom upgrade`

`loom upgrade [OPTIONS]`

Refresh loom.sty, ai/orientation.md, ai/README.md, the vendor files, and unedited mode files; report edited ones.

| option | description |
|---|---|
| `--quilt` `PATH` | Quilt root (default: discovered by walking up). |

## 12.9 Machine output

**[decided]** Every `--json` output is a single JSON document. Shapes reuse the manifest's (specs/manifest.md) wherever the same data appears: `status --json` uses the `keys` shape; `deps --json` and `unravel --json` use the `edges` shape; `search --json` uses the `search` shape plus `file` and `url`. New shapes are documented here before they exist.

**[decided]** `deps --json` carries `relations` beside `statement`, `proof` and `closure`: both directions of every `see:` declaration touching the key, as `{"key": ID, "kind": "see"}`, in target order. In the printed form they are a final section headed "see also (not a dependency):", after the edge lists, so that nothing reads them as dependencies. `unravel` does not list relations: it reports consequences, and a relation has none.

## 12.10 Environment variables

**[decided]** `LOOM_QUILT` (quilt root, overrides discovery); `LOOM_RUN` (default for `--run`); `LOOM_FIXED_TIME` (fixture generation: all timestamps take this value); `LOOM_PAPER_FIXTURES` (tests: directory of arXiv sources for the paper tier); `LOOM_ARRAS_BUNDLE` (a viewer bundle directory that overrides the installed `arras` package and the vendored copy, 12.5); `LOOM_SVG_KEEP` (debugging: a directory that receives every fallback document that failed to compile, DR-79). The test shim reads `FAKE_TEX_LOG`, `FAKE_TEX_FAIL`, and `FAKE_TEX_FAIL_MATCH`. No other variable is read (M7).

## 12.11 Withdrawn commands

For readers of earlier design notes: `impact` became `unravel`; `dependents` and `closure` folded into `deps`/`unravel`; `resolve` folded into `search --json`; `tag` became `id`; `state set`/`state refresh` became `accept`/`status`; `ref use` disappeared when digests became LaTeX; `ai finish`, `ai resume`, `ai list`, `ai restore` folded into runs having no lifecycle, `ai orient --run`, `status --runs`, and `ai discard --undo`; `digest export` is `cp`; `init --ai` is `ai init`; `bundle --for-review` is the modes' business; `new --in FILE` is `new --print`.

## Open questions

- `loom check` compiles bundles with `--bundles stale` by default, `all` or `none` on request. **[decided]** (settled at M2; a failed bundle is reported as `loom:bundle-failed`, M7).
- `loom search` accepts `--kind node|digest|master|thread`. **[decided]** (settled at M1).
- A `loom open KEY` that launches the user's editor at the node's file and line. Not in the MVP; would need a user-config editor key.
