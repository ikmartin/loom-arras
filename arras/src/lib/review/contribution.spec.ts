import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import type { AdoptionReview, IncorporationMathReview, Manifest } from '$lib/manifest/types';
import { acceptFor, decision, itemsOf, stateOf, takeAll, tally } from './contribution';

const fixture = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8')) as Manifest;
const aidoc = () => structuredClone(fixture.contributions!.find((c) => c.kind === 'adopt')) as AdoptionReview;

describe('an agent copy as it is reviewed in one pass (plan 0.25.2)', () => {
	it('names each change by its result in the copy, under its section, and lists the prose after them', () => {
		const items = itemsOf(fixture, aidoc());
		const orbits = items.find((i) => i.key === 'sy-0002')!;
		expect(orbits.name).toBe('Orbits');
		expect(orbits.detail).toContain('Lemma');
		expect(items.at(-1)!.kind).toBe('prose');
	});

	it('marks a clash as not to be taken, with why', () => {
		const widget = itemsOf(fixture, aidoc()).find((i) => i.key === 'sy-0001')!;
		expect(widget.can).toBe(false);
		expect(widget.why).toContain('both changed it');
	});

	it('takes and leaves one item at a time, and takes everything takeable at once', () => {
		const c = aidoc();
		c.choices = { keys: [], document: false, preamble: false, kept: [] };
		const items = itemsOf(fixture, c);
		const orbits = items.find((i) => i.key === 'sy-0002')!;
		expect(decision(c, orbits, true)).toMatchObject({ keys: ['sy-0002'], kept: [] });
		expect(decision(c, orbits, false)).toMatchObject({ keys: [], kept: ['sy-0002'] });
		const all = takeAll(items);
		expect(all.keys).not.toContain('sy-0001');
		expect(all.document).toBe(true);
		c.choices = { ...c.choices, keys: ['sy-0002'], kept: ['sy-0008'] };
		expect(stateOf(c, orbits)).toBe('taken');
		expect(tally(c, items)).toMatchObject({ taken: 1, left: 1, clash: 1 });
	});

	it('accepts only checked blocks the preview holds, under their new ids, and never one without what it rests on', () => {
		const review = { token: 't', reviewer: 'r', items: [
			{ key: 'zk-0009', name: 'New', reason: '', local: null, proposed: { path: '', macros: [] }, unavailable: '' },
			{ key: 'zk-0009/proof', name: 'Proof', reason: '', dependencies: ['zk-0002'], local: null, proposed: { path: '', macros: [] }, unavailable: '' },
			{ key: 'zk-0002', name: 'Old', reason: '', local: null, proposed: { path: '', macros: [] }, unavailable: '' },
			{ key: 'zk-0004', name: 'Held', reason: '', local: null, proposed: { path: '', macros: [] }, unavailable: 'incomplete' }
		] } as IncorporationMathReview;
		expect(acceptFor(review, ['zk-0003', 'zk-0003/proof', 'zk-0004'], { 'zk-0003': 'zk-0009' })).toEqual(['zk-0009']);
		expect(acceptFor(review, ['zk-0003/proof', 'zk-0002'], { 'zk-0003': 'zk-0009' })).toEqual(['zk-0009/proof', 'zk-0002']);
	});
});
