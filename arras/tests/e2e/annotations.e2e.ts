// Annotations as a reader meets them: marks in the text, the boxes they open floating or inline, all of them opened at once, what a suggestion proposes, and the verbs and tools that write one where a publisher serves. Each test is named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { beside, pane, prefs } from '../workspace';
import { openPicker, pickSession } from '../picker';
import { manifest, REFEREE } from '../manifest';

test.describe('marks and boxes', () => {
	test('a mark is coloured by its comment kind', async ({ page }) => {
		await page.goto('/master/main');
		const mark = page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-0001"]');
		await expect(mark).toHaveClass(/k-objection/);
	});

	test('a node draws no annotation list: its marks open their boxes, show all opens every one in the flow, and the discarded are in its context', async ({ page }) => {
		// a mark opens its annotation as a floating box over the text; `show all annotations` opens every one; nothing below the node lists them again
		await page.goto('/node/sy-0003');
		// counted as "every open annotation on this key has a box", not as a literal, so adding one to the fixture does not fail a test that is about marks and boxes agreeing
		const open = await page.evaluate(async () => {
			const m = await (await fetch(new URL('/build/manifest.json', location.href))).json();
			// every key the node owns: its statement and its proofs, which carry ids of their own rather than a `/proof` suffix
			const keys = Object.entries(m.keys)
				.filter(([, k]: [string, any]) => k.node === 'sy-0003')
				.map(([id]) => id);
			return Object.values(m.annotations).filter((a: any) => keys.includes(a.target.key) && !a.in_reply_to && !a.discarded).length;
		});
		expect(open).toBeGreaterThan(1);
		await expect(page.getByTestId('annotation-list')).toHaveCount(0);
		// only the annotations that quote a phrase can be marked in the text
		const marks = page.locator('.fragment mark.annotation');
		await expect(marks).toHaveCount(2);
		await marks.first().click();
		const opened = page.locator('[data-testid="comment-expanded"] article.box');
		await expect(opened).toHaveCount(1);
		await expect(opened.locator('> header .kind')).toHaveText('objection');
		await expect(opened.locator('.reply')).toHaveCount(1);
		await expect(page.locator('.comment-slot.expanded.floating')).toHaveCount(1);
		// the rail opens every one at once, each at its mark or beside its result's label, in the flow rather than floating
		await page.getByTestId('toggle-annotations').click();
		await expect(opened).toHaveCount(open);
		await expect(page.locator('.comment-slot.expanded.floating')).toHaveCount(0);
		await page.getByTestId('toggle-annotations').click();
		await expect(page.locator('aside.comment-slot.expanded')).toHaveCount(0);
		// and with them closed, a single mark still floats
		await marks.first().click();
		await expect(page.locator('.comment-slot.expanded.floating')).toHaveCount(1);
		// sy-000A's one annotation is discarded and belongs to a closed session, so two filters hide it and the reader must lift both; closing a session hides its annotations, which is what closing one is for
		await page.goto('/node/sy-000A' + beside('/context/sy-000A'));
		const context = pane(page, 1);
		await expect(context.getByTestId('context')).toBeVisible();
		await expect(context.getByTestId('show-discarded')).toHaveCount(0);
		// the closed section unfolds, and the setting inside it is what admits their annotations
		await openPicker(page);
		await page.getByTestId('show-closed').click();
		await page.getByTestId('closed-yes').click();
		await page.keyboard.press('Escape');
		// a quiet line in the context says how many were discarded, and shows them there
		await expect(context.getByTestId('show-discarded')).toHaveText('1 discarded — show');
		await context.getByTestId('show-discarded').click();
		await expect(context.getByTestId('discarded-list').locator('article.box.discarded')).toHaveCount(1);
	});

	test('floating, a mark opens a box clear of every edge and a second mark a second box; × closes one, Escape or a click away the rest, and hovering opens nothing', async ({ page }) => {
		await prefs(page, { comments: 'floating' });
		// any delay a hover could open a box after runs on the page's clock, which the test moves on rather than sleeping
		await page.clock.install();
		await page.goto('/node/sy-0003');
		// a fragment is wired once for the default placement and again when the stored preferences arrive, so waiting on the marks is not enough: wait until it is wired for the placement under test
		await page.waitForSelector('.fragment[data-comments-wired="floating"] mark.annotation[data-wired-mark]');
		const marks = page.locator('.fragment mark.annotation');
		await expect(marks).toHaveCount(2);
		const slots = page.locator('aside.comment-slot.floating');
		const open = page.locator('.comment-slot.expanded.floating');
		await expect(slots).toHaveCount(0);

		// hovering never opens one: a box the pointer summons cannot be read without holding it still, and moving toward the box leaves the mark
		await marks.first().hover({ force: true });
		await page.clock.runFor(400);
		await expect(slots).toHaveCount(0);

		await marks.first().click();
		await expect(slots).toHaveCount(1);
		// it floats over the page rather than opening in the flow, so it is free to overlap the text and the gutter
		await expect(slots).toHaveCSS('position', 'fixed');
		await expect(slots.locator('article.box')).toHaveCount(1);
		// and it is kept clear of every edge, so a mark near one slides the box rather than clipping it
		const inset = await slots.evaluate((el) => {
			const r = el.getBoundingClientRect();
			return Math.min(r.left, r.top, window.innerWidth - r.right, window.innerHeight - r.bottom);
		});
		expect(inset).toBeGreaterThanOrEqual(3.5);

		// a second mark opens a second box rather than replacing the first, so two annotations can be read side by side
		await marks.nth(1).click();
		await expect(open).toHaveCount(2);
		// a box's own × closes just that one
		await open.first().locator('.comment-close').click();
		await expect(open).toHaveCount(1);
		// clicking the text closes what is left, leaving no faded stub behind
		await page.locator('.fragment p').first().click({ position: { x: 4, y: 4 } });
		await expect(open).toHaveCount(0);
		await expect(page.locator('.comment-slot.floating.behind')).toHaveCount(0);

		// Escape closes the front-most, and a click anywhere away closes what is open
		await marks.first().click();
		await expect(slots).toHaveCount(1);
		await page.keyboard.press('Escape');
		await expect(slots).toHaveCount(0);
		await marks.first().click();
		await expect(slots).toHaveCount(1);
		await page.mouse.click(4, 4);
		await expect(slots).toHaveCount(0);
	});

	test('inline, a mark expands its comment beneath its paragraph; clicking away closes it', async ({ page }) => {
		await prefs(page, { comments: 'inline' });
		await page.goto('/master/main');
		await page.waitForSelector('.fragment .env[data-key]');
		await expect(page.locator('aside.comment-slot.gutter')).toHaveCount(0);

		const mark = page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-0001"]');
		await mark.click();
		const open = page.locator('aside.comment-slot.expanded');
		await expect(open).toHaveCount(1);
		await expect(open.locator('article.box')).toHaveCount(1); // the reply is inside its parent, not a second box
		await expect(open.locator('.replies')).toBeVisible();
		await expect(mark).toHaveAttribute('aria-expanded', 'true');
		// in the flow, directly after the paragraph holding the mark
		const follows = await mark.evaluate((m) => {
			const block = m.closest('p, li, .math.display, .annotation-block, summary');
			return block?.nextElementSibling?.className ?? '(nothing follows the block)';
		});
		expect(follows.split(/\s+/)).toContain('expanded');

		// clicking away closes it, leaving nothing behind
		await page.mouse.click(5, 5);
		await expect(page.locator('aside.comment-slot.expanded')).toHaveCount(0);

		// and Escape closes the front-most
		await mark.click();
		await expect(open).toHaveCount(1);
		await page.keyboard.press('Escape');
		await expect(page.locator('aside.comment-slot.expanded')).toHaveCount(0);
	});

	test('inline, a comment with no mark is reached from a count beside its node', async ({ page }) => {
		await prefs(page, { comments: 'inline' });
		await page.goto('/master/main');
		// a-2026-09-16-0006 lost its anchor, so it has no mark on sy-0001
		const count = page.locator('.fragment button.comment-count[data-count-for="sy-0001"]');
		await expect(count).toHaveText('1 comment');
		await count.click();
		await expect(page.locator('aside.comment-slot.expanded article.box')).toHaveCount(1);
	});

	test('e opens every annotation at its mark, and h closes them', async ({ page }) => {
		// the document view draws no buttons for these, so the keys are the whole affordance here
		await page.goto('/master/main');
		await page.waitForSelector('.fragment mjx-container');
		const boxes = page.locator('aside.comment-slot.expanded');
		await expect(page.getByTestId('content-head')).toHaveCount(0);
		await expect(boxes).toHaveCount(0);

		await page.locator('.fragment').focus();
		await page.keyboard.press('e');
		await expect.poll(() => boxes.count()).toBeGreaterThan(1);

		await page.keyboard.press('h');
		await expect(boxes).toHaveCount(0);
	});

	test('travel from a mark says so when there is nowhere to go', async ({ page }) => {
		// alone, a node lists no annotations, so a mark has nowhere to travel to, and a notice says so rather than inventing a place
		await page.goto('/node/sy-0003');
		await page.locator('.fragment mark.annotation').first().dblclick();
		await expect(page.getByTestId('travel-nowhere')).toBeVisible();
		await expect(page.getByTestId('travel-nowhere')).toHaveCount(0, { timeout: 3000 });
	});

	test('a document carries annotations of its own, and they are read beside it', async ({ page }) => {
		// a remark about the whole paper is not drawn above its title; it is read in what the session did, beside the document
		await page.goto('/master/main' + beside(`/session/${REFEREE}?view=did`));
		await expect(page.getByTestId('document-annotations')).toHaveCount(0);
		const did = page.getByTestId('session-did');
		// found by its id rather than by being first; the list is compact rows, not boxes
		const own = Object.values(manifest.annotations as Record<string, { id: string; body_html: string; target: { key: string } }>).find(
			(a) => a.body_html.includes('which conventions it inherits') && a.target.key === 'drafting/main.tex'
		)!;
		await expect(did.locator(`[id="ann-${own.id}"]`)).toHaveCount(1);
	});

	test('a suggestion shows the text it proposes as source, says where it would go, and renders it on asking', async ({ page }) => {
		// what is proposed is text to be written into a document, so the source is what a reader judges and what opens; the rendering is the second question, and the control names what a click gives
		await page.goto('/node/sy-0004');
		await page.getByTestId('toggle-annotations').click();
		const payload = page.locator('article.box[data-annotation-id="a-2026-09-16-0002"] [data-testid="payload"]');
		await expect(payload).toBeVisible();
		await expect(payload).toHaveAttribute('data-placement', 'replace');
		await expect(payload).toContainText('disjoint union of orbits');
		await expect(page.getByTestId('severity').first()).toBeVisible();
		await expect(payload.getByTestId('payload-verbatim')).toContainText('\\ref{sy-0002}');
		await expect(payload.getByTestId('payload-rendered')).toHaveCount(0);
		const view = payload.getByTestId('payload-view');
		await expect(view).toHaveText('rendered latex');

		await view.click();
		await expect(payload.getByTestId('payload-verbatim')).toHaveCount(0);
		// rendered means rendered: the math is typeset, and the LaTeX that produced it is not on screen
		await expect(payload.getByTestId('payload-rendered').locator('mjx-container')).not.toHaveCount(0);
		await expect(payload.getByTestId('payload-rendered')).not.toContainText('\\ref');
		await expect(view).toHaveText('verbatim code');
	});
});

