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

export async function hashText(text: string): Promise<string> {
	if (globalThis.crypto?.subtle) {
		const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
		return 'sha256:' + Array.from(new Uint8Array(buf), (b) => b.toString(16).padStart(2, '0')).join('');
	}
	let h = 0;
	for (let i = 0; i < text.length; i++) h = (h * 31 + text.charCodeAt(i)) | 0;
	return 'fnv:' + (h >>> 0).toString(16);
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
	return { manifest: data as Manifest, hash: await hashText(text), etag };
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
