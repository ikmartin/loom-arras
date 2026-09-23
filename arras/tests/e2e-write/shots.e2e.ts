// Screenshots of the editing surfaces, which exist only where a publisher is actually serving the write API.
import { test } from '@playwright/test';
import { openPicker } from '../picker';

const OUT = '../records/images';

test('the editing surfaces', async ({ page }) => {
	await page.setViewportSize({ width: 1440, height: 900 });
	await page.goto('/');
	await page.evaluate(() => localStorage.setItem('arras.prefs', JSON.stringify({ shell: 'c', face: 'serif', size: 'm', width: 'mid', theme: 'light', comments: 'floating' })));

	await page.goto('/node/sy-0002');
	const words = page.locator('[data-pane="0"] .fragment .env[data-id="sy-0002"] > p[data-src]').first();
	await words.locator('mark.annotation').waitFor();
	// a write names its session, and nothing is selected at rest (plan 0.13.1), so the picture is of a reader who
	// has chosen where their work goes -- which is the state the composer is usable in
	await openPicker(page);
	await page.getByTestId('session-list').locator('[data-testid^="session-s-"]').first().click();
	await page.waitForSelector('[data-testid="discussion"]');
	// the composer opens where the selection is, as on a paper's page
	await words.evaluate((node) => {
		const range = document.createRange();
		range.selectNodeContents(node);
		window.getSelection()?.removeAllRanges();
		window.getSelection()?.addRange(range);
		node.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
	});
	await page.getByTestId('annotate-offer').click();
	await page.getByTestId('note-body').fill('Is the singleton orbit counted once or twice here?');
	await page.getByTestId('note-kind').selectOption('question');
	await page.waitForTimeout(600);
	await page.screenshot({ path: `${OUT}/composer.png` });

	await page.goto('/master/main');
	// choosing where to write opens where the writing is read, beside the document
	await openPicker(page);
	await page.getByTestId('session-list').locator('[data-testid^="session-s-"]').first().click();
	await page.waitForSelector('[data-testid="discussion"]');
	await page.waitForTimeout(900);
	await page.screenshot({ path: `${OUT}/document-annotations.png` });
});
