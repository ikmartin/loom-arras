// Annotating a PDF under `loom serve` (plan 0.28, plan 0.30.2): a mark is an annotation on the page, made from the toolbar a document has (Annotate, Comment, the format menu, Undo) and the PDF's own drawing tools, drawn at once and in its look after a reload, on a cited work's page and on a project's PDF; its popup; a saved copy read back; annotations taken in; page edits into a new file, from PDF ▾.
import { expect, test, type Served } from '../served';
import type { Page } from '@playwright/test';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import * as lib from 'pdfjs-dist/legacy/build/pdf.mjs';
import { annotatedCopy, readAnnotations } from '../../src/lib/pdf/portable';
import { RGB } from '../../src/lib/review/annotationTypes';

const pdfjs = lib as unknown as typeof import('pdfjs-dist');
const ARDEN = fileURLToPath(new URL('../../../loom/tests/quilts/sources/showcase-works/arden-cycle-spaces.pdf', import.meta.url));
const BELLAMY = fileURLToPath(new URL('../../../loom/tests/quilts/sources/showcase-works/bellamy-median-orders.pdf', import.meta.url));
const FILE = 'notes/paper.pdf';
const open = (data: Uint8Array) => pdfjs.getDocument({ data: data.slice(), verbosity: 0 }).promise;

/** A project with a PDF of its own among its files. */
const withPaper = {
	prepareQuilt: async ({}, use: (p: (q: { root: string }) => void) => Promise<void>) => {
		await use(({ root }) => {
			mkdirSync(join(root, 'notes'), { recursive: true });
			writeFileSync(join(root, FILE), readFileSync(ARDEN));
		});
	}
};

interface Ann {
	id: string;
	mark: string | null;
	style: string;
	color: string;
	body: string;
	rects: number[][] | null;
	strokes: number[][] | null;
	quote: string | null;
	page: number | null;
	on: string;
	origin: { by?: string } | null;
}

/** The published annotations, by id, with what a mark is read by. */
function annotations(served: Served): Record<string, Ann> {
	type Raw = { id: string; mark?: string | null; look?: { style: string; color: string }; body_html?: string; rects?: number[][] | null; strokes?: number[][] | null; quote?: string | null; target: { key: string; page?: number | null; file?: string | null; work?: string | null }; origin?: { by?: string } | null };
	const all = JSON.parse(readFileSync(join(served.root, '.loom/build/manifest.json'), 'utf8')).annotations as Record<string, Raw>;
	return Object.fromEntries(
		Object.values(all ?? {}).map((a) => [
			a.id,
			{ id: a.id, mark: a.mark ?? null, style: a.look?.style ?? '', color: a.look?.color ?? '', body: (a.body_html ?? '').replace(/<[^>]*>/g, '').trim(), rects: a.rects ?? null, strokes: a.strokes ?? null, quote: a.quote ?? null, page: a.target.page ?? null, on: a.target.file ?? a.target.work ?? a.target.key, origin: a.origin ?? null }
		])
	);
}

/** The annotations on the pages of the PDF `on`, a project file's path or a citekey. */
const marksOf = (served: Served, on = FILE) => Object.values(annotations(served)).filter((a) => a.on === on && a.page !== null);

async function openPaper(page: Page, url: string, n = 1): Promise<void> {
	await page.goto(url);
	await expect.poll(() => page.locator(`[data-testid="pdf-page-${n}"] .text span`).count()).toBeGreaterThan(10);
}

/** Select the words of a span, as a reader does, and let go. */
async function selectWords(page: Page, n: number, phrase: string): Promise<void> {
	const span = page.locator(`[data-testid="pdf-page-${n}"] .text span:has-text("${phrase}")`).first();
	await span.scrollIntoViewIfNeeded();
	await span.evaluate((node) => {
		const range = document.createRange();
		range.selectNodeContents(node);
		const sel = window.getSelection();
		sel?.removeAllRanges();
		sel?.addRange(range);
		node.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
	});
}

/** Mark the words of a span with Annotate, in the look in hand, turning it on where it is off. */
async function annotate(page: Page, n: number, phrase: string): Promise<void> {
	const tool = page.getByTestId('tool-annotate');
	if ((await tool.getAttribute('aria-pressed')) !== 'true') await tool.click();
	await selectWords(page, n, phrase);
}

