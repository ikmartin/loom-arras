// A copy written and read back through the real pdf.js, under node, on a PDF of loom's test quilts.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import * as lib from 'pdfjs-dist/legacy/build/pdf.mjs';
import { annotatedCopy, editedPages, notTheSamePaper, outlineOf, readAnnotations, renameSubtypes, wrapped, type Outgoing } from './portable';

const pdfjs = lib as unknown as typeof import('pdfjs-dist');
const ARDEN = fileURLToPath(new URL('../../../../loom/tests/quilts/sources/showcase-works/arden-cycle-spaces.pdf', import.meta.url));
const FONTS = fileURLToPath(new URL('../../../node_modules/pdfjs-dist/standard_fonts/', import.meta.url));
const original = () => new Uint8Array(readFileSync(ARDEN));
const source = (data: Uint8Array = original()) => ({ data, verbosity: 0, standardFontDataUrl: FONTS });
const open = (data: Uint8Array) => pdfjs.getDocument(source(data.slice())).promise;

const TITLE = [[206.99, 125.41, 293.37, 140.99]];
const marks: Outgoing[] = [
	{ page: 1, kind: 'highlight', rects: TITLE, body: 'on the title', by: 'A Reader' },
	{ page: 1, kind: 'underline', rects: [[100, 300, 300, 312]], body: 'a line under', by: 'A Reader' },
	{ page: 1, kind: 'strike', rects: [[100, 320, 300, 332]], body: '', by: 'A Reader' },
	{ page: 1, kind: 'pin', rects: [[50, 50, 66, 66]], body: 'a sticky note', by: 'A Reader' },
	{ page: 2, kind: 'text', rects: [[60, 60, 260, 90]], body: 'words on the page', by: 'A Reader' },
	{ page: 2, kind: 'ink', rects: [[60, 120, 160, 150]], strokes: [[60, 120, 110, 150, 160, 120]], body: 'a scrawl', by: 'A Reader' },
	{ page: 2, kind: 'box', rects: [[60, 200, 160, 250]], body: '', by: 'A Reader' },
	{ page: 2, kind: 'oval', rects: [[200, 200, 300, 250]], body: '', by: 'A Reader' },
	{ page: 2, kind: 'arrow', rects: [[320, 200, 420, 250]], strokes: [[320, 200, 420, 250]], body: '', by: 'A Reader' }
];

describe('a copy with annotations', () => {
	it('appends to the original bytes and holds a real annotation of each subtype, with its comment', async () => {
		const bytes = original();
		const { bytes: out, written, left } = await annotatedCopy(pdfjs, source(), marks);
		expect([written, left]).toEqual([marks.length, 0]);
		expect(Buffer.from(out.subarray(0, bytes.length)).equals(Buffer.from(bytes))).toBe(true);
		const doc = await open(out);
		const one = (await (await doc.getPage(1)).getAnnotations()).filter((a) => a.subtype !== 'Popup');
		const two = (await (await doc.getPage(2)).getAnnotations()).filter((a) => a.subtype !== 'Popup');
		expect(one.map((a) => a.subtype)).toEqual(['Highlight', 'Underline', 'StrikeOut', 'Text']);
		expect(two.map((a) => a.subtype)).toEqual(['FreeText', 'Ink', 'Ink', 'Ink', 'Ink']);
		expect(one[0].contentsObj.str).toBe('on the title');
		expect(one[3].contentsObj.str).toBe('a sticky note');
		expect(two[0].contentsObj.str).toBe('words on the page');
		expect(one[0].titleObj.str).toBe('A Reader');
		// in user space, whose origin is at the bottom left
		expect(one[0].rect[1]).toBeCloseTo(792 - 140.99, 1);
	});

	it('comes back as the same marks', async () => {
		const { bytes } = await annotatedCopy(pdfjs, source(), marks);
		const { items, skipped } = await readAnnotations(await open(bytes));
		expect(skipped).toBe(0);
		expect(items.map((i) => i.mark)).toEqual(['highlight', 'underline', 'strike', 'pin', 'text', 'ink', 'ink', 'ink', 'ink']);
		expect(items[0].rects?.[0].map(Math.round)).toEqual(TITLE[0].map(Math.round));
		expect(items[0]).toMatchObject({ page: 1, body: 'on the title', origin: { by: 'A Reader', subtype: 'Highlight' } });
		expect(items[5].strokes?.[0].map(Math.round)).toEqual([60, 120, 110, 150, 160, 120]);
		expect(items[0].origin.ref).toBeUndefined();
	});

	it('says what it could not place, and leaves out what a note now stands for', async () => {
		const { bytes } = await annotatedCopy(pdfjs, source(), [marks[0], { ...marks[1], page: 99 }]);
		const doc = await open(bytes);
		const { items } = await readAnnotations(doc, true);
		expect(items).toHaveLength(1);
		const ref = items[0].origin.ref!;
		expect(ref).toMatch(/R$/);
		const again = await annotatedCopy(pdfjs, source(bytes.slice()), [marks[3]], [{ page: 1, ref }]);
		expect(again.left).toBe(0);
		const left = await readAnnotations(await open(again.bytes));
		expect(left.items.map((i) => i.mark)).toEqual(['pin']);
	});
});

