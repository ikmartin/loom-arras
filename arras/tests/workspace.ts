// Reading mode is items in two panes (plan 0.13.3): the path names the left pane's item, `?beside` the right's. Suites that set up an arrangement build it here, so its URL shape is written once.

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
