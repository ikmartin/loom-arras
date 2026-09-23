// Reading a cited work under `loom serve` (plan 0.13 §11): the things the fixture-only suite cannot check because
// they need the publisher — a selection mapped onto the committed page text and recorded, a box recorded as drawn,
// the marks the sidecar then carries, and a locator lit from a link.
//
// Every test starts from the showcase copy the config staged, and the notes it writes accumulate in it; each one
// therefore reads back what it wrote by id rather than by count.
import { expect, test, type Page } from '@playwright/test';
import { openPicker } from '../picker';
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
	// choosing a session opens its discussion beside, which narrows the paper's pane and draws its pages again at the zoom that fits; a selection made while the text layer is being replaced would be lost with it
	await page.waitForTimeout(1500);
	await expect.poll(() => page.locator('[data-testid="pdf-page-2"] .text span').count()).toBeGreaterThan(50);
}

/**
 * Choose where the notes will be filed.
 *
 * A write names its session and nothing is selected at rest (plan 0.13.1), so this is the first thing a reader does
 * before annotating — and therefore the first thing these tests do. Opening one when the showcase has none is the same
 * two clicks the interface asks for.
 */
async function intoASession(page: Page): Promise<void> {
	if ((await page.getByTestId('session-footer').getAttribute('aria-label'))?.startsWith('annotations are written into')) return;
	await openPicker(page);
	const first = page.getByTestId('session-list').locator('[data-testid^="session-s-"]').first();
	if (await first.count()) {
		await first.click();
	} else {
		await page.getByTestId('session-new').click();
		await page.getByTestId('session-new-title').fill('reading Bellamy 19');
		await page.getByTestId('session-new-title').press('Enter');
	}
	await expect(page.getByTestId('session-footer')).toHaveAttribute('aria-label', /^annotations are written into/);
}

/**
 * Select a phrase and ask to annotate it, the way a reader does.
 *
 * Selecting no longer opens the composer by itself: the selection stays live so it can be copied, and an *annotate*
 * chip offers the other thing. Both halves are exercised here, because a test that reached the composer without the
 * chip would not notice the chip disappearing.
 */
async function select(page: Page, phrase: string): Promise<void> {
	await selectOnly(page, phrase);
	await page.getByTestId('annotate-offer').click();
}

