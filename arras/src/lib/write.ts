// The viewer's client for the publisher's write API (specs/write-api.md, plan 0.11 Part H).
//
// Detected, never assumed. The publisher answers `GET /_api` with the capabilities it actually serves, or 404 when it serves none, and a viewer that gets 404 shows no editing affordances at all -- which is how the same bundle reads a corpus published to a static host and edits one served by its own publisher, with no build-time flag deciding which.
//
// Arras writes nothing itself. It asks the publisher to act; sync-incorporate is the one explicit capability that may update author files.

import { base } from '$app/paths';
import { store } from '$lib/manifest/client.svelte';
import { sessionView, writable } from '$lib/sessions/sessions.svelte';
import { judge } from '$lib/outOfStep.svelte';

/** The endpoints that record work into a session, and therefore must name one. An annotation belongs to no session, so its endpoints are not among them; nor are the session verbs, which carry their own subject, nor `locate`, which reads. */
const SESSIONED = new Set(['library-verify', 'library-discard']);

export interface Capabilities {
	write_api: number;
	capabilities: string[];
	/** What every write must carry, from the publisher's own `.loom/serve.json`. Absent from a corpus nobody is serving. */
	token?: string;
	/** Whether the publisher says when it publishes a new manifest, at `/_api/stream` (manifest/stream.ts). */
	stream?: boolean;
	/** The viewer the publisher serves, by its build's version; a page of another version is out of step with it. */
	viewer?: string;
	/** Whether loom has been updated since the publisher started (outOfStep.svelte.ts). */
	stale?: boolean;
	/** The origin an HTML file is framed from, never the viewer's own; absent where none runs, and a page is then drawn with no script. */
	frames?: string;
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
	})().then((caps) => {
		settled = caps;
		judge(caps);
		return caps;
	});
	return probe;
}

/** What the probe answered, once it has; `undefined` until then. Kept so a component mounted after the answer is known does not have to blink while it asks again. */
let settled: Capabilities | null | undefined;

/** Whether one endpoint is served. An endpoint outside the list answers 404, so asking first is what keeps a button from appearing that cannot work. */
export async function can(endpoint: string): Promise<boolean> {
	const caps = await capabilities();
	settled = caps;
	return !!caps?.capabilities?.includes(endpoint);
}

/**
 * Whether one endpoint is served, from the answer already in hand; `undefined` before the first probe returns.
 *
 * The verbs on an annotation are re-mounted whenever its box is re-read, and re-asking asynchronously made the whole
 * row vanish for a frame each time — most visibly right after a write, which is exactly when a reader is looking at it.
 */
export function known(endpoint: string): boolean | undefined {
	return settled === undefined ? undefined : !!settled?.capabilities?.includes(endpoint);
}

export interface WriteResult {
	ok: boolean;
	result?: string;
	/** `fields`, on a form's refusal, says why each field it refused was refused. */
	error?: { code: string; message: string; fields?: Record<string, string> };
	/** `delete`'s answer: the log events it took out, the annotation's and its replies', which `restore` puts back. */
	removed?: Record<string, unknown>[];
}

/** Ask the publisher to write. Errors come back as the publisher's own refusal rather than as an exception, because a refused annotation is an answer a reader needs to see. */
export async function write(endpoint: string, body: Record<string, unknown>): Promise<WriteResult> {
	try {
		if (endpoint === 'review-accept' || endpoint.startsWith('adopt-') || endpoint === 'sync-preview' || endpoint === 'sync-incorporate') {
			body = { reviewer: store.manifest?.reviewer?.name ?? '', ...body };
		}
		// **Every write names its session, and one place puts it there** (plan 0.13.1). The session travels with the
		// write from the writer's own context rather than from a pointer the publisher keeps: a call site that forgot
		// would fall back to that pointer and file work wherever it happened to point. Refusing here rather than at the
		// publisher makes a mis-wired button fail where it was wired, not somewhere in the log.
		if (SESSIONED.has(endpoint) && body.session === undefined) {
			const why = writable(store.manifest);
			if (why) return { ok: false, error: { code: 'no-session', message: why } };
			body = { ...body, session: sessionView.selected };
		}
		// The token is CSRF protection and not a login: a browser blocks a cross-origin response and never the
		// request, so any page the author happens to be reading could otherwise POST into the corpus they are
		// serving. A cross-site form post cannot set a custom header, which is what makes carrying one enough.
		const send = async () => {
			const caps = await capabilities();
			return fetch(apiUrl('/' + endpoint), {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					...(caps?.token ? { 'X-Loom-Token': caps.token } : {})
				},
				body: JSON.stringify(body)
			});
		};
		let res = await send();
		// **A restarted publisher mints a new token**, and the old one is cached for the life of the page — so a tab left open across a restart refused every write with "this request carries no valid X-Loom-Token" until it was reloaded, which is not something a reader should have to work out. A 403 is re-probed and retried once;
		// if the second answer is also 403, it is a real refusal and is shown.
		if (res.status === 403) {
			forgetCapabilities();
			res = await send();
		}
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

/** A read from the publisher that only the viewer may make, carrying the token as a write does: `/jobs`. `null` when no publisher serves it or it refuses. A 403 is re-probed and tried once more, as a write is. */
export async function read<T>(path: string): Promise<T | null> {
	try {
		const get = async () => {
			const caps = await capabilities();
			if (!caps) return null;
			return fetch(apiUrl(path), { headers: caps.token ? { 'X-Loom-Token': caps.token } : {} });
		};
		let res = await get();
		if (res?.status === 403) {
			forgetCapabilities();
			res = await get();
		}
		return res?.ok ? ((await res.json()) as T) : null;
	} catch {
		return null;
	}
}
