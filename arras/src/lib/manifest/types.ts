// Types mirroring docs/specs/manifest.md (interface version 2). Field names are fixed by the spec; unknown fields are ignored by the viewer, so every interface here is open.

export const INTERFACE_VERSION = 2;
export const ACCEPTED_INTERFACE_VERSIONS: readonly number[] = [2];

export type Severity = "error" | "warning" | "info";
export type ColorClass =
  | "neutral"
  | "positive"
  | "positive-strong"
  | "warning"
  | "negative"
  | "info"
  | (string & {});

export interface Author {
  /** Who wrote it. */
  kind: "agent" | "person" | (string & {});
  id: string;
  label?: string;
}

export interface Publisher {
  name: string;
  version: string;
}

/** What a corpus has, never what to draw (manifest.md §1). A publisher declares it; `normalise` derives it from the data when a manifest omits it, so everything downstream reads it as present. */
export interface Publishes {
  documents: boolean;
  review: boolean;
  bibliography: boolean;
  discussions: boolean;
}

export interface Corpus {
  name: string;
  root_label: string;
  /** The file the viewer opens on when it remembers no place: `[quilt] home`, else the root README.md; null when there is neither. */
  home?: string | null;
  /** The project root's own directory name, which `files` is a view of; absent from an older publisher. */
  directory?: string;
}

/** An open file changed since the reviewer's look (plan 0.22.8). */
export interface FileChange {
  path: string;
  kind: "changed" | "new" | "gone" | (string & {});
  /** The unified diff, by its path under the build directory. */
  diff?: string;
  /** The file's hash as the publisher saw it, which a keep or an undo sends back as `seen`; null for a gone file. */
  hash?: string | null;
  /** How many changes (`@@` hunks) the diff holds, each kept or undone alone by its number from 0. */
  hunks?: number;
  /** The statements and proofs each change touches, by its number, in the file's order: what is drawn under a block in Your Changes; an empty list is text outside any block. */
  blocks?: string[][];
  /** The person's documents whose text this file is part of; empty for a file in none. */
  documents?: string[];
}

/** A file of the project the viewer shows, by its quilt-relative path (plan 0.22.7). */
export interface ProjectFile {
  path: string;
  /** What the viewer does with it: a LaTeX document (`document`) or another `.tex` file, a drawn or framed kind, text, or `other`, opened in its application. */
  kind: "document" | "tex" | "markdown" | "html" | "pdf" | "image" | "notebook" | "text" | "other" | (string & {});
  bytes: number;
  /** A Markdown file's or notebook's body as the publisher drew it, by its path under the build directory. */
  body?: string;
  /** What keeps agents from editing it: the deny list's entry as written, or a path loom always protects (`always`); null where agents edit it too, and absent from a publisher that does not say. */
  denied?: { by: string; always: boolean } | null;
}

/** A landmark: a flat, self-contained copy of a document as it stood when loom recorded a step. It is a document, not a corpus of nodes: nothing in it has an identity. */
export interface CanonDoc {
	path: string;
	stem: string;
	title: string;
	fragment: string;
	hash: string;
	/** The step that wrote it, `0002`, when the history knows; a file dropped into the canon directory by hand has none. */
	step?: string;
	name?: string;
	message?: string;
	when?: string;
	/** The macro set to typeset it with: a landmark renders with its own preamble's macros, whatever the drafting documents have since become. */
	macros?: string;
	/** The live document its step was about, where the history's moves have taken it; absent when no live document leads to it. */
	in?: string;
	/** The act it was kept at, besides recording one by hand: `adopt` or `sync` (before taking changes in), `keep` (an edit kept in Changes), `undo` (the text an undo set aside), `restore` (the text a restore replaced). Absent for a version the author recorded or imported. */
	kept_for?: 'adopt' | 'sync' | 'keep' | 'undo' | 'restore' | (string & {});
	/** The step's action: `import` for the paper as received, `stamp` for every other version. */
	action?: string;
	/** Why it cannot be put back into its document, in the person's words; '' when it can. */
	cannot_restore?: string;
}

