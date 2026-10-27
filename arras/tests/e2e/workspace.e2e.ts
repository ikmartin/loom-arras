// Reading mode as items in two panes: what a pane opens on, its tabs and its views, the divider between the panes, focus, the arrangement the URL keeps, and what gives way in a narrow window. Grouped by the principle each rule serves, and each test named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { beside, openHere, pane, prefs, scrollPane, viewMenu } from '../workspace';
import { serve, servePapers } from '../manifest';

/** Advertise a write API that annotates, so a document's and a node's bar carries the tools. */
async function writes(page: Page) {
	await page.route('**/_api', (route) => route.fulfill({ json: { write_api: 1, capabilities: ['annotate'], token: 't' } }));
}

/** Serve the fixture with Kre99 and Har77 filed, so both are works with pages. */
async function withPapers(page: Page) {
	await serve(page, (m) => {
		m.references.Kre99.artifacts.pdf = true;
		m.references.Har77.artifacts.pdf = true;
	});
	await servePapers(page);
}

const tabs = (page: Page, index: number) => pane(page, index).getByTestId('item-tab');
const controls = (page: Page, index: number) => pane(page, index).getByTestId('item-controls');

test.describe('V1 · open on the thing itself', () => {
	test('a document opens on the paper', async ({ page }) => {
		await page.setViewportSize({ width: 1440, height: 900 });
		await page.goto('/master/main');
		const fragment = pane(page, 0).locator('.fragment').first();
		await expect(fragment).toBeVisible();
		const at = await page.evaluate(() => {
			const top = document.querySelector('[data-pane="0"] [data-testid="item-controls"]')!.getBoundingClientRect().bottom;
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

	test("a pane head carries its tabs and nothing else, and its toolbar leads with its item's views", async ({ page }) => {
		await withPapers(page);
		await page.goto('/master/main' + beside('/library/Kre99'));
		for (const [i, views] of [
			[0, false],
			[1, true]
		] as const) {
			const head = page.getByTestId(`pane-head-${i}`);
			await expect(head).toBeVisible();
			expect(await head.evaluate((h) => [...h.children].map((c) => c.getAttribute('role')))).toEqual(['tablist']);
			const kinds = await head.getByRole('tablist').evaluate((t) => [...t.children].map((c) => (c as HTMLElement).dataset.testid));
			expect(kinds).toEqual(kinds.map(() => 'item-tab'));
			const first = await controls(page, i).evaluate((t) => t.firstElementChild?.getAttribute('aria-label') ?? '');
			if (views) expect(first).toBe('views of Kre99');
			else expect(first).not.toMatch(/^views of /);
		}
	});

	test('every pane draws its own toolbar, for every kind, and no rail spans the panes', async ({ page }) => {
		await withPapers(page);
		for (const at of ['/master/main' + beside('/node/sy-0003'), '/library/Kre99' + beside('/context/sy-0003'), '/canon/widgets-v1' + beside('/session/s-2026-09-16-0001')]) {
			await page.goto(at);
			await expect(pane(page, 1)).toBeVisible();
			await expect(pane(page, 0)).toHaveClass(/focused/);
			await expect(page.getByTestId('reading-rail')).toHaveCount(0);
			for (const i of [0, 1]) await expect(controls(page, i), at).toBeVisible();
			// the unfocused pane's is quieter, as its tabs are
			await expect(pane(page, 1)).toHaveClass(/dim/);
			await expect(pane(page, 0)).not.toHaveClass(/dim/);
		}
	});
});

test.describe('V2 · say it once, in the place that governs it', () => {
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

	test("a pane's controls are drawn once in it, and act on it alone", async ({ page }) => {
		await withPapers(page);
		await page.goto('/library/Kre99' + beside('/library/Har77'));
		await expect(pane(page, 0).getByTestId('pdf-doc')).toBeVisible();
		await expect(pane(page, 1).getByTestId('pdf-doc')).toBeVisible();
		for (const i of [0, 1]) await expect(pane(page, i).getByRole('textbox', { name: /^Zoom/ })).toHaveCount(1);
		await expect(pane(page, 0).getByRole('textbox', { name: /^Zoom/ })).toHaveAccessibleName(/Kre99/);
		await expect(pane(page, 1).getByRole('textbox', { name: /^Zoom/ })).toHaveAccessibleName(/Har77/);
	});
});

test.describe('V3 · claim only what is known', () => {
	test('a lone tab offers no controls', async ({ page }) => {
		await page.goto('/master/main');
		await expect(tabs(page, 0)).toHaveCount(1);
		await expect(page.getByTestId('tab-move')).toHaveCount(0);
		await expect(page.getByTestId('tab-close')).toHaveCount(0);
	});

});

test.describe('V4 · name the question', () => {
	test("compare stands in the focused pane's toolbar, disabled with its reason while nothing beside pairs", async ({ page }) => {
		await withPapers(page);
		await page.goto('/library/Kre99');
		// one pane: nothing to compare with, so no compare
		await expect(controls(page, 0)).toBeVisible();
		await expect(page.getByTestId('pane-compare')).toHaveCount(0);
		await page.goto('/library/Kre99' + beside('/master/main'));
		const compare = controls(page, 0).getByTestId('pane-compare');
		await expect(compare).toBeVisible();
		await expect(compare).toBeDisabled();
		await expect(compare).toHaveAccessibleName('compare');
		await expect(compare).toHaveAttribute('title', /.+/);
		// the other pane draws none
		await expect(controls(page, 1).getByTestId('pane-compare')).toHaveCount(0);
	});

	test('every control names its target', async ({ page }) => {
		await withPapers(page);
		await writes(page);
		for (const [at, name] of [
			['/master/main', 'main.tex'],
			['/node/sy-0003', 'Theorem'],
			['/library/Kre99', 'Kre99']
		]) {
			await page.goto(at);
			await expect(controls(page, 0)).toHaveAttribute('aria-label', `controls for ${name === 'Theorem' ? 'Theorem 2.1' : name}`);
			// the menu's lines are the toolbar's too, the pane's own line among them
			await viewMenu(page);
			for (const group of [controls(page, 0), page.getByTestId('toolbar-menu')]) {
				await expect(group.locator('button, a').first()).toBeVisible();
				const names = await group.locator('button, a, input, [role^="menuitem"]').evaluateAll((els) => els.map((e) => e.getAttribute('aria-label') ?? ''));
				for (const n of names) expect(n, n).toContain(name);
			}
		}
	});

	test('a control names the destination, not the state', async ({ page }) => {
		await page.goto('/master/main');
		await viewMenu(page);
		await expect(page.getByTestId('toggle-annotations')).toHaveText(/^show all annotations/);
	});
});

test.describe('V5 · following a connection must not cost the thing you followed it from', () => {
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
		expect(await card.evaluate((c) => ({ inPane: c.closest('[data-pane]')?.getAttribute('data-pane') ?? null, position: getComputedStyle(c).position }))).toEqual({ inPane: null, position: 'fixed' });
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
		// a wheel over the node's pane focuses it: its toolbar is the brighter, and compare moves to it
		await pane(page, 1).hover();
		await page.mouse.wheel(0, 200);
		await expect(pane(page, 1)).toHaveClass(/focused/);
		await expect(pane(page, 0)).toHaveClass(/dim/);
		await expect(controls(page, 1)).toHaveAttribute('aria-label', 'controls for Theorem 2.1');
		await expect(controls(page, 1).getByTestId('pane-compare')).toBeVisible();
		await expect(controls(page, 0).getByTestId('pane-compare')).toHaveCount(0);
		await viewMenu(page);
		await expect(page.getByTestId('open-context')).toBeVisible();
		await page.keyboard.press('Escape');
		// and a wheel over the document: on the document
		await pane(page, 0).hover();
		await page.mouse.wheel(0, 200);
		await expect(pane(page, 0)).toHaveClass(/focused/);
		await expect(controls(page, 0).getByTestId('pane-compare')).toBeVisible();
	});

	test('the focused pane is marked by its shadow, with no line on its head', async ({ page }) => {
		await page.goto('/master/main' + beside('/node/sy-0003'));
		await expect(pane(page, 0)).toHaveClass(/focused/);
		await expect(pane(page, 0).getByTestId('pane-head-0')).toHaveCSS('box-shadow', 'none');
		await expect(pane(page, 0)).not.toHaveCSS('box-shadow', 'none');
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

/** Count what goes through MathJax from here on, as the document's text or a card's, and remember the document's first block. */
async function watchTypesetting(page: Page): Promise<void> {
	await page.evaluate(() => {
		const w = window as unknown as { MathJax: { typesetPromise: (els: Element[]) => Promise<void> }; typeset: string[]; first: Element | null; wrapped?: boolean };
		w.typeset = [];
		w.first = document.querySelector('[data-pane="0"] .fragment [data-src]');
		if (w.wrapped) return;
		w.wrapped = true;
		const real = w.MathJax.typesetPromise.bind(w.MathJax);
		w.MathJax.typesetPromise = (els) => {
			w.typeset.push(els.some((e) => e.closest('.fragment') && !e.closest('aside.comment-slot')) ? 'document' : 'card');
			return real(els);
		};
	});
}

const allTypeset = (page: Page) => page.waitForFunction(() => !!document.querySelector('[data-pane="0"] .fragment mjx-container') && document.querySelectorAll('.fragment .math:not(:has(mjx-container))').length === 0);

test.describe('coming back to a document', () => {
	// leaving a document destroyed it, and coming back drew and typeset it from nothing: a second and more on a whole paper (plan 0.19.2)
	test('a tab switched away from and back to is taken back as it was, with nothing typeset again', async ({ page }) => {
		await page.goto('/master/main');
		await allTypeset(page);
		await page.getByTestId('docs-drafts').getByRole('link', { name: 'talk.tex' }).click();
		await expect(tabs(page, 0)).toHaveCount(2);
		await allTypeset(page);
		await tabs(page, 0).first().getByRole('tab').click();
		await allTypeset(page);
		await watchTypesetting(page);
		await page.getByTestId('docs-drafts').getByRole('link', { name: 'talk.tex' }).click();
		await allTypeset(page);
		await page.evaluate(() => ((window as unknown as { typeset: string[] }).typeset = []));
		await tabs(page, 0).first().getByRole('tab').click();
		await expect.poll(() => page.evaluate(() => (window as unknown as { first: Element }).first.isConnected)).toBe(true);
		expect(await page.evaluate(() => (window as unknown as { typeset: string[] }).typeset)).not.toContain('document');
		await page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-0001"]').click();
		await expect(page.locator('aside.comment-slot.floating article.box').first()).toBeVisible();
	});

	test('reading come back to from the graph is taken back as it was, with nothing typeset again', async ({ page }) => {
		await page.goto('/master/main');
		await allTypeset(page);
		await watchTypesetting(page);
		// the whole graph is reached from the local graph's expanded view
		await page.getByTestId('local-graph-open').click();
		await page.getByTestId('local-graph-expand').click();
		await page.getByTestId('open-graph').click();
		await page.locator('svg g.node').first().waitFor();
		await page.getByTestId('primary-docs').click();
		await expect.poll(() => page.evaluate(() => (window as unknown as { first: Element }).first.isConnected)).toBe(true);
		await allTypeset(page);
		expect(await page.evaluate(() => (window as unknown as { typeset: string[] }).typeset)).not.toContain('document');
		await page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-0001"]').click();
		await expect(page.locator('aside.comment-slot.floating article.box').first()).toBeVisible();
	});
});

test.describe('tabs', () => {
	test('a context is marked by a glyph and named by its node, and says so where it is read as text', async ({ page }) => {
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
		expect(pad, 'the right padding of the label, px').toBeGreaterThanOrEqual(36);
		await expect(label).toHaveCSS('text-overflow', 'ellipsis');
	});
});

test.describe('the tab strip', () => {
	/** The widths of a pane's tabs, px. */
	const widths = (page: Page, index: number) => tabs(page, index).evaluateAll((els) => els.map((e) => e.getBoundingClientRect().width));

	/** Open a node in the focused pane, as a link outside the panes does. */
	const open = (page: Page, id: string) => openHere(page, `/node/${id}`);

	test("each pane's toolbar begins with its own item's views", async ({ page }) => {
		await withPapers(page);
		// a document beside a paper: the paper's pane carries Paper · Info though the document's pane is focused, and the document's carries none
		await page.goto('/master/main' + beside('/library/Kre99'));
		await expect(pane(page, 0)).toHaveClass(/focused/);
		await expect(pane(page, 0).getByRole('group', { name: /^views of / })).toHaveCount(0);
		const views = pane(page, 1).getByRole('group', { name: 'views of Kre99' });
		await expect(views.getByRole('button')).toHaveText(['Paper', 'Info']);
		const bar = (await controls(page, 1).boundingBox())!;
		const box = (await views.boundingBox())!;
		expect(Math.abs(box.x - bar.x), "the views start at the toolbar's left edge, px").toBeLessThanOrEqual(1);
		// the current view is underlined in the accent, the others are links
		const paper = pane(page, 1).getByTestId('tab-paper');
		await expect(paper).toHaveAttribute('aria-pressed', 'true');
		expect(await paper.evaluate((b) => getComputedStyle(b).boxShadow)).toContain('inset');
		await expect(pane(page, 1).getByTestId('tab-info')).toHaveCSS('box-shadow', 'none');
		// a click switches the view in its own pane, which takes focus, and the address follows
		await pane(page, 1).getByTestId('tab-info').click();
		await expect(pane(page, 1).getByTestId('tab-info')).toHaveAttribute('aria-pressed', 'true');
		await expect(pane(page, 1)).toHaveClass(/focused/);
		await expect.poll(() => new URL(page.url()).searchParams.get('beside')).toContain('view=info');

		// two papers: each toolbar its own item's views, switched apart
		await page.goto('/library/Kre99' + beside('/library/Har77'));
		await expect(pane(page, 0).getByRole('group', { name: 'views of Kre99' })).toBeVisible();
		await expect(pane(page, 1).getByRole('group', { name: 'views of Har77' })).toBeVisible();
		await pane(page, 1).getByTestId('tab-info').click();
		await expect(pane(page, 1).getByTestId('tab-info')).toHaveAttribute('aria-pressed', 'true');
		await expect(pane(page, 0).getByTestId('tab-paper')).toHaveAttribute('aria-pressed', 'true');

		// a session beside a document: Transcript · What it did, in the unfocused pane
		await page.goto('/master/main' + beside('/session/s-2026-09-16-0001'));
		await expect(pane(page, 0)).toHaveClass(/focused/);
		await expect(pane(page, 1).getByRole('group', { name: /^views of / }).getByRole('button')).toHaveText(['Transcript', 'What it did']);
		await expect(pane(page, 1).getByTestId('tab-chat')).toHaveAttribute('aria-pressed', 'true');
	});

	test('tabs are 148px, narrow evenly, then scroll with the active tab in view', async ({ page }) => {
		// the right pane is two fifths of the workspace, about 450px, so ten tabs pass the floor
		await prefs(page, { divider: 0.6 });
		await page.setViewportSize({ width: 1440, height: 900 });
		await page.goto('/node/sy-0001' + beside('/node/sy-0002'));
		await tabs(page, 1).first().getByRole('tab').click();
		await expect(pane(page, 1)).toHaveClass(/focused/);
		const row = pane(page, 1).getByRole('tablist');
		const floor = 45; // 1.5 times the strip's 30px

		// two tabs have room, and are 148px
		await open(page, 'sy-0003');
		await expect(tabs(page, 1)).toHaveCount(2);
		expect(await widths(page, 1)).toEqual([148, 148]);

		// four do not: each narrows by the same amount, and together they fill the strip
		for (const id of ['sy-0006', 'sy-0007']) await open(page, id);
		await expect(tabs(page, 1)).toHaveCount(4);
		const four = await widths(page, 1);
		expect(Math.max(...four) - Math.min(...four), 'the spread of the widths, px').toBeLessThanOrEqual(1);
		expect(four[0]).toBeLessThan(148);
		expect(four[0]).toBeGreaterThan(floor);
		const room = await row.evaluate((r) => ({ scroll: r.scrollWidth, client: r.clientWidth }));
		expect(room.scroll).toBeLessThanOrEqual(room.client);

		// twelve are at the floor, and the row scrolls with the newest, the active tab, in view
		for (const id of ['sy-0008', 'sy-0009', 'sy-000A', 'sy-000B', 'sy-000C', 'sy-000D', 'sy-000E', 'sy-999A']) await open(page, id);
		await expect(tabs(page, 1)).toHaveCount(12);
		for (const w of await widths(page, 1)) expect(w).toBeCloseTo(floor, 0);
		const inView = () =>
			row.evaluate((r) => {
				const on = r.querySelector('[aria-selected="true"]')!.parentElement!.getBoundingClientRect();
				const at = r.getBoundingClientRect();
				return { scrolls: r.scrollWidth > r.clientWidth, left: r.scrollLeft, inside: on.left >= at.left - 0.5 && on.right <= at.right + 0.5 };
			});
		const last = await inView();
		expect(last.scrolls).toBe(true);
		expect(last.left).toBeGreaterThan(0);
		expect(last.inside).toBe(true);
		// choosing a tab scrolled out of sight brings it back into view
		await open(page, 'sy-0002');
		await expect(tabs(page, 1).first().getByRole('tab')).toHaveAttribute('aria-selected', 'true');
		await expect.poll(async () => (await inView()).inside).toBe(true);
		expect((await inView()).left).toBe(0);

		// below 90px the active tab shows its controls only under the pointer
		const active = tabs(page, 1).first();
		await page.mouse.move(0, 0);
		await expect(active.getByTestId('tab-close')).toBeHidden();
		await active.hover();
		await expect(active.getByTestId('tab-close')).toBeVisible();
		// and its whole name is its title
		await expect(active.getByRole('tab')).toHaveAttribute('title', /Lemma/);
	});

	test('past the floor the tabs scroll, and the views beneath them keep their place', async ({ page }) => {
		test.setTimeout(60000);
		await withPapers(page);
		// the right pane as narrow as a work lets it be, 420px, so ten tabs pass the floor
		await prefs(page, { divider: 0.8 });
		await page.setViewportSize({ width: 1440, height: 900 });
		await page.goto('/node/sy-0001' + beside('/library/Kre99'));
		await tabs(page, 1).first().getByRole('tab').click();
		for (const id of ['sy-0003', 'sy-0006', 'sy-0007', 'sy-0008', 'sy-0009', 'sy-000A', 'sy-000B', 'sy-000C', 'sy-000D']) await open(page, id);
		// the paper brought forward as a link does it, which reveals its tab; a click on a tab still scrolling never settles on the runner
		await openHere(page, '/library/Kre99');
		const views = pane(page, 1).getByRole('group', { name: 'views of Kre99' });
		await expect(views).toBeVisible();
		const tablist = pane(page, 1).getByRole('tablist');
		const box = (await views.boundingBox())!;
		const scrolled = await tablist.evaluate((r) => {
			r.scrollLeft = r.scrollWidth;
			return r.scrollLeft;
		});
		expect(scrolled).toBeGreaterThan(0);
		expect(await views.boundingBox()).toEqual(box);
	});
});

test.describe('the divider', () => {
	test('it is a 3px rule, beneath what a pane opens over the text', async ({ page }) => {
		await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
		const width = await page.getByTestId('divider').evaluate((d) => getComputedStyle(d, '::before').width);
		expect(width).toBe('3px');
		// a box floating over the text of either pane is drawn over the divider, not under it
		const z = await page.evaluate(() => [...document.querySelectorAll('[data-pane]')].map((p) => Number(getComputedStyle(p).zIndex)));
		const dz = await page.getByTestId('divider').evaluate((d) => Number(getComputedStyle(d).zIndex));
		expect(Math.min(...z), `panes at z ${z.join(', ')}, the divider at ${dz}`).toBeGreaterThan(dz);
	});

	test('a drag sizes the first pane alone, and the preference is stored at the drop', async ({ page }) => {
		// a custom property on the workspace was inherited by every element of both documents, so each move restyled them all (plan 0.19.1)
		await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
		const divider = page.getByTestId('divider');
		const frame = (await page.getByTestId('workspace').boundingBox())!;
		const handle = (await divider.boundingBox())!;
		const stored = () => page.evaluate(() => (JSON.parse(localStorage.getItem('arras.prefs') ?? '{}') as { divider?: number }).divider);
		const before = await stored();
		await page.mouse.move(handle.x + handle.width / 2, handle.y + handle.height / 2);
		await page.mouse.down();
		await page.mouse.move(frame.x + frame.width * 0.3, handle.y + handle.height / 2, { steps: 6 });
		await expect.poll(() => pane(page, 0).evaluate((p) => p.style.flex)).toMatch(/%/);
		expect(await page.getByTestId('workspace').evaluate((w) => w.style.getPropertyValue('--ratio'))).toBe('');
		expect(await stored()).toBe(before);
		await page.mouse.up();
		await expect.poll(stored).toBeLessThan(0.4);
	});

	test('while it moves each pane keeps its content at the width it had, laid out again once at the drop', async ({ page }) => {
		// laid out at every width, a long paper's frame cost 50-60 ms and the divider trailed the pointer at about 20 frames a second
		await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
		const divider = page.getByTestId('divider');
		const frame = (await page.getByTestId('workspace').boundingBox())!;
		const handle = (await divider.boundingBox())!;
		const widths = () => page.evaluate(() => [...document.querySelectorAll<HTMLElement>('[data-pane]')].map((p) => [p.getBoundingClientRect().width, p.querySelector('.body')!.getBoundingClientRect().width]));
		const [[, left], [, right]] = await widths();
		await page.mouse.move(handle.x + handle.width / 2, handle.y + handle.height / 2);
		await page.mouse.down();
		await page.mouse.move(frame.x + frame.width * 0.3, handle.y + handle.height / 2, { steps: 6 });
		await expect.poll(async () => (await widths())[0][0]).toBeLessThan(left - 50);
		const [[, heldLeft], [, heldRight]] = await widths();
		expect(Math.abs(heldLeft - left)).toBeLessThan(1);
		expect(Math.abs(heldRight - right)).toBeLessThan(1);
		await page.mouse.up();
		await expect.poll(async () => (await widths()).every(([p, b]) => Math.abs(p - b) < 1)).toBe(true);
	});

	test('it drags, snaps at the middle, resets on double-click and nudges by key; below the breakpoint one pane shows', async ({ page }) => {
		await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
		const divider = page.getByTestId('divider');
		await expect(divider).toBeVisible();
		const frame = (await page.getByTestId('workspace').boundingBox())!;
		// dragged to a third of the frame, the ratio follows the pointer
		const handle = (await divider.boundingBox())!;
		await page.mouse.move(handle.x + handle.width / 2, handle.y + handle.height / 2);
		await page.mouse.down();
		await page.mouse.move(frame.x + frame.width * 0.33, handle.y + handle.height / 2, { steps: 6 });
		await page.mouse.up();
		await expect.poll(async () => Number(await divider.getAttribute('aria-valuenow'))).toBeLessThan(40);
		// near the middle it snaps to it, and nowhere else
		await page.mouse.move(frame.x + frame.width * 0.33, handle.y + handle.height / 2);
		await page.mouse.down();
		await page.mouse.move(frame.x + frame.width * 0.515, handle.y + handle.height / 2, { steps: 6 });
		await page.mouse.up();
		await expect(divider).toHaveAttribute('aria-valuenow', '50');
		// the keys nudge, Home recentres, a double-click resets
		await divider.focus();
		await page.keyboard.press('ArrowRight');
		await page.keyboard.press('ArrowRight');
		await expect(divider).toHaveAttribute('aria-valuenow', '54');
		await page.keyboard.press('Home');
		await expect(divider).toHaveAttribute('aria-valuenow', '50');
		await page.keyboard.press('ArrowLeft');
		await divider.dblclick();
		await expect(divider).toHaveAttribute('aria-valuenow', '50');
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
});

test.describe('a narrow window', () => {
	test('the column goes first, folded to its rail, and the stored choice is not rewritten', async ({ page }) => {
		await serve(page, (m) => (m.references.Kre99.artifacts.pdf = true));
		await page.setViewportSize({ width: 1100, height: 800 });
		await page.goto('/library/Kre99');
		await expect(page.locator('.panel.away')).toHaveCount(1);
		expect((await page.getByTestId('column').boundingBox())!.width).toBeLessThanOrEqual(45);
		// what must stay in reach stays: unfold, search, the problems chip and the session's dot
		await expect(page.getByTestId('panel-fold')).toBeVisible();
		await expect(page.getByTestId('problems-chip')).toBeVisible();
		await expect(page.getByTestId('session-footer')).toBeVisible();
		expect(await page.evaluate(() => JSON.parse(localStorage.getItem('arras.prefs') ?? '{}').panel)).not.toBe(false);
	});

	test("a narrow pane's toolbar keeps its views and view whole, its bar giving way first", async ({ page }) => {
		await serve(page, (m) => (m.references.Kre99.artifacts.pdf = true));
		await page.setViewportSize({ width: 760, height: 800 });
		await page.goto('/library/Kre99');
		const bar = (await controls(page, 0).boundingBox())!;
		const views = (await pane(page, 0).getByRole('group', { name: 'views of Kre99' }).boundingBox())!;
		expect(Math.abs(views.x - bar.x), "the views start at the toolbar's left edge, px").toBeLessThanOrEqual(1);
		await expect(pane(page, 0).getByTestId('toolbar-view')).toBeInViewport({ ratio: 1 });
		await expect(page.getByTestId('zoom-at')).toBeVisible();
	});

	test("below the two-pane width one strip holds both panes' tabs, and the shown pane's toolbar leads with its views", async ({ page }) => {
		await withPapers(page);
		await page.setViewportSize({ width: 640, height: 800 });
		await page.goto('/master/main' + beside('/library/Kre99'));
		const strip = page.getByTestId('narrow-strip');
		await expect(strip).toBeVisible();
		await expect(strip.getByTestId('item-tab')).toHaveCount(2);
		await expect(strip.getByRole('group', { name: /^views of / })).toHaveCount(0);
		await strip.getByTestId('pane-head-1').getByRole('tab').click();
		const views = controls(page, 1).getByRole('group', { name: 'views of Kre99' });
		await expect(views.getByRole('button')).toHaveText(['Paper', 'Info']);
		const bar = (await controls(page, 1).boundingBox())!;
		expect(Math.abs((await views.boundingBox())!.x - bar.x)).toBeLessThanOrEqual(1);
	});
});

test.describe('the toolbar', () => {
	/** The top of the first line of text in a pane's body, px: its first text that is drawn, a title or a first line alike. */
	const firstLine = (page: Page, index: number) =>
		pane(page, index)
			.locator('> .body')
			.evaluate((body) => {
				const walk = document.createTreeWalker(body, NodeFilter.SHOW_TEXT);
				for (let n = walk.nextNode(); n; n = walk.nextNode()) {
					if (!n.textContent?.trim()) continue;
					const range = document.createRange();
					range.selectNodeContents(n);
					const box = [...range.getClientRects()].find((r) => r.width > 0 && r.height > 0);
					if (box) return box.top;
				}
				return NaN;
			});

	test("it is a row in the pane's flow under its tabs, the width of the pane, one line on the sheet", async ({ page }) => {
		await page.setViewportSize({ width: 1440, height: 900 });
		await page.goto('/master/main' + beside('/node/sy-0003'));
		for (const i of [0, 1]) {
			const bar = controls(page, i);
			await expect(bar).toBeVisible();
			expect(await bar.evaluate((b) => b.closest('.body'))).toBeNull();
			expect(await bar.evaluate((b) => getComputedStyle(b).position)).toBe('static');
			const at = (await bar.boundingBox())!;
			const head = (await page.getByTestId(`pane-head-${i}`).boundingBox())!;
			const body = (await pane(page, i).locator('> .body').boundingBox())!;
			expect(at.height, 'one line, px').toBeLessThan(34);
			expect(Math.abs(at.y - (head.y + head.height)), 'under the tabs, px').toBeLessThanOrEqual(1);
			expect(body.y, 'the page starts below it').toBeGreaterThanOrEqual(at.y + at.height - 1);
			expect(Math.abs(at.width - head.width), 'the width of the pane, px').toBeLessThanOrEqual(1);
		}
	});

	test('the first line starts below the row in a half-width pane, and moving focus moves no text', async ({ page }) => {
		await page.setViewportSize({ width: 1440, height: 900 });
		await page.goto('/node/sy-0003' + beside('/master/main'));
		await expect(pane(page, 1).locator('.fragment').first()).toBeVisible();
		for (const i of [0, 1]) {
			const bar = (await controls(page, i).boundingBox())!;
			const line = await firstLine(page, i);
			expect(line - (bar.y + bar.height), `pane ${i}: from the row's foot to the first line, px`).toBeGreaterThanOrEqual(8);
			expect(line - (bar.y + bar.height), `pane ${i}: from the row's foot to the first line, px`).toBeLessThanOrEqual(40);
		}
		const before = [await firstLine(page, 0), await firstLine(page, 1)];
		await tabs(page, 1).first().getByRole('tab').click();
		await expect(pane(page, 1)).toHaveClass(/focused/);
		expect([await firstLine(page, 0), await firstLine(page, 1)]).toEqual(before);
	});

	test('the bar, then view with every other control in full words and its key, the pane\'s own line last; the divider only when something stands left of view', async ({ page }) => {
		await writes(page);
		await page.goto('/master/main');
		const bar = controls(page, 0);
		await expect(bar.getByTestId('tool-select')).toBeVisible();
		const order = await bar.locator('button').evaluateAll((els) => els.map((e) => (e as HTMLElement).dataset.testid));
		expect(order).toEqual(['tool-select', 'tool-box', 'toolbar-view']);
		await expect(page.getByTestId('toolbar-view')).toHaveCSS('border-left-style', 'solid');
		await expect(page.getByTestId('toolbar-view')).toHaveAttribute('aria-label', 'view menu for main.tex');
		await viewMenu(page);
		const menu = page.getByTestId('toolbar-menu');
		await expect(menu).toHaveAttribute('role', 'menu');
		await expect(menu.getByRole('menuitemcheckbox')).toHaveText(['show all annotationse', 'show settled annotationss', 'annotations off in this panea']);
		await expect(menu.getByTestId('toggle-settled')).toHaveAttribute('aria-keyshortcuts', 's');
		await expect(menu.getByTestId('toggle-hide-notes')).toHaveAttribute('aria-keyshortcuts', 'a');
		await expect(menu.getByTestId('open-pdf')).toHaveText('open the PDF');
		// a mode inside it is on: the dot on view says so, and the menu closed on the choice
		await expect(page.getByTestId('toolbar-view-on')).toHaveCount(0);
		await page.getByTestId('toggle-settled').click();
		await expect(menu).toHaveCount(0);
		await expect(page.getByTestId('toolbar-view-on')).toBeVisible();
		await viewMenu(page);
		await expect(page.getByTestId('toggle-settled')).toHaveAttribute('aria-checked', 'true');
		await expect(page.getByTestId('toggle-settled')).toHaveText(/^hide settled annotations/);
		// the keys move through the menu, and Escape hands focus back to view
		await expect(page.getByTestId('toggle-annotations')).toBeFocused();
		await page.keyboard.press('ArrowDown');
		await expect(page.getByTestId('toggle-settled')).toBeFocused();
		await page.keyboard.press('Escape');
		await expect(menu).toHaveCount(0);
		await expect(page.getByTestId('toolbar-view')).toBeFocused();

		// nothing serving: view stands alone, with no divider before it
		await page.unrouteAll();
		await page.goto('/master/main');
		await expect(page.getByTestId('toolbar-view')).toBeVisible();
		expect(await controls(page, 0).locator('button').evaluateAll((els) => els.map((e) => (e as HTMLElement).dataset.testid))).toEqual(['toolbar-view']);
		await expect(page.getByTestId('toolbar-view')).toHaveCSS('border-left-style', 'none');
	});

	test('a node keeps its context and its source under view', async ({ page }) => {
		await page.goto('/node/sy-0003');
		await viewMenu(page);
		await expect(page.getByTestId('toolbar-menu').locator('[role^="menuitem"]')).toHaveText(['show all annotationse', 'show settled annotationss', 'open its context beside', 'show verbatim code', 'annotations off in this panea']);
		await page.getByTestId('open-context').click();
		await expect(pane(page, 1).getByTestId('context')).toBeVisible();
	});

	test('a paper shows settled annotations from its toolbar, and greys its page tools and its PDF off the Paper view', async ({ page }) => {
		await withPapers(page);
		await page.goto('/library/Kre99');
		await expect(page.getByTestId('pdf-doc')).toBeVisible();
		await viewMenu(page);
		await expect(page.getByTestId('toolbar-menu').locator('[role^="menuitem"]')).toHaveText(['show settled annotations', 'open the PDF', 'annotations off in this panea']);
		await expect(page.getByTestId('open-pdf')).toHaveAttribute('href', /paper\.pdf$/);
		await page.getByTestId('toggle-settled').click();
		await expect(page.locator('.paper').first()).toHaveClass(/show-settled/);
		await expect(page.getByTestId('toolbar-view-on')).toBeVisible();
		// off the paper: drawn and greyed, the PDF with its reason
		await page.getByTestId('tab-info').click();
		await expect(page.getByTestId('tool-select')).toBeDisabled();
		await viewMenu(page);
		await expect(page.getByTestId('open-pdf')).toHaveAttribute('aria-disabled', 'true');
		await expect(page.getByTestId('open-pdf')).toHaveAttribute('title', /Paper view/);
	});

	test('a paper with no readable copy greys its Paper view and opens on Info, which reads its digest', async ({ page }) => {
		await page.goto('/library/Kre99');
		const paper = pane(page, 0).getByTestId('tab-paper');
		await expect(paper).toBeDisabled();
		await expect(paper).toHaveAttribute('title', 'No copy of this work is on file');
		await expect(pane(page, 0).getByTestId('tab-info')).toHaveAttribute('aria-pressed', 'true');
		await expect(pane(page, 0).getByTestId('work-digest').locator('.env').first()).toBeVisible();
		await expect.poll(() => new URL(page.url()).search).toBe('');
		await expect(page.getByTestId('tool-select')).toBeDisabled();
		await viewMenu(page);
		await expect(page.getByTestId('open-pdf')).toHaveAttribute('title', 'No copy of this work is on file');
	});

	test("a landmark, a context and a session draw a toolbar too: their views, and view with the pane's own line", async ({ page }) => {
		for (const at of ['/canon/widgets-v1', '/context/sy-0003', '/session/s-2026-09-16-0001']) {
			await page.goto(at);
			await expect(controls(page, 0), at).toBeVisible();
			await viewMenu(page);
			await expect(page.getByTestId('toolbar-menu').locator('[role^="menuitem"]'), at).toHaveText(['annotations off in this panea']);
			await page.keyboard.press('Escape');
		}
		await expect(controls(page, 0).getByRole('group', { name: /^views of / }).getByRole('button')).toHaveText(['Transcript', 'What it did']);
	});

	test('annotations off hides every mark in its own pane only, from view or by `a`', async ({ page }) => {
		await page.goto('/master/main' + beside('/node/sy-0003'));
		const mark = (i: number) => pane(page, i).locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-0001"]').first();
		for (const i of [0, 1]) await expect(mark(i)).not.toHaveClass(/hidden/);
		await viewMenu(page, 0);
		await page.getByTestId('toggle-hide-notes').click();
		await expect(mark(0)).toHaveClass(/hidden/);
		await expect(mark(1)).not.toHaveClass(/hidden/);
		await expect(controls(page, 0).getByTestId('toolbar-view-on')).toBeVisible();
		// `a` from inside the other pane hides that pane's, and again shows them
		await pane(page, 1).locator('.fragment').first().press('a');
		await expect(mark(1)).toHaveClass(/hidden/);
		await pane(page, 1).locator('.fragment').first().press('a');
		await expect(mark(1)).not.toHaveClass(/hidden/);
		await expect(mark(0)).toHaveClass(/hidden/);
	});
});
