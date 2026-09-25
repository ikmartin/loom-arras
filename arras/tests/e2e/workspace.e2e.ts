// Reading mode as items in two panes: what a pane opens on, its tabs, the divider between the panes, focus, the arrangement the URL keeps, and what gives way in a narrow window. Grouped by the principle each rule serves, and each test named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { beside, pane, scrollPane } from '../workspace';
import { serve, servePapers } from '../manifest';

/** Serve the fixture with Kre99 and Har77 filed, so both are works with pages. */
async function withPapers(page: Page) {
	await serve(page, (m) => {
		m.references.Kre99.artifacts.pdf = true;
		m.references.Har77.artifacts.pdf = true;
	});
	await servePapers(page);
}

const tabs = (page: Page, index: number) => pane(page, index).getByTestId('item-tab');

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

	test('a pane head carries tabs and nothing else', async ({ page }) => {
		await page.goto('/master/main' + beside('/node/sy-0003'));
		for (const i of [0, 1]) {
			const head = page.getByTestId(`pane-head-${i}`);
			await expect(head).toBeVisible();
			const kinds = await head.evaluate((h) => [...h.children].map((c) => (c as HTMLElement).dataset.testid));
			expect(kinds).toEqual(kinds.map(() => 'item-tab'));
		}
	});

	test('no route draws a rail', async ({ page }) => {
		await withPapers(page);
		for (const at of [
			'/master/main' + beside('/node/sy-0003'),
			'/library/Kre99' + beside('/context/sy-0003'),
			'/canon/widgets-v1' + beside('/session/s-2026-09-16-0001')
		]) {
			await page.goto(at);
			await expect(pane(page, 1)).toBeVisible();
			for (const i of [0, 1]) {
				// the one rail and its cluster stand above the workspace, drawn once, never inside a pane
				await expect(pane(page, i).locator('[data-testid="reading-rail"], [data-testid="cluster"]')).toHaveCount(0);
			}
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
	test('the global rail holds two things', async ({ page }) => {
		await page.goto('/master/main');
		const rail = page.getByTestId('reading-rail');
		await expect(rail).toBeVisible();
		expect(await rail.evaluate((r) => r.children.length)).toBe(2);
		await expect(rail.getByRole('group', { name: 'which annotations the page shows' })).toBeVisible();
		await expect(page.getByTestId('cluster')).toBeVisible();
	});

	test('every control names its target', async ({ page }) => {
		for (const [at, name] of [
			['/master/main', 'main.tex'],
			['/node/sy-0003', 'Theorem']
		]) {
			await page.goto(at);
			const cluster = page.getByTestId('cluster');
			await expect(cluster.locator('button, a').first()).toBeVisible();
			const names = await cluster.locator('button, a').evaluateAll((els) => els.map((e) => e.getAttribute('aria-label') ?? ''));
			for (const n of names) expect(n, n).toContain(name);
		}
	});

	test('a control names the destination, not the state', async ({ page }) => {
		await page.goto('/master/main');
		await expect(page.getByTestId('toggle-annotations')).toHaveText('show all annotations');
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
		// a wheel over the node's pane: the rail now acts on the node
		await pane(page, 1).hover();
		await page.mouse.wheel(0, 200);
		await expect(page.getByTestId('open-context')).toBeVisible();
		// and a wheel over the document: on the document
		await pane(page, 0).hover();
		await page.mouse.wheel(0, 200);
		await expect(page.getByTestId('open-context')).toHaveCount(0);
		await expect(page.getByTestId('cluster')).toHaveAttribute('aria-label', 'controls for main.tex');
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

	test('when the parts cannot fit, the filter goes behind ⋯ and the cluster stays', async ({ page }) => {
		await serve(page, (m) => (m.references.Kre99.artifacts.pdf = true));
		await page.setViewportSize({ width: 760, height: 800 });
		await page.goto('/library/Kre99');
		await expect(page.getByTestId('rail-more-toggle')).toBeVisible();
		await expect(page.getByTestId('zoom-at')).toBeVisible();
		await expect(page.getByTestId('reading-rail').getByTestId('show-current')).toHaveCount(0);
		await page.getByTestId('rail-more-toggle').click();
		await expect(page.getByTestId('rail-more').getByTestId('show-current')).toBeVisible();
	});
});
