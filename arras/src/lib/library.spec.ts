import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import type { Manifest } from '$lib/manifest/types';
import { reachedExternal } from '$lib/reached';
import { bySection, citedIn, filterResults, keepRow, ledgerRow, ledgerRows, matches, needsWork, problemsOf, readFrom, resultFilters, shelf, workResults } from './library';

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

describe('the shelf', () => {
	it('lists a work once, by title, opening the copy filed: its own, else a version\'s', () => {
		const m = structuredClone(fixture);
		m.references.Kre99A = { ...structuredClone(m.references.Kre99), citekey: 'Kre99A', version_of: 'Kre99', bib: { title: 'A preprint', author: 'Kresch, A.' }, artifacts: { dir: 'x', pdf: true, source: false } };
		const rows = shelf(m);
		expect(rows.map((r) => r.citekey).sort()).toEqual(Object.keys(fixture.references).sort());
		expect(rows.map((r) => r.title)).toEqual([...rows.map((r) => r.title)].sort((a, b) => a.localeCompare(b)));
		const kre = rows.find((r) => r.citekey === 'Kre99')!;
		expect(kre).toMatchObject({ filed: true, opens: 'Kre99A' });
		// a filter finds the work by its version's key or title
		expect(kre.text).toContain('kre99a');
		expect(kre.text).toContain('a preprint');
		m.references.Kre99.artifacts!.pdf = true;
		expect(shelf(m).find((r) => r.citekey === 'Kre99')!.opens).toBe('Kre99');
	});
});

describe("a work's results on its Info", () => {
	/** Kre99 with a second section and a subsection, a verified result, a proposal and a discarded one. */
	function sectioned(): Manifest {
		const m = structuredClone(fixture);
		const ref = m.references.Kre99;
		const node = (id: string, extra: object) => ({ ...m.nodes['Kre99-thm-2.1'], id, ...extra });
		m.nodes['Kre99-sec-2'] = node('Kre99-sec-2', { kind: 'section', title: 'Cycles', children: ['Kre99-sec-2.1', 'Kre99-thm-2.1'] }) as never;
		m.nodes['Kre99-sec-2.1'] = node('Kre99-sec-2.1', { kind: 'section', title: 'Stacks', children: ['Kre99-lem-2.2'] }) as never;
		m.nodes['Kre99-lem-2.2'] = node('Kre99-lem-2.2', { locator: 'Lemma 2.2, p.~5' }) as never;
		m.nodes['Kre99-x'] = node('Kre99-x', { locator: 'Lemma 9, p.~20' }) as never;
		ref.digest!.nodes = ['Kre99-setup', 'Kre99-thm-2.1', 'Kre99-lem-2.2', 'Kre99-gone'];
		ref.proposed = { file: '', fragment: '', nodes: ['Kre99-x'] };
		ref.results = {
			'Kre99-lem-2.2': { state: 'verified' } as never,
			'Kre99-gone': { state: 'discarded' } as never
		};
		return m;
	}

	it("lists them in the paper's order under their innermost section, leaving a discarded one out", () => {
		const m = sectioned();
		const rs = workResults(m, m.references.Kre99, new Set(['Kre99-thm-2.1']));
		expect(rs.map((r) => [r.id, r.state, r.used, r.section])).toEqual([
			['Kre99-setup', 'extracted', false, '1 · Setup'],
			['Kre99-thm-2.1', 'extracted', true, '2 · Cycles'],
			['Kre99-lem-2.2', 'verified', false, '2.1 · Stacks'],
			['Kre99-x', 'proposed', false, '']
		]);
		expect(bySection(rs).map((g) => [g.section, g.results.length])).toEqual([
			['1 · Setup', 1],
			['2 · Cycles', 1],
			['2.1 · Stacks', 1],
			['', 1]
		]);
	});

	it('offers a filter only where it narrows the list, with its count', () => {
		const m = sectioned();
		const rs = workResults(m, m.references.Kre99, new Set(['Kre99-thm-2.1']));
		expect(resultFilters(rs)).toEqual([
			{ filter: 'all', count: 4 },
			{ filter: 'used', count: 1 },
			{ filter: 'verified', count: 1 },
			{ filter: 'proposed', count: 1 }
		]);
		expect(filterResults(rs, 'verified').map((r) => r.id)).toEqual(['Kre99-lem-2.2']);
		expect(resultFilters(workResults(fixture, fixture.references.Kre99, new Set()))).toEqual([]);
	});

	it("names the person's documents that cite a work, with the keys that do, and never an agent's", () => {
		const cites = citedIn(fixture, fixture.references.Kre99);
		expect(cites.length).toBeGreaterThan(0);
		expect(cites.every((c) => !fixture.masters.find((x) => x.path === c.doc)?.copy_of)).toBe(true);
		expect(cites.flatMap((c) => c.keys)).toContain('sy-000A');
		expect(cites.flatMap((c) => c.keys)).not.toContain('sy-000A-ai');
		const m = structuredClone(fixture);
		m.references.Kre99.cited_by = [];
		expect(citedIn(m, m.references.Kre99)).toEqual([]);
	});
});

