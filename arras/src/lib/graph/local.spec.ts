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
		const rest = n.nodes.slice(1);
		expect(rest.filter((other) => n.distance.get(other) !== 1)).toEqual([]);
		expect(rest.filter((other) => !n.links.some((l) => (l.from === id && l.to === other) || (l.to === id && l.from === other)))).toEqual([]);
	});

	it('grows with depth and never loses a node', () => {
		const id = Object.keys(m.nodes).find((k) => m.edges.some((e) => e.from === k || e.to === k))!;
		const one = new Set(neighbourhood(m, id, 1).nodes);
		const two = new Set(neighbourhood(m, id, 2).nodes);
		expect([...one].filter((x) => !two.has(x))).toEqual([]);
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
		expect([...ids]).toContain(PAPER + 'Kre99'); // digested, and used
		expect([...ids]).toContain(PAPER + 'Har77'); // cited and never digested, which the expanded graph cannot show
		expect([...ids].filter((id) => m.nodes[id]?.external)).toEqual([]); // no external result survives as itself
		expect(edges.filter((e) => !ids.has(e.from) || !ids.has(e.to))).toEqual([]);
		const toKre = edges.filter((e) => e.to === PAPER + 'Kre99');
		expect(toKre.length).toBeGreaterThan(0);
		expect(toKre.filter((e) => (e.count ?? 0) < 1)).toEqual([]);
	});

	it('contracts a digest section, which is not marked external, into its paper', () => {
		const fake = JSON.parse(JSON.stringify(m)) as typeof m;
		const file = fake.references.Kre99.digest!.file;
		fake.nodes['Kre99-sec-1'] = { ...fake.nodes['Kre99-thm-2.1'], id: 'Kre99-sec-1', kind: 'section', external: false, digest: null, file };
		fake.edges = [...fake.edges, { from: 'sy-0003', to: 'Kre99-sec-1', kind: 'prose' } as (typeof fake.edges)[number]];
		const { nodes, edges } = graphInput(fake, { external: 'papers' });
		expect(nodes.map((n) => n.id)).not.toContain('Kre99-sec-1');
		expect(edges).toContainEqual(expect.objectContaining({ from: 'sy-0003', to: PAPER + 'Kre99' }));
	});

	it('is the expanded graph with its external results removed, apart from the paper nodes', () => {
		const expanded = graphInput(m, { external: 'none' });
		const papers = graphInput(m, { external: 'papers' });
		const own = new Set(expanded.nodes.map((n) => n.id));
		expect(papers.nodes.filter((n) => !n.id.startsWith(PAPER)).map((n) => n.id).sort()).toEqual([...own].sort());
	});
});
