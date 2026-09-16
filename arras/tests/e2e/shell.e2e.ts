import { expect, test } from '@playwright/test';

const SHELLS = ['a', 'b', 'c'] as const;

for (const shell of SHELLS) {
	test(`shell ${shell} contains the same elements as the others`, async ({ page }) => {
		await page.goto(`/master/main?shell=${shell}`);
		await expect(page.locator('html')).toHaveAttribute('data-shell', shell);
		// the view switcher, the document picker, the contents tree, the search affordance and the counts are in every arrangement
		await expect(page.getByRole('link', { name: 'graph', exact: true })).toBeVisible();
		await expect(page.getByRole('combobox', { name: 'Document' })).toBeVisible();
		await expect(page.getByRole('navigation', { name: 'Contents' })).toBeVisible();
		await expect(page.getByRole('button', { name: 'Search' })).toBeVisible();
		await expect(page.getByTestId('counts')).toContainText('nodes');
	});
}

test('the default shell is the icon strip', async ({ page }) => {
	await page.goto('/');
	await expect(page.locator('html')).toHaveAttribute('data-shell', 'c');
});

test('the contents rail scrolls rather than overflowing, and its last entry can be reached', async ({ page }) => {
	await page.setViewportSize({ width: 1280, height: 320 }); // short enough that the fixture's contents cannot fit
	await page.goto('/master/main');
	const rail = page.getByRole('navigation', { name: 'Contents' });
	const box = await rail.evaluate((el) => ({ scroll: el.scrollHeight, client: el.clientHeight, overflow: getComputedStyle(el).overflowY }));
	expect(box.overflow).toBe('auto');
	expect(box.scroll).toBeGreaterThan(box.client);
	const last = rail.locator('a').last();
	await last.scrollIntoViewIfNeeded();
	await expect(last).toBeInViewport();
});

test('the contents tree is in document order and stops above paragraph units', async ({ page }) => {
	await page.goto('/master/main');
	const entries = page.getByRole('navigation', { name: 'Contents' }).locator('a');
	await expect(entries.first()).toContainText('Introduction');
	const texts = await entries.allInnerTexts();
	expect(texts.some((t) => t.includes('Results'))).toBe(true);
	expect(texts.some((t) => t.includes('paragraph'))).toBe(false);
});

