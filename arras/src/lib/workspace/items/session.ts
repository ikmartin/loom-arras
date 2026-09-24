// A session's record as its views read it (plan 0.14): the thread when there is one, else an empty one.

import type { Manifest, Thread } from '$lib/manifest/types';

/** The session's record: the thread when there is one, else an empty one standing in for a session that has written nothing yet. */
export function recordOf(m: Manifest, id: string): Thread {
	return (
		m.threads[id] ?? {
			id,
			kind: 'session',
			title: (m.sessions ?? []).find((s) => s.id === id)?.title ?? id,
			created: '',
			participants: [],
			targets: [],
			attachments: [],
			log: [],
			discarded: false
		}
	);
}
