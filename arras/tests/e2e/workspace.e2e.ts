// Reading mode as items in two panes (plan 0.13.3 phase 2). Each test is named for the rule in the plan's Tests section it holds, and fails if that rule is broken.
import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { beside, pane, scrollPane } from '../workspace';

const manifest = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8'));

// the smallest PDF a browser accepts, so a work has a page to draw
const PDF = `%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj
trailer<</Root 1 0 R>>
%%EOF`;

/** Serve the fixture with Kre99 and Har77 filed, so both are works with pages. */
async function withPapers(page: Page) {
	await page.route('**/build/manifest.json', async (route) => {
		const m = JSON.parse(JSON.stringify(manifest));
		m.references.Kre99.artifacts.pdf = true;
		m.references.Har77.artifacts.pdf = true;
		await route.fulfill({ json: m });
	});
	await page.route('**/paper.pdf', (route) => route.fulfill({ body: PDF, contentType: 'application/pdf' }));
}

const tabs = (page: Page, index: number) => pane(page, index).getByTestId('item-tab');

test.describe('P1 · open on the thing itself', () => {
	test('a document opens on the paper', async ({ page }) => {
		await page.setViewportSize({ width: 1440, height: 900 });
		await page.goto('/master/main');
		const fragment = pane(page, 0).locator('.fragment').first();
		await expect(fragment).toBeVisible();
		const at = await page.evaluate(() => {
			const top = document.querySelector('[data-testid="reading-rail"]')!.getBoundingClientRect().bottom;
			const first = document.querySelector('[data-pane] .fragment')!.getBoundingClientRect().top;
			const column = document.querySelector('[data-pane] .gutters > .column')!.getBoundingClientRect();
			const visible = Math.max(0, Math.min(column.bottom, innerHeight) - Math.max(column.top, 0));
			return { lead: first - top, share: (column.width * visible) / (innerWidth * innerHeight) };
		});
		expect(at.lead).toBeLessThanOrEqual(100); // the first line, not chrome, begins the content area
		expect(at.share).toBeGreaterThanOrEqual(0.45); // and the prose column is most of the first screen
	});

	test('a work opens on the paper', async ({ page }) => {
		await withPapers(page);
		await page.setViewportSize({ width: 1440, height: 900 });
		await page.goto('/library/Kre99');
		const paper = pane(page, 0).getByTestId('pdf-doc');
		await expect(paper).toBeVisible();
		const box = (await paper.boundingBox())!;
		expect((box.width * box.height) / (1440 * 900)).toBeGreaterThanOrEqual(0.7);
	});

	test('a pane head carries tabs and nothing else', async ({ page }) => {
		await page.goto('/master/main' + beside('/node/sy-0003'));
		for (const i of [0, 1]) {
			const head = page.getByTestId(`pane-head-${i}`);
			await expect(head).toBeVisible();
			const kinds = await head.evaluate((h) => [...h.children].map((c) => (c as HTMLElement).dataset.testid));
			expect(kinds.every((k) => k === 'item-tab')).toBe(true);
		}
	});

	test('no route draws a rail', async ({ page }) => {
		await withPapers(page);
		for (const at of [
			'/master/main' + beside('/node/sy-0003'),
			'/library/Kre99' + beside('/context/sy-0003'),
			'/canon/widgets-v1' + beside('/session/s-2026-09-16-0001')
		]) {
			await page.goto(at);
			await expect(pane(page, 1)).toBeVisible();
			for (const i of [0, 1]) {
				await expect(pane(page, i).locator('[role="toolbar"], .rail, aside.right, [data-testid="reading-rail"], [data-testid="cluster"]')).toHaveCount(0);
			}
		}
	});
});

test.describe('P2 · say it once, in the place that governs it', () => {
	test('a document is opened once', async ({ page }) => {
		await page.goto('/master/main' + beside('/context/sy-0003'));
		await expect(pane(page, 1).getByTestId('context')).toBeVisible();
		// the context names the document the node is in; following it reveals the open one rather than a second tab
		await pane(page, 1).getByRole('link', { name: 'main.tex' }).first().click();
		await expect(tabs(page, 0)).toHaveCount(1);
		await expect(tabs(page, 1)).toHaveCount(1);
		await expect(pane(page, 0)).toHaveClass(/focused/);
		// and so does choosing it in the panel
		await page.getByTestId('docs-drafts').getByRole('link', { name: 'main.tex' }).click();
		await expect(tabs(page, 0)).toHaveCount(1);
	});

	test("a document's controls are drawn once", async ({ page }) => {
		await withPapers(page);
		await page.goto('/library/Kre99' + beside('/library/Har77'));
		await expect(pane(page, 0).getByTestId('pdf-doc')).toBeVisible();
		await expect(pane(page, 1).getByTestId('pdf-doc')).toBeVisible();
		await expect(page.getByRole('textbox', { name: /^Zoom/ })).toHaveCount(1);
	});
});

