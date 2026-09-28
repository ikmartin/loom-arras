# Write API

The write API is the HTTP form of the publisher's local commands, so that a browser can request record writes and explicit Git sync steps. It is served by the publisher (loom's `serve`), never by the viewer. Its author-file writes are explicit local incorporation actions: `sync-incorporate` and `adopt-finish`. Interface version 1; status: extended for source sync and pending review.

**[decided]** The commands it wraps are library functions with the same signatures, and a viewer detects it rather than assuming it.

## 1. Discovery

**[decided]** `GET /_api` returns `{"write_api": 1, "capabilities": [...], "token": "..."}` or 404. The token is what every write must carry (§3). A viewer that receives 404 or a version it does not accept shows no editing affordances. The capability list is what this publisher actually serves, so a viewer must read it rather than assume the table below: an endpoint absent from the list answers 404, and a viewer that hides the affordance is correct.

## 2. Endpoints

**[decided]** All requests and responses are JSON. Errors return `{"error": {"code": "...", "message": "..."}}` with 4xx status; the codes are the CLI's exit reasons. A request that names something that does not exist answers 404 with `no-such-node`, `no-such-annotation`, `no-such-session`, `no-such-work` or `no-such-result`, the same refusals the CLI exits 2 for; 400 is a malformed request or a write refused on its merits, 403 the CSRF gate, 409 a conflict with the quilt's state. `annotate`, `reply`, `resolve`, `edit`, `discard` and `refs-cite` name the session they are written in, and one naming none is refused with `no-session`: nothing here falls back to the active session.

| method | path | body | effect |
|---|---|---|---|
| `POST` | `/_api/annotate` | `{target, message, session, quote?, kind?, severity?, payload?, placement?, in?, page?, rects?, author?}` | writes one annotation; with `page`, one on that page of the cited work `target` names, anchored by `quote` (text on it) or `rects` (drawn); `in` names the document a claim about a node is read in, and is refused when that document does not hold the node |
| `POST` | `/_api/reply` | `{annotation, message, session, author?}` | answers one |
| `POST` | `/_api/resolve` | `{annotation, session, message?, undo?, author?}` | closes one that is met; with `undo`, reopens it |
| `POST` | `/_api/edit` | `{annotation, session, message?, severity?, payload?, placement?, author?}` | restates one that still stands |
| `POST` | `/_api/discard` | `{annotation, session, reason?, undo?, author?}` | withdraws one that should not have been raised; with `undo`, puts it back |
| `POST` | `/_api/refs-cite` | `{annotation, session, decision: "accept" \| "reject", reason?, author?}` | records a citation suggestion's outcome and resolves it in `session` |
| `POST` | `/_api/digest-verify` | `{node, statement?, local?, taxon?, author?}` | verifies a proposed result, editing the rendering first when `statement` is given |
| `POST` | `/_api/digest-discard` | `{node, reason, author?}` | discards a proposed result, keeping the reason |
| `POST` | `/_api/locate` | `{citekey, page, text? , rects?, span?}` | answers with the anchor loom would record; **writes nothing** |
| `POST` | `/_api/compare` | `{left, right}` | answers with the differing pairs of two items, each a live document's path, a landmark (its path, `DOC@STEP`, its name, its step) or a live node's key, each side rendered with its changed words; **writes nothing** a record holds, its renderings cached under `build/compare/` by their inputs |
| `POST` | `/_api/session-use` | `{session, author?}` | makes one session the one writing lands in, resuming it when closed |
| `POST` | `/_api/session-rename` | `{session, title, author?}` | retitles one; the id does not change, because it is the address |
| `POST` | `/_api/session-delete` | `{session, reason?, author?}` | tombstones one; its annotations stay in the log |
| `POST` | `/_api/session-new` | `{title, purpose?, author?}` | mints a session named on the spot, with what it is for, and makes it the one writing lands in |
| `POST` | `/_api/session-close` | `{session, author?}` | ends the round; a closed session's annotations are hidden until it is shown or resumed; refused when it is not open |
| `POST` | `/_api/session-reopen` | `{session, author?}` | resumes a closed session, opening a new round, without making it the one writing lands in; refused when it is already open |
| `POST` | `/_api/session-purpose` | `{session, purpose?, author?}` | says what the session is for, shown under its title; an empty or absent `purpose` clears it |
| `POST` | `/_api/agent-stop` | `{session}` | ends the turn loom started in that session; 409 where the quilt does not launch agents |
| `POST` | `/_api/message` | `{text?, session, as?, author?}` | posts into a session's inbox with what the person marked since the last message, and answers with who was attached; with no text it posts those alone, and refuses when there are none |

**[decided]** `GET /_api/events?session=ID&since=SEQ` answers `{session, from, seq, events, attached}`: the events after `SEQ` in the transcript's page form (specs/manifest.md §10.1), the last sequence number, and who is attached now. It reads by an index of where each event starts, so a poll costs what is new; a `session` that is not an id's shape is refused.

