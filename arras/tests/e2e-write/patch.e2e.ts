// A rebuild that changes an open document's markup patches it: the blocks that changed are put in and typeset, and the rest stay as they were drawn (plan 0.19.2). Replacing the whole document for one new mark typeset every formula in it again.
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import type { Page } from '@playwright/test';
import { expect, test } from '../served';

type Watched = { MathJax: { typesetPromise: (els: Element[]) => Promise<void> }; typeset: Element[][]; kept: Element; wrapped?: boolean };

const allTypeset = (page: Page) => page.waitForFunction(() => !!document.querySelector('[data-pane="0"] .fragment mjx-container') && document.querySelectorAll('.fragment .math:not(:has(mjx-container))').length === 0);

/** Remember `selector`'s element, and everything typeset from here on. */
async function watch(page: Page, selector: string): Promise<void> {
	await page.evaluate((selector) => {
		const w = window as unknown as Watched;
		w.kept = document.querySelector(selector)!;
		w.typeset = [];
		if (w.wrapped) return;
		w.wrapped = true;
		const real = w.MathJax.typesetPromise.bind(w.MathJax);
		w.MathJax.typesetPromise = (els) => {
			w.typeset.push(els);
			return real(els);
		};
	}, selector);
}

test('an annotation filed from the command line is drawn into the open document, which is not drawn again', async ({ page, served }) => {
	await page.goto('/master/main');
	await allTypeset(page);
	await watch(page, '[data-pane="0"] .fragment h1[data-src]');
	const id = served.loom(['annotate', 'sy-0002', 'Which orbits?', '--quote', 'one or two points']).split(/\s+/)[0];
	const filed = Date.now();
	const mark = page.locator(`[data-pane="0"] .fragment mark.annotation[data-annotation~="${id}"]`);
	await expect(mark).toHaveCount(1, { timeout: 15000 });
	// the watcher looks at loom's records five times a second and the publisher says when it has published, where two one-second polls stood in series; GitHub's runner rebuilds more slowly than a workstation (about 1.65 s there), so it is given more room
	const budget = process.env.GITHUB_ACTIONS ? 2500 : 1500;
	expect(Date.now() - filed, 'ms from the command returning to the mark being drawn').toBeLessThan(budget);
	await allTypeset(page);
	const r = await page.evaluate((id) => {
		const w = window as unknown as Watched;
		const block = document.querySelector(`[data-pane="0"] .fragment mark[data-annotation~="${id}"]`)!.closest('[data-src]')!;
		const elsewhere = w.typeset.flat().filter((e) => e.closest('.fragment') && !block.contains(e) && !e.closest('aside.comment-slot'));
		return { kept: w.kept.isConnected, elsewhere: elsewhere.length };
	}, id);
	expect(r.kept, 'a block the annotation does not touch is the same element').toBe(true);
	expect(r.elsewhere, 'formulas typeset outside the block the mark is in').toBe(0);
	await mark.click();
	await expect(page.getByTestId('comment-expanded').first()).toBeVisible();
});

test('an edit keeps the blocks after it in its file, and moves their offsets', async ({ page, served }) => {
	await page.goto('/master/main');
	await allTypeset(page);
	const blocks = page.locator('[data-pane="0"] .fragment [data-src^="nodes/sy-0002.tex:"]');
	const last = await blocks.last().getAttribute('data-src');
	await watch(page, `[data-pane="0"] .fragment [data-src="${last}"]`);
	const file = join(served.root, 'nodes', 'sy-0002.tex');
	writeFileSync(file, readFileSync(file, 'utf8').replace('one or two points', 'one or two points, never more'));
	await expect(page.locator('[data-pane="0"] .fragment').getByText('never more')).toBeVisible({ timeout: 15000 });
	const after = await page.evaluate(() => {
		const w = window as unknown as Watched;
		return { kept: w.kept.isConnected, src: w.kept.getAttribute('data-src') };
	});
	expect(after.kept, 'the last block of the edited file is the same element').toBe(true);
	const [, a] = last!.split(':');
	const [, b] = after.src!.split(':');
	expect(Number(b) - Number(a), 'its offset moved by what the edit added').toBe(', never more'.length);
});
