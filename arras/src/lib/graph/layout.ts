// The dependency graph as a layered drawing (book 10.2.7): ELK lays out statement nodes grouped by section; edges keep their kind so the drawing can dash proof-edges and dot prose-edges.
import type { Manifest } from '$lib/manifest/types';

export interface GNode {
	id: string;
	label: string;
	taxon: string;
	state: string;
	color: string;
	style: string;
	external: boolean;
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
}

export interface Layout {
	nodes: GNode[];
	groups: { id: string; label: string; x: number; y: number; w: number; h: number }[];
	edges: GEdge[];
	width: number;
	height: number;
}

export interface Filters {
	master?: string;
	taxon?: string;
	tag?: string;
	hideExternal?: boolean;
}

export function graphInput(m: Manifest, f: Filters) {
	const nodes = Object.values(m.nodes).filter((n) => {
		if (n.kind === 'section') return false;
		if (f.master && !n.reached_by.includes(f.master) && !n.external) return false;
		if (f.taxon && n.taxon !== f.taxon) return false;
		if (f.tag && !n.tags.includes(f.tag)) return false;
		if (f.hideExternal && n.external) return false;
		return true;
	});
	const ids = new Set(nodes.map((n) => n.id));
	const stmtOf = (key: string) => m.keys[key]?.node ?? key;
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
	return { nodes, edges: unique };
}

export function colorOf(m: Manifest, state: string): string {
	return m.states.labels[state]?.color ?? 'neutral';
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

type ElkNode = { id: string; width?: number; height?: number; children?: ElkNode[]; labels?: { text: string }[]; x?: number; y?: number; layoutOptions?: Record<string, string> };
type ElkEdge = { id: string; sources: string[]; targets: string[]; sections?: { startPoint: { x: number; y: number }; endPoint: { x: number; y: number }; bendPoints?: { x: number; y: number }[] }[] };

export async function layout(m: Manifest, f: Filters): Promise<Layout> {
	const { nodes, edges } = graphInput(m, f);
	const master = f.master ?? m.masters.find((x) => x.default)?.path ?? m.masters[0]?.path ?? '';
	const groups = new Map<string, ElkNode>();
	const roots: ElkNode[] = [];
	const W = 150;
	const H = 34;
	for (const n of nodes) {
		const child: ElkNode = { id: n.id, width: W, height: H, labels: [{ text: n.id }] };
		const parent = n.parent[master];
		if (parent && m.nodes[parent]) {
			let g = groups.get(parent);
			if (!g) {
				g = { id: 'g:' + parent, children: [], layoutOptions: { 'elk.padding': '[top=28,left=12,bottom=12,right=12]' } };
				groups.set(parent, g);
				roots.push(g);
			}
			g.children!.push(child);
		} else {
			roots.push(child);
		}
	}
	const elkEdges: ElkEdge[] = edges.map((e, i) => ({ id: 'e' + i, sources: [e.from], targets: [e.to] }));
	const { default: ELK } = await import('elkjs/lib/elk.bundled.js');
	const elk = new ELK();
	const graph = {
		id: 'root',
		layoutOptions: { 'elk.algorithm': 'layered', 'elk.direction': 'DOWN', 'elk.hierarchyHandling': 'INCLUDE_CHILDREN', 'elk.layered.spacing.nodeNodeBetweenLayers': '40', 'elk.spacing.nodeNode': '24' },
		children: roots,
		edges: elkEdges
	};
	const laid = (await elk.layout(graph)) as ElkNode & { edges?: ElkEdge[]; width?: number; height?: number };
	const out: Layout = { nodes: [], groups: [], edges: [], width: laid.width ?? 800, height: laid.height ?? 600 };
	const byId = new Map(nodes.map((n) => [n.id, n]));
	const walk = (list: ElkNode[], ox: number, oy: number) => {
		for (const c of list) {
			const x = ox + (c.x ?? 0);
			const y = oy + (c.y ?? 0);
			if (c.id.startsWith('g:')) {
				const key = c.id.slice(2);
				out.groups.push({ id: key, label: m.nodes[key]?.title ?? key, x, y, w: c.width ?? 0, h: c.height ?? 0 });
				walk(c.children ?? [], x, y);
			} else {
				const n = byId.get(c.id)!;
				out.nodes.push({ id: n.id, label: n.id, taxon: n.taxon, state: n.state, color: colorOf(m, n.state), style: n.style ?? 'plain', external: n.external, x, y, w: c.width ?? W, h: c.height ?? H, group: undefined });
			}
		}
	};
	walk(laid.children ?? [], 0, 0);
	const abs = new Map<string, { x: number; y: number }>();
	const collect = (list: ElkNode[], ox: number, oy: number) => {
		for (const c of list) {
			abs.set(c.id, { x: ox + (c.x ?? 0), y: oy + (c.y ?? 0) });
			if (c.children) collect(c.children, ox + (c.x ?? 0), oy + (c.y ?? 0));
		}
	};
	collect(laid.children ?? [], 0, 0);
	for (const [i, e] of (laid.edges ?? []).entries()) {
		const src = edges[i];
		const pts: { x: number; y: number }[] = [];
		for (const s of e.sections ?? []) {
			pts.push(s.startPoint, ...(s.bendPoints ?? []), s.endPoint);
		}
		if (!pts.length) {
			const a = abs.get(src.from);
			const b = abs.get(src.to);
			if (a && b) pts.push({ x: a.x + W / 2, y: a.y + H }, { x: b.x + W / 2, y: b.y });
		}
		out.edges.push({ from: src.from, to: src.to, kind: src.kind, points: pts });
	}
	return out;
}
