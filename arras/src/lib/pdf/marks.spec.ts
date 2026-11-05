import { describe, expect, it } from 'vitest';
import type { Note } from '$lib/manifest/types';
import { kindOf, markAt, markOf, mergeLines, movable, refit, simplify, type PageMark } from './marks';

const mark = (over: Partial<PageMark>): PageMark => ({ id: 'n', page: 1, kind: 'highlight', rects: [[0, 0, 10, 10]], body: '', ...over });

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
	const note = (over: Partial<Note>): Note => ({ id: 'n', when: 'w', author: { kind: 'person', id: 'A' }, session: '', target: { file: 'a.pdf' }, body: '', faded: false, detached: false, page: 2, rects: [[1, 2, 3, 4]], ...over });

	it('draws a mark, and a plain note with a place faintly', () => {
		expect(markOf(note({ mark: 'oval' }))).toMatchObject({ kind: 'oval' });
		expect(markOf(note({ quote: 'words' }))).toMatchObject({ kind: 'underline', plain: true });
		expect(markOf(note({}))).toMatchObject({ kind: 'box', plain: true });
	});

	it('draws nothing it does not know the place of', () => {
		for (const over of [{ detached: true }, { faded: true }, { erased: 'w' }, { rects: undefined }, { page: undefined }]) expect(markOf(note(over))).toBeNull();
	});
});

it('a shape moves and words do not', () => {
	expect(movable(mark({ kind: 'box' }))).toBe(true);
	expect(movable(mark({ kind: 'highlight' }))).toBe(false);
	expect(movable(mark({ kind: 'box', plain: true }))).toBe(false);
	expect(kindOf('rect')).toBe('box');
	expect(kindOf('select')).toBeNull();
});
