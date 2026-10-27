import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import type { Manifest } from '$lib/manifest/types';
import { historyOf, landmarkName } from './history';

const fixture = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8')) as Manifest;
const V1 = '.loom/history/0001-widgets-v1/widgets-v1.tex';
const V2 = '.loom/history/0003-widgets-v2/widgets-v2.tex';

describe("a document's history", () => {
	it('is a draft, its landmarks newest first, and its live agent copies', () => {
		const h = historyOf(fixture, 'drafting/main.tex');
		expect(h?.of).toBe('draft');
		if (h?.of !== 'draft') return;
		expect(h.draft).toBe('drafting/main.tex');
		expect(h.at).toBeUndefined();
		expect(h.landmarks.map((c) => c.name)).toEqual(['widgets-v3', 'widgets-v2', 'widgets-v1']);
		expect(h.kept).toEqual([]);
		expect(h.copies.map((x) => x.path)).toEqual(['drafting-ai/aidoc.tex']);
	});

	it("is, for a landmark, its draft's, at the landmark", () => {
		const h = historyOf(fixture, V2);
		expect(h).toMatchObject({ of: 'draft', draft: 'drafting/main.tex', at: V2 });
	});

	it('folds apart the landmarks loom kept itself', () => {
		const m = structuredClone(fixture);
		m.canon![1].kept_for = 'adopt';
		const h = historyOf(m, 'drafting/main.tex');
		if (h?.of !== 'draft') throw new Error('no history');
		expect(h.landmarks.map((c) => c.name)).toEqual(['widgets-v3', 'widgets-v1']);
		expect(h.kept.map((c) => c.name)).toEqual(['widgets-v2']);
	});

	it('is, for an agent copy, the draft it was copied from', () => {
		expect(historyOf(fixture, 'drafting-ai/aidoc.tex')).toEqual({ of: 'copy', copy: 'drafting-ai/aidoc.tex', source: 'drafting/main.tex' });
	});

	it('is nothing for a draft with neither, a landmark no live draft leads to, or a closed copy', () => {
		expect(historyOf(fixture, 'drafting/talk.tex')).toBeNull();
		const m = structuredClone(fixture);
		delete m.canon![0].in;
		expect(historyOf(m, V1)).toBeNull();
		m.masters.find((x) => x.path === 'drafting-ai/aidoc.tex')!.closed = true;
		expect(historyOf(m, 'drafting-ai/aidoc.tex')).toBeNull();
	});
});

describe("a landmark's name", () => {
	it('is its draft and its name, or its stem and step where no live draft leads to it', () => {
		const m = structuredClone(fixture);
		expect(landmarkName(m, m.canon![1])).toBe('main.tex · widgets-v2');
		delete m.canon![0].in;
		expect(landmarkName(m, m.canon![0])).toBe('widgets-v1 @1');
	});
});
