// The side panel: the documents and their contents, the Nodes and Library sections, the write target pinned in a footer, and the session list in a picker it opens. Each test is named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { beside, pane, scrollPane } from '../workspace';
import { openPicker, pickSession } from '../picker';
import { QUICK, REFEREE, serveKept } from '../manifest';

// these are about annotations and the page; the fixture's pending changes are left out, and tested apart (changes.e2e.ts)
test.beforeEach(({ page }) => serveKept(page));

/** Advertise a write API with `caps`; the static server serves none, and the controls appear only where one is. */
async function writes(page: Page, caps: string[]): Promise<void> {
	await page.route('**/_api', (route) => route.fulfill({ json: { write_api: 1, capabilities: caps, token: 't' } }));
}

test('the write target is stated once', async ({ page }) => {
	// a title no annotation or author shares, so a count of it is a count of the places that name the session
	await serveKept(page, (m) => {
		m.sessions.find((s: { id: string }) => s.id === REFEREE).title = 'the refereeing sitting';
	});
	// a document and a node beside it: two items, two panes, and still one place that says where writes go
	await page.goto('/master/drafting/main' + beside('/node/sy-0003'));
	await expect(pane(page, 1)).toBeVisible();
	await pickSession(page, REFEREE);
	await expect(page.getByTestId('session-footer-name')).toHaveText('the refereeing sitting');
	// choosing it opened its Chat, whose tab names the item that is open, a different question from where writes go
	const naming = await page.evaluate(
		() =>
			[...document.querySelectorAll('body *')].filter(
				(el) => !el.closest('[data-testid="item-tab"]') && [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent?.includes('the refereeing sitting'))
			).length
	);
	expect(naming).toBe(1);
});

test("the picker chooses where notes go, and nothing about which annotations the page draws", async ({ page }) => {
	await page.goto('/node/sy-0002');
	await openPicker(page);
	const picker = page.getByTestId('session-picker');
	await expect(picker.getByRole('group', { name: 'which annotations the page shows' })).toHaveCount(0);
	await expect(picker.getByTestId('show-all')).toHaveCount(0);
	await expect(picker.getByTestId(`session-${REFEREE}`)).not.toContainText('open');
	await page.keyboard.press('Escape');
});

test('an annotation needs no session, and the footer says in its own tone when nothing is selected', async ({ page }) => {
	await writes(page, ['annotate']);
	await page.goto('/node/sy-0002');
	// a comment left on the node asks for no session
	const words = pane(page, 0).locator('.fragment .env[data-id="sy-0002"] p[data-src]').first();
	await expect(words).toBeVisible();
	await page.getByTestId('tool-comment').click();
	await words.click({ position: { x: 4, y: 4 } });
	await page.getByTestId('popup-comment-field').fill('Say which orbit.');
	await expect(page.getByTestId('popup-save')).toBeEnabled();
	// the footer carries only the state: refused, in its own tone, without the sentence
	const footer = page.getByTestId('session-footer');
	await expect(footer).toHaveAttribute('aria-label', /^not writing in a session/);
	await expect(page.getByTestId('session-footer-lead')).toHaveText('not writing in a session');
	await expect(page.locator('.footer.refused')).toHaveCount(1);
	await pickSession(page, REFEREE);
	await expect(footer).toHaveAttribute('aria-label', 'writing in referee');
	await expect(page.locator('.footer.refused')).toHaveCount(0);
});

