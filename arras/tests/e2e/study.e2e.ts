// Faults the 0.14 study found in the viewer (docs/reports/0.14-chat-overhaul.md), each held by a test named for the rule it restores.
import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { beside, pane } from '../workspace';

const manifest = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8'));
const REFEREE = 's-2026-09-16-0001';

async function withPaper(page: Page) {
	await page.route('**/build/manifest.json', async (route) => {
		const m = JSON.parse(JSON.stringify(manifest));
		m.references.Kre99.artifacts.pdf = true;
		await route.fulfill({ json: m });
	});
}

async function saying(page: Page, html: string) {
	await page.route(`**/build/transcripts/${REFEREE}/1.json`, (route) =>
		route.fulfill({ json: { session: REFEREE, page: 1, events: [{ seq: 1, kind: 'message', who: 'Referee Agent', when: '2026-09-16T10:00:00Z', body: '…', body_html: html }] } })
	);
}

test('F9: a link to a result of a cited work opens the paper at its page, as a citation of it does', async ({ page }) => {
	await withPaper(page);
	await saying(page, '<p>See <a href="quilt:Kre99-thm-2.1"></a>.</p>');
	await page.goto('/master/main' + beside('/session/' + REFEREE));
	const link = pane(page, 1).getByTestId('message-1').locator('a');
	await expect(link).toHaveText('Kre99 · Thm 2.1');
	await link.click();
	await expect.poll(() => new URL(page.url()).pathname).toBe('/library/Kre99');
	await expect.poll(() => new URL(page.url()).searchParams.get('page')).toBe('4');
});

test('a \\ref in a message reads as written, never as ???', async ({ page }) => {
	// the 0.14 study: an agent quoted "the saturation of Proposition~\\ref{sh-0007}", and the Chat showed `Proposition~???`
	await saying(page, '<p>by the saturation of Proposition~\\ref{sh-0007}, and <span class="math inline">\\(x\\)</span>.</p>');
	await page.goto('/master/main' + beside('/session/' + REFEREE));
	const said = pane(page, 1).getByTestId('message-1');
	await expect(said.locator('mjx-container')).toHaveCount(1); // the mathematics is still typeset
	await expect(said).toContainText('\\ref{sh-0007}');
	await expect(said).not.toContainText('???');
});

test('a Chat opens at its newest message after the mathematics in it is typeset', async ({ page }) => {
	// the principles check: landing scrolled to the bottom before typesetting grew the messages, and left the newest below the fold
	const display = '<span class="math display">\\[\\sum_{a:t(a)=v} w(a) - \\sum_{a:s(a)=v} w(a) = \\int_0^1 \\frac{x^2}{1+x^2}\\,dx\\]</span>';
	const events = Array.from({ length: 40 }, (_, i) => ({ seq: i + 1, kind: 'message', who: 'Referee Agent', when: '2026-09-16T10:00:00Z', body: 'x', body_html: `<p>message ${i + 1}</p><p>${display}</p><p>${display}</p>` }));
	await page.route(`**/build/transcripts/${REFEREE}/1.json`, (route) => route.fulfill({ json: { session: REFEREE, page: 1, events } }));
	await page.route('**/build/manifest.json', async (route) => {
		const m = JSON.parse(JSON.stringify(manifest));
		for (const s of m.sessions ?? []) if (s.id === REFEREE) s.seq = 40;
		await route.fulfill({ json: m });
	});
	await page.goto('/master/main' + beside('/session/' + REFEREE));
	await expect(pane(page, 1).locator('mjx-container').first()).toBeAttached();
	await page.waitForTimeout(1500);
	await expect(pane(page, 1).getByTestId('message-40')).toBeInViewport();
});

