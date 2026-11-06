// Marking a PDF under `loom serve` (plan 0.28): a mark drawn at once and there after a reload, on a cited work's page and on a project's PDF; comments, erasing and undo; the drawing tools; a saved copy read back; annotations taken in; page edits into a new file.
import { expect, test, type Served } from '../served';
import type { Page } from '@playwright/test';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import * as lib from 'pdfjs-dist/legacy/build/pdf.mjs';
import { annotatedCopy, readAnnotations } from '../../src/lib/pdf/portable';

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

function notes(served: Served): Record<string, { mark?: string; body: string; rects?: number[][]; strokes?: number[][]; session: string; quote?: string; page?: number; origin?: { by?: string } }> {
	return JSON.parse(readFileSync(join(served.root, '.loom/build/manifest.json'), 'utf8')).notes ?? {};
}

const marksOf = (served: Served) => Object.values(notes(served)).filter((n) => n.mark);

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

const marks = (page: Page, kind?: string) => page.locator(kind ? `[data-testid^="page-mark-"][data-kind="${kind}"]` : '[data-testid^="page-mark-"]');
const published = (served: Served, count: number) => expect.poll(() => marksOf(served).length).toBe(count);

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

test('a highlight from the selection needs no session, is drawn at once, and is there after a reload', async ({ page, served }) => {
	await openPaper(page, '/library/Bellamy19?page=2', 2);
	await selectWords(page, 2, 'order');
	await page.getByTestId('highlight-offer').click();
	await expect(marks(page, 'highlight')).toHaveCount(1);
	await published(served, 1);
	const [mark] = marksOf(served);
	expect(mark).toMatchObject({ mark: 'highlight', session: '', page: 2 });
	expect(mark.rects!.length).toBeGreaterThan(0);
	expect(mark.quote).toBeTruthy();
	await openPaper(page, '/library/Bellamy19?page=2', 2);
	await expect(marks(page, 'highlight')).toHaveCount(1);
	expect(existsSync(join(served.root, '.loom/annotations/notes.jsonl'))).toBe(true);
});