test.describe('the placement', () => {
	test('the placement is a display setting', async ({ page }) => {
		await page.goto('/master/main');
		await page.getByTestId('settings-toggle').click();
		await page.getByTestId('comments-inline').click();
		await expect(page.locator('html')).toHaveAttribute('data-comments', 'inline');
		await expect(page.locator('aside.comment-slot.gutter')).toHaveCount(0);
	});

	test('changing the placement re-wires the document without typesetting it again', async ({ page }) => {
		await prefs(page, { comments: 'floating' });
		await page.goto('/master/main');
		await page.waitForSelector('.fragment[data-comments-wired="floating"] mjx-container');
		await page.waitForFunction(() => document.querySelectorAll('.fragment .math:not(:has(mjx-container))').length === 0);
		await page.evaluate(() => {
			const w = window as unknown as { MathJax: { typesetPromise: (els: Element[]) => Promise<void> }; typeset: string[] };
			const real = w.MathJax.typesetPromise.bind(w.MathJax);
			w.typeset = [];
			// a comment card typesets its own body; what must not happen is the document's text going through MathJax again
			w.MathJax.typesetPromise = (els) => {
				w.typeset.push(els.some((e) => e.closest('.fragment') && !e.closest('aside.comment-slot')) ? 'document' : 'card');
				return real(els);
			};
		});
		await page.getByTestId('settings-toggle').click();
		await page.getByTestId('comments-inline').click();
		await page.waitForSelector('.fragment[data-comments-wired="inline"]');
		await page.getByTestId('comments-floating').click();
		await page.waitForSelector('.fragment[data-comments-wired="floating"]');
		// a later event rendered: a mark opened after the switch draws its box, so any re-typeset the switch set off has had its turn
		await page.keyboard.press('Escape');
		await page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-0001"]').click();
		await expect(page.locator('aside.comment-slot.floating article.box').first()).toBeVisible();
		expect(await page.evaluate(() => (window as unknown as { typeset: string[] }).typeset)).not.toContain('document');
	});
});

