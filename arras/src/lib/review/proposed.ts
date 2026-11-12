// Review › Proposed Changes read from the manifest: one card for each thing someone proposes that the person decides, and what a copy's card says of it. Model facts in, display facts out.
import type { AdoptionReview, IncomingReview, Manifest, SuggestedEdit } from '$lib/manifest/types';
import { documentOf, openEdits } from './suggestions';

export type Card =
	| { kind: 'pull'; id: 'pull'; pull: IncomingReview; label: string }
	| { kind: 'copy'; id: string; copy: AdoptionReview; edits: SuggestedEdit[] }
	| { kind: 'edit'; id: string; edit: SuggestedEdit }
	| { kind: 'results'; id: string; citekey: string; count: number };

type Read = Pick<Manifest, 'nodes' | 'keys' | 'masters'> & Partial<Pick<Manifest, 'regions' | 'suggested_edits' | 'contributions' | 'incoming' | 'references'>>;

/** The agents' copies waiting to be taken in. */
export function adoptionsOf(m: Pick<Manifest, 'contributions'>): AdoptionReview[] {
	return (m.contributions ?? []).filter((x): x is AdoptionReview => x.kind === 'adopt');
}

/** What the fetched pull is called, by its contribution where the manifest lists one. */
export function pullLabel(m: Pick<Manifest, 'contributions' | 'incoming'>): string {
	return m.contributions?.find((c) => c.kind === 'workspace')?.label ?? `Pull from ${m.incoming?.workspace}`;
}

/** Each work with results proposed and how many, by key. */
export function resultsOf(m: Pick<Manifest, 'references'>): { citekey: string; count: number }[] {
	return Object.entries(m.references ?? {})
		.map(([citekey, ref]) => ({ citekey, count: Object.values(ref.results ?? {}).filter((r) => r.state === 'proposed').length }))
		.filter((w) => w.count > 0)
		.sort((a, b) => a.citekey.localeCompare(b.citekey));
}

/**
 * Everything to decide, in the order the page lists it: the fetched pull, the agents' copies, then the open suggested edits, newest first, then the works with results proposed.
 *
 * Parameters
 * ----------
 * m : Manifest
 *
 * Returns
 * -------
 * Card[]
 *     A suggested edit on a copy with a card of its own is on that card, since it comes in with the copy; one on a copy with none has a card, saying so.
 */
export function cardsOf(m: Read): Card[] {
	const copies = adoptionsOf(m as Manifest);
	const onCopy = new Map<string, SuggestedEdit[]>(copies.map((c) => [c.copy, []]));
	const own: SuggestedEdit[] = [];
	for (const e of openEdits(m)) {
		const held = onCopy.get(documentOf(m as Manifest, e)?.path ?? '');
		if (held) held.push(e);
		else own.push(e);
	}
	return [
		...(m.incoming ? [{ kind: 'pull' as const, id: 'pull' as const, pull: m.incoming, label: pullLabel(m as Manifest) }] : []),
		...copies.map((copy) => ({ kind: 'copy' as const, id: copy.copy, copy, edits: onCopy.get(copy.copy) ?? [] })),
		...own.map((edit): Card => ({ kind: 'edit', id: edit.id, edit })),
		...resultsOf(m as Manifest).map((w) => ({ kind: 'results' as const, id: w.citekey, ...w }))
	];
}

/** How many things wait to be decided: what Review counts here. */
export function proposedCount(m: Read): number {
	return cardsOf(m).length;
}

/** Where a copy's changes stand, as its card says: how many are decided, how many are not, and how many can't be taken. */
export function copySays(t: { taken: number; left: number; undecided: number; clash: number }): string {
	const decided = t.taken + t.left > 0;
	return [
		t.taken ? `${t.taken} taken` : '',
		t.left ? `${t.left} left out` : '',
		t.undecided ? `${t.undecided} ${decided ? 'to decide' : 'to take or leave'}` : '',
		t.clash ? `${t.clash} that can't be taken` : ''
	]
		.filter(Boolean)
		.join(', ');
}
