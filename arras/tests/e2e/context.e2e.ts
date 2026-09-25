// A node's context, read beside the node: its lists named as a reader names things, what it rests on and what rests on it, its relations and citations, and nothing said about what is absent. Each test is named for the rule it holds.
import { expect, test } from '@playwright/test';
import { beside, pane } from '../workspace';
import { manifest } from '../manifest';

test('it says nothing about absences: no caption over a lone node, no "unreachable", no document it is not in', async ({ page }) => {
	// sy-0009 is reached by no document, and loom says so in a diagnostic the context must not repeat
	expect(manifest.nodes['sy-0009'].reached_by).toEqual([]);
	expect(manifest.diagnostics.filter((d: { keys: string[] }) => d.keys.includes('sy-0009')).map((d: { code: string }) => d.code)).toContainEqual(expect.stringMatching(/unreachable$/));
	await page.goto('/node/sy-0009' + beside('/context/sy-0009'));
	const context = pane(page, 1).getByTestId('context');
	await expect(context.getByTestId('local-graph-panel')).toBeVisible();
	await expect(context).not.toContainText('unreachable');
	await expect(context).not.toContainText('no master reaches');
	await expect(context).not.toContainText('depends on nothing');
	await expect(context).not.toContainText('no document includes');
	const labels = await context.locator('.rail-label').allInnerTexts();
	expect(labels.filter((l) => /^in\b/i.test(l.trim()))).toEqual([]);
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

test('what the node is about stands in its context, with the landmark its text was recorded at', async ({ page }) => {
	await page.goto('/node/sy-0002' + beside('/context/sy-0002'));
	const context = pane(page, 1).getByTestId('context');
	await expect(context.getByTestId('version').first()).toContainText('text of @1');
	await expect(context.getByTestId('reference-notes')).toBeVisible();
	await expect(context.getByTestId('closure-open')).toBeVisible();
});

test('it answers both closure questions without leaving the node', async ({ page }) => {
	// the graph says what this would disturb, the stack says what it rests on; neither is a route
	await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
	const graphLink = page.getByTestId('context').locator('[data-testid="local-graph"] a').first();
	await expect(graphLink).toBeVisible();

	const opener = page.getByTestId('closure-open');
	await opener.locator('> summary').click();
	const panel = page.getByTestId('closure-panel');
	await expect(panel).toBeVisible();
	const shallow = await panel.locator('ol.stack > li').count();
	expect(shallow).toBeGreaterThan(1);
	await expect(panel.locator('ol.stack > li').last()).toHaveClass(/centre/); // the result read is last

	await page.getByTestId('closure-depth-2').click();
	await expect.poll(() => panel.locator('ol.stack > li').count()).toBeGreaterThanOrEqual(shallow);
});

test('see also lists both directions and says where each node is reached', async ({ page }) => {
	await page.goto('/node/sy-0009' + beside('/context/sy-0009'));
	const list = page.getByTestId('relations-see');
	await expect(list.locator('a[href$="/node/sy-0008"]')).toBeVisible();
	await expect(list).toContainText('drafting/main.tex'); // the related node is reached by the paper

	await page.goto('/node/sy-0008' + beside('/context/sy-0008')); // the relation is declared on the other node and shows here too
	await expect(page.getByTestId('relations-see').getByRole('link', { name: /Loose/ })).toBeVisible();
	await expect(page.getByTestId('relations-see')).toContainText('no document'); // where a related node is reached, or that nothing reaches it
});

test('an unknown relation kind renders as a labelled list of links', async ({ page }) => {
	await page.route('**/build/manifest.json', async (route) => {
		const res = await route.fetch();
		const m = await res.json();
		m.relations = [{ from: 'sy-0003', to: 'sy-0001', kind: 'contradicts', src: { file: 'x', line: 1 } }];
		await route.fulfill({ response: res, json: m });
	});
	await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
	const list = page.getByTestId('relations-contradicts');
	await expect(list).toBeVisible();
	await expect(list.getByRole('link').first()).toHaveAttribute('href', '/node/sy-0001');
});

test('it shows the citations suggested for the node and those already accepted', async ({ page }) => {
	await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
	const notes = pane(page, 1).getByTestId('reference-notes');
	await expect(notes).toBeVisible();
	await expect(notes).toContainText('Accepted, not yet in the bibliography');
	await expect(notes).toContainText('identifier unconfirmed'); // a breadcrumb, never a second source of identity truth
	await page.goto('/node/sy-0002' + beside('/context/sy-0002'));
	await expect(pane(page, 1).getByTestId('reference-notes')).toContainText('Suggested citations');
});
