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

## This workspace

`loom-arras/` is the workspace for `loom` (Python CLI, repository in `loom/`) and `arras` (Svelte viewer, repository in `arras/`), and for the three editor clients: `loom-lsp/` (a language server), `loom-nvim/` (a Neovim plugin) and `loom-vscode/` (a VS Code extension). Every tool repository is a separate git repository ignored by this one; this repository tracks the design book, the interface specification, the plan, the demonstration log, the deviations log, and the committed example quilts under `demos/`.

Start by reading `AGENTS.md`, then `docs/plans/implementation-plan.md`, then `docs/demonstrations/README.md` for the current milestone. The rules in `AGENTS.md` apply to every session.