/** Choose a line of PDF ▾. */
async function pdfMenu(page: Page, testid: string): Promise<void> {
	await page.getByTestId('pdf-menu').click();
	await page.getByTestId(testid).click();
}

/** The look in hand, set before the page loads, as the format menu leaves it. */
async function holding(page: Page, h: { type: string | null; over: Record<string, unknown>; plain?: Record<string, unknown> }): Promise<void> {
	await page.addInitScript((v) => localStorage.setItem('arras.annotate.hand', JSON.stringify(v)), h);
}

const marks = (page: Page, kind?: string) => page.locator(kind ? `[data-testid^="page-mark-"][data-kind="${kind}"]` : '[data-testid^="page-mark-"]');
const published = (served: Served, count: number, on = FILE) => expect.poll(() => marksOf(served, on).length).toBe(count);

/** Press and drag across a page, from and to fractions of its size. */
async function drag(page: Page, n: number, from: [number, number], to: [number, number]): Promise<void> {
	const box = (await page.getByTestId(`pdf-page-${n}`).boundingBox())!;
	await page.mouse.move(box.x + box.width * from[0], box.y + box.height * from[1]);
	await page.mouse.down();
	await page.mouse.move(box.x + box.width * ((from[0] + to[0]) / 2), box.y + box.height * ((from[1] + to[1]) / 2), { steps: 4 });
	await page.mouse.move(box.x + box.width * to[0], box.y + box.height * to[1], { steps: 4 });
	await page.mouse.up();
}

async function pressOn(page: Page, n: number, at: [number, number]): Promise<void> {
	const box = (await page.getByTestId(`pdf-page-${n}`).boundingBox())!;
	await page.mouse.click(box.x + box.width * at[0], box.y + box.height * at[1]);
}

/** Click the middle of a mark that takes no pointer: the page below is asked what the click landed on. */
async function clickMark(page: Page, testid: string): Promise<void> {
	const box = (await page.getByTestId(testid).boundingBox())!;
	await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
}

// an effect that feeds itself, or a write the page did not catch, fails the test that caused it
test.beforeEach(({ page }, info) => {
	page.on('pageerror', (e) => info.annotations.push({ type: 'pageerror', description: e.message }));
});
test.afterEach(({}, info) => {
	expect(info.annotations.filter((a) => a.type === 'pageerror')).toEqual([]);
});

test("a highlight on a cited work's page needs no session, is drawn at once in the look in hand, and after a reload is an annotation on its words drawn in its look", async ({ page, served }) => {
	const before = marksOf(served, 'Bellamy19').map((a) => a.id);
	await openPaper(page, '/library/Bellamy19?page=2', 2);
	await annotate(page, 2, 'order');
	await expect.poll(() => marksOf(served, 'Bellamy19').filter((a) => !before.includes(a.id)).length).toBe(1);
	const mark = marksOf(served, 'Bellamy19').find((a) => !before.includes(a.id))!;
	await expect(page.locator(`[data-testid="page-mark-${mark.id}"][data-kind="highlight"]`)).toHaveCount(1);
	// on words, so its look's style draws it and no tool did: the hand's yellow highlight, there being no type in it
	expect(mark).toMatchObject({ mark: null, style: 'highlight', color: 'yellow', page: 2 });
	expect(mark.quote).toBeTruthy();
	expect(served.log().find((e) => e.event === 'created' && e.id === mark.id)).not.toHaveProperty('session');
	await openPaper(page, '/library/Bellamy19?page=2', 2);
	const drawn = page.locator(`[data-testid="page-mark-${mark.id}"][data-kind="highlight"]`);
	await expect(drawn).toHaveCount(1);
	expect(await page.getByTestId(`mark-band-${mark.id}`).evaluate((g) => getComputedStyle(g).getPropertyValue('--band-strength').trim())).toBe('0.6');
});

