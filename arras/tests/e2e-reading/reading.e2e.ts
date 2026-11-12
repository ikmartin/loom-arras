// Reading a cited work under `loom serve` (plan 0.13 §11): the things the fixture-only suite cannot check because they need the publisher — a selection mapped onto the committed page text and recorded, a box recorded as drawn, the marks the sidecar then carries, and a locator lit from a link.
//
// A test that writes (`test`) is served on its own copy of the showcase, and one that only reads (`readOnly`) on its worker's; a test that needs a note to exist writes it first through the API.
import { expect, readOnly, test, type Served } from '../served';
import type { Page } from '@playwright/test';
import { openPicker, pickSession } from '../picker';
import { mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const PAGE2 = '/library/Bellamy19?page=2';

/** Bellamy19 as the served copy's manifest has it: its work id, where its pages are filed, and its sidecar. */
function bellamy(served: Served): { work: string; artifacts: { dir: string }; spans: { path: string } } {
	return JSON.parse(readFileSync(join(served.root, '.loom/build/manifest.json'), 'utf8')).references.Bellamy19;
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
			{ intervals: [every] }
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
	const result = await served.api('annotate', { target: 'Bellamy19', page: 2, quote: phrase, message: body, kind: 'note', session });
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

/** The selection alone, for a test about what selecting does on its own. The phrase is scrolled into view first, as one a reader selects is: the chip is hidden while the selection's end is out of its pane's view. */
async function selectOnly(page: Page, phrase: string): Promise<void> {
	const span = page.locator(`[data-testid="pdf-page-2"] .text span:has-text("${phrase}")`).first();
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

test('a selection stays selected and only offers to annotate; a note written from it shows loom’s own words before anything is recorded', async ({ page, served }) => {
	await opened(page, served);
	// highlighting a phrase to copy it is the ordinary thing to do with a paper, so selecting opens nothing: the selection survives, and the chip is the way to the composer
	await selectOnly(page, 'incidence matrix');
	await expect(page.getByTestId('note-at')).toHaveCount(0);
	expect(await page.evaluate(() => window.getSelection()?.toString() ?? '')).toContain('incidence matrix');
	await expect(page.getByTestId('annotate-offer')).toBeVisible();
	// the one chip every surface has: the annotation neutral, after the selection's last line
	await expect(page.getByTestId('annotate-offer')).toHaveCSS('color', 'rgb(111, 109, 102)');
	await page.getByTestId('annotate-offer').click();
	const form = page.getByTestId('note-at');
	await expect(form).toBeVisible();
	// the header names the page and the words, never the work's key; beneath it, what loom found on the page in its own words, before anything is typed
	await expect(page.getByTestId('note-where')).toContainText('on p. 2,');
	await expect(page.getByTestId('note-where')).toContainText('incidence matrix');
	await expect(page.getByTestId('note-where')).not.toContainText(bellamy(served).work);
	await expect(page.getByTestId('note-located')).toContainText('anchored by text');
	// the composer is a comment box and nothing else: the words stay lit on the page instead of being quoted in it
	await expect(page.getByTestId('note-quote')).toHaveCount(0);
	await expect.poll(() => page.evaluate(() => [...((CSS as unknown as { highlights: Map<string, { values(): Iterable<Range> }> }).highlights.get('note-pending')?.values() ?? [])].map((r) => r.toString()).join(' '))).toContain('incidence matrix');
	await page.getByTestId('note-body').fill('So the vertices are integral.');
	await expect(page.getByTestId('note-kind').locator('[aria-pressed="true"]')).toHaveAttribute('data-kind', 'note');
	await page.getByTestId('note-submit').click();
	await expect(form).toBeHidden();
	const written = served.written('So the vertices are integral.');
	expect(written.target).toBe(bellamy(served).work);
	const anchor = written.anchor as Record<string, unknown>;
	expect(anchor.basis).toBe('text');
	expect(anchor.page).toBe(2);
	expect(String(anchor.exact)).toContain('incidence matrix');
	expect(anchor).not.toHaveProperty('quads'); // derived at build time, never recorded for text
	// and the mark appears once the publisher has rebuilt the sidecar: the underline a fragment draws, beneath each line, over the hue's 5% wash
	const mark = page.getByTestId(`mark-${written.id}`).first();
	await expect(mark).toBeVisible();
	await expect(mark).toHaveClass(/annotation/);
	await expect(mark).toHaveClass(/k-note/);
	expect(await mark.evaluate((el) => getComputedStyle(el).backgroundColor)).toMatch(/[ /,] ?0\.05\)$/);
	await expect(mark).toHaveCSS('border-bottom-width', '2px');
	await expect(mark).toHaveCSS('border-bottom-color', 'rgb(111, 109, 102)');
	await expect(mark).toHaveCSS('border-top-width', '0px');
});

test('Enter on a selection opens the composer, as the chip does', async ({ page, served }) => {
	await opened(page, served);
	await selectOnly(page, 'incidence matrix');
	await expect(page.getByTestId('annotate-offer')).toBeVisible();
	await page.keyboard.press('Enter');
	await expect(page.getByTestId('note-at')).toBeVisible();
	await expect(page.getByTestId('annotate-offer')).toHaveCount(0);
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
	await page.getByTestId('note-kind').locator('[data-kind="question"]').click();
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
		})
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
		}, { intervals: [300, 300, 300, 300] })
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
	await expect(page.getByTestId('note-where')).toHaveText('on p. 2, a box');
	await expect(page.getByTestId('note-located')).toContainText('anchored by box');
	await page.getByTestId('note-body').fill('This is the display I want to cite.');
	await page.getByTestId('note-submit').click();
	await expect(page.getByTestId('note-at')).toBeHidden();
	const written = served.written('This is the display I want to cite.');
	const anchor = written.anchor as Record<string, unknown>;
	expect(anchor.basis).toBe('box');
	expect(anchor.quads).toHaveLength(1);
	// a box anchor is an outline in the hue, not an underline
	const mark = page.getByTestId(`mark-${written.id}`);
	await expect(mark).toBeVisible();
	await expect(mark).toHaveClass(/basis-box/);
	await expect(mark).toHaveCSS('border-top-width', '2px');
	await expect(mark).toHaveCSS('border-top-color', 'rgb(111, 109, 102)');
	expect(await mark.evaluate((el) => getComputedStyle(el).backgroundColor)).toMatch(/[ /,] ?0\.05\)$/);
});

