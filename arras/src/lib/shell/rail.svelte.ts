// The shell owns the right rail and the page owns what goes in it (book 15.3): a page that has context to show registers a snippet here, and the layout hands it to whichever arrangement is on screen. Nothing else crosses the boundary.

import type { Snippet } from 'svelte';

class RailState {
	snippet = $state<Snippet | null>(null);
	/** Whether a split is open on this page. The discussion pane stands where the rail stands (plan 0.13 §7), so the two never share the width: the rail's context is a link away, and a 300px discussion is not a discussion. */
	beside = $state(false);
}

export const rail = new RailState();
