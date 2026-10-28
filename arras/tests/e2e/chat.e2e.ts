// A session's transcript: what agents said into the session, read beside the documents (plan 0.20.1). It comes from the build's pages and, where a publisher serves, from a poll of `/_api/events`; the viewer posts nothing into it. Each test is named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { beside, pane } from '../workspace';
import { openPicker, pickSession } from '../picker';
import { QUICK, REFEREE, saying, serve } from '../manifest';

type Ev = { seq: number; kind: string; who: string; when: string; body?: string; body_html?: string };

function said(seq: number, who = seq % 2 ? 'A. Author' : 'Referee Agent'): Ev {
	return { seq, kind: 'message', who, when: '2026-09-16T10:00:00Z', body: `message ${seq}`, body_html: `<p>message ${seq}</p>` };
}

/** A transcript of `count` messages in the referee session, served as the build's pages, with the manifest's count to match; `html` draws a message's body. */
async function transcript(page: Page, count: number, html?: (seq: number) => string) {
	await serve(page, (m) => (m.sessions.find((s: { id: string }) => s.id === REFEREE).seq = count));
	await page.route(`**/build/transcripts/${REFEREE}/*.json`, async (route) => {
		const n = Number(route.request().url().match(/\/(\d+)\.json$/)![1]);
		const events: Ev[] = [];
		for (let s = (n - 1) * 100 + 1; s <= Math.min(n * 100, count); s++) events.push(html ? { ...said(s), body_html: html(s) } : said(s));
		await route.fulfill({ json: { session: REFEREE, page: n, events } });
	});
}

/** A publisher serving the write API, and with it the events poll: what an agent has said lands in `state` and arrives from the next poll. */
async function publisher(page: Page, state: { events: Ev[] }) {
	await page.route('**/_api', (r) => r.fulfill({ json: { write_api: 1, capabilities: ['annotate'], token: 't' } }));
	await page.route('**/_api/events*', (r) => {
		const since = Number(new URL(r.request().url()).searchParams.get('since') ?? 0);
		const events = state.events.filter((e) => e.seq > since);
		r.fulfill({ json: { session: REFEREE, from: since, seq: state.events.at(-1)?.seq ?? 0, events, attached: [] } });
	});
}