test('opening a session says it is working until the publisher answers, and opens one however long that takes', async ({ page }) => {
	// a large quilt is rebuilt before the publisher answers, which took a minute: the field closed at once and showed nothing, so the reader pressed Enter again and got two sessions
	await writes(page, ['session-new']);
	let calls = 0;
	let release: () => void = () => {};
	const answered = new Promise<void>((done) => (release = done));
	await page.route('**/_api/session-new', async (route) => {
		calls += 1;
		await answered;
		await route.fulfill({ json: { ok: true, result: 's-2026-10-02-7z63as  a long sitting  (active)' } });
	});
	await page.goto('/master/drafting/main');
	await openPicker(page);
	await page.getByTestId('session-new').click();
	const field = page.getByTestId('session-new-title');
	await field.fill('a long sitting');
	await field.press('Enter');
	const status = page.getByTestId('session-new-status');
	await expect(status).toHaveText('opening “a long sitting”…');
	await expect(field).toBeDisabled();
	await expect(field).toHaveValue('a long sitting');
	release();
	await expect(status).toHaveCount(0);
	expect(calls).toBe(1);
});

test('a session the publisher refuses to open says why, and keeps what was typed', async ({ page }) => {
	await writes(page, ['session-new']);
	await page.route('**/_api/session-new', (route) =>
		route.fulfill({ status: 409, json: { error: { code: 'refused', message: 'no author name: set one in Settings' } } })
	);
	await page.goto('/master/drafting/main');
	await openPicker(page);
	await page.getByTestId('session-new').click();
	const field = page.getByTestId('session-new-title');
	await field.fill('a sitting');
	await field.press('Enter');
	await expect(page.getByTestId('session-new-status')).toHaveText('no author name: set one in Settings');
	await expect(field).toBeEnabled();
	await expect(field).toHaveValue('a sitting');
});

test('the session picker is not in the column', async ({ page }) => {
	await page.goto('/master/drafting/main');
	const column = page.locator('.panel .sections');
	await expect(column).toBeVisible();
	await expect(column.getByTestId('session-list')).toHaveCount(0);
	await expect(page.getByTestId('session-picker')).toHaveCount(0);
	await openPicker(page);
	await expect(page.getByTestId('session-list')).toBeVisible();
	await expect(column.getByTestId('session-picker')).toHaveCount(0);
});

