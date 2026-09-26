// The graph: the page's four drawings of what the corpus wrote, and the local graph a context and a document carry. Each test is named for the rule it holds.
import { expect, test } from '@playwright/test';
import { beside, pane, scrollPane } from '../workspace';

test.describe('the graph page', () => {
	test('Scope offers two quilt drawings and four document drawings', async ({ page }) => {
		await page.goto('/graph');
		await expect(page.locator('.toggle button')).toHaveText(['Dots', 'Box']);
		await page.getByLabel('Scope', { exact: true }).selectOption({ index: 1 });
		await expect(page.locator('.toggle button')).toHaveText(['Dots', 'Box', 'Sections', 'Reading Order']);
		await page.getByTestId('layout-sections').click();
		await page.getByLabel('Scope', { exact: true }).selectOption('');
		await expect(page.getByTestId('layout-dots')).toHaveAttribute('aria-pressed', 'true');
	});

	test('readable names identify dots and boxes while hovering keeps the selected statement pinned', async ({ page }) => {
		await page.route('**/build/manifest.json', async (route) => {
			const response = await route.fetch();
			const m = await response.json();
			m.nodes['sy-0003'].name = 'Uniform <energy> bound Ω';
			await route.fulfill({ response, json: m });
		});
		await page.goto('/graph');
		const node = page.getByTestId('gnode-sy-0003');
		await expect(node).toHaveAttribute('aria-label', /Uniform <energy> bound Ω/);
		await node.focus();
		await page.keyboard.press('Enter');
		const rail = page.locator('aside').filter({ has: page.getByRole('link', { name: 'Open in document', exact: true }) });
		await expect(rail.locator('.label').filter({ hasText: 'Uniform <energy> bound Ω' })).toBeVisible();
		await expect(rail.locator('.body.fragment')).not.toBeEmpty();
		await page.getByTestId('gnode-sy-0001').hover();
		await expect(rail.locator('.label').filter({ hasText: 'Uniform <energy> bound Ω' })).toBeVisible();
		await expect(rail.getByText('Direct dependents', { exact: true })).toBeVisible();
		await page.getByTestId('layout-box').click();
		await expect(node.locator('.box-name')).toHaveText('Uniform <energy> bound Ω');
		await expect(node.locator('.id')).toHaveText('sy-0003');
		await expect(page.locator('g.node.selected')).toHaveAttribute('data-testid', 'gnode-sy-0003');
	});

	test('Whole quilt includes the corpus and external nodes', async ({ page }) => {
		await page.goto('/graph');
		await expect(page.getByTestId('gnode-sy-0003')).toHaveCount(1); // the corpus's own results are unchanged
		await expect(page.getByTestId('gnode-Kre99-thm-2.1')).toHaveCount(1);
		await expect(page.locator('[data-testid^="gnode-paper:"]')).toHaveCount(0);
	});

	test('scope lists only documents and the legend highlights without changing scope', async ({ page }) => {
		await page.goto('/graph');
		const panel = page.getByRole('button', { name: 'Show the panel', exact: true });
		if (await panel.isVisible()) await panel.click();
		const scope = page.getByLabel('Scope', { exact: true });
		await expect(scope).toHaveValue('');
		const legend = page.getByRole('group', { name: 'Document membership' });
		const documents = await legend.getByRole('button').allTextContents();
		await expect(scope.locator('option')).toHaveText(['Whole quilt', ...documents.map((d) => d.trim())]);
		const count = await page.locator('g.node').count();
		await legend.getByRole('button').first().click();
		await expect(legend.getByRole('button').first()).toHaveAttribute('aria-pressed', 'true');
		await expect(scope).toHaveValue('');
		await expect(page.locator('g.node')).toHaveCount(count);
		await expect.poll(() => page.locator('g.node.dim').count()).toBeGreaterThan(0);
		await expect.poll(() => page.locator('.membership [data-document]').count()).toBeGreaterThan(0);
		await scope.selectOption({ label: documents[0].trim() });
		await expect(page.getByTestId('gnode-Kre99-thm-2.1')).toHaveCount(0);
	});

	test('shared membership survives modular source paths in every drawing', async ({ page }) => {
		await page.route('**/build/manifest.json', async (route) => {
			const response = await route.fetch();
			const m = await response.json();
			const primary = m.masters[0].path;
			m.masters.push({ ...m.masters[0], path: 'drafting/toy.tex' });
			m.nodes['sy-0003'].reached_by = [primary, 'drafting/toy.tex'];
			m.nodes['sy-0003'].file = 'sections/local-theory.tex';
			await route.fulfill({ response, json: m });
		});
		await page.goto('/graph');
		const panel = page.getByRole('button', { name: 'Show the panel', exact: true });
		if (await panel.isVisible()) await panel.click();
		const node = page.getByTestId('gnode-sy-0003');
		await expect(node.locator('.membership path')).toHaveCount(2);
		await node.click();
		await expect(page.getByText('Source: sections/local-theory.tex')).toBeVisible();
		await page.getByLabel('Scope', { exact: true }).selectOption('drafting/toy.tex');
		await expect(node.locator('.membership path')).toHaveCount(2);
		for (const mode of ['box', 'sections', 'reading']) {
			await page.getByTestId(`layout-${mode}`).click();
			const item = page.getByTestId(`${mode === 'box' ? 'gnode' : 'grow'}-sy-0003`);
			await expect(item.locator('.membership path')).toHaveCount(2);
		}
	});

	test('the toggle keeps the selection, and in the Box drawing every edge begins and ends on a box it joins', async ({ page }) => {
		await page.goto('/graph');
		await expect(page.getByTestId('layout-dots')).toHaveAttribute('aria-pressed', 'true');
		await page.getByTestId('gnode-sy-0003').click();
		await expect(page.locator('aside').getByRole('link', { name: 'Open in document', exact: true })).toBeVisible();
		const dotEdges = await page.locator('svg path.edge').count();
		expect(dotEdges).toBeGreaterThan(0);

		await page.getByTestId('layout-box').click();
		await expect(page.getByTestId('layout-box')).toHaveAttribute('aria-pressed', 'true');
		await expect(page.locator('aside').getByRole('link', { name: 'Open in document', exact: true })).toBeVisible();
		await expect.poll(() => page.locator('svg g.node rect').count()).toBeGreaterThan(3);
		// the layered drawing leaves out an edge from a node into the section that contains it, which ELK cannot route into an ancestor, so it can draw fewer
		await expect.poll(() => page.locator('svg path.edge').count()).toBeGreaterThan(0);
		expect(await page.locator('svg path.edge').count()).toBeLessThanOrEqual(dotEdges);
		const misses = await page.evaluate(() => {
			const boxes = [...document.querySelectorAll('svg g.node rect')].map((r) => (r as SVGRectElement).getBBox());
			const near = (x: number, y: number) => boxes.some((b) => x >= b.x - 2 && x <= b.x + b.width + 2 && y >= b.y - 2 && y <= b.y + b.height + 2);
			const out: string[] = [];
			for (const p of document.querySelectorAll('svg path.edge')) {
				const pts = (p.getAttribute('d') ?? '').match(/-?[\d.]+,-?[\d.]+/g) ?? [];
				if (pts.length < 2) {
					out.push(p.getAttribute('d') ?? '(no points)');
					continue;
				}
				const [x0, y0] = pts[0]!.split(',').map(Number);
				const [x1, y1] = pts[pts.length - 1]!.split(',').map(Number);
				if (!near(x0, y0) || !near(x1, y1)) out.push(p.getAttribute('d') ?? '');
			}
			return out;
		});
		expect(misses).toEqual([]);
	});

	test('a node cannot be dragged in the Box drawing, and dragging pans instead', async ({ page }) => {
		await page.goto('/graph');
		await page.getByTestId('layout-box').click();
		const node = page.locator('svg g.node').first();
		await expect(node.locator('rect')).toBeVisible();
		await expect(node.locator('circle')).toHaveCount(0); // the Box drawing has arrived, not the Dots one it replaces
		const x = await node.locator('rect').getAttribute('x');
		const box = (await node.boundingBox())!;
		const before = await page.locator('svg[aria-label="dependency graph"]').getAttribute('viewBox');
		await page.mouse.move(box.x + 8, box.y + 8);
		await page.mouse.down();
		await page.mouse.move(box.x + 120, box.y + 90, { steps: 6 });
		await page.mouse.up();
		expect(await node.locator('rect').getAttribute('x')).toBe(x);
		expect(await page.locator('svg[aria-label="dependency graph"]').getAttribute('viewBox')).not.toBe(before);
	});

	test('Sections draws a card per section with its results inside, and a row selects the result', async ({ page }) => {
		await page.goto('/graph');
		await page.getByLabel('Scope', { exact: true }).selectOption({ index: 1 });
		await page.getByTestId('layout-sections').click();
		await expect.poll(() => page.locator('g.card').count()).toBeGreaterThan(1);
		const row = page.getByTestId('grow-sy-0003');
		await expect(row).toBeVisible();
		await expect(page.locator('g.card').filter({ has: row })).toHaveCount(1); // the result sits inside its section's card
		await row.click();
		await expect(page.locator('aside').getByRole('link', { name: 'Open in document', exact: true })).toBeVisible();
		// a line between two cards stands for every dependency behind it
		const widths = await page.locator('svg path.edge').evaluateAll((ps) => ps.map((p) => Number(p.getAttribute('stroke-width'))));
		expect(Math.max(...widths)).toBeGreaterThan(1);
	});

	test('Reading Order lists the document in order with arcs, and fades the rest only halfway', async ({ page }) => {
		await page.goto('/graph');
		await page.getByLabel('Scope', { exact: true }).selectOption({ index: 1 });
		await page.getByTestId('layout-reading').click();
		const canvas = page.getByTestId('reading-canvas');
		await expect(canvas).toBeVisible();
		await expect.poll(() => canvas.locator('g.row').count()).toBeGreaterThan(3);
		await expect.poll(() => canvas.locator('path.edge').count()).toBeGreaterThan(0);
		const ys = await canvas.locator('g.row').evaluateAll((gs) => gs.map((g) => g.getBoundingClientRect().top));
		expect(ys).toEqual([...ys].sort((a, b) => a - b)); // rows follow the document, top to bottom
		await canvas.getByTestId('grow-sy-0003').click();
		await expect(page.locator('aside').getByRole('link', { name: 'Open in document', exact: true })).toBeVisible();
		const faded = canvas.locator('g.row.soft').first();
		await expect(faded).toHaveCount(1);
		await expect(faded).toHaveCSS('opacity', '0.55');
	});
});

