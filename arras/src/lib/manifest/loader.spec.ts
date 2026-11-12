import { describe, expect, it } from 'vitest';
import { hashText, parseManifest } from './loader';

const manifest = { corpus: { name: 'x', root_label: 'X' }, nodes: {}, keys: {} };

describe('manifest loader', () => {
	it('hashes text deterministically', async () => {
		const a = await hashText('abc');
		const b = await hashText('abc');
		const c = await hashText('abd');
		expect(a).toBe(b);
		expect(a).not.toBe(c);
		expect(a).toMatch(/^sha256:/);
	});

	it('reads a manifest as written', async () => {
		const result = await parseManifest(JSON.stringify(manifest));
		expect(result.manifest?.corpus.name).toBe('x');
	});

	it('rejects unreadable JSON', async () => {
		const result = await parseManifest('{not json');
		expect(result.manifest).toBeNull();
		if (result.manifest === null) expect(result.diagnostic.code).toBe('arras:manifest-unreadable');
	});
});
