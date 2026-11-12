// Review › Proposed Changes read from the manifest: one card for each thing someone proposes that the person decides in a pass of its own (a pull, an agent's copy, a work's proposed results), and what a copy's card says of it. A suggested edit is a pending change, kept or discarded in the document and in Your Changes; one on an agent's copy is listed on the copy's card, since it comes in with the copy. Model facts in, display facts out.
import type { AdoptionReview, IncomingReview, Manifest, SuggestedEdit } from '$lib/manifest/types';
import { documentOf, openEdits } from './suggestions';

export type Card =
	| { kind: 'pull'; id: 'pull'; pull: IncomingReview; label: string }
	| { kind: 'copy'; id: string; copy: AdoptionReview; edits: SuggestedEdit[] }
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
 * Everything to decide here, in the order the page lists it: the fetched pull, the agents' copies, then the works with results proposed.
 *
 * Parameters
 * ----------
 * m : Manifest
 *
 * Returns
 * -------
 * Card[]
 *     A copy's card holds the open suggested edits on the copy, since they come in with it.
 */
export function cardsOf(m: Read): Card[] {
	const copies = adoptionsOf(m as Manifest);
	const onCopy = new Map<string, SuggestedEdit[]>(copies.map((c) => [c.copy, []]));
	for (const e of openEdits(m)) onCopy.get(documentOf(m as Manifest, e)?.path ?? '')?.push(e);
	return [
		...(m.incoming ? [{ kind: 'pull' as const, id: 'pull' as const, pull: m.incoming, label: pullLabel(m as Manifest) }] : []),
		...copies.map((copy) => ({ kind: 'copy' as const, id: copy.copy, copy, edits: onCopy.get(copy.copy) ?? [] })),
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
