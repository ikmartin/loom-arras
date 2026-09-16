// Fetch and validate a manifest. The viewer's only trigger for re-rendering is this file's hash changing (spec README, viewer obligation 3); a version it does not accept yields exactly one diagnostic and nothing else (obligation 4).

import { ACCEPTED_INTERFACE_VERSIONS, type Diagnostic, type Manifest } from './types';

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
		code: 'loom:interface-version',
		message: `this viewer accepts interface version ${ACCEPTED_INTERFACE_VERSIONS.join(', ')}; the manifest declares ${String(found)}`,
		locations: [],
		keys: []
	};
}

export function checkVersion(data: unknown): Diagnostic | null {
	const v = (data as { interface_version?: unknown } | null)?.interface_version;
	return typeof v === 'number' && ACCEPTED_INTERFACE_VERSIONS.includes(v) ? null : versionDiagnostic(v);
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
	return { manifest: data as Manifest, hash: await hashText(text), etag };
}

export async function loadManifest(url = '/build/manifest.json', etag: string | null = null): Promise<LoadResult | 'unchanged'> {
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
