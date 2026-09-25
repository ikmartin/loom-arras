// What a screenshot waits for before it is taken, shared by the shot suites: the page drawn, every formula typeset, and nothing on it still moving. Where the images land can be moved with `ARRAS_SHOTS_OUT`, so a run that only checks the suites leaves the committed images alone.

import { expect, type Page } from '@playwright/test';

/** The directory a suite writes into: `ARRAS_SHOTS_OUT` when set, else the suite's own committed place. */
export function outDir(committed: string): string {
	return process.env.ARRAS_SHOTS_OUT ?? committed;
}

/** The boxes of what can still move after a page has loaded: the graph's nodes as its layout settles, the fragments as formulas grow, the pages of a paper as they are drawn. */
function layout(): string {
	return [...document.querySelectorAll('svg g.node, svg circle, .fragment, [data-testid="pdf-doc"] canvas, [data-pane] > .body')]
		.map((e) => {
			const r = e.getBoundingClientRect();
			return [r.x, r.y, r.width, r.height].map(Math.round).join(',');
		})
		.join(' ');
}

/** Wait until two reads of the layout a quarter-second apart agree; fails with the layout last read. */
export async function still(page: Page): Promise<void> {
	let last = '';
	await expect
		.poll(
			async () => {
				const now = await page.evaluate(layout);
				const held = now === last;
				last = now;
				return held ? 'held' : `moving: ${now.slice(0, 200)}`;
			},
			{ intervals: [250], timeout: 20000 }
		)
		.toBe('held');
}

/** Wait until the page is drawn, its fonts loaded, every formula typeset, and its layout still. */
export async function settle(page: Page): Promise<void> {
	// a page's title, or in reading mode a pane's content, since an item draws no chrome and a session no title
	await page.waitForSelector('main h1, [data-pane] > .body > *', { timeout: 15000 });
	await page.evaluate(() => document.fonts.ready.then(() => undefined));
	await page.waitForFunction(() => document.querySelectorAll('.math:not(:has(mjx-container))').length === 0);
	await still(page);
}
