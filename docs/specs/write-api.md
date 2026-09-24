# Write API

The write API is the HTTP form of the publisher's local commands, so that a browser can request record writes and explicit Git sync steps. It is served by the publisher (loom's `serve`), never by the viewer. Its sole author-file write is the explicit local `sync-incorporate` action described below. Interface version 1; status: extended for source sync and pending review.

**[decided]** The commands it wraps are library functions with the same signatures, and a viewer detects it rather than assuming it.

## 1. Discovery

**[decided]** `GET /_api` returns `{"write_api": 1, "capabilities": [...], "token": "..."}` or 404. The token is what every write must carry (§3). A viewer that receives 404 or a version it does not accept shows no editing affordances. The capability list is what this publisher actually serves, so a viewer must read it rather than assume the table below: an endpoint absent from the list answers 404, and a viewer that hides the affordance is correct.

## 2. Endpoints

**[decided]** All requests and responses are JSON. Errors return `{"error": {"code": "...", "message": "..."}}` with 4xx status; the codes are the CLI's exit reasons.

| method | path | body | effect |
|---|---|---|---|
| `POST` | `/_api/comment` | `{target, message, quote?, kind?, severity?, payload?, placement?, page?, rects?, author?, session?}` | writes one finding; with `page`, a note on that page of the cited work `target` names, anchored by `quote` (text on it) or `rects` (drawn) |
| `POST` | `/_api/reply` | `{annotation, message, author?, session?}` | answers one |
| `POST` | `/_api/resolve` | `{annotation, message?, undo?, author?, session?}` | closes one that is met |
| `POST` | `/_api/edit` | `{annotation, message?, severity?, payload?, placement?, author?, session?}` | restates one that still stands |
| `POST` | `/_api/discard` | `{annotation, reason?, undo?, author?, session?}` | withdraws one that should not have been raised |
| `POST` | `/_api/refs-note` | `{annotation, decision: "accept" \| "reject", reason?, author?}` | records a citation suggestion's outcome |
| `POST` | `/_api/digest-verify` | `{node, statement?, local?, taxon?, author?}` | verifies a proposed result, editing the rendering first when `statement` is given |
| `POST` | `/_api/digest-discard` | `{node, reason, author?}` | discards a proposed result, keeping the reason |
| `POST` | `/_api/locate` | `{citekey, page, text? , rects?, span?}` | answers with the anchor loom would record; **writes nothing** |
| `POST` | `/_api/session-use` | `{session, author?}` | makes one session the one writing lands in, resuming it when closed |
| `POST` | `/_api/session-rename` | `{session, title, author?}` | retitles one; the id does not change, because it is the address |
| `POST` | `/_api/session-delete` | `{session, reason?, author?}` | tombstones one; its annotations stay in the log |
| `POST` | `/_api/session-new` | `{title, author?}` | mints a session named on the spot and makes it the one writing lands in |
| `POST` | `/_api/session-close` | `{session, author?}` | ends the round; a closed session's annotations are hidden until it is shown or resumed |
| `POST` | `/_api/agent-stop` | `{session}` | ends the turn loom started in that session; 409 where the quilt does not launch agents |
| `POST` | `/_api/message` | `{text?, session, as?, author?}` | posts into a session's inbox with what the person marked since the last message, and answers with who was attached; with no text it posts those alone, and refuses when there are none |

**[decided]** `GET /_api/events?session=ID&since=SEQ` answers `{session, from, seq, events, attached}`: the events after `SEQ` in the transcript's page form (specs/manifest.md §10.1), the last sequence number, and who is attached now. It reads by an index of where each event starts, so a poll costs what is new; a `session` that is not an id's shape is refused.

**[decided]** `GET /_api/packet?session=ID[&author=NAME]` answers `{session, rows, text}`: what the next message into that session will carry — the sender's own annotations and replies no earlier message carried, the sender being `author` or, without it, the name the viewer's messages are sent under — as rows `{id, kind, act, target, work, page}`, and as the text the agent will read beneath the message, rendered by the function that renders it for the agent, so a viewer's preview is the text itself.

**[decided]** `session-purge` is **not** an endpoint and will not become one. Purging rewrites the annotation log, and the one place that should be reachable from is a terminal where the author typed the word.

**[decided]** `comment` with `page` records a note on a page of a cited work (DR-209) through the same mapping `locate` previews — one function on the publisher, so what the viewer showed is what the log says. `locate` with `span` maps offsets into the page's committed text, which is what a `span=` locator in a URL carries.

**[decided]** `locate` maps a selection to an anchor **on the publisher**, never in the browser. The client's text layer is a third extraction of a page, after the committed page text and the word boxes; only the publisher holds the other two, and only the publisher can say what the page says. The client sends the selected string and never a decision about what the anchor is. Geometry-only anchors are legal and are never refused.

