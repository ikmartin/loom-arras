// Where the reader is (plan 0.21.8): each tab reports its place to the publisher, and `loom here` reads back the one touched last.
import { expect, readOnly } from '../served';
import type { Page } from '@playwright/test';

/** What `loom here --json` says the person is looking at. */
function looking(served: { loom(args: string[]): string }): Record<string, any> {
	return JSON.parse(served.loom(['here', '--json'])).looking ?? {};
}

/** Select an element's words as a reader would, and let go. */
async function select(page: Page, selector: string): Promise<void> {
	await page.locator(selector).first().evaluate((node) => {
		const range = document.createRange();
		range.selectNodeContents(node);
		const sel = window.getSelection();
		sel?.removeAllRanges();
		sel?.addRange(range);
		node.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
	});
}

readOnly('the words selected in a result are what loom here reports, by the key they are in', async ({ page, served }) => {
	await page.goto('/node/sy-0003');
	const statement = '[data-pane="0"] .fragment .env[data-id="sy-0003"] > p[data-src]';
	await page.locator(statement).first().locator('mjx-container').first().waitFor();
	await expect.poll(() => looking(served).item?.link).toBe('quilt:sy-0003');
	await select(page, statement);
	await expect.poll(() => looking(served).selection?.text ?? '').toContain('widget');
	expect(looking(served).selection.link).toBe('quilt:sy-0003');
});

readOnly('in Review it is the block under review, and with two tabs open the one touched last', async ({ page, served }) => {
	await page.goto('/node/sy-0003');
	await expect.poll(() => looking(served).item?.link).toBe('quilt:sy-0003');
	const other = await page.context().newPage();
	await other.goto('/review');
	await expect.poll(() => looking(served).review?.key ?? '').toMatch(/^sy-/);
	expect(looking(served).review.cause).toBeTruthy();
	// the first tab is touched again, and says where it is though nothing there changed; headless Chromium keeps both tabs visible and fires no focus on switching, so the test sends it
	await page.evaluate(() => window.dispatchEvent(new Event('focus')));
	await expect.poll(() => looking(served).route).toBe('reading');
	expect(looking(served).item.link).toBe('quilt:sy-0003');
	await other.close();
});
