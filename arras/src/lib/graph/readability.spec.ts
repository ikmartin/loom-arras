import { expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import type { Manifest } from '$lib/manifest/types';
import { displayNode } from '$lib/nodes/display';
import { relationships, scopedDrawing } from './relationships';
import { placeLabels } from './labels';
import { graphInput, layout } from './layout';

it('prefers a name without mistaking a document number for global identity', () => {
	const m = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8')) as Manifest;
	const node = Object.values(m.nodes).find((n) => n.kind === 'environment')!;
	node.name = 'Uniform energy bound'; node.title = 'Printed title'; node.numbers = { 'paper.tex': { number: '3.2' } };
	expect(displayNode(m, node.id).name).toBe(node.name);
	expect(displayNode(m, node.id).context).not.toContain('3.2');
	expect(displayNode(m, node.id, 'paper.tex').context).toContain('3.2');
	delete node.name;
	expect(displayNode(m, node.id).name).toBe('Printed title');
});

it('deduplicates direct links and traverses diamonds and cycles without including the selection', () => {
	const edges = [{ from: 'a', to: 'b' }, { from: 'a', to: 'b' }, { from: 'a', to: 'c' }, { from: 'b', to: 'd' }, { from: 'c', to: 'd' }, { from: 'd', to: 'a' }];
	const r = relationships(edges, 'a', 'closure');
	expect([...r.direct].sort()).toEqual(['b', 'c']);
	expect([...r.indirect]).toEqual(['d']);
	expect(r.reached.has('a')).toBe(false);
	expect(r.paths.has('b\0d')).toBe(true);
	expect([...relationships(edges, 'a', 'downstream').direct]).toEqual(['d']);
});

it('restricts document drawings without changing valid drawings', () => {
	expect(scopedDrawing('sections', '')).toBe('dots');
	expect(scopedDrawing('reading', '')).toBe('dots');
	expect(scopedDrawing('box', '')).toBe('box');
	expect(scopedDrawing('reading', 'paper.tex')).toBe('reading');
});

it('reveals labels as dots separate, with stable priorities and viewport clipping', () => {
	const make = (x: number) => [{ id: 'a', x: 100, y: 100, width: 100, radius: 7, priority: 0 }, { id: 'b', x, y: 100, width: 100, radius: 7, priority: 1 }, { id: 'c', x: -100, y: 0, width: 100, radius: 7, priority: 2 }];
	const dense = placeLabels(make(100), 500, 300);
	const spread = placeLabels(make(300), 500, 300);
	expect(dense.has('a')).toBe(true);
	expect(dense.has('c')).toBe(false);
	expect(spread.has('a') && spread.has('b')).toBe(true);
	expect(placeLabels(make(100).reverse(), 500, 300)).toEqual(dense);
});


it('box arrow endpoints retain dependent-to-dependency direction after layered placement', async () => {
	const m = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8')) as Manifest;
	const drawing = await layout(m, { allNodes: true, external: 'all' });
	const boxes = new Map(drawing.nodes.map((n) => [n.id, n]));
	const inside = (p: { x: number; y: number }, id: string) => {
		const n = boxes.get(id)!;
		return p.x >= n.x - 1 && p.x <= n.x + n.w + 1 && p.y >= n.y - 1 && p.y <= n.y + n.h + 1;
	};
	expect(drawing.edges.length).toBeGreaterThan(0);
	for (const e of drawing.edges) {
		expect(inside(e.points[0], e.from)).toBe(true);
		expect(inside(e.points[e.points.length - 1], e.to)).toBe(true);
	}
});

it('relationship context uses scope before a visual taxon filter', () => {
	const m = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8')) as Manifest;
	const scoped = graphInput(m, { allNodes: true, external: 'all' });
	const relation = relationships(scoped.edges, 'sy-0003', 'closure');
	const visible = graphInput(m, { allNodes: true, external: 'all', taxon: 'Theorem' });
	expect(relation.direct.has('sy-0001')).toBe(true);
	expect(visible.nodes.some((n) => n.id === 'sy-0001')).toBe(false);
	const document = graphInput(m, { allNodes: true, external: 'all', master: 'drafting/talk.tex' });
	expect(relationships(document.edges, 'sy-0003', 'closure').reached.size).toBe(0);
});
