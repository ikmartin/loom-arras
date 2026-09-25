// The write client against a stubbed publisher: a restarted publisher mints a new token, and a 403 re-probes `/_api` once for it.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { forgetCapabilities, write } from './write';

/** A stub publisher. `token` is what a probe answers now (set it to restart the publisher); `answer` decides a POST's status from the token it carries. Every request is logged as `GET <url>` or `POST <url> <token>`. */
function publisher(answer: (token: string, current: string) => number = (t, c) => (t === c ? 200 : 403)) {
	const state = { token: 'first', log: [] as string[] };
	vi.stubGlobal('fetch', async (url: string, init?: RequestInit) => {
		if (!init) {
			state.log.push(`GET ${url}`);
			return Response.json({ write_api: 1, capabilities: ['session-close'], token: state.token });
		}
		const carried = (init.headers as Record<string, string>)['X-Loom-Token'] ?? '';
		state.log.push(`POST ${url} ${carried}`);
		const status = answer(carried, state.token);
		if (status === 200) return Response.json({ ok: true, result: 'closed' });
		return Response.json({ ok: false, error: { code: status === 403 ? 'forbidden' : 'bad-request', message: `refused with ${status}` } }, { status });
	});
	return state;
}

beforeEach(() => forgetCapabilities());
afterEach(() => vi.unstubAllGlobals());

describe('a write carrying a stale token', () => {
	it('re-probes for the fresh token on a 403 and retries once', async () => {
		const p = publisher();
		expect(await write('session-close', { session: 's-1' })).toEqual({ ok: true, result: 'closed' });
		// the publisher restarts and mints a new token; the page still holds the old probe
		p.token = 'second';
		p.log.length = 0;
		expect(await write('session-close', { session: 's-1' })).toEqual({ ok: true, result: 'closed' });
		expect(p.log).toEqual(['POST /_api/session-close first', 'GET /_api', 'POST /_api/session-close second']);
		// the fresh probe is kept: the next write asks nothing first
		p.log.length = 0;
		await write('session-close', { session: 's-1' });
		expect(p.log).toEqual(['POST /_api/session-close second']);
	});

	it('gives up after one retry, and shows the refusal', async () => {
		const p = publisher(() => 403);
		expect(await write('session-close', { session: 's-1' })).toEqual({ ok: false, error: { code: 'forbidden', message: 'refused with 403' } });
		expect(p.log).toEqual(['GET /_api', 'POST /_api/session-close first', 'GET /_api', 'POST /_api/session-close first']);
	});

	it('does not retry any other refusal', async () => {
		const p = publisher(() => 400);
		expect(await write('session-close', { session: 's-1' })).toEqual({ ok: false, error: { code: 'bad-request', message: 'refused with 400' } });
		expect(p.log).toEqual(['GET /_api', 'POST /_api/session-close first']);
	});
});
