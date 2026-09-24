import { describe, expect, it } from 'vitest';
import { isDocument } from './run';
import type { Manifest } from '$lib/manifest/types';

const m = { masters: [{ path: 'drafting/main.tex', title: 'Main', default: true, fragment: 'f' }] } as unknown as Manifest;

describe('a key and a document', () => {
	it('knows a document from a node', () => {
		expect(isDocument(m, 'drafting/main.tex')).toBe(true);
		expect(isDocument(m, 'n-1')).toBe(false);
	});
});
