// Reading a cited work under `loom serve` (plan 0.13 §11): the things the fixture-only suite cannot check because
// they need the publisher — a selection mapped onto the committed page text and recorded, a box recorded as drawn,
// the marks the sidecar then carries, and a locator lit from a link.
//
// Every test starts from the showcase copy the config staged, and the notes it writes accumulate in it; each one
// therefore reads back what it wrote by id rather than by count.
import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';

const QUILT = '.tmp-reading-quilt';
const PAGE2 = '/library/Bellamy19?page=2';

function log(): Record<string, unknown>[] {
	return readFileSync(`${QUILT}/annotations/log.jsonl`, 'utf8')
		.split('\n')
		.filter(Boolean)
		.map((l) => JSON.parse(l));
}

async function opened(page: Page): Promise<void> {
	await page.goto(PAGE2);
	await page.locator('[data-testid="pdf-page-2"] canvas').waitFor();
	await expect.poll(() => page.locator('[data-testid="pdf-page-2"] .text span').count()).toBeGreaterThan(50);
	await intoASession(page);
}

/**
 * Choose where the notes will be filed.
 *
 * A write names its session and nothing is selected at rest (plan 0.13.1), so this is the first thing a reader does
 * before annotating — and therefore the first thing these tests do. Opening one when the showcase has none is the same
 * two clicks the interface asks for.
 */
async function intoASession(page: Page): Promise<void> {
	if ((await page.locator('[data-testid="session-list"] li.selected').count()) === 1) return;
	const first = page.getByTestId('session-list').locator('[data-testid^="session-s-"]').first();
	if (await first.count()) {
		await first.click();
	} else {
		await page.getByTestId('session-new').click();
		await page.getByTestId('session-new-title').fill('reading Bellamy 19');
		await page.getByTestId('session-new-title').press('Enter');
	}
	await expect(page.locator('[data-testid="session-list"] li.selected')).toHaveCount(1);
}

/** Select a phrase on the page the way a reader does: a Range over the text layer and the release the handler reads. */
async function select(page: Page, phrase: string): Promise<void> {
	await page
		.locator(`[data-testid="pdf-page-2"] .text span:has-text("${phrase}")`)
		.first()
		.evaluate((node) => {
			const range = document.createRange();
			range.selectNodeContents(node);
			const sel = window.getSelection();
			sel?.removeAllRanges();
			sel?.addRange(range);
			node.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
		});
}

test('a note is written from a selection, and the page shows loom’s own words before anything is recorded', async ({ page }) => {
	await opened(page);
	await select(page, 'incidence matrix');
	const form = page.getByTestId('note-at');
	await expect(form).toBeVisible();
	// the preview: what loom found on the page, in its own words, before the note is typed
	await expect(page.getByTestId('note-where')).toContainText('anchored by text');
	await expect(page.getByTestId('note-quote')).toContainText('incidence matrix');
	await page.getByTestId('note-body').fill('So the vertices are integral.');
	await page.getByTestId('note-kind').selectOption('note');
	await page.getByTestId('note-submit').click();
	await expect(form).toBeHidden();
	const written = log().at(-1)!;
	expect(written.target).toBe('doi:10.4171/showcase/19-2');
	const anchor = written.anchor as Record<string, unknown>;
	expect(anchor.basis).toBe('text');
	expect(anchor.page).toBe(2);
	expect(String(anchor.exact)).toContain('incidence matrix');
	expect(anchor).not.toHaveProperty('quads'); // derived at build time, never recorded for text
	// and the mark appears once the publisher has rebuilt the sidecar
	await expect(page.getByTestId(`mark-${written.id}`)).toBeVisible({ timeout: 15000 });
	await expect(page.getByTestId(`mark-${written.id}`)).toHaveClass(/k-note/);
});

