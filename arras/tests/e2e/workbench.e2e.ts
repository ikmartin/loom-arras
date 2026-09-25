// The workbench in the viewer (book 15.2, 15.3.1, 15.3.5): landmarks as documents of their own, a corpus named by its project, a corpus with nothing being worked on, and a doubly-defined id. The fixes a diagnostic offers are in problems.e2e.ts, and the badge that says a text is one a landmark recorded is in context.e2e.ts.
import { expect, test } from '@playwright/test';

test('the documents section lists the landmarks and the working drafts in two groups', async ({ page }) => {
	// a list rather than a dropdown: a dropdown shows one name at a time, cannot say which draft is conflicted, and hides the landmarks behind a click
	await page.goto('/');
	await expect(page.getByTestId('docs-drafts')).toBeVisible();
	const canon = page.getByTestId('docs-canon').locator('li');
	// newest landmark first, each named by the step that wrote it
	await expect(canon.first()).toContainText('@5');
	await expect(canon).toHaveCount(3);
	await page.getByTestId('docs-canon').getByRole('link', { name: /widgets-v3/ }).click();
	await expect(page).toHaveURL(/\/canon\/widgets-v3$/);
});

test('a landmark is a document, with no identity and nothing to review', async ({ page }) => {
	await page.goto('/canon/widgets-v1');
	await expect(page.locator('main').getByRole('heading', { level: 1 }).first()).toContainText('Widgets');
	// its step is its identity, so it stands in its tab
	await expect(page.getByTestId('item-tab')).toContainText('widgets-v1 @1');
	const fragment = page.locator('.fragment');
	await expect(fragment.locator('.env').first()).toBeVisible();
	await expect(fragment.locator('.env[data-key], .env[data-id]')).toHaveCount(0); // no theorem in a landmark is a node
	await expect(page.locator('aside.margin')).toHaveCount(0);
	await expect(page.locator('aside.comment-slot')).toHaveCount(0);
	await expect(page.getByTestId('local-graph-open')).toHaveCount(0);
	// its own references stay inside the page; one that pointed at nothing when the landmark was written still points at nothing
	const hrefs = await fragment
		.locator('a.ref:not(.ref-dangling)')
		.evaluateAll((els) => els.map((e) => e.getAttribute('href')));
	expect(hrefs.length).toBeGreaterThan(0);
	for (const href of hrefs) expect(href).toMatch(/^#/);
});

test('the corpus is named by the project, not by its directory', async ({ page }) => {
	await page.goto('/');
	await expect(page).toHaveTitle('The synthetic quilt');
	await expect(page.locator('main')).toContainText('Canon');
});

test('a doubly defined id has no text, and says where both definitions are', async ({ page }) => {
	await page.goto('/problems?code=duplicate-id');
	const item = page.locator('section.group li').first();
	await expect(item).toContainText('is defined by');
	const key = await item.locator('a.key').first().innerText();
	await page.goto('/node/' + key);
	const conflicted = page.getByTestId('conflicted');
	await expect(conflicted).toContainText('Defined in two files');
	await expect(conflicted.locator('code')).toHaveCount(2);
	await expect(conflicted.getByRole('link', { name: 'problems' })).toBeVisible();
	await expect(page.locator('.fragment')).toHaveCount(0);
});

test('with nothing being worked on, every view says so and points at the landmarks', async ({ page }) => {
	await page.route('**/build/manifest.json', async (route) => {
		const res = await route.fetch();
		const m = await res.json();
		m.masters = [];
		await route.fulfill({ response: res, json: m });
	});
	for (const path of ['/', '/graph', '/review', '/master/main']) {
		await page.goto(path);
		await expect(page.getByTestId('no-drafts')).toBeVisible();
		await expect(page.getByTestId('no-drafts')).toContainText('Nothing is being worked on');
	}
	// the read icon falls back to the newest landmark
	const read = page.locator('a[aria-label="read"], a[title="read"]').first();
	if (await read.count()) await expect(read).toHaveAttribute('href', '/canon/widgets-v3');
});