test.describe('the contents', () => {
	test('the outline is the focused pane\'s document\'s, beneath the documents, and absent for anything else', async ({ page }) => {
		await page.goto('/master/drafting/main' + beside('/node/sy-0003'));
		const contents = page.getByRole('navigation', { name: 'Contents' });
		await expect(contents).toBeVisible();
		await expect(page.getByTestId('outline-divider')).toBeVisible();
		// the tree follows the focused pane: a node has none, and the document's comes back with the focus
		await pane(page, 1).locator('.fragment').first().click();
		await expect(contents).toHaveCount(0);
		await pane(page, 0).locator('.fragment').first().click();
		await expect(contents).toBeVisible();
		// and a node alone shows neither the tree nor its divider, and the documents take the column
		await page.goto('/node/sy-0002');
		await expect(pane(page, 0).locator('.fragment').first()).toBeVisible();
		await expect(contents).toHaveCount(0);
		await expect(page.getByTestId('outline-divider')).toHaveCount(0);
	});

	test('the contents tree is in document order and stops above paragraph units', async ({ page }) => {
		await page.goto('/master/drafting/main');
		const entries = page.getByRole('navigation', { name: 'Contents' }).locator('a');
		await expect(entries.first()).toContainText('Introduction');
		const texts = await entries.allInnerTexts();
		expect(texts.join(' | ')).toContain('Results');
		expect(texts.join(' | ')).not.toContain('paragraph');
	});

	test('a contents entry scrolls the document instead of navigating away', async ({ page }) => {
		await page.goto('/master/drafting/main');
		await page.getByRole('navigation', { name: 'Contents' }).getByRole('link', { name: /Results/ }).click();
		await expect(page).toHaveURL(/\/master\/drafting\/main#sy-0200$/);
		await expect(page.locator('#sy-0200')).toBeInViewport();
	});

	test('the contents always mark where the reader is, and the mark follows the scroll both ways', async ({ page }) => {
		// the mark moves with the reader's scroll, not with the URL's hash, and exactly one entry carries it, from before any scrolling (DR-112)
		await page.setViewportSize({ width: 1280, height: 500 });
		await page.goto('/master/drafting/main');
		const contents = page.getByRole('navigation', { name: 'Contents' });
		const current = contents.locator('a[aria-current]');
		await expect(current).toHaveCount(1);
		const first = await current.innerText();
		const target = (await contents.locator('a').last().getAttribute('href'))!.split('#')[1];
		await page.evaluate((id) => document.getElementById(id)?.scrollIntoView({ block: 'start' }), target);
		await expect.poll(() => current.innerText()).not.toBe(first);
		await expect(current).toHaveCount(1);
		// scrolling back returns it; the document scrolls in its pane, not the window
		await scrollPane(page, 0, 'top');
		await expect.poll(() => current.innerText()).toBe(first);
	});

	test('the outline scrolls under the wheel', async ({ page }) => {
		// a box inside it that took the wheel and had nothing of its own to scroll left it stuck, though a scroll from script moved it
		await page.setViewportSize({ width: 1440, height: 330 });
		await page.goto('/master/drafting/main');
		const outline = page.getByTestId('outline');
		await expect(outline.getByRole('navigation', { name: 'Contents' })).toBeVisible();
		expect(await outline.evaluate((e) => e.scrollHeight - e.clientHeight), 'the outline overflows its part, px').toBeGreaterThan(20);
		const box = (await outline.boundingBox())!;
		await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
		await page.mouse.wheel(0, 200);
		await expect.poll(() => outline.evaluate((e) => e.scrollTop)).toBeGreaterThan(0);
	});

	test('the line above the outline moves, is remembered, and the documents and the outline scroll apart', async ({ page }) => {
		await page.setViewportSize({ width: 1440, height: 520 });
		await page.goto('/master/drafting/main');
		const line = page.getByTestId('outline-divider');
		const docs = page.getByTestId('docs-part');
		const outline = page.getByTestId('outline');
		await expect(line).toBeVisible();
		await expect(outline.getByRole('navigation', { name: 'Contents' })).toBeVisible();
		// measured once the column has settled, so the press lands on the line
		await line.hover();
		const before = (await docs.boundingBox())!.height;
		const at = (await line.boundingBox())!;
		await page.mouse.move(at.x + at.width / 2, at.y + at.height / 2);
		await expect(line).toHaveCSS('cursor', 'row-resize');
		await page.mouse.down();
		const start = await line.getAttribute('aria-valuenow');
		await page.mouse.move(at.x + at.width / 2, at.y - 80, { steps: 5 });
		// the moves are drawn a frame at a time, so the drop waits for the line to have followed them, as a hand does
		await expect.poll(() => line.getAttribute('aria-valuenow')).not.toBe(start);
		await expect.poll(async () => Number(await line.getAttribute('aria-valuenow'))).toBeLessThan(40);
		await page.mouse.up();
		await expect.poll(async () => (await docs.boundingBox())!.height).toBeLessThan(before - 40);
		const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('arras.prefs') ?? '{}').outline);
		expect(stored).toBeLessThan(0.55);
		await page.reload();
		await expect.poll(async () => (await page.getByTestId('docs-part').boundingBox())!.height).toBeLessThan(before - 40);
		// each scrolls in its own box: the outline's last entry is reached by scrolling the outline
		for (const part of [docs, outline]) expect(await part.evaluate((e) => getComputedStyle(e).overflowY)).toBe('auto');
		const last = outline.getByRole('navigation', { name: 'Contents' }).locator('a').last();
		await last.scrollIntoViewIfNeeded();
		await expect(last).toBeInViewport();
		// the keys move it too
		await line.focus();
		const now = Number(await line.getAttribute('aria-valuenow'));
		await page.keyboard.press('ArrowDown');
		await expect(line).toHaveAttribute('aria-valuenow', String(now + 3));
	});

	test("the column's edge turns blue under the pointer, moves sideways, and is remembered", async ({ page }) => {
		await page.setViewportSize({ width: 1440, height: 700 });
		await page.goto('/master/drafting/main');
		const edge = page.getByTestId('column-divider');
		const column = page.getByTestId('column');
		await expect(edge).toBeVisible();
		const before = (await column.boundingBox())!.width;
		const at = (await edge.boundingBox())!;
		// the line is the column's own edge, with room inside it to take hold of
		expect(Math.abs(at.x + at.width - before)).toBeLessThanOrEqual(1);
		const line = () => edge.evaluate((e) => getComputedStyle(e, '::before').borderRightColor);
		const resting = await line();
		await page.mouse.move(at.x + at.width / 2, at.y + 200);
		await expect(edge).toHaveCSS('cursor', 'col-resize');
		// under the pointer the line takes the link's blue, as the outline's does
		await expect.poll(line).not.toBe(resting);
		expect(await line()).toBe(await page.getByTestId('outline-divider').evaluate((e) => {
			e.classList.add('moving');
			const c = getComputedStyle(e, '::before').borderTopColor;
			e.classList.remove('moving');
			return c;
		}));
		await page.mouse.down();
		await page.mouse.move(at.x + at.width / 2 + 120, at.y + 200, { steps: 5 });
		await expect.poll(async () => Number(await edge.getAttribute('aria-valuenow'))).toBeGreaterThan(before + 80);
		await page.mouse.up();
		await expect.poll(async () => (await column.boundingBox())!.width).toBeGreaterThan(before + 80);
		const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('arras.prefs') ?? '{}').column);
		expect(stored).toBeGreaterThan(before + 80);
		await page.reload();
		await expect.poll(async () => (await page.getByTestId('column').boundingBox())!.width).toBeGreaterThan(before + 80);
		// the keys move it too
		await edge.focus();
		const now = Number(await edge.getAttribute('aria-valuenow'));
		await page.keyboard.press('ArrowLeft');
		await expect(edge).toHaveAttribute('aria-valuenow', String(now - 16));
		// folded, the column has no edge to drag
		await page.getByTestId('panel-fold').click();
		await expect(edge).toHaveCount(0);
	});
});

