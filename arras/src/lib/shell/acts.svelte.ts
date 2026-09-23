// The rail above a reading view is the shell's, and the controls in it are the page's (plan 0.13.3 phase 1): a page registers what it acts with, the layout draws the rail once above it with the annotation filter at its left. The same pattern as the right rail's registry in `rail.svelte.ts`.

import type { Snippet } from 'svelte';

class ActsState {
	/** What the page says about itself at the rail's left, after the filter: a landmark's step, a work's views. */
	lead = $state<Snippet | null>(null);
	/** The page's controls, at the rail's right. */
	acts = $state<Snippet | null>(null);
}

export const acts = new ActsState();
