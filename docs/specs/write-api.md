# Write API

The write API is the HTTP form of the publisher's local commands, so that a browser can request record writes and explicit document-workspace steps. It is served by the publisher (loom's `serve`), never by the viewer. Its author-file writes are explicit local incorporation actions: `sync-incorporate` and `adopt-finish`. Interface version 1; status: extended for source sync and pending review.

**[decided]** The commands it wraps are library functions with the same signatures, and a viewer detects it rather than assuming it.

## 1. Discovery

**[decided]** `GET /_api` returns `{"write_api": 1, "capabilities": [...], "token": "...", "stream": true}` or 404. `stream` says `GET /_api/stream` is served: a `text/event-stream` with an event `manifest`, carrying nothing, each time a new manifest is published, and a comment every fifteen seconds while idle. The token is what every write must carry (§3). A viewer that receives 404 or a version it does not accept shows no editing affordances. The capability list is what this publisher actually serves, so a viewer must read it rather than assume the table below: an endpoint absent from the list answers 404, and a viewer that hides the affordance is correct.

## 2. Endpoints

**[decided]** All requests and responses are JSON. Errors return `{"error": {"code": "...", "message": "..."}}` with 4xx status; the codes are the CLI's exit reasons. A request that names something that does not exist answers 404 with `no-such-` and what it named (`no-such-node`, `no-such-annotation`, `no-such-session`, `no-such-quote`, …), the same refusals the CLI exits 2 for; 400 is a malformed request or a write refused on its merits, 403 the CSRF gate, 409 a conflict with the quilt's state. `annotate`, `reply`, `resolve`, `edit`, `discard` and `library-cite` name the session they are written in, and one naming none is refused with `no-session`: nothing here falls back to the active session.

| method | path | body | effect |
|---|---|---|---|
| `POST` | `/_api/annotate` | `{target, message, session, quote?, kind?, severity?, payload?, placement?, in?, page?, rects?, author?}` | writes one annotation; with `page`, one on that page of the cited work `target` names, anchored by `quote` (text on it) or `rects` (drawn); `in` names the document a claim about a node is read in, and is refused when that document does not hold the node |
| `POST` | `/_api/reply` | `{annotation, message, session, author?}` | answers one |
| `POST` | `/_api/resolve` | `{annotation, session, message?, undo?, applied?, author?}` | closes one that is met; with `undo`, reopens it; with `applied`, on a suggestion whose key reads as it taken, records the key's hash |
| `POST` | `/_api/edit` | `{annotation, session, message?, severity?, payload?, placement?, author?}` | restates one that still stands |
| `POST` | `/_api/discard` | `{annotation, session, reason?, undo?, author?}` | withdraws one that should not have been raised; with `undo`, puts it back |
| `POST` | `/_api/library-cite` | `{annotation, session, decision: "accept" \| "reject", why?, author?}` | records a citation suggestion's outcome and resolves it in `session`: `loom library verify` and `discard` on its id, through the one function both use, so the note names the payload as the work and the body as the claim |
| `POST` | `/_api/library-verify` | `{node, statement?, local?, taxon?, author?}` | verifies a proposed result, editing the rendering first when `statement` is given |
| `POST` | `/_api/library-discard` | `{node, why, author?}` | discards a proposed result, keeping why |
| `POST` | `/_api/locate` | `{citekey, page?, text? , rects?, span?}` | answers with the anchor loom would record and its page; **writes nothing** |
| `POST` | `/_api/compare` | `{left, right}` | answers with the differing pairs of two items, each a live document's path, a landmark (its path, `DOC@STEP`, its name, its step) or a live node's key, each side rendered with its changed words; **writes nothing** a record holds, its renderings cached under `build/compare/` by their inputs |
| `POST` | `/_api/session-use` | `{session, author?}` | makes one session the one writing lands in, resuming it when closed |
| `POST` | `/_api/session-rename` | `{session, title, author?}` | retitles one; the id does not change, because it is the address |
| `POST` | `/_api/session-delete` | `{session, reason?, author?}` | tombstones one; its annotations stay in the log |
| `POST` | `/_api/session-new` | `{title, purpose?, author?}` | mints a session named on the spot, with what it is for, and makes it the one writing lands in |
| `POST` | `/_api/session-close` | `{session, author?}` | ends the round; a closed session's annotations are hidden until it is shown or resumed; refused when it is not open |
| `POST` | `/_api/session-reopen` | `{session, author?}` | resumes a closed session, opening a new round, without making it the one writing lands in; refused when it is already open |
| `POST` | `/_api/session-purpose` | `{session, purpose?, author?}` | says what the session is for, shown under its title; an empty or absent `purpose` clears it |
| `POST` | `/_api/here` | `{route: "reading" \| "review" \| "elsewhere", item?, beside?, block?, selection?, page?, review?, path?, session?}` | keeps where the reader is, in place of the last place any tab reported; **writes nothing**, and holds it in memory only |

