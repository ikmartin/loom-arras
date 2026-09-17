// The dependency graph as a layered drawing (book 10.2.7): ELK lays out statement nodes grouped by section; edges keep their kind so the drawing can dash proof-edges and dot prose-edges.
import type { Manifest, Node } from "$lib/manifest/types";
import { bibText } from "$lib/works";

export interface GNode {
  id: string;
  label: string;
  taxon: string;
  state: string;
  color: string;
  style: string;
  external: boolean;
  section: boolean;
  x: number;
  y: number;
  w: number;
  h: number;
  group?: string;
}

export interface GEdge {
  from: string;
  to: string;
  kind: string;
  points: { x: number; y: number }[];
  /** For an edge into a paper drawn as one node: how many of its results the edge stands for. */
  count?: number;
}

export interface Layout {
  nodes: GNode[];
  groups: {
    id: string;
    label: string;
    x: number;
    y: number;
    w: number;
    h: number;
  }[];
  edges: GEdge[];
  width: number;
  height: number;
}

export interface Filters {
  master?: string;
  taxon?: string;
  tag?: string;
  /** Which cited results to draw. `reached` is the default: everything this corpus wrote, plus the external nodes it actually depends on. A digest holds a whole paper, so `all` is mostly other people's theorems. `papers` draws each cited work as one node instead of its results (15.5.2). */
  external?: "reached" | "all" | "none" | "papers";
  reached?: Set<string>;
}

/** The id a cited work is drawn under when results are contracted to papers; `paper:` cannot collide with a node id, which never holds a colon. */
export const PAPER = "paper:";