/** One line of the history, as Review › The Record lists it: what was done, when, by whom, and to what. */
export interface HistoryAct {
	action: string;
	when: string;
	actor?: string;
	/** A step's number, for the acts that are steps. */
	step?: number;
	/** The file it was done to (a keep, an undo, a page written, a text put back). */
	path?: string;
	/** The files a whole keep took in. */
	paths?: string[];
	/** The document it concerns, as it is now named. */
	in?: string;
	/** A step's landmark: a `canon` entry's path. */
	landmark?: string;
	message?: string;
	hunks?: number[];
	kept_for?: string;
	copy?: string;
	page?: string;
	/** A text by its hash: what an undo or a put-back replaced (`from`) and wrote (`to`). */
	from?: string;
	to?: string;
	/** A version a restore put back, by its landmark's file name. */
	version?: string;
	/** The line of a box set in the viewer, and the state it was set to. */
	line?: number;
	done?: boolean;
}

/** One step of the history: an import, a stamp, an agent document's copy or an adoption. */
export interface HistoryStep {
	step: number;
	action: string;
	name: string;
	when: string;
	actor?: string;
	message?: string;
	/** The document the step concerns, as the ledger names it; absent for a stamp of the whole quilt. */
	document?: string;
	/** That document where it is now, when it is still live. */
	in?: string;
	/** The landmark the step kept, a `canon` entry's path. */
	landmark?: string;
}

export interface Master {
  path: string;
  title: string;
  default: boolean;
  fragment: string;
  engine?: string;
  compiled?: string;
  pdf?: string;
  numbering_known?: boolean;
  /** An agent document's source document, where the history's moves have taken it. */
  copy_of?: string;
  scope?: {kind: string; key?: string; title?: string; keys?: string[]};
  scope_keys?: string[];
  context_when?: string;
  context_changed?: boolean;
  context_only?: boolean;
  context_document?: string;
  closed?: boolean;
  closed_at?: string;
  closed_annotations?: Annotation[];
  closed_keys?: string[];
  macros?: string;
}

export interface NumberEntry {
  number: string;
  page?: number;
}

export interface Node {
  name?: string;
  /** An agent document's node: the plain key it corresponds to, `zk-0001` for `zk-0001-ai`. Whole-quilt views leave such nodes out. */
  derived_of?: string;
  draft_macros?: string;
  /** A derived node's base: the version of its plain key it began from, and that version's hash as `data-hash` takes it (`math`), so compare can tell a node changed on both sides. */
  base?: { key: string; step: number; hash: string; math?: string };
  id: string;
  kind: "environment" | "section" | "proof" | (string & {});
  /** Sections only: the sectioning depth, 1 for \section. A contents list stops at a chosen depth with it. */
  level?: number | null;
  taxon: string;
  style?: string;
  title?: string;
  aliases: string[];
  author?: string[];
  created?: string;
  tags: string[];
  file: string;
  src: [number, number];
  fragment: string;
  numbers: Record<string, NumberEntry>;
  reached_by: string[];
  parent: Record<string, string>;
  children: string[];
  proofs: string[];
  external: boolean;
  /** Why this block may be relied on; unclassified blocks need an author choice in the drafting source. */
  basis?: 'expository' | 'local-proof' | 'cited-result' | 'assumption' | 'open-claim' | 'unclassified';
  basis_reason?: string;
  inline_proof?: boolean;
  /** The files that each define this id, when two do. The id is then `conflicted`: it has no text, and loom reports both rather than choosing. */
  conflict?: string[];
  digest: string | null;
  locator?: string;
  incomplete: string[];
  state: string;
  derived: Record<string, boolean>;
}

export interface Cause {
  identity?: string;
  label?: string;
  owner?: string;
  kind: string;
  id?: string;
  via?: string;
  citation?: string;
  when?: string;
  diff: string | null;
  current_fragment?: string;
  current_macros?: string;
  comparison?: {
    accepted: string;
    current: string;
    current_macros?: string;
    accepted_macros: string;
    accepted_spans: [number, number][];
    current_spans: [number, number][];
  };
}

