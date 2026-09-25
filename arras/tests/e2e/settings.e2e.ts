// The display settings: the panel that holds them, the preferences it stores, and the four formats a document is read in. The comment placement is with the annotations it places. Each test is named for the rule it holds.
import { expect, test } from '@playwright/test';
import { prefs } from '../workspace';

test('the settings panel puts every row on one line, label included, with nothing cut off, and closes on a press outside it or Escape', async ({ page }) => {
	await page.goto('/');
	await page.getByTestId('settings-toggle').click();
	await expect(page.getByTestId('settings-panel')).toBeVisible();
	const rows = await page.getByTestId('settings-panel').evaluate((el) => {
		const panel = el.getBoundingClientRect();
		return [...el.querySelectorAll('.row')].map((f) => {
			const label = f.querySelector('.lbl') as HTMLElement;
			const buttons = [...f.querySelectorAll('button')].map((b) => b.getBoundingClientRect());
			const mid = (r: DOMRect) => r.top + r.height / 2;
			return {
				label: label.textContent ?? '',
				lines: new Set(buttons.map((r) => Math.round(r.top))).size,
				// the label shares the row's line: its middle falls inside every button's box
				inline: buttons.every((r) => mid(label.getBoundingClientRect()) > r.top && mid(label.getBoundingClientRect()) < r.bottom),
				spill: buttons.filter((r) => r.right > panel.right || r.left < panel.left).length
			};
		});
	});
	expect(rows.map((r) => r.label)).toHaveLength(7); // type, size, width, theme, format, comments, show ids
	for (const r of rows) {
		expect(r.lines, `the ${r.label} row wraps`).toBe(1);
		expect(r.inline, `the ${r.label} label is not on the row's line`).toBe(true);
		expect(r.spill, `the ${r.label} row is clipped by the panel`).toBe(0);
	}
	// a press outside closes it, and so does Escape
	await page.mouse.click(900, 500);
	await expect(page.getByTestId('settings-panel')).toHaveCount(0);
	await page.getByTestId('settings-toggle').click();
	await expect(page.getByTestId('settings-panel')).toBeVisible();
	await page.keyboard.press('Escape');
	await expect(page.getByTestId('settings-panel')).toHaveCount(0);
});

test('the display preferences survive a reload and change the document', async ({ page }) => {
	await page.goto('/');
	await page.getByTestId('settings-toggle').click();
	await page.getByTestId('theme-dark').click();
	await page.getByTestId('size-l').click();
	await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
	await expect(page.locator('html')).toHaveAttribute('data-size', 'l');

	await page.reload();
	await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
	await expect(page.locator('html')).toHaveAttribute('data-size', 'l');
});

test.describe('the four formats a document is read in', () => {
	test('the format is one switch, applied to documents and nodes alike', async ({ page }) => {
		await page.goto('/master/main');
		await expect(page.locator('html')).toHaveAttribute('data-format', 'p1'); // the compiled page, by default
		await expect(page.locator('.fragment .env-label .number').first()).toBeVisible();

		await page.getByTestId('settings-toggle').click();
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
		await page.goto('/master/main');
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
		await page.goto('/master/main');
		await page.waitForSelector('.fragment .env[data-key]');
		const breaks = page.locator('.page-break');
		await expect.poll(() => breaks.count()).toBeGreaterThan(0);
		// every boundary carries the page it begins, which is the page a reader would cite
		const pages = await breaks.evaluateAll((els) => els.map((e) => Number((e as HTMLElement).dataset.page)));
		expect(pages).toEqual([...pages].sort((a, b) => a - b));
		expect(new Set(pages).size).toBe(pages.length);

		await page.getByTestId('settings-toggle').click();
		await page.getByTestId('format-p1').click();
		await expect(page.locator('.page-break')).toHaveCount(0);
	});

	test('b1 keeps the taxon accent, in three colours at most', async ({ page }) => {
		await prefs(page, { format: 'b1' });
		await page.goto('/master/main');
		await page.waitForSelector('.fragment .env[data-key]');
		await expect(page.locator('html')).toHaveAttribute('data-format', 'b1');
		const tones = await page.evaluate(() =>
			[...document.querySelectorAll('.fragment .env[data-key]')].map((e) => (e as HTMLElement).style.getPropertyValue('--taxon-tone'))
		);
		expect([...new Set(tones.filter(Boolean))].length, `the tones: ${[...new Set(tones)].join(', ')}`).toBeLessThanOrEqual(3);
	});
});