describe("the library's page", () => {
	it('says what each row needs: authors, by hand, where its digest came from, its overview and where it is cited', () => {
		const m = structuredClone(fixture);
		const kre = ledgerRow(m, m.references.Kre99, reachedExternal(m));
		expect(kre).toMatchObject({ authors: 'Kresch', added: false, overview: false, identified: true });
		expect(kre.cited).toBeGreaterThan(0);
		expect(ledgerRow(m, m.references.Man12, new Set()).cited).toBe(0);
		m.references.Kre99.digest!.method = 'extract';
		m.references.Kre99.added = { when: '2026-11-03T00:00:00Z', who: 'A. Author' };
		expect(ledgerRow(m, m.references.Kre99, new Set())).toMatchObject({ from: 'source', added: true });
		m.references.Kre99.digest!.method = 'pdf';
		expect(ledgerRow(m, m.references.Kre99, new Set()).from).toBe('pages');
	});

	it("names a work's problems, each with its fixes, from the manifest and from the last run on it", () => {
		const m = structuredClone(fixture);
		// the fixture holds no copy of Kre99, whose entry names an arXiv id, and Har77 names none
		expect(problemsOf(m, m.references.Kre99).map((p) => [p.code, p.fixes])).toEqual([['no-copy', ['run', 'upload', 'ignore']]]);
		expect(problemsOf(m, m.references.Har77).map((p) => [p.code, p.fixes])).toEqual([['unidentified', ['upload', 'ignore']]]);
		expect(problemsOf(m, m.references.Man12)).toEqual([]);
		// a work declared unreadable is wanted no longer, so neither is said
		m.references.Har77.unreadable = { why: 'a living document', who: 'A. Author', when: '2026-11-03T00:00:00Z' };
		expect(problemsOf(m, m.references.Har77)).toEqual([]);
		m.references.Man12.version_mismatch = true;
		const run = { citekey: 'Man12', lookup_error: 'zbMATH Open: HTTP 503', discarded: 'the title did not match', extract_error: 'no main file', map_error: '' };
		expect(problemsOf(m, m.references.Man12, run).map((p) => p.code)).toEqual(['another-version', 'lookup-failed', 'not-this-work', 'extract-failed']);
		expect(problemsOf(m, m.references.Man12, run)[1].text).toContain('HTTP 503');
	});

	it('filters by what a work wants and finds it by key, title or author', () => {
		const m = structuredClone(fixture);
		const rows = ledgerRows(m, reachedExternal(m));
		const kre = rows.find((r) => r.citekey === 'Kre99')!;
		const man = rows.find((r) => r.citekey === 'Man12')!;
		expect(keepRow(kre, problemsOf(m, m.references.Kre99), 'needs-you')).toBe(true);
		expect(keepRow(man, [], 'needs-you')).toBe(false);
		expect(keepRow(man, [], 'not-cited')).toBe(true);
		expect(keepRow(kre, [], 'no-paper')).toBe(true);
		expect(keepRow({ ...kre, unreadable: 'a living document' }, [], 'no-paper')).toBe(false);
		expect(keepRow(kre, [], 'no-overview')).toBe(true);
		expect(matches(kre, 'artin kresch')).toBe(true);
		expect(matches(kre, 'kre99')).toBe(true);
		expect(matches(kre, 'manolache')).toBe(false);
	});
});
