// Reading a cited work under `loom serve` (plan 0.13 §11): the things the fixture-only suite cannot check because they need the publisher — a selection mapped onto the committed page text and recorded, a box recorded as drawn, the marks the sidecar then carries, and a locator lit from a link.
//
// A test that writes (`test`) is served on its own copy of the showcase, and one that only reads (`readOnly`) on its worker's; a test that needs a note to exist writes it first through the API.
import { expect, readOnly, test, type Served } from '../served';
import type { Page } from '@playwright/test';
import { openPicker, pickSession } from '../picker';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const PAGE2 = '/library/Bellamy19?page=2';

/** Bellamy19 as the served copy's manifest has it: its work id, where its pages are filed, and its sidecar. */
function bellamy(served: Served): { work: string; artifacts: { dir: string }; spans: { path: string } } {
	return JSON.parse(readFileSync(join(served.root, 'build/manifest.json'), 'utf8')).references.Bellamy19;
}

/** Open page 2 with a session chosen, and wait until the paper has been drawn again for the narrower pane; returns the session. */
async function opened(page: Page, served: Served): Promise<string> {
	await page.goto(PAGE2);
	await page.locator('[data-testid="pdf-page-2"] canvas').waitFor();
	const session = await intoASession(page, served);
	// choosing a session opens its Chat beside, which narrows the paper's pane and draws its pages again at the zoom that fits; a selection made while the text layer is being replaced would be lost with it
	await expect(page.locator('[data-pane="1"]').getByTestId('chat')).toBeVisible();
	await drawn(page, 2);
	return session;
}

/** The text layer page `n` holds now, numbered in the order this page first saw each layer; 0 before it has one. A redraw replaces the layer, so a new number is a new draw. */
async function layerOf(page: Page, n: number): Promise<{ width: number; spans: number; layer: number }> {
	return page.getByTestId(`pdf-page-${n}`).evaluate((el) => {
		const w = window as unknown as { __layers?: WeakMap<Element, number>; __layerCount?: number };
		w.__layers ??= new WeakMap();
		const all = el.querySelectorAll('.text span');
		const first = all[0];
		if (first && !w.__layers.has(first)) w.__layers.set(first, (w.__layerCount = (w.__layerCount ?? 0) + 1));
		return { width: Math.round(el.getBoundingClientRect().width), spans: all.length, layer: first ? w.__layers.get(first)! : 0 };
	});
}

/**
 * Wait until page `n` is drawn and holding still: the same width and the same text layer, with more than 50 spans of text and newer than `after`, on two reads `every` ms apart; returns that layer.
 *
 * Fails showing the last state read.
 */
async function drawn(page: Page, n: number, { every = 300, after = 0 } = {}): Promise<number> {
	let last = '';
	let layer = 0;
	await expect
		.poll(
			async () => {
				const now = await layerOf(page, n);
				const said = `width ${now.width}, ${now.spans} spans, text layer #${now.layer}`;
				const held = said === last && now.width > 0 && now.spans > 50 && now.layer > after;
				last = said;
				layer = now.layer;
				return held ? 'held' : said;
			},
			{ intervals: [every], timeout: 30000 }
		)
		.toBe('held');
	return layer;
}

/**
 * Choose where the notes will be filed: the showcase's newest open session, read from the copy's session index.
 *
 * A write names its session and nothing is selected at rest (plan 0.13.1), so this is the first thing a reader does before annotating — and therefore the first thing these tests do.
 */
async function intoASession(page: Page, served: Served): Promise<string> {
	const id = served.openSessions().at(-1)!;
	await pickSession(page, id);
	await expect(page.getByTestId('session-footer')).toHaveAttribute('aria-label', /^annotations are written into/);
	return id;
}

/** A person's note on page 2 of Bellamy19 over `phrase`, written through the API into `session`; returns its id. */
async function noteOnPage2(served: Served, session: string, phrase: string, body: string): Promise<string> {
	const result = await served.api('comment', { target: 'Bellamy19', page: 2, quote: phrase, message: body, kind: 'note', session });
	return result.split(/\s+/)[0];
}

