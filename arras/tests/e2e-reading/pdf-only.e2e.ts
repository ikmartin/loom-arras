// A PDF and nothing else (plan 0.30.2): Bellamy19 in the showcase, and a project's own PDF. Every annotation on their pages with a place on one is drawn there in its look, sidecar's and drawings alike; one detached from a changed file is listed in Comments and drawn on no page; one found again on a changed file says so in its popup. The PDF's toolbar is the one a document has, then the PDF's own tools, in either theme.
//
// Rows the fixture does not carry yet are added to the manifest as served: a drawing, an underline and a strike, an own colour, a taken-in mark, a resolved one, a detached one and a re-found one.
import { expect, readOnly, test } from '../served';
import type { Page, Locator } from '@playwright/test';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ARDEN = fileURLToPath(new URL('../../../loom/tests/quilts/sources/showcase-works/arden-cycle-spaces.pdf', import.meta.url));
const FILE = 'notes/paper.pdf';

type Row = { id: string; in_reply_to: string | null; detached: boolean; rects?: number[][] | null; mark?: string | null; look: { style?: string; color?: string }; target: { key: string; work?: string | null; file?: string | null; page?: number | null } };
type Rows = Record<string, Row>;

/** A hand-made annotation on a PDF's page, on the fields of `base` so that every one the viewer reads is there. */
function made(base: Row, id: string, target: Row['target'], over: Record<string, unknown>): Row {
	return { ...structuredClone(base), id, target, in_reply_to: null, status: 'open', type: null, detached: false, anchored: true, recorded: true, refound: null, gap: null, source: null, origin: null, hides: null, version: null, basis: null, quote: undefined, strokes: null, mark: null, body: '', body_html: '', ...over } as Row;
}

const look = (color: string, style: string, weight = 2, opacity = 100) => ({ color, style, weight, opacity });

/** Serve the manifest with `rows(manifest)` added to its annotations. */
async function adding(page: Page, rows: (m: { annotations: Rows; references: Record<string, { work: string }> }) => Row[]): Promise<void> {
	await page.route('**/build/manifest.json', async (route) => {
		// asked afresh, so a copy the browser holds never comes back as an empty 304
		const headers = Object.fromEntries(Object.entries(route.request().headers()).filter(([k]) => !/^if-(none-match|modified-since)$/i.test(k)));
		const res = await route.fetch({ headers });
		const m = await res.json();
		for (const r of rows(m)) m.annotations[r.id] = r;
		await route.fulfill({ status: 200, json: m });
	});
}

/** The manifest as this page is served it. */
const asServed = (page: Page) => page.evaluate(() => fetch('/build/manifest.json').then((r) => r.json())) as Promise<{ annotations: Rows }>;

/** The top-level annotations on the pages of a PDF, by what owns them. */
const onPages = (rows: Rows, owns: (r: Row) => boolean) => Object.values(rows).filter((r) => !r.in_reply_to && (r.target.page ?? 0) > 0 && owns(r));

/** Bring page `n` into view, where its marks are drawn. */
async function toPage(page: Page, n: number): Promise<void> {
	const at = page.getByTestId(`pdf-page-${n}`);
	await at.scrollIntoViewIfNeeded();
	// its words are laid over it once it is drawn; Bellamy19's last page holds a few lines only
	await expect.poll(() => at.locator('.text span').count()).toBeGreaterThan(0);
}

/** Open Comments with the resolved shown, so that every annotation here is listed and drawn. */
async function everyComment(page: Page): Promise<Locator> {
	await page.getByTestId('open-comments').click();
	const list = page.getByTestId('side-list');
	await list.getByTestId('comments-filter').click();
	await list.getByTestId('filter-resolved').check();
	await list.getByTestId('comments-filter').click();
	return list;
}