test('a box is recorded as drawn, and the words under it are its hint', async ({ page }) => {
	await opened(page);
	await page.getByTestId('tool-box').click();
	await expect(page.locator('[data-testid="pdf-page-2"].boxing')).toBeVisible(); // the tool has taken
	const canvas = page.locator('[data-testid="pdf-page-2"] canvas');
	// the column, not the window: the page's top at the top of the reader, so the display a third of the way down is in view
	await canvas.evaluate((c) => c.scrollIntoView({ block: 'start' }));
	// the pages either side report their sizes just after the first draw, which moves page 2 under a box measured
	// too early: wait until its position holds still before drawing on it
	let box = (await canvas.boundingBox())!;
	await expect
		.poll(async () => {
			const again = (await canvas.boundingBox())!;
			const same = Math.abs(again.y - box.y) < 1 && Math.abs(again.height - box.height) < 1;
			box = again;
			return same;
		}, { intervals: [300, 300, 300, 300], timeout: 5000 })
		.toBe(true);
	// traced, so a drag that draws nothing says what the pointer actually hit
	await page.evaluate(() => {
		const w = window as unknown as { __ev: string[] };
		w.__ev = [];
		for (const t of ['pointerdown', 'pointermove', 'pointerup']) {
			document.addEventListener(t, (e) => w.__ev.push(`${t}:${((e.target as Element).className || (e.target as Element).tagName).toString().slice(0, 30)}`), true);
		}
	});
	// the display on page 2, in the page's own proportions
	await page.mouse.move(box.x + box.width * 0.15, box.y + box.height * 0.36);
	await page.mouse.down();
	await page.mouse.move(box.x + box.width * 0.85, box.y + box.height * 0.4, { steps: 6 });
	await page.mouse.up();
	const seen = await page.evaluate(() => (window as unknown as { __ev: string[] }).__ev.slice(0, 10));
	await expect(page.getByTestId('note-at'), `the pointer saw: ${seen.join(' ')}`).toBeVisible();
	await expect(page.getByTestId('note-where')).toContainText('anchored by box');
	await page.getByTestId('note-body').fill('This is the display I want to cite.');
	await page.getByTestId('note-submit').click();
	await expect(page.getByTestId('note-at')).toBeHidden();
	const written = log().at(-1)!;
	const anchor = written.anchor as Record<string, unknown>;
	expect(anchor.basis).toBe('box');
	expect(Array.isArray(anchor.quads) && (anchor.quads as number[][]).length).toBe(1);
	await expect(page.getByTestId(`mark-${written.id}`)).toBeVisible({ timeout: 15000 });
});

test('a mark opens the box a fragment opens, Escape closes it, and the discussion lists the note with its page', async ({ page }) => {
	await opened(page);
	const mark = page.locator('[data-testid="pdf-page-2"] .mark.note').first();
	await expect(mark).toBeVisible();
	const id = (await mark.getAttribute('data-mark'))!;
	await mark.click();
	const open = page.getByTestId('comment-expanded');
	await expect(open).toBeVisible();
	await expect(open.locator('article.box').first()).toBeVisible();
	await page.keyboard.press('Escape');
	await expect(open).toHaveCount(0);
	// beside it: the note, with the page it is on
	await expect(page.getByTestId(`beside-${id}`)).toBeVisible();
	await expect(page.getByTestId(`beside-page-${id}`)).toContainText('p.2');
	// and travel both ways: the row to the mark, the mark to the row
	await page.getByTestId(`beside-${id}`).getByRole('button').first().click();
	await expect(page.getByTestId(`mark-${id}`)).toBeInViewport();
	await mark.dblclick();
	await expect(page.getByTestId(`beside-${id}`)).toBeInViewport();
});

test('the margin column stands beside the page, and inline is never offered on it', async ({ page }) => {
	// set by evaluate rather than an init script, which would re-impose `margin` on every navigation below
	await page.goto('/');
	await page.evaluate(() => localStorage.setItem('arras.prefs', JSON.stringify({ comments: 'margin' })));
	await opened(page);
	await expect(page.locator('[data-testid="pdf-page-2"] .mark.note').first()).toBeVisible({ timeout: 15000 }); // the sidecar, after the publisher's rebuild
	const margin = page.getByTestId('reading-margin');
	await expect(margin).toBeVisible();
	await expect(margin.locator('article.box').first()).toBeVisible();
	await page.evaluate(() => localStorage.setItem('arras.prefs', JSON.stringify({ comments: 'inline' })));
	await opened(page);
	await expect(page.getByTestId('reading-margin')).toHaveCount(0);
	await page.locator('[data-testid="pdf-page-2"] .mark.note').first().click();
	// inline is the Authoring View's alone: a PDF page cannot reflow, so the box floats
	await expect(page.getByTestId('comment-expanded')).toHaveClass(/floating/);
});

test('the session selection governs the page: a hidden note is counted, not drawn', async ({ page }) => {
	await opened(page);
	await expect(page.locator('[data-testid="pdf-page-2"] .mark.note').first()).toBeVisible({ timeout: 15000 }); // the sidecar, after the publisher's rebuild
	const before = await page.locator('[data-testid="pdf-page-2"] .mark.note').count();
	// a fresh session, empty, made the active one; showing only it hides every note the earlier tests wrote
	await page.getByTestId('session-new').click();
	await page.getByTestId('session-new-title').fill('an empty sitting');
	await page.getByTestId('session-new-title').press('Enter');
	// `+ new` selects what it opens, since nothing is created automatically any more (plan 0.13.1)
	await expect(page.locator('[data-testid="session-list"] li.selected')).toContainText('an empty sitting', { timeout: 10000 });
	await page.getByTestId('show-current').click();
	await expect(page.getByTestId('reading-hidden')).toContainText('hidden by the session being shown');
	expect(await page.locator('[data-testid="pdf-page-2"] .mark.note').count()).toBeLessThan(before);
	const hiddenUnderThis = Number((await page.getByTestId('reading-hidden').textContent())!.match(/\d+/)![0]);
	await page.getByTestId('show-all').click();
	// `all` still hides the showcase's own notes, which sit in a closed session; what changes is that this suite's
	// come back, so the count drops rather than vanishes
	await expect(page.locator('[data-testid="pdf-page-2"] .mark.note')).toHaveCount(before);
	const hiddenUnderAll = Number((await page.getByTestId('reading-hidden').textContent())!.match(/\d+/)![0]);
	expect(hiddenUnderAll).toBeLessThan(hiddenUnderThis);
});

