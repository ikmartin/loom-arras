// Reading mode as items in two panes: what a pane opens on, its tabs and its views, the divider between the panes, focus, the arrangement the URL keeps, and what gives way in a narrow window. Grouped by the principle each rule serves, and each test named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { beside, pane, prefs, scrollPane, viewMenu } from '../workspace';
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

	test("a pane head carries its tabs and its item's views, and nothing else", async ({ page }) => {
		await withPapers(page);
		await page.goto('/master/main' + beside('/library/Kre99'));
		for (const [i, views] of [
			[0, false],
			[1, true]
		] as const) {
			const head = page.getByTestId(`pane-head-${i}`);
			await expect(head).toBeVisible();
			const parts = await head.evaluate((h) => [...h.children].map((c) => c.getAttribute('role')));
			expect(parts).toEqual(views ? ['tablist', 'group'] : ['tablist']);
			const kinds = await head.getByRole('tablist').evaluate((t) => [...t.children].map((c) => (c as HTMLElement).dataset.testid));
			expect(kinds).toEqual(kinds.map(() => 'item-tab'));
		}
	});

	test('the rail stands above the panes, and only the focused pane draws a toolbar', async ({ page }) => {
		await withPapers(page);
		for (const [at, drawn] of [
			['/master/main' + beside('/node/sy-0003'), true],
			['/library/Kre99' + beside('/context/sy-0003'), true],
			['/canon/widgets-v1' + beside('/session/s-2026-09-16-0001'), false]
		] as const) {
			await page.goto(at);
			await expect(pane(page, 1)).toBeVisible();
			await expect(pane(page, 0)).toHaveClass(/focused/);
			for (const i of [0, 1]) await expect(pane(page, i).getByTestId('reading-rail')).toHaveCount(0);
			// the focused pane draws its item's toolbar, where it has controls; a landmark has none, and draws no empty box
			if (drawn) await expect(controls(page, 0)).toBeVisible();
			else await expect(controls(page, 0)).toHaveCount(0);
			await expect(controls(page, 1)).toHaveCount(0);
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

});

test.describe('P4 · name the question', () => {
	test('the global rail holds the filter and compare', async ({ page }) => {
		await withPapers(page);
		await page.goto('/library/Kre99');
		const rail = page.getByTestId('reading-rail');
		await expect(rail).toBeVisible();
		expect(await rail.evaluate((r) => r.children.length)).toBe(2);
		await expect(rail.getByRole('group', { name: 'which annotations the page shows' })).toBeVisible();
		// compare is drawn, and disabled until it does what its title says
		const compare = rail.getByTestId('rail-compare');
		await expect(compare).toBeVisible();
		await expect(compare).toBeDisabled();
		await expect(compare).toHaveAttribute('aria-disabled', 'true');
		await expect(compare).toHaveAccessibleName('compare');
		await expect(compare).toHaveAttribute('title', /^Compare the two open documents.*0\.17$/);
		// nothing about one item: its views are in its pane's strip, its controls on its pane
		await expect(rail.locator('[data-testid^="tab-"], [data-testid="zoom-at"]')).toHaveCount(0);
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
			// the menu's lines are the toolbar's too; the pin is one choice for every toolbar and names none
			await viewMenu(page);
			for (const group of [controls(page, 0), pane(page, 0).getByRole('group', { name: /^views of / })]) {
				if (!(await group.count())) continue;
				await expect(group.locator('button, a').first()).toBeVisible();
				const names = await group.locator('button:not([data-testid="toolbar-pin"]), a, input').evaluateAll((els) => els.map((e) => e.getAttribute('aria-label') ?? ''));
				for (const n of names) expect(n, n).toContain(name);
			}
			await expect(page.getByTestId('toolbar-pin')).toHaveAttribute('aria-label', 'fade');
		}
	});

	test('a control names the destination, not the state', async ({ page }) => {
		await page.goto('/master/main');
		await viewMenu(page);
		await expect(page.getByTestId('toggle-annotations')).toHaveText(/^show all annotations/);
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
		// a wheel over the node's pane: its pane now draws the toolbar, and it acts on the node
		await pane(page, 1).hover();
		await page.mouse.wheel(0, 200);
		await expect(controls(page, 1)).toHaveAttribute('aria-label', 'controls for Theorem 2.1');
		await expect(controls(page, 0)).toHaveCount(0);
		await viewMenu(page);
		await expect(pane(page, 1).getByTestId('open-context')).toBeVisible();
		// and a wheel over the document: on the document
		await pane(page, 0).hover();
		await page.mouse.wheel(0, 200);
		await expect(page.getByTestId('open-context')).toHaveCount(0);
		await expect(controls(page, 0)).toHaveAttribute('aria-label', 'controls for main.tex');
		await expect(controls(page, 1)).toHaveCount(0);
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

	/** Open a node from the panel, in the focused pane. */
	async function open(page: Page, id: string): Promise<void> {
		await page.getByTestId('nodes-list').locator('li a', { hasText: id }).first().click();
	}

	test("each pane's strip ends in its own item's views", async ({ page }) => {
		await withPapers(page);
		// a document beside a paper: the paper's pane carries Paper · Digest · Info though the document's pane is focused, and the document's carries none
		await page.goto('/master/main' + beside('/library/Kre99'));
		await expect(pane(page, 0)).toHaveClass(/focused/);
		await expect(pane(page, 0).getByRole('group', { name: /^views of / })).toHaveCount(0);
		const views = pane(page, 1).getByRole('group', { name: 'views of Kre99' });
		await expect(views.getByRole('button')).toHaveText(['Paper', 'Digest', 'Info']);
		const head = (await page.getByTestId('pane-head-1').boundingBox())!;
		const box = (await views.boundingBox())!;
		expect(Math.abs(head.x + head.width - (box.x + box.width)), 'the views end at the strip\'s right edge, px').toBeLessThanOrEqual(1);
		// the current view is underlined in the accent, the others are links
		const paper = pane(page, 1).getByTestId('tab-paper');
		await expect(paper).toHaveAttribute('aria-pressed', 'true');
		expect(await paper.evaluate((b) => getComputedStyle(b).boxShadow)).toContain('inset');
		await expect(pane(page, 1).getByTestId('tab-digest')).toHaveCSS('box-shadow', 'none');
		// a click switches the view in its own pane, which takes focus, and the address follows
		await pane(page, 1).getByTestId('tab-digest').click();
		await expect(pane(page, 1).getByTestId('tab-digest')).toHaveAttribute('aria-pressed', 'true');
		await expect(pane(page, 1)).toHaveClass(/focused/);
		await expect.poll(() => new URL(page.url()).searchParams.get('beside')).toContain('view=digest');

		// two papers: each strip its own item's views, switched apart
		await page.goto('/library/Kre99' + beside('/library/Har77'));
		await expect(pane(page, 0).getByRole('group', { name: 'views of Kre99' })).toBeVisible();
		await expect(pane(page, 1).getByRole('group', { name: 'views of Har77' })).toBeVisible();
		await pane(page, 1).getByTestId('tab-info').click();
		await expect(pane(page, 1).getByTestId('tab-info')).toHaveAttribute('aria-pressed', 'true');
		await expect(pane(page, 0).getByTestId('tab-paper')).toHaveAttribute('aria-pressed', 'true');

		// a session beside a document: Chat · What it did, in the unfocused pane
		await page.goto('/master/main' + beside('/session/s-2026-09-16-0001'));
		await expect(pane(page, 0)).toHaveClass(/focused/);
		await expect(pane(page, 1).getByRole('group', { name: /^views of / }).getByRole('button')).toHaveText(['Chat', 'What it did']);
		await expect(pane(page, 1).getByTestId('tab-chat')).toHaveAttribute('aria-pressed', 'true');
	});

	test('tabs are 148px, narrow evenly, then scroll with the active tab in view', async ({ page }) => {
		// the right pane is two fifths of the workspace, about 450px, so ten tabs pass the floor
		await prefs(page, { divider: 0.6 });
		await page.setViewportSize({ width: 1440, height: 900 });
		await page.goto('/node/sy-0001' + beside('/node/sy-0002'));
		await tabs(page, 1).first().getByRole('tab').click();
		await expect(pane(page, 1)).toHaveClass(/focused/);
		await page.getByTestId('nodes-toggle').click();
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

	test('past the floor the views keep their place', async ({ page }) => {
		await withPapers(page);
		await prefs(page, { divider: 0.6 });
		await page.setViewportSize({ width: 1440, height: 900 });
		await page.goto('/node/sy-0001' + beside('/library/Kre99'));
		await tabs(page, 1).first().getByRole('tab').click();
		await page.getByTestId('nodes-toggle').click();
		for (const id of ['sy-0003', 'sy-0006', 'sy-0007', 'sy-0008', 'sy-0009', 'sy-000A', 'sy-000B', 'sy-000C']) {
			await page.getByTestId('nodes-list').locator('li a', { hasText: id }).first().click();
		}
		await tabs(page, 1).first().getByRole('tab').click();
		const views = pane(page, 1).getByRole('group', { name: 'views of Kre99' });
		await expect(views).toBeVisible();
		const row = (await pane(page, 1).getByRole('tablist').boundingBox())!;
		const box = (await views.boundingBox())!;
		const head = (await page.getByTestId('pane-head-1').boundingBox())!;
		expect(row.x + row.width, 'the tabs end before the views begin').toBeLessThanOrEqual(box.x + 0.5);
		expect(Math.abs(head.x + head.width - (box.x + box.width))).toBeLessThanOrEqual(1);
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
	test('the panel goes first, and the rail keeps its parts apart', async ({ page }) => {
		await serve(page, (m) => (m.references.Kre99.artifacts.pdf = true));
		await page.setViewportSize({ width: 1100, height: 800 });
		await page.goto('/library/Kre99');
		await expect(page.locator('.panel.away')).toHaveCount(1);
		const parts = page.getByTestId('reading-rail').locator('> *');
		await expect(parts).toHaveCount(2);
		const boxes = await parts.evaluateAll((els) =>
			els.map((e) => {
				const r = (e.firstElementChild ?? e).getBoundingClientRect();
				return { name: (e as HTMLElement).dataset.testid ?? e.className, left: r.left, right: r.right };
			})
		);
		for (let i = 1; i < boxes.length; i++) expect(boxes[i].left, `${boxes[i].name} starts before ${boxes[i - 1].name} ends`).toBeGreaterThanOrEqual(boxes[i - 1].right - 1);
		// the reader's stored choice is not rewritten by the window's width
		expect(await page.evaluate(() => JSON.parse(localStorage.getItem('arras.prefs') ?? '{}').panel)).not.toBe(false);
	});

	test('the rail keeps both its parts, and the strip its views, with nothing behind a ⋯', async ({ page }) => {
		await serve(page, (m) => (m.references.Kre99.artifacts.pdf = true));
		await page.setViewportSize({ width: 760, height: 800 });
		await page.goto('/library/Kre99');
		await expect(page.getByTestId('reading-rail').getByTestId('show-current')).toBeVisible();
		await expect(page.getByTestId('rail-compare')).toBeVisible();
		await expect(page.getByTestId('rail-more-toggle')).toHaveCount(0);
		// the views end the strip, and the controls stay on the pane
		const head = (await page.getByTestId('pane-head-0').boundingBox())!;
		const views = (await pane(page, 0).getByRole('group', { name: 'views of Kre99' }).boundingBox())!;
		expect(Math.abs(head.x + head.width - (views.x + views.width)), 'the views end at the strip\'s right edge, px').toBeLessThanOrEqual(1);
		await expect(page.getByTestId('zoom-at')).toBeVisible();
	});
});

test.describe('the toolbar', () => {
	/** The toolbar's opacity as drawn now. */
	const opacity = (page: Page) => page.getByTestId('item-controls').evaluate((t) => Number(getComputedStyle(t).opacity));

	/** A point in the band across the top of pane 0's body, beside the bar, and one well below it. */
	async function points(page: Page) {
		const body = (await pane(page, 0).locator('> .body').boundingBox())!;
		const bar = (await page.getByTestId('item-controls').boundingBox())!;
		return { band: { x: bar.x - 40, y: body.y + 40 }, away: { x: body.x + body.width / 2, y: body.y + body.height - 60 }, bar };
	}

	test('it stands at the focused pane\'s top right, over the page and not in it, one line on the sheet with a shadow', async ({ page }) => {
		await page.setViewportSize({ width: 1440, height: 900 });
		await page.goto('/master/main' + beside('/node/sy-0003'));
		const bar = controls(page, 0);
		await expect(bar).toBeVisible();
		expect(await bar.evaluate((b) => b.closest('.body'))).toBeNull();
		const at = (await bar.boundingBox())!;
		const body = (await pane(page, 0).locator('> .body').boundingBox())!;
		expect(at.height, 'one line, px').toBeLessThan(34);
		expect(body.x + body.width - (at.x + at.width), 'from the pane\'s right, px').toBeLessThan(24);
		expect(at.y - body.y, 'below the head, px').toBeLessThan(16);
		expect(await bar.evaluate((b) => getComputedStyle(b).boxShadow)).not.toBe('none');
		// the pane's text does not move for it: it is on the pane's layer, not in the flow
		expect(await bar.evaluate((b) => getComputedStyle(b).position)).toBe('absolute');
	});

	test('the bar, then view with every other control in full words and its key, then the pin; the divider only when something stands left of view', async ({ page }) => {
		await writes(page);
		await page.goto('/master/main');
		const bar = controls(page, 0);
		await expect(bar.getByTestId('tool-select')).toBeVisible();
		const order = await bar.locator('button').evaluateAll((els) => els.map((e) => (e as HTMLElement).dataset.testid));
		expect(order).toEqual(['tool-select', 'tool-box', 'toolbar-view', 'toolbar-pin']);
		await expect(page.getByTestId('toolbar-view')).toHaveCSS('border-left-style', 'solid');
		await expect(page.getByTestId('toolbar-view')).toHaveAttribute('aria-label', 'view menu for main.tex');
		await viewMenu(page);
		const menu = page.getByTestId('toolbar-menu');
		await expect(menu).toHaveAttribute('role', 'menu');
		await expect(menu.getByRole('menuitemcheckbox')).toHaveText(['show all annotationse', 'show settled annotationss']);
		await expect(menu.getByTestId('toggle-settled')).toHaveAttribute('aria-keyshortcuts', 's');
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

		// nothing serving: view stands first, with no divider before it
		await page.unrouteAll();
		await page.goto('/master/main');
		await expect(page.getByTestId('toolbar-view')).toBeVisible();
		expect(await controls(page, 0).locator('button').evaluateAll((els) => els.map((e) => (e as HTMLElement).dataset.testid))).toEqual(['toolbar-view', 'toolbar-pin']);
		await expect(page.getByTestId('toolbar-view')).toHaveCSS('border-left-style', 'none');
	});

	test('a node keeps its context and its source under view', async ({ page }) => {
		await page.goto('/node/sy-0003');
		await viewMenu(page);
		await expect(page.getByTestId('toolbar-menu').locator('[role^="menuitem"]')).toHaveText(['show all annotationse', 'show settled annotationss', 'open its context beside', 'show verbatim code']);
		await page.getByTestId('open-context').click();
		await expect(pane(page, 1).getByTestId('context')).toBeVisible();
	});

	test('a paper shows settled annotations from its toolbar, and greys its page tools and its PDF off the Paper view', async ({ page }) => {
		await withPapers(page);
		await page.goto('/library/Kre99');
		await expect(page.getByTestId('pdf-doc')).toBeVisible();
		await viewMenu(page);
		await expect(page.getByTestId('toolbar-menu').locator('[role^="menuitem"]')).toHaveText(['show settled annotations', 'open the PDF']);
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

	test('a paper with no readable copy greys its Paper view and opens on the first view that can be read', async ({ page }) => {
		await page.goto('/library/Kre99');
		const paper = pane(page, 0).getByTestId('tab-paper');
		await expect(paper).toBeDisabled();
		await expect(paper).toHaveAttribute('title', 'No copy of this work is on file');
		await expect(pane(page, 0).getByTestId('tab-digest')).toHaveAttribute('aria-pressed', 'true');
		await expect.poll(() => new URL(page.url()).search).toBe('');
		await expect(page.getByTestId('tool-select')).toBeDisabled();
		await viewMenu(page);
		await expect(page.getByTestId('open-pdf')).toHaveAttribute('title', 'No copy of this work is on file');
	});

	test('a landmark, a context and a session draw no toolbar', async ({ page }) => {
		for (const at of ['/canon/widgets-v1', '/context/sy-0003', '/session/s-2026-09-16-0001']) {
			await page.goto(at);
			await expect(pane(page, 0).getByTestId('item-tab')).toHaveCount(1);
			await expect(controls(page, 0)).toHaveCount(0);
		}
	});

	test('unpinned, the band wakes it and leaving fades it; the pointer on it and its open menu hold it', async ({ page }) => {
		await prefs(page, { controls: 'fade' });
		await page.setViewportSize({ width: 1440, height: 900 });
		await page.goto('/master/main');
		await expect(controls(page, 0)).toBeVisible();
		const { band, away, bar } = await points(page);
		await page.mouse.move(away.x, away.y);
		await expect.poll(() => opacity(page)).toBe(0);
		await expect(controls(page, 0)).toHaveCSS('pointer-events', 'none');
		// into the band, left of the bar: it wakes
		await page.mouse.move(band.x, band.y, { steps: 4 });
		await expect.poll(() => opacity(page)).toBe(1);
		await expect(controls(page, 0)).toHaveCSS('transition-duration', '0.4s');
		// the band is 96px tall: just below it, it fades
		await page.mouse.move(band.x, (await pane(page, 0).locator('> .body').boundingBox())!.y + 110, { steps: 4 });
		await expect.poll(() => opacity(page), { timeout: 2000 }).toBe(0);
		// on the bar it stays, and so it does with the menu open, wherever the pointer then goes
		await page.mouse.move(bar.x + bar.width / 2, bar.y + bar.height / 2, { steps: 4 });
		await expect.poll(() => opacity(page)).toBe(1);
		await page.getByTestId('toolbar-view').click();
		await page.mouse.move(away.x, away.y, { steps: 4 });
		await page.waitForTimeout(700);
		expect(await opacity(page)).toBe(1);
		// a choice closes the menu, and then the pointer leaving lets it fade
		await page.getByTestId('toggle-settled').click();
		await page.mouse.move(away.x, away.y, { steps: 4 });
		await expect.poll(() => opacity(page), { timeout: 2000 }).toBe(0);
		// nothing draws the band
		await expect(pane(page, 0).locator('[data-testid*="band"]')).toHaveCount(0);
	});

	test('the pin holds it, pinned by default, and the choice survives a reload', async ({ page }) => {
		await page.goto('/master/main');
		const pin = page.getByTestId('toolbar-pin');
		await expect(pin).toHaveAttribute('aria-pressed', 'true');
		await expect(pin).toHaveAttribute('aria-label', 'fade');
		const { away } = await points(page);
		await page.mouse.move(away.x, away.y);
		await page.waitForTimeout(700);
		expect(await opacity(page)).toBe(1);
		// the tooltip names what a click does, on hover and on keyboard focus
		await pin.hover();
		const tip = page.getByTestId('toolbar-pin-tip');
		await expect(tip).toHaveText('Fade: let these controls fade when the pointer leaves the top of the pane.');
		await expect.poll(() => tip.evaluate((t) => Number(getComputedStyle(t).opacity))).toBe(1);
		await expect(pin).toHaveAccessibleDescription('Fade: let these controls fade when the pointer leaves the top of the pane.');
		await pin.click();
		await expect(pin).toHaveAttribute('aria-pressed', 'false');
		await expect(pin).toHaveAttribute('aria-label', "don't fade");
		await expect(tip).toHaveText("Don't fade: keep these controls showing until you click again.");
		expect(await page.evaluate(() => JSON.parse(localStorage.getItem('arras.prefs') ?? '{}').controls)).toBe('fade');
		await page.mouse.move(away.x, away.y, { steps: 4 });
		await expect.poll(() => opacity(page), { timeout: 2000 }).toBe(0);
		await page.reload();
		await expect(page.getByTestId('toolbar-pin')).toHaveAttribute('aria-pressed', 'false');
		await page.mouse.move(away.x, away.y - 10, { steps: 2 });
		await expect.poll(() => opacity(page), { timeout: 2000 }).toBe(0);
		// and one choice for every toolbar: the node's is unpinned too
		await page.goto('/node/sy-0003');
		await expect(page.getByTestId('toolbar-pin')).toHaveAttribute('aria-pressed', 'false');
	});

	test('keyboard focus in the pane shows it', async ({ page }) => {
		await prefs(page, { controls: 'fade' });
		await page.goto('/master/main');
		const { away } = await points(page);
		await page.mouse.move(away.x, away.y);
		await expect.poll(() => opacity(page), { timeout: 2000 }).toBe(0);
		// from the tab, the next stop is in the toolbar, which the key brings back
		await pane(page, 0).getByRole('tab').first().focus();
		await page.keyboard.press('Tab');
		await expect(page.getByTestId('toolbar-view')).toBeFocused();
		await expect.poll(() => opacity(page)).toBe(1);
		// the pin's tooltip shows on keyboard focus as on hover
		await page.keyboard.press('Tab');
		await expect(page.getByTestId('toolbar-pin')).toBeFocused();
		await expect.poll(() => page.getByTestId('toolbar-pin-tip').evaluate((t) => Number(getComputedStyle(t).opacity))).toBe(1);
	});

	test('with reduced motion it fades at once', async ({ page }) => {
		await page.emulateMedia({ reducedMotion: 'reduce' });
		await prefs(page, { controls: 'fade' });
		await page.goto('/master/main');
		await expect(controls(page, 0)).toHaveCSS('transition-duration', '0s');
		const { band, away } = await points(page);
		await page.mouse.move(band.x, band.y, { steps: 2 });
		await expect.poll(() => opacity(page)).toBe(1);
		await page.mouse.move(away.x, away.y);
		await expect.poll(() => opacity(page), { timeout: 150, intervals: [20] }).toBe(0);
	});
});
