// The shell owns the right rail and the page owns what goes in it (book 15.3): a page that has context to show registers a snippet here, and the layout hands it to whichever arrangement is on screen. Nothing else crosses the boundary.

import type { Snippet } from 'svelte';

class RailState {
	snippet = $state<Snippet | null>(null);
}

export const rail = new RailState();
