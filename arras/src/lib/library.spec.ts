import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import type { Manifest } from '$lib/manifest/types';
import { reachedExternal } from '$lib/reached';
import { ledgerRow, needsWork } from './library';

const fixture = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8')) as Manifest;

describe('the ledger', () => {
	it('counts a digest, and of it what the corpus leans on', () => {
		const r = ledgerRow(fixture, fixture.references.Kre99, reachedExternal(fixture));
		expect(r.digest).toBe(2);
		expect(r.used).toBeGreaterThan(0);
		expect(r.used).toBeLessThanOrEqual(r.digest);
		expect(r.filed).toBe(false);
	});

	it('says what needs work: a statement to judge, or a question open on its pages or its results', () => {
		const m = structuredClone(fixture);
		const ref = m.references.Kre99;
		expect(needsWork(ledgerRow(m, ref, new Set()))).toBe(false);
		ref.results = { 'Kre99-x': { state: 'proposed' } as never };
		expect(ledgerRow(m, ref, new Set()).unvouched).toBe(1);
		expect(needsWork(ledgerRow(m, ref, new Set()))).toBe(true);
		ref.results = {};
		ref.reading = { total: 2, open: 1 };
		expect(ledgerRow(m, ref, new Set()).open).toBe(1);
		expect(needsWork(ledgerRow(m, ref, new Set()))).toBe(true);
	});

	it('claims no digest for a work nothing was read off', () => {
		const r = ledgerRow(fixture, fixture.references.Har77, new Set());
		expect(r.digest).toBe(0);
		expect(r.used).toBe(0);
	});
});