test.describe('writing', () => {
	/** Advertise `caps` from the publisher's write API and accept every write; `vite preview` serves none, and the controls appear only where one is. */
	async function writes(page: Page, caps: string[]): Promise<void> {
		await page.route('**/_api', (r) => r.fulfill({ json: { write_api: 1, capabilities: caps, token: 't' } }));
		await page.route('**/_api/*', (r) => r.fulfill({ json: { ok: true, result: 'done' } }));
	}

	test('with no write API there is no editing affordance at all: no verbs on what is written, no tools to write with', async ({ page }) => {
		// detected, never assumed: the fixture is served by a static preview with no write API, which is also what a deployed static site gets
		await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
		await expect(pane(page, 1).getByTestId('reference-notes')).toBeVisible();
		await pane(page, 0).locator('.fragment mark.annotation').first().click();
		await expect(page.locator('article.box').first()).toBeVisible();
		await expect(page.getByTestId('verb-row')).toHaveCount(0);
		await expect(page.getByTestId('tool-select')).toHaveCount(0);
		await expect(page.getByTestId('refnote-accept')).toHaveCount(0);
	});

	test('a panel opens above the row, so the body it is about never moves', async ({ page }) => {
		await writes(page, ['comment', 'reply', 'resolve', 'edit', 'discard', 'refs-note']);
		// placed inline, the box opens in the flow under its paragraph, which is where a panel pushing down would move the body; a floating box holds its panel in its own flow instead
		await prefs(page, { comments: 'inline' });
		await page.goto('/node/sy-0003');
		await page.locator('.fragment mark.annotation').first().click();
		const row = page.getByTestId('verb-row').first();
		await expect(row).toBeVisible();

		await row.getByTestId('verb-reply').click();
		const panel = row.getByTestId('verb-panel');
		await expect(panel).toBeVisible();
		// polled: the geometry is read after the row has settled, since the row can still be reflowing as its verbs arrive
		await expect
			.poll(async () => {
				const pb = await panel.boundingBox();
				const rb = await row.boundingBox();
				// how far the panel's bottom stands above the row's top; negative is an overlap
				return pb && rb ? rb.y - (pb.y + pb.height) : -Infinity;
			}, { timeout: 5000 })
			.toBeGreaterThanOrEqual(-2);

		// it says nothing until it has something to say
		await expect(panel.getByTestId('verb-send')).toBeDisabled();
		await panel.getByTestId('verb-text').fill('Fixed in the next revision.');
		await expect(panel.getByTestId('verb-send')).toBeEnabled();

		await page.keyboard.press('Escape');
		await expect(panel).toHaveCount(0);
	});

	test('a verb that needs no panel still shows why it was refused', async ({ page }) => {
		// `resolve` is one click and opens no panel, so its refusal is shown in the box: the viewer's own when nothing is selected, the publisher's once the write reaches it
		await page.route('**/_api', (route) => route.fulfill({ json: { write_api: 1, capabilities: ['comment', 'reply', 'resolve', 'edit', 'discard'], token: 't' } }));
		await page.route('**/_api/resolve', (route) =>
			route.fulfill({
				status: 400,
				contentType: 'application/json',
				body: JSON.stringify({ error: { code: 'refused', message: 'no author name: add name = "Your Name" under [author]' } })
			})
		);
		await page.goto('/node/sy-0003');
		const openFirstMark = async () => {
			await page.locator('[data-pane] .fragment mark.annotation').first().click();
			await expect(page.locator('[data-testid="comment-expanded"] article.box').first()).toBeVisible();
		};
		await openFirstMark();
		const said = page.getByTestId('verb-said').first();
		// with nothing selected the write never leaves the viewer, and the verb says which condition is unmet
		await page.getByTestId('verb-resolve').first().click();
		await expect(said).toContainText('No session selected');
		// with one selected the request reaches the publisher, and its refusal is what gets shown
		await pickSession(page, REFEREE);
		await openFirstMark();
		await page.getByTestId('verb-resolve').first().click();
		await expect(said).toBeVisible();
		await expect(said).toContainText('no author name');
	});

	test('with the box tool chosen, a drag that starts on a mark draws a box, and a click on it still opens the mark', async ({ page }) => {
		await page.route('**/_api', (r) => r.fulfill({ json: { write_api: 1, capabilities: ['comment'], token: 't' } }));
		await page.goto('/node/sy-0003');
		const mark = pane(page, 0).locator('.fragment mark.annotation').first();
		await expect(mark).toBeVisible();
		await page.getByTestId('tool-box').click();
		// a click without a drag is still a click on the mark
		await mark.click();
		await expect(pane(page, 0).getByTestId('comment-expanded')).toBeVisible();
		await page.keyboard.press('Escape');
		// a drag from it is a box
		const b = (await mark.boundingBox())!;
		await page.mouse.move(b.x + 4, b.y + b.height / 2);
		await page.mouse.down();
		await page.mouse.move(b.x + 120, b.y + b.height + 30, { steps: 8 });
		await page.mouse.up();
		await expect(page.getByTestId('note-at')).toBeVisible();
	});
});
