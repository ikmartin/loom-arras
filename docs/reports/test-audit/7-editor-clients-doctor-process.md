# S7 · editor clients, loom doctor, and the verification process

Audit date 2026-09-23, branch `ass-reduction` at `43cb4b6` plus a large uncommitted working tree. Read-only. What I ran: `loom-lsp` pytest, ruff, ruff format and mypy; the `loom-nvim` plenary suite headless; `tsc --noEmit` and `eslint` for `loom-vscode` (no VS Code launch); `loom doctor` and `loom doctor --json`; `loom agent check` on the demo fixture; `loom` mypy and ruff; one single loom TeX test; `docs/work-queue/check.py`; `gh run list` and the failed-step logs of the last CI runs. Timings for the loom and arras suites come from the parallel timing job's output in `scratchpad/audit/summary.txt` (I did not run those suites).

Counts: 121 client tests inventoried (26 loom-lsp, 48 loom-nvim, 47 loom-vscode) plus 2 nvim scripts; 16 doctor checks; 5 doctor tests (4 pytest, 1 CI step); 37 suites and commands in the process inventory.

Headline state of the clients: **loom-lsp is red, 10 of 26 failing; loom-nvim is 47 of 48 (1 red); loom-vscode has not been run since 2026-09-17 04:10 and runs against a stale, gitignored, hand-copied fixture that hides the same breakage.** All eleven failures have one cause: plan 0.9 (`a7fc818`, 2026-09-17 21:01) renamed the synthetic quilt's `drafts/` to `drafting/`, and every client suite hardcodes `drafts/main.tex`. No suite runs in CI or in the local block, so six days passed unnoticed.

## A. Editor clients

### Inventory

Status column: result of my run today (`pass`, `FAIL`, `skip`), or `not run` for VS Code. "synthetic copy" means `loom/tests/quilts/synthetic` copied into a temp dir by the test.

#### loom-lsp (`cd loom-lsp && uv run pytest -q`; 26 tests, 6.4 s wall, 10 FAIL)

| file | test | tests | assumes | asserts | status |
|---|---|---|---|---|---|
| test_encoding.py | test_astral_characters_shift_every_column_after_them | Mapper code-point to UTF-16 conversion | nothing | column after an astral char is +1; round trip; earlier column unaffected | pass |
| test_encoding.py | test_code_point_encoding_is_honoured_when_negotiated | utf-32 negotiation | nothing | position equals code-point index | pass |
| test_encoding.py | test_crlf_text_is_normalised_the_way_loom_normalises_it | CRLF normalisation | nothing | text normalised; line/col and offset round trip | pass |
| test_encoding.py | test_a_position_past_the_end_of_a_line_clamps_to_it | clamping | nothing | past-EOL and past-EOF offsets clamp | pass |
| test_stdio.py | test_the_binary_answers_over_stdio | real binary, framing, handshake | `loom-lsp` on PATH (else `python -m`); synthetic copy; 45 s deadline | initialize returns listed capabilities, no executeCommand; one publishDiagnostics | pass |
| test_stdio.py | test_the_transport_flag_clients_append_is_accepted | `--stdio` flag | `loom-lsp` on PATH or module | `--stdio --version` exits 0 and prints name | pass |
| test_server.py | test_the_quilt_is_found_by_walking_up_and_only_inside_one | find_quilt | synthetic copy | root found from file and dir; loose dir gives None | pass |
| test_server.py | test_diagnostics_match_what_lint_reports | diagnostics parity with CLI | synthetic copy; **`loom` on PATH**; `drafts/main.tex` | every (code, line) of `loom lint --json` is published | **FAIL** (drafts/ gone) |
| test_server.py | test_a_dangling_reference_is_an_error_at_the_command_not_the_line | range and severity | `drafts/main.tex` | dangling-link is Error with code description, range starts at `\ref{sy-9999}` | **FAIL** |
| test_server.py | test_an_unsaved_buffer_produces_diagnostics_the_disk_does_not_justify | overlay | sy-0003 node | edited buffer adds dangling-link; disk untouched; revert clears | pass |
| test_server.py | test_definition_of_a_reference_a_citation_and_an_inclusion | go-to-definition | sy-000B, `drafts/main.tex` | ref resolves to sy-0003 label line; `\input` resolves to file (no citation case despite name) | **FAIL** |
| test_server.py | test_references_finds_every_site_that_names_a_key | references | sy-0003 | non-empty, includes sy-000B | pass |
| test_server.py | test_hover_says_what_the_node_is_and_what_state_it_is_in | hover | sy-0003 | hover text has id, `state:` and a latex block | pass |
| test_server.py | test_document_symbols_are_a_tree_with_proofs_under_their_statements | symbols | sy-0003 | Class root with two Method children | pass |
| test_server.py | test_completion_offers_ids_directives_and_taxa_in_the_right_places | completion | sy-0003 | ids+alias after `\ref{`, directive keys, taxon, citekey | pass |
| test_server.py | test_code_actions_offer_the_missing_uses_as_an_edit_and_the_rest_as_commands | code actions | sy-0002 has uses-missing | Add is an edit with the key; Accept is `loom accept --quilt` with confirmation; commands only loom.run/open | pass |
| test_server.py | test_open_in_arras_is_a_command_naming_the_statement_even_from_its_proof | Open action | sy-000B | exactly one `loom.open` with `["sy-000B"]` from statement and proof | pass |
| test_server.py | test_atomizing_the_node_under_the_cursor_is_one_edit_that_creates_its_file | atomize action | `drafts/main.tex` | CreateFile+write+replace; text moved equals region; `\input{nodes/sy-0001}` | **FAIL** |
| test_server.py | test_the_client_gets_only_the_kinds_it_asked_for | `only` filter | `drafts/main.tex` | kind filtering incl. hierarchical `refactor` | **FAIL** |
| test_server.py | test_a_node_already_in_its_own_file_or_a_section_is_not_offered | atomize refusal | `drafts/main.tex` | no extract action for node file or section | **FAIL** |
| test_server.py | test_a_node_with_no_id_is_offered_one_instead_of_an_atomize | id action | `drafts/main.tex` | no extract; one rewrite inserting `\label{sy-…}` on begin line | **FAIL** |
| test_server.py | test_the_plan_reads_the_unsaved_buffer | atomize from buffer | `drafts/main.tex` | written node text comes from buffer | **FAIL** |
| test_server.py | test_workspace_symbols_find_a_node_by_title_at_its_label | workspace symbols | `drafts/main.tex` | title match located at `\label{sy-0001}`; empty query lists ids | **FAIL** |
| test_server.py | test_dependencies_are_a_call_hierarchy_in_both_directions | call hierarchy | sy-000B | outgoing sy-0003/sy-0006 with sites; incoming from ref | pass |
| test_server.py | test_inlay_hints_name_what_references_and_inclusions_point_to | inlay hints | sy-000B, `drafts/main.tex` | one hint per ref and per multi-key `\uses`; `\input` hint, none for missing | **FAIL** |
| test_server.py | test_closing_a_buffer_drops_its_overlay | didClose | sy-0003 | overlay diagnostic disappears after close | pass |

