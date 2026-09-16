import { describe, expect, it } from 'vitest';
import { nodeBadge, stateBadge } from './badges';
import type { Key, Manifest, Node } from './manifest/types';

const states = {
	labels: { draft: { label: 'draft', color: 'neutral' }, accepted: { label: 'accepted', color: 'positive' }, stale: { label: 'stale', color: 'warning', modifier: true }, incomplete: { label: 'incomplete', color: 'negative' } },
	derived: { proved: { label: 'proved', color: 'positive' }, settled: { label: 'settled', color: 'positive-strong' } }
};

function key(k: string, node: string, state: string, extra: Partial<Key> = {}): Key {
	return { key: k, node, kind: k.includes('/proof') ? 'proof' : 'statement', file: 'f', src: [0, 1], hash: 'sha256:0', incomplete: [], state, reviews: { latest_current: null, latest_any: null, open: {}, detached: 0 }, uses: [], closure: [], previous_key_match: null, ...extra };
}

function node(id: string, extra: Partial<Node> = {}): Node {
	return { id, kind: 'environment', taxon: 'Lemma', aliases: [], tags: [], file: 'f', src: [0, 1], fragment: 'x', numbers: {}, reached_by: [], parent: {}, children: [], proofs: [], external: false, digest: null, incomplete: [], state: 'draft', derived: {}, ...extra };
}

const base = { states, keys: {}, nodes: {} } as unknown as Manifest;

describe('badge composition', () => {
	it('shows the state label and the stale modifier', () => {
		const k = key('a', 'a', 'accepted', { acceptance: { author: 'x', date: '2026-09-16T00:00:00Z', fresh: false } });
		expect(stateBadge(base, k).map((p) => p.text)).toEqual(['accepted', 'stale']);
	});

	it('renders an unknown state label generically', () => {
		const k = key('a', 'a', 'mysterious');
		expect(stateBadge(base, k)).toEqual([{ text: 'mysterious', color: 'neutral' }]);
	});

	it('incomplete overrides everything', () => {
		const m = { ...base, keys: { a: key('a', 'a', 'accepted') } } as Manifest;
		expect(nodeBadge(m, node('a', { incomplete: ['todo'] })).map((p) => p.text)).toEqual(['incomplete']);
	});

	it('combines statement, best proof, and derived labels', () => {
		const m = {
			...base,
			keys: { a: key('a', 'a', 'accepted'), 'a/proof': key('a/proof', 'a', 'draft'), 'a/proof/2': key('a/proof/2', 'a', 'accepted', { acceptance: { author: 'x', date: 'd', fresh: false } }) }
		} as Manifest;
		const parts = nodeBadge(m, node('a', { proofs: ['a/proof', 'a/proof/2'], derived: { proved: true, settled: false } })).map((p) => p.text);
		expect(parts).toEqual(['statement accepted', 'proof accepted', 'proof stale', 'proved']);
	});
});
