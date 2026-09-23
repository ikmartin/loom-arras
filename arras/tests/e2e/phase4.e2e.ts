// What human testing of phases 1–3 asked for (plan 0.13.3 phase 4): a node drawn as its statement and proofs, tabs that name what they hold, a narrow window that gives up the panel first, a selection kept across a load, one local graph, a context whose links keep its node, and the chrome made quieter. Each test is named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { beside, pane } from '../workspace';
import { pickSession } from '../picker';

const manifest = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8'));

async function serve(page: Page, edit: (m: typeof manifest) => void) {
	await page.route('**/build/manifest.json', async (route) => {
		const m = JSON.parse(JSON.stringify(manifest));
		edit(m);
		await route.fulfill({ json: m });
	});
}

async function prefs(page: Page, p: Record<string, unknown>) {
	await page.addInitScript((v) => localStorage.setItem('arras.prefs', JSON.stringify(v)), p);
}

test.describe('the node', () => {
	test('a node draws its statement and proofs, and nothing about them', async ({ page }) => {
		await page.goto('/node/sy-0003');
		const item = pane(page, 0).locator('.page.item.node');
		await expect(item.locator('.fragment .env[data-id="sy-0003"]')).toBeVisible();
		// no heading repeating the tab, no meta row, no list of annotations, no composer, no closure
		await expect(item.locator('h1, h2')).toHaveCount(0);
		await expect(page.getByTestId('annotation-list')).toHaveCount(0);
		await expect(page.getByTestId('closure-open')).toHaveCount(0);
		await expect(page.getByTestId('reference-notes')).toHaveCount(0);
		// the statement leads: its first line within a few lines of the tab strip
		const head = (await pane(page, 0).getByTestId('pane-head-0').boundingBox())!;
		const statement = (await item.locator('.fragment .env[data-id="sy-0003"]').boundingBox())!;
		expect(statement.y - (head.y + head.height)).toBeLessThan(60);
	});

	test('Show ids puts the id and state in the gutter, as in a document', async ({ page }) => {
		await prefs(page, { ids: true });
		await page.goto('/node/sy-0003');
		const margin = pane(page, 0).locator('.fragment .env[data-id="sy-0003"] > .node-margin');
		await expect(margin).toBeVisible();
		await expect(margin).toContainText('sy-0003');
	});

	test("what the node is about stands in its context", async ({ page }) => {
		await page.goto('/node/sy-0002' + beside('/context/sy-0002'));
		const context = pane(page, 1).getByTestId('context');
		await expect(context.getByTestId('version').first()).toContainText('text of @1');
		await expect(context.getByTestId('reference-notes')).toBeVisible();
		await expect(context.getByTestId('closure-open')).toBeVisible();
	});
});

test.describe('tabs', () => {
	test("a context is marked by a glyph and named by its node, and says so where it is read as text", async ({ page }) => {
		await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
		const tab = pane(page, 1).getByTestId('item-tab').getByRole('tab');
		await expect(tab.locator('.marker svg')).toHaveCount(1);
		await expect(tab).toHaveAttribute('aria-label', /^context of /);
		await expect(tab).not.toContainText('context ·');
	});

	test('a name that does not fit ends in an ellipsis, never under the controls', async ({ page }) => {
		await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
		const label = pane(page, 0).getByTestId('item-tab').getByRole('tab');
		// the active tab of two shows its controls; the label stops short of them
		const pad = await label.evaluate((l) => parseFloat(getComputedStyle(l).paddingRight));
		expect(pad).toBeGreaterThanOrEqual(36);
		expect(await label.evaluate((l) => getComputedStyle(l).textOverflow)).toBe('ellipsis');
	});
});

test.describe('the work', () => {
	test("a work's tools stay, greyed, off the paper", async ({ page }) => {
		await serve(page, (m) => (m.references.Kre99.artifacts.pdf = true));
		await page.goto('/library/Kre99');
		await expect(page.getByTestId('tool-select')).toBeEnabled();
		await page.getByTestId('tab-info').click();
		await expect(page.getByTestId('tool-select')).toBeDisabled();
		await expect(page.getByTestId('zoom-at')).toBeDisabled();
		await expect(page.getByTestId('page-at')).toBeDisabled();
		await page.getByTestId('tab-paper').click();
		await expect(page.getByTestId('zoom-at')).toBeEnabled();
	});
});

