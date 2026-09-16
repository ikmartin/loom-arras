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
		expect(a.startsWith('sha256:')).toBe(true);
	});

	it('accepts interface version 1', async () => {
		const result = await parseManifest(JSON.stringify(minimal));
		expect(result.manifest?.corpus.name).toBe('x');
	});

	it('rejects a version it does not accept with a single diagnostic', () => {
		const d = checkVersion({ interface_version: 99 });
		expect(d?.code).toBe('loom:interface-version');
		expect(checkVersion({})?.code).toBe('loom:interface-version');
	});

	it('rejects unreadable JSON', async () => {
		const result = await parseManifest('{not json');
		expect(result.manifest).toBeNull();
		if (result.manifest === null) expect(result.diagnostic.code).toBe('arras:manifest-unreadable');
	});
});