/** Every row with a place is drawn on its page and none other is; every detached one is listed, saying so, and drawn nowhere. */
async function drawnAndListed(page: Page, rows: Row[]): Promise<void> {
	const list = await everyComment(page);
	const pages = [...new Set(rows.map((r) => r.target.page!))].sort((a, b) => a - b);
	for (const n of pages) {
		await toPage(page, n);
		for (const r of rows.filter((x) => x.target.page === n)) {
			const mark = page.getByTestId(`page-mark-${r.id}`);
			if (r.detached) await expect(mark, `${r.id} is detached, so drawn nowhere`).toHaveCount(0);
			else await expect(page.getByTestId(`pdf-page-${n}`).getByTestId(`page-mark-${r.id}`), `${r.id} is drawn on page ${n}`).toHaveCount(1);
		}
	}
	for (const r of rows) await expect(list.locator(`[data-testid="comment-card"][data-annotation="${r.id}"]`), `${r.id} is listed`).toHaveCount(1);
	for (const r of rows.filter((x) => x.detached)) await expect(list.locator(`[data-testid="comment-card"][data-annotation="${r.id}"]`).getByTestId('card-detached')).toBeVisible();
}

/** Click the middle of a mark that takes no pointer: the page below is asked what the click landed on. */
async function clickMark(page: Page, id: string): Promise<void> {
	const box = (await page.getByTestId(`page-mark-${id}`).boundingBox())!;
	await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
}

const paint = (page: Page, testid: string, name: string) => page.getByTestId(testid).evaluate((el, n) => getComputedStyle(el).getPropertyValue(n).trim(), name);

// an effect that feeds itself fails the test that caused it
test.beforeEach(({ page }, info) => {
	page.on('pageerror', (e) => info.annotations.push({ type: 'pageerror', description: e.message }));
});
test.afterEach(({}, info) => {
	expect(info.annotations.filter((a) => a.type === 'pageerror')).toEqual([]);
});

readOnly("every annotation on a cited work's pages with a place is drawn there in its look, and a detached one is listed and drawn nowhere", async ({ page }) => {
	await adding(page, (m) => {
		const base = Object.values(m.annotations)[0];
		const on = (p: number) => ({ key: m.references.Bellamy19.work, work: 'Bellamy19', page: p });
		return [
			made(base, 'a-pdf-only-box', on(1), { mark: 'box', rects: [[60, 60, 200, 110]], look: look('green', 'highlight', 3) }),
			made(base, 'a-pdf-only-ink', on(1), { mark: 'ink', rects: [[300, 60, 400, 110]], strokes: [[300, 60, 350, 110, 400, 60]], look: look('blue', 'highlight') }),
			made(base, 'a-pdf-only-arrow', on(1), { mark: 'arrow', status: 'resolved', rects: [[420, 60, 520, 110]], strokes: [[420, 60, 520, 110]], look: look('orange', 'highlight') }),
			made(base, 'a-pdf-only-under', on(2), { rects: [[72, 600, 300, 612]], quote: 'under these words', look: look('red', 'underline') }),
			made(base, 'a-pdf-only-strike', on(2), { rects: [[72, 630, 300, 642]], quote: 'through these words', look: look('purple', 'strike', 1) }),
			made(base, 'a-pdf-only-taken', on(3), { rects: [[72, 200, 300, 214]], quote: 'taken in', origin: { by: 'A Reader', subtype: 'Highlight' }, look: look('pink', 'highlight', 2, 40) }),
			made(base, 'a-pdf-only-refound', on(3), { rects: [[72, 240, 300, 254]], quote: 'moved down a line', refound: true, body: 'found again', body_html: '<p>found again</p>', look: look('blue', 'highlight') }),
			made(base, 'a-pdf-only-gone', on(2), { mark: 'oval', detached: true, anchored: false, rects: null, body: 'its words are gone', body_html: '<p>its words are gone</p>', look: look('grey', 'highlight') })
		];
	});
	await page.goto('/library/Bellamy19?page=1');
	await toPage(page, 1);
	const rows = onPages((await asServed(page)).annotations, (r) => r.target.work === 'Bellamy19');
	expect(rows.filter((r) => r.detached).length).toBeGreaterThan(0);
	await drawnAndListed(page, rows);

	// each in its own look: the tool's shape or the look's style, its colour, weight and opacity
	await toPage(page, 1);
	await expect(page.getByTestId('page-mark-a-pdf-only-box')).toHaveAttribute('data-kind', 'box');
	expect(await paint(page, 'mark-line-a-pdf-only-box', '--weight')).toBe('3');
	await expect(page.getByTestId('page-mark-a-pdf-only-ink')).toHaveAttribute('data-kind', 'ink');
	await expect(page.getByTestId('mark-line-a-pdf-only-arrow')).toHaveClass(/settled/);
	await toPage(page, 2);
	await expect(page.getByTestId('page-mark-a-pdf-only-under')).toHaveAttribute('data-kind', 'underline');
	await expect(page.getByTestId('page-mark-a-pdf-only-strike')).toHaveAttribute('data-kind', 'strike');
	expect(await paint(page, 'mark-line-a-pdf-only-strike', '--line')).toBe(await paint(page, 'mark-line-a-pdf-only-strike', '--ann-purple'));
	await toPage(page, 3);
	expect(await paint(page, 'mark-band-a-pdf-only-taken', '--band-strength')).toBe('0.4');
	expect(await paint(page, 'mark-band-a-pdf-only-taken', '--band')).toBe(await paint(page, 'mark-band-a-pdf-only-taken', '--ann-pink-band'));

	// a mark found again on a changed file says where, and offers no version to open
	await page.getByTestId('side-close').click();
	await clickMark(page, 'a-pdf-only-refound');
	const p = page.getByTestId('ann-popup');
	await expect(p).toHaveAttribute('data-annotation-id', 'a-pdf-only-refound');
	await expect(p.getByTestId('popup-refound')).toHaveText('Found again on page 3 of the changed PDF.');
	await expect(p.getByTestId('popup-earlier')).toHaveCount(0);
});