test('a mark opens the box a fragment opens, Escape closes it, and its mark has nowhere to travel', async ({ page, served }) => {
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

test('the session selection governs the page: a note the view hides is not drawn, and nothing says so', async ({ page, served }) => {
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
	await expect(page.getByTestId('session-footer-name')).toContainText('an empty sitting');
	await openPicker(page);
	await page.getByTestId('show-current').click();
	await expect(page.getByTestId(`mark-${id}`)).toHaveCount(0);
	expect(await page.locator('[data-testid="pdf-page-2"] .mark.note').count()).toBeLessThan(before);
	// a hidden mark needs no notice: the scope is the picker's, said in a word in the footer, and the page draws what it admits
	await expect(page.getByTestId('reading-hidden')).toHaveCount(0);
	await expect(page.getByTestId('session-footer-scope')).toHaveText('· this session');
	await page.getByTestId('show-all').click();
	// `all` still hides the showcase's own notes, which sit in a closed session; what changes is that the one written above comes back
	await expect(page.locator('[data-testid="pdf-page-2"] .mark.note')).toHaveCount(before);
	await expect(page.getByTestId(`mark-${id}`)).toBeVisible();
});

test('a locator in the URL is lit while the URL carries it, and a note is focused by its id', async ({ page, served }) => {
	// a note by id: one written here, since the showcase's own are in a closed session and closed sessions' annotations are hidden until shown
	const id = await noteOnPage2(served, served.openSessions().at(-1)!, 'incidence matrix', 'a note to focus by its id');
	await opened(page, served);
	const pageText = readFileSync(join(served.root, '.loom', bellamy(served).artifacts.dir, 'pages/0002.txt'), 'utf8') // `artifacts.dir` is the store's address, digests/storage/…, which loom keeps under .loom/;
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
	await expect(page.getByTestId('session-footer-name')).toContainText('reading Bellamy, closely');
	// closing the selected session clears the selection, so writing is unavailable until another is chosen
	await openPicker(page);
	// the verbs stand over a row only while the pointer is on it
	const row = page.locator('[data-testid="session-list"] li.selected');
	await expect(row.locator('[data-testid^="session-close-"]')).toBeHidden();
	await row.hover();
	await row.locator('[data-testid^="session-close-"]').click();
	await expect(page.getByTestId('session-footer-lead')).toHaveText('not writing in a session');
});

test('two notes on one place are one mark with no count drawn, and one box holding both', async ({ page, served }) => {
	await opened(page, served);
	for (const body of ['first on this phrase', 'second on this phrase']) {
		await select(page, 'Boundedness holds');
		await expect(page.getByTestId('note-at')).toBeVisible();
		await page.getByTestId('note-body').fill(body);
		await page.getByTestId('note-submit').click();
		await expect(page.getByTestId('note-at')).toBeHidden();
	}
	// one mark carries both ids; nothing is drawn to say how many
	const stacked = page.locator('[data-testid="pdf-page-2"] .mark.note[data-annotation*=" "]').first();
	await expect(stacked).toBeVisible();
	await expect(stacked).not.toHaveAttribute('data-count');
	expect(await stacked.evaluate((el) => getComputedStyle(el, '::after').content)).toBe('none');
	const ids = (await stacked.getAttribute('data-annotation'))!.split(/\s+/);
	expect(ids.length).toBeGreaterThanOrEqual(2);
	await stacked.click();
	await expect(page.getByTestId('comment-expanded').locator('article.box')).toHaveCount(ids.length);
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
	await expect(mark).toBeVisible();
	await mark.click();
	const box = page.getByTestId('comment-expanded');
	await expect(box.getByTestId('outcome')).toHaveCount(0);
	await box.getByTestId('verb-resolve').first().click();
	// the same box, still open, still where the reader put it, now settled: the outcome said once, and reopen its one verb
	await expect(box.getByTestId('outcome').first()).toHaveText('· resolved');
	await expect(box.locator('article.box').first()).toHaveClass(/settled/);
	await expect(box.getByTestId('verb-resolve')).toHaveCount(0);
	const undo = box.getByTestId('verb-reopen').first();
	await undo.click();
	await expect(box.getByTestId('outcome')).toHaveCount(0);
});

test('a selection records the lines it covers and nothing else', async ({ page, served }) => {
	// **A phantom rectangle is a wrong anchor, not a cosmetic fault.** A range over the text layer yields a rectangle for every element it crosses, degenerate ones included, and those were mapped to points and recorded. They sat at the layer's top-left, hundreds of points above the words they claimed to be. A text anchor publishes its geometry through the sidecar rather than the log (DR-209), so that is where the drawn rectangles are checked.
	await opened(page, served);
	await select(page, 'rational polytope');
	await page.getByTestId('note-body').fill('the quads of this note are the lines it covers');
	await page.getByTestId('note-submit').click();
	await expect(page.getByTestId('note-at')).toHaveCount(0);

	const written = served.written('the quads of this note are the lines it covers');
	const id = String(written.id);
	const sidecar = join(served.root, '.loom/build', bellamy(served).spans.path);
	await expect
		.poll(() => JSON.parse(readFileSync(sidecar, 'utf8')).marks?.[id]?.length ?? 0)
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
	// The controls live on the pane's toolbar rather than in a toolbar of the renderer's own, and both boxes are editable the way a desktop viewer's are: `+` twelve times is not how a reader reaches page 12. Typing over a box is the case that broke -- the field held `140`, the reader typed `150`, and `140150` clamped to the maximum -- so each assertion below is that the value taken is exactly the value typed.
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
	// a card drawing its page again holds neither for a moment, which is not yet, not outside
	const mark = c.querySelector('[data-testid="mark-_stmt"]');
	const page = c.querySelector('[data-testid="preview-page"]');
	if (!mark || !page) return Number.POSITIVE_INFINITY;
	const m = mark.getBoundingClientRect();
	const box = page.getBoundingClientRect();
	return Math.max(box.top - m.top, m.top - box.bottom - 2);
}

readOnly('the preview lands on its mark, and a scroll inside it does not dismiss it', async ({ page }) => {
	// A card opened at a result shows that result, not the top of its page: the renderer waits for the mark to exist before scrolling to it, since the card mounts a page that has not drawn yet. The dismissal listens to every scroll, capturing, so it hears the card's own column scrolling itself there, and must let the card stand; a scroll outside the card still dismisses it.
	await page.goto('/master/drafting/main-atomic');
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
	await expect(card.getByTestId('mark-_stmt').first()).toBeVisible();
	// the renderer has scrolled its own column to the mark, so the mark is inside the preview's page, and the dismissal has heard it: the card stands
	await expect.poll(() => card.evaluate(markOutsidePreview)).toBeLessThanOrEqual(2);
	await expect.poll(cardScrolls).toBeGreaterThan(0);
	await expect(card).toBeVisible();
	// and a wheel inside the card scrolls the card, not away from it: once that scroll has been heard, the card still stands
	const heard = await cardScrolls();
	await card.hover();
	await page.mouse.wheel(0, 120);
	await expect.poll(cardScrolls).toBeGreaterThan(heard);
	await expect(card).toBeVisible();
});

readOnly('a citation opens its paper at the result, past the first page, and a \\ref to a result goes where its citation goes', async ({ page }) => {
	// `Theorem 5.1` is read off Arden24's revision, Arden24A, on its third page: the introduction's citation of it opens that document there, with the result in view
	await page.goto('/node/sh-0100');
	const cite = page.locator('[data-pane="0"] span.cite[data-target="Arden24A-thm-5.1"] a').first();
	await expect(cite).toHaveAttribute('href', '/library/Arden24A?page=3&result=Arden24A-thm-5.1');
	await cite.click();
	await expect(page.locator('[data-pane="1"] [data-mark="Arden24A-thm-5.1"]').first()).toBeInViewport();
	await expect(page.getByTestId('pane-1').getByTestId('page-at')).toHaveValue('3');
	// a remark of the revision refers to its Corollary 5.2 by `\ref`, which opens the paper at that result too
	await page.goto('/node/Arden24A-rem-5.3');
	await expect(page.locator('[data-pane="0"] a.ref[data-target="Arden24A-cor-5.2"]').first()).toHaveAttribute('href', '/library/Arden24A?page=3&result=Arden24A-cor-5.2');
	// and the work and its revision are one row of the column's Library
	await page.getByTestId('library-toggle').click();
	await expect(page.getByTestId('library-list').locator('a[data-testid^="library-work-Arden24"]')).toHaveCount(1);
});

readOnly('a link that quotes a work without a page is lit on the page the publisher finds it on', async ({ page }) => {
	await page.goto('/library/Bellamy19?quote=' + encodeURIComponent('The median orders of a weighted digraph are in bijection with the vertices'));
	await expect(page.locator('[data-mark="_locator"]').first()).toBeInViewport();
	await expect(page.getByTestId('page-at')).toHaveValue('2');
});

readOnly('a mark round a formula leaves the formula typeset', async ({ page }) => {
	// the quote `underlying graph has $c$ connected components` is TeX; its mark takes the formula whole, so MathJax still reads it (phase 4)
	await page.goto('/node/sh-0009');
	const mark = page.locator('[data-pane="0"] .fragment mark.annotation', { hasText: 'underlying graph' }).first();
	await expect(mark.locator('mjx-container')).toHaveCount(1);
	await expect(page.locator('[data-pane="0"] .fragment')).not.toContainText('\\(');
});

test.describe('a document never compiled', () => {
	// the talk's compile taken away, so it has none of its own: the default document's `Theorem 3.1` would be plausible and wrong there (V3)
	test.use({
		prepareQuilt: async ({}, use) => {
			await use(({ root }) => rmSync(join(root, '.loom', 'build', 'drafting', 'talk'), { recursive: true, force: true }));
		}
	});

	test('shows its source, and none of another document’s numbers', async ({ page }) => {
		await page.goto('/master/drafting/talk');
		await page.locator('[data-pane="0"] .fragment pre.source').first().waitFor();
		await expect(page.locator('[data-pane="0"] .fragment .env-label').first()).toBeVisible();
		await expect(page.locator('[data-pane="0"] .fragment .env-label .number')).toHaveCount(0);
		await expect(page.getByTestId('item-controls')).not.toContainText('not yet numbered');
	});
});

readOnly('a paper opened into half a pane fits its text, and its landing dot is in the pane', async ({ page }) => {
	await page.setViewportSize({ width: 1440, height: 900 });
	await page.goto('/master/drafting/main-atomic');
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
		})
		.toBe('inside');
	// and the reader's own zoom returns the moment they give one
	await page.getByTestId('zoom-at').fill('140');
	await page.getByTestId('zoom-at').press('Enter');
	await expect(page.getByTestId('zoom-at')).toHaveValue('140%');
});

readOnly('a result is drawn only where a link lands, takes no pointer, and its words select like any other, in either theme', async ({ page }) => {
	// the paper's own typography marks every result; a press on one reaches the words under it, and only a landed result is tinted, translucently, since the glyphs are on the canvas beneath
	const alpha = (c: string) => { const n = (c.match(/[\d.]+/g) ?? []).map(Number); return n[3] ?? 1; };
	for (const scheme of ['light', 'dark'] as const) {
		await page.emulateMedia({ colorScheme: scheme });
		await page.goto('/library/Bellamy19?page=2');
		const mark = page.locator('.page .mark.result').first();
		await expect(mark).toBeAttached();
		await mark.scrollIntoViewIfNeeded();
		expect(alpha(await mark.evaluate((el) => getComputedStyle(el).backgroundColor)), `${scheme}: drawn at rest`).toBe(0);
		const hit = await mark.evaluate((el) => { const r = el.getBoundingClientRect(); return document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2)?.tagName; });
		expect(hit, `${scheme}: a press on a result reaches the words`).toBe('SPAN');
		const box = (await mark.boundingBox())!;
		await page.mouse.move(box.x + 4, box.y + box.height / 2);
		await page.mouse.down();
		await page.mouse.move(box.x + box.width - 4, box.y + box.height / 2, { steps: 8 });
		await page.mouse.up();
		expect((await page.evaluate(() => String(window.getSelection()))).trim().length, `${scheme}: a drag across a result selects its words`).toBeGreaterThan(3);
		await page.goto('/library/Bellamy19?page=2&result=Bellamy19-thm-3.2');
		const landed = page.locator('.page .mark.result.on').first();
		await expect(landed).toBeAttached();
		const a = alpha(await landed.evaluate((el) => getComputedStyle(el).backgroundColor));
		expect(a, `${scheme}: a landed result is tinted`).toBeGreaterThan(0);
		expect(a, `${scheme}: a landed result covers its words`).toBeLessThan(0.5);
	}
});