export interface IncomingChange {
  name?: string;
  category?: "prose";
  current?: string;
  proposed?: string;
  key: string;
  kind: 'edited' | 'added' | 'removed';
  local_changed: boolean;
  conflict: boolean;
  already_local: boolean;
  local: string | null;
  incoming: string | null;
  incoming_macros: string;
  affected: { key: string; citation: string | null }[];
}

export interface IncomingReview {
  workspace: string;
  branch: string;
  base: string;
  commit: string;
  observed: string;
  changes: IncomingChange[];
  files: { status: string; path: string; diff?: string }[];
  issues?: string[];
  prepared?: { patch: string; root: string; incoming: string; paths: string[] };
}

export interface AdoptionReview {
  kind: 'adopt';
  copy: string;
  source: string;
  label: string;
  fingerprint: string;
  /** Each result the copy changes: `class` is new, proposal-only, removed, separate-result, merged (both sides changed it and their edits fall apart line by line, `merged` the text), or conflict (their edits clash: shown, never offered). `proposed_key` is the copy's own key for it, which names it. */
  changes: {key: string; name: string | null; class: string; current: string; proposed: string; merged?: string; offered?: boolean; proposed_key?: string | null; math_changed: boolean; incoming_macros: string; local: string | null; incoming: string | null; documents: string[]; affected: {key: string; citation: string | null}[]}[];
  document_changed: boolean;
  document_conflict: boolean;
  document_diff: string;
  document_comparison?: {local: string | null; incoming: string | null; current: string; proposed: string; incoming_macros: string};
  scope?: {kind: string; title?: string};
  preamble_changed?: boolean;
  preamble_conflict?: boolean;
  preamble_current?: string;
  preamble_proposed?: string;
  choices: {keys: string[]; document: boolean; preamble?: boolean; kept?: string[]; revision?: number; invalidated?: string[]};
  issues: string[];
}

/** A block of the person's not freshly accepted: why it waits, and why loom cannot accept it, if it cannot. */
export interface UnresolvedReview {
  key: string;
  /** `earlier-change`: its acceptance went stale; `adopted` or `incoming-pull`: taken in; `never-accepted`: no acceptance yet. */
  cause: 'incoming-pull' | 'adopted' | 'earlier-change' | 'never-accepted';
  source_label?: string;
  contribution?: string;
  pull: string;
  changed_text: boolean;
  /** Null means an older sync record has no post-pull baseline. */
  local_changed?: boolean | null;
  /** Why loom cannot accept it, in the person's words; '' when it can. */
  refusal: string;
}

export interface Acceptance {
  author: string;
  date: string;
  fresh: boolean;
  causes?: Cause[];
}

export interface Reviews {
  /** Open annotations by type id. */
  open: Record<string, number>;
  detached: number;
}

export interface Key {
  review_fragment?: string;
  review_macros?: string;
  key: string;
  node: string;
  kind: "statement" | "proof" | (string & {});
  ordinal?: number;
  file: string;
  src: [number, number];
  hash: string;
  incomplete: string[];
  state: string;
  acceptance?: Acceptance;
  acceptances?: Acceptance[];
  reviews: Reviews;
  uses: string[];
  closure: string[];
  previous_key_match: string | null;
  /** The step whose recorded text this key's current text is, when it is one: what "text of @2" is built from. */
  version?: { step: string; name?: string };
  conflict?: string[];
}

export interface Region {
  key: string;
  container: string;
  in: string;
  label: string;
  numbers: Record<string, NumberEntry>;
  src: [number, number];
}

export interface Edge {
  from: string;
  to: string;
  kind: "statement" | "proof" | "prose" | (string & {});
  via: string;
  src?: { file: string; line: number };
}

/** A declared relation between two nodes that is not a dependency: it never enters a closure, a bundle, or a staleness computation (specs/manifest.md §16). */
export interface Relation {
  kind: "see" | (string & {});
  from: string;
  to: string;
}

