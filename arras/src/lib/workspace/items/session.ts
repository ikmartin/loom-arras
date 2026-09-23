// What a session's two views read (plan 0.13.3 E1–E3): its record, what it found, what it touched, and one sentence of what happened — each from recorded fields only, since a sentence the record does not support is the viewer inventing a claim (P3).

import type { Annotation, Manifest, SessionRow, Thread } from '$lib/manifest/types';
import { anchorId, keyUrl } from '$lib/nav';
import { documentOf, findingsOf, isDocument } from '$lib/review/run';
import { itemFromPath, type Item } from '../item';
import { keyName } from '../names';

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

/** Every finding the session made, worst first; replies and discarded ones are not findings. */
export function findings(m: Manifest, thread: Thread): Annotation[] {
	const f = findingsOf(m, thread);
	return [...f.document, ...f.node];
}

/** What the session wrote to or annotated, once each: the record's targets and every finding's target. */
export function touched(m: Manifest, thread: Thread): string[] {
	return [...new Set([...thread.targets, ...findings(m, thread).map((a) => a.target.key)])];
}

/**
 * One sentence of what happened, composed only from what the record holds.
 *
 * The session's purpose when it states one; otherwise the modes its pipeline ran and on what. Then the findings by state and the rounds. Nothing else is said, so nothing is made up.
 */
export function said(m: Manifest, thread: Thread, row?: SessionRow): string {
	const all = findings(m, thread);
	const open = all.filter((a) => a.status === 'open').length;
	const settled = all.length - open;
	const steps = thread.pipeline ?? [];
	const what = row?.purpose || (steps.length ? [...new Set(steps.map((s) => `${s.mode} on ${s.target}`))].join('; ') : '');
	const counts = all.length ? `${all.length} finding${all.length === 1 ? '' : 's'}, ${open} open, ${settled} settled` : 'no findings';
	const rounds = row?.rounds ? ` · ${row.rounds} round${row.rounds === 1 ? '' : 's'}` : '';
	return `${what ? what + ' — ' : ''}${counts}${rounds}.`;
}

/** A key or a document path, as the item a reader opens to see it: a key the session's document holds opens that document at it, which is where a finding is read in context; an equation opens where its result is, at the equation; a cited work's identifier opens the work; any other key opens its own node. */
export function itemAt(m: Manifest, thread: Thread, key: string, page?: number): Item | null {
	if (isDocument(m, key)) return { kind: 'document', id: key };
	const work = Object.values(m.references).find((r) => r.work === key || r.works?.includes(key));
	if (work) return { kind: 'work', id: work.citekey, ...(page ? { place: { page } } : {}) };
	const region = m.regions?.[key];
	if (region) {
		const at = itemAt(m, thread, region.container);
		return at ? { ...at, anchor: anchorId(key) } : null;
	}
	const doc = documentOf(m, thread);
	const node = m.nodes[key] ?? m.nodes[m.keys[key]?.node ?? ''];
	if (doc && node?.reached_by?.includes(doc)) return { kind: 'document', id: doc, anchor: anchorId(key) };
	return itemFromPath(m, keyUrl(m, key));
}

/** A target's name for a chip or a row: as a reader refers to it (`keyName`). */
export function targetName(m: Manifest, key: string): string {
	return keyName(m, key);
}