test.describe('a narrow window', () => {
	test('the panel goes first, and the rail keeps its parts apart', async ({ page }) => {
		await serve(page, (m) => (m.references.Kre99.artifacts.pdf = true));
		await page.setViewportSize({ width: 1100, height: 800 });
		await page.goto('/library/Kre99');
		await expect(page.locator('.panel.away')).toHaveCount(1);
		const parts = page.getByTestId('reading-rail').locator('> *');
		await expect(parts).toHaveCount(3);
		const boxes = await parts.evaluateAll((els) => els.map((e) => (e.firstElementChild ?? e).getBoundingClientRect()).map((r) => [r.left, r.right]));
		for (let i = 1; i < boxes.length; i++) expect(boxes[i][0]).toBeGreaterThanOrEqual(boxes[i - 1][1] - 1);
		// the reader's stored choice is not rewritten by the window's width
		expect(await page.evaluate(() => JSON.parse(localStorage.getItem('arras.prefs') ?? '{}').panel)).not.toBe(false);
	});

	test('when the parts cannot fit, the filter and the discussion go behind ⋯ and the cluster stays', async ({ page }) => {
		await serve(page, (m) => (m.references.Kre99.artifacts.pdf = true));
		await page.setViewportSize({ width: 760, height: 800 });
		await page.goto('/library/Kre99');
		await expect(page.getByTestId('rail-more-toggle')).toBeVisible();
		await expect(page.getByTestId('zoom-at')).toBeVisible();
		await expect(page.getByTestId('reading-rail').getByTestId('show-current')).toHaveCount(0);
		await page.getByTestId('rail-more-toggle').click();
		await expect(page.getByTestId('rail-more').getByTestId('show-current')).toBeVisible();
		await expect(page.getByTestId('rail-more').getByTestId('open-discussion')).toBeVisible();
	});
});

test.describe('sessions', () => {
	test('the chosen session is still chosen after a load', async ({ page }) => {
		await page.goto('/master/main');
		await pickSession(page, 's-2026-09-16-0001');
		await expect(page.getByTestId('session-footer')).toHaveAttribute('aria-label', /^annotations are written into/);
		await page.reload();
		await expect(page.getByTestId('session-footer')).toHaveAttribute('aria-label', /^annotations are written into/);
		await expect(page.getByTestId('open-discussion')).toBeEnabled();
	});

	test('a stored session the corpus no longer lists is let go', async ({ page }) => {
		await page.addInitScript(() => localStorage.setItem('arras.session-view', JSON.stringify({ selected: 's-gone', view: 'all', showClosed: false })));
		await page.goto('/master/main');
		await expect(page.getByTestId('session-footer-name')).toHaveText('no session selected');
		await expect.poll(() => page.evaluate(() => JSON.parse(localStorage.getItem('arras.session-view') ?? '{}').selected)).toBeFalsy();
	});
});

test.describe('panes', () => {
	test('one local graph on screen: a context beside a document stands the float down', async ({ page }) => {
		await page.addInitScript(() => localStorage.setItem('arras.localGraph', 'open'));
		await page.goto('/master/main' + beside('/context/sy-0003'));
		await expect(pane(page, 1).getByTestId('local-graph-panel')).toBeVisible();
		await pane(page, 0).locator('.fragment').first().click({ position: { x: 5, y: 5 } });
		await expect(pane(page, 0).getByTestId('local-graph-panel')).toHaveCount(0);
		await expect(page.getByTestId('local-graph-open')).toHaveCount(0);
		// the float's stored preference is untouched: alone, the document shows it again
		await page.goto('/master/main');
		await expect(pane(page, 0).getByTestId('local-graph-panel')).toBeVisible();
	});

	test("a context's links open in its own pane, so the node it belongs to stays", async ({ page }) => {
		await page.goto('/node/sy-0005' + beside('/context/sy-0005'));
		const link = pane(page, 1).getByTestId('context').locator('a[href*="/node/sy-0002"]').first();
		await link.click();
		await expect(pane(page, 0).locator('.fragment').first()).toBeVisible();
		await expect.poll(() => new URL(page.url()).pathname).toBe('/node/sy-0005');
		await expect(pane(page, 1).getByTestId('item-tab')).toHaveCount(2);
		await expect(pane(page, 1).getByTestId('context')).toHaveCount(0);
	});

	test('the focused pane is marked by its shadow, with no line on its head', async ({ page }) => {
		await page.goto('/master/main' + beside('/node/sy-0003'));
		await expect(pane(page, 0)).toHaveClass(/focused/);
		expect(await pane(page, 0).getByTestId('pane-head-0').evaluate((h) => getComputedStyle(h).boxShadow)).toBe('none');
		expect(await pane(page, 0).evaluate((p) => getComputedStyle(p).boxShadow)).not.toBe('none');
	});
});
