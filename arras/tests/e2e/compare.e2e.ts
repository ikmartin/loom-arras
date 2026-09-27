// Compare (book 15.2.6), on the static fixture: no publisher answers, so a node that differs is marked on every line, which is what a static host shows. Its washed words are the write suite's (e2e-write/write.e2e.ts).
import { expect, test, type Page } from '@playwright/test';
import { beside, pane } from '../workspace';

const compare = (page: Page) => page.getByTestId('rail-compare');

async function open(page: Page, left: string, right: string): Promise<void> {
	await page.goto(left + beside(right));
	// both panes typeset, so that nothing reflows under a step
	for (const i of [0, 1]) await expect(pane(page, i).locator('.fragment mjx-container').first()).toBeAttached();
	await page.evaluate(() => document.fonts.ready);
	await expect(compare(page)).toBeEnabled();
	await compare(page).click();
	await expect(compare(page)).toHaveAttribute('aria-pressed', 'true');
}

/** A node's top in the viewport, in one pane. */
const top = async (page: Page, index: number, pair: string) => (await pane(page, index).locator(`[data-pair="${pair}"]`).first().boundingBox())!.y;

test('compare is disabled, saying why, until two things that pair stand side by side', async ({ page }) => {
	await page.goto('/master/main');
	await expect(compare(page)).toBeDisabled();
	await expect(compare(page)).toHaveAttribute('title', /Open a second document/);
	await page.goto('/master/main' + beside('/session/s-2026-09-16-0001'));
	await expect(compare(page)).toHaveAttribute('title', /Nothing in a session pairs/);
	await page.goto('/node/sy-0002' + beside('/master/main'));
	await expect(compare(page)).toHaveAttribute('title', 'A node compares with a node, a document with a document');
	await page.setViewportSize({ width: 600, height: 800 });
	await page.goto('/master/main' + beside('/master/aidoc'));
	await expect(compare(page)).toHaveAttribute('title', /too narrow/);
});

test('pressing compare turns annotations off, and releasing it puts back what was chosen', async ({ page }) => {
	await open(page, '/master/main', '/master/aidoc');
	await expect(page.getByTestId('show-off')).toHaveAttribute('aria-pressed', 'true');
	await expect(page).toHaveURL(/compare=1/);
	await compare(page).click();
	await expect(page.getByTestId('show-all')).toHaveAttribute('aria-pressed', 'true');
	await expect(page.getByTestId('compare-steps')).toHaveCount(0);
	await expect(page).not.toHaveURL(/compare=/);
});

test('an agent copy against its source: − on the source, + on the copy, amber where both changed, a wedge for what one lacks', async ({ page }) => {
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
	await expect(compare(page)).toHaveAttribute('aria-pressed', 'false');
	await expect(page.locator('.compare-mark')).toHaveCount(0);
	await expect(page.getByTestId('show-all')).toHaveAttribute('aria-pressed', 'true');
});
