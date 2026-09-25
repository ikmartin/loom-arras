// What the ledger says about each cited work (plan 0.13.3, View 4): one fact per column, each a question a reader asks of the Library — can I read it here, how much has been read off it, does my text lean on it, what awaits my judgment, what is unanswered on it. Model facts in, display facts out, like `reached.ts`; nothing here renders.

import type { Manifest, Reference } from '$lib/manifest/types';
import { bibText } from '$lib/works';

export interface LedgerRow {
	citekey: string;
	title: string;
	/** A copy of the paper is filed here, so opening the work gives its pages. */
	filed: boolean;
	/** Why nothing can be read off it, when someone declared so; '' otherwise. */
	unreadable: string;
	/** Results read off it into its digest; 0 when it has none. */
	digest: number;
	/** Of those, the ones the corpus's own text leans on. */
	used: number;
	/** Statements an agent read off its pages that nobody has vouched for yet. */
	unvouched: number;
	/** Notes on its pages and findings on its results still awaiting an answer. */
	open: number;
}

/**
 * The ledger's row for one work.
 *
 * Parameters
 * ----------
 * m : Manifest
 * ref : Reference
 * reached : Set<string>
 *     The external nodes the corpus leans on (`reachedExternal`), computed once for every row.
 *
 * Returns
 * -------
 * LedgerRow
 */
export function ledgerRow(m: Manifest, ref: Reference, reached: Set<string>): LedgerRow {
	const digest = ref.digest?.nodes ?? [];
	const mine = new Set(digest);
	const onResults = Object.values(m.annotations).filter(
		(a) => !a.discarded && !a.in_reply_to && a.status === 'open' && mine.has(m.keys[a.target.key]?.node ?? a.target.key)
	).length;
	return {
		citekey: ref.citekey,
		title: bibText(ref.bib.title as string) || ref.citekey,
		filed: !!ref.artifacts?.pdf,
		unreadable: ref.unreadable?.why ?? '',
		digest: digest.length,
		used: digest.filter((id) => reached.has(id)).length,
		unvouched: Object.values(ref.results ?? {}).filter((r) => r.state === 'proposed').length,
		open: (ref.reading?.open ?? 0) + onResults
	};
}

/** Whether a work wants something of the author: a statement to judge, or a question to answer. */
export function needsWork(r: LedgerRow): boolean {
	return r.unvouched > 0 || r.open > 0;
}
