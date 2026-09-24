// Plan 0.6: the running requests, each as the behaviour a reader asked for.
import { expect, test, type Page } from '@playwright/test';
import { beside, pane, scrollPane } from '../workspace';
import { openPicker, pickSession } from '../picker';
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

	test('inline, a mark expands its comment beneath its paragraph; clicking away closes it', async ({ page }) => {
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

		// Clicking away closes. DR-202 backgrounded instead, which left a clipped, faded stub of a box on the page --
		// a ghost when it was alone, and a second border when another box sat in front of it.
		await page.mouse.click(5, 5);
		await expect(page.locator('aside.comment-slot.expanded')).toHaveCount(0);

		// and Escape closes the front-most, as it always did
		await mark.click();
		await expect(open).toHaveCount(1);
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
		await withPrefs(page, { comments: 'floating' });
		await page.goto('/master/main');
		await page.waitForSelector('.fragment[data-comments-wired="floating"] mjx-container');
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
		await page.getByTestId('comments-floating').click();
		await page.waitForSelector('.fragment[data-comments-wired="floating"]');
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
	test("a node's context opens with the neighbourhood, centred on the node", async ({ page }) => {
		await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
		const graph = page.getByTestId('context').getByTestId('local-graph');
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
});

test.describe('the local graph header', () => {
	test('reads Local Graph, then depth, then Dot or Box, then expand; Box draws the neighbourhood in layers', async ({ page }) => {
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
		await page.getByTestId('tab-info').click();
		await expect(page.getByTestId('work-links-Man12').getByRole('link', { name: 'PDF' })).toHaveAttribute('href', `/${manifest.references.Man12.artifacts.dir}/paper.pdf`);
	});
});

test.describe('the review views stay deliberately small', () => {
	test('All is the default and the only other views are Needs review and Incoming', async ({ page }) => {
		await page.goto('/review?show=stale');
		const tabs = page.getByRole('navigation', { name: 'Review views' });
		await expect(tabs.getByRole('link')).toHaveText([/All/, /Needs Review \(\d+\)/, /Incoming \(\d+\)/]);
		await expect(tabs.getByRole('link', { name: 'All' })).toHaveAttribute('aria-current', 'page');
		await expect(page.locator('main table.list')).toBeVisible();
		await expect(page.getByTestId('filter-show')).toHaveCount(0);
	});

	test('the blockers address lands on All', async ({ page }) => {
		await page.goto('/blockers');
		await expect(page).toHaveURL(/\/review\?show=all$/);
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

test.describe('there is one shell', () => {
	test('settings offers no arrangement to choose, and a link asking for one is ignored', async ({ page }) => {
		// Two arrangements meant every panel change had to be made twice, and the second fell behind on the first one
		// that was not. A stored or linked `shell` is now simply unread.
		await page.goto('/?shell=a');
		await expect(page.locator('html')).not.toHaveAttribute('data-shell', /./);
		await expect(page.getByTestId('view-home')).toBeVisible(); // the icon strip, whatever the link asked for
		await page.getByTestId('settings-toggle').click();
		await expect(page.getByTestId('settings-panel')).toBeVisible();
		await expect(page.getByTestId('shell-a')).toHaveCount(0);
		await expect(page.getByTestId('shell-c')).toHaveCount(0);
	});
});

test.describe('hover previews', () => {
	test('resting on a link to a node shows its statement, and Escape dismisses it', async ({ page }) => {
		await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
		const link = page.getByTestId('context').getByRole('link', { name: /^Definition/ }).first();
		await link.hover();
		const card = page.getByTestId('link-preview');
		await expect(card).toBeVisible();
		await expect(card.locator('.fragment mjx-container').first()).toBeVisible();
		await page.keyboard.press('Escape');
		await expect(card).toHaveCount(0);
	});

	test('a quick pass over a link shows nothing', async ({ page }) => {
		await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
		const link = page.getByTestId('context').locator('a[href^="/node/sy-"]').first();
		await link.hover();
		await page.mouse.move(900, 600);
		await page.waitForTimeout(500);
		await expect(page.getByTestId('link-preview')).toHaveCount(0);
	});

	test('a citation previews the page at the place it names, and nothing where the place is unknown', async ({ page }) => {
		// A hover over a citation shows the paper, not a card about it: the entry and the digest are what the work's own
		// Info tab is for. With no copy on this machine there is no page to show, so nothing opens.
		await page.goto('/master/main');
		await page.waitForSelector('.fragment mjx-container'); // typesetting reflows the text, which would move the link out from under the pointer
		await page.locator('.fragment span.cite[data-citekey="Har77"] a').first().hover();
		await page.waitForTimeout(500);
		await expect(page.getByTestId('link-preview')).toHaveCount(0);

		await page.route('**/build/manifest.json', async (route) => {
			const res = await route.fetch();
			const m = await res.json();
			m.references.Har77.artifacts.pdf = true;
			m.references.Kre99.artifacts.pdf = true;
			await route.fulfill({ json: m });
		});
		await page.reload();
		await page.waitForSelector('.fragment mjx-container');

		// A postnote names a place, so a copy being filed is not on its own a reason to open one: `[Har77, Chapter II]`
		// knows no page, and the front page of Hartshorne is not Chapter II. Answering with it would be the reading
		// layer claiming a location it does not have.
		await page.locator('.fragment span.cite[data-citekey="Har77"] a').first().hover();
		await page.waitForTimeout(500);
		await expect(page.getByTestId('link-preview')).toHaveCount(0);

		// where the postnote carries its own page, that is the place, and the card is the page and nothing else
		await page.goto('/node/Kre99-thm-2.1');
		await page.waitForSelector('.fragment mjx-container');
		await page.locator('.fragment span.cite[data-postnote="Theorem 2.1, p.~4"] a').first().hover();
		await expect(page.getByTestId('preview-page')).toBeVisible();
		// the card is the paper, not text about it; its one line is the `open here` every card carries (plan 0.13.3 H6)
		await expect(page.getByTestId('link-preview').locator('p:not(.opens):not(.problem)')).toHaveCount(0); // the renderer's own load notice is not text about the work
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

		// Escape closes the front-most, and a click away closes what is open
		await page.keyboard.press('Escape');
		await expect(box).toHaveCount(0);
		await mark.click();
		await expect(box).toHaveCount(1);
		await page.mouse.click(4, 4);
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
		await page.locator('.fragment mark.annotation').first().click();
		await expect(page.locator('article.box').first()).toBeVisible();
		await expect(page.locator('[data-testid="verb-row"]')).toHaveCount(0);
	});

	test('a panel opens above the row, so the body it is about never moves', async ({ page }) => {
		await withWriteApi(page);
		// placed inline, the box opens in the flow under its paragraph, which is where a panel pushing down would move the body; a floating box holds its panel in its own flow instead
		await page.addInitScript(() => localStorage.setItem('arras.prefs', JSON.stringify({ comments: 'inline' })));
		await page.goto('/node/sy-0003');
		await page.locator('.fragment mark.annotation').first().click();
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

	test('one selection governs the page, and the view filters what the page draws', async ({ page }) => {
		await withSessions(page);
		await page.goto('/node/sy-0002');
		// nothing is selected at rest and the page shows everything (plan 0.13.1)
		await expect(page.getByTestId('show-all')).toHaveAttribute('class', /on/);
		await expect(page.getByTestId('show-current')).toBeDisabled();

		// sy-0002 is now annotated from both sessions: its comment with no mark, from the referee, is counted beside its label
		const counted = pane(page, 0).locator('.fragment button.comment-count');
		await expect(counted).toHaveCount(1);

		// selecting a session does not narrow the page by itself: the selection is the write target, the view is the filter
		await pickSession(page, 's-2026-09-15-0001');
		await expect(counted).toHaveCount(1);
		// and the picker still lists every session, because it is how a reader navigates
		await openPicker(page);
		await expect(page.getByTestId('session-list').locator('li')).toHaveCount(2);
		await page.keyboard.press('Escape');

		// narrowing is the toggle's job, and it is available now that something is selected: the referee's comment goes
		await page.getByTestId('show-current').click();
		await expect(counted).toHaveCount(0);

		// and back to everything
		await page.getByTestId('show-all').click();
		await expect(counted).toHaveCount(1);
	});
});

test.describe('a session opened beside what is read', () => {
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

	test('choosing a session opens its Chat beside the node, focus stays, and the URL is what remembers', async ({ page }) => {
		await withSessions(page);
		await page.goto('/node/sy-0003');
		// one pane at rest: a reader who never wants a second carries no frame for it
		await expect(pane(page, 1)).toHaveCount(0);
		// choosing whom to talk to opens the conversation beside, and the reader stays in the node
		await pickSession(page, 's-2026-09-16-0001');
		await expect(pane(page, 1).getByTestId('chat')).toBeVisible();
		await expect(pane(page, 0)).toHaveClass(/focused/);
		await expect(page.getByTestId('open-context')).toBeVisible();
		// closed, choosing it again opens it again
		await pane(page, 1).getByTestId('tab-close').click();
		await expect(pane(page, 1)).toHaveCount(0);
		await pickSession(page, 's-2026-09-16-0001');
		await expect(pane(page, 1).getByTestId('chat')).toBeVisible();
		await expect.poll(() => new URL(page.url()).searchParams.get('beside')).toBe('/session/s-2026-09-16-0001');
		await expect(page.getByTestId('divider')).toBeVisible();
		// and the arrangement is a link: a reload reproduces it
		await page.reload();
		await expect(pane(page, 1).getByTestId('chat')).toBeVisible();
		await expect(pane(page, 0).locator('.fragment').first()).toBeVisible();
	});

	test('the document holds it the same way, and it is the same frame', async ({ page }) => {
		await withSessions(page);
		await page.goto('/master/main' + beside('/session/s-2026-09-16-0001'));
		await expect(pane(page, 0).locator('.fragment').first()).toBeVisible();
		await expect(pane(page, 1).getByTestId('chat')).toBeVisible();
	});
});

test.describe('the divider and the panel', () => {
	test('the divider is one line that drags, snaps at the middle, resets on double-click and nudges by key', async ({ page }) => {
		await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
		const divider = page.getByTestId('divider');
		await expect(divider).toBeVisible();
		const split = page.getByTestId('workspace');
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
		// one line and nothing on it: no chevrons, no grip
		await expect(divider.locator('button')).toHaveCount(0);
		// and below the breakpoint one pane shows, under one strip holding both panes' tabs
		await page.setViewportSize({ width: 640, height: 800 });
		const strip = page.getByTestId('narrow-strip');
		await expect(strip).toBeVisible();
		await expect(strip.getByTestId('item-tab')).toHaveCount(2);
		await strip.getByTestId('pane-head-1').getByRole('tab').click();
		await expect(pane(page, 1)).toBeVisible();
		await expect(pane(page, 0)).toHaveCount(0);
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

});