export interface InclusionNode {
  key: string;
  via?: string;
  file?: string;
  shift?: number;
  children: InclusionNode[];
}

export interface StateLabel {
  label: string;
  color: ColorClass;
  modifier?: boolean;
}

export interface States {
  labels: Record<string, StateLabel>;
  derived: Record<string, StateLabel>;
}

/** How an annotation is drawn: one of the nine colours, a style, a thickness in whole pixels and an opacity in percent. */
export interface Look {
  color: string;
  style: 'underline' | 'highlight' | 'strike';
  weight: number;
  opacity: number;
}

/** A type an annotation may carry: a label with a look, whether its annotations stay open until resolved, whether they are listed in Notes, and instructions for agents. */
export interface AnnotationType {
  id: string;
  name: string;
  look: Look;
  open: boolean;
  notes: boolean;
  instructions: string;
  /** The modes whose text names this type. */
  modes?: string[];
}

export interface Annotation {
  id: string;
  author: Author;
  created: string;
  /** What it is about: a key in the corpus; a cited work's identifier, with `work` the citekey the viewer knows it by and `page` the page it is on, none for the whole work (plan 0.13 item 2); or a project PDF, with `file` its path and `page`. */
  target: { key: string; hash: string; work?: string | null; page?: number | null; file?: string | null };
  /** The document a claim about a node is read in, as a master path; null for the node wherever it appears. Drawn in that document, listed on the node's page, absent elsewhere. */
  in?: string | null;
  /** On a cited work's page, anchored through its store: `text` when the quotation is located in the page's committed text, `box` when a drawn rectangle is the record. Null for one that records its own place (`rects`). */
  basis?: "text" | "box" | null;
  /** On a PDF page, where it stands now, in points from the page's top left: its words found again on a changed file. */
  rects?: number[][] | null;
  /** A drawing's points, x, y, x, y… per stroke, in points from the page's top left. */
  strokes?: number[][] | null;
  /** The tool it was drawn with: `pin`, `ink`, `text`, `box`, `oval` or `arrow`; null for one on words, which its look's style draws. */
  mark?: string | null;
  /** Where one taken in from a PDF's own annotations came from. */
  origin?: { by?: string; subtype?: string; color?: number[]; ref?: string; sha?: string } | null;
  /** The reference of the PDF's own annotation it stands for, while the file is the one it was taken from: the viewer leaves that one undrawn. */
  hides?: string | null;
  /** The id of one of the quilt's `annotation_types`, or null for an untyped annotation. A type deleted since leaves an id no type has. */
  type: string | null;
  /** The whole look to draw it with, whatever its type now says. */
  look: Look;
  body_html: string;
  status: "open" | "resolved";
  in_reply_to: string | null;
  /** Whether the text this was written against can still be produced: the current text, or a version the publisher kept. */
  recorded?: boolean;
  anchored: boolean;
  detached: boolean;
  quote?: string;
  /** Replacement text the annotation proposes, which the author applies; '' with `replace` deletes the quoted words. */
  payload?: string | null;
  /** The payload as the publisher's converter renders it, in the context of the result it is on; null when it could not be, and then the TeX is read as prose. */
  payload_html?: string | null;
  /** Where the payload goes: `replace` takes exactly the quoted words' place, `after` and `before` go right beside them; with no quote, of the key's body. */
  placement?: string | null;
  /** An open suggestion's key as it would read with the suggestion taken: `ready` with that rendering, its changed words marked, and the patch, both paths under the build directory, and whether the key has changed since though its quote stands; `taken` when the key already reads so; `unplaced` with why the payload has no place. */
  change?: { state: 'ready'; fragment: string; diff: string; moved: boolean } | { state: 'taken' } | { state: 'unplaced'; why: string };
  /** Why it was resolved, when it was. */
  resolved_why?: string | null;
  /** A suggestion resolved as applied: its key's hash once the suggestion was taken. */
  applied?: { hash: string } | null;
}

export interface Attachment {
  name: string;
  kind: string;
  path?: string;
  count?: number;
}