/**
 * Select a phrase and ask to annotate it, the way a reader does.
 *
 * Selecting no longer opens the composer by itself: the selection stays live so it can be copied, and an *annotate* chip offers the other thing. Both halves are exercised here, because a test that reached the composer without the chip would not notice the chip disappearing.
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

test('a selection stays selected and only offers to annotate; a note written from it shows loom’s own words before anything is recorded', async ({ page, served }) => {
	await opened(page, served);
	// highlighting a phrase to copy it is the ordinary thing to do with a paper, so selecting opens nothing: the selection survives, and the chip is the way to the composer
	await selectOnly(page, 'incidence matrix');
	await expect(page.getByTestId('note-at')).toHaveCount(0);
	expect(await page.evaluate(() => window.getSelection()?.toString() ?? '')).toContain('incidence matrix');
	await expect(page.getByTestId('annotate-offer')).toBeVisible();
	await page.getByTestId('annotate-offer').click();
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
	const written = served.written('So the vertices are integral.');
	expect(written.target).toBe(bellamy(served).work);
	const anchor = written.anchor as Record<string, unknown>;
	expect(anchor.basis).toBe('text');
	expect(anchor.page).toBe(2);
	expect(String(anchor.exact)).toContain('incidence matrix');
	expect(anchor).not.toHaveProperty('quads'); // derived at build time, never recorded for text
	// and the mark appears once the publisher has rebuilt the sidecar
	await expect(page.getByTestId(`mark-${written.id}`)).toBeVisible({ timeout: 15000 });
	await expect(page.getByTestId(`mark-${written.id}`)).toHaveClass(/k-note/);
});

test('a selection across a citation and a reference is quoted as they were written, and anchors', async ({ page, served }) => {
	// the 0.14 study (F5): the rendered `[2, Theorem 3.2]` shares no text with `\cite[Theorem 3.2]{Bellamy19}`, and the page prints `Ehrhart’s` for `Ehrhart's`, so a selection across either was "quote not found" and only a note on the whole proof was offered
	await page.goto('/node/sh-000C');
	await intoASession(page, served);
	const para = page.locator('[data-pane="0"] .fragment details p').filter({ hasText: 'Ehrhart' }).first();
	await expect(para.locator('mjx-container').first()).toBeAttached();
	await para.evaluate((node) => {
		const range = document.createRange();
		range.selectNodeContents(node);
		const sel = window.getSelection();
		sel?.removeAllRanges();
		sel?.addRange(range);
		node.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
	});
	await page.getByTestId('annotate-offer').click();
	await page.getByTestId('note-body').fill('Which digraph is this the median polytope of?');
	await page.getByTestId('note-kind').selectOption('question');
	await page.getByTestId('note-submit').click();
	await expect(page.getByTestId('note-at')).toBeHidden();
	const written = served.written('Which digraph is this the median polytope of?');
	expect(written.target).toBe('sh-000C/proof');
	const quote = String((written.anchor as Record<string, unknown>).exact);
	expect(quote).toContain('\\cite[Theorem 3.2]{Bellamy19}');
	expect(quote).toContain('\\ref{sh-0009}');
	// and the note is anchored where it was written, not merely accepted (WQ-48 is a note that was accepted and not)
	await expect
		.poll(async () => {
			const m = await (await page.request.get('/build/manifest.json')).json();
			const a = m.annotations[written.id as string];
			return a ? `${a.recorded} ${a.anchored}` : 'absent';
		}, { timeout: 15000 })
		.toBe('true true');
});

test('a box is recorded as drawn, and the words under it are its hint', async ({ page, served }) => {
	await opened(page, served);
	await page.getByTestId('tool-box').click();
	await expect(page.locator('[data-testid="pdf-page-2"].boxing')).toBeVisible(); // the tool has taken
	const canvas = page.locator('[data-testid="pdf-page-2"] canvas');
	// the column, not the window: the page's top at the top of the reader, so the display a third of the way down is in view
	await canvas.evaluate((c) => c.scrollIntoView({ block: 'start' }));
	// the pages either side report their sizes just after the first draw, which moves page 2 under a box measured too early: wait until its position holds still before drawing on it
	let box = (await canvas.boundingBox())!;
	await expect
		.poll(async () => {
			const again = (await canvas.boundingBox())!;
			const same = Math.abs(again.y - box.y) < 1 && Math.abs(again.height - box.height) < 1;
			box = again;
			return same ? 'held' : `moved to y ${again.y}, height ${again.height}`;
		}, { intervals: [300, 300, 300, 300], timeout: 5000 })
		.toBe('held');
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
	const written = served.written('This is the display I want to cite.');
	const anchor = written.anchor as Record<string, unknown>;
	expect(anchor.basis).toBe('box');
	expect(anchor.quads).toHaveLength(1);
	await expect(page.getByTestId(`mark-${written.id}`)).toBeVisible({ timeout: 15000 });
});

test('a mark opens the box a fragment opens, Escape closes it, and the note waits in the Chat for the next message', async ({ page, served }) => {
	// a person's note in the session the page is opened in, written before the page is
	const id = await noteOnPage2(served, served.openSessions().at(-1)!, 'incidence matrix', 'a note to open from its mark');
	await opened(page, served);
	const mark = page.getByTestId(`mark-${id}`);
	await expect(mark).toBeVisible();
	await mark.click();
	const open = page.getByTestId('comment-expanded');
	await expect(open).toBeVisible();
	await expect(open.locator('article.box').first()).toBeVisible();
	await page.keyboard.press('Escape');
	await expect(open).toHaveCount(0);
	// beside it, the session it was written in, whose Chat choosing it opened: a person's note goes to the agent with the next message (plan 0.14)
	await expect(page.getByTestId(`packet-row-${id}`)).toBeVisible();
	// what the session did is the log of what was done through loom's commands, which a note written here is not: its mark has nowhere to travel, and says so
	await mark.dblclick();
	await expect(page.getByTestId('travel-nowhere')).toBeVisible();
});

test('inline is never offered on a page, and a note opens floating', async ({ page, served }) => {
	// A PDF page cannot reflow, so there is nowhere for an inline box to go.
	const id = await noteOnPage2(served, served.openSessions().at(-1)!, 'incidence matrix', 'a note placed inline by preference');
	await page.addInitScript(() => localStorage.setItem('arras.prefs', JSON.stringify({ comments: 'inline' })));
	await opened(page, served);
	await page.getByTestId(`mark-${id}`).click();
	await expect(page.getByTestId('comment-expanded')).toHaveClass(/floating/);
});

test('the session selection governs the page: a hidden note is counted, not drawn', async ({ page, served }) => {
	const id = await noteOnPage2(served, served.openSessions().at(-1)!, 'incidence matrix', 'a note the empty session hides');
	await opened(page, served);
	await expect(page.getByTestId(`mark-${id}`)).toBeVisible();
	const before = await page.locator('[data-testid="pdf-page-2"] .mark.note').count();
	// a fresh session, empty, made the active one; showing only it hides the note written above
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
	// `all` still hides the showcase's own notes, which sit in a closed session; what changes is that the one written above comes back, so the count drops rather than vanishes
	await expect(page.locator('[data-testid="pdf-page-2"] .mark.note')).toHaveCount(before);
	const hiddenUnderAll = Number((await page.getByTestId('reading-hidden').textContent())!.match(/\d+/)![0]);
	expect(hiddenUnderAll).toBeLessThan(hiddenUnderThis);
});

test('a locator in the URL is lit while the URL carries it, and a note is focused by its id', async ({ page, served }) => {
	// a note by id: one written here, since the showcase's own are in a closed session and closed sessions' annotations are hidden until shown
	const id = await noteOnPage2(served, served.openSessions().at(-1)!, 'incidence matrix', 'a note to focus by its id');
	await opened(page, served);
	const pageText = readFileSync(join(served.root, bellamy(served).artifacts.dir, 'pages/0002.txt'), 'utf8');
	const a = pageText.indexOf('totally unimodular');
	await page.goto(`${PAGE2}&span=${a}-${a + 'totally unimodular'.length}`);
	const lit = page.locator('[data-testid="pdf-page-2"] .mark.transient');
	await expect(lit).toBeVisible();
	await expect(lit).toHaveClass(/on/); // and it is the one in focus
	await page.goto(`${PAGE2}&annot=${id}`);
	await expect(page.getByTestId(`mark-${id}`)).toHaveClass(/on/);
	// and it arrives open: a link to a note is a link to what it says (plan 0.14)
	await expect(page.getByTestId('comment-expanded').locator(`[data-annotation-id="${id}"]`)).toBeVisible();
});

test('a session is named on the spot and closed from the page', async ({ page, served }) => {
	await opened(page, served);
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

test('two notes on one place are one mark carrying the count, and one box holding both', async ({ page, served }) => {
	await opened(page, served);
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

test('a box shows the write it fired, without being closed and reopened', async ({ page, served }) => {
	// `openAt` mounted the card with the annotation as it was and nothing updated it, so resolving from a box left the
	// box saying `open` with the same verbs. In the study the reader clicked twice for that reason and the append-only
	// log took two `resolved` events for one annotation.
	await opened(page, served);
	// a phrase no note in the showcase is on: a stacked mark carries the first id rather than the newest
	await select(page, 'exchange inequalities');
	await expect(page.getByTestId('note-at')).toBeVisible();
	await page.getByTestId('note-body').fill('resolve me');
	await page.getByTestId('note-submit').click();
	await expect(page.getByTestId('note-at')).toBeHidden();
	const id = served.written('resolve me').id as string;
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

test('a selection records the lines it covers and nothing else', async ({ page, served }) => {
	// **A phantom rectangle is a wrong anchor, not a cosmetic fault.** A range over the text layer yields a rectangle for every element it crosses, degenerate ones included, and those were mapped to points and recorded. They sat at the layer's top-left, hundreds of points above the words they claimed to be. A text anchor publishes its geometry through the sidecar rather than the log (DR-209), so that is where the drawn rectangles are checked.
	await opened(page, served);
	await select(page, 'rational polytope');
	await page.getByTestId('note-body').fill('the quads of this note are the lines it covers');
	await page.getByTestId('note-submit').click();
	await expect(page.getByTestId('note-at')).toHaveCount(0, { timeout: 10000 });

	const written = served.written('the quads of this note are the lines it covers');
	const id = String(written.id);
	const sidecar = join(served.root, 'build', bellamy(served).spans.path);
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

readOnly('the page and the zoom are typed into, and take exactly what was typed', async ({ page, served }) => {
	// The controls live on the view's one rail rather than in a toolbar of the renderer's own, and both boxes are editable the way a desktop viewer's are: `+` twelve times is not how a reader reaches page 12. Typing over a box is the case that broke -- the field held `140`, the reader typed `150`, and `140150` clamped to the maximum -- so each assertion below is that the value taken is exactly the value typed.
	await opened(page, served);
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

/** How far the top of a preview card's mark lies outside the preview page's box, above or below; 0 or less is inside. */
function markOutsidePreview(c: Element): number {
	const m = c.querySelector('[data-testid="mark-_stmt"]')!.getBoundingClientRect();
	const box = c.querySelector('[data-testid="preview-page"]')!.getBoundingClientRect();
	return Math.max(box.top - m.top, m.top - box.bottom - 2);
}