test('a contents entry scrolls the document instead of navigating away', async ({ page }) => {
	await page.goto('/master/main');
	const entry = page.getByRole('navigation', { name: 'Contents' }).getByRole('link', { name: /Results/ });
	await entry.click();
	await expect(page).toHaveURL(/\/master\/main#sy-0200$/);
	await expect(page.locator('#sy-0200')).toBeInViewport();
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

test('the display preferences survive a reload and change the document', async ({ page }) => {
	await page.goto('/');
	await page.getByTestId('settings-toggle').click();
	await page.getByTestId('theme-dark').click();
	await page.getByTestId('shell-a').click();
	await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
	await expect(page.locator('html')).toHaveAttribute('data-shell', 'a');

	await page.reload();
	await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
	await expect(page.locator('html')).toHaveAttribute('data-shell', 'a');
});

test('no route reaches an unknown key from review, blockers or the problems page', async ({ page }) => {
	for (const start of ['/review', '/blockers', '/problems']) {
		await page.goto(start);
		await expect(page.locator('main a[href^="/node/"]').first()).toBeAttached();
		const hrefs = await page.locator('main a[href^="/node/"]').evaluateAll((els) => [...new Set(els.map((e) => (e as HTMLAnchorElement).getAttribute('href')!))]);
		expect(hrefs.length).toBeGreaterThan(0);
		for (const href of hrefs) {
			await page.goto(href.split('#')[0]);
			await expect(page.locator('main h1').first(), `${start} links to ${href}`).not.toHaveText('Unknown key');
		}
	}
});

test('the graph toggle keeps the selection and both layouts draw their edges', async ({ page }) => {
	await page.goto('/graph');
	await expect(page.getByTestId('layout-force')).toHaveAttribute('aria-pressed', 'true');
	await page.getByTestId('gnode-sy-0003').click();
	await expect(page.locator('aside').getByRole('link', { name: /Theorem/ })).toBeVisible();
	const forceEdges = await page.locator('svg path.edge').count();
	expect(forceEdges).toBeGreaterThan(0);

	await page.getByTestId('layout-layered').click();
	await expect(page.getByTestId('layout-layered')).toHaveAttribute('aria-pressed', 'true');
	await expect(page.locator('aside').getByRole('link', { name: /Theorem/ })).toBeVisible();
	await expect(page.locator('svg path.edge')).toHaveCount(forceEdges);
});

test('the read view has gutters, with the margin annotation in one and the comments in the other', async ({ page }) => {
	await page.setViewportSize({ width: 1440, height: 1000 });
	await page.goto('/master/main');
	await page.waitForSelector('.fragment .env[data-key]');

	const env = page.locator('.fragment .env[data-key="sy-0001"]');
	const margin = env.locator('.node-margin');
	await expect(margin).toContainText('sy-0001');
	await expect(margin).toContainText('accepted');

	const envBox = (await env.boundingBox())!;
	const marginBox = (await margin.boundingBox())!;
	// the annotation sits wholly in the left gutter, ending where the environment's accent rule begins
	expect(marginBox.x + marginBox.width).toBeLessThanOrEqual(envBox.x + 1);

	const comment = page.locator('aside.comment-slot.gutter[data-slot-for="sy-0001"]');
	await expect(comment).toBeVisible();
	const commentBox = (await comment.boundingBox())!;
	// and the comment sits wholly in the right gutter, beginning where the text column ends
	expect(commentBox.x).toBeGreaterThanOrEqual(envBox.x + envBox.width - 1);
	await expect(comment.locator('article.box')).toHaveCount(1);
	// aligned with the node it is about
	expect(Math.abs(commentBox.y - envBox.y)).toBeLessThan(40);

	// the two gutters are the same width, and the text keeps its measure between them
	const host = (await page.locator('.gutters').boundingBox())!;
	const left = envBox.x - host.x;
	const right = host.x + host.width - (envBox.x + envBox.width);
	expect(Math.abs(left - right)).toBeLessThan(2);
	expect(left).toBeGreaterThan(80);
});

test('a comment with sizeable content stays in the text as a box', async ({ page }) => {
	await page.route('**/build/manifest.json', async (route) => {
		const res = await route.fetch();
		const m = await res.json();
		m.annotations['a-2026-09-16-0006'].body_html =
			'<p>' + 'This comment says a great deal about the involution and its fixed locus. '.repeat(8) + '</p>';
		await route.fulfill({ response: res, json: m });
	});
	await page.setViewportSize({ width: 1440, height: 1000 });
	await page.goto('/master/main');
	await page.waitForSelector('.fragment .env[data-key]');

	const inline = page.locator('aside.comment-slot.inline[data-slot-for="sy-0001"]');
	await expect(inline).toBeVisible();
	await expect(page.locator('aside.comment-slot.gutter[data-slot-for="sy-0001"]')).toHaveCount(0);

	// in the flow: as wide as the text column, and below the node rather than beside it
	const env = (await page.locator('.fragment .env[data-key="sy-0001"]').boundingBox())!;
	const box = (await inline.boundingBox())!;
	expect(box.x).toBeGreaterThanOrEqual(env.x - 1);
	expect(box.width).toBeGreaterThan(env.width / 2);
});

test('the shell fits the window: nothing in a rail falls below the fold', async ({ page }) => {
	await page.setViewportSize({ width: 1440, height: 900 });
	await page.goto('/');
	await page.waitForSelector('main h1');

	const fit = await page.evaluate(() => ({
		inner: window.innerHeight,
		scroll: document.documentElement.scrollHeight
	}));
	expect(fit.scroll).toBeLessThanOrEqual(fit.inner); // a rail is `height: 100vh`, and its padding must count inside that

	// the two things at the foot of the shell are reachable without scrolling
	await expect(page.getByTestId('settings-toggle')).toBeInViewport();
	await expect(page.getByTestId('counts')).toBeInViewport();
});

test('the contents rail shows its scrollbar only while it is in use', async ({ page }) => {
	await page.setViewportSize({ width: 1440, height: 340 });
	await page.goto('/master/main');
	const rail = page.getByRole('navigation', { name: 'Contents' });
	await expect(rail).toBeVisible();

	const atRest = await rail.evaluate((el) => getComputedStyle(el).scrollbarColor);
	expect(atRest).toContain('rgba(0, 0, 0, 0)'); // the thumb is transparent until the rail is used

    await rail.hover();
	await expect
		.poll(async () => rail.evaluate((el) => getComputedStyle(el).scrollbarColor))
		.not.toContain('rgba(0, 0, 0, 0) rgba(0, 0, 0, 0)');
});
