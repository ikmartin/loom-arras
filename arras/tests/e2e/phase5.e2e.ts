// The gaps phase 4 left open (plan 0.13.3 phase 5): a context laid out as its design is and silent about absences, a session that names what it touched as a reader would, a rail that states a refusal once, every annotation opened into the flow, and a divider a reader can see. Each test is named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { beside, pane } from '../workspace';

const manifest = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8'));
const REFEREE = 's-2026-09-16-0001';

async function serve(page: Page, edit: (m: typeof manifest) => void) {
	await page.route('**/build/manifest.json', async (route) => {
		const m = JSON.parse(JSON.stringify(manifest));
		edit(m);
		await route.fulfill({ json: m });
	});
}

test.describe('the context', () => {
	test('it says nothing about absences: no caption over a lone node, no "unreachable"', async ({ page }) => {
		expect(manifest.diagnostics.some((d: { code: string; keys: string[] }) => /unreachable$/.test(d.code) && d.keys.includes('sy-0009'))).toBe(true);
		await page.goto('/node/sy-0009' + beside('/context/sy-0009'));
		const context = pane(page, 1).getByTestId('context');
		await expect(context.getByTestId('local-graph-panel')).toBeVisible();
		await expect(context).not.toContainText('unreachable');
		await expect(context).not.toContainText('no master reaches');
		await expect(context).not.toContainText('depends on nothing');
	});

	test('its lists come first, named as a reader names them, and its graph last', async ({ page }) => {
		await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
		const context = pane(page, 1).getByTestId('context');
		const graph = (await context.getByTestId('local-graph-panel').boundingBox())!;
		const first = (await context.locator('.rail-label').first().boundingBox())!;
		expect(first.y).toBeLessThan(graph.y);
		// the document by its file, linked to where the node is in it
		await expect(context.getByRole('link', { name: 'main.tex' })).toBeVisible();
		await expect(context).not.toContainText('drafting/main.tex');
		// a result by taxon and number, a proof as the proof of its result, never a raw key
		await expect(context).toContainText('Definition 1.1');
		await expect(context).toContainText('proof of Lemma');
		await expect(context).not.toContainText('/proof');
		await expect(context.getByRole('link', { name: 'Definition 1.1' }).first()).toHaveAttribute('title', 'sy-0001');
	});
});

test.describe('a session', () => {
	test('its head names what it touched as a reader would, and folds the rest behind a count', async ({ page }) => {
		await serve(page, (m) => {
			m.threads[REFEREE].targets = [...m.threads[REFEREE].targets, 'sy-0008', 'sy-0006', 'sy-0007', 'sy-0001#eq:fix', 'arXiv:math/9810166v2'];
		});
		await page.goto('/session/' + REFEREE);
		const head = page.getByTestId('session-targets');
		await expect(head.locator('a.chip').first()).toHaveText('main.tex'); // the documents first
		await expect(head.getByRole('link', { name: 'Theorem 2.1', exact: true })).toHaveAttribute('title', 'sy-0003');
		await expect(head).not.toContainText('sy-00');
		const more = page.getByTestId('session-targets-more');
		await expect(more).toHaveText(/^and \d+ more$/);
		await more.click();
		await expect(more).toHaveCount(0);
		// an equation is named by its number in its result, and opens the document at it; a cited work's identifier is the work
		await expect(head.getByRole('link', { name: /^\(\d+\) in Definition 1\.1$/ })).toHaveAttribute('href', /\/master\/main#sy-0001-eq-fix$/);
		await expect(head.getByRole('link', { name: 'Kre99' })).toHaveAttribute('href', /\/library\/Kre99/);
	});
});

test.describe('the rail', () => {
	test('refused, its control keeps its name and gives the reason as its title', async ({ page }) => {
		await page.goto('/master/main');
		const open = page.getByTestId('open-discussion');
		await expect(open).toBeDisabled();
		await expect(open).toHaveText('open session discussion');
		await expect(open).toHaveAttribute('title', /No session selected/);
		await expect(page.getByTestId('reading-rail')).not.toContainText('select a session first');
	});

	test('a closed session is read like any other: its discussion opens', async ({ page }) => {
		const closed = manifest.sessions.find((s: { state: string }) => s.state !== 'open');
		expect(closed).toBeTruthy();
		await page.addInitScript((id) => localStorage.setItem('arras.session-view', JSON.stringify({ selected: id, view: 'all', showClosed: true })), closed.id);
		await page.goto('/master/main');
		const open = page.getByTestId('open-discussion');
		await expect(open).toBeEnabled();
		await open.click();
		await expect(pane(page, 1).getByTestId('discussion')).toBeVisible();
	});
});

test.describe('annotations', () => {
	test('show all opens every box in the flow, and a single mark still floats', async ({ page }) => {
		await page.addInitScript(() => localStorage.setItem('arras.prefs', JSON.stringify({ comments: 'floating' })));
		await page.goto('/node/sy-0003');
		const mark = page.locator('.fragment mark.annotation').first();
		await mark.click();
		await expect(page.locator('.comment-slot.expanded.floating')).toHaveCount(1);
		await page.getByTestId('toggle-annotations').click();
		const open = page.locator('aside.comment-slot.expanded');
		await expect.poll(() => open.count()).toBeGreaterThan(1);
		await expect(page.locator('.comment-slot.expanded.floating')).toHaveCount(0);
		await page.getByTestId('toggle-annotations').click();
		await expect(open).toHaveCount(0);
		await mark.click();
		await expect(page.locator('.comment-slot.expanded.floating')).toHaveCount(1);
	});
});

test.describe('the divider', () => {
	test('is a 3px rule, beneath what a pane opens over the text', async ({ page }) => {
		await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
		const width = await page.getByTestId('divider').evaluate((d) => getComputedStyle(d, '::before').width);
		expect(width).toBe('3px');
		// a box floating over the text of either pane is drawn over the divider, not under it
		const z = await page.evaluate(() => [...document.querySelectorAll('[data-pane]')].map((p) => Number(getComputedStyle(p).zIndex)));
		const dz = await page.getByTestId('divider').evaluate((d) => Number(getComputedStyle(d).zIndex));
		expect(z.every((n) => n > dz)).toBe(true);
	});
});