readOnly('the preview lands on its mark, and a scroll inside it does not dismiss it', async ({ page }) => {
	// A card opened at a result shows that result, not the top of its page: the renderer waits for the mark to exist before scrolling to it, since the card mounts a page that has not drawn yet. The dismissal listens to every scroll, capturing, so it hears the card's own column scrolling itself there, and must let the card stand; a scroll outside the card still dismisses it.
	await page.goto('/master/main-atomic');
	await page.waitForSelector('[data-pane="0"] .fragment mjx-container');
	// every scroll inside a card, heard the way the dismissal hears it and after it: capturing, on the window
	await page.evaluate(() => {
		const w = window as unknown as { __cardScrolls: number };
		w.__cardScrolls = 0;
		window.addEventListener('scroll', (e) => (e.target as Element).closest?.('[data-testid="link-preview"]') && w.__cardScrolls++, { capture: true, passive: true });
	});
	const cardScrolls = () => page.evaluate(() => (window as unknown as { __cardScrolls: number }).__cardScrolls);
	await page.locator('[data-pane="0"] span.cite[data-citekey="Arden24"] a').first().hover();
	const card = page.getByTestId('link-preview');
	await expect(card.getByTestId('mark-_stmt').first()).toBeVisible({ timeout: 10000 });
	// the renderer has scrolled its own column to the mark, so the mark is inside the preview's page, and the dismissal has heard it: the card stands
	await expect.poll(() => card.evaluate(markOutsidePreview), { timeout: 5000 }).toBeLessThanOrEqual(2);
	await expect.poll(cardScrolls).toBeGreaterThan(0);
	await expect(card).toBeVisible();
	// and a wheel inside the card scrolls the card, not away from it: once that scroll has been heard, the card still stands
	const heard = await cardScrolls();
	await card.hover();
	await page.mouse.wheel(0, 120);
	await expect.poll(cardScrolls).toBeGreaterThan(heard);
	await expect(card).toBeVisible();
});