/** One session as the selector shows it. The id is the address and never changes; the title is the author's and may. */
export interface SessionRow {
  id: string;
  title: string;
  /** What the sitting is for, in the author's words; '' when never stated. */
  purpose?: string;
  /** `open`, `closed`, or `deleted` — a tombstone, which the publisher does not send. */
  state: "open" | "closed" | (string & {});
  created: string;
  /** When the current round opened: what "changed since last time" is measured from. */
  opened: string;
  rounds: number;
  /** Whether this is the publisher's own default for writes made at a terminal. The viewer never reads it: a write names its session (plan 0.13.1). */
  active: boolean;
  /** The last event in this session's inbox. A client that has fallen behind knows it has by comparing its own. */
  seq?: number;
  /** When it was last written in: the newest of its logged commands, its annotations and notes, and its transcript's last message; '' when nothing was. */
  last?: string;
}

export interface Thread {
  id: string;
  kind: "session" | (string & {});
  title: string;
  created: string;
  participants: Author[];
  targets: string[];
  attachments: Attachment[];
  /** The session's command log, a line each: what was run, and the keys and files it names, a moved document under where it is now. */
  log: { time: string; command: string; names?: ({ key: string } | { path: string })[] }[];
  discarded: boolean;
}

export interface Location {
  file: string;
  line: number;
  column?: number;
}

/** A command that would resolve a diagnostic, offered to be copied. Nothing in the viewer runs anything. */
export interface Fix {
  label: string;
  command: string;
  /** A fix a viewer may do itself: the write-API endpoint and the body to send it. Without one, the fix is a command to copy. */
  act?: { endpoint: string; body: Record<string, unknown> };
}

export interface Diagnostic {
  severity: Severity;
  code: string;
  message: string;
  locations: Location[];
  keys: string[];
  fixes?: Fix[];
  /** What the diagnostic is about: the source, or loom's own record of it. Absent means `source`. */
  subject?: "source" | "record" | (string & {});
  /** Whose it is to fix: the person's, an agent's copy's, or a cited work's, whose digest loom wrote. Absent means the person's. */
  owner?: "person" | "copy" | "work" | (string & {});
}

export interface Taxon {
  style: string;
  slug: string;
  count: number;
}

export interface ResultRecord {
  /** `proposed` (written, not yet vouched for), `extracted` (loom's own reading of the paper's source, which nobody has vouched for), `verified` (a person compared the rendering to the source text and accepted it) or `discarded`. */
  state: 'proposed' | 'extracted' | 'verified' | 'discarded' | (string & {});
  level: number;
  /** `mechanical` (parsed from a source), `anchored` (read from a page, re-checkable) or `declared` (no check available). */
  class: string;
  /** The page the statement was read from; 0 for a result parsed out of LaTeX. */
  page: number;
  /** The first twelve characters of the artifact's sha256, which is what the anchor names. */
  artifact: string;
  /** Every party who made or changed this result, in order. A record that credits an agent with a sentence a person wrote cannot be audited. */
  origin: { act: string; by: string; when: string }[];
  /** The page's own words, verbatim. Present for every result read off a page, verified or not: it is what a link's two endpoints are judged against by eye. Absent for a mechanically extracted result, whose source is its own LaTeX. */
  source_text?: string;
  /** The same result rendered as LaTeX, which is never claimed to be verbatim. Present for a proposal. */
  statement?: string;
  /** The page around the quoted span, for a proposal: what the rendering is judged against. The quote alone is not enough -- an agent quotes only as much as the anchor check needs. */
  page_text?: string;
  /** Words of `statement`'s prose that the quoted source text does not contain: an agent's gloss, or a word the page spells differently. */
  not_on_page?: string[];
  /** For a result quoted from the paper's LaTeX rather than a page: the file, relative to the corpus root. `page` is then 0. */
  source_file?: string;
  /** A proposal's local name (`thm-4.1`) and environment, which the author may correct when verifying. */
  local?: string;
  taxon?: string;
  supersedes?: string;
  /** On an extracted result whose digest was read off another version than the bibliography cites: the artifact extracted ('' when the digest does not say) and what the bibliography cites, a `work:` identifier when the entry states none. Its numbers and pages are the other version's. */
  version?: { extracted_from: string; cited: string };
}