test.describe('P3 · claim only what is known', () => {
	test('a lone tab offers no controls', async ({ page }) => {
		await page.goto('/master/main');
		await expect(tabs(page, 0)).toHaveCount(1);
		await expect(page.getByTestId('tab-move')).toHaveCount(0);
		await expect(page.getByTestId('tab-close')).toHaveCount(0);
	});

	test('the contents tree is absent for a non-document', async ({ page }) => {
		await page.goto('/master/main' + beside('/node/sy-0003'));
		await expect(page.getByRole('navigation', { name: 'Contents' })).toBeVisible();
		// the tree follows the focused pane (S3)
		await pane(page, 1).locator('.fragment').first().click();
		await expect(page.getByRole('navigation', { name: 'Contents' })).toHaveCount(0);
		await pane(page, 0).locator('.fragment').first().click();
		await expect(page.getByRole('navigation', { name: 'Contents' })).toBeVisible();
	});

	test('a node in no document says nothing about it', async ({ page }) => {
		expect(manifest.nodes['sy-0009'].reached_by).toEqual([]);
		await page.goto('/node/sy-0009' + beside('/context/sy-0009'));
		const context = page.getByTestId('context');
		await expect(context.getByTestId('local-graph-panel')).toBeVisible();
		const labels = await context.locator('.rail-label').allInnerTexts();
		expect(labels.some((l) => /^in\b/i.test(l.trim()))).toBe(false);
		await expect(context).not.toContainText('no document includes');
	});
});

test.describe('P4 · name the question', () => {
	test('the global rail holds two things', async ({ page }) => {
		await page.goto('/master/main');
		const rail = page.getByTestId('reading-rail');
		await expect(rail).toBeVisible();
		expect(await rail.evaluate((r) => r.children.length)).toBe(2);
		await expect(rail.getByRole('group', { name: 'which annotations the page shows' })).toBeVisible();
		await expect(page.getByTestId('cluster')).toBeVisible();
	});

	test('every control names its target', async ({ page }) => {
		for (const [at, name] of [
			['/master/main', 'main.tex'],
			['/node/sy-0003', 'Theorem']
		]) {
			await page.goto(at);
			const cluster = page.getByTestId('cluster');
			await expect(cluster.locator('button, a').first()).toBeVisible();
			const names = await cluster.locator('button, a').evaluateAll((els) => els.map((e) => e.getAttribute('aria-label') ?? ''));
			for (const n of names) expect(n, n).toContain(name);
		}
	});

	test('a control names the destination, not the state', async ({ page }) => {
		await page.goto('/master/main');
		await expect(page.getByTestId('toggle-annotations')).toHaveText('show all annotations');
		await page.goto('/node/sy-0003');
		const source = page.getByTestId('source-toggle');
		await expect(source).toHaveText('verbatim code'); // showing the rendering, it offers the source
		await source.click();
		await expect(source).toHaveText('rendered latex');
	});
});