test.describe('the transcript', () => {
	test('the transcript opens on the newest message once the mathematics in it is typeset, with no heading of its own', async ({ page }) => {
		// typesetting grows the messages under the landing, so a transcript scrolled to the bottom before it would leave the newest below the fold
		const display = '<span class="math display">\\[\\sum_{a:t(a)=v} w(a) - \\sum_{a:s(a)=v} w(a) = \\int_0^1 \\frac{x^2}{1+x^2}\\,dx\\]</span>';
		await transcript(page, 40, (s) => `<p>message ${s}</p><p>${display}</p><p>${display}</p>`);
		await page.goto('/master/main' + beside('/session/' + REFEREE));
		const chat = pane(page, 1).getByTestId('chat');
		// The cold MathJax bundle and 80 display formulas share CI with three other suites.
		await expect(chat.locator('.math mjx-container')).toHaveCount(80, { timeout: 15000 });
		await expect(chat.getByTestId('message-40')).toBeInViewport();
		await expect(chat.getByTestId('message-1')).not.toBeInViewport();
		await expect(chat.locator('h1, h2')).toHaveCount(0);
	});

	test('scrolling to the top loads the page before, and the reader stays where they were', async ({ page }) => {
		await transcript(page, 150);
		await page.goto('/session/' + REFEREE);
		const chat = page.getByTestId('chat');
		await expect(chat.getByTestId('message-150')).toBeInViewport();
		await expect(chat.getByTestId('message-100')).toHaveCount(0); // only the last page, until asked
		// one scroll to the top, as a reader makes it: scrolling to the first message held already reaches it, and a second scroll to 0 after the page came in would undo the place kept
		await chat.locator('.log').evaluate((el) => (el.scrollTop = 0));
		await expect(chat.getByTestId('message-100')).toHaveCount(1);
		// the earlier page went in above, and the message that was at the top is still in view
		await expect(chat.getByTestId('message-101')).toBeInViewport();
	});

	test('a long report folds after its first block, and its mathematics is typeset only once it is opened', async ({ page }) => {
		const finding = (name: string) => `<section data-block="${name}"><h2>${name}</h2><p>${'A finding about the step. '.repeat(30)}<span class="math inline">\\(x^2\\)</span></p></section>`;
		await saying(page, '<p>Mode: referee, on sy-0003.</p><section data-block="summary"><h2>summary</h2><p>One objection.</p></section>' + finding('referee-review') + finding('decision'));
		await page.goto('/session/' + REFEREE);
		const report = page.getByTestId('message-1');
		await expect(report).toContainText('One objection.');
		const fold = report.getByTestId('message-fold');
		await expect(fold).toHaveText('▸ 2 more: referee-review, decision');
		await expect(fold).toHaveAttribute('aria-expanded', 'false');
		await expect(report.getByTestId('message-folded')).toHaveCount(0);
		await expect(report.locator('mjx-container')).toHaveCount(0);
		await fold.click();
		await expect(fold).toHaveAttribute('aria-expanded', 'true');
		await expect(report.getByTestId('message-folded')).toContainText('A finding about the step.');
		await expect(report.locator('mjx-container')).toHaveCount(2);
		await expect(fold).toBeInViewport(); // opening leaves the reader where they were
		await fold.click();
		await expect(report.getByTestId('message-folded')).toHaveCount(0);
	});

	test('a message with one block, or a short tail, is shown whole', async ({ page }) => {
		await saying(page, '<section data-block="summary"><h2>summary</h2><p>Done.</p></section><section data-block="decision"><h2>decision</h2><p>Minor revision.</p></section>');
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('message-1')).toContainText('Minor revision.');
		await expect(page.getByTestId('message-fold')).toHaveCount(0);
	});

	test("the fixture's referee report lands folded after its summary, its headings without their brackets", async ({ page }) => {
		await page.goto('/session/' + REFEREE);
		const report = page.getByTestId('message-2');
		await expect(report).toContainText('The parity theorem is correct as stated');
		await expect(report.getByTestId('message-fold')).toHaveText('▸ 3 more: notation, referee-review, decision');
		await expect(report).not.toContainText('[summary]');
	});

	test("a body is rendered, and the agent's messages carry a rule", async ({ page }) => {
		await page.goto('/session/' + REFEREE);
		const first = page.getByTestId('message-1');
		await expect(first).toContainText('hostile review of the parity theorem');
		await expect(first).toHaveClass(/agent/);
		await expect(first).toHaveCSS('border-left-style', 'solid');
	});

	test('a \\ref in a message reads as written, never as ???', async ({ page }) => {
		// an agent quoting "the saturation of Proposition~\\ref{sh-0007}" is shown the reference as written, never as `Proposition~???`
		await saying(page, '<p>by the saturation of Proposition~\\ref{sh-0007}, and <span class="math inline">\\(x\\)</span>.</p>');
		await page.goto('/master/main' + beside('/session/' + REFEREE));
		const message = pane(page, 1).getByTestId('message-1');
		await expect(message.locator('mjx-container')).toHaveCount(1); // the mathematics is still typeset
		await expect(message).toContainText('\\ref{sh-0007}');
		await expect(message).not.toContainText('???');
	});

	test('a table in a message is drawn as a ruled table, its cells typeset', async ({ page }) => {
		await saying(page, '<table><thead><tr><th>result</th><th>bound</th></tr></thead><tbody><tr><td>Lemma 2</td><td><span class="math inline">\\(n \\le 2\\)</span></td></tr></tbody></table>');
		await page.goto('/master/main' + beside('/session/' + REFEREE));
		const message = pane(page, 1).getByTestId('message-1');
		await expect(message.locator('table th')).toHaveText(['result', 'bound']);
		await expect(message.locator('table td mjx-container')).toHaveCount(1);
		await expect(message.locator('table td').first()).toHaveCSS('border-bottom-style', 'solid');
	});

	test('with no publisher, the transcript is read from the build, and there is nothing to post with', async ({ page }) => {
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('message-1')).toBeVisible();
		await expect(page.getByTestId('chat').getByRole('textbox')).toHaveCount(0);
	});
});

test.describe('one transcript at a time', () => {
	test('the picker opens the transcript beside, focus stays, and the URL remembers it', async ({ page }) => {
		await page.goto('/node/sy-0003');
		// one pane at rest: a reader who never wants a second carries no frame for it
		await expect(pane(page, 1)).toHaveCount(0);
		// choosing a session opens its transcript beside, and the reader stays in the node
		await pickSession(page, REFEREE);
		await expect(pane(page, 1).getByTestId('chat')).toBeVisible();
		await expect(pane(page, 0)).toHaveClass(/focused/);
		await expect(pane(page, 0).getByTestId('item-controls')).toHaveAttribute('aria-label', /^controls for /);
		// closed, choosing it again opens it again
		await pane(page, 1).getByTestId('tab-close').click();
		await expect(pane(page, 1)).toHaveCount(0);
		await pickSession(page, REFEREE);
		await expect(pane(page, 1).getByTestId('chat')).toBeVisible();
		await expect.poll(() => new URL(page.url()).searchParams.get('beside')).toBe('/session/' + REFEREE);
		await expect(page.getByTestId('divider')).toBeVisible();
		// and the arrangement is a link: a reload reproduces it
		await page.reload();
		await expect(pane(page, 1).getByTestId('chat')).toBeVisible();
		await expect(pane(page, 0).locator('.fragment').first()).toBeVisible();
	});

	test("opening a second session's transcript closes the first, and selects it", async ({ page }) => {
		await page.goto('/node/sy-0003' + beside('/session/' + REFEREE));
		await expect(pane(page, 1).getByTestId('chat')).toBeVisible();
		await expect(page.getByTestId('session-footer-name')).toHaveText('referee');
		// the second is the fixture's closed session, which the picker lists under Closed
		await openPicker(page);
		await page.getByTestId('show-closed').click();
		await page.getByTestId(`session-${QUICK}`).click();
		await expect(pane(page, 1).getByTestId('item-tab')).toHaveCount(1);
		await expect(pane(page, 1).getByRole('tab')).toHaveText('quick');
		await expect(page.getByTestId('session-footer-name')).toHaveText('quick');
	});
});

