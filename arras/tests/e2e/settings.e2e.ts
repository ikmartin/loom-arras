// Settings: the window, its sections in two groups, the preferences it stores, and the quilt's settings as a viewer with no publisher shows them; the four formats a document is read in. The comment placement is with the annotations it places. Each test is named for the rule it holds.
import { expect, test } from '@playwright/test';
import { prefs, settings } from '../workspace';

test('Settings opens as a window over the page, Loom first with Profile at its head and Quilt after, and closes on Escape, a press outside or its ×', async ({ page }) => {
	await page.goto('/');
	await page.getByTestId('settings-toggle').click();
	const win = page.getByTestId('settings-window');
	await expect(win).toBeVisible();
	await expect(win).toHaveAttribute('role', 'dialog');
	const nav = page.getByTestId('settings-nav');
	await expect(nav.locator('.group')).toHaveText(['Loom', 'Quilt', 'Development']);
	await expect(nav.locator('[data-testid^="settings-section-"]')).toHaveText(['Profile', 'Appearance', 'Files', 'General', 'Documents', 'Agents', 'Library', 'Problems', 'Overleaf']);
	// larger than the box it replaced: a window, not a menu
	const box = await win.boundingBox();
	expect(box!.width).toBeGreaterThan(700);

	await page.keyboard.press('Escape');
	await expect(win).toHaveCount(0);
	await page.getByTestId('settings-toggle').click();
	await page.mouse.click(5, 5);
	await expect(win).toHaveCount(0);
	await page.getByTestId('settings-toggle').click();
	await win.getByRole('button', { name: 'Close settings' }).click();
	await expect(win).toHaveCount(0);
});

test('each section opens its own page, saying where it is saved, and the window opens again where it was left', async ({ page }) => {
	await page.goto('/');
	for (const [section, title, where] of [
		['appearance', 'Appearance', 'this browser'],
		['profile', 'Profile', 'for every quilt'],
		['agents', 'Agents', "this quilt's config.toml"],
		['overleaf', 'Overleaf', '.loom/source-sync.json, committed with the quilt']
	]) {
		await settings(page, section);
		await expect(page.getByTestId('settings-title')).toHaveText(title);
		await expect(page.getByTestId('settings-window').locator('.where')).toContainText(where);
	}
	await page.reload();
	await page.getByTestId('settings-toggle').click();
	await expect(page.getByTestId('settings-title')).toHaveText('Overleaf');
});

test('the display preferences survive a reload and change the document', async ({ page }) => {
	await page.goto('/');
	await settings(page, 'appearance');
	await page.getByTestId('theme-dark').click();
	await page.getByTestId('size-l').click();
	await expect(page.getByTestId('theme-dark')).toHaveAttribute('aria-pressed', 'true');
	await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
	await expect(page.locator('html')).toHaveAttribute('data-size', 'l');
	await settings(page, 'appearance');
	await page.getByTestId('ids').check();
	await expect(page.locator('html')).toHaveAttribute('data-ids', 'yes');

	await page.reload();
	await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
	await expect(page.locator('html')).toHaveAttribute('data-size', 'l');
	await expect(page.locator('html')).toHaveAttribute('data-ids', 'yes');
});

test("without a publisher, the quilt's settings are shown as published and change nothing", async ({ page }) => {
	await page.goto('/');
	await settings(page, 'general');
	await expect(page.getByTestId('settings-read-only')).toContainText('config.toml');
	await expect(page.getByTestId('config-quilt.name')).toHaveValue('The synthetic quilt');
	await expect(page.getByTestId('config-quilt.name')).toBeDisabled();
	await expect(page.getByTestId('setting-quilt.name')).toContainText('[quilt] name');
	await settings(page, 'documents');
	await expect(page.getByTestId('config-quilt.main')).toHaveValue('drafting/main.tex');
	await expect(page.getByTestId('config-quilt.main')).toBeDisabled();
	await settings(page, 'agents');
	await expect(page.getByTestId('agents-protected')).toContainText('config.toml');
	await expect(page.getByTestId('deny-pattern')).toHaveCount(0);
	await expect(page.getByTestId('agents-update')).toHaveCount(0);
	// a quilt with no agent layer says what writes one, in the publisher's words
	await expect(page.getByTestId('agents-no-layer')).toContainText('loom ai init');
	await settings(page, 'overleaf');
	await expect(page.getByTestId('sync-unpaired')).toBeVisible();
	await expect(page.getByTestId('settings-read-only')).toHaveCount(0);
	await expect(page.getByTestId('settings-savebar')).toHaveCount(0);
	// a name is saved only through a publisher
	await settings(page, 'profile');
	await expect(page.locator('#reviewer-name')).toHaveCount(0);
});

