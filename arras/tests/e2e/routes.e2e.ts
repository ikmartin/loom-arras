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
	['/blockers', 'Review'],
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

test('marks and boxes on the annotated node; discarded hidden by default', async ({ page }) => {
	await page.goto('/node/sy-0003');
	await expect(page.locator('.fragment mark.annotation')).toHaveCount(2);
	await expect(page.getByTestId('annotation-list').locator('article.box')).toHaveCount(2);
	await page.locator('.fragment mark.annotation').first().click();
	await expect(page.locator('article.box.active')).toHaveCount(1);
	await expect(page.locator('article.box.active > header .kind')).toHaveText('objection');
	await expect(page.locator('article.box.active .reply')).toHaveCount(1);
	await page.goto('/node/sy-000A');
	await expect(page.getByTestId('annotation-list').locator('article.box')).toHaveCount(0);
	await page.getByLabel('show discarded').check();
	await expect(page.getByTestId('annotation-list').locator('article.box.discarded')).toHaveCount(1);
});

test('review panel shows stale causes and expands a row into a two-column diff', async ({ page }) => {
	await page.goto('/review');
	await expect(page.getByTestId('review-counts')).toContainText('5 stale');
	const row = page.locator('table.list tr', { hasText: 'sy-0002/proof' });
	await expect(row).toContainText('dependency-changed sy-0001');
	const stale = page.locator('table.list tr', { hasText: 'sy-0001' }).first();
	await expect(stale).toContainText('1 detached');

	await page.getByTestId('expand-sy-0001').first().click(); // the key is listed once per stale cause
	const diff = page.getByTestId('expansion-sy-0001').first().getByTestId('diff').first(); // own text first, then each changed dependency
	await expect(diff).toBeVisible();
	await expect(diff.locator('tr.change td.l').first()).toContainText('satisfying');
	await expect(diff.locator('tr.change td.r').first()).toContainText('involution');
});

test('review panel explains itself and names the command behind each state', async ({ page }) => {
	await page.goto('/review');
	await expect(page.locator('p.lead')).toContainText('states are recorded from the command line');
	await page.getByTestId('help-review').click();
	const help = page.getByTestId('help-panel-review');
	await expect(help).toContainText('stale');
	await expect(help).toContainText('accept');
});

test('digest page lists results with their citers, and the references index counts them', async ({ page }) => {
	await page.goto('/digest/Kre99');
	const item = page.locator('li:has(> a:first-child[href="/node/Kre99-thm-2.1"])');
	await expect(item).toContainText('sy-000A'); // \cite[Theorem 2.1]{Kre99} resolved to this result by its locator
	await page.goto('/references');
	const row = page.locator('tr', { hasText: 'Kre99' });
	await expect(row).toContainText('2 results (manual)');
	await page.goto('/problems');
	await expect(page.getByText('names no result in the digest of Kre99').first()).toBeVisible();
});

test("thread page shows the run's messages, attachments, and log", async ({ page }) => {
	await page.goto('/threads');
	await expect(page.getByText('referee sy-0003').first()).toBeVisible();
	await page.goto('/thread/2026-09-16T00-00-referee');
	await expect(page.getByText('hostile review of the parity theorem').first()).toBeVisible();
	await expect(page.locator('pre', { hasText: 'loom comment sy-0003' })).toHaveCount(1); // the log, collapsed by default
	await expect(page.getByText('annotations.json').first()).toBeVisible();
});


test('see also lists both directions and says where each node is reached', async ({ page }) => {
	await page.goto('/node/sy-0009');
	const list = page.getByTestId('relations-see');
	await expect(list.getByRole('link', { name: /Gadget/ })).toBeVisible();
	await expect(list).toContainText('drafting/main.tex'); // the related node is reached by the paper

	await page.goto('/node/sy-0008'); // the relation is declared on the other node and shows here too
	await expect(page.getByTestId('relations-see').getByRole('link', { name: /Loose/ })).toBeVisible();
	await expect(page.getByTestId('relations-see')).toContainText('loose');
});

test('an unknown relation kind renders as a labelled list of links', async ({ page }) => {
	await page.route('**/build/manifest.json', async (route) => {
		const res = await route.fetch();
		const m = await res.json();
		m.relations = [{ from: 'sy-0003', to: 'sy-0001', kind: 'contradicts', src: { file: 'x', line: 1 } }];
		await route.fulfill({ response: res, json: m });
	});
	await page.goto('/node/sy-0003');
	const list = page.getByTestId('relations-contradicts');
	await expect(list).toBeVisible();
	await expect(list.getByRole('link').first()).toHaveAttribute('href', '/node/sy-0001');
});
