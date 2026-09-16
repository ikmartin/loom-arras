import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

const manifest = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8'));

const routes: [string, string][] = [
	['/node/sy-0003', 'Parity'],
	['/node/sy-0200', 'Results'],
	['/master/main', 'Widgets, gadgets'],
	['/digest/Kre99', 'Cycle groups'],
	['/review', 'Review'],
	['/problems', 'Problems'],
	['/blockers', 'Blockers'],
	['/graph', 'Graph'],
	['/threads', 'Threads'],
	['/tags', 'Tags'],
	['/tag/orbits', '#orbits'],
	['/taxa', 'Taxa'],
	['/taxon/lemma', 'Lemma'],
	['/references', 'References'],
	['/loose', 'Loose']
];

for (const [path, heading] of routes) {
	test(`route ${path} renders`, async ({ page }) => {
		await page.goto(path);
		await expect(page.locator('main h1').first()).toContainText(heading);
	});
}

test('node page shows the fragment with typeset math and its proofs', async ({ page }) => {
	await page.goto('/node/sy-0003');
	await expect(page.locator('.fragment .env[data-id="sy-0003"]')).toBeVisible();
	await expect(page.locator('.fragment details.env-proof')).toHaveCount(2);
	await expect(page.locator('.fragment mjx-container').first()).toBeVisible();
	await expect(page.locator('.fragment .env-label .number')).toHaveText('2.1');
});

test('master view expands inclusions in place', async ({ page }) => {
	await page.goto('/master/main');
	await expect(page.locator('.fragment .included[data-file="nodes/sy-0002.tex"]')).toBeVisible();
	await expect(page.locator('.fragment section[data-id="sy-0300"] h2')).toBeVisible();
});

test('problems page lists every diagnostic code', async ({ page }) => {
	await page.goto('/problems');
	const codes = new Set<string>(manifest.diagnostics.map((d: { code: string }) => d.code));
	for (const code of codes) await expect(page.locator(`main h2 code`, { hasText: code }).first()).toBeVisible();
});

test('unknown state labels and codes render generically', async ({ page }) => {
	await page.route('**/build/manifest.json', async (route) => {
		const m = JSON.parse(JSON.stringify(manifest));
		m.keys['sy-0003'].state = 'mysterious';
		m.diagnostics.push({ severity: 'info', code: 'other:code', message: 'from another publisher', locations: [], keys: [] });
		await route.fulfill({ json: m });
	});
	await page.goto('/node/sy-0003');
	await expect(page.locator('.chip', { hasText: 'statement mysterious' })).toBeVisible();
	await page.goto('/problems');
	await expect(page.locator('main h2 code', { hasText: 'other:code' })).toBeVisible();
});

test('interface version mismatch shows one diagnostic and nothing else', async ({ page }) => {
	await page.route('**/build/manifest.json', async (route) => {
		const m = JSON.parse(JSON.stringify(manifest));
		m.interface_version = 99;
		await route.fulfill({ json: m });
	});
	await page.goto('/node/sy-0003');
	await expect(page.locator('main h1')).toHaveText('Problems');
	await expect(page.locator('main code', { hasText: 'loom:interface-version' })).toBeVisible();
	await expect(page.locator('.fragment')).toHaveCount(0);
});

test('search finds by id, alias, title, and tag', async ({ page }) => {
	await page.goto('/');
	const data = await page.locator('ninja-keys').evaluate((el) => (el as unknown as { data: { id: string; keywords: string; title: string }[] }).data);
	expect(data.some((d) => d.id === 'sy-0002')).toBe(true);
	expect(data.some((d) => d.keywords.includes('def:gadget'))).toBe(true);
	expect(data.some((d) => d.title.includes('Parity'))).toBe(true);
	expect(data.some((d) => d.keywords.includes('orbits'))).toBe(true);
});

test('live reload follows the manifest only', async ({ page }) => {
	let version = 0;
	await page.route('**/build/manifest.json', async (route) => {
		const m = JSON.parse(JSON.stringify(manifest));
		if (version > 0) m.corpus.root_label = 'Renamed corpus';
		await route.fulfill({ json: m });
	});
	await page.goto('/');
	await expect(page.locator('main h1')).toHaveText('Widgets, gadgets, and their fixed loci');
	version = 1;
	await expect(page.locator('main h1')).toHaveText('Renamed corpus', { timeout: 5000 });
});
