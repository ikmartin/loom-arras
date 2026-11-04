// An agent's copy as Incoming reviews it in one pass (plan 0.25.2): each result it changes, its prose and its preamble, named as the person reads them, with whether each can be taken, where each stands, and what Apply asks loom to accept. Model facts in, display facts out; nothing here renders.
import type { AdoptionReview, IncorporationMathReview, Manifest } from '$lib/manifest/types';
import { displayNode } from '$lib/nodes/display';

export type Change = AdoptionReview['changes'][number];
export type State = 'taken' | 'left' | 'undecided';

/** One thing to take or leave: a result's change, the prose and ordering, or the preamble. */
export interface Item {
	key: string;
	kind: 'result' | 'prose' | 'preamble';
	name: string;
	/** What it is and where: "Convention 6.1 · Setting". */
	detail: string;
	/** The section it stands under in the copy, '' at the top. */
	section: string;
	can: boolean;
	/** Why it can't be taken, in the person's words. */
	why: string;
	change?: Change;
}

/** A choice as `adopt-decision` saves it. */
export interface Decision {
	keys: string[];
	document: boolean;
	preamble: boolean;
	kept: string[];
}

const CLASH = 'You and the agent both changed it and the edits clash. Reconcile it in your editor, then refresh the copy.';

function sectionOf(m: Manifest, key: string, master: string): string {
	const node = m.nodes[key] ?? m.nodes[m.keys[key]?.node ?? ''];
	const parent = node?.parent?.[master];
	const section = parent ? m.nodes[parent] : undefined;
	return section?.name?.trim() || section?.title?.trim() || '';
}

/** Every item of a contribution in the copy's order, each named by the copy's own result where it has one, a revision by the person's. */
export function itemsOf(m: Manifest, c: AdoptionReview): Item[] {
	const out: Item[] = c.changes.map((ch) => {
		const own = ch.proposed_key && (m.nodes[ch.proposed_key] || m.keys[ch.proposed_key]) ? ch.proposed_key : '';
		const [key, master] = own ? [own, c.copy] : [ch.key, c.source];
		const shown = displayNode(m, key, master);
		const name = shown.name !== key ? shown.name : ch.name || ch.key;
		const clash = ch.class === 'conflict';
		return { key: ch.key, kind: 'result', name, detail: shown.context, section: sectionOf(m, key, master), can: !clash, why: clash ? CLASH : '', change: ch };
	});
	if (c.document_changed) out.push({ key: 'document', kind: 'prose', name: 'Prose and ordering', detail: 'The text between results, and their order', section: '', can: !c.document_conflict, why: c.document_conflict ? 'The prose changed on both sides and the edits clash. Reconcile it in your editor, then refresh the copy.' : '' });
	if (c.preamble_changed) out.push({ key: 'preamble', kind: 'preamble', name: 'Preamble', detail: 'Packages and macros for the whole paper', section: '', can: !c.preamble_conflict, why: c.preamble_conflict ? 'The preamble changed on both sides and the edits clash. Reconcile it in your editor, then refresh the copy.' : '' });
	return out;
}

/** Where an item stands: taken, left out, or not yet decided; the prose and the preamble are taken or not. */
export function stateOf(c: AdoptionReview, item: Item): State {
	if (item.kind === 'prose') return c.choices.document ? 'taken' : 'undecided';
	if (item.kind === 'preamble') return c.choices.preamble ? 'taken' : 'undecided';
	if (c.choices.keys.includes(item.key)) return 'taken';
	if (c.choices.kept?.includes(item.key)) return 'left';
	return 'undecided';
}

/** The saved choice with one item taken or left. */
export function decision(c: AdoptionReview, item: Item, take: boolean): Decision {
	const d: Decision = { keys: c.choices.keys, kept: c.choices.kept ?? [], document: !!c.choices.document, preamble: !!c.choices.preamble };
	if (item.kind === 'prose') return { ...d, document: take };
	if (item.kind === 'preamble') return { ...d, preamble: take };
	const keys = d.keys.filter((k) => k !== item.key);
	const kept = d.kept.filter((k) => k !== item.key);
	return take ? { ...d, keys: [...keys, item.key], kept } : { ...d, keys, kept: [...kept, item.key] };
}

/** Everything that can be taken, taken: every result that doesn't clash, and the prose and preamble where they changed without clashing. */
export function takeAll(items: Item[]): Decision {
	const can = items.filter((i) => i.can);
	return { keys: can.filter((i) => i.kind === 'result').map((i) => i.key), document: can.some((i) => i.kind === 'prose'), preamble: can.some((i) => i.kind === 'preamble'), kept: [] };
}

/** How many items are taken, left, still to decide, and can't be taken. */
export function tally(c: AdoptionReview, items: Item[]): { taken: number; left: number; undecided: number; clash: number } {
	const t = { taken: 0, left: 0, undecided: 0, clash: 0 };
	for (const i of items) {
		if (!i.can) t.clash++;
		else t[stateOf(c, i)]++;
	}
	return t;
}

/**
 * The blocks Apply asks loom to accept: those of the taken changes the person marked as checked, as the preview names them after taking (`mapping` takes a key to its new id), and only with every block they rest on that the preview holds, since loom refuses an acceptance missing its dependencies.
 */
export function acceptFor(review: IncorporationMathReview, checked: string[], mapping: Record<string, string>): string[] {
	const mapped = (k: string) => {
		const [head, ...rest] = k.split('/');
		return [mapping[head] ?? head, ...rest].join('/');
	};
	const want = new Set(checked.map(mapped));
	const held = new Set(review.items.map((i) => i.key));
	let ok = review.items.filter((i) => want.has(i.key) && !i.unavailable).map((i) => i.key);
	for (let changed = true; changed; ) {
		const set = new Set(ok);
		const next = ok.filter((k) => (review.items.find((i) => i.key === k)?.dependencies ?? []).every((d) => !held.has(d) || set.has(d)));
		changed = next.length !== ok.length;
		ok = next;
	}
	return ok;
}
