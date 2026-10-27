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

/** Open a pane's *view* menu, where a toolbar keeps every control but its bar's: the focused pane's by default; open already, it is left open. */
export async function viewMenu(page: Page, index?: number): Promise<void> {
	const at = index ?? (await page.locator('[data-pane].focused').count() ? Number(await page.locator('[data-pane].focused').getAttribute('data-pane')) : 0);
	const view = pane(page, at).getByTestId('toolbar-view');
	if ((await view.getAttribute('aria-expanded')) !== 'true') await view.click();
	await page.getByTestId('toolbar-menu').waitFor();
}

/** Open an item in the focused pane as a link outside the panes does (the column's, the palette's): the column lists no results, so the link is made for the test and clicked. */
export async function openHere(page: Page, href: string): Promise<void> {
	await page.evaluate((h) => {
		const a = document.createElement('a');
		a.href = h;
		document.querySelector('[data-testid="column"]')!.appendChild(a);
		a.click();
		a.remove();
	}, href);
}
