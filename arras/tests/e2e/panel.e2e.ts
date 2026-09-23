// The side panel (plan 0.13.3 phase 1): the write target pinned in a footer, the session list in a picker it opens, and the annotation filter in the rail above the content. Each test is named for the rule in the plan's Tests section it holds.
import { expect, test, type Page } from '@playwright/test';
import { beside, pane } from '../workspace';
import { readFileSync } from 'node:fs';
import { openPicker, pickSession } from '../picker';

const manifest = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8'));
const REFEREE = 's-2026-09-16-0001';
const QUICK = 's-2026-09-15-0001';

/** Serve the fixture with `edit` applied to its manifest. */
async function serve(page: Page, edit: (m: typeof manifest) => void): Promise<void> {
	await page.route('**/build/manifest.json', async (route) => {
		const m = JSON.parse(JSON.stringify(manifest));
		edit(m);
		await route.fulfill({ json: m });
	});
}

/** Select an element's words as a reader would, and let go. */
async function selectWithin(at: import('@playwright/test').Locator): Promise<void> {
	await at.evaluate((node) => {
		const range = document.createRange();
		range.selectNodeContents(node);
		const sel = window.getSelection();
		sel?.removeAllRanges();
		sel?.addRange(range);
		node.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
	});
}

/** Advertise a write API with `caps`; `vite preview` serves none, and the controls appear only where one is. */
async function writes(page: Page, caps: string[]): Promise<void> {
	await page.route('**/_api', (route) => route.fulfill({ json: { write_api: 1, capabilities: caps, token: 't' } }));
}

test('the write target is stated once', async ({ page }) => {
	// a title no annotation or author shares, so a count of it is a count of the places that name the session
	await serve(page, (m) => {
		m.sessions.find((s: { id: string }) => s.id === REFEREE).title = 'the refereeing sitting';
	});
	// a document and a node beside it: two items, two panes, and still one place that says where writes go
	await page.goto('/master/main' + beside('/node/sy-0003'));
	await expect(pane(page, 1)).toBeVisible();
	await pickSession(page, REFEREE);
	await expect(page.getByTestId('session-footer-name')).toHaveText('the refereeing sitting');
	// choosing it opened its discussion, whose tab names the item that is open, a different question from where writes go
	const naming = await page.evaluate(
		() =>
			[...document.querySelectorAll('body *')].filter(
				(el) => !el.closest('[data-testid="item-tab"]') && [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent?.includes('the refereeing sitting'))
			).length
	);
	expect(naming).toBe(1);
});

test('annotations are filtered from one control', async ({ page }) => {
	for (const at of ['/master/main' + beside('/node/sy-0003'), '/node/sy-0002' + beside('/context/sy-0002'), '/library/Kre99']) {
		await page.goto(at);
		await expect(page.getByTestId('reading-rail')).toBeVisible();
		await expect(page.getByTestId('show-current')).toHaveCount(1);
		await expect(page.getByRole('group', { name: 'which annotations the page shows' })).toHaveCount(1);
		// and the picker, which lists sessions, does not also filter what the page draws
		await openPicker(page);
		await expect(page.getByTestId('show-current')).toHaveCount(1);
		await expect(page.getByTestId('session-picker').getByTestId('show-current')).toHaveCount(0);
		await page.keyboard.press('Escape');
	}
});

test('a refusal names its condition', async ({ page }) => {
	await writes(page, ['comment']);
	await page.goto('/node/sy-0002');
	// a selection on the node offers to annotate it, as on a paper's page
	const words = pane(page, 0).locator('.fragment .env[data-id="sy-0002"] p[data-src]').first();
	await expect(words).toBeVisible();
	await selectWithin(words);
	await page.getByTestId('annotate-offer').click();
	await page.getByTestId('note-body').fill('Say which orbit.');
	const open = page.getByTestId('note-submit');
	await expect(open).toBeDisabled();
	// the sentence `writable()` returns, beside the control it refuses, for as long as the refusal holds
	await expect(page.getByTestId('no-session-tip')).toHaveText('No session selected: either select a session or start a new session.');
	// and the footer carries only the state: refused, in its own tone, without the sentence
	const footer = page.getByTestId('session-footer');
	await expect(footer).toHaveAttribute('aria-label', /^annotations cannot be written/);
	await expect(page.getByTestId('session-footer-name')).toHaveText('no session selected');
	await expect(page.locator('.footer.refused')).toHaveCount(1);
	await pickSession(page, REFEREE);
	await expect(open).toBeEnabled();
	await expect(page.getByTestId('no-session-tip')).toHaveCount(0);
	await expect(footer).toHaveAttribute('aria-label', 'annotations are written into referee');
	await expect(page.locator('.footer.refused')).toHaveCount(0);
});

