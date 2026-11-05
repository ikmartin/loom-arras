// Keeping a page's polls from firing, so that what it learns it learned some other way: a test of "at once" holds back what it should not wait for and asserts what still arrives, rather than timing it.

import type { Page } from '@playwright/test';

/** From the page's first script on, no interval of a second or more fires, which is how the viewer polls. Call it before the page loads. */
export async function noPolls(page: Page): Promise<void> {
	await page.addInitScript(() => {
		const setInterval = window.setInterval;
		window.setInterval = ((run: TimerHandler, ms = 0, ...rest: unknown[]) => (ms >= 1000 ? 0 : setInterval(run, ms, ...rest))) as typeof window.setInterval;
	});
}
