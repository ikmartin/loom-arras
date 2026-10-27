// The session verbs every surface shares — the picker, the footer's delete and Review's Sessions — so a session is renamed, closed, reopened or deleted one way wherever it is.

import { store } from '$lib/manifest/client.svelte';
import type { SessionRow } from '$lib/manifest/types';
import { write } from '$lib/write';
import { sessionView } from './sessions.svelte';

async function act(id: string, endpoint: string, body: Record<string, unknown> = {}): Promise<boolean> {
	const res = await write(endpoint, { session: id, ...body });
	void store.refresh();
	return res.ok;
}

/** Rename, shown at once: the footer drops the pending name when the manifest carries it. */
export async function renameSession(s: SessionRow, want: string): Promise<boolean> {
	sessionView.renamed[s.id] = want;
	const ok = await act(s.id, 'session-rename', { title: want });
	if (!ok) delete sessionView.renamed[s.id];
	return ok;
}

/** Close; a closed session cannot be the write target, so the selection lets it go. */
export async function closeSession(id: string): Promise<boolean> {
	const ok = await act(id, 'session-close');
	if (ok) sessionView.dropped(id);
	return ok;
}

/** Reopen and select (S8): the refusal's wording promises this path, and a reopened session nobody selected would still refuse. Set directly rather than through `select`: the manifest still says closed, and that would admit every closed session's annotations. */
export async function reopenSession(id: string): Promise<boolean> {
	const ok = await act(id, 'session-reopen');
	if (ok) {
		sessionView.selected = id;
		sessionView.save();
	}
	return ok;
}

/** Delete: a tombstone in the index; its annotations stay in the log. */
export async function deleteSession(id: string): Promise<boolean> {
	const ok = await act(id, 'session-delete');
	if (ok) sessionView.dropped(id);
	return ok;
}
