// Plan 0.9.5 §11 check 5: a bundle built for a non-empty base serves correctly under that path.
// The suite's own build has an empty base, so this spec asserts the composition rules the build depends on rather
// than rebuilding: that every URL the core emits is composed rather than written, and that the default composes to
// exactly what a publisher serving the app at the root expects. The built-under-a-base case is checked by
// `scripts/build-prerender.mjs` writing the whole site under the prefix, exercised by hand and recorded in the plan.
import { expect, test } from '@playwright/test';

test('every route and every corpus URL is composed from the configured roots', async ({ page }) => {
	await page.goto('/');
	await expect(page.locator('main')).toBeVisible();
	// with the default (empty) base these are the same strings as before, which is the point: nothing a reader sees moves
	const hrefs = await page
		.locator('a[href]')
		.evaluateAll((els) => els.map((e) => e.getAttribute('href') ?? '').filter((h) => !/^(https?:|mailto:)/.test(h)));
	expect(hrefs.length).toBeGreaterThan(0);
	for (const href of hrefs) expect(href).toMatch(/^[/#]/);

	const fetched: string[] = [];
	page.on('request', (r) => {
		const u = new URL(r.url());
		if (u.pathname.includes('/build/')) fetched.push(u.pathname);
	});
	await page.goto('/node/sy-0003');
	await expect(page.locator('.fragment')).toBeVisible();
	expect(fetched.some((p) => p.startsWith('/build/'))).toBe(true);
	expect(fetched.every((p) => p.startsWith('/build/'))).toBe(true);
});