test.describe('on a project PDF', () => {
	test.use(withPaper);

	test('a comment is written on a mark, erased, and undone, and the file is not touched', async ({ page, served }) => {
		await openPaper(page, `/file/${FILE}`);
		await selectWords(page, 1, 'Cycle');
		await page.getByTestId('highlight-offer').click();
		await published(served, 1);
		const id = Object.keys(notes(served))[0];
		await clickMark(page, `page-mark-${id}`);
		await page.getByTestId('mark-comment').fill('the title says it');
		await page.getByTestId('mark-done').click();
		await expect.poll(() => notes(served)[id]?.body).toBe('the title says it');
		await page.reload();
		await expect.poll(() => page.locator('[data-testid="pdf-page-1"] .text span').count()).toBeGreaterThan(10);
		await clickMark(page, `page-mark-${id}`);
		await expect(page.getByTestId('mark-card-body')).toContainText('the title says it');
		await page.getByTestId('mark-erase').click();
		await expect(page.getByTestId(`page-mark-${id}`)).toHaveCount(0);
		await expect.poll(() => id in notes(served)).toBe(false);
		await page.getByTestId('markup-toggle').click();
		await page.getByTestId('mark-undo').click();
		await expect(page.getByTestId(`page-mark-${id}`)).toHaveCount(1);
		await expect.poll(() => id in notes(served)).toBe(true);
		expect(readFileSync(join(served.root, FILE)).equals(readFileSync(ARDEN))).toBe(true);
	});

	test('a word tool marks each selection until it is put down, and leaves a plain selection to the chip afterwards', async ({ page, served }) => {
		await openPaper(page, `/file/${FILE}`);
		await page.getByTestId('markup-toggle').click();
		await page.getByTestId('tool-underline').click();
		await selectWords(page, 1, 'Cycle');
		await expect(marks(page, 'underline')).toHaveCount(1);
		await page.getByTestId('tool-strike').click();
		await selectWords(page, 1, 'Abstract');
		await expect(marks(page, 'strike')).toHaveCount(1);
		await expect(page.getByTestId('highlight-offer')).toHaveCount(0);
		await published(served, 2);
		await page.keyboard.press('Escape');
		await expect(page.getByTestId('tool-select')).toHaveAttribute('aria-pressed', 'true');
		await selectWords(page, 1, 'Introduction');
		await expect(page.getByTestId('highlight-offer')).toBeVisible();
	});

	test('the drawing tools each leave a mark, a pin and words only once they say something, and a shape moves and resizes', async ({ page, served }) => {
		test.slow();
		await openPaper(page, `/file/${FILE}`);
		await page.getByTestId('markup-toggle').click();

		await page.getByTestId('tool-pin').click();
		await pressOn(page, 1, [0.1, 0.1]);
		await page.getByTestId('mark-done').click();
		await expect(marks(page, 'pin')).toHaveCount(0);
		await pressOn(page, 1, [0.1, 0.1]);
		await page.getByTestId('mark-comment').fill('see the second section');
		await page.getByTestId('mark-done').click();
		await expect(marks(page, 'pin')).toHaveCount(1);

		await page.getByTestId('tool-text').click();
		await pressOn(page, 1, [0.25, 0.08]);
		await page.getByTestId('mark-comment').fill('words on the page');
		await page.getByTestId('mark-done').click();
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

		// lines of ink drawn close together are one mark; a busy machine can leave more than `INK_PAUSE` between two drags, so that timer is held back here and the change of tool ends them
		const inkPause = await page.evaluateHandle(() => {
			const setTimeout = window.setTimeout;
			window.setTimeout = ((run: TimerHandler, ms = 0, ...rest: unknown[]) => (ms === 900 ? 0 : setTimeout(run, ms, ...rest))) as typeof window.setTimeout;
			return () => (window.setTimeout = setTimeout);
		});
		await page.getByTestId('tool-ink').click();
		await drag(page, 1, [0.5, 0.5], [0.6, 0.55]);
		await drag(page, 1, [0.6, 0.55], [0.7, 0.5]);
		await page.getByTestId('tool-select').click();
		await inkPause.evaluate((restore) => void restore());
		await expect(marks(page, 'ink')).toHaveCount(1);
		await published(served, 6);
		const ink = marksOf(served).find((n) => n.mark === 'ink')!;
		expect(ink.strokes).toHaveLength(2);

		// a press inside a shape looks at it; dragging moves it and the record follows
		const box = Object.entries(notes(served)).find(([, n]) => n.mark === 'box')!;
		const [x0, y0] = box[1].rects![0];
		await clickMark(page, `page-mark-${box[0]}`);
		await expect(page.getByTestId('mark-grab')).toBeVisible();
		const grab = (await page.getByTestId('mark-grab').boundingBox())!;
		await page.mouse.move(grab.x + grab.width / 2, grab.y + grab.height / 2);
		await page.mouse.down();
		await page.mouse.move(grab.x + grab.width / 2 + 30, grab.y + grab.height / 2 + 20, { steps: 4 });
		await page.mouse.up();
		await expect.poll(() => notes(served)[box[0]].rects![0][0]).toBeGreaterThan(x0 + 5);
		expect(notes(served)[box[0]].rects![0][1]).toBeGreaterThan(y0 + 5);
		const moved = notes(served)[box[0]].rects![0];
		const handle = (await page.getByTestId('mark-handle-se').boundingBox())!;
		await page.mouse.move(handle.x + 4, handle.y + 4);
		await page.mouse.down();
		await page.mouse.move(handle.x + 44, handle.y + 34, { steps: 4 });
		await page.mouse.up();
		await expect.poll(() => notes(served)[box[0]].rects![0][2]).toBeGreaterThan(moved[2] + 5);
		// and the keyboard takes it back, then takes it off the page
		await page.getByTestId('mark-done').click();
		await page.keyboard.press('ControlOrMeta+z');
		await expect.poll(() => notes(served)[box[0]].rects![0][2]).toBeCloseTo(moved[2], 0);
		await clickMark(page, `page-mark-${box[0]}`);
		await page.getByTestId('mark-done').focus();
		await page.locator('body').evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
		await page.keyboard.press('Delete');
		await expect(page.getByTestId(`page-mark-${box[0]}`)).toHaveCount(0);
	});

	test('a saved copy holds the marks as a PDF reader finds them, and its original bytes', async ({ page, served }) => {
		await openPaper(page, `/file/${FILE}`);
		await selectWords(page, 1, 'Cycle');
		await page.getByTestId('highlight-offer').click();
		await published(served, 1);
		const id = Object.keys(notes(served))[0];
		await clickMark(page, `page-mark-${id}`);
		await page.getByTestId('mark-comment').fill('in the copy');
		await page.getByTestId('mark-done').click();
		await expect.poll(() => notes(served)[id]?.body).toBe('in the copy');
		await page.getByTestId('markup-toggle').click();
		const [saved] = await Promise.all([page.waitForEvent('download'), page.getByTestId('mark-save-copy').click()]);
		expect(saved.suggestedFilename()).toBe('paper-annotated.pdf');
		const bytes = new Uint8Array(readFileSync(await saved.path()));
		const original = readFileSync(ARDEN);
		expect(Buffer.from(bytes.subarray(0, original.length)).equals(original)).toBe(true);
		const { items } = await readAnnotations(await open(bytes));
		expect(items).toHaveLength(1);
		expect(items[0]).toMatchObject({ mark: 'highlight', body: 'in the copy', page: 1 });
		await expect(page.getByTestId('mark-said')).toContainText('Saved a copy with 1 annotation');
	});

	test('annotations are taken in from another copy once, and never from a different paper', async ({ page, served }) => {
		const { bytes } = await annotatedCopy(pdfjs, { data: new Uint8Array(readFileSync(ARDEN)), verbosity: 0 }, [
			{ page: 1, kind: 'highlight', rects: [[206.99, 125.41, 293.37, 140.99]], body: 'from elsewhere', by: 'A Reader' },
			{ page: 1, kind: 'pin', rects: [[50, 50, 66, 66]], body: 'a sticky note', by: 'A Reader' }
		]);
		await openPaper(page, `/file/${FILE}`);
		await page.getByTestId('markup-toggle').click();
		const file = { name: 'marked.pdf', mimeType: 'application/pdf', buffer: Buffer.from(bytes) };
		await page.getByTestId('mark-take-file').setInputFiles(file);
		await expect(page.getByTestId('mark-said')).toContainText('Took in 2');
		await expect(marks(page)).toHaveCount(2);
		const taken = marksOf(served).find((n) => n.mark === 'highlight')!;
		expect(taken).toMatchObject({ body: 'from elsewhere', origin: { by: 'A Reader' } });
		expect(taken.quote).toContain('Cycle spaces');
		await page.getByTestId('mark-take-file').setInputFiles(file);
		await expect(page.getByTestId('mark-said')).toContainText('2 were here already');
		await page.getByTestId('mark-take-file').setInputFiles({ name: 'other.pdf', mimeType: 'application/pdf', buffer: readFileSync(BELLAMY) });
		await expect(page.getByTestId('mark-said')).toContainText('no place here');
		await published(served, 2);
	});

	test('edited pages are saved as a new file, opened, and the PDF being read stays as it was', async ({ page, served }) => {
		await openPaper(page, `/file/${FILE}`);
		await page.getByTestId('markup-toggle').click();
		await page.getByTestId('mark-pages').click();
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

	test('its comment can be read, and once taken in the note stands for it', async ({ page, served }) => {
		await openPaper(page, `/file/${FILE}`);
		const held = page.locator('[data-testid^="pdf-annotation-"]');
		await expect(held).toHaveCount(1);
		const box = (await held.boundingBox())!;
		await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
		await expect(page.getByTestId('mark-card-body')).toHaveText('said in Preview');
		await page.getByTestId('mark-done').click();
		await page.getByTestId('markup-toggle').click();
		await page.getByTestId('mark-take-here').click();
		await expect(page.getByTestId('mark-said')).toContainText('Took in 1');
		await expect(marks(page, 'highlight')).toHaveCount(1);
		await expect(held).toHaveCount(0);
		expect(marksOf(served)[0]).toMatchObject({ body: 'said in Preview' });
		// a copy holds it once
		const [saved] = await Promise.all([page.waitForEvent('download'), page.getByTestId('mark-save-copy').click()]);
		const { items } = await readAnnotations(await open(new Uint8Array(readFileSync(await saved.path()))));
		expect(items.map((i) => i.body)).toEqual(['said in Preview']);
	});
});

test.describe('where no publisher takes writes', () => {
	test.use({
		prepareQuilt: async ({}, use) => {
			await use(({ loom }) => {
				loom(['note', '--on', 'Bellamy19', '--page', '2', '--box', '50,50,100,60', '--mark', 'box', '--as', 'A Person']);
			});
		}
	});

	test('marks are drawn, the tools are not offered, and a copy can still be saved', async ({ page }) => {
		await page.route('**/_api', (route) => route.fulfill({ status: 404, body: '' }));
		await openPaper(page, '/library/Bellamy19?page=2', 2);
		await expect(marks(page, 'box')).toHaveCount(1);
		await page.getByTestId('markup-toggle').click();
		await expect(page.getByTestId('tool-highlight')).toHaveCount(0);
		await expect(page.getByTestId('mark-save-copy')).toBeVisible();
		await selectWords(page, 2, 'order');
		await expect(page.getByTestId('highlight-offer')).toHaveCount(0);
		const [saved] = await Promise.all([page.waitForEvent('download'), page.getByTestId('mark-save-copy').click()]);
		expect(saved.suggestedFilename()).toBe('Bellamy19-annotated.pdf');
		const { items } = await readAnnotations(await open(new Uint8Array(readFileSync(await saved.path()))));
		expect(items.map((i) => i.mark)).toContain('ink');
	});
});
