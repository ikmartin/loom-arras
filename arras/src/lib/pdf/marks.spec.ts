import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import type { Annotation } from '$lib/manifest/types';
import { RGB } from '$lib/review/annotationTypes';
import { COLOR_NAMES, copyColor, kindOf, markAt, markOf, mergeLines, movable, nearestColor, paintOf, refit, simplify, textOf, type MarkColor, type PageMark } from './marks';

const mark = (over: Partial<PageMark>): PageMark => ({ id: 'n', page: 1, kind: 'highlight', rects: [[0, 0, 10, 10]], body: '', ...over });

describe("a mark's colour", () => {
	it('is the nearest of the nine by hue: one with little hue is grey, a dark or dull orange brown', () => {
		expect([[255, 255, 0], [60, 200, 80], [30, 120, 255], [255, 105, 180], [140, 80, 220], [255, 0, 0], [255, 140, 0]].map(nearestColor)).toEqual(['yellow', 'green', 'blue', 'pink', 'purple', 'red', 'orange']);
		expect([[0, 0, 0], [255, 255, 255], [128, 128, 130]].map(nearestColor)).toEqual(['grey', 'grey', 'grey']);
		expect([[120, 70, 30], [210, 175, 135]].map(nearestColor)).toEqual(['brown', 'brown']);
	});

	it('is itself when its own paint comes back from a PDF', () => {
		for (const name of COLOR_NAMES) {
			expect(nearestColor(RGB[name].band)).toBe(name);
			expect(nearestColor(RGB[name].line)).toBe(name);
		}
	});

	it('goes into a copy as the PDF had it until its reader changes it', () => {
		expect(copyColor('highlight', 'yellow', [250, 240, 30])).toEqual([250, 240, 30]);
		expect(copyColor('highlight', 'green', [250, 240, 30])).toEqual([...RGB.green.band]);
		expect(copyColor('underline', 'green')).toEqual([...RGB.green.line]);
		expect(copyColor('ink', '', [10, 10, 10])).toEqual([10, 10, 10]);
		expect(copyColor('ink')).toBeUndefined();
	});

	it("paints from the theme's tokens, and nothing for a colour this viewer does not know", () => {
		expect(paintOf('teal' as MarkColor)).toBe('');
		expect(paintOf('')).toBe('');
		expect(paintOf('green')).toContain('--line: var(--ann-green)');
		expect(paintOf('green')).toContain('--band: var(--ann-green-band)');
	});

	it('is one the record takes', () => {
		const python = readFileSync(fileURLToPath(new URL('../../../../loom/src/loom/records/marks.py', import.meta.url)), 'utf8');
		const block = /^RGB = \{([\s\S]*?)^\}/m.exec(python)?.[1] ?? '';
		expect([...block.matchAll(/"(\w+)":/g)].map((x) => x[1])).toEqual(COLOR_NAMES);
	});
});

describe('mergeLines', () => {
	it('makes one rectangle per line of what a text layer gives', () => {
		const got = mergeLines([
			[10, 100, 60, 112],
			[60, 101, 120, 112],
			[119, 100, 200, 113],
			[10, 114, 90, 126]
		]);
		expect(got).toEqual([
			[10, 100, 200, 113],
			[10, 114, 90, 126]
		]);
	});

	it('keeps two columns apart', () => {
		expect(mergeLines([[10, 100, 100, 112], [320, 100, 400, 112]])).toHaveLength(2);
	});
});

describe('simplify', () => {
	it('takes out the points on a straight run and keeps the corner', () => {
		const run = [0, 0, 10, 0, 20, 0, 30, 0, 30, 10, 30, 20];
		expect(simplify(run)).toEqual([0, 0, 30, 0, 30, 20]);
	});

	it('leaves a two-point stroke alone', () => {
		expect(simplify([1.26, 2.34, 3, 4])).toEqual([1.3, 2.3, 3, 4]);
	});
});

describe('refit', () => {
	it('moves a stroked mark with its strokes and bound together', () => {
		const m = mark({ kind: 'ink', rects: [[10, 10, 30, 20]], strokes: [[10, 10, 30, 20]] });
		expect(refit(m, [20, 30, 40, 40])).toEqual({ rects: [[20, 30, 40, 40]], strokes: [[20, 30, 40, 40]] });
	});

	it('scales a rectangle', () => {
		expect(refit(mark({ kind: 'box' }), [0, 0, 20, 5]).rects).toEqual([[0, 0, 20, 5]]);
	});
});

describe('markAt', () => {
	it('takes the smallest mark under the point', () => {
		const big = mark({ id: 'big', kind: 'box', rects: [[0, 0, 100, 100]] });
		const small = mark({ id: 'small', rects: [[10, 10, 20, 20]] });
		expect(markAt([big, small], 15, 15)?.id).toBe('small');
		expect(markAt([big, small], 50, 50)?.id).toBe('big');
		expect(markAt([big, small], 150, 50)).toBeNull();
	});

	it('finds a stroke near its line and not across its bound', () => {
		const ink = mark({ kind: 'ink', rects: [[0, 0, 100, 100]], strokes: [[0, 0, 100, 100]] });
		expect(markAt([ink], 50, 52)?.id).toBe('n');
		expect(markAt([ink], 90, 10)).toBeNull();
	});
});

describe('markOf', () => {
	const ann = (over: Partial<Annotation> = {}, page: number | null = 2): Annotation =>
		({ id: 'a', created: 'w', author: { kind: 'person', id: 'A' }, target: { key: 'a.pdf', hash: '', file: 'a.pdf', page }, body_html: '<p>said &amp; done</p>', type: null, look: { color: 'blue', style: 'highlight', weight: 2, opacity: 60 }, status: 'open', in_reply_to: null, anchored: true, detached: false, rects: [[1, 2, 3, 4]], ...over }) as Annotation;

	it("draws a drawing as its tool and one on words as its look's style, in its look's colour, with its words as text", () => {
		expect(markOf(ann({ mark: 'oval' }))).toMatchObject({ kind: 'oval', color: 'blue', body: 'said & done', page: 2 });
		expect(markOf(ann({ quote: 'words' }))).toMatchObject({ kind: 'highlight', quote: 'words' });
		expect(markOf(ann({ look: { color: 'red', style: 'strike', weight: 1, opacity: 100 } }))).toMatchObject({ kind: 'strike', color: 'red' });
	});

	it('draws nothing it does not know the place of', () => {
		for (const over of [{ detached: true }, { rects: null }, { in_reply_to: 'a-x' }]) expect(markOf(ann(over))).toBeNull();
		expect(markOf(ann({}, null))).toBeNull();
	});

	it('reads the words of a body as published', () => {
		expect(textOf('<p>one &lt; two</p>\n<p>three</p>')).toBe('one < two\nthree');
	});
});

it('a shape moves and words do not', () => {
	expect(movable(mark({ kind: 'box' }))).toBe(true);
	expect(movable(mark({ kind: 'highlight' }))).toBe(false);
	expect(movable(mark({ kind: 'box', plain: true }))).toBe(false); // a place still being written
	expect(kindOf('rect')).toBe('box');
	expect(kindOf('select')).toBeNull();
});