export function graphInput(m: Manifest, f: Filters): { nodes: Node[]; edges: { from: string; to: string; kind: string; count?: number }[] } {
  const passes = (n: Node) => {
    if (f.master && !n.reached_by.includes(f.master) && !n.external)
      return false;
    if (f.taxon && n.taxon !== f.taxon) return false;
    if (f.tag && !n.tags.includes(f.tag)) return false;
    if (n.external) {
      if (f.external === "none" || f.external === "papers") return false;
      if (
        (f.external ?? "reached") === "reached" &&
        !(f.reached?.has(n.id) ?? false)
      )
        return false;
    }
    return true;
  };
  const stmtOf = (key: string) => m.keys[key]?.node ?? key;
  // A section is a container, not a result, so it is not drawn — unless something depends on it by name, in which case dropping it would silently delete the edge as well. Sections that are an endpoint are kept and drawn as containers.
  const endpoints = new Set<string>();
  for (const e of m.edges) {
    endpoints.add(stmtOf(e.from));
    endpoints.add(stmtOf(e.to));
  }
  const nodes = Object.values(m.nodes).filter((n) => {
    if (n.kind === "section" && !endpoints.has(n.id)) return false;
    return passes(n);
  });
  const ids = new Set(nodes.map((n) => n.id));
  const edges = m.edges
    .map((e) => ({ from: stmtOf(e.from), to: stmtOf(e.to), kind: e.kind }))
    .filter((e) => ids.has(e.from) && ids.has(e.to) && e.from !== e.to);
  const seen = new Set<string>();
  const unique = edges.filter((e) => {
    const k = `${e.from}>${e.to}>${e.kind}`;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
  if (f.external !== "papers") return { nodes, edges: unique };
  return contractToPapers(m, nodes, unique, stmtOf);
}

/** The citekey whose digest a node belongs to: its `digest` for a result, and the digest file it sits in for a section of that file, which the manifest does not mark external. */
function sourceOf(m: Manifest): (id: string) => string | null {
  const byFile = new Map<string, string>();
  for (const r of Object.values(m.references)) if (r.digest?.file) byFile.set(r.digest.file, r.citekey);
  return (id: string) => {
    const n = m.nodes[id];
    if (!n) return null;
    if (n.external && n.digest) return n.digest;
    return byFile.get(n.file) ?? null;
  };
}

/**
 * The work graph (15.5.2): the corpus's own results as they are, and every cited work as one node.
 *
 * It is the result graph's quotient by source, taken over external nodes only. An edge runs from an own result to a paper when the result depends on any of the paper's digested results — counting how many — or cites the paper at all; an edge runs between two papers when a result in one digest depends on a result in another. A work cited but never digested appears too, from the references' `cited_by`, which the expanded graph cannot show. Nothing beyond the manifest is needed: a node's source is its `digest`.
 */
function contractToPapers(
  m: Manifest,
  nodes: Node[],
  own: { from: string; to: string; kind: string }[],
  stmtOf: (key: string) => string,
) {
  const paperOf = sourceOf(m);
  // a digest's own sections are part of the paper too, though not marked external, so they are contracted with it
  nodes = nodes.filter((n) => !paperOf(n.id));
  const shown = new Set(nodes.map((n) => n.id));
  const agg = new Map<string, { from: string; to: string; kind: string; results: Set<string> }>();
  const add = (from: string, to: string, kind: string, result: string) => {
    const k = `${from}>${to}`;
    const e = agg.get(k) ?? agg.set(k, { from, to, kind, results: new Set() }).get(k)!;
    e.results.add(result);
  };
  for (const e of m.edges) {
    const a = stmtOf(e.from);
    const b = stmtOf(e.to);
    const pa = paperOf(a);
    const pb = paperOf(b);
    if (!pa && pb && shown.has(a)) add(a, PAPER + pb, e.kind, b);
    else if (pa && pb && pa !== pb) add(PAPER + pa, PAPER + pb, e.kind, b);
  }
  for (const r of Object.values(m.references)) {
    for (const c of r.cited_by) {
      const a = stmtOf(c);
      if (shown.has(a) && !paperOf(a) && !agg.has(`${a}>${PAPER}${r.citekey}`)) add(a, PAPER + r.citekey, "cites", "");
    }
  }
  const papers = new Set<string>();
  for (const e of agg.values()) for (const end of [e.from, e.to]) if (end.startsWith(PAPER)) papers.add(end.slice(PAPER.length));
  const paperNodes = [...papers].sort().map((ck) => {
    const ref = m.references[ck];
    const title = bibText(ref?.bib.title) || ck;
    return {
      id: PAPER + ck,
      kind: "work",
      taxon: "Paper",
      style: "paper",
      title: title.length > 30 ? title.slice(0, 29) + "…" : title,
      aliases: [],
      tags: [],
      file: "",
      src: [0, 0],
      fragment: "",
      numbers: {},
      reached_by: [],
      parent: {},
      children: [],
      proofs: [],
      external: true,
      digest: ref?.digest ? ck : null,
      incomplete: [],
      state: "",
      derived: {},
    } as Node;
  });
  const edges = [
    ...own.filter((e) => shown.has(e.from) && shown.has(e.to)),
    ...[...agg.values()].map((e) => ({ from: e.from, to: e.to, kind: e.kind, count: Math.max(1, [...e.results].filter(Boolean).length) })),
  ];
  return { nodes: [...nodes, ...paperNodes], edges };
}

export function colorOf(m: Manifest, state: string): string {
  return m.states.labels[state]?.color ?? "neutral";
}

export function downstream(m: Manifest, id: string): Set<string> {
  const stmtOf = (key: string) => m.keys[key]?.node ?? key;
  const rev = new Map<string, string[]>();
  for (const e of m.edges) {
    const a = stmtOf(e.from);
    const b = stmtOf(e.to);
    if (!rev.has(b)) rev.set(b, []);
    rev.get(b)!.push(a);
  }
  const out = new Set<string>();
  const stack = [id];
  while (stack.length) {
    const cur = stack.pop()!;
    for (const nxt of rev.get(cur) ?? []) {
      if (!out.has(nxt) && nxt !== id) {
        out.add(nxt);
        stack.push(nxt);
      }
    }
  }
  return out;
}

export function closureOf(m: Manifest, id: string): Set<string> {
  return new Set(m.keys[id]?.closure.filter((k) => k !== id) ?? []);
}

type ElkNode = {
  id: string;
  width?: number;
  height?: number;
  children?: ElkNode[];
  labels?: { text: string }[];
  x?: number;
  y?: number;
  layoutOptions?: Record<string, string>;
  edges?: ElkEdge[];
};
type ElkEdge = {
  id: string;
  sources: string[];
  targets: string[];
  sections?: {
    id: string;
    startPoint: { x: number; y: number };
    endPoint: { x: number; y: number };
    bendPoints?: { x: number; y: number }[];
  }[];
};

/**
 * Lay the filtered graph out in layers with ELK, dependencies above what uses them, statements grouped by the section that holds them.
 *
 * Every coordinate ELK returns is asked for in the root's frame (`elk.json.shapeCoords` and `elk.json.edgeCoords`). By default a node is placed relative to its group and an edge relative to the lowest common ancestor of its endpoints, while the edge is still listed at the root; reading such an edge as if it were at the root is what drew grouped edges away from the nodes they join. A section that is both a group and an endpoint is drawn once, as the group, and an edge from a node to the section that contains it is left out, since ELK cannot route an edge into its own ancestor.
 */
export async function layout(m: Manifest, f: Filters): Promise<Layout> {
  const { nodes, edges } = graphInput(m, f);
  const master =
    f.master ??
    m.masters.find((x) => x.default)?.path ??
    m.masters[0]?.path ??
    "";
  const W = 150;
  const H = 34;
  const drawn = new Set(nodes.map((n) => n.id));
  const groupOf = new Map<string, string>();
  for (const n of nodes) {
    const parent = n.parent[master];
    if (parent && parent !== n.id && m.nodes[parent]) groupOf.set(n.id, parent);
  }
  const groupIds = new Set(groupOf.values());
  const groups = new Map<string, ElkNode>();
  const roots: ElkNode[] = [];
  const groupNode = (id: string): ElkNode => {
    let g = groups.get(id);
    if (!g) {
      g = {
        id,
        children: [],
        layoutOptions: { "elk.padding": "[top=28,left=12,bottom=12,right=12]" },
      };
      groups.set(id, g);
      roots.push(g);
    }
    return g;
  };
  for (const n of nodes) {
    // a section that holds drawn nodes is its group; drawing it a second time as a node inside or beside that group would give one key two boxes
    if (groupIds.has(n.id)) {
      groupNode(n.id);
      continue;
    }
    const child: ElkNode = { id: n.id, width: W, height: H };
    const parent = groupOf.get(n.id);
    if (parent) groupNode(parent).children!.push(child);
    else roots.push(child);
  }
  const inside = (id: string, ancestor: string) => groupOf.get(id) === ancestor;
  const routed = edges
    .map((e, i) => ({ e, i }))
    .filter(({ e }) => !inside(e.from, e.to) && !inside(e.to, e.from) && (drawn.has(e.from) || groups.has(e.from)) && (drawn.has(e.to) || groups.has(e.to)));
  // ELK puts a source above its target, and upstream belongs above (15.5), so each edge is laid out from the dependency to what uses it
  const elkEdges: ElkEdge[] = routed.map(({ e, i }) => ({ id: "e" + i, sources: [e.to], targets: [e.from] }));
  const { default: ELK } = await import("elkjs/lib/elk.bundled.js");
  const elk = new ELK();
  const graph = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "DOWN",
      "elk.hierarchyHandling": "INCLUDE_CHILDREN",
      "elk.layered.spacing.nodeNodeBetweenLayers": "40",
      "elk.spacing.nodeNode": "24",
      "elk.json.shapeCoords": "ROOT",
      "elk.json.edgeCoords": "ROOT",
    },
    children: roots,
    edges: elkEdges,
  };
  const laid = (await elk.layout(graph)) as ElkNode & {
    edges?: ElkEdge[];
    width?: number;
    height?: number;
  };
  const out: Layout = {
    nodes: [],
    groups: [],
    edges: [],
    width: laid.width ?? 800,
    height: laid.height ?? 600,
  };
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const box = new Map<string, { x: number; y: number; w: number; h: number }>();
  const walk = (list: ElkNode[]) => {
    for (const c of list) {
      const b = { x: c.x ?? 0, y: c.y ?? 0, w: c.width ?? W, h: c.height ?? H };
      box.set(c.id, b);
      if (groups.has(c.id)) {
        out.groups.push({ id: c.id, label: m.nodes[c.id]?.title ?? c.id, ...b });
        walk(c.children ?? []);
      } else {
        const n = byId.get(c.id)!;
        out.nodes.push({
          id: n.id,
          label: n.kind === "work" ? (n.title ?? n.id) : n.id,
          taxon: n.taxon,
          state: n.state,
          color: colorOf(m, n.state),
          style: n.style ?? "plain",
          external: n.external,
          section: n.kind === "section",
          ...b,
          group: groupOf.get(n.id),
        });
      }
    }
  };
  walk(laid.children ?? []);
  for (const e of laid.edges ?? []) {
    const src = edges[Number(e.id.slice(1))];
    if (!src) continue;
    const pts: { x: number; y: number }[] = [];
    for (const s of e.sections ?? [])
      for (const p of [s.startPoint, ...(s.bendPoints ?? []), s.endPoint]) pts.push({ x: p.x, y: p.y });
    if (!pts.length) {
      const a = box.get(src.to);
      const b = box.get(src.from);
      if (a && b) pts.push({ x: a.x + a.w / 2, y: a.y + a.h }, { x: b.x + b.w / 2, y: b.y });
    }
    out.edges.push({ from: src.from, to: src.to, kind: src.kind, points: pts, count: src.count });
  }
  return out;
}