test.describe('the local graph', () => {
	test("a node's context opens with the neighbourhood, centred on the node", async ({ page }) => {
		await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
		const graph = page.getByTestId('context').getByTestId('local-graph');
		await expect.poll(() => graph.locator('circle').count()).toBeGreaterThan(1);
		await expect(graph.locator('circle.centre')).toHaveCount(1);
		await expect(graph.locator('a[data-preview-key="sy-0003"] circle.centre')).toHaveCount(1);
	});

	test('its header reads Local Graph, then depth, then Dot or Box, then expand; Box draws the neighbourhood in layers', async ({ page }) => {
		await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
		const panel = page.getByTestId('context').getByTestId('local-graph-panel');
		const bar = panel.locator('.bar');
		await expect(bar.locator('.title')).toHaveText('Local Graph');
		await expect(bar.locator('button')).toHaveText(['1', '2', 'Dot', 'Box', '']);
		await expect(bar.locator('.sep')).toHaveCount(2);
		await expect(panel.getByTestId('local-graph-dot')).toHaveAttribute('aria-pressed', 'true');

		await panel.getByTestId('local-graph-box-toggle').click();
		const boxes = panel.getByTestId('local-graph-box');
		await expect.poll(() => boxes.locator('rect.box').count()).toBeGreaterThan(1);
		await expect(boxes.locator('a[data-preview-key="sy-0003"] rect.centre')).toHaveCount(1);
		await expect(panel.getByTestId('local-graph')).toHaveCount(0);
		// the neighbourhood is laid out in more than one layer
		const centreY = Number(await boxes.locator('a[data-preview-key="sy-0003"] rect').getAttribute('y'));
		const ys = await boxes.locator('a:not([data-preview-key="sy-0003"]) rect').evaluateAll((rs) => rs.map((r) => Number(r.getAttribute('y'))));
		expect(ys.filter((y) => y !== centreY), `the centre at y=${centreY}, the rest at ${ys.join(', ')}`).not.toHaveLength(0);

		await panel.getByTestId('local-graph-dot').click();
		await expect(panel.getByTestId('local-graph')).toBeVisible();
	});

	test('in the read view it opens on request, follows the reader, and expands into a dialog that closes on an outside click', async ({ page }) => {
		await page.setViewportSize({ width: 1440, height: 600 });
		await page.goto('/master/main');
		await page.waitForSelector('.fragment .env[data-key]');
		await page.getByTestId('local-graph-open').click();
		const panel = page.getByTestId('local-graph-panel');
		await expect(panel).toBeVisible();
		const centre = () => panel.locator('a:has(circle.centre)').getAttribute('data-preview-key');
		await expect.poll(centre).toBeTruthy();
		const first = await centre();
		await scrollPane(page, 0, 'bottom');
		await expect.poll(centre).not.toBe(first);

		await page.getByTestId('local-graph-expand').click();
		await expect(page.getByTestId('local-graph-dialog')).toBeVisible();
		await page.mouse.click(10, 10);
		await expect(page.getByTestId('local-graph-dialog')).toHaveCount(0);

		await page.reload();
		await expect(page.getByTestId('local-graph-panel')).toBeVisible(); // remembered in this browser
		await page.getByTestId('local-graph-close').click();
		await expect(page.getByTestId('local-graph-open')).toBeVisible();
	});

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
});
