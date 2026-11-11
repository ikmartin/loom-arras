// What this page deleted, held until the page closes so each delete can be undone: the log events loom took out (the annotation's and its replies'), which `restore` puts back, and the words naming what went. `DeletedBar` offers the undo, since the deleted annotation's box and mark go with it.

import { store } from '$lib/manifest/client.svelte';
import { write } from '$lib/write';

export interface Deletion {
	id: string;
	/** What went, as a reader names it: `Revision on Theorem 2.1`. */
	said: string;
	removed: Record<string, unknown>[];
}

export const deletions = $state<Deletion[]>([]);

/** Delete annotation `id`, holding what loom removed for the undo; '' when it is done, else loom's refusal in its words. */
export async function deleteAnnotation(id: string, said: string): Promise<string> {
	const res = await write('delete', { annotation: id });
	if (!res.ok) return res.error?.message ?? 'the publisher refused it';
	deletions.push({ id, said, removed: res.removed ?? [] });
	void store.refresh();
	return '';
}

/** Put a deletion back, and forget it once loom has; '' when it is done, else loom's refusal. */
export async function undoDelete(id: string): Promise<string> {
	const held = deletions.find((d) => d.id === id);
	if (!held) return '';
	const res = await write('restore', { events: $state.snapshot(held.removed) });
	if (!res.ok) return res.error?.message ?? 'the publisher refused it';
	forget(id);
	void store.refresh();
	return '';
}

/** Stop offering the undo of a deletion. */
export function forget(id: string): void {
	const at = deletions.findIndex((d) => d.id === id);
	if (at >= 0) deletions.splice(at, 1);
}
