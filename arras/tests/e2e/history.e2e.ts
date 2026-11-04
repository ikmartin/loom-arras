// A draft's history menu (plan 0.20.6), on the fixture: main.tex has three landmarks, widgets-v1 to -v3, and one agent copy, aidoc.tex. A landmark is shown read-only in the draft's own tab, at the result the reader was at; compare is started from the menu and nowhere else.
import { expect, test, type Page } from '@playwright/test';
import { beside, openHere, pane } from '../workspace';
import { serve } from '../manifest';

const tabs = (page: Page, index: number) => pane(page, index).getByTestId('item-tab');

/** Open a pane's history menu. */
async function history(page: Page, index = 0): Promise<void> {
	await pane(page, index).getByTestId('toolbar-history').click();
	await expect(page.getByTestId('history-menu')).toBeVisible();
}

test('the menu lists the live text and the landmarks newest first, each with its compare, then the agent copy', async ({ page }) => {
	await page.goto('/master/drafting/main');
	await history(page);
	const menu = page.getByTestId('history-menu');
	await expect(menu.locator('[role="menuitemradio"]')).toHaveText([/live text/, /widgets-v3\s*step 5/, /widgets-v2\s*step 3/, /widgets-v1\s*step 1/]);
	await expect(page.getByTestId('history-version-live')).toHaveAttribute('aria-checked', 'true');
	// every version but the one shown can be compared, and the copy below a rule
	await expect(page.getByTestId('history-compare-live')).toHaveCount(0);
	for (const v of ['widgets-v3', 'widgets-v2', 'widgets-v1', 'aidoc']) await expect(page.getByTestId(`history-compare-${v}`)).toBeVisible();
	// the arrow keys pass through both lines of a row
	await expect(page.getByTestId('history-version-live')).toBeFocused();
	await page.keyboard.press('ArrowDown');
	await expect(page.getByTestId('history-version-widgets-v3')).toBeFocused();
	await page.keyboard.press('ArrowDown');
	await expect(page.getByTestId('history-compare-widgets-v3')).toBeFocused();
});

test('a version kept at an act is listed with the rest, named by the act', async ({ page }) => {
	await serve(page, (m) => {
		m.canon.push({ ...structuredClone(m.canon[1]), path: '.loom/history/0007-main-before-adopt-aidoc/main-before-adopt-aidoc.tex', stem: 'main-before-adopt-aidoc', name: 'main-before-adopt-aidoc', step: '0007', kept_for: 'adopt', message: 'Before taking changes from the copy “aidoc”' });
	});
	await page.goto('/master/drafting/main');
	await history(page);
	await expect(page.getByTestId('history-version-main-before-adopt-aidoc')).toContainText('Before taking changes from the copy “aidoc”');
	await expect(page.getByTestId('history-menu').locator('[role="menuitemradio"]').nth(1)).toContainText('Before taking changes');
});

test('a draft with no landmarks and no copies, and a landmark no live draft leads to, have no menu', async ({ page }) => {
	await serve(page, (m) => delete m.canon[0].in);
	await page.goto('/master/drafting/talk');
	await expect(pane(page, 0).getByTestId('item-controls')).toBeVisible();
	await expect(pane(page, 0).getByTestId('toolbar-history')).toHaveCount(0);
	await page.goto('/canon/widgets-v1');
	await expect(tabs(page, 0)).toContainText('widgets-v1 @1');
	await expect(pane(page, 0).getByTestId('toolbar-history')).toHaveCount(0);
});

