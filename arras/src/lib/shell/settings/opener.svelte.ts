// Opening Settings at a section from elsewhere in the viewer: Customize in the format menu opens Settings › Annotations, and Add new… or Save as new type opens it with a new type started, which what asked for it takes once it is saved. Each request is counted, so asking twice for the same section opens it twice.

import type { Look } from '$lib/manifest/types';
import type { SectionId } from './catalog';

/** Who takes a new type once it is saved: the look in hand, or an annotation. */
export type Taker = { kind: 'hand' } | { kind: 'annotation'; id: string };

/** A new type to start: the look it starts with, and who takes it. */
export interface NewType {
	look?: Look;
	take?: Taker;
}

export const settingsAsked = $state<{ section: SectionId | null; add: NewType | null; n: number }>({ section: null, add: null, n: 0 });

/** Open Settings at `section`; with `add`, Annotations starts a new type. */
export function openSettings(section: SectionId, add: NewType | null = null): void {
	settingsAsked.section = section;
	settingsAsked.add = add;
	settingsAsked.n++;
}
