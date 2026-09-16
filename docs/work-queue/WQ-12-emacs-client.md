# WQ-12 · An Emacs client

**Repo:** —

## Trigger

Someone wants to drive loom from Emacs.

## Why deferred

No one uses Emacs on this project. `eglot` needs only the server and a root function, so the work is genuinely small — but it is small *whenever* it is done, and writing a client nobody runs means shipping something untested against a real editor, which is exactly what the Neovim and VS Code clients were careful not to do.

## Rough design

An `eglot` server registration plus a root function that finds `config.toml` containing `[quilt]`, mirroring `loom-nvim`'s detection. The commands over loom itself follow the Neovim set. A fourth repository in the workspace, local until the author creates a remote.

## Blast radius

A new repository; Chapter 16 gains a client; nothing in loom changes, since P8 holds and no loom command requires an editor.

## Related

Chapter 16; `loom-nvim` as the closest model.
