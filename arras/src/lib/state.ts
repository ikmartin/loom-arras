// The one place the interface's colour vocabulary meets arras's tokens (book 15.6).
// The manifest declares a colour class per state label; the stylesheet declares five state pairs. Everything that needs a state colour goes through here, so adding a state to the interface is a one-line change and an unknown class still renders.

import type { ColorClass } from './manifest/types';

export type StateTone = 'accepted' | 'stale' | 'draft' | 'incomplete' | 'conflicted' | 'loose';

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

/**
 * The tone for a state by name, so a state whose colour class it shares with another still reads as itself.
 *
 * `conflicted` and `incomplete` are both declared negative, but they are not the same fact: one says the mathematics is unfinished, the other that two files claim one id. The dashed outline is what tells them apart.
 */
export function stateTone(labels: Record<string, { color?: ColorClass } | undefined>, state: string): StateTone {
	if (state === 'conflicted') return 'conflicted';
	return toneOf(labels[state]?.color);
}

export function stateClass(labels: Record<string, { color?: ColorClass } | undefined>, state: string): string {
	return 'tone-' + stateTone(labels, state);
}

/** The class name the stylesheet keys off, e.g. `tone-accepted`. */
export function toneClass(color: ColorClass | undefined): string {
	return 'tone-' + toneOf(color);
}