test('a session rename shows at once', async ({ page }) => {
	await writes(page, ['session-rename']);
	// the publisher does not answer until the name has shown, so a name that waited for it never would
	let shown = () => {};
	const nameShown = new Promise<void>((r) => (shown = r));
	await page.route('**/_api/session-rename', async (route) => {
		await nameShown;
		await route.fulfill({ json: { ok: true, result: '' } });
	});
	await page.goto('/master/drafting/main');
	await pickSession(page, REFEREE);
	await openPicker(page);
	// the verbs stand over a row only while the pointer is on it, the selected row included
	await expect(page.getByTestId(`session-edit-${REFEREE}`)).toBeHidden();
	await page.getByTestId(`session-${REFEREE}`).hover();
	await page.getByTestId(`session-edit-${REFEREE}`).click();
	await page.getByTestId(`session-rename-${REFEREE}`).fill('the second reading');
	await page.getByTestId(`session-rename-${REFEREE}`).press('Enter');
	await expect(page.getByTestId(`session-${REFEREE}`)).toContainText('the second reading');
	await expect(page.getByTestId('session-footer-name')).toHaveText('the second reading');
	const answered = page.waitForResponse('**/_api/session-rename');
	shown();
	await answered;
});

test('⟳ reopens and selects', async ({ page }) => {
	await writes(page, ['session-reopen']);
	let reopened = '';
	await page.route('**/_api/session-reopen', async (route) => {
		reopened = route.request().postDataJSON().session;
		await route.fulfill({ json: { ok: true, result: '' } });
	});
	await page.goto('/master/drafting/main');
	await openPicker(page);
	await page.getByTestId('show-closed').click();
	await page.getByTestId(`session-reopen-${QUICK}`).click();
	await expect.poll(() => reopened).toBe(QUICK);
	await expect(page.getByTestId('session-footer-name')).toHaveText('quick');
	await expect(page.getByTestId('session-picker')).toHaveCount(0);
});

