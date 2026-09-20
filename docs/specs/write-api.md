# Write API

The write API is the HTTP form of the publisher's record-writing commands, so that a browser can do what the CLI does: create a thread, append a message, comment, reply, resolve, accept, discard. It is served by the publisher (loom's `serve`), never by the viewer. It writes only to the publisher's own record locations and never to source files. Interface version 1; status: built in plan 0.11.

**[decided]** The commands it wraps are library functions with the same signatures, and a viewer detects it rather than assuming it.

## 1. Discovery

**[decided]** `GET /_api` returns `{"write_api": 1, "capabilities": [...]}` or 404. A viewer that receives 404 or a version it does not accept shows no editing affordances. The capability list is what this publisher actually serves, so a viewer must read it rather than assume the table below: an endpoint absent from the list answers 404, and a viewer that hides the affordance is correct.

## 2. Endpoints

**[decided]** All requests and responses are JSON. Errors return `{"error": {"code": "...", "message": "..."}}` with 4xx status; the codes are the CLI's exit reasons.

| method | path | body | effect |
|---|---|---|---|
| `POST` | `/_api/comment` | `{target, message, quote?, kind?, severity?, payload?, placement?, author?, run?}` | writes one finding |
| `POST` | `/_api/reply` | `{annotation, message, author?, run?}` | answers one |
| `POST` | `/_api/resolve` | `{annotation, message?, undo?, author?, run?}` | closes one that is met |
| `POST` | `/_api/edit` | `{annotation, message?, severity?, payload?, placement?, author?, run?}` | restates one that still stands |
| `POST` | `/_api/discard` | `{annotation, reason?, undo?, author?, run?}` | withdraws one that should not have been raised |
| `POST` | `/_api/refs-note` | `{annotation, decision: "accept" \| "reject", reason?, author?}` | records a citation suggestion's outcome |

**[decided]** `discard` takes an **annotation**, not a record. Until the annotation log there was a file per review and discarding meant discarding the file; there is one log now, and what a person withdraws is a finding. Discarding a whole run is not served here: it is the author's own housekeeping and has no viewer affordance.

**[decided]** `undo: true` on `resolve` or `discard` puts the finding back (DR-174). It appends another event rather than removing one, so the record still says that it was resolved or withdrawn, when and by whom, and that it was reopened. A viewer offers it in place of the verb that fired, which is what lets those two act on a single click: a wrong one is one click back.

**[decided]** `resolve` and `discard` are different acts and the API keeps them apart, as the log does. Resolved means the fault was addressed; discarded means it should not have been raised. Collapsing them loses the only record of which agent findings were worth having.

Every successful write triggers a republish; the viewer sees the change through the manifest as usual. No endpoint returns rendered content.

## 3. Authorship

**[decided]** `author` defaults to the publisher's resolved author name. There is no authentication in version 1; the API binds to localhost and is intended for one person's machine. Exposing it beyond localhost would need authentication, and CSRF and origin checks, designed first; version 1 does not, because it never leaves the machine.

## 4. No model behaviour, and no bridge

**[decided]** Version 1 has no `message` endpoint, and nothing in it wakes an agent. An earlier draft routed a reply through "the bridge": a component that watched threads and invoked the runner. The runner was declined as WQ-15 and `specs/runner.md` is kept only as a declined design, so the bridge had nothing left to invoke. **[decided]** A later version may carry one, for a different reason than the bridge had: not loom invoking a model, but the viewer handing a message to a local agent session the author is already running, so that writing in the browser and writing in the terminal are the same conversation (DR-195). What version 1 says is that the API as it stands does not, and a client detects the endpoint rather than assuming it.

**[decided]** The direction is the other way round, and it already works: an agent **pulls**. It reads open findings with `loom status` and `loom ai findings`, and answers with `loom comment --reply`. That needs no server, no credentials held by loom, and no tracking of vendor flags that churn. A person writing in the viewer and an agent answering in its own session are the same log seen from two ends, which is what the log was for.

## 5. Selection to quote

**[decided]** The viewer computes the `quote` for a comment from the user's selection in a fragment: the selected text mapped back through the block's `data-src` to source text. When the selection crosses converted markup and the source text cannot be recovered exactly, the viewer sends the rendered text and the publisher attempts the whitespace-normalized match; failure returns the CLI's "quote not found" error and the viewer offers a whole-block comment instead.
