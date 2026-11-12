// Pending changes read from the manifest (specs/manifest.md §9): every edit made in the person's text since their look, and every open suggested edit, cut by words. Model facts in, display facts out: who made one, what it does in a line, why Keep and Discard are refused, which document lists it, and what Keep all and Discard all would do.
import { isAgentDocument } from '$lib/manifest/documents';
import type { Manifest, PendingChange } from '$lib/manifest/types';

type Read = Partial<Pick<Manifest, 'changes'>> | null | undefined;

/** The name the filter and the lists give the author of an edit made in the file, which no record names. */
export const IN_THE_FILE = 'Edits in the file';

/** Every pending change the manifest lists, in its order; an entry that is not one is left out. */
export function pending(m: Read): PendingChange[] {
	return (m?.changes ?? []).filter((c): c is PendingChange => !!c && typeof c.id === 'string' && typeof c.old === 'string' && typeof c.new === 'string');
}

/** Pending change `id`, while the manifest lists it. */
export function changeById(m: Read, id: string | null | undefined): PendingChange | undefined {
	return id ? pending(m).find((c) => c.id === id) : undefined;
}

/** The pending changes in document `path`'s text. */
export function changesIn(m: Read, path: string): PendingChange[] {
	return pending(m).filter((c) => c.documents?.includes(path));
}

/** Whether Keep and Discard act on it now: one ready to write, or a suggestion the text already reads as, which Keep records kept and Discard records discarded. */
export function ready(c: Pick<PendingChange, 'state'>): boolean {
	return c.state === 'ready' || c.state === 'taken';
}

/** What a change is, in two words: an edit made in the file, or a suggestion. */
export function kindName(c: Pick<PendingChange, 'kind'>): string {
	return c.kind === 'suggested' ? 'Suggestion' : 'Edit in the file';
}

/** Who made it, by the id the filter leaves people out by and the name it shows: an edit in the file with no author is the file's. The manifest names an author by name, or as an annotation's author is named. */
export function authorOf(c: Pick<PendingChange, 'author'>): { id: string; name: string } {
	if (!c.author) return { id: IN_THE_FILE, name: IN_THE_FILE };
	if (typeof c.author === 'string') return { id: c.author, name: c.author };
	return { id: c.author.id, name: c.author.label ?? c.author.id };
}

/** Who made it, as the person reads it on a card: "you" for their own, a writer by the name they gave, nothing for an edit in the file. */
export function whoMade(m: Pick<Manifest, 'reviewer'> | null | undefined, c: Pick<PendingChange, 'author'>): string {
	if (!c.author) return '';
	const a = authorOf(c);
	return a.id === m?.reviewer?.name ? 'you' : a.name;
}

/** Words cut short for a line, with an ellipsis. */
function clip(t: string, n = 60): string {
	const one = t.replace(/\s+/g, ' ').trim();
	return one.length > n ? one.slice(0, n - 1) + '…' : one;
}

/** What it does, in one line: “old” → “new”, add “new”, or remove “old”. */
export function summary(c: Pick<PendingChange, 'old' | 'new'>): string {
	const o = clip(c.old);
	const n = clip(c.new);
	if (!o) return `add “${n}”`;
	if (!n) return `remove “${o}”`;
	return `“${o}” → “${n}”`;
}

/** Why Keep and Discard are refused, or for a suggestion the text already reads as, what Keep does: loom's words, else the state's; '' for one that is ready. */
export function refusal(c: Pick<PendingChange, 'state' | 'why'>): string {
	if (c.state === 'taken') return c.why || 'The text already reads so; Keep records it kept.';
	if (ready(c)) return '';
	if (c.why) return c.why;
	if (c.state === 'unplaced') return 'It has no place in the text as it stands.';
	if (c.state === 'on-a-copy') return "It is on the agent's copy, and comes in with the copy.";
	return 'It cannot be kept or discarded now.';
}

/** What its popup and card say beside Keep and Discard: where the change stands, and what each does. */
export function actSays(c: Pick<PendingChange, 'kind'>): { line: string; keep: string; discard: string } {
	return c.kind === 'suggested'
		? { line: 'Not in the file yet. Keep writes it in.', keep: 'Write it into the file', discard: 'Delete the suggestion; the text stays as it is' }
		: { line: 'Already in the file. Discard writes your words back.', keep: 'Take it into what you have kept', discard: 'Write your old words back into the file' };
}

const plural = (n: number, one: string) => `${n} ${n === 1 ? one : one + 's'}`;
const sentence = (parts: (string | false)[]) => {
	const t = parts.filter(Boolean).join(' and ');
	return t ? t.charAt(0).toUpperCase() + t.slice(1) + '.' : '';
};

/** What Keep all and Discard all would do to `list`, a line each, as the Changes menu and a document's group say. */
export function allSays(list: Pick<PendingChange, 'kind'>[]): { keep: string; discard: string } {
	const ns = list.filter((c) => c.kind === 'suggested').length;
	const nf = list.length - ns;
	return {
		keep: sentence([ns > 0 && `writes the ${plural(ns, 'suggestion')} into the file`, nf > 0 && `keeps the ${plural(nf, 'edit')} already in it`]),
		discard: sentence([ns > 0 && `deletes the ${plural(ns, 'suggestion')}`, nf > 0 && `writes your old words back over the ${plural(nf, 'edit')}`])
	};
}

/** One document's pending changes, as Review › Your Changes groups them; a change in no document is grouped under its file. */
export interface ChangeGroup {
	/** The document's path, or the file's for one in no document. */
	path: string;
	/** What the group is called: the document's file name, or the file's path. */
	label: string;
	/** Whether it is a document, which Keep all and Discard all can name. */
	document: boolean;
	changes: PendingChange[];
}

/**
 * Every pending change, grouped by the document that lists it.
 *
 * Parameters
 * ----------
 * m : Manifest
 *
 * Returns
 * -------
 * ChangeGroup[]
 *     The person's own documents in the quilt's order, then agents' copies, then each file in no document; a change in several documents is listed under the first of them in that order.
 */
export function byDocument(m: Pick<Manifest, 'masters'> & Partial<Pick<Manifest, 'changes'>>): ChangeGroup[] {
	const live = m.masters.filter((d) => !d.closed && !d.context_only);
	const ranked = [...live.filter((d) => !isAgentDocument(d)), ...live.filter((d) => isAgentDocument(d))];
	const groups = new Map<string, ChangeGroup>();
	for (const d of ranked) groups.set(d.path, { path: d.path, label: d.path.split('/').pop() ?? d.path, document: true, changes: [] });
	const files = new Map<string, ChangeGroup>();
	for (const c of pending(m)) {
		const home = ranked.find((d) => c.documents?.includes(d.path));
		if (home) groups.get(home.path)!.changes.push(c);
		else {
			const g = files.get(c.path) ?? { path: c.path, label: c.path, document: false, changes: [] };
			g.changes.push(c);
			files.set(c.path, g);
		}
	}
	return [...[...groups.values()].filter((g) => g.changes.length), ...files.values()];
}
