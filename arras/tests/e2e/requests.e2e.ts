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

	test('inline, a mark expands its comment beneath its paragraph; clicking away backgrounds it and Escape closes it', async ({ page }) => {
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

		// clicking outside backgrounds rather than collapses: nothing a reader opened disappears because they looked
		// elsewhere (plan 0.13 §7)
		await page.mouse.click(5, 5);
		await expect(open).toHaveCount(1);
		await expect(page.locator('aside.comment-slot.expanded.behind')).toHaveCount(1);

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

	test('changing the placement re-wires the document without typesetting it again', async ({ page }) => {
		await withPrefs(page, { comments: 'margin' });
		await page.goto('/master/main');
		await page.waitForSelector('.fragment[data-comments-wired="margin"] mjx-container');
		await page.waitForFunction(() => document.querySelectorAll('.fragment .math:not(:has(mjx-container))').length === 0);
		await page.evaluate(() => {
			const w = window as unknown as { MathJax: { typesetPromise: (els: Element[]) => Promise<void> }; ofDocument: number };
			const real = w.MathJax.typesetPromise.bind(w.MathJax);
			w.ofDocument = 0;
			// a comment card typesets its own body; what must not happen is the document's text going through MathJax again
			w.MathJax.typesetPromise = (els) => {
				if (els.some((e) => e.closest('.fragment') && !e.closest('aside.comment-slot'))) w.ofDocument++;
				return real(els);
			};
		});
		await page.getByTestId('settings-toggle').click();
		await page.getByTestId('comments-inline').click();
		await page.waitForSelector('.fragment[data-comments-wired="inline"]');
		await page.getByTestId('comments-margin').click();
		await page.waitForSelector('.fragment[data-comments-wired="margin"] aside.comment-slot.gutter');
		await page.waitForTimeout(300);
		expect(await page.evaluate(() => (window as unknown as { ofDocument: number }).ofDocument)).toBe(0);
	});

	test('the drawing of a formula may be skipped off screen, and its MathML never is', async ({ page }) => {
		await page.goto('/master/main');
		await page.waitForSelector('.fragment mjx-container mjx-assistive-mml');
		const cv = await page.evaluate(() => {
			const c = document.querySelector('.fragment mjx-container')!;
			return [getComputedStyle(c.querySelector(':scope > svg')!).contentVisibility, getComputedStyle(c.querySelector('mjx-assistive-mml')!).contentVisibility];
		});
		// a skipped MathML is dropped from the accessibility tree, and clipped to a pixel it is never on screen to be un-skipped
		expect(cv).toEqual(['auto', 'visible']);
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
		await expect(cite.locator('a')).toHaveAttribute('href', '/library/Har77');
		const toResult = page.locator('.fragment span.cite[data-target="Kre99-thm-2.1"]').first();
		await expect(toResult.locator('a')).toHaveAttribute('href', '/node/Kre99-thm-2.1');
	});

	test('the references page links each work out by its identifier', async ({ page }) => {
		await page.goto('/library');
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
		await page.goto('/library/Man12');
		await expect(page.getByTestId('work-links-Man12').getByRole('link', { name: 'PDF' })).toHaveAttribute('href', `/${manifest.references.Man12.artifacts.dir}/paper.pdf`);
	});
});

