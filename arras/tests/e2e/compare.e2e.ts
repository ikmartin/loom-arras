// Compare, on the static fixture: no publisher answers, so a node that differs is marked on every line, which is what a static host shows. Its washed words are the write suite's (e2e-write/write.e2e.ts). A draft's history menu starts it (history.e2e.ts); here the address does, which also reaches the comparisons no menu offers, two of the author's documents among them.
import { expect, test, type Page } from '@playwright/test';
import { beside, pane } from '../workspace';

/** The two items side by side and compared, as the address `?compare=1` asks. */
async function open(page: Page, left: string, right: string): Promise<void> {
	await page.goto(left + beside(right) + '&compare=1');
	// both panes typeset, so that nothing reflows under a step
	for (const i of [0, 1]) await expect(pane(page, i).locator('.fragment mjx-container').first()).toBeAttached();
	await page.evaluate(() => document.fonts.ready);
	await expect(page.getByTestId('compare-count')).toBeVisible();
	// the comparison drawn in both panes before anything is measured against it
	await expect(pane(page, 0).locator('.compare-mark').first()).toBeAttached();
	await expect(pane(page, 1).locator('.compare-mark').first()).toBeAttached();
}

/** A node's top in the viewport, in one pane. */
const top = async (page: Page, index: number, pair: string) => (await pane(page, index).locator(`[data-pair="${pair}"]`).first().boundingBox())!.y;

test('an address that compares two things that do not pair is let go, and nothing offers compare but a history', async ({ page }) => {
	await page.goto('/master/main' + beside('/session/s-2026-09-16-0001') + '&compare=1');
	await expect(pane(page, 1).getByTestId('item-controls')).toBeVisible();
	await expect(page.getByTestId('compare-count')).toHaveCount(0);
	await expect(page).not.toHaveURL(/compare=/);
	await page.goto('/node/sy-0002' + beside('/master/main') + '&compare=1');
	await expect(pane(page, 1).getByTestId('item-controls')).toBeVisible();
	await expect(page.getByTestId('compare-count')).toHaveCount(0);
	await expect(page.getByTestId('pane-compare')).toHaveCount(0);
	// and in a window too narrow for two panes
	await page.setViewportSize({ width: 600, height: 800 });
	await page.goto('/master/main' + beside('/master/aidoc') + '&compare=1');
	await expect(page.getByTestId('narrow-strip')).toBeVisible();
	await expect(page.getByTestId('compare-count')).toHaveCount(0);
});

test('comparing hides annotations in both panes, and stopping puts back what each had', async ({ page }) => {
	await open(page, '/master/main', '/master/aidoc');
	for (const i of [0, 1]) await expect(pane(page, i).getByTestId('toolbar-view-on')).toBeVisible();
	await expect(page).toHaveURL(/compare=1/);
	await page.getByTestId('compare-stop').click();
	for (const i of [0, 1]) await expect(pane(page, i).getByTestId('toolbar-view-on')).toHaveCount(0);
	await expect(page.getByTestId('compare-steps')).toHaveCount(0);
	await expect(page).not.toHaveURL(/compare=/);
});

test('an agent document against its source: − on the source, + on the copy, amber where both changed, a wedge for what one lacks', async ({ page }) => {
	await open(page, '/master/main', '/master/aidoc');
	await expect(page.getByTestId('compare-count')).toHaveText('6 differences');
	const left = pane(page, 0);
	const right = pane(page, 1);
	// sy-0002 was changed by the agent: the source holds the base
	await expect(left.locator('[data-pair="sy-0002"].compare-del')).toHaveCount(1);
	await expect(right.locator('[data-pair="sy-0002"].compare-add')).toHaveCount(1);
	await expect(left.locator('.compare-gutter .gl.del').first()).toHaveText('−');
	// sy-0001 was changed on both sides since the copy
	await expect(left.locator('[data-pair="sy-0001"]')).toContainText('changed on both sides since the copy');
	await expect(right.locator('.compare-gutter .gl.both').first()).toHaveText('~');
	// sy-0202 is gone from the copy: marked on the source, a wedge in the copy where it stood
	await expect(left.locator('[data-pair="sy-0202"]')).toContainText('removed in aidoc.tex');
	await expect(right.locator('.compare-gutter .gw.del[data-wedge="sy-0202"]')).toHaveCount(1);
	// sy-999C is new, and sy-000A moved unchanged
	await expect(right.locator('[data-pair="sy-999C"]')).toContainText('new');
	await expect(right.locator('[data-pair="sy-000A"].compare-moved')).toContainText('moved from');
	await expect(left.locator('[data-pair="sy-000A"]')).toContainText('moved in aidoc.tex');
});

test('stepping brings both panes to one difference at one height, and a double-click brings the partner', async ({ page }) => {
	await open(page, '/master/main', '/master/aidoc');
	await page.keyboard.press(']');
	await page.keyboard.press(']');
	await expect(page.getByTestId('compare-count')).toHaveText('2 of 6');
	await expect.poll(async () => Math.abs((await top(page, 0, 'sy-0002')) - (await top(page, 1, 'sy-0002')))).toBeLessThan(4);
	// the partner of a node far down one pane comes to its height in the other
	await pane(page, 0).locator('[data-pair="sy-000C"]').first().scrollIntoViewIfNeeded();
	await pane(page, 0).locator('[data-pair="sy-000C"] .env-label').first().dblclick();
	await expect.poll(async () => Math.abs((await top(page, 0, 'sy-000C')) - (await top(page, 1, 'sy-000C')))).toBeLessThan(4);
});

test('two of the author’s documents: presence dashed and order dotted, no gutter', async ({ page }) => {
	await open(page, '/master/main', '/master/talk');
	await expect(page.locator('.compare-gutter')).toHaveCount(0);
	await expect(pane(page, 0).locator('[data-pair="sy-0001"].compare-only')).toContainText('not in talk.tex');
	await expect(page.locator('.compare-order').first()).toContainText('order differs');
});

test('a landmark against today: the landmark holds the base', async ({ page }) => {
	await open(page, '/canon/widgets-v1', '/master/main');
	await expect(pane(page, 0).locator('[data-pair="sy-0001"].compare-del')).toHaveCount(1);
	await expect(pane(page, 1).locator('[data-pair="sy-0001"].compare-add')).toHaveCount(1);
});

test('a changed tab ends compare', async ({ page }) => {
	await open(page, '/master/main', '/master/aidoc');
	// the right pane takes another document, as a reader choosing one from the panel does
	await pane(page, 1).locator('.fragment').first().click();
	await page.getByTestId('docs-drafts').getByRole('link', { name: 'talk.tex' }).click();
	await expect(pane(page, 1).getByTestId('item-tab').filter({ hasText: 'talk.tex' })).toHaveCount(1);
	await expect(page.getByTestId('compare-stop')).toHaveCount(0);
	await expect(page.locator('.compare-mark')).toHaveCount(0);
	// and each pane has its annotations back
	for (const i of [0, 1]) await expect(pane(page, i).getByTestId('toolbar-view-on')).toHaveCount(0);
});