#### loom-nvim (`nvim --headless --noplugin -u tests/minimal_init.lua -c "PlenaryBustedDirectory tests/ {…sequential = true}"`; 48 tests, 9.4 s wall, 1 FAIL)

| file | test | tests | assumes | asserts | status |
|---|---|---|---|---|---|
| setup_spec | creates every command | `setup()` | plenary at `~/.local/share/nvim/lazy` or `site/pack/vendor` | ten `:Loom*` user commands exist | pass |
| setup_spec | builds a client configuration that starts only inside a quilt | `lsp.client_config` | Neovim 0.12 root_dir contract | cmd, filetypes, init_options; root_dir calls back only inside a quilt | pass |
| setup_spec | registers the server through the mechanism this Neovim has | registration | nvim ≥ 0.11 or lspconfig | returns `vim.lsp.config` or `lspconfig` | pass |
| setup_spec | carries out the language server's commands, confirming before one that writes | `loom.run`/`loom.open` handlers | run and confirm stubbed | declined confirm runs nothing; accepted runs once; `--print` output inserted in buffer; VimLeavePre autocmd | pass |
| setup_spec | gives an empty statusline outside a quilt | statusline | temp dir | returns "" | pass |
| quilt_spec | quilt.root accepts a directory whose config.toml declares a quilt | root detection | temp quilt | resolves root from file and dir | pass |
| quilt_spec | quilt.root rejects a bare directory of .tex files | root detection | temp dir | nil | pass |
| quilt_spec | quilt.root rejects a config.toml that is not a quilt's | root detection | `[tool.black]` config | nil | pass |
| quilt_spec | key_at_cursor takes the argument of the command under the cursor | key extraction | scratch buffer | `rl-0011` | pass |
| quilt_spec | takes the first item of a list | key extraction | scratch buffer | first of `\uses{a, b}` | pass |
| quilt_spec | falls back to the last label above the cursor | key extraction | scratch buffer | label above | pass |
| quilt_spec | takes the first node of the file an \input names, not its path | `\input`/`\nest` | temp quilt with `drafts/` | node id of included file | pass |
| quilt_spec | falls back to the label above for an \input of a file with no node | key extraction | temp quilt | section label | pass |
| quilt_spec | never takes the argument of a command that names no key | key extraction | scratch buffer | `\emph`/`\section` ignored | pass |
| quilt_spec | takes a reference with an optional argument and a star | key extraction | scratch buffer | `\cref*[x]{…}` | pass |
| quilt_spec | returns nil when there is nothing to take | key extraction | scratch buffer | nil | pass |
| commands_spec | argv_for puts the quilt root on every call | argv builder | none | argv[1] is loom, ends `--quilt ROOT` for six commands | pass |
| commands_spec | asks lint for json | argv builder | none | exact lint argv | pass |
| commands_spec | keeps a title with spaces in one argument | argv builder | none | exact `new` argv | pass |
| commands_spec | refuses a new without a title | argv builder | none | nil | pass |
| commands_spec | gives serve the port the session chose | argv builder | none | exact serve argv | pass |
| commands_spec | open starts this session's server, says so, opens the node on it, and reuses it | `:LoomOpen` | fake loom shell script running `python3 -m http.server`; TMUX unset | one start notice; `/node/rl-0004` URL twice, same server; cursor stays | pass |
| commands_spec | opens the node on a real loom serve | end to end | **`loom` on PATH** (here `~/.local/bin/loom`, a uv tool install); demo copy; 60 s wait | URL `/node/dm-0003`; server answers probe | pass |
| atomize_spec | says so and changes nothing when the server is not attached | `:LoomAtomize`/`:LoomId` | client stubbed nil | one WARN "not attached"; buffer unchanged | pass |
| atomize_spec | asks the loom client for one kind at the cursor | request shape | fake client | method, `only` kind, empty diagnostics, uri, range | pass |
| atomize_spec | reports that there is nothing to do, and points at the other command | empty result | fake client | WARN naming `:LoomId`; buffer unchanged | pass |
| atomize_spec | applies the one action the server offers and names it | apply edit | fake client | line replaced; notice is title | pass |
| atomize_spec | takes the first when more than one comes back | tie-break | fake client | first applied | pass |
| atomize_spec | atomize on the real server moves the node under the cursor into nodes/, in the buffer | end to end | **`loom` and `loom-lsp` on PATH**; synthetic copy; opens `drafts/main.tex` | node file created; `\input` in buffer; buffer modified not written | **FAIL** ("the definition is not in the draft": the file does not exist) |
| serve_spec | serve_target takes a tmux pane only when Neovim runs inside tmux | target choice | none | four cases | pass |
| serve_spec | keeps a terminal when told to, even inside tmux | target choice | none | terminal, no warning | pass |
| serve_spec | warns when tmux was asked for and is not there | target choice | none | terminal plus warning | pass |
| serve_spec | tmux argument vectors splits below Neovim's own pane… | argv | none | exact split-window argv | pass |
| serve_spec | passes the server command as separate arguments | argv | none | exact respawn-pane argv | pass |
| serve_spec | free_port returns a port that can be bound | port | loopback | bindable | pass |
| serve_spec | starts once, answers, keeps the cursor in the file, and is reused | terminal server | python3 http.server | started once; URL; window/buffer kept; reuse | pass |
| serve_spec | waits for one server when asked twice while it starts | concurrency | python3 | one start, same URL | pass |
| serve_spec | tries a second port when the first process exits before answering | retry | python3 | two attempts, started | pass |
| serve_spec | stops its server when the session ends | cleanup | python3 | job exits; probe fails | pass |
| serve_spec | runs in one pane beside Neovim, reuses it, and closes it when the session ends | tmux | tmux installed; private socket | pane count 2 then 1; focus kept | pass |
| serve_spec | restarts in the same pane after the server has exited | tmux | tmux | same pane respawned | pass |
| texenv_spec | puts the quilt root first while a quilt file is current, keeping what was there | TEXINPUTS | temp quilt | TEXINPUTS and BIBINPUTS prefixed | pass |
| texenv_spec | does not add the root twice when the quilt is entered again | idempotence | temp quilt | single prefix | pass |
| texenv_spec | restores the original values for a file outside any quilt | restore | temp dirs | originals back | pass |
| texenv_spec | leaves the path alone for a buffer that is not a file | scratch buffer | temp quilt | unchanged | pass |
| texenv_spec | switches between two quilts | switching | two temp quilts | second root | pass |
| texenv_spec | reaches the processes Neovim starts, so TeX run from drafts/ finds the root's files | child env | `kpsewhich` installed (else pending) | kpsewhich finds root loom.sty and refs.bib | pass |
| texenv_spec | texenv in setup is not installed when tex_search_path is off | option | none | no BufEnter autocmd; TEXINPUTS unchanged | pass |

