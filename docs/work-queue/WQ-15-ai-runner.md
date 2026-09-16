# WQ-15 · The AI runner

**Repo:** loom

## Trigger

An agent needs to be *run by* loom rather than beside it — a session that must be reproducible from the quilt, or a mode that has to be executed unattended.

## Why deferred

`docs/specs/runner.md` was written ahead of any need and its flags were never verified against the tools' real documentation. The AI layer works today by preparing context and letting the author run their agent; nothing yet requires loom to hold the process. `config.toml` carries `runner = ""` marked deferred to this specification, which is honest about the state.

## Rough design

Per `docs/specs/runner.md`: a command template, a timeout (`[ai] runner_timeout`, default 900 seconds; on timeout the process is killed and treated as failure), the prompt delivered both on stdin and as `LOOM_PROMPT_FILE` so a tool that cannot read stdin still works, and responses written into the run directory. Two things that specification leaves open and this item must settle: the exact flags, verified against each tool's current documentation at the time rather than at drafting time, and whether responses are streamed into the run directory for long runs.

## Blast radius

A new subsystem, `config.toml`'s `[ai] runner` key (which exists and is inert), `docs/specs/runner.md`, Chapter 11, `loom ai` commands.

## Related

Chapter 11; `docs/specs/runner.md`; [[WQ-18]].
