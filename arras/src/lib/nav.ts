// Routes. Keys may contain / and #; they travel in the rest segment of /node/, with # percent-encoded.
// Every route is composed from the configured base path, never written origin-absolute (plan 0.9.5 R1).
import type { Manifest } from '$lib/manifest/types';
import { route } from '$lib/paths';
import { placeParams, resultPlace } from '$lib/worklink';
export function nodeUrl(key: string): string {
	return route('/node/' + key.split('/').map(encodeURIComponent).join('/'));
}

export function keyFromParam(param: string): string {
	return param.split('/').map(decodeURIComponent).join('/');
}

export function masterUrl(path: string): string {
	const stem = path.split('/').pop()?.replace(/\.tex$/, '') ?? path;
	return route('/master/' + encodeURIComponent(stem));
}

export function masterStem(path: string): string {
	return path.split('/').pop()?.replace(/\.tex$/, '') ?? path;
}

export function reviewUrl(masterPath?: string, key?: string): string {
	const query = masterPath ? '?document=' + encodeURIComponent(masterPath) : '';
	return route('/review') + query + (key ? '#review-' + anchorId(key) : '');
}

export function canonUrl(path: string): string {
	const stem = path.split('/').pop()?.replace(/\.tex$/, '') ?? path;
	return route('/canon/' + encodeURIComponent(stem));
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