| script | what | assumes | asserts |
|---|---|---|---|
| scripts/smoke.lua | attach to a real server on a real file, print diagnostics | `LOOM_LSP` or `loom-lsp` on PATH; args quilt root and file | nothing: exits 1 only if the client never attaches; prints counts |
| scripts/probe.lua | hover and definition at the first `\ref` | same | nothing: Lua `assert` on attach only; prints results |

#### loom-vscode (`LOOM_LSP=… LOOM_BIN=… npm test`; 47 tests in two runs; not run today)

`npm test` compiles, downloads VS Code into `.vscode-test/` (1.138.0 cached here), and opens two Electron hosts: `fixtures/synthetic` and `fixtures/plain`. Both fixture dirs are **gitignored** and filled by hand (`cp -R ../loom/tests/quilts/synthetic fixtures/synthetic`); the copy here dates from 2026-09-16 and still has `drafts/`, `comments/`, `refs/`. `tsc --noEmit` and `eslint src` are clean (1.4 s, 1.1 s).

| file | test | tests | assumes | asserts | status |
|---|---|---|---|---|---|
| unit | command builders put the quilt root on every call | argvFor | none | argv[0] loom, ends `--quilt` root | not run |
| unit | ask lint for json and serve for the port given | argvFor | none | exact argv | not run |
| unit | build no serve without a port | argvFor | none | undefined | not run |
| unit | keep a title with spaces in one argument | argvFor | none | exact argv | not run |
| unit | refuse what they cannot build | argvFor | none | undefined for three cases | not run |
| unit | build the arras url on a server, with or without a trailing slash | nodeUrl | none | two URLs | not run |
| unit | confirm only what writes | confirmationFor | none | accept confirms, status not | not run |
| unit | freePort gives a port that can be listened on | freePort | loopback | listens on it | not run |
| unit | waitForManifest is true once the manifest answers | poll | local http server | true | not run |
| unit | waitForManifest is false on timeout | poll | free port | false in < 3 s | not run |
| unit | waitForManifest is false promptly once the process is gone | poll | alive callback | false in < 1 s | not run |
| unit | accepts a directory whose config.toml declares a quilt | findQuilt | temp dir | root | not run |
| unit | rejects a bare directory of tex files and a config.toml that is not a quilt | findQuilt | temp dirs | undefined twice | not run |
| unit | key: takes the argument of the command it sits in | keyAt | none | id | not run |
| unit | key: takes the first item of a list | keyAt | none | first id | not run |
| unit | key: falls back to the last label above it | keyAt | none | label | not run |
| unit | key: takes the first node of the file an \input names, not its path | keyAt | temp root | node id for `\input` and `\nest` | not run |
| unit | key: falls back to the label above for an \input of a file with no node | keyAt | temp root | section label | not run |
| unit | key: never takes the argument of a command that names no key | keyAt | none | label / undefined | not run |
| unit | key: takes a reference with an optional argument and a star | keyAt | none | id | not run |
| unit | key: gives nothing when there is nothing to take | keyAt | none | undefined | not run |
| unit | LaTeX Workshop names the quilt root from the workspace folder | fromFolderValue | none | `.`, relative, absolute | not run |
| unit | compares versions numerically | compareVersions/atLeast | none | orderings | not run |
| unit | does nothing when LaTeX Workshop is not installed | plan | none | `none` | not run |
| unit | sets fromFolder on a recent version | plan | none | `fromFolder` values | not run |
| unit | does nothing when fromFolder already names the root | plan | none | `none` | not run |
| unit | sets fromWorkspaceFolder on 10.12 to 10.14 when the quilt is the folder | plan | none | kind | not run |
| unit | needs 10.15.0 for a nested quilt, and 10.12.0 for any | plan | none | `unsupported` with message | not run |
| integration | activates, because the workspace is a quilt | activation | real VS Code; fixture | isActive | not run |
| integration | registers every Loom command | contributions | real VS Code | twelve commands | not run |
| integration | finds the quilt this workspace is | findQuilt + exports | fixture | root equals folder; `client` in api | not run |
| integration | opens a node of the quilt and keeps the document intact | open doc | `LOOM_NODE` or sy-0003 | text names id | not run |
| integration | the language client reaches running when the server is on the path | client | **skips without `LOOM_LSP`** | state 2 within 30 s | not run |
| integration | open in arras starts a server once, on a free port, and reuses it | `loom.open` | hooks stubbed | one start; URL; reuse | not run |
| integration | open in arras runs a real loom serve when loom is on the path | end to end | **skips without `LOOM_BIN`** | manifest 200; stop gives 0 | not run |
| integration | LaTeX Workshop: the command sets fromFolder to . for the workspace folder | command | hooks stubbed | one ask; one write | not run |
| integration | the automatic offer stops after Don't ask again | memory | hooks stubbed | asked once; no write | not run |
| integration | the command writes nothing without LaTeX Workshop | command | hooks stubbed | nothing asked or written | not run |
| integration | navigation: finds a node by its title in the workspace | workspace symbols | **skips without `LOOM_LSP`** | sy-0001 found | not run |
| integration | navigation: shows what a node uses in its call hierarchy | call hierarchy | `LOOM_LSP` | sy-000B → sy-0003 | not run |
| integration | navigation: gives inlay hints over the document | inlay hints | `LOOM_LSP` | ≥ 1 hint | not run |
| integration | atomize does nothing for a node that is already its own file | atomize no-op | `LOOM_LSP` | text and dir unchanged | not run |
| integration | atomize moves the definition in the draft into its own file | atomize | `LOOM_LSP`; **`drafts/main.tex`**; mutates fixture then reverts | file created; `\input` present; reverted and clean | not run (would fail on a fresh fixture copy) |
| outside | the workspace is not one | findQuilt | `fixtures/plain` (gitignored) | undefined | not run |
| outside | no language client is started | activation | same | currentClient undefined | not run |
| outside | the commands are registered but report that there is no quilt | commands | same | registered; **the report is not asserted** | not run |
| outside | atomize and the id command are registered and report there is no quilt | commands | same | registered; **the report is not asserted** | not run |

### Critique

#### Redundant / overlapping

