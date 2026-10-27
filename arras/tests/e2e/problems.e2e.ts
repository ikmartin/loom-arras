// The problems page: every diagnostic the publisher reports, grouped by what it is about, filtered from the URL, with the fix it offers ready to copy. Each test is named for the rule it holds.
import { expect, test } from '@playwright/test';
import { manifest, serve } from '../manifest';

test('the problems page lists every diagnostic code', async ({ page }) => {
	await page.goto('/problems');
	const codes = new Set<string>(manifest.diagnostics.map((d: { code: string }) => d.code));
	for (const code of codes) await expect(page.locator(`main h2 code`, { hasText: code }).first()).toBeVisible();
});

test('the problems page filters by severity from the URL, with its filters in the panel', async ({ page }) => {
	await page.goto('/problems?severity=error');
	await expect(page.getByTestId('filter-severity')).toHaveValue('error');
	const errorCodes = new Set((manifest.diagnostics as { severity: string; code: string }[]).filter((d) => d.severity === 'error').map((d) => d.code));
	await expect(page.getByTestId('problem-group')).toHaveCount(errorCodes.size);
});

test('the problems page groups by subject and copies a fix', async ({ page, context, browserName }) => {
	// the fixture's record is sound, so one fault in it is added: a document the records name that is gone, with the command that finds it
	await serve(page, (m) => {
		m.diagnostics.push({
			severity: 'warning',
			code: 'loom:document-gone',
			message: 'drafting/draft0.tex is gone, and 1 acceptance row names it; loom mv records where it went',
			locations: [],
			keys: [],
			subject: 'record',
			fixes: [{ label: 'record where it went', command: 'loom mv drafting/draft0.tex NEW' }]
		});
	});
	await page.goto('/problems');
	const headings = page.getByTestId('subject-heading');
	await expect(headings.first()).toHaveText('The source');
	await expect(headings.nth(1)).toHaveText('The record');
	await page.getByTestId('filter-subject').selectOption('record');
	await expect(page.getByTestId('problem-group')).toContainText('loom:document-gone');
	await page.getByTestId('problem-group').first().locator('summary').click();
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

test('each code is folded to its count until opened, one at a time or all at once, and the bar shows at rest', async ({ page }) => {
	await page.setViewportSize({ width: 1440, height: 500 });
	await page.goto('/problems');
	const groups = page.getByTestId('problem-group');
	await expect(groups.first()).toBeVisible();
	const n = await groups.count();
	expect(n).toBeGreaterThan(1);
	for (let i = 0; i < n; i++) await expect(groups.nth(i)).not.toHaveAttribute('open');
	await expect(groups.first().locator('li').first()).toBeHidden();
	await groups.first().locator('summary').click();
	await expect(groups.first().locator('li').first()).toBeVisible();
	await page.getByTestId('problems-expand').click();
	for (let i = 0; i < n; i++) await expect(groups.nth(i)).toHaveAttribute('open');
	await expect(page.getByTestId('problems-expand')).toHaveText('fold all');
	// a code the URL names stands open
	const code = manifest.diagnostics[0].code;
	await page.goto('/problems?code=' + encodeURIComponent(code));
	await expect(page.getByTestId('problem-group').first()).toHaveAttribute('open');
	// the page is read by moving through it, so its bar is drawn at rest
	expect(await page.evaluate(() => getComputedStyle(document.documentElement).scrollbarColor)).not.toBe('rgba(0, 0, 0, 0) rgba(0, 0, 0, 0)');
});