test.describe('on a project PDF', () => {
	test.use(withPaper);

	test('a comment is written in a mark\'s popup, the mark is deleted from it and put back by Undo, and the file is not touched', async ({ page, served }) => {
		await openPaper(page, `/file/${FILE}`);
		await annotate(page, 1, 'Cycle');
		await published(served, 1);
		const id = marksOf(served)[0].id;
		await page.keyboard.press('Escape');
		await clickMark(page, `page-mark-${id}`);
		const p = page.getByTestId('ann-popup');
		await expect(p).toHaveAttribute('data-annotation-id', id);
		await p.getByTestId('popup-comment-field').fill('the title says it');
		await p.getByTestId('popup-save').click();
		await expect.poll(() => annotations(served)[id]?.body).toBe('the title says it');
		await page.reload();
		await expect.poll(() => page.locator('[data-testid="pdf-page-1"] .text span').count()).toBeGreaterThan(10);
		await clickMark(page, `page-mark-${id}`);
		await expect(p.getByTestId('popup-comment')).toContainText('the title says it');
		await p.getByTestId('popup-delete').click();
		await expect(page.getByTestId(`page-mark-${id}`)).toHaveCount(0);
		await expect.poll(() => id in annotations(served)).toBe(false);
		await page.getByTestId('annotate-undo').click();
		await expect(page.getByTestId(`page-mark-${id}`)).toHaveCount(1);
		await expect.poll(() => id in annotations(served)).toBe(true);
		expect(readFileSync(join(served.root, FILE)).equals(readFileSync(ARDEN))).toBe(true);
	});

	test('Annotate marks each selection in the style in hand until it is put down, and leaves a plain selection to Quote afterwards', async ({ page, served }) => {
		await openPaper(page, `/file/${FILE}`);
		await annotate(page, 1, 'Cycle');
		await expect(marks(page, 'highlight')).toHaveCount(1);
		await page.getByTestId('format-toggle').click();
		await page.getByTestId('format-menu').getByTestId('style-underline').click();
		await page.keyboard.press('Escape');
		await selectWords(page, 1, 'Abstract');
		await expect(marks(page, 'underline')).toHaveCount(1);
		await expect(page.getByTestId('quote-offer')).toHaveCount(0);
		await published(served, 2);
		expect(marksOf(served).map((a) => a.style).sort()).toEqual(['highlight', 'underline']);
		await page.keyboard.press('Escape');
		await expect(page.getByTestId('tool-annotate')).toHaveAttribute('aria-pressed', 'false');
		await selectWords(page, 1, 'Introduction');
		await expect(page.getByTestId('quote-offer')).toBeVisible();
	});

	test('Comment writes a pin once it says something, the drawing tools each leave a mark in the look in hand, and a shape moves, resizes and comes back with Undo', async ({ page, served }) => {
		test.slow();
		await holding(page, { type: null, over: {}, plain: { color: 'purple', style: 'highlight', weight: 3, opacity: 80 } });
		await openPaper(page, `/file/${FILE}`);

		await page.getByTestId('tool-comment').click();
		await pressOn(page, 1, [0.1, 0.1]);
		const draft = page.getByTestId('ann-popup');
		await expect(draft.getByTestId('popup-save')).toBeDisabled();
		await draft.getByTestId('popup-comment-field').fill('see the second section');
		await draft.getByTestId('popup-save').click();
		await expect(marks(page, 'pin')).toHaveCount(1);
		await expect(page.getByTestId('tool-comment')).toHaveAttribute('aria-pressed', 'false');

		await page.getByTestId('tool-text').click();
		await pressOn(page, 1, [0.25, 0.08]);
		await page.getByTestId('popup-comment-field').fill('words on the page');
		await page.getByTestId('popup-save').click();
		await expect(marks(page, 'text')).toContainText('words on the page');

		await page.getByTestId('tool-rect').click();
		await drag(page, 1, [0.2, 0.3], [0.4, 0.4]);
		await expect(marks(page, 'box')).toHaveCount(1);
		await page.getByTestId('tool-oval').click();
		await drag(page, 1, [0.5, 0.3], [0.7, 0.4]);
		await expect(marks(page, 'oval')).toHaveCount(1);
		await page.getByTestId('tool-arrow').click();
		await drag(page, 1, [0.2, 0.5], [0.4, 0.6]);
		await expect(marks(page, 'arrow')).toHaveCount(1);

		// lines of ink drawn close together are one mark; a busy machine can leave more than `INK_PAUSE` between two drags, so that timer is held back here and putting the tool down ends them
		const inkPause = await page.evaluateHandle(() => {
			const setTimeout = window.setTimeout;
			window.setTimeout = ((run: TimerHandler, ms = 0, ...rest: unknown[]) => (ms === 900 ? 0 : setTimeout(run, ms, ...rest))) as typeof window.setTimeout;
			return () => (window.setTimeout = setTimeout);
		});
		await page.getByTestId('tool-ink').click();
		await drag(page, 1, [0.5, 0.5], [0.6, 0.55]);
		await drag(page, 1, [0.6, 0.55], [0.7, 0.5]);
		await page.getByTestId('tool-ink').click();
		await inkPause.evaluate((restore) => void restore());
		await expect(marks(page, 'ink')).toHaveCount(1);
		await published(served, 6);
		const ink = marksOf(served).find((a) => a.mark === 'ink')!;
		expect(ink.strokes).toHaveLength(2);
		// every one in the look in hand
		expect(new Set(marksOf(served).map((a) => a.color))).toEqual(new Set(['purple']));
		expect(await page.locator('.k-box .shape').first().evaluate((s) => getComputedStyle(s).strokeWidth)).toBe('3px');

		// a press inside a shape opens its popup and takes hold of it; dragging moves it and the record follows
		const box = marksOf(served).find((a) => a.mark === 'box')!;
		const [x0, y0] = box.rects![0];
		await clickMark(page, `page-mark-${box.id}`);
		await expect(page.getByTestId('ann-popup')).toHaveAttribute('data-annotation-id', box.id);
		await expect(page.getByTestId('mark-grab')).toBeVisible();
		const grab = (await page.getByTestId('mark-grab').boundingBox())!;
		await page.mouse.move(grab.x + grab.width / 2, grab.y + grab.height / 2);
		await page.mouse.down();
		await page.mouse.move(grab.x + grab.width / 2 + 30, grab.y + grab.height / 2 + 20, { steps: 4 });
		await page.mouse.up();
		await expect.poll(() => annotations(served)[box.id].rects![0][0]).toBeGreaterThan(x0 + 5);
		expect(annotations(served)[box.id].rects![0][1]).toBeGreaterThan(y0 + 5);
		const moved = annotations(served)[box.id].rects![0];
		const handle = (await page.getByTestId('mark-handle-se').boundingBox())!;
		await page.mouse.move(handle.x + 4, handle.y + 4);
		await page.mouse.down();
		await page.mouse.move(handle.x + 44, handle.y + 34, { steps: 4 });
		await page.mouse.up();
		await expect.poll(() => annotations(served)[box.id].rects![0][2]).toBeGreaterThan(moved[2] + 5);
		// and Undo takes the resize back, then Delete takes it off the page
		await page.getByTestId('annotate-undo').click();
		await expect.poll(() => annotations(served)[box.id].rects![0][2]).toBeCloseTo(moved[2], 0);
		await page.locator('body').evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
		await page.keyboard.press('Delete');
		await expect(page.getByTestId(`page-mark-${box.id}`)).toHaveCount(0);
	});

	test('a saved copy holds the marks as a PDF reader finds them, in their looks, and its original bytes', async ({ page, served }) => {
		await holding(page, { type: null, over: {}, plain: { color: 'green', style: 'highlight', weight: 2, opacity: 55 } });
		await openPaper(page, `/file/${FILE}`);
		await annotate(page, 1, 'Cycle');
		await published(served, 1);
		const id = marksOf(served)[0].id;
		await page.keyboard.press('Escape');
		await clickMark(page, `page-mark-${id}`);
		await page.getByTestId('popup-comment-field').fill('in the copy');
		await page.getByTestId('popup-save').click();
		await expect.poll(() => annotations(served)[id]?.body).toBe('in the copy');
		await page.keyboard.press('Escape');
		const [saved] = await Promise.all([page.waitForEvent('download'), pdfMenu(page, 'mark-save-copy')]);
		expect(saved.suggestedFilename()).toBe('paper-annotated.pdf');
		const bytes = new Uint8Array(readFileSync(await saved.path()));
		const original = readFileSync(ARDEN);
		expect(Buffer.from(bytes.subarray(0, original.length)).equals(original)).toBe(true);
		const { items } = await readAnnotations(await open(bytes));
		expect(items).toHaveLength(1);
		expect(items[0]).toMatchObject({ style: 'highlight', body: 'in the copy', page: 1, color: 'green', opacity: 55, weight: 2 });
		await expect(page.getByTestId('toast')).toContainText('It holds 1 annotation');
	});

	test('a colour is set in the popup, with Undo, and the look in hand is what the next mark is drawn in', async ({ page, served }) => {
		test.slow();
		await holding(page, { type: null, over: {}, plain: { color: 'green', style: 'highlight', weight: 2, opacity: 100 } });
		await openPaper(page, `/file/${FILE}`);
		await annotate(page, 1, 'Cycle');
		await published(served, 1);
		const id = marksOf(served)[0].id;
		expect(annotations(served)[id].color).toBe('green');
		const band = page.getByTestId(`mark-band-${id}`).locator('rect').first();
		const fill = () => band.evaluate((r) => getComputedStyle(r).fill);
		await expect.poll(fill).toBe('rgb(160, 232, 140)');

		await page.keyboard.press('Escape');
		await clickMark(page, `page-mark-${id}`);
		await page.getByTestId('popup-type').click();
		await page.getByTestId('popup-format').getByTestId('swatch-pink').click();
		await expect.poll(() => annotations(served)[id]?.color).toBe('pink');
		await expect.poll(fill).toBe('rgb(255, 174, 220)');
		await page.getByTestId('annotate-undo').click();
		await expect.poll(() => annotations(served)[id]?.color).toBe('green');
		await page.keyboard.press('Escape');

		// the hand keeps its own colour; blue chosen there draws the next box
		await page.getByTestId('format-toggle').click();
		await page.getByTestId('format-menu').getByTestId('swatch-blue').click();
		await page.keyboard.press('Escape');
		await page.getByTestId('tool-rect').click();
		await drag(page, 1, [0.2, 0.6], [0.5, 0.75]);
		await published(served, 2);
		const box = marksOf(served).find((a) => a.mark === 'box');
		expect(box?.color).toBe('blue');
		await expect.poll(() => page.locator('.k-box .shape').first().evaluate((s) => getComputedStyle(s).stroke)).toBe('rgb(26, 111, 196)');
		await page.getByTestId('tool-rect').click();

		const [saved] = await Promise.all([page.waitForEvent('download'), pdfMenu(page, 'mark-save-copy')]);
		const { items } = await readAnnotations(await open(new Uint8Array(readFileSync(await saved.path()))));
		expect(items.find((i) => i.style === 'highlight')?.color).toBe('green');
		expect(items.find((i) => i.mark === 'ink')?.color).toBe('blue');
	});

	test('annotations are taken in from another copy once, in their colours, and never from a different paper', async ({ page, served }) => {
		const { bytes } = await annotatedCopy(pdfjs, { data: new Uint8Array(readFileSync(ARDEN)), verbosity: 0 }, [
			{ page: 1, kind: 'highlight', rects: [[206.99, 125.41, 293.37, 140.99]], body: 'from elsewhere', by: 'A Reader', color: RGB.red.band },
			{ page: 1, kind: 'pin', rects: [[50, 50, 66, 66]], body: 'a sticky note', by: 'A Reader' }
		]);
		await openPaper(page, `/file/${FILE}`);
		const file = { name: 'marked.pdf', mimeType: 'application/pdf', buffer: Buffer.from(bytes) };
		await page.getByTestId('mark-take-file').setInputFiles(file);
		await expect(page.getByTestId('toast')).toContainText('Took in 2');
		await expect(marks(page)).toHaveCount(2);
		const taken = marksOf(served).find((a) => a.style === 'highlight' && !a.mark)!;
		expect(taken).toMatchObject({ body: 'from elsewhere', color: 'red', origin: { by: 'A Reader' } });
		expect(taken.quote).toContain('Cycle spaces');
		await page.getByTestId('mark-take-file').setInputFiles(file);
		await expect(page.getByTestId('toast')).toContainText('2 were here already');
		await page.getByTestId('mark-take-file').setInputFiles({ name: 'other.pdf', mimeType: 'application/pdf', buffer: readFileSync(BELLAMY) });
		await expect(page.getByTestId('toast')).toContainText('no place here');
		await published(served, 2);
	});

	test('edited pages are saved as a new file, opened, and the PDF being read stays as it was', async ({ page, served }) => {
		await openPaper(page, `/file/${FILE}`);
		await pdfMenu(page, 'mark-pages');
		const editor = page.getByTestId('pages-editor');
		await expect(editor.getByTestId('pages-count')).toHaveText('2 pages');
		// the second page first, and turned
		await editor.getByTestId('pages-page-2').click();
		await editor.getByTestId('pages-earlier').click();
		await expect(editor.getByTestId('pages-page-1')).toHaveAttribute('data-index', '1');
		await editor.getByTestId('pages-right').click();
		await expect(editor.getByTestId('pages-page-1')).toHaveAttribute('data-rotate', '90');
		// a page from another PDF in between
		await editor.getByTestId('pages-insert-file').setInputFiles({ name: 'other.pdf', mimeType: 'application/pdf', buffer: readFileSync(BELLAMY) });
		await expect(editor.getByTestId('pages-count')).not.toHaveText('2 pages');
		await expect(editor.getByTestId('pages-path')).toHaveValue('notes/paper-edited.pdf');
		await editor.getByTestId('pages-path').fill(FILE);
		await editor.getByTestId('pages-save').click();
		await expect(editor.getByTestId('pages-said')).toContainText('never replaces');
		await editor.getByTestId('pages-path').fill('notes/paper-edited.pdf');
		await editor.getByTestId('pages-save').click();
		await expect(page).toHaveURL(/paper-edited\.pdf/);
		const made = await open(new Uint8Array(readFileSync(join(served.root, 'notes/paper-edited.pdf'))));
		expect(made.numPages).toBeGreaterThan(2);
		expect((await made.getPage(1)).rotate).toBe(90);
		expect(readFileSync(join(served.root, FILE)).equals(readFileSync(ARDEN))).toBe(true);
	});
});

