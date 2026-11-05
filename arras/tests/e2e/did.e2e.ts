// What it did: a session's command log read as its record. Recorded groups the annotations it made by the block they are on, named as a reader names it, each with its kind as a dot in the kind's hue and where it stands; Ran lists every other command once, with how many times and what it names; every line stays, in order, folded at the foot; and an annotation's row and its mark point at each other across the panes. Each test is named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { beside } from '../workspace';
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
	// a command that made an annotation is in Recorded, not Ran
	await expect(page.getByTestId('did-ran')).not.toContainText('loom annotate sy-0003');
});

test('what it recorded is grouped by the block it is on, named as a reader names it, each with its kind by hue and where it stands', async ({ page }) => {
	await page.goto(`/session/${REFEREE}?view=did`);
	const made = page.locator('[id="ann-a-2026-09-16-ecnav2"]');
	const group = page.getByTestId('did-group').filter({ has: made });
	await expect(group.getByTestId('did-on')).toHaveAttribute('title', 'sy-0003');
	await expect(group.getByTestId('did-on')).not.toHaveText('sy-0003');
	// the kind is a dot in the objection's red, the word kept for a screen reader only (annotation study A2, A4)
	const dot = made.getByTestId('did-kind');
	await expect(dot).toHaveClass(/k-objection/);
	await expect(dot).toHaveAttribute('aria-label', 'objection');
	await expect(dot).toHaveCSS('background-color', 'rgb(163, 45, 45)');
	await expect(made.getByTestId('did-state')).toHaveText('open');
	await expect(made.getByTestId('did-first')).toContainText('finite');
	// an annotation the log names twice, made and then resolved, is one row, where it stands now
	await expect(page.locator('[id="ann-a-2026-09-16-hwtkaw"]')).toHaveCount(1);
	await expect(page.locator('[id="ann-a-2026-09-16-hwtkaw"]').getByTestId('did-state')).toHaveText('resolved');
});

test('a row links the annotation it made by its quilt: address, which opens where every such link does', async ({ page }) => {
	// where the link opens, with its box, is the one rule's (links.e2e.ts); the row's part is to link the annotation
	await page.goto(`/session/${REFEREE}?view=did`);
	await expect(page.locator('[id="ann-a-2026-09-16-ecnav2"]').getByTestId('did-annotation')).toHaveAttribute('href', 'quilt:a-2026-09-16-ecnav2');
});

test('with an empty log it says so in one line, rather than a section over nothing', async ({ page }) => {
	await serve(page, (m) => (m.threads[QUICK].log = []));
	await page.goto(`/session/${QUICK}?view=did`);
	await expect(page.getByTestId('session-did')).toHaveText('Nothing done through loom in this session yet.');
	await expect(page.getByTestId('did-row')).toHaveCount(0);
});

test('a row opens its mark in the other pane, and the mark travels to its own box rather than back to the row', async ({ page }) => {
	// a finding in what the session did opens the document it is about at its mark in the other pane; the mark's double-click lands on the annotation's box, which carries its id, so the row is never where a mark sends the reader
	// the measure is how far the element sticks out of its pane, above or below; 0 or less is inside
	const outOfPane = (el: Element) => {
		const pane = el.closest('[data-pane] > .body') as HTMLElement;
		const a = el.getBoundingClientRect();
		const b = pane.getBoundingClientRect();
		return Math.max(b.top - a.top, a.bottom - b.bottom);
	};
	await page.goto('/master/drafting/main' + beside(`/session/${REFEREE}?view=did`));
	await expect(page.getByTestId('session-did')).toBeVisible();
	await page.waitForSelector('[data-pane="0"] .fragment [data-annotation]');
	// the first row that made an annotation with a mark in the text: one about the document as a whole has none
	const id = await page.evaluate(() => {
		for (const li of document.querySelectorAll('[data-testid="session-did"] li[id^="ann-"]')) {
			const id = li.id.replace(/^ann-/, '');
			if (document.querySelector(`[data-pane="0"] [data-annotation~="${id}"]`)) return id;
		}
		return '';
	});
	expect(id).not.toBe('');
	const row = page.locator(`[data-pane="1"] [id="ann-${id}"]`);
	const mark = page.locator(`[data-pane="0"] [data-annotation~="${id}"]`).first();

	await page.locator('[data-pane="0"] > .body').evaluate((el) => (el.scrollTop = el.scrollHeight));
	await row.getByTestId('did-annotation').click();
	await expect.poll(() => mark.evaluate(outOfPane), { timeout: 5000 }).toBeLessThanOrEqual(2);

	await mark.dblclick();
	// the box it lands on flashes, so the eye is told where it landed; the row stays where it was
	const box = page.locator(`[data-pane="0"] article.box[data-annotation-id="${id}"]`);
	await expect(box).toHaveClass(/travelled/);
	await expect(row).not.toHaveClass(/travelled/);
});