test('F4: with the box tool chosen, a drag that starts on a mark draws a box, and a click on it still opens the mark', async ({ page }) => {
	await page.route('**/_api', (r) => r.fulfill({ json: { write_api: 1, capabilities: ['comment'], token: 't' } }));
	await page.goto('/node/sy-0003');
	const mark = pane(page, 0).locator('.fragment mark.annotation').first();
	await expect(mark).toBeVisible();
	await page.getByTestId('tool-box').click();
	// a click without a drag is still a click on the mark
	await mark.click();
	await expect(pane(page, 0).getByTestId('comment-expanded')).toBeVisible();
	await page.keyboard.press('Escape');
	// a drag from it is a box
	const b = (await mark.boundingBox())!;
	await page.mouse.move(b.x + 4, b.y + b.height / 2);
	await page.mouse.down();
	await page.mouse.move(b.x + 120, b.y + b.height + 30, { steps: 8 });
	await page.mouse.up();
	await expect(page.getByTestId('note-at')).toBeVisible();
});

test('F13: where something keeps loom from starting the agent, the Chat says what', async ({ page }) => {
	const agent = { launch: true, name: 'Claude Agent', blocked: 'git tracks ai/ai-config.toml, so loom will not run it' };
	await page.route('**/_api', (r) => r.fulfill({ json: { write_api: 1, capabilities: ['message'], token: 't' } }));
	await page.route('**/_api/packet*', (r) => r.fulfill({ json: { session: REFEREE, rows: [], text: '' } }));
	await page.route('**/_api/events*', (r) => r.fulfill({ json: { session: REFEREE, from: 0, seq: 1, events: [], attached: [], agent } }));
	await page.goto('/session/' + REFEREE);
	await expect(page.getByTestId('chat-status')).toHaveText('Claude Agent cannot be started: git tracks ai/ai-config.toml, so loom will not run it');
});

test('F14: under a publisher the Chat opens on the newest page the publisher holds, not everything since the last build', async ({ page }) => {
	const asked: string[] = [];
	await page.route('**/_api', (r) => r.fulfill({ json: { write_api: 1, capabilities: ['message'], token: 't' } }));
	await page.route('**/_api/packet*', (r) => r.fulfill({ json: { session: REFEREE, rows: [], text: '' } }));
	await page.route('**/_api/events*', (r) => {
		const since = Number(new URL(r.request().url()).searchParams.get('since'));
		asked.push(String(since));
		r.fulfill({ json: { session: REFEREE, from: since, seq: 250, events: [], attached: [] } });
	});
	await page.route(`**/build/transcripts/${REFEREE}/*.json`, (route) => {
		const n = Number(route.request().url().match(/\/(\d+)\.json$/)![1]);
		const events = Array.from({ length: n === 3 ? 50 : 100 }, (_, i) => ({ seq: (n - 1) * 100 + i + 1, kind: 'message', who: 'Seed Agent', when: '2026-09-16T10:00:00Z', body: 'x', body_html: '<p>x</p>' }));
		route.fulfill({ json: { session: REFEREE, page: n, events } });
	});
	await page.goto('/session/' + REFEREE);
	await expect(page.getByTestId('message-250')).toBeInViewport();
	// a reader at the newest stays there when the log's own height changes (the principles check: a narrower window, or the tray opening, left the newest below the fold)
	await page.setViewportSize({ width: 1100, height: 600 });
	await expect(page.getByTestId('message-250')).toBeInViewport();
	await expect(page.getByTestId('message-200')).toHaveCount(0); // only the newest page, until asked
	// and not the page the stale manifest names beside it: the study found 1–100 then 201–250, with nothing between
	await page.waitForTimeout(500);
	await expect(page.getByTestId('message-100')).toHaveCount(0);
	// scrolling up fills in from the page before, so what is held is always one unbroken run
	await page.getByTestId('chat-log').evaluate((e) => (e.scrollTop = 0));
	await expect(page.getByTestId('message-200')).toHaveCount(1);
	const held = await page.locator('[data-testid^=message-]').evaluateAll((ms) => ms.map((m) => Number(m.getAttribute('data-testid')!.slice(8))));
	expect(held).toEqual(Array.from({ length: held.length }, (_, i) => held[0] + i));
	// every poll after landing asks from the last message held, never from nothing
	await expect.poll(() => asked.filter((s) => s === '250').length).toBeGreaterThan(0);
	expect(asked).not.toContain('0');
});