test.describe('a PDF that already holds annotations', () => {
	test.use({
		prepareQuilt: async ({}, use) => {
			const { bytes } = await annotatedCopy(pdfjs, { data: new Uint8Array(readFileSync(ARDEN)), verbosity: 0 }, [{ page: 1, kind: 'highlight', rects: [[206.99, 125.41, 293.37, 140.99]], body: 'said in Preview', by: 'A Reader' }]);
			await use(({ root }) => {
				mkdirSync(join(root, 'notes'), { recursive: true });
				writeFileSync(join(root, FILE), bytes);
			});
		}
	});

	test('its comment can be read, and once taken in an annotation stands for it', async ({ page, served }) => {
		await openPaper(page, `/file/${FILE}`);
		const held = page.locator('[data-testid^="pdf-annotation-"]');
		await expect(held).toHaveCount(1);
		const box = (await held.boundingBox())!;
		await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
		await expect(page.getByTestId('toast')).toContainText('said in Preview');
		await pdfMenu(page, 'mark-take-here');
		await expect(page.getByTestId('toast')).toContainText('Took in 1');
		await expect(marks(page, 'highlight')).toHaveCount(1);
		await expect(held).toHaveCount(0);
		expect(marksOf(served)[0]).toMatchObject({ body: 'said in Preview' });
		// a copy holds it once
		const [saved] = await Promise.all([page.waitForEvent('download'), pdfMenu(page, 'mark-save-copy')]);
		const { items } = await readAnnotations(await open(new Uint8Array(readFileSync(await saved.path()))));
		expect(items.map((i) => i.body)).toEqual(['said in Preview']);
	});
});

