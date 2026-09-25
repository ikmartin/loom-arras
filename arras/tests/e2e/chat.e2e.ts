// The Chat: a session's conversation and its input in one pane. The transcript comes from the build's pages, and, where a publisher serves, from a poll of `/_api/events`; the status line and the input exist only where a publisher answers (P3). Each test is named for the rule it holds.
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

/** A publisher that serves messages: the probe, the events poll and the message endpoint. */
async function publisher(page: Page, state: { events: Ev[]; attached: { who: string; kind: string }[] }) {
	await page.route('**/_api', (r) => r.fulfill({ json: { write_api: 1, capabilities: ['message', 'comment'], token: 't' } }));
	await page.route('**/_api/events*', (r) => {
		const since = Number(new URL(r.request().url()).searchParams.get('since') ?? 0);
		const events = state.events.filter((e) => e.seq > since);
		r.fulfill({ json: { session: REFEREE, from: since, seq: state.events.at(-1)?.seq ?? 0, events, attached: state.attached } });
	});
	await page.route('**/_api/message', async (r) => {
		const body = r.request().postDataJSON();
		const seq = (state.events.at(-1)?.seq ?? 0) + 1;
		state.events.push({ seq, kind: 'message', who: 'A. Author', when: '2026-09-16T10:05:00Z', body: body.text, body_html: `<p>${body.text}</p>` });
		r.fulfill({ json: { ok: true, result: `posted to ${REFEREE}`, session: REFEREE, seq, attached: state.attached } });
	});
}

