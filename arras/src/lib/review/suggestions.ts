// Suggested edits read from the manifest (specs/manifest.md §9.2): the open ones, the document each is on in the person's words, who wrote it, and the open one that answers an annotation. Model facts in, display facts out.
import { isAgentDocument } from '$lib/manifest/documents';
import type { Manifest, SuggestedEdit } from '$lib/manifest/types';

const file = (p: string) => p.split('/').pop() ?? p;

/** The open suggested edits, newest first: what Review counts. */
export function openEdits(m: Pick<Manifest, 'suggested_edits'>): SuggestedEdit[] {
	return Object.values(m.suggested_edits ?? {})
		.filter((e) => e.status === 'open')
		.sort((a, b) => (b.created ?? '').localeCompare(a.created ?? '') || a.id.localeCompare(b.id));
}

/** The open suggested edit that answers annotation `id`, if one does. */
export function editAnswering(m: Pick<Manifest, 'suggested_edits'> | null, id: string): SuggestedEdit | undefined {
	return openEdits(m ?? {}).find((e) => e.answers === id);
}

/**
 * The document a key is read in, and the words that say so: "in draft5.tex", or "in examples-shared.tex, the agent's copy of examples.tex". The document `inDoc` names when it names one, else the first live document reading the key, the person's own before an agent's copy; null for a key no live document reads.
 */
export function documentOf(m: Pick<Manifest, 'nodes' | 'keys' | 'masters'> & Partial<Pick<Manifest, 'regions'>>, at: { target: { key: string }; in?: string | null }): { path: string; words: string; copy: boolean } | null {
	const key = at.target.key;
	const owner = m.nodes[key] ? key : (m.keys[key]?.node ?? m.regions?.[key]?.container);
	const reached = (owner && m.nodes[owner]?.reached_by) || [];
	const live = m.masters.filter((d) => !d.closed && !d.context_only && (reached.includes(d.path) || d.path === key));
	const rank = (d: (typeof live)[number]) => (d.path === at.in ? -1 : isAgentDocument(d) ? 2 : d.default ? 0 : 1);
	const doc = [...live].sort((x, y) => rank(x) - rank(y))[0];
	if (!doc) return null;
	const copy = isAgentDocument(doc);
	// one on a whole document is named by it already
	if (doc.path === key) return { path: doc.path, copy, words: copy ? `the agent's copy of ${file(doc.copy_of ?? '')}` : '' };
	return { path: doc.path, copy, words: copy ? `in ${file(doc.path)}, the agent's copy of ${file(doc.copy_of ?? '')}` : `in ${file(doc.path)}` };
}

/** Who wrote it, as the person reads it: "you" for their own, an agent by the name it gave itself. */
export function writerOf(m: Pick<Manifest, 'reviewer'>, by: { author?: { id: string; label?: string } }): string {
	const id = by.author?.id ?? '';
	return id && id === m.reviewer?.name ? 'you' : (by.author?.label ?? id);
}
