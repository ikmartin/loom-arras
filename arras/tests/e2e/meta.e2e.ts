// Review as the meta view (plan 0.22.8), read from the fixture: Review leads with what changed in the open files since the author's look, each with its diff, and Proposed Changes lists what waits to be taken.
import { expect, test } from '@playwright/test';

test('Review leads with the changes since the look, each file with its diff, and lists what is proposed', async ({ page }) => {
	await page.goto('/review');
	const change = page.getByTestId('change');
	await expect(change).toHaveCount(1);
	await expect(change).toHaveAttribute('data-path', 'notes/intro.md');
	await expect(change).toContainText('and by nothing else.');
	// the bar says how much changed since when, and stays at the top while the page scrolls
	const bar = page.getByTestId('review-bar');
	await expect(bar).toContainText('edited since your look');
	await expect(bar).toHaveCSS('position', 'sticky');
	// the file's name opens the file, as the tree does
	await expect(change.getByTestId('change-open')).toHaveAttribute('href', /\/file\/notes\/intro\.md$/);
	// no publisher to ask, so no verbs
	await expect(page.getByTestId('change-keep')).toHaveCount(0);
	await page.getByTestId('section-proposed').click();
	await expect(page.getByTestId('proposed')).toBeVisible();
	// a suggestion opens in the document that reads it, at its place, with it open there
	await expect(page.getByTestId('suggestion-open').first()).toHaveAttribute('href', /^\/master\/drafting\/main\?note=a-[\d-]+/);
});
