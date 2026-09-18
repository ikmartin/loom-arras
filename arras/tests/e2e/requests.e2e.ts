// Plan 0.6: the running requests, each as the behaviour a reader asked for.
import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';

const manifest = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8'));

async function withPrefs(page: Page, prefs: Record<string, string>) {
	await page.addInitScript((p) => {
		try {
			localStorage.setItem('arras.prefs', JSON.stringify({ shell: 'c', face: 'serif', size: 'm', width: 'mid', theme: 'light', comments: 'margin', ...p }));
		} catch {
			/* storage unavailable: defaults */
		}
	}, prefs);
}

test.describe('comments as expandable highlights', () => {
	test('a mark is coloured by its comment kind in either placement', async ({ page }) => {
		await page.goto('/master/main');
		const mark = page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-0001"]');
		await expect(mark).toHaveClass(/k-objection/);
	});

	test('inline, a mark expands its comment beneath its paragraph and selecting outside closes it', async ({ page }) => {
		await withPrefs(page, { comments: 'inline' });
		await page.goto('/master/main');
		await page.waitForSelector('.fragment .env[data-key]');
		await expect(page.locator('aside.comment-slot.gutter')).toHaveCount(0);

		const mark = page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-0001"]');
		await mark.click();
		const open = page.locator('aside.comment-slot.expanded');
		await expect(open).toHaveCount(1);
		await expect(open.locator('article.box')).toHaveCount(1); // the reply is inside its parent, not a second box
		await expect(open.locator('.replies')).toBeVisible();
		await expect(mark).toHaveAttribute('aria-expanded', 'true');
		// in the flow, directly after the paragraph holding the mark
		const follows = await mark.evaluate((m) => {
			const block = m.closest('p, li, .math.display, .annotation-block, summary');
			return block?.nextElementSibling?.classList.contains('expanded') ?? false;
		});
		expect(follows).toBe(true);

		await page.mouse.click(5, 5);
		await expect(open).toHaveCount(0);

		await mark.click();
		await expect(page.locator('aside.comment-slot.expanded')).toHaveCount(1);
		await page.keyboard.press('Escape');
		await expect(page.locator('aside.comment-slot.expanded')).toHaveCount(0);
	});

	test('inline, a comment with no mark is reached from a count beside its node', async ({ page }) => {
		await withPrefs(page, { comments: 'inline' });
		await page.goto('/master/main');
		// a-2026-09-16-0006 lost its anchor, so it has no mark on sy-0001
		const count = page.locator('.fragment button.comment-count[data-count-for="sy-0001"]');
		await expect(count).toHaveText('1 comment');
		await count.click();
		await expect(page.locator('aside.comment-slot.expanded article.box')).toHaveCount(1);
	});

	test('the placement is a display setting', async ({ page }) => {
		await page.goto('/master/main');
		await page.getByTestId('settings-toggle').click();
		await page.getByTestId('comments-inline').click();
		await expect(page.locator('html')).toHaveAttribute('data-comments', 'inline');
		await expect(page.locator('aside.comment-slot.gutter')).toHaveCount(0);
	});
});

