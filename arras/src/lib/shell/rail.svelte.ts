// The shell owns the right rail and the page owns what goes in it: a page that has context to show registers a snippet here, and the layout hands it to the shell. Nothing else crosses the boundary.

import type { Snippet } from 'svelte';

class RailState {
	snippet = $state<Snippet | null>(null);
}

export const rail = new RailState();
