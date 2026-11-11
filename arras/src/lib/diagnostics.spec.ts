import { describe, expect, it } from 'vitest';
import { byWork, groupProblems, ownerOf, partsOf, splitFixes, titleOf, workOf } from './diagnostics';
import type { Diagnostic, Manifest } from './manifest/types';

const d = (code: string, more: Partial<Diagnostic> = {}): Diagnostic => ({ severity: 'error', code, message: `${code} said`, locations: [], keys: [], ...more });

describe('Problems', () => {
	it('says whose each diagnostic is, the person being whose a publisher that does not say leaves it', () => {
		expect(ownerOf(d('dangling-link'))).toBe('person');
		expect(ownerOf(d('dangling-link', { owner: 'copy' }))).toBe('copy');
		expect(ownerOf(d('dangling-link', { owner: 'work' }))).toBe('work');
		expect(ownerOf(d('dangling-link', { owner: 'someone new' }))).toBe('person');
	});

	it("puts the person's errors and warnings first and every remark apart, whoever's it is", () => {
		const parts = partsOf([
			d('a'),
			d('b', { severity: 'warning' }),
			d('c', { owner: 'copy' }),
			d('e', { owner: 'work' }),
			d('f', { severity: 'info', owner: 'work' }),
			d('g', { severity: 'info' })
		]);
		expect([parts.yours, parts.copy, parts.works, parts.remarks].map((xs) => xs.map((x) => x.code))).toEqual([['a', 'b'], ['c'], ['e'], ['f', 'g']]);
	});

	it('titles a problem by what is wrong, two codes that say one thing as one group, and an unknown code by its message', () => {
		expect(titleOf(d('dangling-link'))).toBe('A reference points nowhere');
		expect(titleOf(d('x:snippet-failed', { severity: 'warning' }))).toBe('TeX could not make a text, shown as its source');
		expect(titleOf(d('zzz:made-up', { message: 'Something new.' }))).toBe('Something new.');
		const groups = groupProblems([d('zzz:made-up', { severity: 'info' }), d('loom:duplicate-label'), d('duplicate-id'), d('duplicate-id'), d('dangling-link', { severity: 'warning' })]);
		expect(groups.map((g) => [g.title, g.items.length, g.codes])).toEqual([
			['Defined twice', 3, ['loom:duplicate-label', 'duplicate-id']],
			['A reference points nowhere', 1, ['dangling-link']],
			['zzz:made-up said', 1, ['zzz:made-up']]
		]);
	});

	it("finds a cited work's diagnostic its work by the fix that digests it again, else by its results", () => {
		const m = { nodes: { 'Kre99-thm-2.1': { digest: 'Kre99', file: '.loom/digests/Kre99.tex' } } } as unknown as Pick<Manifest, 'nodes'>;
		const again = d('dangling-link', { owner: 'work', fixes: [{ label: 'digest Man12 again', command: 'x', act: { endpoint: 'library-update', body: { works: ['Man12'], redo: true, steps: ['extract'] } } }] });
		const keyed = d('loom:converter-fallback', { owner: 'work', keys: ['Kre99-thm-2.1'] });
		const located = d('loom:missing-package', { owner: 'work', locations: [{ file: '.loom/digests/Kre99.tex', line: 1 }] });
		expect([workOf(m, again), workOf(m, keyed), workOf(m, located), workOf(m, d('x', { owner: 'work' }))]).toEqual(['Man12', 'Kre99', 'Kre99', '']);
		expect(byWork(m, [keyed, again, keyed]).map((w) => [w.work, w.items.length])).toEqual([['Kre99', 2], ['Man12', 1]]);
	});

	it('offers a fix with an act as a button and every other as a command to copy', () => {
		const { acts, commands } = splitFixes(d('loom:undigested-citekey', { fixes: [{ label: 'digest it', command: 'a', act: { endpoint: 'library-update', body: { works: ['Har77'] } } }, { label: 'by hand', command: 'b' }] }));
		expect([acts.map((f) => f.command), commands.map((f) => f.command)]).toEqual([['a'], ['b']]);
	});
});
