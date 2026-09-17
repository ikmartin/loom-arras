import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { neighbourhood } from './local';
import { graphInput, PAPER } from './layout';
import type { Manifest } from '$lib/manifest/types';

const m = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8')) as Manifest;

describe('the local graph', () => {
	it('holds the centre and exactly its direct neighbours at depth 1', () => {
		const id = Object.keys(m.nodes).find((k) => m.edges.some((e) => e.from === k || e.to === k))!;
		const n = neighbourhood(m, id, 1);
		expect(n.nodes[0]).toBe(id);
		expect(n.distance.get(id)).toBe(0);
		for (const other of n.nodes.slice(1)) {
			expect(n.distance.get(other)).toBe(1);
			expect(n.links.some((l) => (l.from === id && l.to === other) || (l.to === id && l.from === other))).toBe(true);
		}
	});

	it('grows with depth and never loses a node', () => {
		const id = Object.keys(m.nodes).find((k) => m.edges.some((e) => e.from === k || e.to === k))!;
		const one = new Set(neighbourhood(m, id, 1).nodes);
		const two = new Set(neighbourhood(m, id, 2).nodes);
		for (const x of one) expect(two.has(x)).toBe(true);
		expect(neighbourhood(m, id, 0).nodes).toEqual([id]);
	});

	it('draws a proof as its statement', () => {
		const proof = Object.values(m.keys).find((k) => k.key !== k.node && m.nodes[k.node])!;
		expect(neighbourhood(m, proof.key, 1).nodes[0]).toBe(proof.node);
	});

	it('draws nothing for a key the manifest does not know', () => {
		expect(neighbourhood(m, 'no-such-node', 2).nodes).toEqual([]);
	});
});


describe('the work graph', () => {
	it('draws each cited work as one node and keeps the corpus own results', () => {
		const { nodes, edges } = graphInput(m, { external: 'papers' });
		const ids = new Set(nodes.map((n) => n.id));
		expect(ids.has(PAPER + 'Kre99')).toBe(true); // digested, and used
		expect(ids.has(PAPER + 'Har77')).toBe(true); // cited and never digested, which the expanded graph cannot show
		expect([...ids].some((id) => m.nodes[id]?.external)).toBe(false); // no external result survives as itself
		for (const e of edges) {
			expect(ids.has(e.from) && ids.has(e.to)).toBe(true);
		}
		const toKre = edges.filter((e) => e.to === PAPER + 'Kre99');
		expect(toKre.length).toBeGreaterThan(0);
		expect(toKre.every((e) => (e.count ?? 0) >= 1)).toBe(true);
	});

	it('contracts a digest section, which is not marked external, into its paper', () => {
		const fake = JSON.parse(JSON.stringify(m)) as typeof m;
		const file = fake.references.Kre99.digest!.file;
		fake.nodes['Kre99-sec-1'] = { ...fake.nodes['Kre99-thm-2.1'], id: 'Kre99-sec-1', kind: 'section', external: false, digest: null, file };
		fake.edges = [...fake.edges, { from: 'sy-0003', to: 'Kre99-sec-1', kind: 'prose' } as (typeof fake.edges)[number]];
		const { nodes, edges } = graphInput(fake, { external: 'papers' });
		expect(nodes.some((n) => n.id === 'Kre99-sec-1')).toBe(false);
		expect(edges.some((e) => e.from === 'sy-0003' && e.to === PAPER + 'Kre99')).toBe(true);
	});

	it('is the expanded graph with its external results removed, apart from the paper nodes', () => {
		const expanded = graphInput(m, { external: 'none' });
		const papers = graphInput(m, { external: 'papers' });
		const own = new Set(expanded.nodes.map((n) => n.id));
		expect(papers.nodes.filter((n) => !n.id.startsWith(PAPER)).map((n) => n.id).sort()).toEqual([...own].sort());
	});
});