/** The selection alone, for a test about what selecting does on its own. */
async function selectOnly(page: Page, phrase: string): Promise<void> {
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

test('selecting text leaves it selected, and only offers to annotate it', async ({ page }) => {
	// Highlighting a phrase to copy it is the ordinary thing to do with a paper. The composer used to open on every
	// mouse-up, so it could not be done at all; now the selection survives and the chip is the way to the composer.
	await opened(page);
	await selectOnly(page, 'incidence matrix');
	await expect(page.getByTestId('note-at')).toHaveCount(0);
	expect(await page.evaluate(() => window.getSelection()?.toString() ?? '')).toContain('incidence matrix');
	await expect(page.getByTestId('annotate-offer')).toBeVisible();
	await page.getByTestId('annotate-offer').click();
	await expect(page.getByTestId('note-at')).toBeVisible();
});

test('a note is written from a selection, and the page shows loom’s own words before anything is recorded', async ({ page }) => {
	await opened(page);
	await select(page, 'incidence matrix');
	const form = page.getByTestId('note-at');
	await expect(form).toBeVisible();
	// the preview: what loom found on the page, in its own words, before the note is typed
	await expect(page.getByTestId('note-where')).toContainText('anchored by text');
	// the composer is a comment box and nothing else: the words stay lit on the page instead of being quoted in it
	await expect(page.getByTestId('note-quote')).toHaveCount(0);
	await expect.poll(() => page.evaluate(() => [...((CSS as unknown as { highlights: Map<string, { values(): Iterable<Range> }> }).highlights.get('note-pending')?.values() ?? [])].map((r) => r.toString()).join(' '))).toContain('incidence matrix');
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
	await expect(mark).toBeVisible({ timeout: 15000 }); // the sidecar, after the publisher's rebuild
	const id = (await mark.getAttribute('data-mark'))!;
	await mark.click();
	const open = page.getByTestId('comment-expanded');
	await expect(open).toBeVisible();
	await expect(open.locator('article.box').first()).toBeVisible();
	await page.keyboard.press('Escape');
	await expect(open).toHaveCount(0);
	// beside it, in the discussion of the session it was written in: the note, with the page it is on
	await page.getByTestId('open-discussion').click();
	await expect(page.getByTestId(`beside-${id}`)).toBeVisible();
	await expect(page.getByTestId(`beside-page-${id}`)).toContainText('p.2');
	// and travel both ways: the row to the mark, the mark to the row
	await page.getByTestId(`beside-${id}`).getByRole('button').first().click();
	await expect(page.getByTestId(`mark-${id}`)).toBeInViewport();
	await mark.dblclick();
	await expect(page.getByTestId(`beside-${id}`)).toBeInViewport();
});

test('inline is never offered on a page, and a note opens floating', async ({ page }) => {
	// A PDF page cannot reflow, so there is nowhere for an inline box to go. The margin column this test also covered
	// is retired with the `margin` placement.
	await page.goto('/');
	await page.evaluate(() => localStorage.setItem('arras.prefs', JSON.stringify({ comments: 'inline' })));
	await opened(page);
	await expect(page.locator('[data-testid="pdf-page-2"] .mark.note').first()).toBeVisible({ timeout: 15000 });
	await page.locator('[data-testid="pdf-page-2"] .mark.note').first().click();
	await expect(page.getByTestId('comment-expanded')).toHaveClass(/floating/);
});

test('the session selection governs the page: a hidden note is counted, not drawn', async ({ page }) => {
	await opened(page);
	await expect(page.locator('[data-testid="pdf-page-2"] .mark.note').first()).toBeVisible({ timeout: 15000 }); // the sidecar, after the publisher's rebuild
	const before = await page.locator('[data-testid="pdf-page-2"] .mark.note').count();
	// a fresh session, empty, made the active one; showing only it hides every note the earlier tests wrote
	await openPicker(page);
	await page.getByTestId('session-new').click();
	await page.getByTestId('session-new-title').fill('an empty sitting');
	await page.getByTestId('session-new-title').press('Enter');
	// `+ new` selects what it opens, since nothing is created automatically any more (plan 0.13.1)
	await expect(page.getByTestId('session-footer-name')).toContainText('an empty sitting', { timeout: 10000 });
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
	await openPicker(page);
	await page.getByTestId('session-new').click();
	await page.getByTestId('session-new-title').fill('reading Bellamy, closely');
	await page.getByTestId('session-new-title').press('Enter');
	// it is selected on being opened, and the footer says so because that is where a note would land
	await expect(page.getByTestId('session-footer-name')).toContainText('reading Bellamy, closely', { timeout: 10000 });
	// closing the selected session clears the selection, so writing is unavailable until another is chosen
	await openPicker(page);
	// the verbs stand over a row only while the pointer is on it
	const row = page.locator('[data-testid="session-list"] li.selected');
	await expect(row.locator('[data-testid^="session-close-"]')).toBeHidden();
	await row.hover();
	await row.locator('[data-testid^="session-close-"]').click();
	await expect(page.getByTestId('session-footer-name')).toHaveText('no session selected', { timeout: 10000 });
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

test('a selection records the lines it covers and nothing else', async ({ page }) => {
	// **A phantom rectangle is a wrong anchor, not a cosmetic fault.** A range over the text layer yields a rectangle
	// for every element it crosses, degenerate ones included, and those were mapped to points and recorded. They sat
	// at the layer's top-left, hundreds of points above the words they claimed to be. A text anchor publishes its
	// geometry through the sidecar rather than the log (DR-209), so that is where the drawn rectangles are checked.
	await opened(page);
	await select(page, 'rational polytope');
	await page.getByTestId('note-body').fill('the quads of this note are the lines it covers');
	await page.getByTestId('note-submit').click();
	await expect(page.getByTestId('note-at')).toHaveCount(0, { timeout: 10000 });

	const written = log().filter((e) => String(e.body ?? '').startsWith('the quads of this note')).at(-1)!;
	const id = String(written.id);
	const sidecar = `${QUILT}/build/spans/doi/10.4171_showcase_19-2.json`;
	await expect
		.poll(() => JSON.parse(readFileSync(sidecar, 'utf8')).marks?.[id]?.length ?? 0, { timeout: 15000 })
		.toBeGreaterThan(0);

	const spans = JSON.parse(readFileSync(sidecar, 'utf8'));
	const box = spans.pages[String((written.anchor as { page: number }).page)];
	for (const [x0, y0, x1, y1] of spans.marks[id] as number[][]) {
		expect(x1, `a quad with no width: ${JSON.stringify([x0, y0, x1, y1])}`).toBeGreaterThan(x0);
		expect(y1, `a quad with no height: ${JSON.stringify([x0, y0, x1, y1])}`).toBeGreaterThan(y0);
		expect(x0).toBeGreaterThanOrEqual(-1);
		expect(y0).toBeGreaterThanOrEqual(-1);
		expect(x1).toBeLessThanOrEqual(box.width + 1);
		expect(y1).toBeLessThanOrEqual(box.height + 1);
	}
});

test('the page and the zoom are typed into, and take exactly what was typed', async ({ page }) => {
	// The controls live on the view's one rail rather than in a toolbar of the renderer's own, and both boxes are
	// editable the way a desktop viewer's are: `+` twelve times is not how a reader reaches page 12. Typing over a box
	// is the case that broke -- the field held `140`, the reader typed `150`, and `140150` clamped to the maximum -- so
	// each assertion below is that the value taken is exactly the value typed.
	await opened(page);
	const zoom = page.getByTestId('zoom-at');
	const at = page.getByTestId('page-at');
	await expect(page.getByTestId('page-count')).toContainText('/');

	await zoom.click();
	await page.keyboard.type('150');
	await page.keyboard.press('Enter');
	await expect(zoom).toHaveValue('150%');

	await zoom.click();
	await page.keyboard.type('75');
	await page.keyboard.press('Enter');
	await expect(zoom).toHaveValue('75%');

	// Escape puts back what the view holds rather than committing what was typed
	await zoom.click();
	await page.keyboard.type('300');
	await page.keyboard.press('Escape');
	await expect(zoom).toHaveValue('75%');

	// matching the width is a zoom the reader did not have to name, so the box reports whatever it came to
	await page.getByTestId('zoom-fit').click();
	await expect(page.getByTestId('zoom-fit')).toHaveAttribute('aria-pressed', 'true');
	await expect(zoom).not.toHaveValue('75%');

	// and the page box moves the reader, the count beside it saying how far it can go
	await at.click();
	await page.keyboard.type('1');
	await page.keyboard.press('Enter');
	await expect(at).toHaveValue('1');
});

test('the preview lands on its mark', async ({ page }) => {
	// Owed since plan 0.13.3: a card opened at a result shows that result, not the top of its page. The renderer waits for the mark to exist before scrolling to it, since the card mounts a page that has not drawn yet.
	await page.goto('/master/main-atomic');
	await page.waitForSelector('[data-pane="0"] .fragment mjx-container');
	await page.locator('[data-pane="0"] span.cite[data-citekey="Arden24"] a').first().hover();
	const card = page.getByTestId('link-preview');
	const mark = card.getByTestId('mark-_stmt').first();
	await expect(mark).toBeVisible({ timeout: 10000 });
	await expect
		.poll(() =>
			card.evaluate((c) => {
				const m = c.querySelector('[data-testid="mark-_stmt"]')!.getBoundingClientRect();
				const box = c.querySelector('[data-testid="preview-page"]')!.getBoundingClientRect();
				return m.top >= box.top - 2 && m.top <= box.bottom;
			}),
			{ timeout: 5000 }
		)
		.toBe(true);
});

test('a scroll inside the preview does not dismiss it', async ({ page }) => {
	// Owed since plan 0.13.3: the dismissal listens to every scroll, capturing, so it hears the card's own column scrolling itself to the page it was asked for — which once closed the card in the frame it opened. A scroll outside the card still dismisses it.
	await page.goto('/master/main-atomic');
	await page.waitForSelector('[data-pane="0"] .fragment mjx-container');
	await page.locator('[data-pane="0"] span.cite[data-citekey="Arden24"] a').first().hover();
	const card = page.getByTestId('link-preview');
	await expect(card.getByTestId('mark-_stmt').first()).toBeVisible({ timeout: 10000 });
	// the renderer has scrolled its own column by now; the card stands
	await page.waitForTimeout(800);
	await expect(card).toBeVisible();
	// and a wheel inside the card scrolls the card, not away from it
	await card.hover();
	await page.mouse.wheel(0, 120);
	await page.waitForTimeout(300);
	await expect(card).toBeVisible();
});

test('a mark round a formula leaves the formula typeset', async ({ page }) => {
	// the quote `underlying graph has $c$ connected components` is TeX; its mark takes the formula whole, so MathJax still reads it (phase 4)
	await page.goto('/node/sh-0009');
	const mark = page.locator('[data-pane="0"] .fragment mark.annotation', { hasText: 'underlying graph' }).first();
	await expect(mark.locator('mjx-container')).toHaveCount(1);
	await expect(page.locator('[data-pane="0"] .fragment')).not.toContainText('\\(');
});

test('a document never compiled shows none of another document’s numbers', async ({ page }) => {
	// the talk has no compile of its own: the default document's `Theorem 3.1` would be plausible and wrong there (P3)
	await page.goto('/master/talk');
	await page.locator('[data-pane="0"] .fragment mjx-container').first().waitFor();
	await expect(page.locator('[data-pane="0"] .fragment .env-label .number')).toHaveCount(0);
	await expect(page.getByTestId('cluster')).not.toContainText('not yet numbered');
});

test('a paper opened into half a pane fits its text, and its landing dot is in the pane', async ({ page }) => {
	await page.setViewportSize({ width: 1440, height: 900 });
	await page.goto('/master/main-atomic');
	await page.locator('[data-pane="0"] .fragment mjx-container').first().waitFor();
	await page.locator('[data-pane="0"] a', { hasText: 'Proposition 2.1' }).first().click();
	const lead = page.locator('[data-pane="1"] .mark.on.lead').first();
	await lead.waitFor();
	const paneBox = (await page.getByTestId('pane-1').boundingBox())!;
	// the whole line is inside the pane, with room left of it for the dot, once the smooth scroll to it has settled
	await expect
		.poll(async () => {
			const box = (await lead.boundingBox())!;
			return box.x >= paneBox.x + 8 && box.x + box.width <= paneBox.x + paneBox.width;
		}, { timeout: 8000 })
		.toBe(true);
	// and the reader's own zoom returns the moment they give one
	await page.getByTestId('zoom-at').fill('140');
	await page.getByTestId('zoom-at').press('Enter');
	await expect(page.getByTestId('zoom-at')).toHaveValue('140%');
});

test('a paper drawn again at a new zoom never shows a render refused', async ({ page, context }) => {
	// a page redrawn while its first draw was running told the reader "Cannot use the same canvas during multiple render() operations" (phase 5). The race needs a slow machine to show, so the CPU is slowed and the zoom changed while pages are drawing.
	test.setTimeout(90000);
	const cdp = await context.newCDPSession(page);
	await cdp.send('Emulation.setCPUThrottlingRate', { rate: 8 });
	for (const at of ['/library/Arden24', '/master/main-atomic']) {
		await page.goto(at);
		if (at.startsWith('/master')) {
			await page.locator('[data-pane="0"] .fragment mjx-container').first().waitFor({ timeout: 30000 });
			await page.locator('[data-pane="0"] a', { hasText: 'Proposition 2.1' }).first().click();
		}
		await page.getByTestId('zoom-in').waitFor({ timeout: 30000 });
		await page.evaluate(async () => {
			const b = document.querySelector<HTMLButtonElement>('[data-testid="zoom-in"]');
			for (let k = 0; k < 3; k++) {
				b?.click();
				await new Promise((r) => setTimeout(r, 40));
			}
		});
		await page.waitForTimeout(6000);
		await expect(page.getByText('Cannot use the same canvas')).toHaveCount(0);
		await expect(page.locator('[data-testid="pdf-page-1"] canvas').first()).toBeVisible();
	}
	await cdp.send('Emulation.setCPUThrottlingRate', { rate: 1 });
});
