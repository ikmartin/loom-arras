// `/`: reading where it was left — this visit's workspace, else the address remembered from an earlier visit, else the default draft, else the newest landmark — and, in a quilt with nothing to read, how to start. Each test is named for the rule it holds.
import { expect, test } from '@playwright/test';
import { beside, pane } from '../workspace';
import { manifest, serve } from '../manifest';

test('a first visit opens the default draft', async ({ page }) => {
	await page.goto('/');
	await expect(page).toHaveURL(/\/master\/main$/);
	await expect(pane(page, 0).locator('.fragment').first()).toBeVisible();
});

test('a reload, or a visit another day, reopens both panes as they were left', async ({ page }) => {
	await page.goto('/master/main' + beside('/node/sy-0003'));
	await expect(pane(page, 1).locator('.fragment').first()).toBeVisible();
	await page.goto('/');
	await expect(page).toHaveURL(/\/master\/main\?beside=%2Fnode%2Fsy-0003/);
	await expect(pane(page, 1).getByTestId('item-tab')).toContainText('Theorem 2.1');
	// what is remembered is the corpus's own, in this browser
	const kept = await page.evaluate(() => JSON.parse(localStorage.getItem('arras.workspace') ?? '{}'));
	expect(Object.keys(kept)).toEqual([manifest.corpus.name]);
});

test('a remembered document no longer in the corpus gives way to the default draft', async ({ page }) => {
	await page.addInitScript((name) => localStorage.setItem('arras.workspace', JSON.stringify({ [name]: '/master/gone' })), manifest.corpus.name);
	await page.goto('/');
	await expect(page).toHaveURL(/\/master\/main$/);
});

test('a quilt with nothing to read opens on how to start: the publisher\'s advice, one step a fix', async ({ page }) => {
	await serve(page, (m) => {
		m.masters = [];
		m.canon = [];
		m.diagnostics = [
			{
				severity: 'info',
				code: 'loom:no-live-document',
				message: 'nothing is being worked on: drafting/ holds no document; write one there with \\documentclass, or begin from a paper',
				locations: [],
				keys: [],
				fixes: [
					{ label: 'bring in a paper you are writing', command: 'loom import FILE' },
					{ label: 'file a paper you are reading', command: 'loom library add FILE' }
				]
			}
		] as typeof m.diagnostics;
	});
	await page.goto('/');
	const start = page.getByTestId('how-to-start');
	await expect(start.getByRole('heading', { level: 1 })).toHaveText('Nothing to read yet');
	await expect(start).toContainText('write one there with \\documentclass');
	await expect(start.getByTestId('start-step')).toHaveCount(2);
	await expect(start.getByTestId('start-step').locator('code')).toHaveText(['loom import FILE', 'loom library add FILE']);
	await expect(page).toHaveURL(/\/$/);
	// and Docs, with nothing to return to, comes back here
	await expect(page.getByTestId('primary-docs')).toHaveAttribute('href', '/');
});
