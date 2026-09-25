// A document as it is drawn: inclusions expanded in place, headings and equation references that lead where they say, and formulas that neither scroll nor drop out of the accessibility tree. Each test is named for the rule it holds.
import { expect, test } from '@playwright/test';

test('a document expands its inclusions in place', async ({ page }) => {
	await page.goto('/master/main');
	await expect(page.locator('.fragment .included[data-file="nodes/sy-0002.tex"]')).toBeVisible();
	await expect(page.locator('.fragment section[data-id="sy-0300"] h2')).toBeVisible();
});

test('a heading links to its node, and an equation reference lands on the equation', async ({ page }) => {
	await page.goto('/master/main');
	const head = page.locator('#sy-0200 > h1');
	await expect(head.locator('a.heading-link')).toHaveAttribute('href', '/node/sy-0200');
	const eq = page.locator('a.ref-eq').first();
	await expect(eq).toHaveAttribute('href', /^#sy-\d+/);
	const target = await eq.getAttribute('href');
	await expect(page.locator(target!)).toHaveCount(1);
});

test('a display block never scrolls vertically', async ({ page }) => {
	await page.goto('/master/main');
	await page.waitForSelector('.fragment .math.display');
	// every formula typeset, since MathJax's output is what could overflow
	await page.waitForFunction(() => document.querySelectorAll('.fragment .math:not(:has(mjx-container))').length === 0);
	const r = await page.evaluate(() => {
		const els = [...document.querySelectorAll('.fragment .math.display')] as HTMLElement[];
		return {
			n: els.length,
			// naming one axis makes the browser compute the other to `auto`, and MathJax's hidden accessibility copy is taller than the box, which grew a scrollbar beside a formula that fitted
			axes: [...new Set(els.map((el) => getComputedStyle(el).overflowY))],
			bars: els.filter((el) => el.offsetWidth > el.clientWidth).length
		};
	});
	expect(r.n).toBeGreaterThan(0);
	expect(r.axes).toEqual(['hidden']);
	expect(r.bars).toBe(0);
});

test('the drawing of a formula may be skipped off screen, and its MathML never is', async ({ page }) => {
	await page.goto('/master/main');
	await page.waitForSelector('.fragment mjx-container mjx-assistive-mml');
	const cv = await page.evaluate(() => {
		const c = document.querySelector('.fragment mjx-container')!;
		return [getComputedStyle(c.querySelector(':scope > svg')!).contentVisibility, getComputedStyle(c.querySelector('mjx-assistive-mml')!).contentVisibility];
	});
	// a skipped MathML is dropped from the accessibility tree, and clipped to a pixel it is never on screen to be un-skipped
	expect(cv).toEqual(['auto', 'visible']);
});