**[decided]** `GET /_api/packet?session=ID[&author=NAME]` answers `{session, rows, text}`: what the next message into that session will carry — the sender's own annotations and replies no earlier message carried, the sender being `author` or, without it, the name the viewer's messages are sent under — as rows `{id, kind, act, target, work, page}`, and as the text the agent will read beneath the message, rendered by the function that renders it for the agent, so a viewer's preview is the text itself.

**[decided]** `compare` answers `{ok, left, right, pairs}`. `left` and `right` are `{item, kind, macros}`: the item as asked, `"document"`, `"landmark"` or `"node"`, and the manifest macro set its renderings are typeset with (`canon:<stem>` for a landmark, null for the default). Each pair is `{pair, base, left, right}`: the plain key; which side holds the base — `"left"`, `"right"`, `"both"` when the node changed on both sides since the version an agent copy began from, or null when nothing orders them; and per side `{key, hash, fragment?}`, the node's key there, its `data-hash`, and a fragment path under the build directory with the changed words marked as Review marks them. A pair whose hashes agree is no difference and is left out, a display name changed alone included. A pair the quilt no longer has a live node for has no `fragment`, and the viewer keeps its whole-node marks. An item that is none of these is refused with `unknown-item`, 404. It is a read: the publisher does not rebuild after it. The answer is computed when asked, never at build, since the pairs two items can form grow with the square of the landmarks (book 15.2.6).

**[decided]** `session-purge` is **not** an endpoint and will not become one. Purging rewrites the annotation log, and the one place that should be reachable from is a terminal where the author typed the word.

**[decided]** `annotate` with `page` records a note on a page of a cited work (DR-209) through the same mapping `locate` previews — one function on the publisher, so what the viewer showed is what the log says. `locate` with `span` maps offsets into the page's committed text, which is what a `span=` locator in a URL carries.

**[decided]** `locate` maps a selection to an anchor **on the publisher**, never in the browser. The client's text layer is a third extraction of a page, after the committed page text and the word boxes; only the publisher holds the other two, and only the publisher can say what the page says. The client sends the selected string and never a decision about what the anchor is. Geometry-only anchors are legal and are never refused.

**[decided]** `discard` takes an **annotation**, not a record. Until the annotation log there was a file per review and discarding meant discarding the file; there is one log now, and what a person withdraws is a finding. Discarding a whole session is not served here: it is the author's own housekeeping and has no viewer affordance.

**[decided]** `undo: true` on `resolve` or `discard` puts the finding back (DR-174). It appends another event rather than removing one, so the record still says that it was resolved or withdrawn, when and by whom, and that it was reopened. A viewer offers it in place of the verb that fired, which is what lets those two act on a single click: a wrong one is one click back.

**[decided]** `resolve` and `discard` are different acts and the API keeps them apart, as the log does. Resolved means the fault was addressed; discarded means it should not have been raised. Collapsing them loses the only record of which agent findings were worth having.

### Local source sync and pending review

| method | path | body | effect |
|---|---|---|---|
| `POST` | `/_api/sync-incorporate` | `{incoming, base, reviewer?, review_token?, accept?: string[]}` | verifies the displayed revision and base, preflights and applies its exact patch, then commits only its source paths and the private sync record in separate local commits |
| `POST` | `/_api/adopt-decision` | `{copy, reviewer, fingerprint, keys, document}` | saves the reviewer's selected node keys and document-level group against the exact displayed contribution; changes no author source |
| `POST` | `/_api/adopt-preview` | `{copy, reviewer, fingerprint}` | validates the saved choices and returns an immutable `{token, patch, paths}` preview; writes build cache only, without rebuilding |
| `POST` | `/_api/adopt-finish` | `{copy, reviewer, token, review_token?, accept?: string[]}` | revalidates source, proposal, choices and reviewer, applies exactly the preview and records incorporation locally; optionally records explicit mathematical acceptances bound to review_token |

| `POST` | `/_api/review-decision` | `{reviewer, key, status: "ok" \| "requires-attention"}` | saves a private, version-bound review decision and atomically publishes queue metadata without accepting mathematics or rebuilding document renderings; Finish review rebuilds after the batch (DR-315-luisa) |
| `POST` | `/_api/review-finish` | `{reviewer}` | validates pending OK decisions and records eligible acceptances together |

Every successful mutation triggers a republish; `compare` and `adopt-preview` only prepare cached inspection results and do not republish; the viewer sees the change through the manifest as usual. No endpoint returns rendered content. `sync-incorporate` is a local-only, explicit exception to the rule that Loom does not write author files. It stops before changing them when the reviewed patch conflicts, applies only the files already listed in Incoming, creates one local source commit and one local sync-record commit, and never pushes to Overleaf. Mathematical acceptance is optional and explicit as described below.

## 3. Authorship

**[decided]** `author` defaults to the publisher's resolved author name; `as` declares an identity, and an agent names itself including `Agent` or `AI`. The author's verbs refuse a declared agent identity whichever surface it came through.

**[decided]** **Every write carries three checks.** They are CSRF protection and not a login: they keep other *pages* out, not other people.

