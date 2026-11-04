// Review › Your text read from the manifest: one document's blocks, each listed once with every reason it waits (edited since the look, changed since accepted, taken in), the text edited outside any block, and the files in no document. Model facts in, display facts out.
import type { FileChange, Key, Manifest, UnresolvedReview } from '$lib/manifest/types';
import { groupsOf } from './queue';

type Read = Pick<Manifest, 'nodes' | 'keys' | 'unresolved'> & Partial<Pick<Manifest, 'changes'>>;

/** Some of a file's changes, by number. */
export interface Edit {
	change: FileChange;
	hunks: number[];
}

/** One block as the page lists it. */
export interface BlockRow {
	key: string;
	/** Why it waits to be accepted; none when it stands accepted though its text was edited. */
	row?: UnresolvedReview;
	/** Its edit since the look, drawn under it. */
	edit?: Edit;
	/** The block whose row draws an edit running across this one too. */
	editedWith?: string;
}

export interface YourText {
	/** Edited since the look, or changed since accepted. */
	changed: BlockRow[];
	/** Taken in from a copy or a pull, one group per source. */
	taken: { label: string; rows: BlockRow[] }[];
	/** Text of the document's files edited outside any block, by file. */
	outside: Edit[];
	/** Never accepted and not edited: listed, not counted. */
	never: BlockRow[];
	/** Accepted, as they stand. */
	accepted: Key[];
}

const reaches = (m: Pick<Manifest, 'nodes' | 'keys'>, key: string, path: string) => !!m.nodes[m.keys[key]?.node ?? key]?.reached_by.includes(path);

/** Files whose edits belong to no document's blocks: those in no document, and an empty new file, which has no change to draw. */
export function otherFiles(m: Pick<Manifest, 'changes'>): FileChange[] {
	return (m.changes ?? []).filter((c) => !c.documents?.length || !c.hunks);
}

/**
 * One document's text as the page lists it.
 *
 * Parameters
 * ----------
 * m : Manifest
 * path : str
 *     The document.
 *
 * Returns
 * -------
 * YourText
 *     An edit touching several blocks is drawn under the first, and each other says so; a block is in one list, its edit shown wherever that is.
 */
export function yourTextOf(m: Read, path: string): YourText {
	const g = groupsOf(m, path);
	const edits = new Map<string, Edit>();
	const shared = new Map<string, string>();
	const outside: Edit[] = [];
	for (const c of m.changes ?? []) {
		if (!c.hunks || !c.documents?.includes(path)) continue;
		const loose: number[] = [];
		(c.blocks ?? []).forEach((keys, n) => {
			const here = keys.filter((k) => reaches(m, k, path));
			if (!here.length) return void loose.push(n);
			const edit = edits.get(here[0]) ?? { change: c, hunks: [] };
			edit.hunks.push(n);
			edits.set(here[0], edit);
			for (const k of here.slice(1)) if (!shared.has(k)) shared.set(k, here[0]);
		});
		if (loose.length) outside.push({ change: c, hunks: loose });
	}
	const edited = (k: string) => edits.has(k) || shared.has(k);
	const block = (key: string, row?: UnresolvedReview): BlockRow => ({ key, row, edit: edits.get(key), editedWith: edits.has(key) ? undefined : shared.get(key) });
	const waits = new Set((m.unresolved ?? []).filter((r) => reaches(m, r.key, path)).map((r) => r.key));
	return {
		changed: [
			...g.changed.map((r) => block(r.key, r)),
			...g.never.filter((r) => edited(r.key)).map((r) => block(r.key, r)),
			...[...new Set([...edits.keys(), ...shared.keys()])].filter((k) => !waits.has(k)).map((k) => block(k))
		],
		taken: g.taken.map((t) => ({ label: t.label, rows: t.rows.map((r) => block(r.key, r)) })),
		outside,
		never: g.never.filter((r) => !edited(r.key)).map((r) => block(r.key, r)),
		accepted: g.accepted.filter((k) => !edited(k.key))
	};
}

/** How many rows of one document wait: never accepted ones are listed, and do not. */
export function waitingIn(y: YourText): number {
	return y.changed.length + y.taken.reduce((n, t) => n + t.rows.length, 0) + y.outside.length;
}

/**
 * What Review counts here: each block waiting or edited once, however many documents read it, each file's text outside any block once, and each file in no document.
 *
 * Parameters
 * ----------
 * m : Manifest
 *
 * Returns
 * -------
 * int
 */
export function yourTextCount(m: Pick<Manifest, 'unresolved'> & Partial<Pick<Manifest, 'changes'>>): number {
	const blocks = new Set((m.unresolved ?? []).filter((r) => r.cause !== 'never-accepted').map((r) => r.key));
	let files = otherFiles(m).length;
	for (const c of m.changes ?? []) {
		if (!c.hunks || !c.documents?.length) continue;
		for (const k of (c.blocks ?? []).flat()) blocks.add(k);
		if ((c.blocks ?? []).some((keys) => !keys.length)) files += 1;
	}
	return blocks.size + files;
}