readOnly('a mark round a formula leaves the formula typeset', async ({ page }) => {
	// the quote `underlying graph has $c$ connected components` is TeX; its mark takes the formula whole, so MathJax still reads it (phase 4)
	await page.goto('/node/sh-0009');
	const mark = page.locator('[data-pane="0"] .fragment mark.annotation', { hasText: 'underlying graph' }).first();
	await expect(mark.locator('mjx-container')).toHaveCount(1);
	await expect(page.locator('[data-pane="0"] .fragment')).not.toContainText('\\(');
});

readOnly('a document never compiled shows none of another document’s numbers', async ({ page }) => {
	// the talk has no compile of its own: the default document's `Theorem 3.1` would be plausible and wrong there (P3)
	await page.goto('/master/talk');
	await page.locator('[data-pane="0"] .fragment mjx-container').first().waitFor();
	await expect(page.locator('[data-pane="0"] .fragment .env-label .number')).toHaveCount(0);
	await expect(page.getByTestId('cluster')).not.toContainText('not yet numbered');
});

readOnly('a paper opened into half a pane fits its text, and its landing dot is in the pane', async ({ page }) => {
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
			const roomLeft = box.x - paneBox.x;
			const pastRight = box.x + box.width - (paneBox.x + paneBox.width);
			return roomLeft >= 8 && pastRight <= 0 ? 'inside' : `starts ${roomLeft}px into the pane, ends ${pastRight}px past its right edge`;
		}, { timeout: 8000 })
		.toBe('inside');
	// and the reader's own zoom returns the moment they give one
	await page.getByTestId('zoom-at').fill('140');
	await page.getByTestId('zoom-at').press('Enter');
	await expect(page.getByTestId('zoom-at')).toHaveValue('140%');
});

