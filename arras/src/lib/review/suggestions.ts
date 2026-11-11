// Suggestions read from the manifest: the open annotations carrying text to put in, whatever their type, the document each is on in the person's words, and who wrote it. Model facts in, display facts out.
import { isAgentDocument } from '$lib/manifest/documents';
import type { Annotation, Manifest } from '$lib/manifest/types';

const file = (p: string) => p.split('/').pop() ?? p;

/** The open annotations carrying text to put in (an empty payload deletes the words it quotes), whatever their type, newest first: neither a reply nor resolved. What Review counts. */
export function toApply(m: Pick<Manifest, 'annotations'>): Annotation[] {
	return newest(Object.values(m.annotations ?? {}).filter((a) => a.payload !== null && a.payload !== undefined && !a.in_reply_to && a.status === 'open'));
}

const newest = (as: Annotation[]) => as.sort((a, b) => (b.created ?? '').localeCompare(a.created ?? ''));

/**
 * The document a suggestion is read in, and the words that say so: "in draft5.tex", or "in examples-shared.tex, the agent's copy of examples.tex". The document it names (`in`) when it names one, else the first live document reading its key, the person's own before an agent's copy; null for a key no live document reads.
 */
export function documentOf(m: Pick<Manifest, 'nodes' | 'keys' | 'masters'> & Partial<Pick<Manifest, 'regions'>>, a: Annotation): { path: string; words: string; copy: boolean } | null {
	const key = a.target.key;
	const owner = m.nodes[key] ? key : (m.keys[key]?.node ?? m.regions?.[key]?.container);
	const reached = (owner && m.nodes[owner]?.reached_by) || [];
	const live = m.masters.filter((d) => !d.closed && !d.context_only && (reached.includes(d.path) || d.path === key));
	const rank = (d: (typeof live)[number]) => (d.path === a.in ? -1 : isAgentDocument(d) ? 2 : d.default ? 0 : 1);
	const doc = [...live].sort((x, y) => rank(x) - rank(y))[0];
	if (!doc) return null;
	const copy = isAgentDocument(doc);
	// a suggestion on a whole document is named by it already
	if (doc.path === key) return { path: doc.path, copy, words: copy ? `the agent's copy of ${file(doc.copy_of ?? '')}` : '' };
	return { path: doc.path, copy, words: copy ? `in ${file(doc.path)}, the agent's copy of ${file(doc.copy_of ?? '')}` : `in ${file(doc.path)}` };
}

/** Who wrote it, as the person reads it: "you" for their own, an agent by the name it gave itself. */
export function writerOf(m: Pick<Manifest, 'reviewer'>, a: Annotation): string {
	const id = a.author?.id ?? '';
	return id && id === m.reviewer?.name ? 'you' : (a.author?.label ?? id);
}
