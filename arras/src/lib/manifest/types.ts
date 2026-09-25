// Types mirroring docs/specs/manifest.md (interface version 1). Field names are fixed by the spec; unknown fields are ignored by the viewer, so every interface here is open.

export const INTERFACE_VERSION = 1;
export const ACCEPTED_INTERFACE_VERSIONS: readonly number[] = [1];

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
  /** Who wrote it; where it belongs is the annotation's session. */
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
}

/** A landmark: a flat, self-contained copy of a document as it stood when loom recorded a step (book 17.1). It is a document, not a corpus of nodes: nothing in it has an identity. */
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
}

export interface NumberEntry {
  number: string;
  page?: number;
}

export interface Node {
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
  /** The files that each define this id, when two do. The id is then `conflicted`: it has no text, and loom reports both rather than choosing (book 5.3.5). */
  conflict?: string[];
  digest: string | null;
  locator?: string;
  incomplete: string[];
  state: string;
  derived: Record<string, boolean>;
}

export interface Cause {
  kind: string;
  id?: string;
  via?: string;
  citation?: string;
  when?: string;
  diff: string | null;
  comparison?: {
    accepted: string;
    current: string;
    accepted_macros: string;
    accepted_spans: [number, number][];
    current_spans: [number, number][];
  };
}

export interface IncomingChange {
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
  remote: string;
  branch: string;
  base: string;
  commit: string;
  observed: string;
  changes: IncomingChange[];
  files: { status: string; path: string; diff?: string }[];
  issues?: string[];
  prepared?: { patch: string; root: string; incoming: string; paths: string[] };
}

export interface UnresolvedReview {
  key: string;
  status: 'needs-review' | 'ok' | 'requires-attention';
  cause: 'incoming-pull' | 'earlier-change';
  pull: string;
  changed_text: boolean;
  /** Null means an older sync record has no post-pull baseline. */
  local_changed?: boolean | null;
  invalidated: boolean;
}

export interface Acceptance {
  author: string;
  date: string;
  fresh: boolean;
  causes?: Cause[];
}

export interface Reviews {
  latest_current: { author: Author; date: string } | null;
  latest_any: { author: Author; date: string } | null;
  open: Record<string, number>;
  detached: number;
}

export interface Key {
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
  reviews: Reviews;
  uses: string[];
  closure: string[];
  previous_key_match: string | null;
  /** The step whose recorded text this key's current text is, when it is one: what "text of @2" is built from (book 17.5). */
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

export interface Annotation {
  id: string;
  author: Author;
  created: string;
  /** What it is about. A key in the corpus -- or, for a note on a page of a cited work, the work's identifier, with `work` the citekey the viewer knows it by and `page` where on it (plan 0.13 item 2). */
  target: { key: string; hash: string; work?: string | null; page?: number | null };
  /** The document a claim about a node is read in, as a master path; null for the node wherever it appears. Drawn in that document, listed on the node's page, absent elsewhere. */
  in?: string | null;
  /** On a note on a page: `text` when the quotation is located in the page's committed text, `box` when a drawn rectangle is the record. */
  basis?: "text" | "box" | null;
  kind: string;
  body_html: string;
  status: "open" | "resolved" | (string & {});
  in_reply_to: string | null;
  /** Whether the text this was written against can still be produced: the current text, or a version the publisher kept. */
  recorded?: boolean;
  anchored: boolean;
  detached: boolean;
  quote?: string;
  /** Why it was withdrawn, when it was. The only record of why a finding should not have stood. */
  discard_reason?: string | null;
  /** How bad the fault is, not how strongly it is felt: `major` | `moderate` | `minor`. */
  severity?: string | null;
  /** Text the annotation proposes. Preview and copy only; nothing here applies it. */
  payload?: string | null;
  /** Where the payload would go relative to the anchor: `replace` | `after` | `before`. A hint, not an instruction. */
  placement?: string | null;
  /** The run or session this belongs to; the grouping key, since every annotation now lives in one log. */
  run: string;
  /** @deprecated Use `run`. Kept while publishers that wrote a file path are still in use. */
  record: string;
  discarded: boolean;
}

export interface Attachment {
  name: string;
  kind: string;
  path?: string;
  count?: number;
}

/** One named section of a rendered report, and the findings inside it. */
export interface Symbol {
  /** The TeX as the agent wrote it. */
  tex: string;
  means: string;
}

export interface ReportBlock {
  name: string;
  title: string;
  findings?: string[];
  /** Declared symbols, on a `notation` block. */
  symbols?: Symbol[];
}

/** One mode a run applied. Derived by the publisher from what the run wrote; a corpus whose publisher has no modes emits none. */
export interface PipelineStep {
  mode: string;
  target: string;
  /** The notes file, corpus-relative. */
  report: string;
  /** Present on a numbered re-run. */
  pass?: number;
  /** The rendered report fragment, when the publisher rendered one. */
  fragment?: string;
  blocks?: ReportBlock[];
}

/** A work an agent proposed citing and a person accepted: a breadcrumb, never a second source of identity truth. */
export interface ReferenceNote {
  work: string;
  for?: string[];
  claim?: string | null;
  identifier?: { verified: boolean; id?: string };
  accepted?: { when: string; who: string };
  from?: { session: string; annotation: string };
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
  /** Who is listening now, by a heartbeat that goes stale rather than being believed forever. Empty means nobody. */
  attached?: { who: string; kind: string }[];
  /** The last event in this session's inbox. A client that has fallen behind knows it has by comparing its own. */
  seq?: number;
}

export interface Thread {
  id: string;
  kind: "session" | (string & {});
  title: string;
  created: string;
  participants: Author[];
  targets: string[];
  attachments: Attachment[];
  pipeline?: PipelineStep[];
  log: { time: string; command: string; annotation?: string }[];
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
}

export interface Taxon {
  style: string;
  slug: string;
  count: number;
}

export interface ResultRecord {
  /** `proposed` (written, not yet vouched for) or `verified` (a person compared the rendering to the source text and accepted it). */
  state: string;
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

export interface Manifest {
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
  unresolved?: UnresolvedReview[];
  regions: Record<string, Region>;
  relations?: Relation[];
  edges: Edge[];
  inclusion: Record<string, InclusionNode>;
  states: States;
  annotations: Record<string, Annotation>;
  threads: Record<string, Thread>;
  /** Every session the index leaves standing, for the selector: which exists, which loom is writing into, and what round each is on. */
  sessions?: SessionRow[];
  reference_notes?: ReferenceNote[];
  diagnostics: Diagnostic[];
  tags: Record<string, string[]>;
  taxa: Record<string, Taxon>;
  references: Record<string, Reference>;
  /** Asserted relations between two results, each with a reason. Nobody verifies these and every surface that shows one says so: they are navigation, not mathematics, and are never citable and never in a closure. */
  links?: AssertedLink[];
  macros: { default: Macro[]; sets: Record<string, Macro[]> };
  search: SearchEntry[];
}