test.describe("a project's PDF", () => {
	test.use({
		prepareQuilt: async ({}, use) => {
			await use(({ root }) => {
				mkdirSync(join(root, 'notes'), { recursive: true });
				writeFileSync(join(root, FILE), readFileSync(ARDEN));
			});
		}
	});

	test('its annotations with a place are drawn, a detached one is listed and drawn nowhere, and a re-found one says so', async ({ page }) => {
		await adding(page, (m) => {
			const base = Object.values(m.annotations)[0];
			const on = (p: number) => ({ key: FILE, file: FILE, page: p });
			return [
				made(base, 'a-pdf-only-oval', on(1), { mark: 'oval', rects: [[60, 60, 200, 110]], look: look('green', 'highlight', 4) }),
				made(base, 'a-pdf-only-moved', on(2), { rects: [[72, 240, 300, 254]], quote: 'moved down a line', refound: true, look: look('yellow', 'highlight', 2, 60) }),
				made(base, 'a-pdf-only-lost', on(1), { mark: 'pin', detached: true, anchored: false, rects: null, body: 'beside words now gone', body_html: '<p>beside words now gone</p>', look: look('red', 'highlight') })
			];
		});
		await page.goto(`/file/${FILE}`);
		await toPage(page, 1);
		const rows = onPages((await asServed(page)).annotations, (r) => r.target.file === FILE);
		expect(rows.map((r) => r.id).sort()).toEqual(['a-pdf-only-lost', 'a-pdf-only-moved', 'a-pdf-only-oval']);
		await drawnAndListed(page, rows);
		await page.getByTestId('side-close').click();
		await toPage(page, 2);
		await clickMark(page, 'a-pdf-only-moved');
		await expect(page.getByTestId('ann-popup').getByTestId('popup-refound')).toHaveText('Found again on page 2 of the changed PDF.');
	});
});

