# Runner contract (deferred)

**Not implemented.** This file is the runner's design, kept here because `config.toml`'s `[ai] runner` key points at it. Building it is WQ-15 in `docs/work-queue/`; everything below is what it would be, not what loom does today.
A runner is an external command that turns one prompt into one response with no interactive session. Loom needs one only for things that happen without a person at the terminal: a triggered ingest under an explicit `--auto`, a batch review of every stale key, and the reply in an in-viewer thread. The MVP builds none of these. This file fixes the contract so the CLI and the AI layer are designed with it in mind. Status: specified, not built.

**[decided]** Loom never contains a model client. The runner is a command named in `config.toml` under `[ai] runner`, and loom knows nothing about what it does beyond this contract. Any model reached through it must be local: a model running on the machine, or an agent CLI operated locally, per principle P9. No hosted API path exists.

## 1. Invocation

**[decided]** Loom executes the runner command as a subprocess with:

- stdin: the prompt, UTF-8. The prompt is the mode template followed by the input bundle the mode's input contract specifies (a `loom bundle` output, context JSON, digest entries), separated by a line `----- INPUT -----`.
- environment: `LOOM_RUN` set to the run directory's absolute path; `LOOM_QUILT` to the quilt root; `LOOM_MODE` to the mode name; `LOOM_TARGET` to the target key if any. Nothing else is added; nothing is removed.
- working directory: the quilt root.
- arguments: none beyond those in the configured command string, which may include fixed flags.

## 2. Result

**[decided]**

- stdout: the response, UTF-8, written by loom to `<run>/<mode>-<target>.response.md` verbatim.
- exit code 0: success; loom then validates the run directory against the mode's output contract (for a review mode, that `loom comment --run` calls were made or a `--batch` file was written to stdout in the documented form; for a draft mode, that a `draft-<id>.tex` exists) and reports.
- exit code nonzero: failure; stderr is written to `<run>/<mode>-<target>.error.log`; nothing else is recorded.
- timeout: `[ai] runner_timeout` seconds (default 900); on timeout the process is killed and treated as failure.

## 3. What the runner may do

**[decided]** The runner runs with the same permissions as the user; loom cannot sandbox it. The orientation document's write policy applies to it as to any agent: it should write only under the run directory and call loom commands for everything else. Loom checks after the run that no file outside `ai/runs/`, `comments/`, and `build/` changed (by mtime), and reports `loom:runner-wrote-outside-run` (error) if one did; it does not revert.

## 4. Examples of runner commands

The exact flags are to be verified against each tool's current documentation when the runner is built. The shapes:

- An agent CLI's non-interactive mode reading the prompt from stdin and writing the reply to stdout.
- A local model server's CLI (`ollama run <model>` and similar) with the same stdin/stdout behaviour.
- A shell wrapper that does either and adds fixed system instructions.

## 5. Triggers

**[decided]** With a runner configured, `loom ai run --queued` executes, one at a time and with confirmation, the items `loom status` would list as work: undigested citekeys (ingest), stale accepted keys (review). `--auto` skips confirmation and is the explicit opt-in to unattended use, because unattended runs cost tokens and review half-typed lemmas. Nothing runs on save; `serve` never invokes the runner.
