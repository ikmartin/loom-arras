// Fetch and validate a manifest. The viewer's only trigger for re-rendering is this file's hash changing (spec README, viewer obligation 3); a version it does not accept yields exactly one diagnostic and nothing else (obligation 4).

import { dataUrl } from '$lib/paths';
import { ACCEPTED_INTERFACE_VERSIONS, type Diagnostic, type Manifest, type Publishes } from './types';

export interface Loaded {
	manifest: Manifest;
	hash: string;
	etag: string | null;
}

export interface Rejected {
	manifest: null;
	diagnostic: Diagnostic;
}

export type LoadResult = Loaded | Rejected;

export async function hashText(text: string): Promise<string> {
	if (globalThis.crypto?.subtle) {
		const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
		return 'sha256:' + Array.from(new Uint8Array(buf), (b) => b.toString(16).padStart(2, '0')).join('');
	}
	let h = 0;
	for (let i = 0; i < text.length; i++) h = (h * 31 + text.charCodeAt(i)) | 0;
	return 'fnv:' + (h >>> 0).toString(16);
}

export function versionDiagnostic(found: unknown): Diagnostic {
	return {
		severity: 'error',
		code: 'arras:interface-version',
		message: `this viewer accepts interface version ${ACCEPTED_INTERFACE_VERSIONS.join(', ')}; the manifest declares ${String(found)}`,
		locations: [],
		keys: []
	};
}

export function checkVersion(data: unknown): Diagnostic | null {
	const v = (data as { interface_version?: unknown } | null)?.interface_version;
	return typeof v === 'number' && ACCEPTED_INTERFACE_VERSIONS.includes(v) ? null : versionDiagnostic(v);
}

/**
 * Fill in every top-level section the publisher left out.
 *
 * A publisher writes what it has: one may have no masters, another no review ledger, and a corpus nobody has worked
 * on yet has no states. The interface says an absent section means an empty one (specs/manifest.md §1),
 * so absence is resolved here, once, and every consumer downstream keeps a total type. Only top-level sections are
 * filled: a malformed *value* is still the publisher's error and is not papered over.
 */
export function normalise(data: Record<string, unknown>): Manifest {
	const m = { ...data } as Record<string, unknown>;
	for (const k of ['masters', 'canon', 'relations', 'edges', 'diagnostics', 'search'])
		if (m[k] === undefined || m[k] === null) m[k] = [];
	for (const k of ['nodes', 'keys', 'regions', 'inclusion', 'annotations', 'threads', 'tags', 'taxa', 'references'])
		if (m[k] === undefined || m[k] === null) m[k] = {};
	if (m.macros === undefined || m.macros === null) m.macros = { default: [], sets: {} };
	if (m.states === undefined || m.states === null) m.states = { labels: {}, derived: {} };
	if (m.corpus === undefined || m.corpus === null) m.corpus = { name: '', root_label: '' };
	if (m.publisher === undefined || m.publisher === null) m.publisher = { name: '', version: '' };
	if (typeof m.generated !== 'string') m.generated = '';
	// A publisher that declares `publishes` is believed; one that does not gets the best the data can say. The two are
	// not the same answer -- declared `false` means never, an empty section means only "not right now" -- which is why
	// the field exists. Resolving it here means nothing downstream has to know which of the two it is looking at.
	const declared = m.publishes as Partial<Publishes> | undefined | null;
	const some = (v: unknown) => Object.keys((v ?? {}) as object).length > 0;
	m.publishes = {
		documents: declared?.documents ?? ((m.masters as unknown[]).length > 0 || (m.canon as unknown[]).length > 0),
		review: declared?.review ?? some(m.annotations),
		bibliography: declared?.bibliography ?? some(m.references),
		discussions: declared?.discussions ?? some(m.threads)
	};
	return m as unknown as Manifest;
}

export async function parseManifest(text: string, etag: string | null = null): Promise<LoadResult> {
	let data: unknown;
	try {
		data = JSON.parse(text);
	} catch (err) {
		return {
			manifest: null,
			diagnostic: {
				severity: 'error',
				code: 'arras:manifest-unreadable',
				message: `manifest.json is not valid JSON: ${(err as Error).message}`,
				locations: [],
				keys: []
			}
		};
	}
	const problem = checkVersion(data);
	if (problem) return { manifest: null, diagnostic: problem };
	return { manifest: normalise(data as Record<string, unknown>), hash: await hashText(text), etag };
}

export async function loadManifest(url = dataUrl('manifest.json'), etag: string | null = null): Promise<LoadResult | 'unchanged'> {
	const headers: Record<string, string> = etag ? { 'If-None-Match': etag } : {};
	const res = await fetch(url, { headers, cache: 'no-cache' });
	if (res.status === 304) return 'unchanged';
	if (!res.ok) {
		return {
			manifest: null,
			diagnostic: {
				severity: 'error',
				code: 'arras:manifest-missing',
				message: `${url} returned ${res.status}`,
				locations: [],
				keys: []
			}
		};
	}
	return parseManifest(await res.text(), res.headers.get('ETag'));
}
