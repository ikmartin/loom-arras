// What a run says about a document: which document it is about, which of its findings are about the document as a whole, and which of them no longer line up with the text they were written against (plan 0.11 Parts B and C).
//
// Model facts in, display facts out, like `badges.ts` and `reached.ts`. Nothing here touches the DOM, so the split view's decisions are testable without a browser and the same derivation serves the run page, a node page and anything else that wants to know what a run found.

import type { Annotation, Manifest, Thread } from '$lib/manifest/types';

/** Worst first. An annotation with no severity sorts after every graded one: ungraded is not a grade. */
const RANK: Record<string, number> = { major: 0, moderate: 1, minor: 2 };

export interface Findings {
	/** Findings whose target is a document rather than a key: about the thing the left pane is showing as a whole. */
	document: Annotation[];
	/** Findings about one node inside it, worst first. */
	node: Annotation[];
}

/** Whether a key names a document rather than a node. Masters are keyed by path, and an annotation's target may be a path as easily as a key. */
export function isDocument(m: Manifest, key: string): boolean {
	return m.masters.some((x) => x.path === key);
}

/**
 * The document a run is about, by path.
 *
 * A run that annotated the document itself names it outright. Otherwise the document is the one that reaches its first annotated node, which is what a reader wants to see the finding in. A run whose nodes are in no document has none, and the split view shows the nodes instead.
 */
export function documentOf(m: Manifest, thread: Thread): string | null {
	const named = thread.targets.find((k) => isDocument(m, k));
	if (named) return named;
	for (const key of thread.targets) {
		const node = m.nodes[key] ?? m.nodes[m.keys[key]?.node ?? ''];
		const reached = node?.reached_by?.[0];
		if (reached) return reached;
	}
	return null;
}

/** Every finding this run made, split by what it is about and ranked worst first. Replies and discarded findings are not findings. */
export function findingsOf(m: Manifest, thread: Thread): Findings {
	const mine = Object.values(m.annotations).filter((a) => a.run === thread.id && !a.in_reply_to && !a.discarded);
	const by = (a: Annotation, b: Annotation) =>
		(RANK[a.severity ?? ''] ?? 9) - (RANK[b.severity ?? ''] ?? 9) || a.created.localeCompare(b.created);
	return {
		document: mine.filter((a) => isDocument(m, a.target.key)).sort(by),
		node: mine.filter((a) => !isDocument(m, a.target.key)).sort(by)
	};
}

/**
 * What the left pane says about the version a finding was written against.
 *
 * A run is made against a text, and the text moves. `null` when the anchor still matches, so the pane says nothing in the ordinary case.
 *
 * The publisher records the hash an annotation was written against and the key's hash now, but not which recorded version the old hash was, so this names the version the text is at and not the one it was: "changed since, now @2" rather than "@1, now @2". Saying less is better than naming a version nobody can look up.
 */
export function versionNote(m: Manifest, a: Annotation): string | null {
	const key = m.keys[a.target.key];
	if (!key || !a.target.hash || !key.hash || a.target.hash === key.hash) return null;
	const now = key.version?.name || key.version?.step;
	return now ? `changed since this run, now @${now}` : 'changed since this run';
}

/** Whether any finding in this run stands against a text that has since moved, which is when the pane is worth showing at all. */
export function anyMoved(m: Manifest, thread: Thread): boolean {
	const f = findingsOf(m, thread);
	return [...f.document, ...f.node].some((a) => versionNote(m, a) !== null);
}

/** The runs and comment sessions that touched this document, newest first, for the pane's run picker. */
export function runsOn(m: Manifest, doc: string | null): Thread[] {
	if (!doc) return [];
	const keys = new Set<string>([doc]);
	for (const [key, node] of Object.entries(m.nodes)) if (node.reached_by?.includes(doc)) keys.add(key);
	for (const [key, k] of Object.entries(m.keys)) if (keys.has(k.node)) keys.add(key);
	const touched = new Set<string>();
	for (const a of Object.values(m.annotations)) if (keys.has(a.target.key)) touched.add(a.run);
	return Object.values(m.threads)
		.filter((t) => touched.has(t.id) && !t.discarded)
		.sort((a, b) => b.created.localeCompare(a.created));
}