**[decided]** `GET /_api/events?session=ID&since=SEQ` answers `{session, from, seq, events}`: the events after `SEQ` in the transcript's page form (specs/manifest.md §10.1) and the last sequence number. It reads by an index of where each event starts, so a poll costs what is new; a `session` that is not an id's shape is refused.

**[decided]** `here` is the reader's place, which `loom here` reports to an agent. A tab posts it after a change of the focused item, the block at the top of its pane, the selection, the PDF page, the session or the block under review has settled, and again when it gains focus, so the tab touched last wins. `item` and `beside` are the focused pane's active item and the other pane's, in the viewer's item shape (`{kind, id, place?}`); `block` is `{src, key}`, the `data-src` and key of the block at the pane's top; `selection` is `{key, text}` in a document or `{page, text?, rects}` on a PDF page, in points from the page's top left, the box tool's region included; `page` is the PDF page in view; on `/review`, `review` is `{key, cause}` in place of the workspace, the cause in the viewer's words; on any other page, `route` is `elsewhere` and `path` is the viewer's. A place over 64,000 bytes, or with no `route`, is refused with `bad-field`. `GET /_api/here` answers `{place, when, age}`: the last place, the second it came and how many seconds ago, `place` null before any tab has reported. It requires the token and this server's origin, like a write, since where a person is reading and what they selected are theirs. Nothing writes it to disk, and a server's stop forgets it.


**[decided]** `compare` answers `{ok, left, right, pairs}`. `left` and `right` are `{item, kind, macros}`: the item as asked, `"document"`, `"landmark"` or `"node"`, and the manifest macro set its renderings are typeset with (`canon:<stem>` for a landmark, null for the default). Each pair is `{pair, base, left, right}`: the plain key; which side holds the base — `"left"`, `"right"`, `"both"` when the node changed on both sides since the version an agent document began from, or null when nothing orders them; and per side `{key, hash, fragment?}`, the node's key there, its `data-hash`, and a fragment path under the build directory with the changed words marked as Review marks them. A pair whose hashes agree is no difference and is left out, a display name changed alone included. A pair the quilt no longer has a live node for has no `fragment`, and the viewer keeps its whole-node marks. An item that is none of these is refused with `unknown-item`, 404. It is a read: the publisher does not rebuild after it. The answer is computed when asked, never at build, since the pairs two items can form grow with the square of the landmarks.

**[decided]** `session-purge` is **not** an endpoint and will not become one. Purging rewrites the annotation log, and the one place that should be reachable from is a terminal where the author typed the word.

**[decided]** `annotate` with `page` records a note on a page of a cited work (DR-209) through the same mapping `locate` previews — one function on the publisher, so what the viewer showed is what the log says. `locate` with `span` maps offsets into the page's committed text, which is what a `span=` locator in a URL carries. `locate` with `text` and no `page` maps the quote on the first page whose committed text holds it, which is what a `quote=` locator with no `page=` carries; it is refused with `not-found`, 404, when no page does.

**[decided]** `locate` maps a selection to an anchor **on the publisher**, never in the browser. The client's text layer is a third extraction of a page, after the committed page text and the word boxes; only the publisher holds the other two, and only the publisher can say what the page says. The client sends the selected string and never a decision about what the anchor is. Geometry-only anchors are legal and are never refused.

