# loom-arras

One repository holding five tools and the documents that govern them. `loom` turns a LaTeX paper into a *quilt*, where every theorem-like environment and section carries a permanent id as an ordinary `\label`, dependencies are read from the `\ref`, `\cite[postnote]` and `\uses` an author already writes, acceptances are recorded with content hashes, and review comments are anchored to quoted text. `arras` is the viewer it publishes to. The three editor clients bring the same commands into an editor. The paper still compiles with plain `pdflatex`, from the same files, on Overleaf.

| directory | what it is | language |
|---|---|---|
| `loom/` | the CLI: scanner, reshaping commands, history, digests, build | Python |
| `arras/` | the static viewer for a published quilt | Svelte |
| `loom-lsp/` | a language server over stdio, a client of loom | Python |
| `loom-nvim/` | a Neovim plugin, beside vimtex rather than replacing it | Lua |
| `loom-vscode/` | a VS Code extension, through the language server | TypeScript |

Each tool keeps its own build, tests, dependencies and release. None of them requires any other: a quilt edited in a plain text editor loses nothing but convenience, and `loom` never needs the viewer or an editor client.

## The documents

They are the reason this repository exists, and they govern the tools rather than describing them after the fact.

- `docs/book/` — the design book, in seventeen chapters plus appendices. It describes **what is implemented**, so it reads as the specification of what exists, not as a plan. `docs/book/A-decision-records.md` holds every decision, numbered, with the evidence that forced it.
- `docs/specs/` — the loom–arras interface: the manifest shape, the HTML dialect, the conformance fixture. It wins over the book wherever shapes are concerned.
- `docs/work-queue/` — what is **not** done, each item with an observable trigger saying when it becomes worth doing. A question of the form "what is left?" is answered here and never by a chapter.
- `docs/deviations.md` — every place the implementation departs from a decided statement, each row pointing at its decision record.
- `docs/plans/` — the plan for work in progress. The numbered plans below the current one are history: what was intended at the time.
- `AGENTS.md` — the rules that hold for everyone working here, human or agent. Read it first.

`demos/` holds example quilts: `demo/` is what `loom init --demo` writes, `synthetic/` exercises every construct of the source contract and generates the conformance fixture, and `showcase/` is the one to open when you want to see what loom does. Quilts built from real papers are gitignored, because they contain the paper sources.

## Getting started

```sh
git clone https://github.com/ikmartin/loom-arras
cd loom-arras
uv tool install -e ./loom        # puts `loom` on your PATH, running this checkout
loom --version
```

`uv sync` inside `loom/` builds a virtual environment but does **not** put `loom` on your PATH; that is what `uv tool install -e` is for, and `-e` means a `git pull` takes effect without reinstalling. If the command is still not found afterwards, run `uv tool update-shell` and open a new terminal.

To see a quilt in the viewer:

```sh
cd demos/showcase && loom serve
```

For the viewer's own development, `cd arras && npm ci && npm run dev`. The editor clients have their own READMEs, and `loom-nvim` is installed by a plugin manager from `ikmartin/loom-nvim` (see the mirror, below).

## Tests

| suite | command |
|---|---|
| loom, unit tier | `cd loom && uv run pytest -m "not tex and not paper and not network"` |
| loom, everything | `cd loom && uv run pytest` (needs a TeX distribution and poppler) |
| loom-lsp | `cd loom-lsp && uv run pytest` |
| arras | `cd arras && npm run test:unit` and `npm run test:e2e` |
| the documents | `python docs/work-queue/check.py` |

The LaTeX compiles in loom's tests run with an empty `HOME` and empty TeX trees, so a test can only read what it created.

## Working here

A change that crosses the tools — a language server feature and its two editor sides, say — is one branch and one pull request. That is why they are one repository (DR-196); they were five, and nothing tied the three halves of such a change together.

CI runs `scripts/verify`, one workflow per lane: `loom`, `arras` and `docs`, each triggered only by the paths its lane reads (book 14.4). `loom-nvim/` is additionally pushed to `ikmartin/loom-nvim` by the `mirror loom-nvim` workflow, because a Neovim plugin manager installs a plugin from a repository whose root is the plugin. That repository is a mirror: it takes no pull requests, and what is pushed there is exactly what `loom-nvim/` splits to, so a commit pinned in someone's `lazy-lock.json` keeps resolving.

Releases stay separate: `loom` to PyPI, `arras` to npm, the extension to the Marketplace. Publishing is done by hand, never by CI.

## Collaborators: setting your git up (temporary)

**This section is for the move from five repositories to one, in September 2026. Delete it once everyone has moved.**

`loom`, `arras`, `loom-lsp` and `loom-vscode` are now **archived** on GitHub: read-only, kept so old links and clones still resolve. `loom-nvim` is still live, but only as the mirror described above. All development happens here.

**If you have not cloned anything yet**, the Getting started section above is all you need: one clone brings every tool.

**If you have an old clone of `loom-arras` with the tools cloned inside it**, those directories used to be ignored and are now tracked, so git will not check them out over what is already there. From the root of your clone:

```sh
git status                                  # note anything of yours that is uncommitted
mv loom loom.old && mv arras arras.old      # and the same for loom-lsp, loom-nvim, loom-vscode
git pull
```

The pull writes the five directories with their full history in place. Then check that nothing of yours is left behind: each `*.old` directory is a clone of an archived repository, so anything you had **committed** there is in this repository's history already, and anything **uncommitted** is not.

```sh
cd loom.old && git status && git log origin/main..HEAD    # uncommitted work, and commits you never pushed
```

For uncommitted edits, copy the files across. For commits you never pushed, take them as patches — the old repository is read-only now, so there is nowhere else for them to go:

```sh
cd loom.old && git format-patch origin/main --stdout > /tmp/mine.patch
cd .. && git switch -c my-branch && git am --directory=loom /tmp/mine.patch
```

`git am --directory` replays each commit under that directory, so your messages and authorship survive the move.

Delete the `*.old` directories once they hold nothing you need. Then reinstall the CLI so it points at this checkout, since the old path is gone:

```sh
uv tool install -e ./loom --force
```

**If you develop the Neovim plugin**, point your plugin manager at the checkout instead of the mirror, so you are running the code you are editing:

```lua
{
  dir = "~/dev/loom-arras/loom-nvim",   -- instead of "ikmartin/loom-nvim"
  ft = { "tex", "plaintex" },
}
```

**Do not push to the archived repositories**, and remove them from any remotes you have configured. A push there would be refused, and a fork of one would be a fork of a snapshot.

## License

GPL-3.0-or-later; see `LICENSE`. Files under `loom/src/loom/assets/` (`loom.sty`, the demo quilt, the AI-layer templates) are MIT, so they can travel with your paper: see `loom/NOTICE`.
