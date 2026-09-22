# WQ-34 · Writing through the editor and the viewer

**Repo:** loom, loom-lsp, loom-nvim, loom-vscode, arras

## Trigger

The author works a review without using the terminal — which means answering an annotation in arras or applying a proposal from the editor, and finding that only the CLI can do it.

## Why deferred

Carried out of [[WQ-23]] when that item graduated into [plan 0.11](../plans/0.11-run-review-view.md). The author's intent, settled there: **the editor clients supersede the CLI for people, further work passes to arras, and the CLI stays as the interface for GUIs and agents.** A few setup commands stay terminal-only — `init`, `upgrade`, `doctor`, `import`, `digest fetch`. The division is source changes in the editor, reading and discussion in arras, conversation in the agent session, the CLI underneath all three.

Two of the five pieces are already spoken for: the write API **was built in 0.11** (DR-161) and proposals as editor code actions are [[WQ-27]]. What is left is the rest of the surface, and it waits until those two show what the shape actually is.

What 0.11 settled that this item inherits: the API is **detected, never assumed** — `GET /_api` answers with the capabilities the publisher serves, and a client that gets 404 offers nothing. An editor client speaks the same endpoints arras does, over the same library functions, so `--json` on write commands is for clients that would rather run a command than open a socket, not for clients that have no other way in.

**Revisited after plan 0.13**, which moved two of this item's assumptions:

- **There is a `message` endpoint now, and it still wakes nothing** (DR-203, DR-195). Loom appends to a session's inbox and a parked reader wakes because a file grew. An editor client that wanted a composer of its own would post to the same endpoint; nothing about it is arras's.
- **Every write now carries a token, an `Origin` check and a JSON content type.** An editor client is a new client of this API and must read `GET /_api` for the token rather than assuming there is none — which is the strongest argument yet for *detected, never assumed*, since a client written against the 0.11 shape would now be refused with a 403 it does not expect.

The trigger is unchanged. What has shrunk is the unknown: the composer in arras is the worked example of a write surface that is not the CLI, and the editor clients' version of it is the same three calls against the same detection.

## Rough design

- **`--json` on every write command.** It covers only read commands today, so a client can write only by parsing prose — which is why the editor clients carry no AI workflow at all: no runs, no comments, no proposals, no promote.
- **Hand-offs between arras and the editor**, the reverse of the existing open-in-arras action: `vscode://file/PATH:LINE` for VS Code, and a server socket (`nvim --listen`, `--remote`) for Neovim.
- **The AI commands in the editor clients**, once the two above exist.

The ordering matters and is the author's: `--json` first, because everything else parses it.

## Blast radius

`loom/src/loom/cli/` for `--json` on writes, `loom-lsp/`, `loom-nvim/`, `loom-vscode/`, arras's own open-in-editor action, Chapter 16.

## Related

[[WQ-23]] (closed; this is the second of the two threads it carried); [[WQ-27]] for code actions; [[WQ-11]] and [[WQ-29]], which are the other editor-client items; [plan 0.11](../plans/0.11-run-review-view.md) for the write API this builds on.