test('a landmark is shown in the draft’s own tab, read-only, at the result the reader was at, and the live text is one choice back', async ({ page }) => {
	await page.goto('/master/drafting/main' + beside('/node/sy-0002'));
	await pane(page, 0).locator('.fragment').first().click();
	await expect(tabs(page, 0)).toHaveCount(1);
	// the reader at Theorem 3
	await pane(page, 0).locator('#sy-0003').evaluate((el) => el.scrollIntoView({ block: 'start' }));
	await expect(pane(page, 0).locator('#sy-0003')).toBeInViewport();
	await history(page);
	await page.getByTestId('history-version-widgets-v2').click();
	// the same tab, in the same place, turned
	await expect(tabs(page, 0)).toHaveCount(1);
	await expect(tabs(page, 0)).toContainText('main.tex · widgets-v2');
	await expect(page).toHaveURL(/\/canon\/widgets-v2/);
	await expect(pane(page, 0).locator('#sy-0003')).toBeInViewport();
	// a landmark is read, not annotated: no marks, no annotating tools
	await expect(pane(page, 0).locator('.fragment mark.annotation')).toHaveCount(0);
	await expect(pane(page, 0).getByTestId('tool-select')).toHaveCount(0);
	// its own menu is the draft's, with it checked
	await history(page);
	await expect(page.getByTestId('history-version-widgets-v2')).toHaveAttribute('aria-checked', 'true');
	await page.keyboard.press('Escape');
	// back, by the bar's one choice
	await page.getByTestId('history-live').click();
	await expect(tabs(page, 0)).toContainText('main.tex');
	await expect(tabs(page, 0)).not.toContainText('widgets');
	await expect(page).toHaveURL(/\/master\/drafting\/main/);
	await expect(pane(page, 0).locator('#sy-0003')).toBeInViewport();
	// and by the menu's
	await history(page);
	await page.getByTestId('history-version-widgets-v1').click();
	await expect(tabs(page, 0)).toContainText('main.tex · widgets-v1');
	await history(page);
	await page.getByTestId('history-version-live').click();
	await expect(page).toHaveURL(/\/master\/drafting\/main/);
});

test('compare with a landmark opens it beside and compares the two; stop, or the same line again, ends it', async ({ page }) => {
	await page.goto('/master/drafting/main');
	await history(page);
	await page.getByTestId('history-compare-widgets-v1').click();
	await expect(tabs(page, 1)).toContainText('main.tex · widgets-v1');
	await expect(page).toHaveURL(/compare=1/);
	await expect(page.getByTestId('compare-count')).toBeVisible();
	// the pane it was chosen from keeps the focus, and its line says what it compares with
	await expect(pane(page, 0)).toHaveClass(/focused/);
	await history(page);
	await expect(page.getByTestId('history-compare-widgets-v1')).toHaveAttribute('aria-checked', 'true');
	await page.getByTestId('history-compare-widgets-v1').click();
	await expect(page.getByTestId('compare-count')).toHaveCount(0);
	await expect(page).not.toHaveURL(/compare=/);
	// again, and stopped from the toolbar
	await history(page);
	await page.getByTestId('history-compare-widgets-v1').click();
	await expect(page.getByTestId('compare-count')).toBeVisible();
	await page.getByTestId('compare-stop').click();
	await expect(page.getByTestId('compare-count')).toHaveCount(0);
});

test("compare with the agent's copy reads its changes, and the copy's own menu compares it with its source", async ({ page }) => {
	await page.goto('/master/drafting/main');
	await history(page);
	await page.getByTestId('history-compare-aidoc').click();
	await expect(tabs(page, 1)).toContainText('aidoc.tex');
	await expect(page.getByTestId('compare-count')).toHaveText('6 differences');
	await page.getByTestId('compare-stop').click();
	// from the copy: its one line, its source
	await pane(page, 1).locator('.fragment').first().click();
	await history(page, 1);
	const menu = page.getByTestId('history-menu');
	await expect(menu.locator('[role^="menuitem"]')).toHaveCount(1);
	await expect(page.getByTestId('history-compare-main')).toHaveText(/compare with main\.tex/);
	await page.getByTestId('history-compare-main').click();
	await expect(page.getByTestId('compare-count')).toHaveText('6 differences');
});

