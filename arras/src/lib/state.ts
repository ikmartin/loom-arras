// The one place the interface's colour vocabulary meets arras's tokens (book 15.6).
// The manifest declares a colour class per state label; the stylesheet declares five state pairs. Everything that needs a state colour goes through here, so adding a state to the interface is a one-line change and an unknown class still renders.

import type { ColorClass } from './manifest/types';

export type StateTone = 'accepted' | 'stale' | 'draft' | 'incomplete' | 'loose';

const BY_CLASS: Record<string, StateTone> = {
	positive: 'accepted',
	'positive-strong': 'accepted',
	warning: 'stale',
	neutral: 'draft',
	negative: 'incomplete',
	info: 'loose'
};

/** The tone for a manifest colour class; anything unrecognised is `loose`, which is `--ink-soft` on no wash. */
export function toneOf(color: ColorClass | undefined): StateTone {
	return BY_CLASS[color ?? ''] ?? 'loose';
}

/** The class name the stylesheet keys off, e.g. `tone-accepted`. */
export function toneClass(color: ColorClass | undefined): string {
	return 'tone-' + toneOf(color);
}
