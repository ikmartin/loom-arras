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
	await page.goto('/master/main');
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

test("the landmarks loom kept itself are folded under one line, which opens them in place", async ({ page }) => {
	await serve(page, (m) => {
		m.canon.push({ ...structuredClone(m.canon[1]), path: '.loom/history/0007-main-before-adopt-aidoc/main-before-adopt-aidoc.tex', stem: 'main-before-adopt-aidoc', name: 'main-before-adopt-aidoc', step: '0007', kept_for: 'adopt' });
	});
	await page.goto('/master/main');
	await history(page);
	await expect(page.getByTestId('history-version-main-before-adopt-aidoc')).toHaveCount(0);
	await page.getByTestId('history-kept').click();
	// the menu stays open, and the line opens the ones it folded
	await expect(page.getByTestId('history-menu')).toBeVisible();
	await expect(page.getByTestId('history-version-main-before-adopt-aidoc')).toBeVisible();
	await expect(page.getByTestId('history-kept')).toHaveAttribute('aria-expanded', 'true');
});

test('a draft with no landmarks and no copies, and a landmark no live draft leads to, have no menu', async ({ page }) => {
	await serve(page, (m) => delete m.canon[0].in);
	await page.goto('/master/talk');
	await expect(pane(page, 0).getByTestId('item-controls')).toBeVisible();
	await expect(pane(page, 0).getByTestId('toolbar-history')).toHaveCount(0);
	await page.goto('/canon/widgets-v1');
	await expect(tabs(page, 0)).toContainText('widgets-v1 @1');
	await expect(pane(page, 0).getByTestId('toolbar-history')).toHaveCount(0);
});

test('a landmark is shown in the draft’s own tab, read-only, at the result the reader was at, and the live text is one choice back', async ({ page }) => {
	await page.goto('/master/main' + beside('/node/sy-0002'));
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
	await expect(page).toHaveURL(/\/master\/main/);
	await expect(pane(page, 0).locator('#sy-0003')).toBeInViewport();
	// and by the menu's
	await history(page);
	await page.getByTestId('history-version-widgets-v1').click();
	await expect(tabs(page, 0)).toContainText('main.tex · widgets-v1');
	await history(page);
	await page.getByTestId('history-version-live').click();
	await expect(page).toHaveURL(/\/master\/main/);
});

test('compare with a landmark opens it beside and compares the two; stop, or the same line again, ends it', async ({ page }) => {
	await page.goto('/master/main');
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
	await page.goto('/master/main');
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
	await page.goto('/master/main');
	await expect(pane(page, 0).locator('.fragment').first()).toBeVisible();
	await openHere(page, '/canon/widgets-v2');
	await expect(tabs(page, 0)).toHaveCount(2);
	await openHere(page, '/master/main');
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
	await page.goto('/master/main');
	await history(page);
	const line = page.getByTestId('history-compare-widgets-v1');
	await expect(line).toHaveAttribute('aria-disabled', 'true');
	await expect(line).toHaveAttribute('title', /too narrow/);
	await expect(page.getByTestId('history-compare-aidoc')).toHaveAttribute('aria-disabled', 'true');
});

test('a landmark opened from Review › History carries its draft’s menu', async ({ page }) => {
	await page.goto('/review/history');
	await page.locator('main').getByRole('link', { name: 'widgets-v3' }).first().click();
	await expect(page).toHaveURL(/\/canon\/widgets-v3$/);
	await expect(tabs(page, 0)).toContainText('main.tex · widgets-v3');
	await history(page);
	await expect(page.getByTestId('history-version-widgets-v3')).toHaveAttribute('aria-checked', 'true');
	await expect(page.getByTestId('history-compare-live')).toBeVisible();
});
