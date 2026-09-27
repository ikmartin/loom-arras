// The graph in reading order (book 15.5): the document top to bottom, its sections and results as rows, and every dependency an arc in the left margin.

import type { Manifest } from '$lib/manifest/types';
import { colorOf, graphInput, sectionOf, type Filters } from './layout';
import { shortLabel } from './local';
import { documentOrder, placeOf } from './order';

export interface ReadingRow {
	id: string;
	kind: 'section' | 'result';
	label: string;
	/** How deep the section sits, for the indent; a result is one deeper than its section. */
	depth: number;
	y: number;
	color: string;
	external: boolean;
}

export interface Arc {
	from: string;
	to: string;
	kind: string;
	d: string;
}

export interface Reading {
	rows: ReadingRow[];
	arcs: Arc[];
	/** Where the rows begin; the arcs live to the left of it. */
	gutter: number;
	width: number;
	height: number;
}

const ROW = 21;
const TOP = 18;
const GUTTER = 210;

/**
 * The filtered graph as the document reads, with dependencies as arcs.
 *
 * Parameters
 * ----------
 * m : Manifest
 * f : Filters
 *     As for `layout`; the master is the document whose order and numbering are used.
 *
 * Returns
 * -------
 * Reading
 *     Rows in reading order and one arc per edge between two rows. Nothing is laid out: a row's place is where it falls in the document.
 */
export function readingOrder(m: Manifest, f: Filters): Reading {
	const { nodes, edges } = graphInput(m, f);
	const master = f.master ?? m.masters.find((x) => x.default)?.path ?? m.masters[0]?.path ?? '';
	const order = documentOrder(m, master);
	const shown = new Set(nodes.map((n) => n.id));
	const chain = (id: string) => {
		const out: string[] = [];
		let p: string = id;
		while (p && m.nodes[p]) {
			out.unshift(p);
			p = sectionOf(m, p, master);
		}
		return out;
	};
	const wanted = new Set<string>();
	for (const n of nodes) {
		wanted.add(n.id);
		for (const s of chain(sectionOf(m, n.id, master))) wanted.add(s);
	}
	// a section an edge points at is a row too, with the sections above it
	for (const e of edges) for (const end of [e.from, e.to]) if (m.nodes[end]?.kind === 'section') for (const s of chain(end)) wanted.add(s);
	const depth = new Map<string, number>();
	for (const id of wanted) depth.set(id, chain(sectionOf(m, id, master)).length);
	const rows: ReadingRow[] = [...wanted]
		.sort((a, b) => placeOf(order, a) - placeOf(order, b) || a.localeCompare(b))
		.map((id, i) => {
			const n = m.nodes[id];
			const section = n?.kind === 'section';
			const number = n?.numbers[master]?.number ?? '';
			return {
				id,
				kind: section ? ('section' as const) : ('result' as const),
				label: section ? [number, n?.name ?? n?.title ?? id].filter(Boolean).join(' ') : shortLabel(m, id, master),
				depth: depth.get(id) ?? 0,
				y: TOP + i * ROW,
				color: colorOf(m, n?.state ?? ''),
				external: !!n?.external
			};
		});
	const at = new Map(rows.map((r) => [r.id, r.y]));
	const arcs: Arc[] = [];
	for (const e of edges) {
		const y1 = at.get(e.from);
		const y2 = at.get(e.to);
		if (y1 === undefined || y2 === undefined || !shown.has(e.from)) continue;
		// an arc bulges with the distance it reaches, so a long reach back is visible as a wide arc
		const bulge = Math.min(GUTTER - 30, 20 + Math.abs(y1 - y2) * 0.32);
		const x = GUTTER - 8;
		arcs.push({ from: e.from, to: e.to, kind: e.kind, d: `M${x},${y1 - 4} C${x - bulge},${y1 - 4} ${x - bulge},${y2 - 4} ${x},${y2 - 4}` });
	}
	return { rows, arcs, gutter: GUTTER, width: 1000, height: TOP + rows.length * ROW + 12 };
}
