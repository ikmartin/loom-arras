This file was turned into plan 0.14.

Loom is a shared, durable, addressable medium for mathematical work between a person and an agent. Everything either party produces has a permanent address, a place to live proportional to how far it is trusted, and one explicit act that moves it to the next place.

This document is about expanding and beefing out the ai integration features. It stops short of creating an ai-quilt. It focuses on the following:

### The transcript

**A session's transcript is a faithful record of the conversation between the person and the agent, and nothing else.**

**Decided:**
- One log per session, `inbox.jsonl`, kept as one file however long it grows.
- Only the two parties write to it: the person through the chat input or `loom session send`, the agent through a new `loom session say`. Loom never writes to it automatically.
- Annotations are not shown in the transcript. An agent may mention and link the annotations it writes, and is encouraged to.
- The transcript stays out of the manifest. It is served in pages: the chat opens on the latest messages and scrolling up loads older ones.
- `loom serve` reads only what is new: an index of where each message starts replaces parsing the whole file on every poll.
- `thread.md` stops being the transcript. `loom ai orient --session` resumes from the chat's tail instead.

### The Chat view

**The conversation and its input live together in one pane: the session item's Chat view, which replaces the Discussion view.**

**Decided:**
- The Chat view belongs to the one attached session; there is only ever one.
- The rail's cluster for a session reads **Chat | What it did**.
- Top to bottom: the transcript, newest at the bottom and paged upward; the status line; the packet tray; the input, with send and stop.
- The input is as wide as its pane. It is today's composer (`arras/src/lib/sessions/Composer.svelte`), moved into the new layout and widened.
- The status line says whether an agent is attached, what it is doing, and whether it failed to start. None of this is written to the transcript.
- Choosing a session in the picker opens its Chat.
- Annotations made in other panes still collect in the tray, so sending a packet needs the Chat open but not in focus.
- If a reply that lands off screen turns out to be missed, a small marker in the rail is the remedy, not a second input.

### Packets

**The annotations a person makes reach the agent without being retyped as a message.**

**Decided:**
- A new annotation — a mark, a card or a text selection — goes out with the person's next message automatically.
- The message in the transcript carries a summary of the annotations it sent (`4 suggestions, 2 questions, 3 notes`), never the annotations themselves.
- A tray above the input lists what the next packet holds, each row linking to its annotation, with a preview of the exact text that will be sent.
- A packet can be sent without a message.
- Choosing which annotations a packet carries is left for later.

### Launching an agent from the command line

**Loom starts an agent through a command-line program the person configures, and never through an API.**

**Decided:**
- Loom never asks for an API key and calls no model; it runs a local agent command such as the Claude CLI.
- The commands are set in a quilt-specific `ai/ai-config.toml`, which is gitignored by default and overrides the user-level config. Commands are never in `config.toml`.
- They are a `start` and a `resume` argument list, with a few placeholders loom fills in: the session, a conversation id derived from it, and the prompt.
- Loom refuses to launch from an `ai-config.toml` that git tracks. Otherwise a cloned quilt would run its author's command on the cloner's machine.
- `loom init` creates `ai-config.toml` after asking which AI the person uses: `1. Claude/Claude Code 2. ChatGPT/Codex 3. Other 4. No AI`.
  - Any other answer counts as 4.
  - For 1 or 2 the config is written automatically, and the person is pointed to the file if they want to change anything.
  - For 3 they are told how to fill in the file by hand.
- A flag answers the question without the prompt, so `loom init` can run in tests and scripts.
- Whether loom launches agents at all is a setting in `config.toml`, off by default. `loom init --launch-agents` turns it on. It is a yes or no, not a command, so committing it runs nothing.
- `loom init` asks the questions and writes `ai-config.toml` whether launching is on or off. Its printout says plainly whether agents will be launched and where to change that.
- When launching is on, a message lands and no agent is attached, `loom serve` runs the command: one process per turn, with the conversation carried across turns by the agent's own resume.
- The Chat view offers a stop button, and `loom agent check` tests the configuration without spending anything.

### Links

**An agent can link from the chat to anything the viewer can show, and a click takes the reader there.**

**Decided:**
- One link form for everything: nodes, documents at a place, works at a page or a quote, annotations and sessions.
- Only what the viewer can display is linkable; a session's drafts and diffs are not.
- A link with empty text is named by the viewer (`[](loom:node/sh-0009)` reads `Theorem 3.1`); a link with text shows the text as written. The choice is the agent's.
- Links are checked when a message is posted, and a `loom link` helper prints a correct one, so the agent never composes one by hand.
- A click reveals the item where it is open, or opens it at the place named in the pane the reader is not focused on. A link to an annotation opens its target at the mark with the card open.
- Links in the chat get hover previews, as links elsewhere do.

### What it did

**A session's What it did view is the plain record of everything the agent did through loom.**