1. **`X-Loom-Token`** must equal the token in `.loom/serve.json`, which `GET /_api` serves and the viewer reads.
2. **`Origin`**, when present, must be this server's own.
3. **`Content-Type: application/json`** is required.

A browser blocks a cross-origin *response* and never the *request*, so any page the author happens to be reading could otherwise POST into their quilt and create, resolve or discard. A cross-site form post can set neither a custom header nor a JSON content type, which is what closes it. The socket still binds to loopback, which keeps other machines out; it never kept out the page the author was reading. A request failing any of the three answers 403 with `{"error": {"code": "refused", ...}}`.

## 4. No model behaviour, and no bridge

**[decided]** A publisher calls no model. Loom's `message` endpoint appends to a session's inbox; a parked reader wakes because a file grew. Where the quilt says `launch = true` under `[ai]`, `loom serve` may also start the author's own agent command for one turn when a message waits (DR-273-ikmartin) — the person's command line, not an API — and `POST /_api/agent-stop {session}` ends a running turn, refused with 409 where nothing is launched. `GET /_api/events` carries `agent: {launch, name, state?, error?, activity?, started?, blocked?}`: the last turn's state, when it started, while it runs the last command it logged since it started, and `blocked`, what keeps loom from starting the agent at all (a tracked or faulty `ai-config.toml`) (DR-278-ikmartin). An earlier draft routed a reply through "the bridge": a component that watched threads and invoked the runner. The runner was declined as WQ-15, so the bridge had nothing left to invoke. What this endpoint does is different in kind: the viewer hands a message to a local agent session the author is running or has let loom start for a turn, so that writing in the browser and writing in the terminal are the same conversation (DR-195, DR-203, DR-273-ikmartin). Loom holds no credentials and calls no model. A message lands whether or not anybody is attached, and the answer carries who was, so the composer can say so rather than implying delivery.

**[decided]** The direction is the other way round, and it already works: an agent **pulls**. It reads open annotations with `loom status` and `loom ai annotations`, and answers with `loom annotate --reply`. That needs no server, no credentials held by loom, and no tracking of vendor flags that churn. A person writing in the viewer and an agent answering in its own session are the same log seen from two ends, which is what the log was for.

## 5. Selection to quote

**[decided]** The viewer computes the `quote` for an annotation from the user's selection in a fragment: the selected text mapped back through the block's `data-src` to source text. When the selection crosses converted markup and the source text cannot be recovered exactly, the viewer sends the rendered text and the publisher attempts the whitespace-normalized match; failure returns the CLI's "quote not found" error and the viewer offers a whole-block annotation instead.


| method | path | body | effect |
|---|---|---|---|
| `POST` | `/_api/reviewer-settings` | `{name?: string}` | reads effective local reviewer and source; when name is supplied, trims and atomically saves only local author.name, preserving other keys; response includes reviewer `{name, source}` and rebuilds before returning |

Personal review writes require the displayed `reviewer` to equal the current local identity; missing identity returns `no-reviewer`, changed or missing displayed context returns `reviewer-changed` (409) before mutation. Review decision validation also checks the build's reviewer. The local settings capability uses the existing localhost and token protections and exposes no arbitrary path or configuration write. Unsupported TOML author-table forms refuse rather than risking unrelated keys. Settings changes select a history, never rename it.

The `adopt-decision` body optionally accepts `kept: string[]` beside `keys` and `document`. Kept keys are offered comparison entries explicitly left current; they never enter the incorporation selection or alter the acceptance ledger. Selection, reviewer, revision and preview-token checks remain authoritative. Review finish checks stale support reached through equation targets as well as ordinary statement dependencies (DR-314-luisa).

### Mathematical decisions during incorporation (DR-316-luisa)

| `POST` | `/_api/sync-preview` | `{incoming, base, reviewer}` | prepares the pinned whole pull without applying it and returns a mathematical review preview |

`sync-preview` returns `{ok, result: {token, reviewer, items}}`. `adopt-preview` adds the same object as `result.review` for the selected AI patch. Each mathematical item has `{key, name, reason, local, proposed, unavailable}`; local and proposed hold `{path, macros}` for isolated renderings, local may be null for new blocks, and unavailable explains why acceptance is disabled. Items include unchanged dependent proofs and exclude structural sections and prose. Preview preparation changes no acceptance records or author source.

`sync-incorporate` and `adopt-finish` optionally take `review_token` and `accept: string[]` with the effective `reviewer`. Omitting accept accepts nothing. Tokens bind the exact source, proposed patch and reviewer; foreign keys, repeated keys, changed source and stale selections are refused before application. After incorporation the selected blocks' fingerprints are checked again, applicable masters must compile and stale mathematical support must be included in the acceptance batch. The result adds `accepted` and `pending` lists. All unselected preview items remain explicitly pending. If incorporation succeeded but acceptance validation failed, the success result includes `acceptance_error` and pending mathematics; the UI reports both outcomes without suggesting that source application failed. The final server rebuild publishes the resulting review states. Prose has no acceptance action.
