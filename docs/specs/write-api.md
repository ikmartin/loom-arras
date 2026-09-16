# Write API (deferred)

The write API is the HTTP form of the publisher's record-writing commands, so that a browser can do what the CLI does: create a thread, append a message, comment, reply, resolve, accept, discard. It is served by the publisher (loom's `serve`), never by the viewer. It writes only to the publisher's own record locations and never to source files. Interface version 1; status: specified, not built.

**[decided]** Everything in this file is deferred. It is written now so that the CLI commands it wraps are designed as library functions with the same signatures, and so that arras can be built with feature detection from the start.

## 1. Discovery

**[decided]** `GET /_api` returns `{"write_api": 1, "capabilities": ["comment", "reply", "resolve", "accept", "thread", "message", "discard"]}` or 404. A viewer that receives 404 or a version it does not accept shows no editing affordances.

## 2. Endpoints

**[decided]** All requests and responses are JSON. Errors return `{"error": {"code": "...", "message": "..."}}` with 4xx status; the codes are the CLI's exit reasons.

| method | path | body | effect |
|---|---|---|---|
| `POST` | `/_api/comment` | `{target, message, quote?, kind?, author?, run?}` | as `loom comment` |
| `POST` | `/_api/reply` | `{annotation, message, author?, run?}` | as `loom comment --reply` |
| `POST` | `/_api/resolve` | `{annotation, message?, author?}` | as `loom comment --resolve` |
| `POST` | `/_api/accept` | `{keys: [...], proofs?: bool, author?}` | as `loom accept` |
| `POST` | `/_api/thread` | `{title?}` | as `loom ai start`; returns the run id |
| `POST` | `/_api/message` | `{thread, body, author}` | appends to the thread's message log |
| `POST` | `/_api/discard` | `{record, undo?: bool}` | as `loom ai discard` |

Every successful write triggers a republish; the viewer sees the change through the manifest as usual. No endpoint returns rendered content.

## 3. Authorship

**[decided]** `author` defaults to the publisher's resolved author name. There is no authentication in version 1; the API binds to localhost and is intended for one person's machine. **[deferred]** Any multi-user deployment needs authentication designed before this API is exposed beyond localhost.

## 4. Messages and the bridge

**[decided]** `POST /_api/message` appends a human message to a thread (`messages.jsonl` in the run directory). Whether a model replies is the bridge's business: a separate, optional component that watches threads and invokes the runner (`runner.md`). Version 1 of this API has no model behaviour; a thread with no bridge is a place people write to each other.

## 5. Selection to quote

**[decided]** The viewer computes the `quote` for a comment from the user's selection in a fragment: the selected text mapped back through the block's `data-src` to source text. When the selection crosses converted markup and the source text cannot be recovered exactly, the viewer sends the rendered text and the publisher attempts the whitespace-normalized match; failure returns the CLI's "quote not found" error and the viewer offers a whole-block comment instead.

## Open questions

- Whether `accept` should be exposed at all in version 1, given that a mis-click is an acceptance row forever. **[assumed]** Exposed behind a confirmation in the viewer.
- CSRF and origin checks for a localhost API. **[deferred]**