test('a landmark moved into the other pane by compare, when it stood behind the draft in this one', async ({ page }) => {
	await page.goto('/master/drafting/main');
	await expect(pane(page, 0).locator('.fragment').first()).toBeVisible();
	await openHere(page, '/canon/widgets-v2');
	await expect(tabs(page, 0)).toHaveCount(2);
	await openHere(page, '/master/drafting/main');
	await expect(pane(page, 0).getByTestId('toolbar-history')).toBeVisible();
	await expect(tabs(page, 0).first().getByRole('tab')).toHaveAttribute('aria-selected', 'true');
	await history(page);
	await page.getByTestId('history-compare-widgets-v2').click();
	await expect(tabs(page, 0)).toHaveCount(1);
	await expect(tabs(page, 1)).toContainText('main.tex · widgets-v2');
	await expect(page.getByTestId('compare-count')).toBeVisible();
});

test('in a window too narrow for two panes, compare is greyed with its reason', async ({ page }) => {
	await page.setViewportSize({ width: 600, height: 800 });
	await page.goto('/master/drafting/main');
	await history(page);
	const line = page.getByTestId('history-compare-widgets-v1');
	await expect(line).toHaveAttribute('aria-disabled', 'true');
	await expect(line).toHaveAttribute('title', /too narrow/);
	await expect(page.getByTestId('history-compare-aidoc')).toHaveAttribute('aria-disabled', 'true');
});

test('a landmark opened from Review › History carries its draft’s menu', async ({ page }) => {
	await page.goto('/review/history');
	await page.getByTestId('history-open').click();
	await expect(page).toHaveURL(/\/canon\/widgets-v3$/);
	await expect(tabs(page, 0)).toContainText('main.tex · widgets-v3');
	await history(page);
	await expect(page.getByTestId('history-version-widgets-v3')).toHaveAttribute('aria-checked', 'true');
	await expect(page.getByTestId('history-compare-live')).toBeVisible();
});

test('a version steps to the older and the newer in place, the newest to the live text, and says why it cannot be put back', async ({ page }) => {
	await page.route('**/_api', (route) => route.fulfill({ json: { write_api: 1, capabilities: ['history-restore', 'history-record'], token: 't' } }));
	await serve(page, (m) => {
		m.canon[0].cannot_restore = 'This version was kept as one text, and the document is now several files.';
	});
	await page.goto('/canon/widgets-v2');
	await pane(page, 0).getByTestId('version-older').click();
	await expect(page).toHaveURL(/\/canon\/widgets-v1/);
	await expect(pane(page, 0).getByTestId('version-older')).toBeDisabled();
	await expect(pane(page, 0).getByTestId('version-restore')).toBeDisabled();
	await expect(pane(page, 0).getByTestId('version-restore')).toHaveAttribute('title', /kept as one text/);
	await pane(page, 0).getByTestId('version-newer').click();
	await pane(page, 0).getByTestId('version-newer').click();
	await expect(page).toHaveURL(/\/canon\/widgets-v3/);
	await pane(page, 0).getByTestId('version-newer').click();
	await expect(page).toHaveURL(/\/master\/drafting\/main/);
});

test('Restore on a version asks first, then puts it back and turns to the live text', async ({ page }) => {
	let posted: Record<string, unknown> | null = null;
	await page.route('**/_api', (route) => route.fulfill({ json: { write_api: 1, capabilities: ['history-restore'], token: 't' } }));
	await page.route('**/_api/history-restore', async (route) => {
		posted = route.request().postDataJSON();
		await route.fulfill({ json: { ok: true, result: 'put main.tex back as “widgets-v2” holds it; its text before is the version “Before restoring “widgets-v2””' } });
	});
	await page.goto('/canon/widgets-v2');
	await pane(page, 0).getByTestId('version-restore').click();
	await expect(pane(page, 0).getByTestId('version-ask')).toContainText('Put main.tex back as this version? Its text now is kept as a version.');
	expect(posted).toBeNull();
	await pane(page, 0).getByTestId('version-restore-go').click();
	await expect(page).toHaveURL(/\/master\/drafting\/main/);
	expect(posted).toMatchObject({ document: 'drafting/main.tex', version: '.loom/history/0003-widgets-v2/widgets-v2.tex' });
	// the answer stays under the live text's toolbar until closed
	await expect(pane(page, 0).getByTestId('version-said')).toContainText('Put main.tex back as “widgets-v2” holds it');
	await pane(page, 0).getByTestId('strip-close').click();
	await expect(pane(page, 0).getByTestId('version-said')).toHaveCount(0);
});

