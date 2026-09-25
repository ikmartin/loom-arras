// Reading mode is items in two panes: the path names the left pane's item, `?beside` the right's. Suites that set up an arrangement build it here, so its URL shape is written once; the display preferences a test starts under are stored here too.

import type { Page } from '@playwright/test';

/** The query that puts `path`'s item in the right pane. */
export function beside(path: string): string {
	return '?beside=' + encodeURIComponent(path);
}

/** A pane, by index: 0 is the left one. */
export function pane(page: Page, index: number) {
	return page.getByTestId(`pane-${index}`);
}

/** Scroll a pane's body, which is what scrolls in reading mode; the window does not. */
export async function scrollPane(page: Page, index: number, to: 'top' | 'bottom'): Promise<void> {
	await pane(page, index)
		.locator('> .body')
		.evaluate((el, where) => el.scrollTo(0, where === 'top' ? 0 : el.scrollHeight), to);
}

/** Start the page under these display preferences, stored before any script of the app runs; what is not named takes its default. */
export async function prefs(page: Page, p: Record<string, unknown>): Promise<void> {
	await page.addInitScript((v) => localStorage.setItem('arras.prefs', JSON.stringify(v)), p);
}
