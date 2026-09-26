// The graph by section (book 15.5): one card per section holding its results in document order, and one edge per pair of sections carrying the dependencies behind it.

import type { Manifest } from '$lib/manifest/types';
import { colorOf, graphInput, PAPER, sectionOf, type Filters } from './layout';
import { shortLabel } from './local';
import { documentOrder, placeOf } from './order';

export interface CardRow {
	id: string;
	label: string;
	color: string;
	external: boolean;
	/** Baseline within the card. */
	dy: number;
}

export interface Card {
	id: string;
	label: string;
	x: number;
	y: number;
	w: number;
	h: number;
	rows: CardRow[];
}

export interface CardEdge {
	from: string;
	to: string;
	kind: string;
	/** How many dependencies this one line stands for. */
	count: number;
	/** The result pairs behind it, so hovering or selecting a result can light the lines it is in. */
	members: { from: string; to: string }[];
	points: { x: number; y: number }[];
}

export interface Sections {
	cards: Card[];
	edges: CardEdge[];
	width: number;
	height: number;
}

const ROW = 16;
const HEAD = 24;
const CARD_W = 200;
/** Results with no section of their own: papers drawn as one node, and anything outside every section. */
const LOOSE = 'loose:';

/**
 * Lay the filtered graph out as section cards.
 *
 * Parameters
 * ----------
 * m : Manifest
 * f : Filters
 *     As for `layout`; the master also fixes the reading order the rows and cards follow.
 *
 * Returns
 * -------
 * Sections
 *     Cards, their rows, and the aggregated edges, all in one frame.
 */
export async function sectionLayout(m: Manifest, f: Filters): Promise<Sections> {
	const { nodes, edges } = graphInput(m, f);
	const master = f.master ?? m.masters.find((x) => x.default)?.path ?? m.masters[0]?.path ?? '';
	const order = documentOrder(m, master);
	const clip = (t: string, n: number) => (t.length > n ? t.slice(0, n - 1) + '…' : t);
	const cardOf = new Map<string, string>();
	const rows = new Map<string, CardRow[]>();
	const results = nodes.filter((n) => n.kind !== 'section');
	results.sort((a, b) => placeOf(order, a.id) - placeOf(order, b.id) || a.id.localeCompare(b.id));
	for (const n of results) {
		const card = n.id.startsWith(PAPER) ? LOOSE + 'papers' : sectionOf(m, n.id, master) || LOOSE + 'rest';
		cardOf.set(n.id, card);
		const list = rows.get(card) ?? rows.set(card, []).get(card)!;
		list.push({
			id: n.id,
			label: clip(n.id.startsWith(PAPER) ? (n.title ?? n.id) : shortLabel(m, n.id, master), 26),
			color: colorOf(m, n.state),
			external: n.external,
			dy: HEAD + list.length * ROW + ROW - 5
		});
	}
	// a section that is an edge's endpoint but holds no drawn result belongs to the nearest section above it that has a card; a reference to §2 is a reference to the card §2 is drawn as
	const ancestorCard = (id: string) => {
		let p = sectionOf(m, id, master);
		while (p && !rows.has(p)) p = sectionOf(m, p, master);
		return p;
	};
	for (const e of edges)
		for (const end of [e.from, e.to])
			if (!cardOf.has(end) && m.nodes[end]?.kind === 'section') {
				const up = ancestorCard(end);
				if (up) cardOf.set(end, up);
				else {
					cardOf.set(end, end);
					rows.set(end, []);
				}
			}
	const label = (id: string) => {
		if (id === LOOSE + 'papers') return 'cited papers';
		if (id === LOOSE + 'rest') return 'outside every section';
		const n = m.nodes[id];
		const number = n?.numbers[master]?.number;
		return clip([number, n?.name ?? n?.title ?? id].filter(Boolean).join(' '), 28);
	};
	const cards: Card[] = [...rows.entries()]
		.map(([id, list]) => ({ id, label: label(id), rows: list, x: 0, y: 0, w: CARD_W, h: HEAD + Math.max(1, list.length) * ROW + 6 }))
		.sort((a, b) => placeOf(order, a.id) - placeOf(order, b.id) || a.id.localeCompare(b.id));
	const agg = new Map<string, CardEdge>();
	for (const e of edges) {
		const a = cardOf.get(e.from);
		const b = cardOf.get(e.to);
		if (!a || !b || a === b) continue;
		// every kind between two sections is one line; a reference in prose stays distinct, since it is not a dependency
		const kind = e.kind === 'prose' ? 'prose' : e.kind === 'cites' ? 'cites' : 'statement';
		const key = `${a}>${b}>${kind}`;
		const cur = agg.get(key) ?? agg.set(key, { from: a, to: b, kind, count: 0, members: [], points: [] }).get(key)!;
		cur.count++;
		cur.members.push({ from: e.from, to: e.to });
	}
	const list = [...agg.values()];
	const { default: ELK } = await import('elkjs/lib/elk.bundled.js');
	const laid = (await new ELK().layout({
		id: 'root',
		layoutOptions: {
			'elk.algorithm': 'layered',
			'elk.direction': 'DOWN',
			'elk.edgeRouting': 'POLYLINE',
			'elk.layered.spacing.nodeNodeBetweenLayers': '32',
			'elk.spacing.nodeNode': '16',
			'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
			'elk.layered.considerModelOrder.strategy': 'NODES_AND_EDGES'
		},
		children: cards.map((c) => ({ id: c.id, width: c.w, height: c.h })),
		edges: list.map((e, i) => ({ id: 'e' + i, sources: [e.to], targets: [e.from] }))
	})) as {
		width?: number;
		height?: number;
		children?: { id: string; x?: number; y?: number }[];
		edges?: { id: string; sections?: { startPoint: { x: number; y: number }; endPoint: { x: number; y: number }; bendPoints?: { x: number; y: number }[] }[] }[];
	};
	const at = new Map((laid.children ?? []).map((c) => [c.id, c]));
	for (const c of cards) {
		const b = at.get(c.id);
		c.x = b?.x ?? 0;
		c.y = b?.y ?? 0;
	}
	for (const e of laid.edges ?? []) {
		const src = list[Number(e.id.slice(1))];
		if (!src) continue;
		src.points = (e.sections ?? []).flatMap((s) => [s.startPoint, ...(s.bendPoints ?? []), s.endPoint]).reverse();
	}
	return { cards, edges: list.filter((e) => e.points.length), width: laid.width ?? 800, height: laid.height ?? 600 };
}
