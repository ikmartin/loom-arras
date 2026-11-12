// The changes Keep or Discard has just been pressed on, shown so at once: a kept one as its new words, a discarded one as its old, out of the stepper and the lists, until the manifest no longer lists it. A refused act takes its change back out of here.

import type { Manifest } from '$lib/manifest/types';
import { pending } from './changes';

export type Act = 'kept' | 'discarded';

class Acted {
	/** By change id. Kept raw and replaced whole, so a reader of it is told when it changes. */
	map = $state.raw<Record<string, Act>>({});
}

export const acted = new Acted();

/** Show `ids` as kept or discarded. */
export function mark(ids: string[], how: Act): void {
	if (!ids.length) return;
	acted.map = { ...acted.map, ...Object.fromEntries(ids.map((id) => [id, how])) };
}

/** Show `ids` as pending again: their act was refused or undone. */
export function unmark(ids: string[]): void {
	if (!ids.some((id) => id in acted.map)) return;
	acted.map = Object.fromEntries(Object.entries(acted.map).filter(([id]) => !ids.includes(id)));
}

/** Let go of every change the manifest no longer lists, so one that comes back is shown pending. */
export function prune(m: Partial<Pick<Manifest, 'changes'>> | null | undefined): void {
	const ids = Object.keys(acted.map);
	if (!ids.length || !m) return;
	const live = new Set(pending(m).map((c) => c.id));
	const gone = ids.filter((id) => !live.has(id));
	if (gone.length) unmark(gone);
}