it('renames a Highlight in place, at the same length', () => {
	const text = '9 0 obj\n<< /Type /Annot /Subtype /Highlight /Rect [10 20 30 40] >>\nendobj\n';
	const bytes = new TextEncoder().encode(text);
	renameSubtypes(bytes, [{ rect: [10, 20, 30, 40], name: 'Text' }]);
	const out = new TextDecoder().decode(bytes);
	expect(out).toContain('/Subtype /Text      /Rect');
	expect(out.length).toBe(text.length);
});

it('an arrow is drawn with its head, and a box closes', () => {
	expect(outlineOf({ kind: 'arrow', rects: [[0, 0, 10, 10]], strokes: [[0, 0, 10, 10]] })).toHaveLength(3);
	expect(outlineOf({ kind: 'box', rects: [[0, 0, 10, 10]] })[0]).toEqual([0, 0, 10, 0, 10, 10, 0, 10, 0, 0]);
});

it('words are broken to the width they are set in', () => {
	expect(wrapped('one two three four', 44).split('\n').length).toBeGreaterThan(1);
	expect(wrapped('short', 200)).toBe('short');
});

describe('whether a PDF is the same paper', () => {
	it('agrees with a copy of itself, and refuses a different page count', async () => {
		const doc = await open(original());
		expect(await notTheSamePaper(doc, await open(original()))).toBe('');
		const one = await editedPages(pdfjs, source(), [{ from: 0, index: 0, rotate: 0 }]);
		expect(await notTheSamePaper(doc, await open(one))).toMatch(/has 1 page and this one has 2/);
	});
});

describe('page edits', () => {
	const first = async (doc: Awaited<ReturnType<typeof open>>, n: number) => {
		const t = await (await doc.getPage(n)).getTextContent();
		return t.items.map((i) => ('str' in i ? i.str : '')).join(' ');
	};

	it('reorders, deletes, and inserts from another PDF', async () => {
		const swapped = await open(await editedPages(pdfjs, source(), [{ from: 0, index: 1, rotate: 0 }, { from: 0, index: 0, rotate: 0 }]));
		expect(swapped.numPages).toBe(2);
		expect(await first(swapped, 2)).toContain('Cycle spaces');
		const merged = await open(await editedPages(pdfjs, source(), [{ from: 0, index: 0, rotate: 0 }, { from: 1, index: 0, rotate: 0 }, { from: 0, index: 1, rotate: 0 }], [original()]));
		expect(merged.numPages).toBe(3);
		expect(await first(merged, 2)).toContain('Cycle spaces');
	});

	it('turns a page by each angle, and leaves its words readable', async () => {
		for (const turn of [90, 180, 270]) {
			const doc = await open(await editedPages(pdfjs, source(), [{ from: 0, index: 0, rotate: turn }, { from: 0, index: 1, rotate: 0 }]));
			expect([(await doc.getPage(1)).rotate, (await doc.getPage(2)).rotate]).toEqual([turn, 0]);
			expect(await first(doc, 1)).toContain('Cycle spaces');
		}
	});

	it('carries marks into the new file', async () => {
		const out = await editedPages(pdfjs, source(), [{ from: 0, index: 1, rotate: 0 }, { from: 0, index: 0, rotate: 0 }], [], [marks[1]]);
		const { items } = await readAnnotations(await open(out));
		expect(items).toHaveLength(1);
		expect(items[0]).toMatchObject({ page: 2, mark: 'underline', body: 'a line under' });
	});
});
