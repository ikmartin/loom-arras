// Screenshots of the editing surfaces, which exist only where a publisher is actually serving the write API.
import { test } from '@playwright/test';

const OUT = '../records/images';

test('the editing surfaces', async ({ page }) => {
	await page.setViewportSize({ width: 1440, height: 900 });
	await page.goto('/');
	await page.evaluate(() => localStorage.setItem('arras.prefs', JSON.stringify({ shell: 'c', face: 'serif', size: 'm', width: 'mid', theme: 'light', comments: 'margin' })));

	await page.goto('/node/sy-0002');
	await page.waitForSelector('main h1');
	// a write names its session, and nothing is selected at rest (plan 0.13.1), so the picture is of a reader who
	// has chosen where their work goes -- which is the state the composer is usable in
	await page.getByTestId('session-list').locator('[data-testid^="session-s-"]').first().click();
	await page.getByTestId('composer-open').click();
	await page.getByTestId('composer-quote').fill('one or two points');
	await page.getByTestId('composer-message').fill('Is the singleton orbit counted once or twice here?');
	await page.getByTestId('composer-kind').selectOption('question');
	await page.waitForTimeout(600);
	await page.screenshot({ path: `${OUT}/composer.png` });

	await page.goto('/master/main');
	await page.waitForSelector('[data-testid="document-annotations"]');
	await page.waitForTimeout(900);
	await page.screenshot({ path: `${OUT}/document-annotations.png` });
});