/** A page loom keeps for one thing, the research state or a work's overview (plan 0.21.3): a reading, never a source. */
export interface Page {
  path: string;
  hash: string;
  body_html: string;
  /** Who last wrote it through loom, and when; absent when nobody has. */
  by?: { kind: "agent" | "person" | (string & {}); id: string };
  when?: string;
  /** Changed by hand since the last write through loom, or never written through it. */
  edited_since: boolean;
  links: { broken: { href: string; why: string }[]; moved: { href: string; key: string }[] };
}

export interface Reference {
  citekey: string;
  slug?: string;
  bib: Record<string, string | number>;
  /** The work's global identifier, and every identifier it states. Local names are for authoring; these are what name the same work on another machine. */
  work?: string;
  works?: string[];
  /** What has been fetched for the work. `dir` is servable under the viewer's origin; both flags are false until someone fetches or adds a copy, and the fetched material is not in version control, so another reader's copy of the corpus may have neither. */
  artifacts?: { dir: string; pdf: boolean; source: boolean };
  /** The author's standing claim that no document can be held for this work: the Stacks Project is a living work with no fixed version. Nothing in a bibliography entry says so, so it is declared and never inferred, and the reading view says it rather than showing an empty pane. */
  unreadable?: { why: string; who: string; when: string };
  /** When and by whom the person added this work to the library by hand (plan 0.24.2); absent for a work a document's bibliography brought. */
  added?: { when: string; who: string };
  /** The entry as a person pastes it into a `.bib`: its type and its bibliographic fields, never the publisher's own. */
  bibtex?: string;
  /** The work's overview, a reading an agent or the person wrote (plan 0.21.3); absent until one is. */
  overview?: Page;
  /** Where the work's anchor geometry is published, and its hash. Beside the manifest rather than in it: the manifest is loaded whole on every poll, and rectangles are wanted for the one paper being read. Absent when no copy of the paper is on the publishing machine, which is the honest state — the viewer then has nothing to draw. */
  spans?: { path: string; sha256: string };
  /** The notes on this work's pages: how many, and how many still await an answer. They are in no key's row and count toward no total, so this is where a list says a paper has been read. */
  reading?: { total: number; open: number };
  digest: {
    file: string;
    fragment: string;
    source: string;
    extracted_from?: string;
    published_as?: string;
    method: string;
    nodes: string[];
  } | null;
  /** Proposals: results read off a page and rendered by an agent, which nobody has vouched for yet. They live in a file no bundle inputs, so nothing here can be cited or compiled until it is verified. */
  proposed?: { file: string; fragment: string; nodes: string[] } | null;
  /** What is recorded for each of the work's results (digest contract §9). Both texts travel only for a proposal, because that is the one claim a person is being asked to make. */
  results?: Record<string, ResultRecord>;
  version_mismatch: boolean;
  cited_by: string[];
  /** On a work with several documents, its other versions: each a bibliography entry of its own, filed beside the first document, with its identifier and what the store holds for it. Absent on a work with one document. */
  versions?: { citekey: string; work: string; artifacts: { dir: string; pdf: boolean; source: boolean } }[];
  /** On a version, the citekey of the work it is another document of; that work's reference lists it under `versions`. */
  version_of?: string;
  /** Identifiers a lookup proposed for a work whose entry states none. Unconfirmed: never the work's identity, which changes only when the bibliography states it. */
  candidates?: { id: string; source: string; confidence: number; strength: 'strong' | 'possible' | (string & {}); title: string }[];
}

export interface Macro {
  name: string;
  args: number;
  body: string;
}

export interface SearchEntry {
  key: string;
  title: string;
  taxon?: string;
  kind?: string;
  aliases?: string[];
  tags?: string[];
  excerpt?: string;
}

