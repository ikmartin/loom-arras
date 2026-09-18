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
  kind: "run" | "person" | "agent" | (string & {});
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
  when?: string;
  diff: string | null;
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
  target: { key: string; hash: string };
  kind: string;
  body_html: string;
  status: "open" | "resolved" | (string & {});
  in_reply_to: string | null;
  anchored: boolean;
  detached: boolean;
  quote?: string;
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

export interface ThreadMessage {
  author: Author;
  time: string;
  body_html: string;
}

export interface Attachment {
  name: string;
  kind: string;
  path?: string;
  count?: number;
}

/** One named section of a rendered report, and the findings inside it. */
export interface ReportBlock {
  name: string;
  title: string;
  findings?: string[];
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

export interface Thread {
  id: string;
  kind: string;
  title: string;
  created: string;
  participants: Author[];
  targets: string[];
  messages: ThreadMessage[];
  attachments: Attachment[];
  pipeline?: PipelineStep[];
  log: { time: string; command: string }[];
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

export interface Reference {
  citekey: string;
  slug?: string;
  bib: Record<string, string | number>;
  /** The work's global identifier, and every identifier it states. Local names are for authoring; these are what name the same work on another machine. */
  work?: string;
  works?: string[];
  /** What has been fetched for the work. `dir` is servable under the viewer's origin; both flags are false until someone fetches or adds a copy, and the fetched material is not in version control, so another reader's copy of the corpus may have neither. */
  artifacts?: { dir: string; pdf: boolean; source: boolean };
  digest: {
    file: string;
    fragment: string;
    source: string;
    extracted_from?: string;
    published_as?: string;
    method: string;
    nodes: string[];
  } | null;
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
  regions: Record<string, Region>;
  relations?: Relation[];
  edges: Edge[];
  inclusion: Record<string, InclusionNode>;
  states: States;
  annotations: Record<string, Annotation>;
  threads: Record<string, Thread>;
  diagnostics: Diagnostic[];
  tags: Record<string, string[]>;
  taxa: Record<string, Taxon>;
  references: Record<string, Reference>;
  macros: { default: Macro[]; sets: Record<string, Macro[]> };
  search: SearchEntry[];
}
