// The problems page: every diagnostic the publisher reports, grouped by what it is about, filtered from the URL, with the fix it offers ready to copy. Each test is named for the rule it holds.
import { expect, test } from '@playwright/test';
import { manifest } from '../manifest';

test('the problems page lists every diagnostic code', async ({ page }) => {
	await page.goto('/problems');
	const codes = new Set<string>(manifest.diagnostics.map((d: { code: string }) => d.code));
	for (const code of codes) await expect(page.locator(`main h2 code`, { hasText: code }).first()).toBeVisible();
});

test('the problems page filters by severity from the URL, with its filters in the panel', async ({ page }) => {
	await page.goto('/problems?severity=error');
	await expect(page.getByTestId('filter-severity')).toHaveValue('error');
	const errorCodes = new Set((manifest.diagnostics as { severity: string; code: string }[]).filter((d) => d.severity === 'error').map((d) => d.code));
	await expect(page.locator('main section.group')).toHaveCount(errorCodes.size);
});

test('the problems page groups by subject and copies a fix', async ({ page, context, browserName }) => {
	await page.goto('/problems');
	const headings = page.getByTestId('subject-heading');
	await expect(headings.first()).toHaveText('The source');
	await expect(headings.nth(1)).toHaveText('The record');
	await page.getByTestId('filter-subject').selectOption('record');
	await expect(page.locator('section.group')).toContainText('loom:canon-edited');
	const fix = page.getByTestId('fix').first();
	await expect(fix).toHaveText('copy');
	if (browserName === 'chromium') {
		await context.grantPermissions(['clipboard-read', 'clipboard-write']);
		await fix.click();
		await expect(fix).toHaveText('copied');
		const copied = await page.evaluate(() => navigator.clipboard.readText());
		expect(copied.length).toBeGreaterThan(0); // the command as the publisher wrote it, whatever it is
	}
});
