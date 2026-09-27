export interface Dependency { from: string; to: string; kind?: string }

/** Traverse recorded edges in one direction, retaining the edges on the resulting paths. */
export function relationships(edges: Dependency[], selected: string, direction: 'closure' | 'downstream') {
	const adjacency = new Map<string, { id: string; edge: Dependency }[]>();
	for (const edge of edges) {
		if (edge.from === edge.to) continue;
		const [from, to] = direction === 'closure' ? [edge.from, edge.to] : [edge.to, edge.from];
		if (!adjacency.has(from)) adjacency.set(from, []);
		adjacency.get(from)!.push({ id: to, edge });
	}
	const direct = new Set((adjacency.get(selected) ?? []).map((x) => x.id).filter((id) => id !== selected));
	const reached = new Set<string>();
	const paths = new Set<string>();
	const queue = selected ? [selected] : [];
	const visited = new Set(queue);
	for (let i = 0; i < queue.length; i++) {
		for (const { id, edge } of adjacency.get(queue[i]) ?? []) {
			paths.add(`${edge.from}\0${edge.to}`);
			if (id !== selected) reached.add(id);
			if (!visited.has(id)) { visited.add(id); queue.push(id); }
		}
	}
	return { direct, indirect: new Set([...reached].filter((id) => !direct.has(id))), reached, paths };
}

export type Drawing = 'dots' | 'box' | 'sections' | 'reading';
export function scopedDrawing(mode: Drawing, master: string): Drawing {
	return !master && (mode === 'sections' || mode === 'reading') ? 'dots' : mode;
}
