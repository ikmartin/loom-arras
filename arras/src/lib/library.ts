// What the ledger says about each cited work (plan 0.13.3, View 4): one fact per column, each a question a reader asks of the Library — can I read it here, how much has been read off it, does my text lean on it, what has a person vouched for, what awaits my judgment, what is unanswered on it. Model facts in, display facts out, like `reached.ts`; nothing here renders.

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
	/** Results read off it by loom's extraction, which nobody has vouched for. */
	extracted: number;
	/** Results a person compared with the paper and vouched for. */
	verified: number;
	/** Statements an agent read off its pages that await the author's judgment. */
	proposed: number;
	/** Notes on its pages and findings on its results still awaiting an answer. */
	open: number;
	/** The work's other documents, each a citekey of its own, whose counts are folded into this row. */
	versions: string[];
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
		...resultCounts(ref),
		open: (ref.reading?.open ?? 0) + onResults,
		versions: []
	};
}

/**
 * The ledger: one row per work, a version's counts folded into its work's row, which names it.
 *
 * Parameters
 * ----------
 * m : Manifest
 * reached : Set<string>
 *     As for `ledgerRow`.
 *
 * Returns
 * -------
 * LedgerRow[]
 *     In the manifest's order; a version whose work is not in the manifest keeps a row of its own.
 */
export function ledgerRows(m: Manifest, reached: Set<string>): LedgerRow[] {
	const rows = new Map(Object.values(m.references).map((ref) => [ref.citekey, ledgerRow(m, ref, reached)]));
	for (const ref of Object.values(m.references)) {
		const top = ref.version_of ? rows.get(ref.version_of) : undefined;
		const own = rows.get(ref.citekey);
		if (!top || !own) continue;
		top.filed ||= own.filed;
		for (const k of ['digest', 'used', 'extracted', 'verified', 'proposed', 'open'] as const) top[k] += own[k];
		top.versions.push(ref.citekey);
		rows.delete(ref.citekey);
	}
	return [...rows.values()];
}

/** How many of a work's results are in each state a reader is told: extracted by loom, verified by a person, proposed by an agent. */
export function resultCounts(ref: Reference): { extracted: number; verified: number; proposed: number } {
	const states = Object.values(ref.results ?? {}).map((r) => r.state);
	const count = (s: string) => states.filter((x) => x === s).length;
	return { extracted: count('extracted'), verified: count('verified'), proposed: count('proposed') };
}

/**
 * Where a work's extracted results were read from, when that is another version than the bibliography cites; null otherwise.
 *
 * Parameters
 * ----------
 * ref : Reference
 *
 * Returns
 * -------
 * string | null
 *     The sentence the work's Info says, naming the artifact and what the bibliography cites.
 */
export function readFrom(ref: Reference): string | null {
	const v = Object.values(ref.results ?? {}).find((r) => r.version)?.version;
	if (!v) return null;
	if (!v.extracted_from) return 'The digest does not say what it was read from.';
	const cited = v.cited.startsWith('work:') ? 'a version it does not identify' : 'the published version';
	return `Read from ${v.extracted_from}; the bibliography cites ${cited}.`;
}

/** Whether a work wants something of the author: a statement to judge, or a question to answer. */
export function needsWork(r: LedgerRow): boolean {
	return r.proposed > 0 || r.open > 0;
}