test.describe('the Box drawing', () => {
	test('every edge begins and ends on a box it joins', async ({ page }) => {
		await page.goto('/graph');
		await page.getByTestId('layout-box').click();
		await expect.poll(() => page.locator('svg g.node rect').count()).toBeGreaterThan(3);
		const misses = await page.evaluate(() => {
			const boxes = [...document.querySelectorAll('svg g.node rect')].map((r) => {
				const b = (r as SVGRectElement).getBBox();
				return b;
			});
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
});

test.describe('the local graph', () => {
	test('a node page opens its rail with the neighbourhood, centred on the node', async ({ page }) => {
		await page.goto('/node/sy-0003');
		const graph = page.locator('aside').getByTestId('local-graph');
		await expect.poll(() => graph.locator('circle').count()).toBeGreaterThan(1);
		await expect(graph.locator('circle.centre')).toHaveCount(1);
		await expect(graph.locator('a[data-preview-key="sy-0003"] circle.centre')).toHaveCount(1);
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
		await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
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
});

test.describe('the local graph header', () => {
	test('reads Local Graph, then depth, then Dot or Box, then expand; Box draws the neighbourhood in layers', async ({ page }) => {
		await page.goto('/node/sy-0003');
		const panel = page.locator('aside').getByTestId('local-graph-panel');
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
		expect(ys.some((y) => y !== centreY)).toBe(true);

		await panel.getByTestId('local-graph-dot').click();
		await expect(panel.getByTestId('local-graph')).toBeVisible();
	});

	test('the graph page offers four drawings by name', async ({ page }) => {
		await page.goto('/graph');
		await expect(page.locator('.toggle button')).toHaveText(['Dots', 'Box', 'Sections', 'Reading Order']);
	});
});

test.describe('the Sections and Reading Order drawings', () => {
	test('Sections draws a card per section with its results inside, and a row selects the result', async ({ page }) => {
		await page.goto('/graph');
		await page.getByTestId('layout-sections').click();
		await expect.poll(() => page.locator('g.card').count()).toBeGreaterThan(1);
		const row = page.getByTestId('grow-sy-0003');
		await expect(row).toBeVisible();
		await expect(page.locator('g.card').filter({ has: row })).toHaveCount(1); // the result sits inside its section's card
		await row.click();
		await expect(page.locator('aside').getByRole('link', { name: /Theorem/ })).toBeVisible();
		// a line between two cards stands for every dependency behind it
		const widths = await page.locator('svg path.edge').evaluateAll((ps) => ps.map((p) => Number(p.getAttribute('stroke-width'))));
		expect(Math.max(...widths)).toBeGreaterThan(1);
	});

	test('Reading Order lists the document in order with arcs, and fades the rest only halfway', async ({ page }) => {
		await page.goto('/graph');
		await page.getByTestId('layout-reading').click();
		const canvas = page.getByTestId('reading-canvas');
		await expect(canvas).toBeVisible();
		await expect.poll(() => canvas.locator('g.row').count()).toBeGreaterThan(3);
		await expect.poll(() => canvas.locator('path.edge').count()).toBeGreaterThan(0);
		const ys = await canvas.locator('g.row').evaluateAll((gs) => gs.map((g) => g.getBoundingClientRect().top));
		expect(ys).toEqual([...ys].sort((a, b) => a - b)); // rows follow the document, top to bottom
		await canvas.getByTestId('grow-sy-0003').click();
		await expect(page.locator('aside').getByRole('link', { name: /Theorem/ })).toBeVisible();
		const faded = canvas.locator('g.row.soft').first();
		await expect(faded).toHaveCount(1);
		expect(await faded.evaluate((el) => getComputedStyle(el).opacity)).toBe('0.55');
	});
});

test.describe('references', () => {
	test('a citation with no digest result behind it links to its reference', async ({ page }) => {
		await page.goto('/master/main');
		const cite = page.locator('.fragment span.cite[data-citekey="Har77"]').first();
		await expect(cite.locator('a')).toHaveAttribute('href', '/digest/Har77');
		const toResult = page.locator('.fragment span.cite[data-target="Kre99-thm-2.1"]').first();
		await expect(toResult.locator('a')).toHaveAttribute('href', '/node/Kre99-thm-2.1');
	});

	test('the references page links each work out by its identifier', async ({ page }) => {
		await page.goto('/references');
		const links = page.getByTestId('work-links-Man12').locator('a');
		await expect(links).toHaveCount(1);
		await expect(links.first()).toHaveAttribute('href', 'https://arxiv.org/abs/0805.2065v2');
		await expect(links.first()).toHaveAttribute('target', '_blank');
		// a work with only a synthetic identifier has nowhere to link
		await expect(page.getByTestId('work-links-Har77')).toHaveCount(0);
		await expect(page.locator('main table')).not.toContainText('{');
	});

	test('a fetched PDF is offered only when the manifest says it is there', async ({ page }) => {
		await page.route('**/build/manifest.json', async (route) => {
			const m = JSON.parse(JSON.stringify(manifest));
			m.references.Man12.artifacts.pdf = true;
			await route.fulfill({ json: m });
		});
		await page.goto('/digest/Man12');
		await expect(page.getByTestId('work-links-Man12').getByRole('link', { name: 'PDF' })).toHaveAttribute('href', '/refs/arxiv/0805.2065v2/paper.pdf');
	});
});

test.describe('the counts open filtered tables', () => {
	test('the review filter lives in the URL, and a count toggles it', async ({ page }) => {
		await page.goto('/review?show=stale');
		await expect(page.getByTestId('filter-show')).toHaveValue('stale');
		const staleCount = Object.values(manifest.keys as Record<string, { acceptance?: { fresh: boolean } }>).filter((k) => k.acceptance && k.acceptance.fresh === false).length;
		await expect(page.locator('main table.list tbody tr')).toHaveCount(staleCount);
		await page.getByTestId('filter-show').selectOption('draft');
		await expect(page).toHaveURL(/show=draft/);
		await page.getByTestId('show-draft').click();
		await expect(page).toHaveURL(/\/review$/);
	});

	test('the incomplete view says what each gap blocks', async ({ page }) => {
		await page.goto('/review?show=incomplete');
		await expect(page.locator('main table.list tbody tr')).toHaveCount(1);
		await expect(page.getByTestId('blocks-sy-000C/proof')).toBeVisible();
	});

	test('the blockers address lands on the incomplete view', async ({ page }) => {
		await page.goto('/blockers');
		await expect(page).toHaveURL(/\/review\?show=incomplete$/);
	});

	test('the problems page filters by severity from the URL, with its filters in the panel', async ({ page }) => {
		await page.goto('/problems?severity=error');
		await expect(page.getByTestId('filter-severity')).toHaveValue('error');
		const errorCodes = new Set((manifest.diagnostics as { severity: string; code: string }[]).filter((d) => d.severity === 'error').map((d) => d.code));
		await expect(page.locator('main section.group')).toHaveCount(errorCodes.size);
	});

	test('the strip panel never repeats the strip', async ({ page }) => {
		for (const path of ['/threads', '/tags', '/references', '/loose']) {
			await page.goto(path);
			await expect(page.locator('.panel .rail-label', { hasText: /^Views$/ })).toHaveCount(0);
			await expect(page.getByRole('navigation', { name: 'Contents' })).toBeVisible();
		}
	});
});

test.describe('floating boxes close when you select outside them', () => {
	test('the settings panel', async ({ page }) => {
		await page.goto('/');
		await page.getByTestId('settings-toggle').click();
		await expect(page.getByTestId('settings-panel')).toBeVisible();
		await page.mouse.click(900, 500);
		await expect(page.getByTestId('settings-panel')).toHaveCount(0);
		await page.getByTestId('settings-toggle').click();
		await page.keyboard.press('Escape');
		await expect(page.getByTestId('settings-panel')).toHaveCount(0);
	});

	test('a help panel', async ({ page }) => {
		await page.goto('/review');
		await page.getByTestId('help-review').click();
		await expect(page.getByTestId('help-panel-review')).toBeVisible();
		await page.mouse.click(900, 700);
		await expect(page.getByTestId('help-panel-review')).toHaveCount(0);
	});
});

test.describe('the tabs shell is retired', () => {
	test('a link asking for it gets the default, and settings offers two', async ({ page }) => {
		await page.goto('/?shell=b');
		await expect(page.locator('html')).toHaveAttribute('data-shell', 'c');
		await page.getByTestId('settings-toggle').click();
		await expect(page.getByTestId('shell-b')).toHaveCount(0);
		await expect(page.getByTestId('shell-a')).toBeVisible();
		await expect(page.getByTestId('shell-c')).toBeVisible();
	});
});

test.describe('hover previews', () => {
	test('resting on a link to a node shows its statement, and Escape dismisses it', async ({ page }) => {
		await page.goto('/node/sy-0003');
		const link = page.locator('aside a[href^="/node/sy-"]').filter({ hasNotText: 'document' }).first();
		await link.hover();
		const card = page.getByTestId('link-preview');
		await expect(card).toBeVisible();
		await expect(card.locator('.fragment mjx-container').first()).toBeVisible();
		await page.keyboard.press('Escape');
		await expect(card).toHaveCount(0);
	});

	test('a quick pass over a link shows nothing', async ({ page }) => {
		await page.goto('/node/sy-0003');
		const link = page.locator('aside a[href^="/node/sy-"]').first();
		await link.hover();
		await page.mouse.move(900, 600);
		await page.waitForTimeout(500);
		await expect(page.getByTestId('link-preview')).toHaveCount(0);
	});

	test('a citation previews the reference behind it', async ({ page }) => {
		await page.goto('/master/main');
		await page.waitForSelector('.fragment mjx-container'); // typesetting reflows the text, which would move the link out from under the pointer
		await page.locator('.fragment span.cite[data-citekey="Har77"] a').first().hover();
		await expect(page.getByTestId('link-preview')).toContainText('Algebraic Geometry');
	});
});

test.describe('comments on hover', () => {
	test('a mark opens a floating box the pointer brings up, and clicking away closes it', async ({ page }) => {
		await withPrefs(page, { comments: 'hover' });
		await page.goto('/master/main');
		await page.waitForSelector('.fragment .env[data-key]');
		await expect(page.locator('aside.comment-slot.floating')).toHaveCount(0);

		const mark = page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-0001"]');
		await mark.hover();
		const box = page.locator('aside.comment-slot.floating');
		await expect(box).toHaveCount(1);
		// it floats over the page rather than opening in the flow, so it is free to overlap the text and the gutter
		await expect(box).toHaveCSS('position', 'fixed');
		await expect(box.locator('article.box')).toHaveCount(1);

		await page.mouse.click(4, 4);
		await expect(box).toHaveCount(0);
	});
});
