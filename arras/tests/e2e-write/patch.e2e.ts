// A rebuild that changes an open document's markup patches it: the blocks that changed are put in and typeset, and the rest stay as they were drawn (plan 0.19.2). Replacing the whole document for one new mark typeset every formula in it again.
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import type { Page } from '@playwright/test';
import { expect, test } from '../served';

type Watched = { MathJax: { typesetPromise: (els: Element[]) => Promise<void> }; typeset: Element[][]; kept: Element; wrapped?: boolean };
type Streams = { streams: EventSource[] };

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

/** From the page's first script on, no poll fires, the manifest's included, and each stream it opens is noted: what reaches the page after that came by the publisher's word. */
async function withoutPolling(page: Page): Promise<void> {
	await page.addInitScript(() => {
		const setInterval = window.setInterval;
		window.setInterval = ((run: TimerHandler, ms = 0, ...rest: unknown[]) => (ms >= 1000 ? 0 : setInterval(run, ms, ...rest))) as typeof window.setInterval;
		const streams: EventSource[] = ((window as unknown as Streams).streams = []);
		window.EventSource = class extends window.EventSource {
			constructor(url: string | URL, init?: EventSourceInit) {
				super(url, init);
				streams.push(this);
			}
		};
	});
}

// What keeps this fast is structure, tested without a clock: the watcher looks at loom's records between scans of the tree (`test_the_watcher_sees_loom_s_own_records_between_full_scans`) and the publisher says when it has published, which is all that can bring the mark here, where two one-second polls once stood in series. How long it takes is `scripts/bench`'s to say.
test('an annotation filed from the command line is drawn into the open document, which is not drawn again', async ({ page, served }) => {
	await withoutPolling(page);
	await page.goto('/master/drafting/main');
	await allTypeset(page);
	// a publication before the stream opens is one only the poll would have told of
	await page.waitForFunction(() => (window as unknown as Streams).streams.some((s) => s.readyState === EventSource.OPEN));
	await watch(page, '[data-pane="0"] .fragment h1[data-src]');
	const id = served.loom(['annotate', 'sy-0002', 'Which orbits?', '--quote', 'one or two points']).split(/\s+/)[0];
	const mark = page.locator(`[data-pane="0"] .fragment mark.annotation[data-annotation~="${id}"]`);
	await expect(mark).toHaveCount(1);
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
	await page.goto('/master/drafting/main');
	await allTypeset(page);
	const blocks = page.locator('[data-pane="0"] .fragment [data-src^="drafting/nodes/sy-0002.tex:"]');
	const last = await blocks.last().getAttribute('data-src');
	await watch(page, `[data-pane="0"] .fragment [data-src="${last}"]`);
	const file = join(served.root, 'drafting', 'nodes', 'sy-0002.tex');
	writeFileSync(file, readFileSync(file, 'utf8').replace('one or two points', 'one or two points, never more'));
	await expect(page.locator('[data-pane="0"] .fragment').getByText('never more')).toBeVisible();
	const after = await page.evaluate(() => {
		const w = window as unknown as Watched;
		return { kept: w.kept.isConnected, src: w.kept.getAttribute('data-src') };
	});
	expect(after.kept, 'the last block of the edited file is the same element').toBe(true);
	const [, a] = last!.split(':');
	const [, b] = after.src!.split(':');
	expect(Number(b) - Number(a), 'its offset moved by what the edit added').toBe(', never more'.length);
});
