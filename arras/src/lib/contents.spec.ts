import { describe, expect, it } from 'vitest';
import { contentsOf } from './contents';
import type { Manifest } from './manifest/types';

function section(id: string, level: number, title: string, number = '') {
	return { id, kind: 'section', level, title, taxon: 'section', aliases: [], tags: [], file: 'f', src: [0, 1], fragment: 'x', numbers: number ? { 'm.tex': { number } } : {}, reached_by: [], parent: {}, children: [], proofs: [], external: false, digest: null, incomplete: [], state: 'draft', derived: {} };
}

// One section, a file included inside it, a subsection, a paragraph unit, and a second top-level section.
const m = {
	nodes: {
		s1: section('s1', 1, 'Introduction', '1'),
		s2: section('s2', 2, 'Consequences', '1.1'),
		s3: section('s3', 4, 'A paragraph unit'),
		s4: section('s4', 1, 'Results', '2'),
		e1: { id: 'e1', kind: 'environment', taxon: 'Lemma', aliases: [], tags: [], file: 'f', src: [0, 1], fragment: 'x', numbers: {}, reached_by: [], parent: {}, children: [], proofs: [], external: false, digest: null, incomplete: [], state: 'draft', derived: {} }
	},
	inclusion: {
		'm.tex': {
			key: 'm.tex',
			children: [
				{
					key: 's1',
					children: [
						{ key: 'nodes/a.tex', file: 'nodes/a.tex', children: [{ key: 'e1', children: [] }] },
						{ key: 's2', children: [{ key: 's3', children: [] }] }
					]
				},
				{ key: 's4', children: [] }
			]
		}
	}
} as unknown as Manifest;

describe('the contents tree', () => {
	it('is in document order with depth from the sectioning level', () => {
		expect(contentsOf(m, 'm.tex')).toEqual([
			{ key: 's1', title: 'Introduction', number: '1', depth: 0, level: 1 },
			{ key: 's2', title: 'Consequences', number: '1.1', depth: 1, level: 2 },
			{ key: 's4', title: 'Results', number: '2', depth: 0, level: 1 }
		]);
	});

	it('drops units below the cap and keeps them when the cap is raised', () => {
		expect(contentsOf(m, 'm.tex').map((e) => e.key)).not.toContain('s3');
		expect(contentsOf(m, 'm.tex', 4).map((e) => e.key)).toContain('s3');
	});

	it('is empty for a master with no inclusion tree', () => {
		expect(contentsOf(m, 'other.tex')).toEqual([]);
	});
});