export interface AssertedLink {
  id: string;
  from: string;
  to: string;
  /** `same-notion`, `generalises`, `specialises`, `depends-on` or `contradicts`. A closed vocabulary: a viewer can only draw what it can name. */
  kind: string;
  /** Why, in a sentence or two. Never optional: an unexplained edge is noise. */
  why: string;
  by?: string;
  when?: string;
}

/** An agent app with a file in the quilt that starts loom's server, and whether it does. */
export interface AgentClient {
  key: string;
  label: string;
  file: string;
  set_up: boolean;
  /** What a person runs to set it up, from the publisher; empty when it is set up. */
  command: string;
}

/** What the quilt's configuration holds and what follows from it, for Settings (plan 0.23). */
export interface QuiltSettings {
  /** The `table.key` names Settings may change, and the ones it only shows. */
  editable: string[];
  read_only: string[];
  quilt: { name: string; main: string; home: string; prefix: string; engine: string; history: string; research_state: string };
  library: { online: boolean; contact: string };
  /** `codes`: every diagnostic code that can be silenced. */
  lint: { disable: string[]; codes: string[] };
  agents: {
    deny: string[];
    protected: string[];
    /** Whether the quilt has an agent layer, and how its agents reach loom. */
    layer: boolean;
    variant: 'mcp' | 'shell' | null;
    /** Whether Claude Code's permission file lags the deny list. */
    stale: boolean;
    command: string;
    clients: AgentClient[];
  };
  sync: { paired: true; directory: string; workspace: string; branch: string; documents: string[] } | { paired: false; command: string };
  warnings: string[];
}

export interface Manifest {
  reviewer?: { name: string; source: string };
  interface_version: number;
  publisher: Publisher;
  publishes: Publishes;
  generated: string;
  corpus: Corpus;
  masters: Master[];
  canon?: CanonDoc[];
  nodes: Record<string, Node>;
  keys: Record<string, Key>;
  /** Fetched source waiting for incorporation; never changes a key's recorded state. */
  incoming?: IncomingReview;
  contributions?: (AdoptionReview | (IncomingReview & {kind: 'workspace'; label: string}))[];
  unresolved?: UnresolvedReview[];
  history?: { steps: HistoryStep[]; acts?: HistoryAct[] };
  regions: Record<string, Region>;
  relations?: Relation[];
  edges: Edge[];
  inclusion: Record<string, InclusionNode>;
  states: States;
  annotations: Record<string, Annotation>;
  /** The quilt's annotation types, in its file's order (specs/manifest.md §1). */
  annotation_types?: AnnotationType[];
  threads: Record<string, Thread>;
  /** Every session the index leaves standing, for the selector: which exists, which loom is writing into, and what round each is on. */
  sessions?: SessionRow[];
  diagnostics: Diagnostic[];
  tags: Record<string, string[]>;
  taxa: Record<string, Taxon>;
  references: Record<string, Reference>;
  /** The quilt's research state (plan 0.21.3); absent until one is written. */
  research_state?: Page;
  /** Every file of the project the viewer shows, hidden ones left out (plan 0.22.7); absent from an older publisher. */
  files?: ProjectFile[];
  /** The open files changed since the reviewer's look, and that look; absent before a first look. */
  changes?: FileChange[];
  changes_since?: { who: string; when: string };
  /** The quilt's configuration, for Settings; absent from an older publisher. */
  config?: QuiltSettings;
  /** Asserted relations between two results, each with a reason. Nobody verifies these and every surface that shows one says so: they are navigation, not mathematics, and are never citable and never in a closure. */
  links?: AssertedLink[];
  macros: { default: Macro[]; sets: Record<string, Macro[]> };
  search: SearchEntry[];
}

export interface IncorporationMathItem {
  key: string;
  dependencies?: string[];
  name: string;
  reason: string;
  local: {path: string; macros: Macro[]} | null;
  proposed: {path: string; macros: Macro[]};
  unavailable: string;
}
export interface IncorporationMathReview {
  token: string;
  reviewer: string;
  items: IncorporationMathItem[];
}
export interface IncorporationOutcome {
  accepted?: string[];
  pending?: string[];
  acceptance_error?: string;
}