- The same behaviour is implemented and tested three or four times: root detection (loom's `find_quilt`, lsp `find_quilt`, nvim `quilt.root`, vscode `findQuilt`), the key under the cursor (nvim 8 cases, vscode 8 cases, identical inputs), and the argv builders (nvim 5, vscode 7). The cases were clearly copied from one suite to the other and will drift independently. Either move key-at-cursor into the server (a custom request or `textDocument/prepareRename`-style call, since the server already knows every key's range) or keep one JSON case table under `loom-lsp/tests/cases/` that all three suites read.
- `test_diagnostics_match_what_lint_reports` (lsp) and the vscode "client reaches running" test overlap with the stdio test; fine as layers, but only the lsp one checks content.
- `scripts/smoke.lua` and `scripts/probe.lua` overlap the real-server atomize test and the vscode navigation suite and assert nothing; they are manual probes, not tests.

#### Long / slow

- Not a problem: lsp 6.4 s wall (1.86 s in pytest), nvim 9.4 s. The vscode suite pays an Electron start per run and up to 30–60 s waits per `until`; unmeasured today.

#### Delete / combine

- Delete the unused `demo` fixture in `loom-lsp/tests/conftest.py` (no test requests it).
- Rename `test_definition_of_a_reference_a_citation_and_an_inclusion`: it tests no citation.
- Either promote `smoke.lua`/`probe.lua` into assertions inside `atomize_spec` or move them out of the test story in the README.
- Combine the nvim and vscode key/argv cases into one shared table (above).

#### Missing

- **No CI and no local-block entry for any client.** The suites are red and nobody saw: `mirror-nvim.yml` pushes `loom-nvim/` to the public `ikmartin/loom-nvim` on every main push without running a single test.
- No check that a client fixture path exists before use. All three suites hardcode `drafts/main.tex`; they should read `[quilt] main` from the copied quilt's `config.toml` (the rename was exactly a "default presented as constant" failure).
- VS Code fixtures should be made by the test harness (a `pretest` that copies `../loom/tests/quilts/synthetic` and writes `fixtures/plain/paper.tex`), not by a README instruction; on a fresh clone `fixtures/plain` does not exist and the second run cannot start.
- No lsp test for `textDocument/definition` on a `\cite` (the name promises one), for rename, or for the `--stdio` binary shutting down cleanly on `shutdown`/`exit`.
- The outside-a-quilt vscode tests execute `loom.compileFromRoot`, `loom.atomize` and `loom.nodeId` but never capture the message they show; they would pass if the commands threw nothing and said nothing.
- `loom-lsp` mypy and ruff exist in `pyproject.toml` and are clean, but run nowhere.

#### Failure diagnostics

- lsp: `FileNotFoundError: …/synthetic/drafts/main.tex` is clear enough once read, but ten separate failures with the same root cause hide that it is one fault; a session fixture that asserts the expected layout once ("synthetic quilt has no drafts/main.tex; did the fixture layout change?") would fail once with the cause.
- nvim: the real-server test says "the definition is not in the draft" when the draft file does not exist, because `:edit` of a missing path silently opens an empty buffer. It should `assert(vim.fn.filereadable(path) == 1, path .. " missing")` first.
- vscode: skips are silent. Without `LOOM_LSP`/`LOOM_BIN`, 7 of 15 in-quilt tests (client running, real serve, three navigation, two atomize) are skipped and `npm test` is green; the harness should print a loud "7 skipped: LOOM_LSP/LOOM_BIN unset" or fail unless `LOOM_ALLOW_SKIP=1`.

#### Other (fragility, hermeticity)

- Which `loom` a client test runs depends on PATH: lsp's parity test runs `loom` from the uv venv under `uv run` but whatever is first on PATH otherwise; the nvim end-to-end tests use `~/.local/bin/loom` (a uv tool editable install of this checkout, whose dependencies can drift from `loom/.venv`). Pass the loom path explicitly (`LOOM_BIN`) everywhere.
- `tests/minimal_init.lua` finds plenary only at two paths under `~/.local/share/nvim`; on a fresh machine or CI it fails with no hint. Bootstrap it (clone into `.tests/` on first run) or print where it looked.
- The vscode atomize test mutates the shared fixture and reverts in `finally`; an interrupted run leaves `nodes/sy-0001.tex` behind, which then breaks "atomize does nothing for a node already its own file" on the next run. Copy the fixture per run instead.
- Book drift: chapter 14.6's client paragraph says loom-lsp has seventeen tests, loom-nvim seventeen that "start nothing … no loom process runs", loom-vscode twenty, "in their own repositories". Actual: 26, 48 (two start `loom`), 47, all in this workspace. The three client READMEs still say masters live in `drafts/`.

## B. loom doctor

Source: `loom/src/loom/doctor.py` (153 lines), `loom/src/loom/cli/doctor.py` (22 lines). Book: 12.2 generated entry, 4.x (author), 4.7/DR-105 (git), 6.x (pdftotext optional), 9.x (bundle lookup), 14.4 (CI), RELEASE.md steps 5 and 8.

### Checks

Exit code: 2 (`EXIT_USAGE`) if any *required* tool is missing, else 0. There is no warn tier: an optional tool that is missing prints `MISSING (optional)` and still exits 0; a missing author or bundle never changes the exit or the final `ok`.

| # | check | looks at | ok | warn | fail |
|---|---|---|---|---|---|
| 1 | python | `sys.version` | always (report only) | — | — |
| 2 | loom version | `loom.version.__version__` | always | — | — |
| 3 | interface version | `INTERFACE_VERSION` | always | — | — |
| 4 | latexmk | `shutil.which` + `-v`, first line ≤ 60 chars, 20 s timeout | found | — | missing → exit 2, hint `brew install --cask mactex-no-gui` / TeX Live |
| 5 | pdflatex | same, `--version` | found | — | missing → exit 2 |
| 6 | dvisvgm | same | found | — | missing → exit 2 |
| 7 | bibtex | same | found | missing, shown as MISSING (optional), exit 0 | — |
| 8 | biber | same | found | missing (optional) | — |
| 9 | lualatex | same | found | missing (optional) | — |
| 10 | kpsewhich | same | found | missing (optional) | — |
| 11 | pdftotext | same, `-v` | found | missing (optional), hint `brew install poppler` | — |
| 12 | pdfinfo | same | found | missing (optional) | — |
| 13 | git | same | found | missing (optional), hint `brew install git` | — |
| 14 | author | `resolve_author(None)`: the cwd quilt's `[author]`, then `~/.config/loom/config.toml`, then `git config user.name` | name and source printed | `author: none (<how to set it>)`, exit 0 | — |
| 15 | arras bundle | `find_bundle()`: `LOOM_ARRAS_BUNDLE` if it holds `index.html`, the `arras` package, the vendored copy | path, source, `VERSION` first line | `not found (…)`, exit 0 | — |
| 16 | overall | `DoctorReport.ok` = no required tool missing | `ok` | — | `problems: a required tool is missing (exit 2)` |

### Tests

