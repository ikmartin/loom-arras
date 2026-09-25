// What it did: a session's `run.log`, in order, opening on the newest action; a row that made or changed an annotation links it, names what it is on by the key it was filed under, says its kind by a dot in the kind's hue and where it stands in a word; and the row and the annotation's mark point at each other across the panes. Each test is named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { beside } from '../workspace';
import { manifest, QUICK, REFEREE, serve } from '../manifest';

/** The referee's log, padded with `extra` plain commands before it, so the view has something to scroll. */
async function longLog(page: Page, extra: number) {
	await serve(page, (m) => {
		const pad = Array.from({ length: extra }, (_, i) => ({ time: '2026-09-15T09:00:00Z', command: `loom source sy-000${i % 9} --closure` }));
		m.threads[REFEREE].log = [...pad, ...m.threads[REFEREE].log];
	});
}

test('the rows are the log, in order, and the view opens on the newest', async ({ page }) => {
	await longLog(page, 60);
	await page.goto(`/session/${REFEREE}?view=did`);
	const rows = page.getByTestId('did-row');
	await expect(rows).toHaveCount(60 + manifest.threads[REFEREE].log.length);
	await expect(rows.last()).toBeInViewport();
	await expect(rows.first()).not.toBeInViewport();
	await expect(rows.first()).toContainText('loom source sy-0000 --closure');
});

test('a row names what its annotation is on by its key, never as a reader numbers it, says its kind by hue and where it stands', async ({ page }) => {
	await page.goto(`/session/${REFEREE}?view=did`);
	const made = page.locator('[id="ann-a-2026-09-16-0001"]');
	// the kind is a dot in the objection's red, the word kept for a screen reader only (annotation study A2, A4)
	await expect(made.getByTestId('did-annotation')).toHaveText('sy-0003');
	await expect(made.locator('.made')).not.toContainText('objection');
	await expect(made).not.toContainText('Theorem');
	const dot = made.getByTestId('did-kind');
	await expect(dot).toHaveClass(/k-objection/);
	await expect(dot).toHaveAttribute('aria-label', 'objection');
	await expect(dot).toHaveCSS('background-color', 'rgb(163, 45, 45)');
	await expect(made.getByTestId('did-state')).toHaveText('open');
	// a reply's dot is a ring in its thread's hue
	const reply = page.locator('[id="ann-a-2026-09-16-0008"]').getByTestId('did-kind');
	await expect(reply).toHaveClass(/reply/);
	await expect(reply).toHaveAttribute('aria-label', 'reply, question');
	// a later row about the same annotation links it too, but only the first carries its anchor
	const resolved = page.getByTestId('did-row').filter({ hasText: '--resolve a-2026-09-16-0002' });
	await expect(resolved.getByTestId('did-state')).toHaveText('resolved');
	await expect(resolved).not.toHaveAttribute('id', /.+/);
});

test('a row links the annotation it made by its quilt: address, which opens where every such link does', async ({ page }) => {
	// where the link opens, with its box, is the one rule's (links.e2e.ts); the row's part is to link the annotation
	await page.goto(`/session/${REFEREE}?view=did`);
	await expect(page.locator('[id="ann-a-2026-09-16-0001"]').getByTestId('did-annotation')).toHaveAttribute('href', 'quilt:a-2026-09-16-0001');
});

test('with an empty log it says so in one line, rather than a section over nothing', async ({ page }) => {
	await serve(page, (m) => (m.threads[QUICK].log = []));
	await page.goto(`/session/${QUICK}?view=did`);
	await expect(page.getByTestId('session-did')).toHaveText('Nothing done through loom in this session yet.');
	await expect(page.getByTestId('did-row')).toHaveCount(0);
});

test('a row opens its mark in the other pane, and the mark travels to its own box rather than back to the row', async ({ page }) => {
	// a finding in what the session did opens the document it is about at its mark in the other pane; the mark's double-click lands on the annotation's box, which carries its id (15.3.1), so the row is never where a mark sends the reader
	// the measure is how far the element sticks out of its pane, above or below; 0 or less is inside
	const outOfPane = (el: Element) => {
		const pane = el.closest('[data-pane] > .body') as HTMLElement;
		const a = el.getBoundingClientRect();
		const b = pane.getBoundingClientRect();
		return Math.max(b.top - a.top, a.bottom - b.bottom);
	};
	await page.goto('/master/main' + beside(`/session/${REFEREE}?view=did`));
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
