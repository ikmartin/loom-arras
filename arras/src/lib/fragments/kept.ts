// Documents kept after their fragment goes: a tab switched away from, a narrow layout's other pane, reading left for the graph. Coming back takes the typeset markup back instead of drawing and typesetting it again. Two are kept, since a reader goes back and forth between few.

export interface Kept {
	/** The markup as published, which the kept nodes were drawn from. */
	html: string;
	/** The fragment's children, typeset, with the comment placements taken out. */
	nodes: DocumentFragment;
}

const LIMIT = 2;
const kept = new Map<string, Kept>();

/** Keep a document under `key`, dropping the one kept longest when there are too many. */
export function keep(key: string, entry: Kept): void {
	kept.delete(key);
	kept.set(key, entry);
	while (kept.size > LIMIT) kept.delete(kept.keys().next().value!);
}

/** Take back the document kept under `key`, if any; it is no longer kept. */
export function take(key: string): Kept | undefined {
	const entry = kept.get(key);
	kept.delete(key);
	return entry;
}