| test | tests | assumes | asserts |
|---|---|---|---|
| tests/unit/test_cli.py::test_doctor_ok_on_shim | text report on the fake toolchain | conftest shim on PATH; isolated HOME | exit 0; `latexmk` in output; last line contains `ok` |
| tests/unit/test_cli.py::test_doctor_json_shape | `--json` | shim | interface and loom versions; five tool names present; `arras.path is None or arras.source` (always true, so vacuous) |
| tests/unit/test_cli.py::test_doctor_missing_tool_exit_2 | required tool missing | shim minus `latexmk`, PATH `partial:/usr/bin:/bin` | exit 2; `latexmk` and `MISSING` in output (would break on a machine with latexmk in /usr/bin) |
| tests/unit/test_fixtures.py::test_never_modifies_author_files (["doctor"] among ~20 commands, ×10 quilts) | doctor writes nothing | fixture copies | exit in (0,1,2); author files' hashes unchanged |
| .github/workflows/loom-unit.yml install-from-clone "doctor reports and exits 2 without TeX" | installed package on a bare runner | ubuntu-latest, `pipx install .` | exit status is exactly 2 (nothing about the output) |

### Critique

**Missing checks** (grouped by what the session history shows breaks a user):

- **Tools loom calls that doctor does not list.** `latex` (the DVI engine behind the per-block SVG fallback, `render/fallback.py`), `xelatex` (a supported `--engine`, `tex/runner.py`), `pdftocairo` (first choice for PDF figures, `render/assets.py`), and the agent CLIs `claude`/`codex` (`agent.py`). The shim in `conftest.py` provides `latex`, `xelatex` and `pdftocairo`, so tests already treat them as part of the toolchain; doctor does not.
- **Capability, not presence.** `refs/pages.py` runs `pdftotext -bbox-layout`; xpdf's `pdftotext` (also `brew install xpdf`) has no such flag and doctor says "found". The quilt's configured `engine` is never checked (a quilt with `engine = "xelatex"` gets `ok`). Biber is optional but a quilt using biblatex needs it, and a biber/biblatex version mismatch is the classic failure; doctor could run `kpsewhich biblatex.sty` and compare versions when biber is present.
- **Bundle interface not compared.** `VERSION` carries `interface 1` but doctor never compares it to `INTERFACE_VERSION`; it prints the string. A `LOOM_ARRAS_BUNDLE` that points at a directory without `index.html` is silently skipped and the next source reported, so a developer who set it gets the vendored bundle without being told. In a dev checkout, the vendored stamp names `arras 43cb4b6` while `arras/` has dozens of uncommitted changes; `vendor_arras.py` stamps HEAD with no `-dirty` marker, so doctor's line cannot tell a stale bundle from a current one.
- **Author treated as informational.** Chapter 12.1 lists "no author name" as an exit-2 environment problem for `accept`/`comment`, but doctor prints `author: none` and then `ok`.
- **Bundle missing treated as informational.** `loom serve` exits 2 without a bundle; doctor says `ok`.
- **Quilt-level checks exist nowhere in one place.** Doctor is machine-level except that it reads the cwd quilt for the author, so it is neither cleanly machine-level nor quilt-aware. What the recent sessions tripped on, and where each is checked today:
  - agent CLI on PATH, `ai/ai-config.toml` complete, tracked by git, ignored by `.gitignore`, `launch` in `config.toml`: `loom agent check` only (which I ran on the demo fixture: `fault: no agent is configured` and `note: .gitignore does not ignore ai/ai-config.toml`, exit 1).
  - `.claude/settings.json` and `.codex/rules/loom.rules` current against `permissions_json()`: **nowhere read-only**; `loom upgrade` rewrites them silently. `ai/layout.py:settings_deny_paths` says it exists "for tests and doctor", but doctor never calls it (stale docstring, or an unbuilt check).
  - mode files and `.loom-modes-version` stale, `loom.sty` older than the installed one: nowhere read-only; only `loom upgrade` acts.
  - `[quilt] drafts` deprecated key: `loom lint` (`loom:deprecated-config-key`).
  
  Recommendation: keep doctor machine-level by default, and when run inside a quilt add a "quilt" section that reuses the existing functions (agent check's `load`/`tracked`/`unignored`, a dry-run of `vendor_files` comparing bytes, the modes-version hash comparison, `loom.sty` version) and says "run `loom upgrade`" or "run `loom agent check`" as the fix. That makes doctor the one place a user runs when something is off, without duplicating logic.
- **Duplication:** none today. Doctor does not overlap `loom agent check` or `loom lint`; the problem is the opposite, that there is no umbrella and nothing points from one to the others.
- **Other missing:** `loom-lsp` on PATH (the editor clients' first failure mode), git `user.name` when no other author source exists (covered by author), the default serve port 8791 being free, Python ≥ 3.11 (pip enforces).

**Clarity of output.** Each missing tool line has a platform hint (good), but the summary `problems: a required tool is missing (exit 2)` does not name which; optional tools share one generic TeX hint even when a user has TeX Live without biber (`tlmgr install biber` would be the fix). The bundle-not-found line gives no remedy (`reinstall loom`, or `scripts/vendor_arras.py ../arras/build` in a checkout). The JSON has no per-item `status` or `severity`, so a consumer must infer "missing" from `path: null` and "matters" from `required`; there is no machine-readable reason for author or bundle problems. The final `ok` is printed even when the author and the bundle are both missing, which reads as "everything is fine".

**Tests.** Three unit tests plus one CI assertion for a command whose whole job is edge cases. Untested: the author line (present, none, from a quilt), the bundle lines (not found, `LOOM_ARRAS_BUNDLE` valid and invalid, vendored), `ok: false` in JSON, the per-platform hints, a version command that hangs (20 s timeout path). `test_doctor_json_shape`'s bundle assertion is vacuous. `test_doctor_missing_tool_exit_2` depends on `/usr/bin` not containing `latexmk` (true on macOS and the CI runner, false on some Linux TeX packagings). `test_doctor_ok_on_shim` costs 1.2 s because every tool version is a fresh Python start of the shim.

**The CI step is weak.** `install-from-clone` asserts only that the exit status is 2. A click usage error also exits 2, so a broken `doctor` could pass. It also never checks the thing the job exists for (DR on install-from-a-clone: "a bare clone is sufficient"): that `arras bundle:` reports `vendored` with the expected interface. Add `loom doctor --json | jq -e '.arras.source == "vendored" and .ok == false and (.tools[] | select(.name=="latexmk") | .path == null)'` and a `loom serve` smoke on the demo quilt.

### Observed output

`loom doctor` (exit 0, 1.6 s wall):

```
loom 0.1.0.dev0  (interface version 1)
python 3.13.13

  latexmk    Latexmk, John Collins, 27 Dec. 2024. Version 4.86a /usr/local/texlive/2024/bin/universal-darwin/latexmk
  pdflatex   pdfTeX 3.141592653-2.6-1.40.26 (TeX Live 2024) /usr/local/texlive/2024/bin/universal-darwin/pdflatex
  dvisvgm    dvisvgm 3.2.2                            /usr/local/texlive/2024/bin/universal-darwin/dvisvgm
  bibtex     BibTeX 0.99d (TeX Live 2024)             /usr/local/texlive/2024/bin/universal-darwin/bibtex
  biber      biber version: 2.20                      /usr/local/texlive/2024/bin/universal-darwin/biber
  lualatex   This is LuaHBTeX, Version 1.18.0 (TeX Live 2024) /usr/local/texlive/2024/bin/universal-darwin/lualatex
  kpsewhich  kpathsea version 6.4.0                   /usr/local/texlive/2024/bin/universal-darwin/kpsewhich
  pdftotext  pdftotext version 25.11.0                /opt/homebrew/bin/pdftotext
  pdfinfo    pdfinfo version 25.11.0                  /opt/homebrew/bin/pdfinfo
  git        git version 2.50.1 (Apple Git-155)       /usr/bin/git

author: ikmartin  (from git config user.name)
arras bundle: /Users/isaac/dev/loom-arras/loom/src/loom/assets/arras  (vendored, arras 43cb4b6 interface 1 vendored 2026-09-23T23:24:53Z)

ok
```

Note the column overflow: a version line of 40+ characters pushes the path out of alignment (latexmk, pdflatex, lualatex). `loom doctor --json` (exit 0), abridged: `{"arras": {"path": ".../loom/src/loom/assets/arras", "source": "vendored", "version": "arras 43cb4b6 interface 1 vendored 2026-09-23T23:24:53Z"}, "author": {"name": "ikmartin", "source": "git config user.name"}, "interface_version": 1, "loom": "0.1.0.dev0", "ok": true, "python": "3.13.13", "tools": [{"hint": "brew install --cask mactex-no-gui", "name": "latexmk", "path": "/usr/local/texlive/2024/bin/universal-darwin/latexmk", "required": true, "version": "Latexmk, John Collins, 27 Dec. 2024. Version 4.86a"}, … nine more of the same shape …]}`. What doctor did not notice here: `arras/` is far ahead of `43cb4b6` in the working tree; `loom-lsp` on PATH is fine but its suite is red; `claude` is not checked.

## C. The verification process

### Suites

Timings: "measured" are from the timing job (`summary.txt`, this machine, 8 cores) or my own runs; CI times from the GitHub step logs of the latest runs.

| suite | command | local block | CI | nowhere | notes |
|---|---|---|---|---|---|
| loom ruff lint | `uv run ruff check src tests scripts` | yes (with `scripts`) | yes (`src tests`, no `scripts`) | | clean; < 1 s |
| loom ruff format | `uv run ruff format --check src tests` | yes | yes | | `scripts/` never format-checked; clean today with it |
| loom mypy (strict, `src`) | `uv run mypy` | **no** | yes, ×3 Pythons | | **fails now: 2 errors in untracked `src/loom/agent.py`**; 1 s |
| loom pytest unit tier | `uv run pytest -q` (all markers) | yes | `-m "not tex and not paper and not network"` ×3 | | ~600 tests; CI 55–58 s |
| loom pytest TeX tier | same (local), `-m tex` (CI) | yes | yes (`loom-tex.yml`, texlive container) | | 32 tests; CI 50 s + 79 s container init; local full run 129 s |
| loom paper tier | `LOOM_PAPER_FIXTURES=… pytest -m paper` | skipped (6 skip) | no | yes | uncommitted fixtures |
| loom network tier | `LOOM_NETWORK=1 pytest` | skipped (1) | excluded | yes | |
| the deselected "biber" test | `--deselect tests/tex/test_reshape_real.py::test_import_neither_reads_nor_writes_the_authors_build_files` | deselected by hand | runs (tex) | | **passes** alone (my run) and in the timing job's full run (11.35 s, slowest test); the exclusion is stale or environment-specific and lives only in session history |
| gen_quilts check | `uv run python scripts/gen_quilts.py --check` | yes | via pytest (`test_the_checked_in_quilt_is_what_the_generator_writes`, synthetic unit + demo/showcase tex) | | **duplicate** of that pytest test in the local run |
| CLI reference check | `test_cli_reference_matches_checked_in` (`gen_cli_reference.py --check`) | via pytest | via pytest | | covers `loom/docs/cli-reference.md` only, not book ch. 12 |
| install from clone + doctor | `pipx install . && loom doctor` exit 2 | no | yes | | 10 s; asserts exit code only |
| arras svelte-check | `npm run check` | yes | yes | | measured 4 s; CI 9 s |
| arras vitest (incl. forbidden-words and host-neutrality guards) | `npx vitest --run` | yes | yes | | 120 tests; measured 2 s |
| arras plain build | `npm run build` | implicitly (write, reading webServers) | yes, separate step | | CI 6 s; built three times locally |
| arras Playwright e2e | `npx playwright test` | yes | yes | | 217 tests; measured 36 s (incl. `build:fixture`); CI 65 s |
| arras Playwright minimal | `npm run test:minimal` | **no** | yes | | 32 tests; measured 8 s |
| arras Playwright write | `npm run test:write` | yes | **no** | | 11 tests; measured 25 s; needs `loom/.venv` |
| arras Playwright reading | `npm run test:reading` | yes | **no** | | 20 tests; measured 53 s, workers 1; slowest single item |
| arras shots / shots:report / shots:floor | `npm run shots…` | no | no | yes | figure generation, manual |
| arras perf probe | `playwright test -c playwright.perf.config.ts` | no | no | yes | needs `PERF_BUILD` |
| arras prerender | `npm run build:prerender` | no | no | yes | book 14.1 says no test checks it |
| arras probes | `scripts/drive.mjs`, `scripts/measure-reading.mjs` | no | no | yes | ad hoc |
| work-queue and book check | `uv run --project loom python docs/work-queue/check.py` | yes | **no** | | 0.04 s; its docstring says "the workspace repository has no CI workflows", stale |
| spec fixture refresh | `docs/specs/tools/refresh-fixture.sh` | via `demos/build.py` | no | | a generator, no `--check` |
| dialect validator | `docs/specs/tools/validate-dialect.py` | inside refresh + loom test | via loom test | | |
| demos rebuild | `python demos/build.py --skip-papers` | yes (generator) | no | | no check mode; nothing tests `demos/{demo,showcase,synthetic}` equal their sources |
| vendor arras | `uv run python loom/scripts/vendor_arras.py ../arras/build` | yes (generator) | no | | stamps HEAD even on a dirty tree; nothing checks the vendored bundle is complete or current |
| loom measure_mapping | `loom/scripts/measure_mapping.py` | no | no | yes | ad hoc |
| loom-lsp pytest | `cd loom-lsp && uv run pytest -q` | no | no | **yes** | **10/26 FAIL** since 2026-09-17; 6 s |
| loom-lsp ruff + mypy | `uv run ruff check src tests && uv run mypy` | no | no | yes | clean; 1 s |
| loom-nvim plenary | `nvim --headless … PlenaryBustedDirectory tests/` | no | no | **yes** | **47/48**; 9 s |
| loom-nvim scripts | `smoke.lua`, `probe.lua` | no | no | yes | manual, no assertions |
| loom-vscode compile + lint | `npm run compile && npm run lint` | no | no | yes | clean (tsc 1.4 s, eslint 1.1 s) |
| loom-vscode integration | `LOOM_LSP=… LOOM_BIN=… npm test` | no | no | **yes** | last run 2026-09-17 04:10; stale gitignored fixture |
| nvim mirror | `mirror-nvim.yml` | — | deploy on main | | pushes untested code to a public repo |
| manual tier | Overleaf procedure, agent sessions | no | no | yes | book 14.1/14.5; per release |
| hard-wrap rule, appendix C/D, chapter 12 | — | no | no | **no check exists** | see Missing checks |

### Critique

#### CI is red and the local block cannot see why

- `loom unit` has failed on every push to this branch since 2026-09-22 (three runs); `loom tex` failed on `43cb4b6`. The latest `loom unit` run: 17 failures in `test_ai_layer.py`, all `FileNotFoundError` from `loom ai init`; `loom tex`: `gen_quilts --check` fails for demo and showcase with `loom ai init --skills --permissions -> 1`. Cause: the workspace `.gitignore` line `ai/` (added 2026-09-16 in `00d1039` to ignore a stray `ai/runs` at the root) is unanchored, so it ignores **`loom/src/loom/assets/ai/formatting.md`**, `loom/src/loom/assets/demo/ai/formatting.md`, and `loom/tests/quilts/{demo,showcase}/ai/formatting.md`. They exist on this disk, so every local run is green; they were never committed, so every CI run is red. The fix is `/ai/` in the root `.gitignore` and `git add` of the four files. No local check compares "what the tests read" with "what git tracks".
- The earlier failure (`35824894685`) was ruff `I001` import order in a file: the local block runs `ruff check` too, so that one was simply not run before pushing.
- mypy is in CI and not in the local block: it fails today on `src/loom/agent.py` (untracked, plan 0.14), so the next commit that adds that file turns CI red a second way.
- `arras-ci.yml` uploads `arras/build` as the `bundle` artefact **after** `test:e2e` and `test:minimal`, whose webServers rebuild `build/` with a fixture staged into `static/build`. The uploaded "bundle" is therefore the minimal-fixture build with `build/build/manifest.json` inside, not the clean `npm run build` from the earlier step.
- Book 14.4 is stale three ways: workflows live at the workspace root as `loom-unit.yml`, `loom-tex.yml`, `arras-ci.yml` (not `loom/.github/workflows/unit.yml`, `tex.yml`, `arras/.github/workflows/ci.yml`); arras CI also runs `test:minimal`; and "the workspace repository has no workflows" is false (it has four). `docs/work-queue/check.py` repeats the false claim.

#### The block itself

- **There is no single entry point.** No Makefile, justfile or `scripts/verify`. The block is restated inside each plan (0.13.2 has mypy and `gen_quilts showcase --check` and splits unit/tex; 0.13.3 and 0.14 have neither; 0.10/0.11 list `gen_cli_reference --check`). Each copy is pass 6 of CLAUDE.md ("restatement that drifts") and it has drifted: none includes the client suites or `test:minimal`, one includes mypy.
- Local-only: `test:write`, `test:reading`, `gen_quilts --check` (explicit), `work-queue/check.py`, ruff on `scripts/`. CI-only: mypy, `test:minimal`, the Python 3.11/3.12 matrix, install-from-clone. Nowhere: all three client suites, lsp mypy/ruff, vscode compile/lint, paper/network tiers, prerender, shots.
- `gen_quilts.py --check` after `pytest` is redundant: the full local pytest already runs `test_the_checked_in_quilt_is_what_the_generator_writes` for all three quilts (showcase 8.1 s alone). Delete it from the block.
- The hand-deselected "biber-failing" test passes on this machine both alone and in the full suite. Either the failure was specific to a sandboxed agent shell (biber's PAR cache needs a writable `$TMPDIR`/HOME) or it has been fixed; either way, a hand `--deselect` that lives in nobody's file is invisible. If it is environment-specific, make the test `skip` with a reason when biber cannot unpack.
- Order dependence: `npx playwright test` leaves `arras/build` holding the staged fixture; the block only ends with a clean `build/` because `test:write`/`test:reading` rebuild after it. Running `vendor_arras.py` after e2e alone would vendor a fixture-staged build (it drops `build/build` but would keep `digests/` if the fixture had a store).
- Port collision: `playwright.reading.config.ts` and `playwright.shots-minimal.config.ts` both pin 4177 with `reuseExistingServer: false`; the shots-minimal comment ("the other three configs pin 4173 and 4176") is stale.

#### Redundant / overlapping

- `gen_quilts --check` vs its pytest wrapper (above).
- Three vite builds per local run (e2e `build:fixture`, write `build`, reading `build`); write and reading produce byte-identical `build/`. CI builds three times too (`build` step, `build:fixture`, `build:fixture-minimal`).
- Root-detection, key-at-cursor and argv tests duplicated across nvim and vscode (part A).

#### Long / slow (measured)

loom pytest 129 s (slowest: the biber test 11.4 s, showcase generator check 8.1 s, vendored-fixture rebuild 7.4 s, canonize 6.6 s, atomize identity 5.9 s: all TeX tier); reading 53 s; e2e 36 s; write 25 s; minimal 8 s; svelte-check 4 s; vitest 2 s; mypy 1 s; lsp 6 s; nvim 9 s. Serial local block ≈ 129 + ~12 (gen_quilts) + 4 + 2 + 36 + 25 + 53 + 1 ≈ **260 s (4.3 min)**, plus ~20 s if mypy, minimal and the three client suites are added.

#### Failure diagnostics

- CI failures are clear in the log but nobody reads them: there is no status check on the branch and the local block never consults `gh run list`.
- A red lsp suite shows ten tracebacks for one cause (see A). The work-queue check prints one line per fault (good).
- `loom doctor` in CI proves only the exit code (see B).

#### Other (hermeticity, fragility)

- Local green does not imply CI green whenever a needed file is untracked or ignored (the `ai/` case) or a generated asset is new (the vendored bundle's hashed chunks are untracked right now: 13+ new files under `loom/src/loom/assets/arras/_app/`). A `git commit -a` would commit an `index.html` that references chunks that are not in the commit, and no test would notice, because loom's serve tests use a fake bundle and CI never loads the vendored one.
- `playwright.write.config.ts` and `playwright.reading.config.ts` hardcode `../loom/.venv/bin/loom` and copy quilts into `arras/.tmp-*` inside the repo (gitignored).
- The loom unit suite is hermetic (isolated PATH/HOME/TEXMF, `GIT_CONFIG_GLOBAL`, agent markers cleared) and xdist-safe in principle: `os.chdir` appears 58 times but each xdist worker is its own process, and the 8791 ports in tests are never bound.

### Speed-ups

Estimates are for this 8-core Mac against the measured serial ≈ 260 s.

1. **Two lanes in parallel (loom ∥ arras).** loom lane ≈ 130 s, arras lane ≈ 120 s, so wall ≈ 135 s. Saves ~125 s (≈ 48 %) with no code change beyond a script with `&` and `wait` that collects both exit codes.
2. **pytest-xdist in loom** (`uv add --dev pytest-xdist`, `pytest -n auto --dist loadfile`). The longest single test is 11.4 s and the TeX tier is ~50 s of serial compiles, so 129 s should fall to ~30–40 s. Watch the TeX tests competing for CPU with Playwright; `-n 4` if both lanes run together. Loom lane becomes ≈ 40 s.
3. **One arras build for every Playwright config.** Build once with `npm run build` (clean). For e2e and minimal, copy `build/` to `build-fixture/` and `build-minimal/` and stage the fixture into each copy's `build/` subdir (a file copy, well under a second), then serve each with `vite preview --outDir` or a static server. Write and reading already serve `build/` through `loom serve` via `LOOM_ARRAS_BUNDLE`; give their webServer commands a `SKIP_BUILD` path. Saves two of three builds locally (~10–15 s) and two of three in CI (~12 s), and, more importantly, removes the shared-`build/` race that currently forbids running configs concurrently.
4. **Run e2e, write and reading concurrently** once (3) is done and ports are unique (reading 4177 vs shots-minimal 4177 must be fixed). Arras lane becomes max(36, 25, 53) + build ≈ 60 s instead of 114 s.
5. **Shard reading.** It is 20 tests at `workers: 1` because the tests write into one quilt copy. A per-worker fixture that copies the showcase and starts `loom serve` on `4177 + workerIndex` would allow 2–3 workers: 53 s → ~25 s.
6. **Drop the redundant `gen_quilts --check`** from the block: ~10–15 s.
7. **Tiers.** `verify fast` (ruff, mypy, loom unit tier with xdist, svelte-check, vitest, lsp pytest, nvim plenary, vscode tsc+eslint, work-queue check): ≈ 30–40 s wall; the inner loop. `verify full` (adds TeX tier, all Playwright configs, vscode integration): with 1–5 ≈ **65–80 s wall** instead of 260 s. `verify paper` stays manual.
8. **CI.** Cache `~/.cache/ms-playwright` (24 s per run on `install --with-deps`); the TeX container init is 79 s of the 2.5 min `loom tex` job, so a slimmer image (`texlive/texlive:latest-small` plus the packages the tests use) or `setup-texlive-action` with a cache would halve it; drop the separate `npm run build` step or make the Playwright configs reuse it.

Should there be a single entry point? Yes. `scripts/verify` (a short Python or shell script at the workspace root, with `fast`/`full` and `--only loom|arras|clients`) that every plan links to instead of pasting a block, that CI calls in each job so local and CI cannot diverge, and that prints a one-line table of suite, result and seconds at the end.

### Missing checks

1. **Tracked-file guard**: fail if any file under `loom/src/loom/assets/`, `loom/tests/quilts/`, `arras/src/` or `loom/src/` is untracked or git-ignored (`git ls-files --others --ignored --exclude-standard -- <paths>` must be empty, and `git ls-files --others --exclude-standard -- <paths>` warned). Would have caught the `ai/` failure and the untracked bundle chunks. Cheap enough for `verify fast`.
2. **Client suites in CI** (a `clients.yml` with path filters): lsp pytest+ruff+mypy; nvim with a pinned Neovim and plenary cloned; vscode compile+lint always, and `xvfb-run npm test` with `LOOM_LSP`/`LOOM_BIN` set and skips disallowed. Gate `mirror-nvim.yml` on the nvim job.
3. **Chapter 12 equals `loom/docs/cli-reference.md`.** Chapter 12.2 says they are "the same text" and that `test_cli_reference_matches_checked_in` "fails when either drifts". The test reads only `loom/docs/cli-reference.md`; chapter 12 has drifted by ~115 lines, including all nine `loom sync` commands missing. Extend the test to compare the chapter's generated section (pass 7 of CLAUDE.md: advice that silently fails).
4. **Appendices C and D equal `loom/src/loom/assets/ai/modes/*.md` and `orientation.md`.** They match today by line containment; nothing enforces it.
5. **Fixture copies agree**: `docs/specs/fixture` = `loom/tests/fixture` = `arras/tests/fixture`, and `demos/{demo,showcase,synthetic}` = `loom/tests/quilts/*` minus `EXPECTED-LINT.txt`, and `loom/src/loom/assets/demo` = `loom/tests/quilts/demo` minus the same. All agree today; only the loom copy is tested (TeX tier). A byte-compare test is milliseconds.
6. **Vendored bundle is current and complete**: `VERSION`'s commit equals `git log -1 --format=%h -- arras/` and the arras tree is clean at vendor time (make `vendor_arras.py` append `-dirty` and refuse unless `--allow-dirty`); every file `index.html` and the `_app` manifest reference exists under `assets/arras` and is tracked; interface in `VERSION` equals `INTERFACE_VERSION`. The last one belongs in doctor too.
7. **mypy in the local block**, and ruff format over `scripts/` in both places.
8. **`docs/work-queue/check.py` in CI** (a workspace job; 0.04 s).
9. **Hard-wrap guard** for markdown, docstrings and comments (CLAUDE.md passes 9 and 10). A crude detector over `docs/**/*.md` finds only six files with probable wraps, so the markdown is nearly clean, but code prose is not: `demos/build.py`'s docstring and the comments in `arras/playwright.*.config.ts` are hard-wrapped. A check makes the rule enforceable instead of remembered.
10. **Book counts and claims that a script can verify**: chapter 14's tier counts (213 unit, 20 vitest, 43 e2e, clients 17/17/20) are all stale; either generate them or stop printing numbers.
11. **CI status in the loop**: `verify` ends with `gh run list --branch "$(git branch --show-current)" --limit 3` so a red CI is seen at the moment the developer is already looking at test output.
12. **Doctor's missing checks** (part B): `latex`, `xelatex`, `pdftocairo`, `claude`/`codex`, `loom-lsp`; poppler capability; bundle interface; a quilt section that reports stale vendor files, modes and `loom.sty` and points at `loom upgrade` and `loom agent check`.
