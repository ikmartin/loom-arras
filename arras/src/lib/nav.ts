// Routes. Keys may contain / and #; they travel in the rest segment of /node/, with # percent-encoded.
// Every route is composed from the configured base path, never written origin-absolute (plan 0.9.5 R1).
import type { Manifest } from '$lib/manifest/types';
import { isAgentDocument } from '$lib/manifest/documents';
import { route } from '$lib/paths';
import { placeParams, resultPlace } from '$lib/worklink';
export function nodeUrl(key: string): string {
	return route('/node/' + key.split('/').map(encodeURIComponent).join('/'));
}

export function keyFromParam(param: string): string {
	return param.split('/').map(decodeURIComponent).join('/');
}

/** A document's name, its address under /master/: its path without `.tex`, kept as a path (loom's `paths.document_name`), so two documents of one stem in two directories never share it. */
export function masterName(path: string): string {
	return path.replace(/\.tex$/, '');
}

export function masterUrl(path: string): string {
	return route('/master/' + masterName(path).split('/').map(encodeURIComponent).join('/'));
}

export function reviewUrl(masterPath?: string, key?: string): string {
	const query = masterPath ? '?document=' + encodeURIComponent(masterPath) : '';
	return route('/review') + query + (key ? '#review-' + anchorId(key) : '');
}

/** A landmark's address under /canon/: its file's stem, which the history keeps unique. */
export function canonStem(path: string): string {
	return path.split('/').pop()?.replace(/\.tex$/, '') ?? path;
}

export function canonUrl(path: string): string {
	return route('/canon/' + encodeURIComponent(canonStem(path)));
}

/** A cited work's page in the Library, which is where its digest, its proposals, its links and the paper itself are read. */
export function workUrl(citekey: string): string {
	return route('/library/' + encodeURIComponent(citekey));
}

export function tagUrl(tag: string): string {
	return route('/tag/' + encodeURIComponent(tag));
}

export function taxonUrl(slug: string): string {
	return route('/taxon/' + encodeURIComponent(slug));
}

/** A session or run, read as a session item: its record and its discussion (plan 0.13.3 E1). */
export function threadUrl(id: string): string {
	return route('/session/' + encodeURIComponent(id));
}


/**
 * The publisher's slug rule, `[^A-Za-z0-9]+` to `-`, trimmed and lowercased (loom `render/convert.py::slug`).
 * Both sides must agree or a link into a document lands nowhere, which is how equation references came to point at `#eq-fix` when the element was `#sy-0001-eq-fix`.
 */
export function anchorId(key: string): string {
	return key.replace(/[^A-Za-z0-9]+/g, '-').replace(/^-+|-+$/g, '').toLowerCase() || 'x';
}

/** A link into a master's rendered document, at the element for `key`. */
export function readUrl(masterPath: string, key?: string): string {
	return masterUrl(masterPath) + (key ? '#' + anchorId(key) : '');
}

/** A block in its document with Review's panel beside it: why it waits, and Accept. `cause`, an index into its acceptance's causes, opens on that change. */
export function reviewReadUrl(masterPath: string, key: string, cause?: number): string {
	const q = new URLSearchParams({ review: key });
	if (cause !== undefined) q.set('cause', String(cause));
	return masterUrl(masterPath) + '?' + q + '#' + anchorId(key);
}

/**
 * Where a link to `key` goes: a cited result to its paper at its page, anything else to its page, resolved through its owner when the key has no page of its own.
 *
 * An unlabelled proof gets a review key but no node entry, so linking it directly lands on "Unknown key"; `keys[key].node` names the statement that owns it, and the proof is an anchor within that page. A result with no paper to open at a page goes to its digest node's page, which is also where `nodeUrl` always goes.
 */
export function keyUrl(m: KeyIndex | null, key: string): string {
	const at = resultPlace(m, key);
	if (at) return workUrl(at.citekey) + '?' + placeParams({ page: at.page, result: at.result }).toString();
	return keyTarget(m, key) ?? nodeUrl(key);
}

type KeyIndex = Pick<Manifest, 'nodes'> & Partial<Pick<Manifest, 'keys' | 'references'>>;

/**
 * Where Review opens `key`: in the document that reads it, at its place (V7), with the annotation `note` open there when one is named; a key that is a document opens the document; a cited result, or one no live document reads, goes where `keyUrl` sends it.
 *
 * The document is the first live document that reaches the key: the person's own first, the default one leading, then an agent's copy, for a result of the copy's own. A proof with no node of its own is read through the statement that owns it.
 */
export function placeUrl(m: (KeyIndex & Partial<Pick<Manifest, 'masters'>>) | null, key: string, note?: string): string {
	const asked = note ? '?note=' + encodeURIComponent(note) : '';
	// a note on a whole document is read at the document's head
	if (m?.masters?.some((d) => d.path === key)) return masterUrl(key) + asked;
	const owner = m?.nodes[key] ? key : m?.keys?.[key]?.node;
	const node = owner ? m?.nodes[owner] : undefined;
	// the person's own documents first, the default leading, then an agent's copy, which is where a result of the copy's own lives
	const live = (m?.masters ?? []).filter((d) => !d.closed && !d.context_only);
	const rank = (d: (typeof live)[number]) => (isAgentDocument(d) ? 2 : d.default ? 0 : 1);
	const doc = node && [...live].sort((a, b) => rank(a) - rank(b)).find((d) => node.reached_by?.includes(d.path));
	if (!doc) return keyUrl(m, key) + (note ? (keyUrl(m, key).includes('?') ? '&' : '?') + 'note=' + encodeURIComponent(note) : '');
	return masterUrl(doc.path) + asked + '#' + anchorId(key);
}

/**
 * The page for `key`, or `null` when nothing in the manifest has one.
 *
 * A diagnostic names whatever it is about, which includes file containers such as `nodes/sy-0002.tex`; those have no page, and linking them lands on "Unknown key". A caller that can render plain text uses this and links only what resolves.
 */
export function keyTarget(m: KeyIndex | null, key: string): string | null {
	if (!m) return null;
	if (m.nodes[key]) return nodeUrl(key);
	const owner = m.keys?.[key]?.node;
	if (owner && m.nodes[owner]) return nodeUrl(owner) + '#' + anchorId(key);
	return null;
}
