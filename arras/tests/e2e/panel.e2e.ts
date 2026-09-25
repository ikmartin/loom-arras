// The side panel: the documents and their contents, the Nodes and Library sections, the write target pinned in a footer, the session list in a picker it opens, and the annotation filter in the rail above the content. Each test is named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { beside, pane, scrollPane } from '../workspace';
import { openPicker, pickSession } from '../picker';
import { QUICK, REFEREE, serve } from '../manifest';

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

/** Advertise a write API with `caps`; the static server serves none, and the controls appear only where one is. */
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
	// choosing it opened its Chat, whose tab names the item that is open, a different question from where writes go
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

test.describe('the contents', () => {
	test('the contents hang open under the document in the focused pane, and are absent for anything else', async ({ page }) => {
		await page.goto('/master/main' + beside('/node/sy-0003'));
		const contents = page.getByRole('navigation', { name: 'Contents' });
		await expect(contents).toBeVisible();
		await expect(page.getByTestId('contents-toggle')).toHaveAttribute('aria-expanded', 'true');
		// the tree follows the focused pane: a node has none, and the document's comes back with the focus
		await pane(page, 1).locator('.fragment').first().click();
		await expect(contents).toHaveCount(0);
		await pane(page, 0).locator('.fragment').first().click();
		await expect(contents).toBeVisible();
		// and a node alone shows neither the tree nor its toggle
		await page.goto('/node/sy-0002');
		await expect(pane(page, 0).locator('.fragment').first()).toBeVisible();
		await expect(contents).toHaveCount(0);
		await expect(page.getByTestId('contents-toggle')).toHaveCount(0);
	});

	test('the contents tree is in document order and stops above paragraph units', async ({ page }) => {
		await page.goto('/master/main');
		const entries = page.getByRole('navigation', { name: 'Contents' }).locator('a');
		await expect(entries.first()).toContainText('Introduction');
		const texts = await entries.allInnerTexts();
		expect(texts.join(' | ')).toContain('Results');
		expect(texts.join(' | ')).not.toContain('paragraph');
	});

	test('a contents entry scrolls the document instead of navigating away', async ({ page }) => {
		await page.goto('/master/main');
		await page.getByRole('navigation', { name: 'Contents' }).getByRole('link', { name: /Results/ }).click();
		await expect(page).toHaveURL(/\/master\/main#sy-0200$/);
		await expect(page.locator('#sy-0200')).toBeInViewport();
	});

	test('the contents always mark where the reader is, and the mark follows the scroll both ways', async ({ page }) => {
		// the mark moves with the reader's scroll, not with the URL's hash, and exactly one entry carries it, from before any scrolling (DR-112)
		await page.setViewportSize({ width: 1280, height: 500 });
		await page.goto('/master/main');
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

test.describe('sessions', () => {
	test('the chosen session is still chosen after a load', async ({ page }) => {
		await page.goto('/master/main');
		await pickSession(page, REFEREE);
		await expect(page.getByTestId('session-footer')).toHaveAttribute('aria-label', /^annotations are written into/);
		await page.reload();
		await expect(page.getByTestId('session-footer')).toHaveAttribute('aria-label', /^annotations are written into/);
		await expect(pane(page, 1).getByTestId('chat')).toBeVisible();
	});

	test('a stored session the corpus no longer lists is let go', async ({ page }) => {
		await page.addInitScript(() => localStorage.setItem('arras.session-view', JSON.stringify({ selected: 's-gone', view: 'all', showClosed: false })));
		await page.goto('/master/main');
		await expect(page.getByTestId('session-footer-name')).toHaveText('no session selected');
		await expect.poll(() => page.evaluate(() => JSON.parse(localStorage.getItem('arras.session-view') ?? '{}').selected)).toBeFalsy();
	});

	test('one selection governs the page, and the view filters what the page draws', async ({ page }) => {
		// the fixture's two sessions, with the closed one opened and one annotation on sy-0002 moved into it, so that one key carries work from two sessions: the state the filter exists for, which the fixture does not happen to contain
		await serve(page, (m) => {
			for (const s of m.sessions) if (s.id === QUICK) s.state = 'open';
			m.annotations['a-2026-09-16-0006'].run = QUICK;
		});
		await page.goto('/node/sy-0002');
		// nothing is selected at rest and the page shows everything
		await expect(page.getByTestId('show-all')).toHaveAttribute('class', /on/);
		await expect(page.getByTestId('show-current')).toBeDisabled();

		// sy-0002 is now annotated from both sessions: its comment with no mark, from the referee, is counted beside its label
		const counted = pane(page, 0).locator('.fragment button.comment-count');
		await expect(counted).toHaveCount(1);

		// selecting a session does not narrow the page by itself: the selection is the write target, the view is the filter
		await pickSession(page, QUICK);
		await expect(counted).toHaveCount(1);
		// and the picker still lists every session, because it is how a reader navigates
		await openPicker(page);
		await expect(page.getByTestId('session-list').locator('li')).toHaveCount(2);
		await page.keyboard.press('Escape');

		// narrowing is the toggle's job, and it is available now that something is selected: the referee's comment goes
		await page.getByTestId('show-current').click();
		await expect(counted).toHaveCount(0);

		// and back to everything
		await page.getByTestId('show-all').click();
		await expect(counted).toHaveCount(1);
	});
});

test.describe('sections', () => {
	test('the panel has a Nodes section, folded, narrowed by what is typed', async ({ page }) => {
		await page.goto('/node/sy-0003');
		await expect(page.getByTestId('nodes-list')).toHaveCount(0); // folded: a corpus of a hundred results would otherwise be the panel
		await page.getByTestId('nodes-toggle').click();
		await expect(page.getByTestId('nodes-list')).toBeVisible();
		await page.getByTestId('nodes-filter').fill('parity');
		const rows = page.getByTestId('nodes-list').locator('li a');
		await expect(rows.first()).toContainText('sy-0003');
		await expect(rows).toHaveCount(1);
		await page.getByTestId('nodes-filter').fill('zzz');
		await expect(page.getByTestId('nodes-list')).toContainText('nothing matches');
	});

	test('the panel never repeats the strip', async ({ page }) => {
		for (const path of ['/threads', '/tags', '/loose']) {
			await page.goto(path);
			await expect(page.locator('.panel .rail-label', { hasText: /^Views$/ })).toHaveCount(0);
			// the documents stand there instead, with the contents folded under the open one
			await expect(page.getByTestId('docs-drafts')).toBeVisible();
		}
		// the Library fills the panel with its own filters, which is the other half of the same rule
		await page.goto('/library');
		await expect(page.locator('.panel .rail-label', { hasText: /^Views$/ })).toHaveCount(0);
		await expect(page.getByTestId('show-proposed')).toBeVisible();
	});
});