readOnly('a result that starts mid-line lands with every line of it in half a pane', async ({ page }) => {
	// the 0.14 study: landing scrolled to the first word of `Theorem 3.2.`'s statement, past the margin its other lines start at, so every line but the first lost its opening words
	await page.setViewportSize({ width: 1440, height: 900 });
	// Let the initial 30-frame landing window expire before the PDF arrives.
	await page.route('**/paper.pdf', async (route) => {
		await new Promise((resolve) => setTimeout(resolve, 1200));
		await route.continue();
	});
	await page.goto('/library/Bellamy19?page=2&result=Bellamy19-thm-3.2&beside=%2Fnode%2Fsh-0009');
	const lines = page.locator('[data-pane="0"] [data-mark="Bellamy19-thm-3.2"]');
	await expect(lines).toHaveCount(4);
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
	const cdp = await context.newCDPSession(page);
	await cdp.send('Emulation.setCPUThrottlingRate', { rate: 8 });
	for (const at of ['/library/Arden24', '/master/drafting/main-atomic']) {
		await page.goto(at);
		if (at.startsWith('/master')) {
			await page.locator('[data-pane="0"] .fragment mjx-container').first().waitFor();
			await page.locator('[data-pane="0"] a', { hasText: 'Proposition 2.1' }).first().click();
		}
		await page.getByTestId('zoom-in').waitFor();
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

readOnly("Bellamy19's overview, written by the survey agent through `loom write`, tops its Info with its result links named", async ({ page }) => {
	// plan 0.21.3: the showcase's survey session writes the overview; the publisher renders it with its blocks and says who wrote it
	await page.goto('/library/Bellamy19?view=info');
	const overview = page.getByTestId('work-overview');
	await expect(overview).toContainText('Bellamy counts the lattice points of the median polytope');
	await expect(overview.getByTestId('page-meta')).toContainText('written by Survey Agent');
	await expect(overview.locator('section[data-block="proof-basics"] h2')).toHaveText('proof-basics');
	await expect(overview.locator('a').filter({ hasText: /3\.2/ }).first()).toBeVisible();
});

readOnly("a paper's page in view is what loom here reports, at the address loom link prints", async ({ page, served }) => {
	await page.goto(PAGE2);
	await page.locator('[data-testid="pdf-page-2"] canvas').waitFor();
	const looking = () => JSON.parse(served.loom(['here', '--json'])).looking ?? {};
	await expect.poll(() => looking().item?.work).toBe('Bellamy19');
	await expect.poll(() => looking().item?.page).toBe(2);
	expect(looking().item.link).toMatch(/^cited:.+\?page=2$/);
});

// Where a work opens: where the reader last was, unless a link names a place. These write nothing to the quilt, only to this browser, so each runs on its worker's copy in a browser of its own.
const BELLAMY = '/library/Bellamy19';
const SECOND = '/library/Arden24A';
const QUOTE = 'The median orders of a weighted digraph are in bijection with the vertices';

/** A work's file in a copy of the quilt, by what its manifest says. */
function fileOf(root: string, citekey: string): Buffer {
	const ref = JSON.parse(readFileSync(join(root, '.loom/build/manifest.json'), 'utf8')).references[citekey];
	return readFileSync(join(root, '.loom', ref.artifacts.dir, 'paper.pdf'));
}

/** The paper's scrolling column in a pane. */
const paperIn = (page: Page, pane: number) => page.locator(`[data-pane="${pane}"] .column`);

type At = { page: number; share: number };

/** Where a pane's paper stands, read off the column itself: the page at its top, and how far down that page. */
async function placeIn(page: Page, pane = 0): Promise<At> {
	return paperIn(page, pane).evaluate((c) => {
		const tops = [...c.querySelectorAll<HTMLElement>('[data-holder]')].map((h) => h.offsetTop);
		let at = 0;
		while (at + 1 < tops.length && tops[at + 1] <= c.scrollTop) at++;
		return { page: at + 1, share: Math.max(0, (c.scrollTop - tops[at]) / ((tops[at + 1] ?? c.scrollHeight) - tops[at])) };
	});
}

const said = (at: At) => `page ${at.page}, ${at.share.toFixed(3)} down`;

/** Wait until a pane's paper stands at `want`, to within `within` of a page: a hundredth is about eleven pixels at the default zoom. */
async function isAt(page: Page, want: At, { pane = 0, within = 0.01 } = {}): Promise<void> {
	await expect
		.poll(async () => {
			const at = await placeIn(page, pane);
			return at.page === want.page && Math.abs(at.share - want.share) <= within ? said(want) : said(at);
		})
		.toBe(said(want));
}

/** As `isAt`, and still there a moment later: what undoes a place arrives after it has been reached, a drawn page or a landing's scroll. */
async function staysAt(page: Page, want: At, { pane = 0, within = 0.01 } = {}): Promise<void> {
	await isAt(page, want, { pane, within });
	await paperIn(page, pane).locator(`[data-holder="${want.page}"] canvas`).waitFor();
	await page.waitForTimeout(800);
	await isAt(page, want, { pane, within });
}

/** Wait until page `n`'s top is at the top of a pane's paper, where asking for a page sends it, and still there a moment later. Measured exactly, since a page's top can fall between pixels, where `placeIn`, which reads rounded offsets, calls it the foot of the page before. */
async function arrived(page: Page, n: number, pane = 0): Promise<void> {
	const off = () => paperIn(page, pane).evaluate((c, n) => Math.abs(c.querySelector(`[data-holder="${n}"]`)!.getBoundingClientRect().top - c.getBoundingClientRect().top), n);
	await expect.poll(off).toBeLessThanOrEqual(1);
	await page.waitForTimeout(800);
	await expect.poll(off).toBeLessThanOrEqual(1);
}

/** Wait until this browser has kept `want` as where the reader is in a file, which it does once the column has been still a moment: a window opened or a reload before that finds the place before it. */
async function kept(page: Page, want: At): Promise<void> {
	await expect
		.poll(async () => {
			const places = await page.evaluate(() => Object.values<At>(JSON.parse(localStorage.getItem('arras.places') ?? '{}')));
			return places.some((at) => at.page === want.page && Math.abs(at.share - want.share) <= 0.01) ? said(want) : places.map(said).join(', ') || 'nothing kept';
		})
		.toBe(said(want));
}

/** Scroll a pane's paper to `want` as a reader does, with the wheel: only a hand on the paper moves it off a link's place. */
async function readTo(page: Page, want: At, pane = 0): Promise<void> {
	const paper = paperIn(page, pane);
	await paper.locator(`[data-holder="${want.page}"]`).waitFor({ state: 'attached' });
	const box = (await paper.boundingBox())!;
	await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
	await expect
		.poll(
			async () => {
				const away = await paper.evaluate((c, to) => {
					const holder = c.querySelector<HTMLElement>(`[data-holder="${to.page}"]`)!;
					const next = holder.nextElementSibling as HTMLElement | null;
					return Math.round(holder.offsetTop + to.share * ((next?.offsetTop ?? c.scrollHeight) - holder.offsetTop) - c.scrollTop);
				}, want);
				if (Math.abs(away) <= 4) return 'there';
				await page.mouse.wheel(0, away);
				return `${away}px away`;
			},
			{ intervals: [300] }
		)
		.toBe('there');
}

/** Open a work from the column's Library, as a reader chooses what to read. A work and its revision are one row, so a row is named by how its key begins. */
async function fromShelf(page: Page, citekey: string): Promise<void> {
	const row = page.locator(`a[data-testid^="library-work-${citekey}"]`);
	if (!(await row.isVisible())) await page.getByTestId('library-toggle').click();
	await row.click();
}

/** Leave for the work's Info and come back, which makes the paper again. */
async function toInfoAndBack(page: Page): Promise<void> {
	await page.getByTestId('tab-info').click();
	await page.getByTestId('work-info').waitFor();
	await page.getByTestId('tab-paper').click();
}

/** A PDF of `n` pages saying their numbers, the first small and the rest A4, as nothing in the showcase is: long enough that most of it is never drawn, and not one size throughout. */
function longPdf(n: number): Buffer {
	const bodies = ['<< /Type /Catalog /Pages 2 0 R >>', `<< /Type /Pages /Count ${n} /Kids [${Array.from({ length: n }, (_, i) => `${4 + 2 * i} 0 R`).join(' ')}] >>`, '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>'];
	for (let i = 0; i < n; i++) {
		const text = `BT /F1 24 Tf 72 400 Td (Page ${i + 1}) Tj ET`;
		bodies.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${i ? '595 842' : '400 600'}] /Resources << /Font << /F1 3 0 R >> >> /Contents ${5 + 2 * i} 0 R >>`);
		bodies.push(`<< /Length ${text.length} >>\nstream\n${text}\nendstream`);
	}
	let out = '%PDF-1.4\n';
	const offsets = bodies.map((b, i) => {
		const at = out.length;
		out += `${i + 1} 0 obj\n${b}\nendobj\n`;
		return at;
	});
	const xref = out.length;
	out += `xref\n0 ${bodies.length + 1}\n0000000000 65535 f \n${offsets.map((o) => `${String(o).padStart(10, '0')} 00000 n \n`).join('')}`;
	out += `trailer\n<< /Size ${bodies.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
	return Buffer.from(out, 'latin1');
}

readOnly('a work opens where the reader left it: after a reload, by a plain link, from the shelf and from the library’s page', async ({ page }) => {
	const left = { page: 2, share: 0.4 };
	await page.goto(BELLAMY);
	await readTo(page, left);
	await page.reload();
	await staysAt(page, left);
	// a new visit, by a plain link
	await page.goto('/review');
	await page.goto(BELLAMY);
	await staysAt(page, left);
	// from the shelf, with something else being read
	await page.goto(SECOND);
	await fromShelf(page, 'Bellamy19');
	await staysAt(page, left);
	// from the library's own page
	await page.goto('/review/library');
	await page.getByTestId('ledger-Bellamy19').locator('a.title').click();
	await staysAt(page, left);
});

readOnly('a link that names a place wins over where the reader last was, and is where they are from then on', async ({ page }) => {
	const left = { page: 3, share: 0.2 };
	await page.goto(BELLAMY);
	await readTo(page, left);
	// a page
	await page.goto(`${BELLAMY}?page=2`);
	await staysAt(page, { page: 2, share: 0 });
	// and the visit has moved where the reader last was
	await page.goto(BELLAMY);
	await staysAt(page, { page: 2, share: 0 });
	// a quote with no page, which the paper only learns is on page 2 from loom's answer
	await readTo(page, left);
	await page.goto(`${BELLAMY}?quote=${encodeURIComponent(QUOTE)}`);
	const lit = page.locator('[data-mark="_locator"]').first();
	await expect(lit).toBeInViewport();
	await expect(page.getByTestId('page-at')).toHaveValue('2');
	await page.waitForTimeout(800);
	await expect(lit).toBeInViewport();
	// a result, by its address and by a citation of it
	await page.goto(SECOND);
	await readTo(page, { page: 1, share: 0.5 });
	await page.goto(`${SECOND}?page=3&result=Arden24A-thm-5.1`);
	const mark = page.locator('[data-mark="Arden24A-thm-5.1"]').first();
	await expect(mark).toBeInViewport();
	await page.waitForTimeout(800);
	await expect(mark).toBeInViewport();
	await expect(page.getByTestId('page-at')).toHaveValue('3');
	await readTo(page, { page: 1, share: 0.5 });
	await page.goto('/node/sh-0100');
	await page.locator('[data-pane="0"] span.cite[data-target="Arden24A-thm-5.1"] a').first().click();
	await expect(page.locator('[data-pane="1"] [data-mark="Arden24A-thm-5.1"]').first()).toBeInViewport();
	await expect(page.getByTestId('pane-1').getByTestId('page-at')).toHaveValue('3');
});

readOnly('a work never read opens at its start, whatever was read before it', async ({ page }) => {
	await page.goto(BELLAMY);
	await staysAt(page, { page: 1, share: 0 });
	await readTo(page, { page: 2, share: 0.4 });
	await page.goto(SECOND);
	await staysAt(page, { page: 1, share: 0 });
});

readOnly('two works keep a place each', async ({ page }) => {
	const first = { page: 3, share: 0.2 };
	const second = { page: 2, share: 0.4 };
	await page.goto(BELLAMY);
	await readTo(page, first);
	await page.goto(SECOND);
	await readTo(page, second);
	await page.reload();
	await staysAt(page, second);
	await fromShelf(page, 'Bellamy19');
	await staysAt(page, first);
	await page.getByRole('tab', { name: 'Arden24A' }).click();
	await staysAt(page, second);
});

readOnly('a work is open in one pane of a window, and a second window on it leaves the first where it is', async ({ page, context }) => {
	await page.goto(`${BELLAMY}?beside=${encodeURIComponent(BELLAMY)}`);
	await expect(page.locator('[data-pane]')).toHaveCount(1);
	await page.goto(BELLAMY);
	const mine = { page: 2, share: 0.4 };
	await readTo(page, mine);
	// a second window opens where the first was, and goes its own way
	const other = await context.newPage();
	await other.goto(BELLAMY);
	await staysAt(other, mine);
	const theirs = { page: 3, share: 0.2 };
	await readTo(other, theirs);
	await staysAt(page, mine);
	// not even a paper made again takes the other window's place: what this window was doing is in the tab
	await toInfoAndBack(page);
	await staysAt(page, mine);
	await staysAt(other, theirs);
	// whichever moved last is what the next visit opens at
	await readTo(page, { page: 1, share: 0.5 });
	await kept(page, { page: 1, share: 0.5 });
	const third = await context.newPage();
	await third.goto(BELLAMY);
	await staysAt(third, { page: 1, share: 0.5 });
});

readOnly('a tab brought back and a paper back from Info are where they were left', async ({ page }) => {
	const left = { page: 2, share: 0.4 };
	await page.goto(BELLAMY);
	await readTo(page, left);
	await fromShelf(page, 'Arden24');
	await staysAt(page, { page: 1, share: 0 });
	await page.getByRole('tab', { name: 'Bellamy19' }).click();
	await staysAt(page, left);
	await toInfoAndBack(page);
	await staysAt(page, left);
	// a page asked for in the box is answered once, not again by a paper made later
	const at = page.getByTestId('page-at');
	await at.click();
	await page.keyboard.type('3');
	await page.keyboard.press('Enter');
	await expect(at).toHaveValue('3');
	// read back from page 3, once the paper is there
	await arrived(page, 3);
	await readTo(page, left);
	await toInfoAndBack(page);
	await staysAt(page, left);
});

readOnly('a link’s place holds until the reader has left its page: then it comes off the address, and a reload stays with them', async ({ page }) => {
	await page.goto(`${BELLAMY}?quote=${encodeURIComponent(QUOTE)}`);
	const lit = page.locator('[data-mark="_locator"]').first();
	await expect(lit).toBeInViewport();
	await expect(page).toHaveURL(/quote=/);
	// moved within its page, the link is still in force and still lit, and a paper made again does not send the reader back to its place
	const within = { page: 2, share: 0.4 };
	await readTo(page, within);
	await expect(page).toHaveURL(/quote=/);
	await expect(lit).toBeAttached();
	await toInfoAndBack(page);
	await staysAt(page, within);
	await expect(lit).toBeAttached();
	// off its page, it lets go
	const on = { page: 3, share: 0.2 };
	await readTo(page, on);
	await expect(page).toHaveURL(new RegExp(`${BELLAMY}$`));
	await expect(page.locator('[data-mark="_locator"]')).toHaveCount(0);
	await staysAt(page, on);
	await page.reload();
	await staysAt(page, on);
});

readOnly('a plain link to a work already open leaves the reader where they are', async ({ page }) => {
	const left = { page: 2, share: 0.4 };
	await page.goto(BELLAMY);
	await readTo(page, left);
	await fromShelf(page, 'Bellamy19');
	await staysAt(page, left);
	// and with a link's place in force, it is the plain link that goes
	await page.goto(`${BELLAMY}?page=3`);
	await staysAt(page, { page: 3, share: 0 });
	await readTo(page, { page: 3, share: 0.2 });
	await fromShelf(page, 'Bellamy19');
	await expect(page).toHaveURL(new RegExp(`${BELLAMY}$`));
	await staysAt(page, { page: 3, share: 0.2 });
});

readOnly('a place holds at another zoom and another width, with most of a long paper never drawn', async ({ page }) => {
	const body = longPdf(40);
	await page.route('**/paper.pdf', (r) => r.fulfill({ body, contentType: 'application/pdf' }));
	await page.goto(BELLAMY);
	await expect(page.getByTestId('page-count')).toContainText('40');
	const at = page.getByTestId('page-at');
	await at.click();
	await page.keyboard.type('30');
	await page.keyboard.press('Enter');
	await page.locator('[data-testid="pdf-page-30"] canvas').waitFor();
	const left = { page: 30, share: 0.4 };
	await readTo(page, left);
	await page.reload();
	await staysAt(page, left);
	// the pages it passed over hold a size and nothing else, and the size is the first page's even though the first page was never drawn
	await expect(page.locator('[data-testid="pdf-page-1"] canvas')).toHaveCount(0);
	await expect(page.locator('[data-testid="pdf-page-20"] canvas')).toHaveCount(0);
	const tall = (n: number) => page.locator(`[data-holder="${n}"]`).evaluate((h) => h.getBoundingClientRect().height);
	expect((await tall(20)) / (await tall(30))).toBeCloseTo(600 / 842, 2);
	const zoom = page.getByTestId('zoom-at');
	await zoom.click();
	await page.keyboard.type('75');
	await page.keyboard.press('Enter');
	await expect(zoom).toHaveValue('75%');
	await staysAt(page, left, { within: 0.02 });
	await page.reload();
	await staysAt(page, left, { within: 0.02 });
	await page.setViewportSize({ width: 900, height: 700 });
	await page.reload();
	await staysAt(page, left, { within: 0.02 });
});

readOnly('a page asked for as a long paper opens is where it stays, as the pages around it draw at their own size', async ({ page }) => {
	const body = longPdf(300);
	await page.route('**/paper.pdf', (r) => r.fulfill({ body, contentType: 'application/pdf' }));
	await page.goto(BELLAMY);
	await expect(page.getByTestId('page-count')).toContainText('300');
	const at = page.getByTestId('page-at');
	await at.click();
	await page.keyboard.type('250');
	await page.keyboard.press('Enter');
	await arrived(page, 250);
	await expect(at).toHaveValue('250');
	// and it is where a paper made again opens
	await toInfoAndBack(page);
	await arrived(page, 250);
});

readOnly('a place in another file behind the work is not carried over, and a page it no longer has is not looked for', async ({ page, served }) => {
	const left = { page: 2, share: 0.4 };
	await page.goto(BELLAMY);
	await readTo(page, left);
	await kept(page, left);
	// another file of the same length: its page 2 is not the page they were on
	const another = fileOf(served.root, 'Arden24A');
	await page.route('**/paper.pdf', (r) => r.fulfill({ body: another, contentType: 'application/pdf' }));
	await page.reload();
	await staysAt(page, { page: 1, share: 0 });
	// a file that came back is the one they were in
	await page.unroute('**/paper.pdf');
	await page.reload();
	await staysAt(page, left);
	// a shorter file has no such page, and opens at its start rather than at its end
	await readTo(page, { page: 3, share: 0.2 });
	await kept(page, { page: 3, share: 0.2 });
	const shorter = longPdf(2);
	await page.route('**/paper.pdf', (r) => r.fulfill({ body: shorter, contentType: 'application/pdf' }));
	await page.reload();
	await expect(page.getByTestId('page-count')).toContainText('2');
	await staysAt(page, { page: 1, share: 0 });
});

test.describe('a PDF among the project’s files', () => {
	const OWN = 'notes/bellamy.pdf';
	const AT = `/file/${OWN}`;
	// the same bytes as Bellamy19's paper, as a reference kept in a folder and also added to the library is
	test.use({
		prepareQuilt: async ({}, use: (p: (q: { root: string }) => void) => Promise<void>) => {
			await use(({ root }) => {
				mkdirSync(join(root, 'notes'), { recursive: true });
				writeFileSync(join(root, OWN), fileOf(root, 'Bellamy19'));
			});
		}
	});

	test('opens where it was left, after a reload, by a plain link and as a tab brought back', async ({ page }) => {
		await page.goto(AT);
		await staysAt(page, { page: 1, share: 0 });
		const left = { page: 2, share: 0.4 };
		await readTo(page, left);
		await page.reload();
		await staysAt(page, left);
		await page.goto('/review');
		await page.goto(AT);
		await staysAt(page, left);
		await fromShelf(page, 'Arden24');
		await staysAt(page, { page: 1, share: 0 });
		await page.getByRole('tab', { name: 'bellamy.pdf' }).click();
		await staysAt(page, left);
	});

	test('a link to its page wins, until the reader has left that page: then the address lets go, and a reload stays with them', async ({ page }) => {
		await page.goto(AT);
		await readTo(page, { page: 2, share: 0.4 });
		await page.goto(`${AT}#page=3`);
		await staysAt(page, { page: 3, share: 0 });
		// moved within its page, the link is still in force, and a tab brought back does not send the reader back to its place
		const within = { page: 3, share: 0.2 };
		await readTo(page, within);
		await expect(page).toHaveURL(/#page=3$/);
		await fromShelf(page, 'Arden24');
		await page.getByRole('tab', { name: 'bellamy.pdf' }).click();
		await staysAt(page, within);
		// off its page, it lets go
		const on = { page: 1, share: 0.5 };
		await readTo(page, on);
		await expect(page).toHaveURL(new RegExp(`${AT}$`));
		await staysAt(page, on);
		await page.reload();
		await staysAt(page, on);
	});

	test('the same file as a work keeps one place, whichever way it is opened, and neither moves the other when both are open', async ({ page }) => {
		const first = { page: 2, share: 0.4 };
		await page.goto(BELLAMY);
		await readTo(page, first);
		await page.goto(AT);
		await staysAt(page, first);
		// a place the column can stand at in half a pane too, where the pages are drawn smaller and its end comes sooner
		const then = { page: 2, share: 0.1 };
		await readTo(page, then);
		await page.goto(BELLAMY);
		await staysAt(page, then);
		await page.goto(`${BELLAMY}?beside=${encodeURIComponent(AT)}`);
		await staysAt(page, then, { pane: 0 });
		await staysAt(page, then, { pane: 1 });
		const beside = { page: 1, share: 0.5 };
		await readTo(page, beside, 1);
		await staysAt(page, then, { pane: 0 });
		await page.waitForTimeout(400);
		await page.goto(BELLAMY);
		await staysAt(page, beside);
	});
});
