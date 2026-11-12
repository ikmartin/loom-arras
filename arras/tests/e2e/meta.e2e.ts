// Review as the meta view (plan 0.22.8), read from the fixture: Review leads with every change waiting in the person's text, each with its words, and Proposed Changes lists what waits to be decided in a pass of its own.
import { expect, test } from '@playwright/test';
import { manifest } from '../manifest';

test('Review leads with the changes waiting, each with its words, and lists what is proposed', async ({ page }) => {
	await page.goto('/review');
	const waiting = (manifest.changes ?? []).filter((c: { id?: unknown }) => typeof c.id === 'string');
	await expect(page.getByTestId('change-card')).toHaveCount(waiting.length);
	// a file in no document is listed under its path, its words in and out
	const intro = page.locator('[data-testid="change-group"][data-path="notes/intro.md"]');
	await expect(intro).toContainText("in no document's text");
	await expect(intro.getByTestId('change-words')).toContainText('and by nothing else.');
	// the bar says how much waits, and stays at the top while the page scrolls
	const bar = page.getByTestId('review-bar');
	await expect(bar).toContainText(`${waiting.length} changes waiting`);
	await expect(bar).toHaveCSS('position', 'sticky');
	// no publisher to ask, so no act can be pressed
	await expect(page.getByTestId('card-keep').first()).toBeDisabled();
	await page.getByTestId('section-proposed').click();
	await expect(page.getByTestId('proposed')).toBeVisible();
});