test.describe('the review views stay deliberately small', () => {
	test('working documents replace All while Needs review and Incoming stay global', async ({ page }) => {
		await page.goto('/review?show=stale');
		const tabs = page.getByRole('navigation', { name: 'Review views' });
		await expect(tabs.getByRole('link')).toHaveText(['main.tex', 'talk.tex', /Needs Review \(\d+\)/, /Incoming \(\d+\)/]);
		await expect(tabs.getByRole('link', { name: 'main.tex' })).toHaveAttribute('aria-current', 'page');
		await expect(page.locator('main table.list')).toBeVisible();
		await expect(page.getByTestId('filter-show')).toHaveCount(0);
	});

	test('the blockers address lands on the default working document', async ({ page }) => {
		await page.goto('/blockers');
		await expect(page).toHaveURL(/\/review$/);
		await expect(page.getByRole('link', { name: 'main.tex' })).toHaveAttribute('aria-current', 'page');
	});

	test('the problems page filters by severity from the URL, with its filters in the panel', async ({ page }) => {
		await page.goto('/problems?severity=error');
		await expect(page.getByTestId('filter-severity')).toHaveValue('error');
		const errorCodes = new Set((manifest.diagnostics as { severity: string; code: string }[]).filter((d) => d.severity === 'error').map((d) => d.code));
		await expect(page.locator('main section.group')).toHaveCount(errorCodes.size);
	});

	test('the strip panel never repeats the strip', async ({ page }) => {
		for (const path of ['/threads', '/tags', '/loose']) {
			await page.goto(path);
			await expect(page.locator('.panel .rail-label', { hasText: /^Views$/ })).toHaveCount(0);
			// the documents stand there instead, with the contents folded under the open one (plan 0.13.1)
			await expect(page.getByTestId('docs-drafts')).toBeVisible();
		}
		// the Library fills the panel with its own filters, which is the other half of the same rule
		await page.goto('/library');
		await expect(page.locator('.panel .rail-label', { hasText: /^Views$/ })).toHaveCount(0);
		await expect(page.getByTestId('show-proposed')).toBeVisible();
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

test.describe('the floating placement', () => {
	test('a mark opens a box over the page, clear of every edge, and hovering opens nothing', async ({ page }) => {
		await withPrefs(page, { comments: 'floating' });
		await page.goto('/master/main');
		// A fragment is wired once for the default placement and again when the stored preferences arrive, so waiting
		// on the marks is not enough: wait until it is wired for the placement under test.
		await page.waitForSelector('.fragment[data-comments-wired="floating"] mark.annotation[data-wired-mark]');
		await expect(page.locator('aside.comment-slot.floating')).toHaveCount(0);

		const mark = page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-0001"]');
		const box = page.locator('aside.comment-slot.floating');

		// hovering never opens one: a box the pointer summons cannot be read without holding it still, and moving
		// toward the box leaves the mark (plan 0.13 §7)
		await mark.hover({ force: true });
		await page.waitForTimeout(400);
		await expect(box).toHaveCount(0);

		await mark.click();
		await expect(box).toHaveCount(1);
		// it floats over the page rather than opening in the flow, so it is free to overlap the text and the gutter
		await expect(box).toHaveCSS('position', 'fixed');
		await expect(box.locator('article.box')).toHaveCount(1);
		// and it is kept clear of every edge, so a mark near one slides the box rather than clipping it
		const inset = await box.evaluate((el) => {
			const r = el.getBoundingClientRect();
			return Math.min(r.left, r.top, window.innerWidth - r.right, window.innerHeight - r.bottom);
		});
		expect(inset).toBeGreaterThanOrEqual(3.5);

		await page.mouse.click(4, 4);
		await expect(box).toHaveCount(1); // backgrounded, not closed
		await page.keyboard.press('Escape');
		await expect(box).toHaveCount(0);
	});
});

test.describe('the four verbs on an annotation', () => {
	/** The publisher's own write API, stubbed: the fixture is served by `vite preview`, which has none. */
	async function withWriteApi(page: import('@playwright/test').Page) {
		await page.route('**/_api', (r) =>
			r.fulfill({
				contentType: 'application/json',
				body: JSON.stringify({ write_api: 1, capabilities: ['comment', 'reply', 'resolve', 'edit', 'discard', 'refs-note'] })
			})
		);
		await page.route('**/_api/*', (r) =>
			r.fulfill({ contentType: 'application/json', body: JSON.stringify({ ok: true, result: 'done' }) })
		);
	}

	test('no write API means no editing affordance at all', async ({ page }) => {
		await page.goto('/node/sy-0003');
		await expect(page.locator('article.box').first()).toBeVisible();
		await expect(page.locator('[data-testid="verb-row"]')).toHaveCount(0);
	});

	test('a panel opens above the row, so the body it is about never moves', async ({ page }) => {
		await withWriteApi(page);
		await page.goto('/node/sy-0003');
		const row = page.locator('[data-testid="verb-row"]').first();
		await expect(row).toBeVisible();

		await row.getByTestId('verb-reply').click();
		const panel = row.getByTestId('verb-panel');
		await expect(panel).toBeVisible();
		// polled: the geometry is read after the row has settled. Read the instant the panel appeared, the row could still
		// be reflowing as its verbs arrived, and this failed about one run in three
		await expect
			.poll(async () => {
				const pb = await panel.boundingBox();
				const rb = await row.boundingBox();
				return !!pb && !!rb && pb.y + pb.height <= rb.y + 2;
			}, { timeout: 5000 })
			.toBe(true);

		// it says nothing until it has something to say
		await expect(panel.getByTestId('verb-send')).toBeDisabled();
		await panel.getByTestId('verb-text').fill('Fixed in the next revision.');
		await expect(panel.getByTestId('verb-send')).toBeEnabled();

		await page.keyboard.press('Escape');
		await expect(panel).toHaveCount(0);
	});

	test('in a gutter slot two verbs fold behind a menu', async ({ page }) => {
		await withWriteApi(page);
		await withPrefs(page, { comments: 'margin', width: 'narrow' });
		await page.setViewportSize({ width: 1600, height: 1000 });
		await page.goto('/master/main');
		const slot = page.locator('aside.comment-slot.gutter').first();
		await expect(slot).toBeVisible();
		// the slot is about (container - measure) / 3 wide, and four verbs will not fit beside the metadata
		expect((await slot.boundingBox())!.width).toBeLessThan(330);

		const row = slot.locator('[data-testid="verb-row"]').first();
		await expect(row.getByTestId('verb-reply')).toBeVisible();
		await expect(row.getByTestId('verb-edit')).toBeHidden();
		await row.getByTestId('verb-more').click();
		await expect(row.getByTestId('verb-menu')).toBeVisible();
	});
});

test.describe('the four settings a document is read in', () => {
	test('p1 sets the compiled page: run-in heads, no colour on a result', async ({ page }) => {
		await withPrefs(page, { format: 'p1' });
		await page.goto('/master/main');
		await page.waitForSelector('.fragment .env[data-key]');
		await expect(page.locator('html')).toHaveAttribute('data-format', 'p1');

		const env = page.locator('.fragment .env[data-style="plain"]').first();
		const label = env.locator('> .env-label');
		// the head runs into the first line, in weight, and the statement is italic as the class sets it
		await expect(label).toHaveCSS('display', 'inline');
		await expect(label).toHaveCSS('font-weight', '700');
		await expect(env.locator('> .env-label + p')).toHaveCSS('font-style', 'italic');
		// and carries no colour of its own at all
		await expect(env).toHaveCSS('border-left-width', '0px');
		await expect(env).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)');

		// a remark's head is italic rather than bold
		const remark = page.locator('.fragment .env[data-style="remark"] > .env-label').first();
		if (await remark.count()) await expect(remark).toHaveCSS('font-style', 'italic');
	});

	test('p2 marks where the compiled pages ended, and p1 marks nothing', async ({ page }) => {
		await withPrefs(page, { format: 'p2' });
		await page.goto('/master/main');
		await page.waitForSelector('.fragment .env[data-key]');
		const breaks = page.locator('.page-break');
		await expect.poll(() => breaks.count()).toBeGreaterThan(0);
		// every boundary carries the page it begins, which is the page a reader would cite
		const pages = await breaks.evaluateAll((els) => els.map((e) => Number((e as HTMLElement).dataset.page)));
		expect(pages).toEqual([...pages].sort((a, b) => a - b));
		expect(new Set(pages).size).toBe(pages.length);

		await page.getByTestId('settings-toggle').click();
		await page.getByTestId('format-p1').click();
		await expect(page.locator('.page-break')).toHaveCount(0);
	});

	test('b1 and b2 keep the taxon accent, and there are three colours in it', async ({ page }) => {
		await withPrefs(page, { format: 'b1' });
		await page.goto('/master/main');
		await page.waitForSelector('.fragment .env[data-key]');
		const tones = await page.evaluate(() =>
			[...document.querySelectorAll('.fragment .env[data-key]')].map((e) =>
				(e as HTMLElement).style.getPropertyValue('--taxon-tone')
			)
		);
		expect(new Set(tones.filter(Boolean)).size).toBeLessThanOrEqual(3);

		await page.getByTestId('settings-toggle').click();
		await page.getByTestId('format-b2').click();
		await expect(page.locator('html')).toHaveAttribute('data-format', 'b2');
		// b2 points at a result by name, not by number
		await expect(page.locator('.fragment .env-label .number').first()).toBeHidden();
	});
});

test.describe('the session selector', () => {
	// The fixture's own two sessions, `referee` (active) and `quick` (closed). Only the second annotation on sy-0002 is
	// moved, and only so that one key carries work from two sessions — which is the state the filter exists for and
	// which no fixture happens to contain. The sessions themselves are not invented.
	const withSessions = async (page: Page) =>
		page.route('**/build/manifest.json', async (route) => {
			const res = await route.fetch();
			const m = await res.json();
			for (const s of m.sessions) if (s.id === 's-2026-09-15-0001') s.state = 'open';
			m.annotations['a-2026-09-16-0006'].run = 's-2026-09-15-0001';
			await route.fulfill({ json: m });
		});

	test('one selection governs the page, and the view filters annotations rather than the list', async ({ page }) => {
		await withSessions(page);
		await page.goto('/node/sy-0002');
		// nothing is selected at rest and the page shows everything (plan 0.13.1)
		await expect(page.getByTestId('show-all')).toHaveAttribute('class', /on/);
		await expect(page.getByTestId('show-current')).toBeDisabled();

		// sy-0002 is now annotated from both sessions. Waited for rather than counted straight away: a bare `count()`
		// races the first render and reports zero.
		await expect(page.getByTestId('annotation-list').locator('article.box').first()).toBeVisible();
		const all = await page.getByTestId('annotation-list').locator('article.box').count();
		expect(all).toBeGreaterThan(1);

		// selecting a session does not narrow the page by itself: the selection is the write target, the view is the filter
		await page.getByTestId('session-s-2026-09-15-0001').click();
		await expect(page.getByTestId('annotation-list').locator('article.box')).toHaveCount(all);
		// and the list still shows every session, because it is how a reader navigates
		await expect(page.getByTestId('session-list').locator('li')).toHaveCount(2);

		// narrowing is the toggle's job, and it is available now that something is selected
		await page.getByTestId('show-current').click();
		const mine = await page.getByTestId('annotation-list').locator('article.box').count();
		expect(mine).toBeGreaterThan(0);
		expect(mine).toBeLessThan(all);

		// and back to everything
		await page.getByTestId('show-all').click();
		await expect(page.getByTestId('annotation-list').locator('article.box')).toHaveCount(all);
	});
});

test.describe('the split as a mode of a route', () => {
	// Presence and the round count are what a heartbeat and a resumed session produce at runtime; a checked-in fixture
	// has neither, so they are added to the fixture's own active session rather than to an invented one.
	const withSessions = async (page: Page) =>
		page.route('**/build/manifest.json', async (route) => {
			const res = await route.fetch();
			const m = await res.json();
			const here = m.sessions.find((s: { id: string }) => s.id === 's-2026-09-16-0001');
			here.rounds = 2;
			here.attached = [{ who: 'referee', kind: 'agent' }];
			here.seq = 0;
			await route.fulfill({ json: m });
		});

	test('a node page opens a discussion beside it, and the URL is what remembers', async ({ page }) => {
		await withSessions(page);
		await page.goto('/node/sy-0003');
		// closed by default: a reader who never wants one carries a single control and no frame
		await expect(page.getByTestId('beside')).toBeHidden();
		await page.getByTestId('beside-toggle').click();
		await expect(page.getByTestId('beside')).toBeVisible();
		await expect(page).toHaveURL(/beside=1/);
		// the divider is the same one the reading pane uses, and the discussion says where writing goes -- which,
		// with nothing selected, is nowhere until the reader picks a session (plan 0.13.1)
		await expect(page.getByTestId('divider')).toBeVisible();
		await expect(page.getByTestId('discussion-into')).toContainText('no session selected');
		await page.getByTestId('session-s-2026-09-16-0001').click();
		await expect(page.getByTestId('discussion-into')).toContainText('referee');
		// what is beside it is what is on this result
		await expect(page.getByTestId('beside-a-2026-09-16-0001')).toBeVisible();
		await page.getByTestId('beside-toggle').click();
		await expect(page.getByTestId('beside')).toBeHidden();
	});

	test('the document does too, and it is the same frame', async ({ page }) => {
		await withSessions(page);
		await page.goto('/master/main?beside=1');
		await expect(page.getByTestId('beside')).toBeVisible();
		await expect(page.getByTestId('pane-content').locator('.fragment').first()).toBeVisible();
		// an annotation on a key inside the document, not only on the document itself
		await expect(page.getByTestId('beside-a-2026-09-16-0001')).toBeVisible();
	});

	test("a session's permalink opens split, and reads the session back whole", async ({ page }) => {
		await withSessions(page);
		await page.goto('/session/s-2026-09-16-0001');
		await expect(page.getByRole('heading', { level: 1 })).toHaveText('referee');
		await expect(page.getByTestId('session-facts')).toContainText('round 2');
		await expect(page.getByTestId('session-attached')).toContainText('referee ⟨agent⟩');
		// it opens split without being asked, because the discussion is what a session is
		await expect(page.getByTestId('beside')).toBeVisible();
		// every annotation filed in it, oldest first, each a link to what it is about
		const filed = page.getByTestId('session-filed').locator('> li');
		await expect(filed.first()).toHaveAttribute('data-testid', 'filed-a-2026-09-16-0001');
		await expect(filed).toHaveCount(9);
		// and closing it leaves the record in place
		await page.getByTestId('beside-toggle').click();
		await expect(page.getByTestId('beside')).toBeHidden();
		await expect(page.getByTestId('session-filed')).toBeVisible();
	});

	test('an unknown session is reported rather than invented', async ({ page }) => {
		await withSessions(page);
		await page.goto('/session/nope');
		await expect(page.getByRole('heading', { level: 1 })).toHaveText('Unknown session');
	});
});

test.describe('the divider, the panel and the ticks', () => {
	test('the divider drags, snaps at the middle, resets on double-click, nudges by key, and collapses', async ({ page }) => {
		await page.goto('/node/sy-0003?beside=1');
		const divider = page.getByTestId('divider');
		await expect(divider).toBeVisible();
		const split = page.getByTestId('split');
		const frame = (await split.boundingBox())!;
		const at = async () => Number(await divider.getAttribute('aria-valuenow'));
		// dragged to a third of the frame, the ratio follows the pointer
		const handle = (await divider.boundingBox())!;
		await page.mouse.move(handle.x + handle.width / 2, handle.y + handle.height / 2);
		await page.mouse.down();
		await page.mouse.move(frame.x + frame.width * 0.33, handle.y + handle.height / 2, { steps: 6 });
		await page.mouse.up();
		expect(await at()).toBeLessThan(40);
		// near the middle it snaps to it, and nowhere else
		await page.mouse.move(frame.x + frame.width * 0.33, handle.y + handle.height / 2);
		await page.mouse.down();
		await page.mouse.move(frame.x + frame.width * 0.515, handle.y + handle.height / 2, { steps: 6 });
		await page.mouse.up();
		expect(await at()).toBe(50);
		// the keys nudge, Home recentres, a double-click resets
		await divider.focus();
		await page.keyboard.press('ArrowRight');
		await page.keyboard.press('ArrowRight');
		expect(await at()).toBe(54);
		await page.keyboard.press('Home');
		expect(await at()).toBe(50);
		await page.keyboard.press('ArrowLeft');
		await divider.dblclick();
		expect(await at()).toBe(50);
		// the chevrons collapse either pane and the ratio is remembered
		await page.getByTestId('fold-discussion').click();
		await expect(page.getByTestId('pane-discussion')).toBeHidden();
		await page.getByTestId('fold-discussion').click();
		await expect(page.getByTestId('pane-discussion')).toBeVisible();
		expect(await at()).toBe(50);
		// and below the breakpoint the split is a switch
		await page.setViewportSize({ width: 640, height: 800 });
		await expect(page.getByTestId('switch-discussion')).toBeVisible();
		await page.getByTestId('switch-discussion').click();
		await expect(page.getByTestId('pane-discussion')).toBeVisible();
	});

	test('the panel has a Nodes section, folded, narrowed by what is typed', async ({ page }) => {
		await page.goto('/node/sy-0003');
		await expect(page.getByTestId('nodes-list')).toHaveCount(0); // folded: a corpus of a hundred results would otherwise be the panel
		await page.getByTestId('nodes-toggle').click();
		await expect(page.getByTestId('nodes-list')).toBeVisible();
		await page.getByTestId('nodes-filter').fill('parity');
		const rows = page.getByTestId('nodes-list').locator('li a');
		await expect(rows.first()).toContainText('sy-0003');
		await expect(rows).toHaveCount(1);
		await page.getByTestId('nodes-filter').fill('zzz');
		await expect(page.getByTestId('nodes-list')).toContainText('nothing matches');
	});

	test('a tick stands beside every annotated line, carrying the count where two share one', async ({ page }) => {
		await page.goto('/node/sy-0003');
		const ticks = page.getByTestId('ticks');
		await expect(ticks).toBeVisible();
		const marks = await page.locator('.fragment mark.annotation').count();
		expect(await ticks.locator('.tick').count()).toBeGreaterThan(0);
		expect(await ticks.locator('.tick').count()).toBeLessThanOrEqual(marks);
		// a tick selects its annotation, and double-click travels to the mark
		const first = ticks.locator('.tick').first();
		const lead = (await first.getAttribute('data-testid'))!.replace('tick-', '');
		await first.dblclick();
		await expect(page.locator(`.fragment [data-annotation~="${lead}"]`)).toBeInViewport();
	});
});