test.describe('P5 · following a connection must not cost the thing you followed it from', () => {
	test('a link opens beside and leaves its source rendered', async ({ page }) => {
		await page.goto('/master/main');
		await page.waitForSelector('[data-pane="0"] .fragment mjx-container');
		await pane(page, 0).locator('span.cite[data-target="Kre99-thm-2.1"] a').first().click();
		await expect(pane(page, 1)).toBeVisible();
		await expect(tabs(page, 1)).toContainText(['Kre99 · Thm 2.1']);
		await expect(pane(page, 0).locator('.fragment').first()).toBeVisible();
		await expect(tabs(page, 0)).toHaveCount(1);
	});

	test('a panel click does not split', async ({ page }) => {
		await page.goto('/master/main');
		await page.getByTestId('docs-drafts').getByRole('link', { name: 'talk.tex' }).click();
		await expect(pane(page, 1)).toHaveCount(0);
		await expect(tabs(page, 0)).toHaveCount(2);
	});

	test('the preview is not clipped', async ({ page }) => {
		await page.goto('/master/main' + beside('/node/sy-0003'));
		await page.waitForSelector('[data-pane="0"] .fragment mjx-container');
		await pane(page, 0).locator('span.cite[data-target="Kre99-thm-2.1"] a').first().hover();
		const card = page.getByTestId('link-preview');
		await expect(card).toBeVisible();
		// it stands against the window, in no pane, so no pane's edge or divider can cut it
		expect(await card.evaluate((c) => !c.closest('[data-pane]') && getComputedStyle(c).position === 'fixed')).toBe(true);
	});

	test('open here and a click differ only in pane', async ({ page }) => {
		await page.goto('/master/main');
		await page.waitForSelector('[data-pane="0"] .fragment mjx-container');
		const link = pane(page, 0).locator('span.cite[data-target="Kre99-thm-2.1"] a').first();
		await link.hover();
		await page.getByTestId('preview-open-here').click();
		await expect(pane(page, 1)).toHaveCount(0);
		await expect(tabs(page, 0)).toHaveCount(2);
		const here = new URL(page.url()).pathname;
		expect(here).toBe('/node/Kre99-thm-2.1');

		await page.goto('/master/main');
		await page.waitForSelector('[data-pane="0"] .fragment mjx-container');
		await pane(page, 0).locator('span.cite[data-target="Kre99-thm-2.1"] a').first().click();
		await expect(pane(page, 1)).toBeVisible();
		await expect.poll(() => new URL(page.url()).searchParams.get('beside')).toBe(here);
	});

	test('focus follows interaction', async ({ page }) => {
		await page.goto('/master/main' + beside('/node/sy-0003'));
		await expect(pane(page, 1).locator('.fragment').first()).toBeVisible();
		// a wheel over the node's pane: the rail now acts on the node
		await pane(page, 1).hover();
		await page.mouse.wheel(0, 200);
		await expect(page.getByTestId('open-context')).toBeVisible();
		// and a wheel over the document: on the document
		await pane(page, 0).hover();
		await page.mouse.wheel(0, 200);
		await expect(page.getByTestId('open-context')).toHaveCount(0);
		await expect(page.getByTestId('cluster')).toHaveAttribute('aria-label', 'controls for main.tex');
	});
});

test.describe('the arrangement', () => {
	test('the URL reproduces the arrangement', async ({ page }) => {
		await page.goto('/master/main' + beside('/node/sy-0003'));
		await expect(tabs(page, 1)).toHaveCount(1);
		await page.reload();
		await expect(tabs(page, 0)).toHaveText([/main\.tex/]);
		await expect(pane(page, 1).locator('.fragment').first()).toBeVisible();
		await expect(pane(page, 0)).toHaveClass(/focused/);
	});

	test('⇄ moves a tab and focus follows it', async ({ page }) => {
		await page.goto('/master/main');
		await page.getByTestId('docs-drafts').getByRole('link', { name: 'talk.tex' }).click();
		await expect(tabs(page, 0)).toHaveCount(2);
		await tabs(page, 0).nth(1).getByTestId('tab-move').click();
		await expect(tabs(page, 0)).toHaveCount(1);
		await expect(tabs(page, 1)).toHaveText([/talk\.tex/]);
		await expect(pane(page, 1)).toHaveClass(/focused/);
		// moving the last tab of a pane closes it, and the other takes the width
		await tabs(page, 1).first().getByTestId('tab-move').click();
		await expect(pane(page, 1)).toHaveCount(0);
		await expect(tabs(page, 0)).toHaveCount(2);
	});

	test('a scrolled tab is where it was left', async ({ page }) => {
		await page.goto('/master/main');
		await expect(pane(page, 0).locator('.fragment').first()).toBeVisible();
		await scrollPane(page, 0, 'bottom');
		const body = pane(page, 0).locator('> .body');
		const at = await body.evaluate((b) => b.scrollTop);
		expect(at).toBeGreaterThan(0);
		await page.getByTestId('docs-drafts').getByRole('link', { name: 'talk.tex' }).click();
		await tabs(page, 0).first().getByRole('tab').click();
		await expect.poll(() => body.evaluate((b) => b.scrollTop)).toBeGreaterThan(at / 2);
	});
});
