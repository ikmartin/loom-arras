// The force layout (book 15.5), the default: a neighbourhood, circular nodes, labels beneath, no direction encoded. It answers what sits near what, where the layered drawing answers what this rests on.

import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, forceX, forceY, type SimulationLinkDatum, type SimulationNodeDatum } from 'd3-force';
import type { Manifest } from '$lib/manifest/types';
import { colorOf, graphInput, type Filters, type Layout } from './layout';

/** The radius of a node at rest; the selection is drawn larger by the page, not here. */
export const R = 7;

interface Sim extends SimulationNodeDatum {
	id: string;
}

/**
 * Lay the filtered graph out by simulated forces, synchronously.
 *
 * The simulation is stepped to completion rather than animated: the page animates between the two layouts itself, and a running simulation would fight the drag handler. `seed` carries positions over from a previous layout so a filter change moves nodes rather than reshuffling them.
 */
export function forceLayout(m: Manifest, f: Filters, seed?: Map<string, { x: number; y: number }>): Layout {
	const { nodes, edges } = graphInput(m, f);
	const sims: Sim[] = nodes.map((n, i) => {
		const s = seed?.get(n.id);
		const a = (i / Math.max(1, nodes.length)) * Math.PI * 2;
		return { id: n.id, x: s?.x ?? Math.cos(a) * 200, y: s?.y ?? Math.sin(a) * 200 };
	});
	const links: SimulationLinkDatum<Sim>[] = edges.map((e) => ({ source: e.from, target: e.to }));
	const sim = forceSimulation<Sim>(sims)
		.force(
			'link',
			forceLink<Sim, SimulationLinkDatum<Sim>>(links)
				.id((d) => d.id)
				.distance(58)
				.strength(0.35)
		)
		.force('charge', forceManyBody().strength(-160).distanceMax(520))
		.force('collide', forceCollide(R * 2.4))
		.force('x', forceX(0).strength(0.035))
		.force('y', forceY(0).strength(0.035))
		.force('center', forceCenter(0, 0))
		.stop();
	for (let i = 0; i < 320; i++) sim.tick();

	let minX = Infinity;
	let minY = Infinity;
	let maxX = -Infinity;
	let maxY = -Infinity;
	for (const s of sims) {
		minX = Math.min(minX, s.x ?? 0);
		minY = Math.min(minY, s.y ?? 0);
		maxX = Math.max(maxX, s.x ?? 0);
		maxY = Math.max(maxY, s.y ?? 0);
	}
	if (!sims.length) {
		minX = minY = 0;
		maxX = maxY = 1;
	}
	const pad = 60;
	const dx = pad - minX;
	const dy = pad - minY;
	const at = new Map(sims.map((s) => [s.id, { x: (s.x ?? 0) + dx, y: (s.y ?? 0) + dy }]));

	return {
		nodes: nodes.map((n) => {
			const p = at.get(n.id)!;
			return {
				id: n.id,
				label: n.id,
				taxon: n.taxon,
				state: n.state,
				color: colorOf(m, n.state),
				style: n.style ?? 'plain',
				external: n.external,
				section: n.kind === 'section',
				x: p.x,
				y: p.y,
				w: R * 2,
				h: R * 2
			};
		}),
		groups: [],
		edges: edges.map((e) => {
			const a = at.get(e.from)!;
			const b = at.get(e.to)!;
			return { from: e.from, to: e.to, kind: e.kind, points: [a, b] };
		}),
		width: maxX - minX + pad * 2,
		height: maxY - minY + pad * 2
	};
}
