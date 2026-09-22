# Write API

The write API is the HTTP form of the publisher's local commands, so that a browser can request record writes and explicit Git sync steps. It is served by the publisher (loom's `serve`), never by the viewer. It never writes author source files. The sync finish action may write local Git commits after the author has applied a patch. Interface version 1; status: extended for source sync and pending review.

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
| `POST` | `/_api/message` | `{text, session?, as?, author?}` | posts into a session's inbox and answers with who was attached |

**[decided]** `session-purge` is **not** an endpoint and will not become one. Purging rewrites the annotation log, and the one place that should be reachable from is a terminal where the author typed the word.

**[decided]** `comment` with `page` records a note on a page of a cited work (DR-209) through the same mapping `locate` previews — one function on the publisher, so what the viewer showed is what the log says. `locate` with `span` maps offsets into the page's committed text, which is what a `span=` locator in a URL carries.

**[decided]** `locate` maps a selection to an anchor **on the publisher**, never in the browser. The client's text layer is a third extraction of a page, after the committed page text and the word boxes; only the publisher holds the other two, and only the publisher can say what the page says. The client sends the selected string and never a decision about what the anchor is. Geometry-only anchors are legal and are never refused.

**[decided]** `discard` takes an **annotation**, not a record. Until the annotation log there was a file per review and discarding meant discarding the file; there is one log now, and what a person withdraws is a finding. Discarding a whole session is not served here: it is the author's own housekeeping and has no viewer affordance.

**[decided]** `undo: true` on `resolve` or `discard` puts the finding back (DR-174). It appends another event rather than removing one, so the record still says that it was resolved or withdrawn, when and by whom, and that it was reopened. A viewer offers it in place of the verb that fired, which is what lets those two act on a single click: a wrong one is one click back.

**[decided]** `resolve` and `discard` are different acts and the API keeps them apart, as the log does. Resolved means the fault was addressed; discarded means it should not have been raised. Collapsing them loses the only record of which agent findings were worth having.

### Local source sync and pending review

| method | path | body | effect |
|---|---|---|---|
| `POST` | `/_api/sync-prepare` | `{incoming}` | pins and checks an incoming Git patch, returning its absolute path and the quilt directory; changes no author file |
| `POST` | `/_api/sync-finish` | `{incoming}` | verifies that the author applied the exact patch with Git, then commits only its source paths and the private sync record in separate local commits |
| `POST` | `/_api/review-decision` | `{key, status: "ok" \| "requires-attention"}` | saves a private, version-bound review decision without accepting mathematics |
| `POST` | `/_api/review-finish` | `{}` | validates pending OK decisions and records eligible acceptances together |

Every successful write triggers a republish; the viewer sees the change through the manifest as usual. No endpoint returns rendered content. The sync endpoints are local-only actions: the browser cannot apply the patch, and Loom never writes an author file. `sync-finish` writes Git commits and Loom's sync record after verifying the author's Git application. It never pushes to Overleaf.

## 3. Authorship

**[decided]** `author` defaults to the publisher's resolved author name; `as` declares an identity, and an agent names itself including `Agent` or `AI`. The author's verbs refuse a declared agent identity whichever surface it came through.

**[decided]** **Every write carries three checks.** They are CSRF protection and not a login: they keep other *pages* out, not other people.

1. **`X-Loom-Token`** must equal the token in `.loom/serve.json`, which `GET /_api` serves and the viewer reads.
2. **`Origin`**, when present, must be this server's own.
3. **`Content-Type: application/json`** is required.

A browser blocks a cross-origin *response* and never the *request*, so any page the author happens to be reading could otherwise POST into their quilt and create, resolve or discard. A cross-site form post can set neither a custom header nor a JSON content type, which is what closes it. The socket still binds to loopback, which keeps other machines out; it never kept out the page the author was reading. A request failing any of the three answers 403 with `{"error": {"code": "refused", ...}}`.

## 4. No model behaviour, and no bridge

**[decided]** There is a `message` endpoint and **nothing in it wakes an agent**. Loom appends to a session's inbox; a parked reader wakes because a file grew. An earlier draft routed a reply through "the bridge": a component that watched threads and invoked the runner. The runner was declined as WQ-15, so the bridge had nothing left to invoke. What this endpoint does is different in kind: the viewer hands a message to a local agent session the author is already running, so that writing in the browser and writing in the terminal are the same conversation (DR-195, DR-203). Loom holds no credentials and calls no model. A message lands whether or not anybody is attached, and the answer carries who was, so the composer can say so rather than implying delivery.

**[decided]** The direction is the other way round, and it already works: an agent **pulls**. It reads open findings with `loom status` and `loom ai findings`, and answers with `loom comment --reply`. That needs no server, no credentials held by loom, and no tracking of vendor flags that churn. A person writing in the viewer and an agent answering in its own session are the same log seen from two ends, which is what the log was for.

## 5. Selection to quote

**[decided]** The viewer computes the `quote` for a comment from the user's selection in a fragment: the selected text mapped back through the block's `data-src` to source text. When the selection crosses converted markup and the source text cannot be recovered exactly, the viewer sends the rendered text and the publisher attempts the whitespace-normalized match; failure returns the CLI's "quote not found" error and the viewer offers a whole-block comment instead.
