// A node's own page: its statement and proofs and nothing about them, read as it was written on asking, and a missing proof said where the proof would be. Each test is named for the rule it holds.
import { expect, test } from '@playwright/test';
import { beside, pane } from '../workspace';
import { serve } from '../manifest';

test('a node draws its statement, typeset, and its proofs, and nothing about them', async ({ page }) => {
	await page.goto('/node/sy-0003');
	const item = pane(page, 0).locator('.page.item.node');
	const statement = item.locator('.fragment .env[data-id="sy-0003"]');
	await expect(statement).toBeVisible();
	await expect(item.locator('.fragment .env-label .number')).toHaveText('2.1');
	await expect(item.locator('.fragment mjx-container').first()).toBeVisible();
	await expect(item.locator('.fragment details.env-proof')).toHaveCount(2);
	// no heading repeating the tab, no list of annotations, no closure, no citation notes: those are the context's
	await expect(item.locator('h1, h2')).toHaveCount(0);
	await expect(page.getByTestId('annotation-list')).toHaveCount(0);
	await expect(page.getByTestId('closure-open')).toHaveCount(0);
	await expect(page.getByTestId('reference-notes')).toHaveCount(0);
	// the statement leads: its first line within a few lines of the tab strip
	const head = (await pane(page, 0).getByTestId('pane-head-0').boundingBox())!;
	const top = (await statement.boundingBox())!;
	expect(top.y - (head.y + head.height), 'the statement top below the tab strip, px').toBeLessThan(60);
});

test('a node can be read as it was written', async ({ page }) => {
	// the source is fetched one key at a time from build/source/, only when asked
	await page.goto('/node/sy-0003');
	await expect(page.locator('.fragment .env').first()).toBeVisible();
	const toggle = page.getByTestId('source-toggle').first();
	await expect(toggle).toHaveText('verbatim code'); // the control names what a click gives, not what is on screen
	await toggle.click();
	const verbatim = page.getByTestId('verbatim').first();
	await expect(verbatim).toBeVisible();
	await expect(verbatim).toContainText('\\begin{theorem}'); // the LaTeX, not the rendering
	await expect(page.locator('.fragment .env')).toHaveCount(0); // and the rendering stands aside
	await expect(toggle).toHaveText('rendered latex');
	await toggle.click();
	await expect(page.locator('.fragment .env').first()).toBeVisible();
});

test('a missing proof is said where the proof would be, and its diagnostic is in the context', async ({ page }) => {
	await serve(page, (m) => {
		m.diagnostics.push({ severity: 'warning', code: 'loom:missing-proof', message: 'No proof attached', locations: [], keys: ['sy-0003'] });
	});
	await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
	const said = pane(page, 0).getByTestId('missing-proof');
	await expect(said).toHaveText('No proof is attached.');
	// after the statement, not above it: the statement leads
	const statement = (await pane(page, 0).locator('.fragment .env[data-id="sy-0003"]').boundingBox())!;
	expect((await said.boundingBox())!.y).toBeGreaterThan(statement.y);
	await expect(pane(page, 1).getByTestId('context')).toContainText('No proof attached');
});