**Decided:**
- A chronological list of everything in `run.log`, to be edited down later.
- It opens at the bottom of its page, so the newest action is at the bottom and is the first thing seen.
- Each row gives a link to the annotation where there is one, the fixed name of what it concerns (`draft1.tex`, `sh-0009`), never a derived one such as `Theorem 3.1`, and its state.
- The annotation state system is to be fixed separately.

### The formatting document

**Agents are told, during orientation, how to write what a person reads in the viewer.**

**Decided:**
- A formatting document beside `orientation.md`, served to the agent by `loom ai orient`; a stub exists at `loom/src/loom/assets/ai/formatting.md`.
- It records the link rules: empty link text is named by the viewer, and only what the viewer can show is linked.
- It tells the agent to write proposed text as a suggestion, which the viewer displays, rather than as a file in its session, which it does not.
- Contains instructions for math formatting to achieve proper rendering in the transcript and in annotations
- Contains relevant information regarding loom's rendering system and conventions so content can be written properly, lists packages and dependencies used (like MathJax) that are relevant.

### Proposed dependency edges

**An agent can propose that one result depends on another, and the author decides.**

**Decided:**
- A proposed edge is a suggestion annotation whose proposed text is `\uses{…}`; no new kind of record is made.
- Loom never writes the edge into the author's source; the author applies the suggestion.

## Visual elements to be added or modified or deleted in this pass

**New:**
- The Chat view: the session item's view that replaces Discussion. From top to bottom it holds the transcript, the status line, the packet tray, and the input with its buttons. It is as wide as its pane, and it opens on the newest messages; scrolling up loads older ones.
- The status line. It is one line in the Chat view, above the tray, and states whether an agent is attached, what it is doing, and whether it failed to start.
- Run controls. A send button and a stop button, possibly more.
- The packet tray. It sits above the input and lists the new annotations the next message will carry. Each row links to its annotation and previews the exact text that will be sent.
- Annotations listed in sent messages, a message in the transcript includes a SUMMARIZED list of the annotations it carried, NEVER the full annotations (4 suggestions, 2 questions, 3 notes).
- Sending a packet alone. The send button works with an empty message when the tray holds something.
- Links in messages: an empty link shows the viewer name for the item, a link with text shows text. Clicking the link follows it into the unfocused pane when document not already open, otherwise it puts the relevant document in focus in the pane it is open in and goes to the specified location, showing a little mark initially and then fading. Links get hover previews. This link system is unified across all documents, there is not a separate link system for the transcript and for the drafting documents, its all the same link system so it is predictable and unified and simpler in code.

**Changed:**
- What it did becomes one chronological list of everything in `run.log`, opening at the bottom.
  - Each row shows a link to the annotation where there is one, the fixed name of what it concerns (`draft1.tex`, `sh-0009`) and its state
  - It replaces today's sections in SessionDid.svelte: the summary sentence, open, touched, settled, the report and the notation.
- Agent messages come from loom session say instead of thread.md's ## entries.
- The composer (`Composer.svelte`) moves from the Discussion view's foot to the Chat view's, beneath the tray, and spans its pane.
- Choosing a session in the picker opens its Chat instead of its Discussion.

**Removed:**
- The discussion view (`SessionDiscussion.svelte`), with:
  - its target chips and and N more;
  - its findings flow with coloured edges;
  - its "attached" line.
- The session item's discussion | What it did switch in the rail's control cluster is removed and replaced with "chat | what it did" switch
- The open session discussion link (GlobalRail.svelte:80) is removed

### The visual principles

Reading mode is measured against these. They came out of the work rather than preceding it, and each one has cost something to follow.

**P1 · Open on the thing itself.** The first screenful belongs to what the reader came for. What the application has to say *about* that thing goes to an edge or behind a control.

**P2 · Say it once, in the place that governs it.** Where two surfaces state the same fact, one is deleted rather than restyled, and the survivor is whichever one controls the fact.

**P3 · Claim only what is known.** Where the viewer does not know something it shows nothing rather than something plausible. A marker says the one thing that cannot be inferred and no more.

**P4 · Name the question. One element, one question.** Every element exists because a reader asks something at that moment. If the question cannot be named in one short sentence, the element goes; if two can be named, it is two elements; if two elements answer one question, one goes. Two riders: **a place is not an element** — a rail or a panel groups elements, and the test for a place is whether its elements' questions are asked at the same moment — and **the question is the reader's, not the system's**, which is what condemns a section reporting that a node is "in no document".

**P5 · Following a connection must not cost the thing you followed it from.** The viewer's subject is how texts relate; a relation has two terms; a viewer that holds one term can only show a relation by destroying the other.

**P6 · Show less rather than more by default.** Unless something has a good reason to be shown, don't show it. Corollaries: simpler is better, visual noise is BAD