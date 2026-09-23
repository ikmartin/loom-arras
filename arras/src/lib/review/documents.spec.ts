import { describe, expect, it } from 'vitest';
import type { Manifest } from '$lib/manifest/types';
import { documentKeys } from './documents';

describe('documentKeys', () => {
	it('uses the owner node reachability for statements, proofs, shared nodes, and conflicts', () => {
		const manifest = {
			nodes: {
				main: { reached_by: ['drafting/main.tex'] },
				shared: { reached_by: ['drafting/main.tex', 'drafting/talk.tex'] },
				conflict: { reached_by: ['drafting/main.tex', 'drafting/talk.tex'] },
				loose: { reached_by: [] }
			},
			keys: {
				main: { key: 'main', node: 'main' },
				'main/proof': { key: 'main/proof', node: 'main' },
				shared: { key: 'shared', node: 'shared' },
				conflict: { key: 'conflict', node: 'conflict' },
				loose: { key: 'loose', node: 'loose' }
			}
		} as unknown as Manifest;

		expect(documentKeys(manifest, 'drafting/main.tex').map((key) => key.key)).toEqual(['main', 'main/proof', 'shared', 'conflict']);
		expect(documentKeys(manifest, 'drafting/talk.tex').map((key) => key.key)).toEqual(['shared', 'conflict']);
	});
});