test('a version compared with now keeps its toolbar on one line, older and newer alone', async ({ page }) => {
	await page.setViewportSize({ width: 1100, height: 800 });
	await page.goto('/canon/widgets-v2');
	await pane(page, 0).getByTestId('version-compare').click();
	const bar = pane(page, 0).getByTestId('item-controls');
	await expect(bar.getByTestId('version-older')).toBeVisible();
	await expect(bar.getByTestId('version-compare')).toHaveCount(0);
	await expect(bar.getByTestId('history-live')).toHaveCount(0);
	const box = (await bar.boundingBox())!;
	const controls = (await bar.getByTestId('version-controls').boundingBox())!;
	expect(controls.y).toBeGreaterThanOrEqual(box.y);
	expect(controls.y + controls.height).toBeLessThanOrEqual(box.y + box.height);
});

test('the history menu records a version from Review › History', async ({ page }) => {
	await page.route('**/_api', (route) => route.fulfill({ json: { write_api: 1, capabilities: ['history-record', 'history-restore'], token: 't' } }));
	let posted: Record<string, unknown> | null = null;
	await page.route('**/_api/history-record', async (route) => {
		posted = route.request().postDataJSON();
		await route.fulfill({ json: { ok: true, result: 'kept this version of main.tex as “Before referee”' } });
	});
	await page.goto('/master/drafting/main');
	await history(page);
	await page.getByTestId('history-record').click();
	await expect(page).toHaveURL(/\/review\/history\?document=drafting%2Fmain\.tex&record=1/);
	await page.getByTestId('history-record-name').fill('Before referee');
	await page.getByTestId('history-record-go').click();
	await expect(page.getByTestId('history-bar-said')).toHaveText('Kept this version of main.tex as “Before referee”.');
	expect(posted).toMatchObject({ document: 'drafting/main.tex', name: 'Before referee' });
});

test('an undo’s set-aside text is put back from everything recorded, after asking', async ({ page }) => {
	let posted: Record<string, unknown> | null = null;
	await page.route('**/_api', (route) => route.fulfill({ json: { write_api: 1, capabilities: ['history-restore'], token: 't' } }));
	await page.route('**/_api/history-restore', async (route) => {
		posted = route.request().postDataJSON();
		await route.fulfill({ json: { ok: true, result: 'put README.md back as the undo found it; its text before is kept' } });
	});
	await serve(page, (m) => {
		m.history.acts.push({ action: 'undo', when: '2026-11-04T00:00:00Z', actor: 'The synthetic quilt', path: 'README.md', from: 'sha256:abc', to: 'sha256:def' });
	});
	await page.goto('/review/history');
	await page.getByTestId('history-acts').locator('summary').click();
	const undo = page.getByTestId('history-act').first();
	await expect(undo).toContainText('Undid an edit to README.md');
	await undo.getByTestId('history-put-back').click();
	expect(posted).toBeNull();
	await undo.getByTestId('history-put-back-go').click();
	await expect(undo.getByTestId('history-act-said')).toHaveText('Put README.md back as the undo found it; its text before is kept.');
	expect(posted).toMatchObject({ path: 'README.md', text: 'sha256:abc' });
});
