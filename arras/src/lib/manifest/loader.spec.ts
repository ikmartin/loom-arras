import { describe, expect, it } from 'vitest';
import { checkVersion, hashText, parseManifest } from './loader';

const minimal = { interface_version: 1, corpus: { name: 'x', root_label: 'X' }, nodes: {}, keys: {} };

describe('manifest loader', () => {
	it('hashes text deterministically', async () => {
		const a = await hashText('abc');
		const b = await hashText('abc');
		const c = await hashText('abd');
		expect(a).toBe(b);
		expect(a).not.toBe(c);
		expect(a).toMatch(/^sha256:/);
	});

	it('believes a declared capability, and derives one that is absent', async () => {
		// The whole point of the field: a corpus with no annotations YET and one that will never have them look
		// identical in the data, and only a declaration tells them apart.
		const declared = await parseManifest(
			JSON.stringify({ ...minimal, publishes: { documents: false, review: true }, annotations: {} })
		);
		// review is declared true although `annotations` is empty; bibliography is undeclared, and with no references derives false
		expect(declared.manifest?.publishes).toMatchObject({ documents: false, review: true, bibliography: false });

		const derived = await parseManifest(
			JSON.stringify({ ...minimal, masters: [{ path: 'main.tex' }], threads: { t: {} } })
		);
		expect(derived.manifest?.publishes).toMatchObject({ documents: true, discussions: true, review: false });
	});

	it('accepts interface version 1', async () => {
		const result = await parseManifest(JSON.stringify(minimal));
		expect(result.manifest?.corpus.name).toBe('x');
	});

	it('rejects a version it does not accept with a single diagnostic', () => {
		const d = checkVersion({ interface_version: 99 });
		expect(d?.code).toBe('arras:interface-version');
		expect(checkVersion({})?.code).toBe('arras:interface-version');
	});

	it('rejects unreadable JSON', async () => {
		const result = await parseManifest('{not json');
		expect(result.manifest).toBeNull();
		if (result.manifest === null) expect(result.diagnostic.code).toBe('arras:manifest-unreadable');
	});
});
