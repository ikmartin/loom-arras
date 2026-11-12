// Fetch a manifest. The viewer's only trigger for re-rendering is this file's hash changing (spec README, viewer obligation 3). loom writes every section, and the viewer ships inside loom, so what it reads is taken as written.

import { dataUrl } from '$lib/paths';
import { type Diagnostic, type Manifest } from './types';

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

/** The hash a manifest is known by, of its text or of the bytes it came as; the bytes spare encoding an 11 MB text again. */
export async function hashText(text: string | Uint8Array): Promise<string> {
	const bytes = typeof text === 'string' ? new TextEncoder().encode(text) : text;
	if (globalThis.crypto?.subtle) {
		const buf = await crypto.subtle.digest('SHA-256', bytes as Uint8Array<ArrayBuffer>);
		return 'sha256:' + Array.from(new Uint8Array(buf), (b) => b.toString(16).padStart(2, '0')).join('');
	}
	let h = 0;
	for (const b of bytes) h = (h * 31 + b) | 0;
	return 'fnv:' + (h >>> 0).toString(16);
}

export async function parseManifest(text: string, etag: string | null = null, bytes?: Uint8Array): Promise<LoadResult> {
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
	return { manifest: data as Manifest, hash: await hashText(bytes ?? text), etag };
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
	const bytes = new Uint8Array(await res.arrayBuffer());
	return parseManifest(new TextDecoder().decode(bytes), res.headers.get('ETag'), bytes);
}
