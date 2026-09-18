# loom — working conventions

Loaded automatically at the start of every session in this repo.

## Prose style: NEVER hard-wrap

**Write every docstring, comment, report and markdown file as continuous lines. Do not insert newlines mid-paragraph to hit a column limit.** The editor soft-wraps; a hard wrap just makes the text painful to edit and produces noisy diffs when a sentence changes length.

```python
# WRONG -- hard-wrapped to ~100 cols
def f():
    """One D8 flow field per PARENT, reused across its children -- the BFS is the expensive step
    and d8 caches it per rounded (lat, lon), so edges are grouped by parent to pay it once.
    """

# RIGHT -- one line per paragraph, however long
def f():
    """One D8 flow field per PARENT, reused across its children -- the BFS is the expensive step and d8 caches it per rounded (lat, lon), so edges are grouped by parent to pay it once.
    """
```

This applies to prose only. **Keep** structural line breaks: blank lines between paragraphs, bullet and numbered lists, tables, usage/example blocks, ASCII diagrams, and `key: value` definition lines. Code is formatted normally — this is not a rule about code width.

If a hard-wrapped docstring needs editing, unwrap it while you are in there.

## Docstrings: brief, and about the CURRENT state

Two styles, by audience. Both prefer brevity over completeness — long paragraphs of justification inside a docstring are a smell even when every sentence is true.

**API methods** (public entry points — anything a caller outside the module uses): **full NumPy.** Every parameter with type and default, then `Returns`, then `See Also` where a sibling is the better choice. A parameter whose meaning is obvious still gets a line; type and default alone is enough, no prose needed.

```python
def render_page(*, title, body, active_href, base_url=None, toc_html="", ...):
    """Wrap a body fragment in the shared template.

    Parameters
    ----------
    title : str
        Page title; also the <h1> and the browser tab.
    base_url : str, optional
        Relative path back to the site root; default the config value.
    toc_html : str, default ''
        Pre-rendered rail TOC; '' omits the block.

    Returns
    -------
    str
        Complete HTML document.
    """
```

**Everything else** (helpers, private `_functions`): **one-line summary, blank line, then one or two dense lines.** Cover the call sites and the gotcha, nothing more. Not full sentences — this register:

```python
def assign_urls(nodes, *, disambiguate=True):
    """Assign each rendered node a unique slug + /notes/<slug>/ url.

    Colliding stems and RESERVED_SLUGS names take a subdir prefix, then a counter. Returns a SlugReport for the build log; the corpus is read-only so nothing here is fatal.
    """
```

**Document the current state only. Never explain what changed or why.** The previous version is not visible from the docstring, so text that only makes sense as a diff is dead weight — "there used to be an extra x0.85 here", "this replaced the old two-function pair", "moved on 2026-07-28". Rationale a reader needs in order to not MISUSE the function stays; rationale that is really a changelog entry goes in the commit.

## Reviewing documentation: ten passes

Run these against any markdown or documentation you are reviewing, one pass at a time. They are ordered so that the cheap mechanical ones come last and the ones that survive proofreading come first — 4, 5 and 9 are the dangerous group, because every line reads correctly on its own and only the comparison exposes the fault.

1. **Stale fact** — true when written, false now. *Example: the orientation described `comments/` as "human review records" for a month after the annotation log replaced it, and told agents that loom writes `annotations.json` into their run.*
2. **Missing fact** — the thing shipped and nothing was added. *Example: `canon/` landed in plan 0.9 and never reached the orientation's layout section; neither did the `conflicted` state, the `annotations/` directory, or five commands an agent needs.*
3. **Default presented as constant** — a configurable value written as though it were fixed. *Example: the orientation listed `drafting/`, `canon/` and `.loom/history` as the layout, when all three are `[quilt]` keys; and every id example read `rl-0004`, which an agent in a quilt whose prefix is `q` will copy.*
4. **Conditional stated as universal** — a rule true in one mode, one command or one state, asserted flatly. *Example: "Findings are annotations, graded with `--severity`" — required by review mode, optional elsewhere, and wrong on a clean `ok` read.*
5. **Contradiction with the normative source** — a summary that disagrees with the file that actually governs. *Example: the same sentence contradicted `blocks.md` rule 5, which an agent reads second and which is the real contract. A summary must name which document wins.*
6. **Restatement that drifts** — duplicating a fact that lives elsewhere, so the copy rots. The structural cause of 1 and 2. *Example: the orientation kept its own list of commands and modes, which fell behind the command tree twice. The fix is to point — `loom status --json`, the mode templates — rather than to paraphrase.*
7. **Advice that silently fails** — an instruction that looks right and does nothing. *Example: "pass `--run $LOOM_RUN` on every command" survived the deletion of the launcher that set `$LOOM_RUN`; the variable is simply empty, and every command still succeeds.*
8. **Framing error** — a wrong first sentence that shapes everything after it. *Example: "a quilt: a LaTeX paper managed by loom" made every downstream sentence assume one document, when a quilt is a research project that may hold several or none.*
9. **Prose broken by editing** — a sentence a previous edit left malformed. *Example: `draft.md` read "Never edit source. Never run paste it; the author decides" from 0.9 until it was noticed three plans later; hard wrapping is what hid it.*
10. **Formatting violation** — anything against the hard-wrap rule above. *Example: the orientation and all ten mode templates wrapped every line, which is what concealed 9.*

Two habits make the passes cheap. **Verify, do not recall**: check a command's options against `--help` and a path against the code, because the document you are reviewing is the least reliable source in the room. And **read the normative file beside the summary**, since 4 and 5 are invisible from the summary alone.

## This workspace

`loom-arras/` is the workspace for `loom` (Python CLI, repository in `loom/`) and `arras` (Svelte viewer, repository in `arras/`), and for the three editor clients: `loom-lsp/` (a language server), `loom-nvim/` (a Neovim plugin) and `loom-vscode/` (a VS Code extension). Every tool repository is a separate git repository ignored by this one; this repository tracks the design book, the interface specification, the plans, the work queue, the deviations log, and the committed example quilts under `demos/`.

Start by reading `AGENTS.md`, then `docs/work-queue/README.md`, which is the one place that says what is not done and what would make each of it worth doing. The book describes what is implemented and carries no unfinished business of its own (DR-107), so a question of the form "what is left?" is answered by the queue and never by a chapter. The rules in `AGENTS.md` apply to every session.