readOnly('a result that starts mid-line lands with every line of it in half a pane', async ({ page }) => {
	// the 0.14 study: landing scrolled to the first word of `Theorem 3.2.`'s statement, past the margin its other lines start at, so every line but the first lost its opening words
	await page.setViewportSize({ width: 1440, height: 900 });
	await page.goto('/library/Bellamy19?page=2&result=Bellamy19-thm-3.2&beside=%2Fnode%2Fsh-0009');
	const lines = page.locator('[data-pane="0"] [data-mark="Bellamy19-thm-3.2"]');
	await expect(lines).toHaveCount(4, { timeout: 10000 });
	const pane = (await page.getByTestId('pane-0').boundingBox())!;
	// polled, since the scroll to the result is smooth: the lines that stick out of the pane, until none do
	await expect
		.poll(async () => {
			const out: string[] = [];
			for (const [i, line] of (await lines.all()).entries()) {
				const box = (await line.boundingBox())!;
				if (box.x < pane.x || box.x + box.width > pane.x + pane.width) out.push(`line ${i + 1} spans ${box.x}..${box.x + box.width}, the pane ${pane.x}..${pane.x + pane.width}`);
			}
			return out;
		})
		.toEqual([]);
});

readOnly('a paper drawn again at a new zoom never shows a render refused', async ({ page, context }) => {
	// a page redrawn while its first draw was running told the reader "Cannot use the same canvas during multiple render() operations" (phase 5). The race needs a slow machine to show, so the CPU is slowed and the zoom changed while pages are drawing.
	readOnly.setTimeout(90000);
	const cdp = await context.newCDPSession(page);
	await cdp.send('Emulation.setCPUThrottlingRate', { rate: 8 });
	for (const at of ['/library/Arden24', '/master/main-atomic']) {
		await page.goto(at);
		if (at.startsWith('/master')) {
			await page.locator('[data-pane="0"] .fragment mjx-container').first().waitFor({ timeout: 30000 });
			await page.locator('[data-pane="0"] a', { hasText: 'Proposition 2.1' }).first().click();
		}
		await page.getByTestId('zoom-in').waitFor({ timeout: 30000 });
		const before = (await layerOf(page, 1)).layer;
		await page.evaluate(async () => {
			const b = document.querySelector<HTMLButtonElement>('[data-testid="zoom-in"]');
			for (let k = 0; k < 3; k++) {
				b?.click();
				await new Promise((r) => setTimeout(r, 40));
			}
		});
		// the draws the clicks set off have run out: page 1 holds a layer drawn after them, unchanged for a second of the slowed clock
		await drawn(page, 1, { every: 1000, after: before });
		await expect(page.getByText('Cannot use the same canvas')).toHaveCount(0);
		await expect(page.locator('[data-testid="pdf-page-1"] canvas').first()).toBeVisible();
	}
	await cdp.send('Emulation.setCPUThrottlingRate', { rate: 1 });
});