test('a locator in the URL is lit while the URL carries it, and a note is focused by its id', async ({ page }) => {
	await opened(page);
	const pageText = readFileSync(`${QUILT}/digests/storage/doi/10.4171_showcase_19-2/pages/0002.txt`, 'utf8');
	const a = pageText.indexOf('totally unimodular');
	await page.goto(`${PAGE2}&span=${a}-${a + 'totally unimodular'.length}`);
	const lit = page.locator('[data-testid="pdf-page-2"] .mark.transient');
	await expect(lit).toBeVisible();
	await expect(lit).toHaveClass(/on/); // and it is the one in focus
	// a note by id: one this suite wrote, since the showcase's own are in a closed session and closed sessions'
	// annotations are hidden until shown
	const mine = log().filter((e) => e.event === 'created' && (e.anchor as Record<string, unknown>)?.kind === 'pdf').at(-1)!;
	await page.goto(`${PAGE2}&annot=${mine.id}`);
	await expect(page.getByTestId(`mark-${mine.id}`)).toHaveClass(/on/, { timeout: 15000 });
});

test('a session is named on the spot and closed from the page', async ({ page }) => {
	await opened(page);
	await page.getByTestId('session-new').click();
	await page.getByTestId('session-new-title').fill('reading Bellamy, closely');
	await page.getByTestId('session-new-title').press('Enter');
	// it is selected on being opened, and the discussion says so because that is where a reply would land
	await expect(page.locator('[data-testid="session-list"] li.selected')).toContainText('reading Bellamy, closely', { timeout: 10000 });
	await expect(page.getByTestId('discussion-into')).toContainText('reading Bellamy, closely');
	// closing the selected session clears the selection, so writing is unavailable until another is chosen
	await page.locator('[data-testid="session-list"] li.selected [data-testid^="session-close-"]').click();
	await expect(page.locator('[data-testid="session-list"] li.selected')).toHaveCount(0, { timeout: 10000 });
	await expect(page.getByTestId('discussion-into')).toContainText('no session selected');
});

test('two notes on one place are one mark carrying the count, and one box holding both', async ({ page }) => {
	await opened(page);
	for (const body of ['first on this phrase', 'second on this phrase']) {
		await select(page, 'Boundedness holds');
		await expect(page.getByTestId('note-at')).toBeVisible();
		await page.getByTestId('note-body').fill(body);
		await page.getByTestId('note-submit').click();
		await expect(page.getByTestId('note-at')).toBeHidden();
	}
	const stacked = page.locator('[data-testid="pdf-page-2"] .mark.note[data-count]').first();
	await expect(stacked).toBeVisible({ timeout: 15000 });
	await expect(stacked).toHaveAttribute('data-count', /^[2-9]$/);
	await stacked.click();
	await expect(page.getByTestId('comment-expanded').locator('article.box')).toHaveCount(Number(await stacked.getAttribute('data-count')));
});

test('a box shows the write it fired, without being closed and reopened', async ({ page }) => {
	// `openAt` mounted the card with the annotation as it was and nothing updated it, so resolving from a box left the
	// box saying `open` with the same verbs. In the study the reader clicked twice for that reason and the append-only
	// log took two `resolved` events for one annotation.
	await opened(page);
	// a note of its own, on a phrase no other test in this file uses: sharing one would stack the marks, and a stacked
	// mark carries the first id rather than the newest
	await select(page, 'exchange inequalities');
	await expect(page.getByTestId('note-at')).toBeVisible();
	await page.getByTestId('note-body').fill('resolve me');
	await page.getByTestId('note-submit').click();
	await expect(page.getByTestId('note-at')).toBeHidden();
	const id = (log().at(-1) as { id: string }).id;
	const mark = page.getByTestId(`mark-${id}`);
	await expect(mark).toBeVisible({ timeout: 15000 });
	await mark.click();
	const box = page.getByTestId('comment-expanded');
	await expect(box.locator('.status').first()).toHaveText('open');
	await box.getByTestId('verb-resolve').first().click();
	// the same box, still open, still where the reader put it
	await expect(box.locator('.status').first()).toHaveText('resolved', { timeout: 10000 });
	// the button that fired it becomes its own undo, where it stood
	await expect(box.getByTestId('verb-undo-resolve').first()).toBeVisible();
	const undo = box.getByTestId('verb-undo-resolve').first();
	await undo.click();
	await expect(box.locator('.status').first()).toHaveText('open', { timeout: 10000 });
});
