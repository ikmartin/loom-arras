import { displayNode } from '$lib/nodes/display';
// The force layout, the default: a neighbourhood, circular nodes, labels beneath, no direction encoded. It answers what sits near what, where the layered drawing answers what this rests on.

import type { Manifest } from '$lib/manifest/types';
import { taxonTone } from '$lib/taxonomy';
import { forcePositions, R, type ForceInput, type ForceOutput } from './force-sim';
import { colorOf, graphInput, type Filters, type Layout } from './layout';

export { R };

type Input = ReturnType<typeof graphInput>;

/** What the force layout's positions depend on: the nodes in order and the edges between them. A manifest that leaves it unchanged leaves the drawing where it is. */
export function forceKey(input: Input): string {
	return input.nodes.map((n) => n.id).join(',') + '|' + input.edges.map((e) => `${e.from}>${e.to}>${e.kind}`).join(',');
}

function simInput(input: Input, seed?: Map<string, { x: number; y: number }>): ForceInput {
	const s: Record<string, [number, number]> = {};
	for (const [id, p] of seed ?? []) s[id] = [p.x, p.y];
	return { ids: input.nodes.map((n) => n.id), edges: input.edges.map((e) => [e.from, e.to]), seed: s };
}

/** Positions laid out as a drawing: each node with its label, colour and tone from the manifest as it stands. */
function decorate(m: Manifest, f: Filters, input: Input, out: ForceOutput): Layout {
	return {
		nodes: input.nodes.map((n) => {
			const [x, y] = out.at[n.id] ?? [0, 0];
			return {
				id: n.id,
				label: n.kind === 'work' ? (n.title ?? n.id) : displayNode(m, n.id, f.master).name,
				taxon: n.taxon,
				state: n.state,
				color: colorOf(m, n.state),
				tone: taxonTone(m, n.taxon),
				style: n.style ?? 'plain',
				external: n.external,
				section: n.kind === 'section',
				x,
				y,
				w: R * 2,
				h: R * 2
			};
		}),
		edges: input.edges.map((e) => {
			const [ax, ay] = out.at[e.from] ?? [0, 0];
			const [bx, by] = out.at[e.to] ?? [0, 0];
			return { from: e.from, to: e.to, kind: e.kind, points: [{ x: ax, y: ay }, { x: bx, y: by }], count: e.count };
		}),
		width: out.width,
		height: out.height
	};
}

/** A drawing already laid out, its labels, colours and tones read again from `m`: what a manifest that moved no node or edge changes. */
export function redecorate(m: Manifest, f: Filters, laid: Layout): Layout {
	const input = graphInput(m, f);
	const at: Record<string, [number, number]> = {};
	for (const n of laid.nodes) at[n.id] = [n.x, n.y];
	return decorate(m, f, input, { at, width: laid.width, height: laid.height });
}

let worker: Worker | null = null;
let asked = 0;
const waiting = new Map<number, { input: ForceInput; done: (out: ForceOutput) => void }>();

/** The simulation in a worker, or on the page where no worker can be had. */
function positionsOff(input: ForceInput): Promise<ForceOutput> {
	if (typeof Worker === 'undefined') return Promise.resolve(forcePositions(input));
	try {
		if (!worker) {
			worker = new Worker(new URL('./force.worker.ts', import.meta.url), { type: 'module' });
			worker.onmessage = (e: MessageEvent<{ n: number; out: ForceOutput }>) => {
				waiting.get(e.data.n)?.done(e.data.out);
				waiting.delete(e.data.n);
			};
			// a worker that cannot run leaves the page to do it, as it did before there was one
			worker.onerror = () => {
				for (const { input: i, done } of waiting.values()) done(forcePositions(i));
				waiting.clear();
				worker?.terminate();
				worker = null;
			};
		}
	} catch {
		return Promise.resolve(forcePositions(input));
	}
	const n = ++asked;
	return new Promise((done) => {
		waiting.set(n, { input, done });
		worker!.postMessage({ ...input, n });
	});
}

/**
 * Lay the filtered graph out by simulated forces, in a worker, so the page is not frozen while it settles.
 *
 * Parameters
 * ----------
 * m : Manifest
 *     The manifest the graph is drawn from.
 * f : Filters
 *     What is drawn.
 * seed : Map<string, {x, y}>, optional
 *     The previous drawing's positions, which the simulation starts from.
 *
 * Returns
 * -------
 * Promise<Layout>
 *     The drawing; a caller that asked again since discards it.
 */
export async function forceLayoutOff(m: Manifest, f: Filters, seed?: Map<string, { x: number; y: number }>): Promise<Layout> {
	const input = graphInput(m, f);
	return decorate(m, f, input, await positionsOff(simInput(input, seed)));
}