test.describe('the toolbar', () => {
	test.use({
		prepareQuilt: async ({}, use) => {
			await use(({ root }) => {
				mkdirSync(join(root, 'notes'), { recursive: true });
				writeFileSync(join(root, FILE), readFileSync(ARDEN));
			});
		}
	});

	/** The row that reads, left to right: Annotate, Comments and Notes, PDF ▾, and the zoom and the page. */
	const BAR = ['toggle-annotation-row', 'open-comments', 'open-notes', 'pdf-menu', 'zoom-fit', 'zoom-out', 'zoom-at', 'zoom-in', 'page-at'];
	/** The annotation row beneath it, left to right: a document's annotating tools, then the PDF's drawing tools. */
	const ROW = ['tool-annotate', 'tool-comment', 'format-toggle', 'annotate-undo', 'annotate-redo', 'tool-ink', 'tool-text', 'tool-rect', 'tool-oval', 'tool-arrow'];

	/** How light a colour an element is drawn in, 0 to 1, read off a canvas so that any notation the browser gives it is read alike; a background is the first one not transparent, from the element out. */
	const lightness = (loc: Locator, prop: 'color' | 'backgroundColor') =>
		loc.evaluate((el, p) => {
			const c = document.createElement('canvas').getContext('2d', { willReadFrequently: true })!;
			for (let n: Element | null = el; n; n = n.parentElement) {
				c.clearRect(0, 0, 1, 1);
				c.fillStyle = getComputedStyle(n)[p];
				c.fillRect(0, 0, 1, 1);
				const [r, g, b, a] = c.getImageData(0, 0, 1, 1).data;
				if (a > 200) return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
			}
			return -1;
		}, prop);

	for (const scheme of ['light', 'dark'] as const) {
		test(`a cited work and a project PDF carry the same bar, in the ${scheme} theme`, async ({ page }) => {
			await page.emulateMedia({ colorScheme: scheme });
			for (const url of ['/library/Bellamy19?page=1', `/file/${FILE}`]) {
				await page.goto(url);
				await toPage(page, 1);
				const tops: number[] = [];
				for (const row of [BAR, ROW]) {
					let left = -Infinity;
					for (const id of row) {
						const at = page.getByTestId(id);
						await expect(at, `${url}: ${id}`).toBeVisible();
						const box = (await at.boundingBox())!;
						expect(box.x, `${url}: ${id} after the one before it`).toBeGreaterThan(left);
						left = box.x;
					}
					tops.push((await page.getByTestId(row[0]).boundingBox())!.y);
				}
				expect(tops[1], `${url}: the annotation row beneath the row that reads`).toBeGreaterThan(tops[0]);
				// drawn in the theme: dark words on light, light on dark, in the bar and in the menus it opens
				const words = await lightness(page.getByTestId('open-comments'), 'color');
				expect(scheme === 'light' ? words < 0.5 : words > 0.5, `${url}: the bar's words in the ${scheme} theme`).toBe(true);
				await page.getByTestId('format-toggle').click();
				const menu = await lightness(page.getByTestId('format-menu'), 'backgroundColor');
				expect(scheme === 'light' ? menu > 0.5 : menu < 0.5, `${url}: the format menu in the ${scheme} theme`).toBe(true);
				await page.keyboard.press('Escape');
				await page.getByTestId('pdf-menu').click();
				await expect(page.getByTestId('mark-save-copy')).toBeVisible();
				const items = await lightness(page.getByTestId('pdf-menu-items'), 'backgroundColor');
				expect(scheme === 'light' ? items > 0.5 : items < 0.5, `${url}: PDF ▾ in the ${scheme} theme`).toBe(true);
				await page.keyboard.press('Escape');
				// and Annotate draws on it
				await page.getByTestId('tool-annotate').click();
				await expect(page.getByTestId('tool-annotate')).toHaveAttribute('aria-pressed', 'true');
				await page.keyboard.press('Escape');
			}
		});
	}
});
