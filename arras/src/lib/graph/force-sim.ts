// The force layout's simulation alone: ids and edges in, positions out. Nothing here touches the page or the manifest, so it runs in a worker (force.worker.ts) as readily as on the page.

import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, forceX, forceY, type SimulationLinkDatum, type SimulationNodeDatum } from 'd3-force';

/** The radius of a node at rest; the selection is drawn larger by the page, not here. */
export const R = 7;

export interface ForceInput {
	ids: string[];
	edges: [string, string][];
	/** Where nodes stood in the previous drawing, so a change moves them rather than reshuffling them. */
	seed: Record<string, [number, number]>;
}

export interface ForceOutput {
	/** Each node's position, shifted so the drawing starts at its padding. */
	at: Record<string, [number, number]>;
	width: number;
	height: number;
}

interface Sim extends SimulationNodeDatum {
	id: string;
}

/** Run the simulation to completion: it is stepped rather than animated, since the page animates between drawings itself and a running simulation would fight the drag handler. */
export function forcePositions({ ids, edges, seed }: ForceInput): ForceOutput {
	const sims: Sim[] = ids.map((id, i) => {
		const s = seed[id];
		const a = (i / Math.max(1, ids.length)) * Math.PI * 2;
		return { id, x: s?.[0] ?? Math.cos(a) * 200, y: s?.[1] ?? Math.sin(a) * 200 };
	});
	const links: SimulationLinkDatum<Sim>[] = edges.map(([source, target]) => ({ source, target }));
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
	const at: Record<string, [number, number]> = {};
	for (const s of sims) at[s.id] = [(s.x ?? 0) + pad - minX, (s.y ?? 0) + pad - minY];
	return { at, width: maxX - minX + pad * 2, height: maxY - minY + pad * 2 };
}