test.describe('where a publisher serves', () => {
	test('what an agent says arrives from the next poll, with no rebuild, and the viewer offers no way to post', async ({ page }) => {
		// the fixture's referee session holds two messages, its account and its report
		const state = { events: [said(1, 'Referee Agent'), said(2, 'Referee Agent')] };
		await publisher(page, state);
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('message-2')).toBeVisible();
		await expect(page.getByTestId('chat').getByRole('textbox')).toHaveCount(0);
		state.events.push({ seq: 3, kind: 'message', who: 'Referee Agent', when: '2026-09-16T10:06:00Z', body: 'Not reviewed.', body_html: '<p>Not reviewed.</p>' });
		await expect(page.getByTestId('message-3')).toContainText('Not reviewed.');
		await expect(page.getByTestId('message-3')).toBeInViewport();
	});

	test('in a wide pane the transcript takes its width', async ({ page }) => {
		// the paper's measure (33rem) left two thirds of a wide pane blank; the margin is at most 3rem a side
		await page.setViewportSize({ width: 1600, height: 900 });
		await publisher(page, { events: [said(1, 'Referee Agent')] });
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('message-1')).toBeVisible();
		const chat = (await page.getByTestId('chat').boundingBox())!;
		const message = (await page.getByTestId('message-1').boundingBox())!;
		expect(chat.width).toBeGreaterThan(900);
		expect(message.x - chat.x).toBeLessThanOrEqual(49);
		expect(message.width).toBeGreaterThan(chat.width - 2 * 48 - 20);
	});

	test('the first poll follows the newest page at once, not a second later', async ({ page }) => {
		const state = { events: [said(1, 'Referee Agent')] };
		await publisher(page, state);
		// the ask for the newest page carries the largest `since`; every other ask is a poll
		const at: { latest?: number; poll?: number } = {};
		page.on('request', (r) => {
			const since = r.url().includes('/_api/events') ? new URL(r.url()).searchParams.get('since') : null;
			if (since === String(Number.MAX_SAFE_INTEGER)) at.latest ??= Date.now();
			else if (since !== null) at.poll ??= Date.now();
		});
		await page.goto('/session/' + REFEREE);
		await expect.poll(() => at.poll).toBeDefined();
		// the interval is a second; a poll that waited for it would come a second after landing
		expect(at.poll! - at.latest!).toBeLessThan(600);
	});

	test('under a publisher the transcript opens on the newest page the publisher holds, not everything since the last build', async ({ page }) => {
		const asked: string[] = [];
		await page.route('**/_api', (r) => r.fulfill({ json: { write_api: 1, capabilities: ['annotate'], token: 't' } }));
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
		// a reader at the newest stays there when the log's own height changes, as when the window narrows
		await page.setViewportSize({ width: 1100, height: 600 });
		await expect(page.getByTestId('message-250')).toBeInViewport();
		await expect(page.getByTestId('message-200')).toHaveCount(0); // only the newest page, until asked
		// and not the page the stale manifest names beside it, which would hold 1–100 then 201–250 with nothing between; asserted once the transcript is polling from the newest, which is after landing has fetched all it will
		await expect.poll(() => asked.filter((s) => s === '250').length).toBeGreaterThan(0);
		await expect(page.getByTestId('message-100')).toHaveCount(0);
		// scrolling up fills in from the page before, so what is held is always one unbroken run
		await page.getByTestId('chat-log').evaluate((e) => (e.scrollTop = 0));
		await expect(page.getByTestId('message-200')).toHaveCount(1);
		const held = await page.locator('[data-testid^=message-]').evaluateAll((ms) => ms.map((m) => Number(m.getAttribute('data-testid')!.slice(8))));
		expect(held).toEqual(Array.from({ length: held.length }, (_, i) => held[0] + i));
		// every poll after landing asks from the last message held, never from nothing
		expect(asked).not.toContain('0');
	});
});
