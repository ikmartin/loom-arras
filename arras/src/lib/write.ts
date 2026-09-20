// The viewer's client for the publisher's write API (specs/write-api.md, plan 0.11 Part H).
//
// Detected, never assumed. The publisher answers `GET /_api` with the capabilities it actually serves, or 404 when it serves none, and a viewer that gets 404 shows no editing affordances at all -- which is how the same bundle reads a corpus published to a static host and edits one served by its own publisher, with no build-time flag deciding which.
//
// Arras still writes nothing itself. It asks the publisher to, and the publisher writes only to its own record locations.

import { base } from '$app/paths';

export interface Capabilities {
	write_api: number;
	capabilities: string[];
}

/** The versions of the write API this viewer knows how to speak. */
const ACCEPTED = [1];

let probe: Promise<Capabilities | null> | null = null;

/** Where the publisher's API lives: beside the app, never inside the corpus, since a corpus may be served from anywhere while the API is the publisher's own. */
function apiUrl(path = ''): string {
	return base + '/_api' + path;
}

/** What the publisher can do, or `null` when it serves no write API. Probed once per page. */
export function capabilities(): Promise<Capabilities | null> {
	probe ??= (async () => {
		try {
			const res = await fetch(apiUrl());
			if (!res.ok) return null;
			const body = (await res.json()) as Capabilities;
			return ACCEPTED.includes(body?.write_api) ? body : null;
		} catch {
			return null;
		}
	})();
	return probe;
}

/** Whether one endpoint is served. An endpoint outside the list answers 404, so asking first is what keeps a button from appearing that cannot work. */
export async function can(endpoint: string): Promise<boolean> {
	const caps = await capabilities();
	return !!caps?.capabilities?.includes(endpoint);
}

export interface WriteResult {
	ok: boolean;
	result?: string;
	error?: { code: string; message: string };
}

/** Ask the publisher to write. Errors come back as the publisher's own refusal rather than as an exception, because a refused comment is an answer a reader needs to see. */
export async function write(endpoint: string, body: Record<string, unknown>): Promise<WriteResult> {
	try {
		const res = await fetch(apiUrl('/' + endpoint), {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		});
		const payload = (await res.json().catch(() => ({}))) as WriteResult;
		if (res.ok && payload.ok) return payload;
		return { ok: false, error: payload.error ?? { code: 'failed', message: `the publisher answered ${res.status}` } };
	} catch (err) {
		return { ok: false, error: { code: 'unreachable', message: (err as Error).message } };
	}
}

/** Forget the probe, for when the publisher may have changed underneath. */
export function forgetCapabilities(): void {
	probe = null;
}
