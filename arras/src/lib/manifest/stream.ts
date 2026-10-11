// The publisher's word that a new manifest exists, where it offers one: the viewer fetches it at once, and its poll only stands by. Detected like the write API, never assumed, so a corpus on a static host polls as it always has.
//
// The stream says nothing of what changed, so what the viewer does with a new manifest is what it does after a poll (spec README, viewer obligation 3).

import { base } from '$app/paths';
import { capabilities } from '$lib/write';
import { store } from './client.svelte';

/** How often to poll while the stream is open, as a net under it; while it is down, the poll is what tells. */
const NET = 5000;
const UNASSISTED = 1000;

let source: EventSource | null = null;

/** Listen to the publisher's stream, if it offers one. */
export async function listen(): Promise<void> {
	if (source || typeof EventSource === 'undefined') return;
	const caps = await capabilities();
	if (!caps?.stream || source) return;
	source = new EventSource(base + '/_api/stream');
	source.addEventListener('manifest', () => void store.refresh());
	source.onopen = () => store.pace(NET);
	// the browser reconnects by itself; until it does, the poll is back at its own pace
	source.onerror = () => store.pace(UNASSISTED);
}
