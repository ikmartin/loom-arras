// What it did: a session's command log read as its record. Ran lists every command once, with how many times and what it names, and every line stays, in order, folded at the foot. Annotations belong to no session, so none is listed. Each test is named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { manifest, QUICK, REFEREE, serve } from '../manifest';

/** The referee's log, padded with `extra` plain commands before it, nine distinct ones repeated. */
async function longLog(page: Page, extra: number) {
	await serve(page, (m) => {
		const pad = Array.from({ length: extra }, (_, i) => ({ time: '2026-09-15T09:00:00Z', command: `loom source sy-000${i % 9} --closure`, names: [{ key: `sy-000${i % 9}` }] }));
		m.threads[REFEREE].log = [...pad, ...m.threads[REFEREE].log];
	});
}

test('every line of the log stays, in order, folded at the foot', async ({ page }) => {
	await longLog(page, 60);
	await page.goto(`/session/${REFEREE}?view=did`);
	const every = page.getByTestId('did-every');
	await expect(every).not.toHaveAttribute('open', '');
	await every.locator('summary').click();
	const rows = page.getByTestId('did-row');
	await expect(rows).toHaveCount(60 + manifest.threads[REFEREE].log.length);
	await expect(rows.first()).toContainText('loom source sy-0000 --closure');
});

test('a command run again and again is one row, with how many times, and links what it names', async ({ page }) => {
	await longLog(page, 60);
	await page.goto(`/session/${REFEREE}?view=did`);
	const ran = page.getByTestId('did-ran').getByTestId('did-command').filter({ hasText: 'loom source sy-0000 --closure' });
	await expect(ran).toHaveCount(1);
	await expect(ran.getByTestId('did-times')).toContainText('×7 ·');
	await expect(ran.getByTestId('did-named')).toHaveAttribute('href', 'quilt:sy-0000');
	await expect(page.getByTestId('did-recorded')).toHaveCount(0);
});

test('with an empty log it says so in one line, rather than a section over nothing', async ({ page }) => {
	await serve(page, (m) => (m.threads[QUICK].log = []));
	await page.goto(`/session/${QUICK}?view=did`);
	await expect(page.getByTestId('session-did')).toHaveText('Nothing done through loom in this session yet.');
	await expect(page.getByTestId('did-row')).toHaveCount(0);
});