test('accepting needs no session', async ({ page }) => {
	// accepting and incorporating a pull name no session, so an amber footer must not mean nothing can be written
	await writes(page, ['review-accept']);
	let accepted: string[] = [];
	await page.route('**/_api/review-accept', async (route) => {
		accepted = route.request().postDataJSON().keys;
		await route.fulfill({ json: { ok: true, result: 'accepted 1 of 1', accepted, refused: [] } });
	});
	await page.goto('/review');
	await expect(page.getByTestId('session-footer')).toHaveAttribute('aria-label', /^not writing in a session/);
	const accept = page.locator('[data-testid="review-row"][data-key="sy-0001"]').getByTestId('review-accept');
	await expect(accept).toBeEnabled();
	await accept.click();
	await expect.poll(() => accepted).toEqual(['sy-0001']);
});

test.describe('sessions', () => {
	test('the chosen session is still chosen after a load', async ({ page }) => {
		await page.goto('/master/drafting/main');
		await pickSession(page, REFEREE);
		await expect(page.getByTestId('session-footer')).toHaveAttribute('aria-label', /^writing in /);
		await page.reload();
		await expect(page.getByTestId('session-footer')).toHaveAttribute('aria-label', /^writing in /);
		await expect(pane(page, 1).getByTestId('chat')).toBeVisible();
	});

	test('a stored session the corpus no longer lists is let go', async ({ page }) => {
		await page.addInitScript(() => localStorage.setItem('arras.session-view', JSON.stringify({ selected: 's-gone', view: 'all', showClosed: false })));
		await page.goto('/master/drafting/main');
		await expect(page.getByTestId('session-footer-lead')).toHaveText('not writing in a session');
		await expect.poll(() => page.evaluate(() => JSON.parse(localStorage.getItem('arras.session-view') ?? '{}').selected)).toBeFalsy();
	});

	test('selecting a session narrows nothing on the page; the pane alone hides its annotations', async ({ page }) => {
		await page.goto('/node/sy-0002');
		const counted = pane(page, 0).locator('.fragment mark.annotation-label');
		await expect(counted).toHaveCount(1);
		await pickSession(page, REFEREE);
		await expect(counted).toHaveCount(1);
		// the pane's `a` draws no annotation at all in it, whatever is selected
		await pane(page, 0).locator('.fragment').first().press('a');
		await expect(pane(page, 0).locator('.fragment mark.annotation:not(.hidden)')).toHaveCount(0);
		await pane(page, 0).locator('.fragment').first().press('a');
		await expect(counted).toHaveCount(1);
	});
});

test.describe('sections', () => {
	test('the column lists no results: a result is read where it lives, and found by ⌘K', async ({ page }) => {
		await page.goto('/node/sy-0003');
		await expect(page.getByTestId('docs-tree')).toBeVisible();
		await expect(page.getByTestId('nodes-toggle')).toHaveCount(0);
		await expect(page.getByTestId('nodes-list')).toHaveCount(0);
		// found by ⌘K, which is search's one way in
		await expect(page.getByTestId('column-search')).toHaveCount(0);
	});

	test('the panel never repeats the strip', async ({ page }) => {
		for (const path of ['/threads', '/tags', '/loose']) {
			await page.goto(path);
			await expect(page.locator('.panel .rail-label', { hasText: /^Views$/ })).toHaveCount(0);
			// the documents stand there instead, with the contents folded under the open one
			await expect(page.getByTestId('docs-tree')).toBeVisible();
		}
		// the Library fills the panel with its own filters, which is the other half of the same rule
		await page.goto('/review/library');
		await expect(page.locator('.panel .rail-label', { hasText: /^Views$/ })).toHaveCount(0);
		await expect(page.getByTestId('show-proposed')).toBeVisible();
	});
});