test.describe('the transcript', () => {
	test('the Chat opens on the newest message once the mathematics in it is typeset, with no heading of its own', async ({ page }) => {
		// typesetting grows the messages under the landing, so a Chat scrolled to the bottom before it would leave the newest below the fold
		const display = '<span class="math display">\\[\\sum_{a:t(a)=v} w(a) - \\sum_{a:s(a)=v} w(a) = \\int_0^1 \\frac{x^2}{1+x^2}\\,dx\\]</span>';
		await transcript(page, 40, (s) => `<p>message ${s}</p><p>${display}</p><p>${display}</p>`);
		await page.goto('/master/main' + beside('/session/' + REFEREE));
		const chat = pane(page, 1).getByTestId('chat');
		await expect(chat.locator('mjx-container').first()).toBeAttached();
		await expect.poll(() => chat.locator('.math:not(:has(mjx-container))').count()).toBe(0);
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

	test('with no publisher, the Chat is the transcript alone', async ({ page }) => {
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('message-1')).toBeVisible();
		await expect(page.getByTestId('chat-status')).toHaveCount(0);
		await expect(page.getByTestId('composer')).toHaveCount(0);
	});
});

test.describe('one Chat at a time', () => {
	test('the picker opens the Chat beside, focus stays, and the URL remembers it', async ({ page }) => {
		await page.goto('/node/sy-0003');
		// one pane at rest: a reader who never wants a second carries no frame for it
		await expect(pane(page, 1)).toHaveCount(0);
		// choosing whom to talk to opens the conversation beside, and the reader stays in the node
		await pickSession(page, REFEREE);
		await expect(pane(page, 1).getByTestId('chat')).toBeVisible();
		await expect(pane(page, 0)).toHaveClass(/focused/);
		await expect(page.getByTestId('open-context')).toBeVisible();
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

	test("opening a second session's Chat closes the first, and selects it", async ({ page }) => {
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
	test('the status line says who is listening, and a sent message arrives from the next poll', async ({ page }) => {
		const state = { events: [said(1, 'Referee Agent')], attached: [{ who: 'Referee Agent', kind: 'agent' }] };
		await publisher(page, state);
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('chat-status')).toHaveText('Referee Agent is attached');
		await page.getByTestId('composer-text').fill('And the second proof?');
		await page.getByTestId('composer-send').click();
		await expect(page.getByTestId('message-2')).toContainText('And the second proof?');
		await expect(page.getByTestId('chat-status')).toHaveText('sent · Referee Agent is attached');
		// the answer lands without a manifest rebuild, and the send's note gives way to it
		state.events.push({ seq: 3, kind: 'message', who: 'Referee Agent', when: '2026-09-16T10:06:00Z', body: 'Not reviewed.', body_html: '<p>Not reviewed.</p>' });
		await expect(page.getByTestId('message-3')).toContainText('Not reviewed.');
		await expect(page.getByTestId('chat-status')).toHaveText('Referee Agent is attached');
		await expect(page.getByTestId('message-3')).toBeInViewport();
	});

	test('the first poll follows the newest page at once, not a second later', async ({ page }) => {
		const state = { events: [said(1, 'Referee Agent')], attached: [{ who: 'Referee Agent', kind: 'agent' }] };
		await publisher(page, state);
		// the ask for the newest page carries the largest `since`; every other ask is a poll
		const at: { latest?: number; poll?: number } = {};
		page.on('request', (r) => {
			const since = r.url().includes('/_api/events') ? new URL(r.url()).searchParams.get('since') : null;
			if (since === String(Number.MAX_SAFE_INTEGER)) at.latest ??= Date.now();
			else if (since !== null) at.poll ??= Date.now();
		});
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('chat-status')).toHaveText('Referee Agent is attached');
		// the interval is a second; a poll that waited for it would come a second after landing
		expect(at.poll! - at.latest!).toBeLessThan(600);
	});

	test('under a publisher the Chat opens on the newest page the publisher holds, not everything since the last build', async ({ page }) => {
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
		// a reader at the newest stays there when the log's own height changes: a narrower window, or the tray opening
		await page.setViewportSize({ width: 1100, height: 600 });
		await expect(page.getByTestId('message-250')).toBeInViewport();
		await expect(page.getByTestId('message-200')).toHaveCount(0); // only the newest page, until asked
		// and not the page the stale manifest names beside it, which would hold 1–100 then 201–250 with nothing between; asserted once the Chat is polling from the newest, which is after landing has fetched all it will
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

	test('with nobody listening, it says the message waits', async ({ page }) => {
		const state = { events: [said(1, 'Referee Agent')], attached: [] };
		await publisher(page, state);
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('chat-status')).toHaveText('nobody is attached — messages wait in the inbox');
		await page.getByTestId('composer-text').fill('Hello?');
		await page.keyboard.press('Enter');
		await expect(page.getByTestId('chat-status')).toHaveText('sent · it waits in the inbox');
	});
});

test.describe('packets', () => {
	type Row = { id: string; kind: string; act: string; target: string; work?: string | null; page?: number | null };
	const QUESTION: Row = { id: 'a-2026-09-16-0001', kind: 'question', act: 'created', target: 'sy-0003' };
	const NOTE: Row = { id: 'a-2026-09-16-0004', kind: 'note', act: 'created', target: 'drafting/main.tex' };
	const TEXT = '  a-2026-09-16-0001  question · sy-0003 · created by A. Author\n      "Which orbit?"';

	/** A publisher whose packet holds `rows` until a message carries them. */
	async function packet(page: Page, rows: Row[]) {
		const state = { events: [said(1, 'Referee Agent')], attached: [] as { who: string; kind: string }[], rows: [...rows], posted: [] as unknown[] };
		await publisher(page, state);
		await page.route('**/_api/packet*', (r) => r.fulfill({ json: { session: REFEREE, rows: state.rows, text: state.rows.length ? TEXT : '' } }));
		await page.route('**/_api/message', async (r) => {
			const body = r.request().postDataJSON();
			state.posted.push(body);
			const seq = state.events.length + 1;
			const changed = state.rows.map((x) => ({ ...x, by: 'A. Author' }));
			state.events.push({ seq, kind: 'message', who: 'A. Author', when: '2026-09-16T10:05:00Z', ...(body.text ? { body: body.text, body_html: `<p>${body.text}</p>` } : {}), changed } as Ev);
			state.rows = [];
			r.fulfill({ json: { ok: true, result: `posted to ${REFEREE}`, session: REFEREE, seq, attached: [] } });
		});
		return state;
	}

	test('the tray lists what the next message carries, and is not drawn when it holds nothing', async ({ page }) => {
		await packet(page, [QUESTION, NOTE]);
		await page.goto('/session/' + REFEREE);
		const tray = page.getByTestId('packet-tray');
		await expect(tray.getByTestId(`packet-row-${QUESTION.id}`)).toContainText('question');
		await expect(tray.getByTestId(`packet-row-${QUESTION.id}`)).toContainText('Theorem 2.1');
		await expect(tray.getByTestId(`packet-row-${NOTE.id}`)).toContainText('main.tex');
		// the preview is the publisher's own text, verbatim
		await tray.getByTestId('packet-preview-toggle').click();
		expect(await tray.getByTestId('packet-preview').textContent()).toBe(TEXT);
	});

	test('the preview is read whole, however long the transcript above it', async ({ page }) => {
		// the principles check: under a long transcript the tray shrank with the log, and the preview showed one clipped line
		const state = await packet(page, [QUESTION, NOTE]);
		for (let n = 2; n <= 60; n++) state.events.push(said(n, 'Referee Agent'));
		const long = Array.from({ length: 12 }, (_, i) => `      line ${i + 1} of what the agent will read`).join('\n');
		await page.route('**/_api/packet*', (r) => r.fulfill({ json: { session: REFEREE, rows: state.rows, text: TEXT + '\n' + long } }));
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('message-60')).toBeAttached();
		const tray = page.getByTestId('packet-tray');
		await tray.getByTestId('packet-preview-toggle').click();
		// as tall as what it holds, up to its cap of 40% of the Chat; past that it scrolls
		const [own, holds, chat] = await tray.evaluate((t) => [t.clientHeight, t.scrollHeight, t.parentElement!.clientHeight]);
		expect(own).toBeGreaterThanOrEqual(Math.min(holds, Math.floor(chat * 0.4)) - 1);
		// and opening it kept the reader at the newest message
		await expect(page.getByTestId('message-60')).toBeInViewport();
	});

	test('with nothing marked there is no tray', async ({ page }) => {
		await packet(page, []);
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('chat-status')).toBeVisible();
		await expect(page.getByTestId('packet-tray')).toHaveCount(0);
		await expect(page.getByTestId('composer-send')).toBeDisabled();
	});

	test('a row links its annotation by its quilt: address, which opens where every such link does', async ({ page }) => {
		// where the link opens, and that the Chat stays, is the one rule's (links.e2e.ts); the row's part is to link the annotation
		await packet(page, [QUESTION]);
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId(`packet-row-${QUESTION.id}`).locator('a')).toHaveAttribute('href', `quilt:${QUESTION.id}`);
	});

	test('a packet goes without words, the tray empties, and the message says what it carried', async ({ page }) => {
		const state = await packet(page, [QUESTION, NOTE]);
		await page.goto('/session/' + REFEREE);
		const send = page.getByTestId('composer-send');
		await expect(page.getByTestId('packet-tray')).toBeVisible();
		await expect(send).toBeEnabled();
		await send.click();
		await expect(page.getByTestId('packet-tray')).toHaveCount(0);
		const sent = page.getByTestId('message-2');
		await expect(sent.getByTestId('message-carried')).toHaveText('carried 1 question, 1 note');
		// no words: the message is who, when, and what it carried
		await expect(sent.locator('.body')).toHaveCount(0);
		expect(state.posted).toEqual([{ text: '', session: REFEREE }]);
	});
});

test.describe('an agent loom starts', () => {
	type Agent = { launch: boolean; name: string; state?: string; error?: string; activity?: string; blocked?: string; started?: string };

	/** A publisher whose events answer carries `agent`, as `loom serve` does. */
	async function starting(page: Page, agent: Agent) {
		const state = { agent, stops: 0 };
		await page.route('**/_api', (r) => r.fulfill({ json: { write_api: 1, capabilities: ['message', 'agent-stop'], token: 't' } }));
		await page.route('**/_api/packet*', (r) => r.fulfill({ json: { session: REFEREE, rows: [], text: '' } }));
		await page.route('**/_api/events*', (r) =>
			r.fulfill({ json: { session: REFEREE, from: 0, seq: 1, events: [said(1, 'Referee Agent')], attached: [], agent: state.agent } })
		);
		await page.route('**/_api/agent-stop', (r) => {
			state.stops++;
			state.agent = { ...state.agent, state: 'stopped' };
			r.fulfill({ json: { ok: true, result: 'stopped', session: REFEREE } });
		});
		return state;
	}

	test('a running turn says what it last ran, and stop ends it', async ({ page }) => {
		const state = await starting(page, { launch: true, name: 'Claude Agent', state: 'running', activity: 'loom source sy-0003 --closure' });
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('chat-status')).toHaveText('Claude Agent is working · loom source sy-0003 --closure');
		await page.getByTestId('agent-stop').click();
		await expect(page.getByTestId('chat-status')).toHaveText('Claude Agent was stopped');
		await expect(page.getByTestId('agent-stop')).toHaveCount(0);
		expect(state.stops).toBe(1);
	});

	test('a failed turn says why, with nothing to stop', async ({ page }) => {
		await starting(page, { launch: true, name: 'Claude Agent', state: 'failed', error: 'claude is not on PATH' });
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('chat-status')).toHaveText('Claude Agent could not run: claude is not on PATH');
		await expect(page.getByTestId('agent-stop')).toHaveCount(0);
	});

	test('where loom starts agents and none is running, it says sending starts one', async ({ page }) => {
		await starting(page, { launch: true, name: 'Claude Agent' });
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('chat-status')).toHaveText('Claude Agent starts when you send');
	});

	test('where it does not, the line is who is listening, as before', async ({ page }) => {
		await starting(page, { launch: false, name: '' });
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('chat-status')).toHaveText('nobody is attached — messages wait in the inbox');
	});

	test('where something keeps loom from starting the agent, the Chat says what', async ({ page }) => {
		await starting(page, { launch: true, name: 'Claude Agent', blocked: 'git tracks ai/ai-config.toml, so loom will not run it' });
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('chat-status')).toHaveText('Claude Agent cannot be started: git tracks ai/ai-config.toml, so loom will not run it');
	});

	test('a turn that fails after a send says so, rather than that the agent will start', async ({ page }) => {
		// the send's own note must not outrank the turn's failure, or the line says "will start" for ever
		const state = await starting(page, { launch: true, name: 'Claude Agent' });
		await page.route('**/_api/message', (r) => {
			// the turn starts after the send, by the test's clock, which is the browser's on this machine
			state.agent = { ...state.agent, state: 'failed', error: 'Session ID is already in use.', started: new Date(Date.now() + 1000).toISOString().replace(/\.\d{3}Z$/, 'Z') };
			r.fulfill({ json: { ok: true, result: 'posted', session: REFEREE, seq: 2, attached: [] } });
		});
		await page.goto('/session/' + REFEREE);
		await page.getByTestId('composer-text').fill('Hello?');
		await page.getByTestId('composer-send').click();
		await expect(page.getByTestId('chat-status')).toHaveText('Claude Agent could not run: Session ID is already in use.');
	});
});