test('the session picker is not in the column', async ({ page }) => {
	await page.goto('/master/main');
	const column = page.locator('.panel .sections');
	await expect(column).toBeVisible();
	await expect(column.getByTestId('session-list')).toHaveCount(0);
	await expect(page.getByTestId('session-picker')).toHaveCount(0);
	await openPicker(page);
	await expect(page.getByTestId('session-list')).toBeVisible();
	await expect(column.getByTestId('session-picker')).toHaveCount(0);
});

test('the contents hang open under a document on screen, and nowhere else', async ({ page }) => {
	await page.goto('/master/main');
	await expect(page.getByRole('navigation', { name: 'Contents' })).toBeVisible();
	await expect(page.getByTestId('contents-toggle')).toHaveAttribute('aria-expanded', 'true');
	await page.goto('/node/sy-0002');
	await expect(pane(page, 0).locator('.fragment').first()).toBeVisible();
	await expect(page.getByRole('navigation', { name: 'Contents' })).toHaveCount(0);
	await expect(page.getByTestId('contents-toggle')).toHaveCount(0);
});

test('the contents bar follows the reader', async ({ page }) => {
	// DR-112 was the only record of this: the mark moves with the reader's scroll, and exactly one entry carries it
	await page.setViewportSize({ width: 1280, height: 500 });
	await page.goto('/master/main');
	const contents = page.getByRole('navigation', { name: 'Contents' });
	await expect(contents.locator('a[aria-current]')).toHaveCount(1);
	const first = await contents.locator('a[aria-current]').innerText();
	const last = contents.locator('a').last();
	const target = (await last.getAttribute('href'))!.split('#')[1];
	await page.evaluate((id) => document.getElementById(id)?.scrollIntoView({ block: 'start' }), target);
	await expect(contents.locator('a[aria-current]')).toHaveCount(1);
	await expect.poll(() => contents.locator('a[aria-current]').innerText()).not.toBe(first);
});

test('a session rename shows at once', async ({ page }) => {
	await writes(page, ['session-rename']);
	// the publisher takes its time; the name must not wait for it
	await page.route('**/_api/session-rename', async (route) => {
		await new Promise((r) => setTimeout(r, 3000));
		await route.fulfill({ json: { ok: true, result: '' } });
	});
	await page.goto('/master/main');
	await pickSession(page, REFEREE);
	await openPicker(page);
	// the verbs stand over a row only while the pointer is on it, the selected row included
	await expect(page.getByTestId(`session-edit-${REFEREE}`)).toBeHidden();
	await page.getByTestId(`session-${REFEREE}`).hover();
	await page.getByTestId(`session-edit-${REFEREE}`).click();
	await page.getByTestId(`session-rename-${REFEREE}`).fill('the second reading');
	await page.getByTestId(`session-rename-${REFEREE}`).press('Enter');
	await expect(page.getByTestId(`session-${REFEREE}`)).toContainText('the second reading', { timeout: 1000 });
	await expect(page.getByTestId('session-footer-name')).toHaveText('the second reading', { timeout: 1000 });
});

test('⟳ reopens and selects', async ({ page }) => {
	await writes(page, ['session-reopen']);
	let reopened = '';
	await page.route('**/_api/session-reopen', async (route) => {
		reopened = route.request().postDataJSON().session;
		await route.fulfill({ json: { ok: true, result: '' } });
	});
	await page.goto('/master/main');
	await openPicker(page);
	await page.getByTestId('show-closed').click();
	await page.getByTestId(`session-reopen-${QUICK}`).click();
	await expect.poll(() => reopened).toBe(QUICK);
	await expect(page.getByTestId('session-footer-name')).toHaveText('quick');
	await expect(page.getByTestId('session-picker')).toHaveCount(0);
});

test('a review decision needs no session', async ({ page }) => {
	// review decisions and incorporating a pull name no session, so an amber footer must not mean nothing can be written
	await serve(page, (m) => {
		m.unresolved = [{ key: 'sy-0001', status: 'needs-review', cause: 'incoming-pull', pull: 'b'.repeat(40), changed_text: true, local_changed: false, invalidated: false }];
	});
	await writes(page, ['review-decision']);
	let decided = '';
	await page.route('**/_api/review-decision', async (route) => {
		decided = route.request().postDataJSON().key;
		await route.fulfill({ json: { ok: true, result: '' } });
	});
	await page.goto('/review?show=needs-review');
	await expect(page.getByTestId('session-footer')).toHaveAttribute('aria-label', /^annotations cannot be written/);
	await page.getByRole('button', { name: 'Start review' }).click();
	const ok = page.getByRole('button', { name: 'OK', exact: true });
	await expect(ok).toBeEnabled();
	await ok.click();
	await expect.poll(() => decided).toBe('sy-0001');
});