test.describe('where no publisher takes writes', () => {
	test.use({
		prepareQuilt: async ({}, use) => {
			await use(({ loom }) => {
				loom(['annotate', 'Bellamy19', '--page', '2', '--box', '50,50,100,60', '--mark', 'box', '--as', 'A Person']);
			});
		}
	});

	test('marks are drawn, the tools are not offered, and a copy can still be saved', async ({ page, served }) => {
		await page.route('**/_api', (route) => route.fulfill({ status: 404, body: '' }));
		await openPaper(page, '/library/Bellamy19?page=2', 2);
		const drawn = marksOf(served, 'Bellamy19').find((a) => a.mark === 'box')!;
		await expect(page.getByTestId(`page-mark-${drawn.id}`)).toHaveAttribute('data-kind', 'box');
		await expect(page.getByTestId('tool-annotate')).toHaveCount(0);
		await expect(page.getByTestId('tool-rect')).toHaveCount(0);
		// Quote writes nothing, so it is offered still
		await selectWords(page, 2, 'order');
		await expect(page.getByTestId('quote-offer')).toBeVisible();
		const [saved] = await Promise.all([page.waitForEvent('download'), pdfMenu(page, 'mark-save-copy')]);
		expect(saved.suggestedFilename()).toBe('Bellamy19-annotated.pdf');
		const { items } = await readAnnotations(await open(new Uint8Array(readFileSync(await saved.path()))));
		expect(items.map((i) => i.mark)).toContain('ink');
	});
});
