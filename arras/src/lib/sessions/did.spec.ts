import { describe, expect, it } from 'vitest';
import type { Manifest, Thread } from '$lib/manifest/types';
import { didOf } from './did';

const ann = (id: string, key: string, body = '') => ({ id, type: 'revision', target: { key }, status: 'open', body_html: body });
const m = { annotations: { a1: ann('a1', 'k-1', '<p>The <em>orbit</em> is finite.</p>'), a2: ann('a2', 'k-2'), a3: ann('a3', 'k-1') } } as unknown as Manifest;
const line = (time: string, command: string, extra: object = {}) => ({ time, command, ...extra }) as Thread['log'][number];

describe('what a session did', () => {
	const log = [
		line('t1', 'loom ai orient'),
		line('t2', 'loom annotate k-1 --type revision', { annotation: 'a1' }),
		line('t3', 'loom compile drafting-ai/x.tex', { names: [{ path: '.loom/copies/x.tex' }] }),
		line('t4', 'loom annotate k-2 --type revision', { annotation: 'a2' }),
		line('t5', 'loom compile drafting-ai/x.tex', { names: [{ path: '.loom/copies/x.tex' }] }),
		line('t6', 'loom annotate --resolve a1', { annotation: 'a1' }),
		line('t7', 'loom annotate k-1 --type revision', { annotation: 'a3' })
	];
	const did = didOf(m, log);

	it('groups the annotations it recorded by the block they are on, each once', () => {
		expect(did.recorded.map((r) => [r.key, r.annotations.map((a) => a.id)])).toEqual([
			['k-1', ['a1', 'a3']],
			['k-2', ['a2']]
		]);
	});
	it('lists every other command once, with how many times, when last, and what it names', () => {
		expect(did.ran).toEqual([
			{ command: 'loom ai orient', count: 1, last: 't1', names: [] },
			{ command: 'loom compile drafting-ai/x.tex', count: 2, last: 't5', names: [{ path: '.loom/copies/x.tex' }] }
		]);
	});
});
