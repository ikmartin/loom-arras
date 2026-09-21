// Opening a session (plan 0.13.1). Its own module because the control that opens one stands in the panel's header
// while the list that shows them is the picker, and because `write.ts` imports the session state — putting this beside
// that state would close a cycle.

import { store } from '$lib/manifest/client.svelte';
import { sessionView } from './sessions.svelte';
import { write } from '$lib/write';

/**
 * Open a session and select it.
 *
 * **It is selected because nothing is created automatically any more.** With the viewer no longer opening a session on the first write, this is the only way to reach a fresh one, and leaving it unselected would make opening a session a two-step act whose second step is easy to forget — which is how work ends up filed in yesterday's sitting.
 *
 * Returns the new session's id, or `''` when the publisher refused.
 */
export async function openSession(title: string, purpose = ''): Promise<string> {
	const res = await write('session-new', purpose ? { title, purpose } : { title });
	if (!res.ok) return '';
	// the endpoint answers with what the CLI prints: `<id>  <title>  (active)`
	const made = typeof res.result === 'string' ? res.result.trim().split(/\s+/)[0] : '';
	if (made) {
		sessionView.selected = made;
		sessionView.save();
	}
	store.refresh();
	return made;
}