**[decided]** `discard` takes an **annotation**, not a record. Until the annotation log there was a file per review and discarding meant discarding the file; there is one log now, and what a person withdraws is a finding. Discarding a whole session is not served here: it is the author's own housekeeping and has no viewer affordance.

**[decided]** `undo: true` on `resolve` or `discard` puts the finding back (DR-174). It appends another event rather than removing one, so the record still says that it was resolved or withdrawn, when and by whom, and that it was reopened. A viewer offers it in place of the verb that fired, which is what lets those two act on a single click: a wrong one is one click back.

**[decided]** `resolve` and `discard` are different acts and the API keeps them apart, as the log does. Resolved means the fault was addressed; discarded means it should not have been raised. Collapsing them loses the only record of which agent findings were worth having.

### Local source sync and pending review

| method | path | body | effect |
|---|---|---|---|
| `POST` | `/_api/sync-incorporate` | `{incoming, base}` | verifies the displayed revision and base, preflights and applies its exact patch, then commits only its source paths and the private sync record in separate local commits |
| `POST` | `/_api/review-decision` | `{key, status: "ok" \| "requires-attention"}` | saves a private, version-bound review decision without accepting mathematics |
| `POST` | `/_api/review-finish` | `{}` | validates pending OK decisions and records eligible acceptances together |

Every successful write triggers a republish; the viewer sees the change through the manifest as usual. No endpoint returns rendered content. `sync-incorporate` is a local-only, explicit exception to the rule that Loom does not write author files. It stops before changing them when the reviewed patch conflicts, applies only the files already listed in Incoming, creates one local source commit and one local sync-record commit, and never pushes to Overleaf or accepts mathematics.

## 3. Authorship

**[decided]** `author` defaults to the publisher's resolved author name; `as` declares an identity, and an agent names itself including `Agent` or `AI`. The author's verbs refuse a declared agent identity whichever surface it came through.

**[decided]** **Every write carries three checks.** They are CSRF protection and not a login: they keep other *pages* out, not other people.

1. **`X-Loom-Token`** must equal the token in `.loom/serve.json`, which `GET /_api` serves and the viewer reads.
2. **`Origin`**, when present, must be this server's own.
3. **`Content-Type: application/json`** is required.

A browser blocks a cross-origin *response* and never the *request*, so any page the author happens to be reading could otherwise POST into their quilt and create, resolve or discard. A cross-site form post can set neither a custom header nor a JSON content type, which is what closes it. The socket still binds to loopback, which keeps other machines out; it never kept out the page the author was reading. A request failing any of the three answers 403 with `{"error": {"code": "refused", ...}}`.

## 4. No model behaviour, and no bridge

**[decided]** A publisher calls no model. Loom's `message` endpoint appends to a session's inbox; a parked reader wakes because a file grew. Where the quilt says `launch = true` under `[ai]`, `loom serve` may also start the author's own agent command for one turn when a message waits (DR-273-ikmartin) — the person's command line, not an API — and `POST /_api/agent-stop {session}` ends a running turn, refused with 409 where nothing is launched. `GET /_api/events` carries `agent: {launch, name, state?, error?, activity?, started?, blocked?}`: the last turn's state, when it started, while it runs the last command it logged since it started, and `blocked`, what keeps loom from starting the agent at all (a tracked or faulty `ai-config.toml`) (DR-278-ikmartin). An earlier draft routed a reply through "the bridge": a component that watched threads and invoked the runner. The runner was declined as WQ-15, so the bridge had nothing left to invoke. What this endpoint does is different in kind: the viewer hands a message to a local agent session the author is running or has let loom start for a turn, so that writing in the browser and writing in the terminal are the same conversation (DR-195, DR-203, DR-273-ikmartin). Loom holds no credentials and calls no model. A message lands whether or not anybody is attached, and the answer carries who was, so the composer can say so rather than implying delivery.

**[decided]** The direction is the other way round, and it already works: an agent **pulls**. It reads open findings with `loom status` and `loom ai findings`, and answers with `loom comment --reply`. That needs no server, no credentials held by loom, and no tracking of vendor flags that churn. A person writing in the viewer and an agent answering in its own session are the same log seen from two ends, which is what the log was for.

## 5. Selection to quote

**[decided]** The viewer computes the `quote` for a comment from the user's selection in a fragment: the selected text mapped back through the block's `data-src` to source text. When the selection crosses converted markup and the source text cannot be recovered exactly, the viewer sends the rendered text and the publisher attempts the whitespace-normalized match; failure returns the CLI's "quote not found" error and the viewer offers a whole-block comment instead.
