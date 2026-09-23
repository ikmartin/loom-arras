// The session list lives in a picker opened from the side panel's footer (plan 0.13.3 S7), so every suite that selects a session goes through it.

import type { Page } from '@playwright/test';

/** Open the picker from the footer, unless it is already open. */
export async function openPicker(page: Page): Promise<void> {
	const footer = page.getByTestId('session-footer');
	if ((await footer.getAttribute('aria-expanded')) !== 'true') await footer.click();
	await page.getByTestId('session-picker').waitFor();
}

/** Select a session by id; the picker closes behind the choice. */
export async function pickSession(page: Page, id: string): Promise<void> {
	await openPicker(page);
	await page.getByTestId(`session-${id}`).click();
}