test('on a phone the sections are a row above the page, and nothing runs off the screen', async ({ page }) => {
	await page.setViewportSize({ width: 375, height: 760 });
	await page.goto('/');
	await page.getByTestId('panel-fold').click();
	await settings(page, 'agents');
	const win = (await page.getByTestId('settings-window').boundingBox())!;
	expect(win.x).toBeGreaterThanOrEqual(0);
	expect(win.x + win.width).toBeLessThanOrEqual(375);
	expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(375);
	// the open section is scrolled into the row
	await expect(page.getByTestId('settings-section-agents')).toBeInViewport();
	const nav = (await page.getByTestId('settings-nav').boundingBox())!;
	const body = (await page.getByTestId('settings-page').boundingBox())!;
	expect(body.y).toBeGreaterThanOrEqual(nav.y + nav.height - 1);
});

test.describe('the four formats a document is read in', () => {
	test('the format is one switch, applied to documents and nodes alike', async ({ page }) => {
		await page.goto('/master/drafting/main');
		await expect(page.locator('html')).toHaveAttribute('data-format', 'p1'); // the compiled page, by default
		await expect(page.locator('.fragment .env-label .number').first()).toBeVisible();

		await settings(page, 'appearance');
		await page.getByTestId('format-b2').click();
		await expect(page.locator('html')).toHaveAttribute('data-format', 'b2');
		// b2 points at a result by name, not by number
		await expect(page.locator('.fragment .env-label .number').first()).toBeHidden();

		// the same switch on a node's own page: a result does not change character with the page it stands on
		await page.goto('/node/sy-0003');
		await expect(page.locator('html')).toHaveAttribute('data-format', 'b2');
		await expect(page.locator('.fragment .env-label .number').first()).toBeHidden();
	});

	test('p1 sets the compiled page: run-in heads, no colour on a result', async ({ page }) => {
		await prefs(page, { format: 'p1' });
		await page.goto('/master/drafting/main');
		await page.waitForSelector('.fragment .env[data-key]');
		await expect(page.locator('html')).toHaveAttribute('data-format', 'p1');

		const env = page.locator('.fragment .env[data-style="plain"]').first();
		const label = env.locator('> .env-label');
		// the head runs into the first line, in weight, and the statement is italic as the class sets it
		await expect(label).toHaveCSS('display', 'inline');
		await expect(label).toHaveCSS('font-weight', '700');
		await expect(env.locator('> .env-label + p')).toHaveCSS('font-style', 'italic');
		// and carries no colour of its own at all
		await expect(env).toHaveCSS('border-left-width', '0px');
		await expect(env).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)');

		// a remark's head is italic rather than bold
		const remark = page.locator('.fragment .env[data-style="remark"] > .env-label').first();
		if (await remark.count()) await expect(remark).toHaveCSS('font-style', 'italic');
	});

	test('p2 marks where the compiled pages ended, and p1 marks nothing', async ({ page }) => {
		await prefs(page, { format: 'p2' });
		await page.goto('/master/drafting/main');
		await page.waitForSelector('.fragment .env[data-key]');
		const breaks = page.locator('.page-break');
		await expect.poll(() => breaks.count()).toBeGreaterThan(0);
		// every boundary carries the page it begins, which is the page a reader would cite
		const pages = await breaks.evaluateAll((els) => els.map((e) => Number((e as HTMLElement).dataset.page)));
		expect(pages).toEqual([...pages].sort((a, b) => a - b));
		expect(new Set(pages).size).toBe(pages.length);

		await settings(page, 'appearance');
		await page.getByTestId('format-p1').click();
		await expect(page.locator('.page-break')).toHaveCount(0);
	});

	test('b1 keeps the taxon accent, in three colours at most', async ({ page }) => {
		await prefs(page, { format: 'b1' });
		await page.goto('/master/drafting/main');
		await page.waitForSelector('.fragment .env[data-key]');
		await expect(page.locator('html')).toHaveAttribute('data-format', 'b1');
		const tones = await page.evaluate(() =>
			[...document.querySelectorAll('.fragment .env[data-key]')].map((e) => (e as HTMLElement).style.getPropertyValue('--taxon-tone'))
		);
		expect([...new Set(tones.filter(Boolean))].length, `the tones: ${[...new Set(tones)].join(', ')}`).toBeLessThanOrEqual(3);
	});
});
