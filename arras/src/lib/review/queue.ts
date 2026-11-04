// The acceptance half of Your Changes: one document's blocks not freshly accepted, grouped by why they wait.
import type { Key, Manifest, UnresolvedReview } from '$lib/manifest/types';
import { documentKeys } from './documents';

export interface TakenIn {
	label: string;
	rows: UnresolvedReview[];
}

export interface Groups {
	/** Accepted once, and changed since, or something they rest on has. */
	changed: UnresolvedReview[];
	/** Taken in from an agent's copy or a pull, one group per source. */
	taken: TakenIn[];
	never: UnresolvedReview[];
	/** Accepted, as they stand. */
	accepted: Key[];
}

const reaches = (m: Pick<Manifest, 'nodes' | 'keys'>, key: string, path: string) => !!m.nodes[m.keys[key]?.node ?? key]?.reached_by.includes(path);

/** The source a taken-in row came from, as its group is headed. */
export function takenLabel(row: UnresolvedReview): string {
	if (row.source_label) return row.source_label;
	if (row.contribution) return `Taken in from the copy “${row.contribution.split('/').pop()!.replace(/\.tex$/, '')}”`;
	return 'Taken in from a pull';
}

/** One document's groups, each in the publisher's (dependency) order. */
export function groupsOf(m: Pick<Manifest, 'nodes' | 'keys' | 'unresolved'>, path: string): Groups {
	const rows = (m.unresolved ?? []).filter((r) => reaches(m, r.key, path));
	const taken = new Map<string, UnresolvedReview[]>();
	for (const r of rows.filter((r) => r.cause === 'adopted' || r.cause === 'incoming-pull')) {
		const label = takenLabel(r);
		if (!taken.has(label)) taken.set(label, []);
		taken.get(label)!.push(r);
	}
	const waiting = new Set(rows.map((r) => r.key));
	return {
		changed: rows.filter((r) => r.cause === 'earlier-change'),
		taken: [...taken.entries()].map(([label, rs]) => ({ label, rows: rs })),
		never: rows.filter((r) => r.cause === 'never-accepted'),
		accepted: documentKeys(m as Manifest, path).filter((k) => k.acceptance?.fresh === true && !waiting.has(k.key))
	};
}

/** The blocks Review counts as waiting: changed since accepted, or taken in. A block never accepted is listed, not counted, so a draft does not keep Review open on it. */
export function waitingCount(m: Pick<Manifest, 'unresolved'>): number {
	return (m.unresolved ?? []).filter((r) => r.cause !== 'never-accepted').length;
}

/** The documents a reviewer can pick: the person's own that reach at least one block. */
export function documentsWithBlocks<T extends { path: string }>(m: Pick<Manifest, 'nodes' | 'keys'>, documents: T[]): T[] {
	const reached = new Set(Object.values(m.keys).flatMap((k) => m.nodes[k.node]?.reached_by ?? []));
	return documents.filter((d) => reached.has(d.path));
}

/** What a row says beside its name: a statement still owed a proof, and the annotations open on it by kind ("1 open objection"). */
export function notesOf(m: Pick<Manifest, 'keys' | 'diagnostics'>, key: string): string[] {
	const out: string[] = [];
	if (m.diagnostics.some((d) => d.code.endsWith('missing-proof') && d.keys.includes(key))) out.push('no proof yet');
	for (const [kind, n] of Object.entries(m.keys[key]?.reviews?.open ?? {})) if (n > 0) out.push(`${n} open ${kind}${n === 1 ? '' : 's'}`);
	return out;
}
