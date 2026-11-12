import { describe, expect, it } from 'vitest';
import type { Thread } from '$lib/manifest/types';
import { didOf } from './did';

const line = (time: string, command: string, extra: object = {}) => ({ time, command, ...extra }) as Thread['log'][number];

describe('what a session did', () => {
	const log = [
		line('t1', 'loom ai orient'),
		line('t3', 'loom compile drafting-ai/x.tex', { names: [{ path: '.loom/copies/x.tex' }] }),
		line('t5', 'loom compile drafting-ai/x.tex', { names: [{ path: '.loom/copies/x.tex' }] })
	];

	it('lists every command once, with how many times, when last, and what it names', () => {
		expect(didOf(log).ran).toEqual([
			{ command: 'loom ai orient', count: 1, last: 't1', names: [] },
			{ command: 'loom compile drafting-ai/x.tex', count: 2, last: 't5', names: [{ path: '.loom/copies/x.tex' }] }
		]);
	});
});
