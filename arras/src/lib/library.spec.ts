import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import type { Manifest } from '$lib/manifest/types';
import { reachedExternal } from '$lib/reached';
import { ledgerRow, ledgerRows, needsWork, readFrom } from './library';

const fixture = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8')) as Manifest;

describe('the ledger', () => {
	it('counts a digest, and of it what the corpus leans on', () => {
		const r = ledgerRow(fixture, fixture.references.Kre99, reachedExternal(fixture));
		expect(r).toMatchObject({ digest: 2, filed: false });
		expect(r.used).toBeGreaterThan(0);
		expect(r.used).toBeLessThanOrEqual(r.digest);
	});

	it('says what needs work: a statement to judge, or a question open on its pages or its results', () => {
		const m = structuredClone(fixture);
		const ref = m.references.Kre99;
		expect(needsWork(ledgerRow(m, ref, new Set()))).toBe(false);
		ref.results = { 'Kre99-x': { state: 'proposed' } as never };
		expect(ledgerRow(m, ref, new Set()).proposed).toBe(1);
		expect(needsWork(ledgerRow(m, ref, new Set()))).toBe(true);
		ref.results = {};
		ref.reading = { total: 2, open: 1 };
		expect(ledgerRow(m, ref, new Set()).open).toBe(1);
		expect(needsWork(ledgerRow(m, ref, new Set()))).toBe(true);
	});

	it("counts a work's results by who stands behind them, and only a proposal needs work", () => {
		const m = structuredClone(fixture);
		const ref = m.references.Kre99;
		ref.results = {
			'Kre99-a': { state: 'extracted' } as never,
			'Kre99-b': { state: 'extracted' } as never,
			'Kre99-c': { state: 'verified' } as never,
			'Kre99-d': { state: 'discarded' } as never
		};
		expect(ledgerRow(m, ref, new Set())).toMatchObject({ extracted: 2, verified: 1, proposed: 0 });
		expect(needsWork(ledgerRow(m, ref, new Set()))).toBe(false);
	});

	it('says when the results were read off another version than the one cited', () => {
		const ref = structuredClone(fixture.references.Kre99);
		ref.results = { 'Kre99-a': { state: 'extracted' } as never };
		expect(readFrom(ref)).toBeNull();
		ref.results['Kre99-a'].version = { extracted_from: 'arXiv:math/9810166v2', cited: 'doi:10.1007/s002220050351' };
		expect(readFrom(ref)).toBe('Read from arXiv:math/9810166v2; the bibliography cites the published version.');
		ref.results['Kre99-a'].version = { extracted_from: 'arXiv:math/9810166v2', cited: 'work:1a2b3c4d' };
		expect(readFrom(ref)).toContain('a version it does not identify');
	});

	it("folds a version into its work's row, which names it", () => {
		const m = structuredClone(fixture);
		m.references.Kre99.results = { 'Kre99-a': { state: 'extracted' } as never };
		m.references.Kre99A = {
			...structuredClone(m.references.Kre99),
			citekey: 'Kre99A',
			version_of: 'Kre99',
			digest: null,
			results: { 'Kre99A-b': { state: 'extracted' } as never, 'Kre99A-c': { state: 'proposed' } as never }
		};
		m.references.Kre99.versions = [{ citekey: 'Kre99A', work: 'arXiv:math/9810166v1', artifacts: { dir: 'x', pdf: true, source: false } }];
		const rows = ledgerRows(m, new Set());
		expect(rows.map((r) => r.citekey)).toEqual(Object.keys(fixture.references));
		expect(rows.find((r) => r.citekey === 'Kre99')).toMatchObject({ versions: ['Kre99A'], extracted: 2, proposed: 1 });
		// a version whose work is not in the manifest keeps its own row
		delete m.references.Kre99;
		expect(ledgerRows(m, new Set()).map((r) => r.citekey)).toContain('Kre99A');
	});

	it('claims no digest for a work nothing was read off', () => {
		const r = ledgerRow(fixture, fixture.references.Har77, new Set());
		expect(r.digest).toBe(0);
		expect(r.used).toBe(0);
	});
});
