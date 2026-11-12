// Review › Your Changes read from the manifest: every pending change in the quilt, grouped by the document that lists it (`changes.ts`); the quilt's To do, the open annotations from others, grouped the same way; and, beneath, each document's blocks waiting to be accepted (changed since accepted, taken in from a copy or a pull), with the never accepted and the accepted folded. Model facts in, display facts out.
import type { Annotation, Key, Manifest, UnresolvedReview } from '$lib/manifest/types';
import { documentLabel } from '$lib/workspace/names';
import { documentOf, isTodo } from './annotating.svelte';
import { pending } from './changes';
import { groupsOf } from './queue';

/** One block as the acceptance list draws it. */
export interface BlockRow {
	key: string;
	/** Why it waits to be accepted. */
	row?: UnresolvedReview;
}

/** One document's blocks as the acceptance list draws them. */
export interface Acceptance {
	/** Changed since accepted. */
	changed: BlockRow[];
	/** Taken in from a copy or a pull, one group per source. */
	taken: { label: string; rows: BlockRow[] }[];
	/** Never accepted: listed, not counted. */
	never: BlockRow[];
	/** Accepted, as they stand. */
	accepted: Key[];
}

/**
 * One document's blocks waiting to be accepted, and those that are not.
 *
 * Parameters
 * ----------
 * m : Manifest
 * path : str
 *     The document.
 *
 * Returns
 * -------
 * Acceptance
 */
export function acceptanceOf(m: Pick<Manifest, 'nodes' | 'keys' | 'unresolved'>, path: string): Acceptance {
	const g = groupsOf(m, path);
	const row = (r: UnresolvedReview): BlockRow => ({ key: r.key, row: r });
	return {
		changed: g.changed.map(row),
		taken: g.taken.map((t) => ({ label: t.label, rows: t.rows.map(row) })),
		never: g.never.map(row),
		accepted: g.accepted
	};
}

/** How many of one document's blocks wait to be accepted: never accepted ones are listed, and do not. */
export function waitingIn(a: Acceptance): number {
	return a.changed.length + a.taken.reduce((n, t) => n + t.rows.length, 0);
}

/** The open annotations from others in one document, work or file, as the To do of Review lists them. */
export interface TodoGroup {
	/** The document's path, a work's citekey or a file's path. */
	path: string;
	label: string;
	annotations: Annotation[];
}

/**
 * The quilt's To do: every open annotation, of a type that stays open, from someone other than the reader, grouped by where it is read.
 *
 * Parameters
 * ----------
 * m : Manifest
 *
 * Returns
 * -------
 * TodoGroup[]
 *     In the order the groups first appear.
 */
export function todoOf(m: Manifest): TodoGroup[] {
	const groups = new Map<string, TodoGroup>();
	for (const a of Object.values(m.annotations ?? {})) {
		if (a.in_reply_to || !isTodo(m, a)) continue;
		const at = documentOf(m, a);
		const g = groups.get(at) ?? { path: at, label: m.masters.some((x) => x.path === at) ? documentLabel(m.masters, at) : (at.split('/').pop() ?? at), annotations: [] };
		g.annotations.push(a);
		groups.set(at, g);
	}
	return [...groups.values()];
}

/**
 * What Review counts here: every pending change, and each block waiting to be accepted once, however many documents read it.
 *
 * Parameters
 * ----------
 * m : Manifest
 *
 * Returns
 * -------
 * int
 */
export function yourChangesCount(m: Pick<Manifest, 'unresolved'> & Partial<Pick<Manifest, 'changes'>>): number {
	const blocks = new Set((m.unresolved ?? []).filter((r) => r.cause !== 'never-accepted').map((r) => r.key));
	return pending(m).length + blocks.size;
}
