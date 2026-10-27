// A document's history (plan 0.20.6): a draft, the landmarks that kept its text, newest first, and its live agent copies; for an agent copy, the draft it was copied from. What a draft's history menu lists, and what a landmark is named by in its tab and in search. Model facts in, display facts out; nothing here renders.

import type { CanonDoc, Manifest, Master } from '$lib/manifest/types';

export type History =
	| {
			of: 'draft';
			/** The live draft the history is of. */
			draft: string;
			/** The landmark shown, when the document is one of the draft's; absent on the draft itself. */
			at?: string;
			/** The landmarks the author stamped or imported, newest first. */
			landmarks: CanonDoc[];
			/** The landmarks loom kept itself, before an adoption or a sync wrote over the draft, newest first. */
			kept: CanonDoc[];
			/** The draft's live agent copies. */
			copies: Master[];
	  }
	| { of: 'copy'; copy: string; source: string };

/** A master that can be worked in: not closed, not a saved paper context. */
function live(m: Manifest, path: string | undefined): Master | undefined {
	return path ? m.masters.find((x) => x.path === path && !x.closed && !x.context_only) : undefined;
}

/** One of the author's own live drafts, not an agent's. */
function ownDraft(m: Manifest, path: string | undefined): Master | undefined {
	const d = live(m, path);
	return d && d.directory !== 'drafting-ai' ? d : undefined;
}

/**
 * The history a document's menu lists, or null when there is nothing to list.
 *
 * Parameters
 * ----------
 * m : Manifest
 * path : str
 *     A draft's path, a landmark's canon path, or an agent copy's path.
 *
 * Returns
 * -------
 * History | None
 *     A draft's family (for a landmark, its draft's, with `at` set); for a live agent copy, its source. Null for a draft with no landmarks and no copies, a landmark no live draft leads to, a closed copy, and anything else.
 */
export function historyOf(m: Manifest, path: string): History | null {
	const copy = live(m, path);
	if (copy?.directory === 'drafting-ai') return ownDraft(m, copy.copy_of ?? undefined) ? { of: 'copy', copy: path, source: copy.copy_of! } : null;
	const landmark = m.canon?.find((c) => c.path === path);
	const draft = landmark ? landmark.in : path;
	if (!ownDraft(m, draft)) return null;
	const mine = [...(m.canon ?? [])].filter((c) => c.in === draft).reverse();
	const copies = m.masters.filter((x) => x.directory === 'drafting-ai' && x.copy_of === draft && !x.closed && !x.context_only);
	if (!mine.length && !copies.length) return null;
	return { of: 'draft', draft: draft!, ...(landmark ? { at: path } : {}), landmarks: mine.filter((c) => !c.kept_for), kept: mine.filter((c) => c.kept_for), copies };
}

/**
 * A landmark's name, as its tab and search show it: its draft's file and the landmark's name (`main.tex · widgets-v2`) where a live draft leads to it, else its own stem and step (`widgets-v1 @1`).
 *
 * Parameters
 * ----------
 * m : Manifest
 * c : CanonDoc
 *
 * Returns
 * -------
 * str
 */
export function landmarkName(m: Manifest, c: CanonDoc): string {
	const file = (p: string) => p.split('/').pop() ?? p;
	if (ownDraft(m, c.in)) return `${file(c.in!)} · ${c.name ?? c.stem}`;
	return c.step ? `${c.stem} @${Number(c.step)}` : file(c.path);
}