**[decided]** `discard` takes an **annotation**, not a record. Until the annotation log there was a file per review and discarding meant discarding the file; there is one log now, and what a person withdraws is a finding. Discarding a whole session is not served here: it is the author's own housekeeping and has no viewer affordance.

**[decided]** `undo: true` on `resolve` or `discard` puts the finding back (DR-174). It appends another event rather than removing one, so the record still says that it was resolved or withdrawn, when and by whom, and that it was reopened. A viewer offers it in place of the verb that fired, which is what lets those two act on a single click: a wrong one is one click back.

**[decided]** `applied: true` on `resolve` says a suggestion was taken. It is refused unless the suggestion's key reads as it taken, and the event records the key's hash then, which the manifest publishes as the annotation's `applied`. Nothing in the write API applies a suggestion: the author edits the source, and loom reads that it was done.

**[decided]** `resolve` and `discard` are different acts and the API keeps them apart, as the log does. Resolved means the fault was addressed; discarded means it should not have been raised. Collapsing them loses the only record of which agent findings were worth having.

### Local source sync and pending review

| method | path | body | effect |
|---|---|---|---|
| `POST` | `/_api/sync-incorporate` | `{incoming, base, reviewer?, review_token?, accept?: string[]}` | verifies the displayed revision and base, checks its exact patch applies, stamps each selected document it reaches, then writes its files and the sync record; commits nothing |
| `POST` | `/_api/adopt-close` | `{copy, reviewer, confirmed?}` | reports unapplied changes for explicit confirmation, then preserves a frozen readable copy and releases its scope |
| `POST` | `/_api/adopt-reopen` | `{copy, reviewer}` | restores a retained draft to active use if its source, identities and scope are still available |
| `POST` | `/_api/adopt-refresh` | `{copy, reviewer}` | merges current paper changes into a draft while retaining proposals; advances saved context only without conflicts |
| `POST` | `/_api/adopt-paper` | `{copy, reviewer}` | compiles the scoped draft in its saved paper context and returns a build-relative PDF path; no rebuild |
| `POST` | `/_api/adopt-start` | `{copy, reviewer, to}` | starts a working document `to`, directly in the drafting directory and never over a file, from an agent document written from scratch, every id it defines made plain (one whose plain id is another result's takes a fresh one); records a `start` line and answers `{to, renamed, inserted, twice}`; changes no existing source |
| `POST` | `/_api/adopt-decision` | `{copy, reviewer, fingerprint, revision, keys, document, preamble}` | saves the reviewer's selected node keys and document-level group against the exact displayed contribution; changes no author source |
| `POST` | `/_api/adopt-preview` | `{copy, reviewer, fingerprint}` | validates the saved choices and returns an immutable `{token, patch, paths}` preview; writes build cache only, without rebuilding |
| `POST` | `/_api/adopt-finish` | `{copy, reviewer, token, review_token?, accept?: string[]}` | revalidates source, proposal, choices and reviewer, stamps the working document as a landmark, applies exactly the preview and records incorporation; answers `{paths, step, landmark, copy, message}`; commits nothing and needs no git repository; optionally records explicit mathematical acceptances bound to review_token |

| `POST` | `/_api/review-decision` | `{reviewer, key, status: "ok" \| "requires-attention"}` | saves a private, version-bound review decision and atomically publishes queue metadata without accepting mathematics or rebuilding document renderings; Finish review rebuilds after the batch (DR-315-luisa) |
| `POST` | `/_api/review-finish` | `{reviewer}` | validates pending OK decisions and records eligible acceptances together |

Every successful mutation triggers a republish before it answers, so the manifest is current when a write answers; `compare` and `adopt-preview` only prepare cached inspection results and do not republish; the viewer sees the change through the manifest as usual. A write that changes records alone (annotations, sessions, messages, citation notes, adoption decisions, reviewer settings) republishes from the publisher's last scan, since the scan reads none of them. No endpoint returns rendered content. `sync-incorporate` is a local-only, explicit exception to the rule that Loom does not write author files. It stops before changing them when the reviewed patch conflicts, applies only the files already listed in Incoming, keeps each document it reaches as a landmark first, commits nothing, and never pushes to the workspace. Mathematical acceptance is optional and explicit as described below.

## 3. Authorship

**[decided]** `author` defaults to the publisher's resolved author name; `as` declares an identity, and an agent names itself including `Agent` or `AI`. The author's verbs refuse a declared agent identity whichever surface it came through.

**[decided]** **Every write carries three checks.** They are CSRF protection and not a login: they keep other *pages* out, not other people.

1. **`X-Loom-Token`** must equal the token in `.loom/serve.json`, which `GET /_api` serves and the viewer reads.
2. **`Origin`**, when present, must be this server's own.
3. **`Content-Type: application/json`** is required.

A browser blocks a cross-origin *response* and never the *request*, so any page the author happens to be reading could otherwise POST into their quilt and create, resolve or discard. A cross-site form post can set neither a custom header nor a JSON content type, which is what closes it. The socket still binds to loopback, which keeps other machines out; it never kept out the page the author was reading. A request failing any of the three answers 403 with `{"error": {"code": "refused", ...}}`.

## 4. No model behaviour, and no bridge

**[decided]** A publisher calls no model and starts no agent (plan 0.20.1). A session's inbox is its transcript: agents write it with `loom session say`, and the viewer reads it through `GET /_api/events` and posts nothing into it, since a conversation with an agent happens in the agent's own app. An earlier draft routed a reply through "the bridge": a component that watched threads and invoked the runner. The runner was declined as WQ-15, so the bridge had nothing left to invoke; the viewer's message composer and loom's launching of an agent for a turn (DR-195, DR-203, DR-273-ikmartin, DR-278-ikmartin) were retired in plan 0.20.1. Loom holds no credentials and calls no model.

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

`sync-preview` returns `{ok, result: {token, reviewer, items}}`. `adopt-preview` adds the same object as `result.review` for the selected agent document's changes. Each mathematical item has `{key, name, reason, local, proposed, unavailable}`; local and proposed hold `{path, macros}` for isolated renderings, local may be null for new blocks, and unavailable explains why acceptance is disabled. Items include unchanged dependent proofs and exclude structural sections and prose. Preview preparation changes no acceptance records or author source.

`sync-incorporate` and `adopt-finish` optionally take `review_token` and `accept: string[]` with the effective `reviewer`. Omitting accept accepts nothing. Tokens bind the exact source, proposed patch and reviewer; foreign keys, repeated keys, changed source and stale selections are refused before application. After incorporation the selected blocks' fingerprints are checked again, applicable masters must compile and stale mathematical support must be included in the acceptance batch. The result adds `accepted` and `pending` lists. All unselected preview items remain explicitly pending. If incorporation succeeded but acceptance validation failed, the success result includes `acceptance_error` and pending mathematics; the UI reports both outcomes without suggesting that source application failed. The final server rebuild publishes the resulting review states. Prose has no acceptance action.

## Section drafts and responsive choices (DR-323-luisa)

`adopt-decision` is a metadata-only publication. The body carries the displayed contribution fingerprint and saved choice revision (initially zero); a stale revision returns 409 rather than overwriting another tab. Its returned result has `keys`, `kept`, `document`, `preamble`, `revision` and `fingerprint`. Every successful selection increments the revision; the manifest publishes the same authoritative row without rendering or compiling. The viewer applies that row immediately and ignores older rows for the same reviewer and fingerprint. A manifest poll containing only changed adoption choices preserves the loaded rendering.

`document` selects prose and ordering; `preamble` separately selects macros and packages, and is false by default. Choices whose base/current/proposed inputs still agree survive unrelated source changes; `invalidated` names choices needing inspection again. Preview tokens bind source, proposal, context, reviewer and choices. Selection does not accept mathematics. Incoming shows accumulated outstanding edits, not just the latest agent message; leaving a change out keeps it available.

Closing and reopening are author actions. Close with outstanding proposals first returns `confirmation_required`, `unapplied` and a message without closing; resend `confirmed: true` to preserve the snapshot and release the scope. Closed source remains on disk but is excluded from the live scan. Reopen refuses a changed retained file, missing source, overlapping scope or occupied identities. The saved rendering and annotations remain readable under the original document path.
