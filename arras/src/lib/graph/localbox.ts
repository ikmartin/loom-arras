// The local graph drawn as boxes (book 15.5.1): the same neighbourhood as the dot drawing, laid out in layers by ELK with what a result rests on above it. No section groups: a neighbourhood crosses sections, and a handful of boxes reads without them.

import type { Manifest } from '$lib/manifest/types';
import { shortLabel, type Neighbourhood } from './local';

export interface BoxNode {
	id: string;
	label: string;
	x: number;
	y: number;
	w: number;
	h: number;
}

export interface BoxEdge {
	from: string;
	to: string;
	kind: string;
	points: { x: number; y: number }[];
}

export interface BoxDrawing {
	nodes: BoxNode[];
	edges: BoxEdge[];
	width: number;
	height: number;
}

export const BOX_H = 22;

/** A box wide enough for its label at the drawing's type size, within bounds. */
export const boxWidth = (label: string) => Math.round(Math.max(56, Math.min(170, 18 + label.length * 5.8)));

/** Dependency kinds, drawn from what is rested on to what rests on it; anything else is a relation between peers. */
const DEPENDS = new Set(['statement', 'proof', 'prose']);

/**
 * Lay a neighbourhood out in layers.
 *
 * Parameters
 * ----------
 * m : Manifest
 * hood : Neighbourhood
 *     From `neighbourhood`; its first node is the centre.
 * master : string, optional
 *     The document whose numbering labels the boxes.
 *
 * Returns
 * -------
 * BoxDrawing
 *     Boxes and routed edges in one frame, with the drawing's extent.
 */
export async function boxLayout(m: Manifest, hood: Neighbourhood, master?: string): Promise<BoxDrawing> {
	const labels = new Map(hood.nodes.map((id) => [id, shortLabel(m, id, master)]));
	const children = hood.nodes.map((id) => ({ id, width: boxWidth(labels.get(id)!), height: BOX_H }));
	const edges = hood.links.map((l, i) => {
		const up = DEPENDS.has(l.kind);
		return { id: 'e' + i, sources: [up ? l.to : l.from], targets: [up ? l.from : l.to] };
	});
	const { default: ELK } = await import('elkjs/lib/elk.bundled.js');
	const laid = (await new ELK().layout({
		id: 'root',
		layoutOptions: {
			'elk.algorithm': 'layered',
			'elk.direction': 'DOWN',
			'elk.edgeRouting': 'POLYLINE',
			'elk.layered.spacing.nodeNodeBetweenLayers': '26',
			'elk.spacing.nodeNode': '12',
			'elk.padding': '[top=6,left=6,bottom=6,right=6]'
		},
		children,
		edges
	})) as {
		width?: number;
		height?: number;
		children?: { id: string; x?: number; y?: number; width?: number; height?: number }[];
		edges?: { id: string; sections?: { startPoint: { x: number; y: number }; endPoint: { x: number; y: number }; bendPoints?: { x: number; y: number }[] }[] }[];
	};
	const nodes: BoxNode[] = (laid.children ?? []).map((c) => ({ id: c.id, label: labels.get(c.id) ?? c.id, x: c.x ?? 0, y: c.y ?? 0, w: c.width ?? 60, h: c.height ?? BOX_H }));
	const out: BoxEdge[] = [];
	for (const e of laid.edges ?? []) {
		const l = hood.links[Number(e.id.slice(1))];
		if (!l) continue;
		const points = (e.sections ?? []).flatMap((s) => [s.startPoint, ...(s.bendPoints ?? []), s.endPoint]);
		out.push({ from: l.from, to: l.to, kind: l.kind, points });
	}
	return { nodes, edges: out, width: laid.width ?? 0, height: laid.height ?? 0 };
}
