// The left panel's contents follow the view (book 15.4): a document's contents in read and graph, a page's filters on a table page. The page registers what belongs there and the shell places it, so no page draws a rail of its own.

import type { Snippet } from 'svelte';

class PanelState {
	snippet = $state<Snippet | null>(null);
	label = $state('');
}

export const panel = new PanelState();
